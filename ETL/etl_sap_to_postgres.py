"""
etl_sap_to_postgres.py - ETL: Sync PR & PO dari Excel ke PostgreSQL (Lokal)

Cara pakai:
  1. Pastikan file 'PR SAP.xlsx' dan 'PO SAP.xlsx' ada di folder yang sama
  2. Jalankan: python etl_sap_to_postgres.py

Cara kerja (UPSERT):
  - Data baru   → INSERT
  - Data lama yang berubah (status, tanggal GR, dll) → UPDATE otomatis
  - Aman dijalankan berkali-kali (idempotent)
  - Cocok untuk sync mingguan dari file Excel akumulatif

Requirements:
  pip install pandas openpyxl sqlalchemy psycopg2-binary tqdm --break-system-packages
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')


# =====================================================
# KONFIGURASI
# =====================================================

class Config:
    DB_HOST     = 'localhost'
    DB_PORT     = '5432'
    DB_NAME     = 'pr_po_monitoring'
    DB_USER     = 'postgres'
    DB_PASSWORD = 'Hx4Khos2'

    PR_FILE = 'PR SAP - 2026 - Mar.xlsx'
    PO_FILE = 'PO SAP - 2026 - Mar.xlsx'


# =====================================================
# DATABASE
# =====================================================

def get_db_engine():
    cs = f"postgresql://{Config.DB_USER}:{Config.DB_PASSWORD}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}"
    return create_engine(cs)


# =====================================================
# DATA CLEANING
# =====================================================

def clean_numeric(value):
    try:
        if pd.isna(value): return None
        return float(value)
    except: return None

def clean_string(value):
    if pd.isna(value) or value == 'nan': return None
    return str(value).strip()

def clean_date(value):
    if pd.isna(value) or str(value).strip() in ['NaT', 'nan', 'None', '']: 
        return None
        
    if isinstance(value, (int, float)) or str(value).replace('.0', '').isdigit():
        try:
            # Excel menghitung hari sejak 30 Desember 1899
            return pd.to_datetime(int(float(value)), unit='D', origin='1899-12-30')
        except:
            pass
            
    try: 
        return pd.to_datetime(value, dayfirst=True)
    except: 
        return None

def clean_boolean(value):
    if pd.isna(value): return False
    if isinstance(value, bool): return value
    return str(value).upper() in ['TRUE', 'YES', 'X', '1']


# =====================================================
# KLASIFIKASI BAGIAN
# =====================================================

def _bagian_logic(tracking_no, department, purchasing_group, material_no_raw):
    tracking_no      = str(tracking_no).strip().upper()      if pd.notna(tracking_no)      else ''
    department       = str(department).strip().upper()       if pd.notna(department)       else ''
    purchasing_group = str(purchasing_group).strip().upper() if pd.notna(purchasing_group) else ''
    try:    material_no = str(int(float(material_no_raw))).strip() if pd.notna(material_no_raw) else ''
    except: material_no = str(material_no_raw).replace('.0', '').strip()

    bb_groups     = ['B01', 'B02', 'B03', 'B04', 'B06', 'B18', 'B19']
    alpata_groups = ['B08', 'B09', 'B10', 'B11', 'B12', 'B17', 'B20', 'B23']

    if 'PDSPPB' in tracking_no or (department.startswith('INV') and len(department) > 3):
        return 'BARUM'
    if material_no == '3000002' or purchasing_group in bb_groups:
        return 'BB/BD/BP'
    if purchasing_group in alpata_groups:
        return 'ALPATA'
    return 'BARUM'

def classify_bagian(row):
    return _bagian_logic(row.get('Tracking No'), row.get('Departement(Requisitioner)'),
                         row.get('Purchasing Group'), row.get('Material No'))

def classify_bagian_po(row):
    return _bagian_logic(row.get('Tracking No'), row.get('Departement(Requisitioner)'),
                         row.get('Purchasing Group'), row.get('Material No'))

def classify_bagian_by_creator(created_by_raw):
    if pd.isna(created_by_raw) or str(created_by_raw).lower() == 'nan':
        return 'UNKNOWN'
    
    cb = str(created_by_raw).strip().upper()
    if cb.endswith('.0'):
        cb = cb[:-2]
        
    alpata_users = {'2135855', '2145923', '2146001', '2166521', '2190478', 'B3410000ST04', 'B3410000ST05', 'B3410000ST06', 'B3410000ST08', 'B3410000ST13', 'SYS_EPROC'}
    barum_users = {'2095185', '2156378', '2180261', '2115464', 'B3410000ST07', 'B3410000ST09', 'B3410000ST10', 'B3410000ST11'}
    bb_users = {'2156257', 'B3410000ST01', 'B3410000ST02', '2190583'}

    if cb in alpata_users:
        return 'ALPATA'
    elif cb in barum_users:
        return 'BARUM'
    elif cb in bb_users:
        return 'BB/BD/BP'
    else:
        return 'UNKNOWN'


# =====================================================
# ON TIME DELIVERY
# =====================================================

def calculate_ontime_delivery(row):
    try:
        mat_raw = row.get('Material No', '')
        mat_no  = str(int(float(mat_raw))) if pd.notna(mat_raw) else ''
    except: mat_no = str(row.get('Material No', '')).strip()

    if mat_no == '1000076': return None
    if str(row.get('PO Deletion Flag', '')).strip().upper() == 'L': return None

    del_completed = str(row.get('Delivery Completed', '')).strip().upper()

    # IN PROGRESS: Delivery Completed belum 'X' (barang belum diterima semua,
    # bisa sebagian sudah diterima atau belum sama sekali)
    if del_completed != 'X':
        return 'IN PROGRESS'

    # Delivery Completed = 'X' → cek apakah tepat waktu atau terlambat
    tgl_terima = clean_date(row.get('Tgl Terima Barang'))
    tgl_janji  = clean_date(row.get('Del Date PO'))
    if pd.isna(tgl_terima) or pd.isna(tgl_janji): return None
    return 'TEPAT WAKTU' if tgl_terima <= tgl_janji else 'TERLAMBAT'


# =====================================================
# EXTRACT & FILTER EXCEL
# =====================================================

def load_excel_files():
    print("📂 Membaca file Excel (ini memakan waktu, harap tunggu)...")

    try:
        df_pr = pd.read_excel(Config.PR_FILE)
        n0 = len(df_pr)
        col_flag = df_pr['PR Deletion Flag'].fillna('').astype(str).str.strip().str.upper() if 'PR Deletion Flag' in df_pr.columns else pd.Series([''] * n0)
        col_acc  = df_pr['Account Assignment'].fillna('').astype(str).str.strip().str.upper() if 'Account Assignment' in df_pr.columns else pd.Series([''] * n0)
        pr_mat   = 'Material No' if 'Material No' in df_pr.columns else 'Material'
        col_mat  = df_pr[pr_mat].astype(str).str.replace('.0', '', regex=False).str.strip() if pr_mat in df_pr.columns else pd.Series([''] * n0)

        m_batal   = (col_flag == 'X')
        m_kontrak = col_acc.str.startswith('U')
        m_petro   = col_mat.str.contains('1000076', na=False) & ~m_kontrak

        df_pr = df_pr[~m_batal & ~m_kontrak & ~m_petro].dropna(subset=['No PR'])
        print(f"   PR  : {n0:,} baris raw → {len(df_pr):,} bersih  (-{n0-len(df_pr)} | batal={m_batal.sum()}, kontrak={m_kontrak.sum()}, petro={m_petro.sum()})")
    except Exception as e:
        print(f"❌ Gagal membaca PR: {e}"); return None, None

    try:
        df_po = pd.read_excel(Config.PO_FILE)
        n0 = len(df_po)
        po_mat   = 'Material No' if 'Material No' in df_po.columns else 'Material'
        col_mp   = df_po[po_mat].astype(str).str.replace('.0', '', regex=False).str.strip() if po_mat in df_po.columns else pd.Series([''] * n0)
        del_cols = ['PO Deletion Flag', 'Deletion Indicator', 'D', 'L']
        tdc      = next((c for c in del_cols if c in df_po.columns), None)
        col_del  = df_po[tdc].fillna('').astype(str).str.strip().str.upper() if tdc else pd.Series([''] * n0)

        m_petro  = col_mp.str.contains('1000076', na=False)
        m_batal  = (col_del == 'L')

        df_po = df_po[~m_petro & ~m_batal].dropna(subset=['Nomor PO'])

        # Filter: buang baris PO yang Created By-nya tidak dikenal
        known_users = (
            {'2135855', '2145923', '2146001', '2166521', '2190478', 'B3410000ST04', 'B3410000ST05', 'B3410000ST06', 'B3410000ST08', 'B3410000ST13'}  # ALPATA
            | {'2095185', '2156378', '2180261', 'B3410000ST07', 'B3410000ST09', 'B3410000ST10', 'B3410000ST11'}  # BARUM
            | {'2156257', 'B3410000ST01', 'B3410000ST02', '2190583'}  # BB/BD/BP
        )

        def _normalize_created_by(val):
            if pd.isna(val) or str(val).strip().lower() == 'nan':
                return ''
            s = str(val).strip().upper()
            if s.endswith('.0'):
                s = s[:-2]
            return s

        if 'Created By' in df_po.columns:
            cb_norm = df_po['Created By'].apply(_normalize_created_by)
            m_unknown = ~cb_norm.isin(known_users)
            unknown_count = m_unknown.sum()
            if unknown_count > 0:
                unknown_vals = cb_norm[m_unknown].unique().tolist()
                print(f"   ⚠️  PO dibuang (Created By tidak dikenal): {unknown_count} baris → {unknown_vals}")
            df_po = df_po[~m_unknown]

        print(f"   PO  : {n0:,} baris raw → {len(df_po):,} bersih  (-{n0-len(df_po)} | petro={m_petro.sum()}, batal={m_batal.sum()}, unknown_user={unknown_count if 'Created By' in df_po.columns else 0})")
    except Exception as e:
        print(f"❌ Gagal membaca PO: {e}"); return df_pr, None

    return df_pr, df_po


# =====================================================
# UPSERT HELPERS
# =====================================================

def upsert(engine, table, rows, conflict_cols, update_cols, chunksize=1000):
    if not rows:
        return 0, 0

    inserted = updated = 0
    all_cols = list(rows[0].keys())

    set_clause = ', '.join(f"{c} = EXCLUDED.{c}" for c in update_cols)
    conflict   = ', '.join(conflict_cols)
    cols_str   = ', '.join(f':{c}' for c in all_cols)
    col_names  = ', '.join(all_cols)

    sql = text(f"""
        INSERT INTO {table} ({col_names})
        VALUES ({cols_str})
        ON CONFLICT ({conflict}) DO UPDATE SET {set_clause}
        RETURNING (xmax = 0) AS is_insert
    """)

    for i in range(0, len(rows), chunksize):
        chunk = rows[i:i+chunksize]
        with engine.begin() as conn:
            for row in chunk:
                r = conn.execute(sql, row)
                if r.fetchone()[0]: inserted += 1
                else: updated += 1

    return inserted, updated


# =====================================================
# MASTER DATA UPSERT
# =====================================================

def sync_master_data(df_pr, df_po, engine):
    stats = {}

    # Plants
    plants = set(df_pr['Plant'].dropna().unique()) | set(df_po['Plant'].dropna().unique())
    rows   = [{'plant_code': clean_string(p), 'plant_name': f'Plant {p}'} for p in plants if clean_string(p)]
    i, u   = upsert(engine, 'plants', rows, ['plant_code'], ['plant_name'])
    stats['Plants'] = (i, u)

    # Departments
    dept_rows = []
    seen = set()
    df_pr_dept = df_pr[['Departement(Requisitioner)']].drop_duplicates()
    for _, row in tqdm(df_pr_dept.iterrows(), total=len(df_pr_dept), desc=" Master Dept (PR)", leave=False):
        d = clean_string(row['Departement(Requisitioner)'])
        if d and d not in seen:
            dept_rows.append({'department_code': d, 'department_name': d, 'bagian': classify_bagian(row)})
            seen.add(d)
            
    df_po_dept = df_po[['Departement(Requisitioner)']].drop_duplicates()
    for _, row in tqdm(df_po_dept.iterrows(), total=len(df_po_dept), desc=" Master Dept (PO)", leave=False):
        d = clean_string(row['Departement(Requisitioner)'])
        if d and d not in seen:
            dept_rows.append({'department_code': d, 'department_name': d, 'bagian': classify_bagian_po(row)})
            seen.add(d)
    i, u = upsert(engine, 'departments', dept_rows, ['department_code'], ['department_name', 'bagian'])
    stats['Departments'] = (i, u)

    # Vendors
    vendor_rows = []
    seen = set()
    df_po_vendor = df_po[['Vendor Code','Vendor Name','Vendor Account Group','City','Salesperson']].drop_duplicates()
    for _, row in tqdm(df_po_vendor.iterrows(), total=len(df_po_vendor), desc=" Master Vendor (PO)", leave=False):
        vc = clean_string(row['Vendor Code'])
        if vc:
            try: code = str(int(float(vc)))
            except: continue
            if code not in seen:
                vendor_rows.append({'vendor_code': code, 'vendor_name': clean_string(row['Vendor Name']),
                    'vendor_account_group': clean_string(row['Vendor Account Group']), 'city': clean_string(row['City']),
                    'salesperson': clean_string(row.get('Salesperson'))})
                seen.add(code)
                
    df_pr_vendor = df_pr[['Vendor Code','Vendor Name','Vendor Account Group','City']].drop_duplicates()
    for _, row in tqdm(df_pr_vendor.iterrows(), total=len(df_pr_vendor), desc=" Master Vendor (PR)", leave=False):
        vc = clean_numeric(row['Vendor Code'])
        if vc:
            code = str(int(vc))
            if code not in seen:
                vendor_rows.append({'vendor_code': code, 'vendor_name': clean_string(row['Vendor Name']),
                    'vendor_account_group': clean_string(row['Vendor Account Group']), 'city': clean_string(row['City']), 'salesperson': None})
                seen.add(code)
    i, u = upsert(engine, 'vendors', vendor_rows, ['vendor_code'],
                  ['vendor_name', 'vendor_account_group', 'city', 'salesperson'])
    stats['Vendors'] = (i, u)

    # Materials
    mat_rows, seen = [], set()
    for src, unit_col, desc in [(df_po, 'Satuan PO', 'PO'), (df_pr, 'Satuan PR', 'PR')]: 
        df_mat = src[['Material No','Description','Material Group','ABC Indicator', unit_col]].drop_duplicates()
        for _, row in tqdm(df_mat.iterrows(), total=len(df_mat), desc=f" Master Material ({desc})", leave=False):
            mn = clean_numeric(row['Material No'])
            if mn:
                code = str(int(mn))
                if code not in seen:
                    mat_rows.append({'material_no': code, 'description': clean_string(row['Description']),
                        'material_group': clean_string(row['Material Group']),
                        'abc_indicator': clean_string(row['ABC Indicator']),
                        'base_unit': clean_string(row[unit_col])})
                    seen.add(code)
    i, u = upsert(engine, 'materials', mat_rows, ['material_no'],
                  ['description', 'material_group', 'abc_indicator', 'base_unit'])
    stats['Materials'] = (i, u)

    # Contracts
    contract_rows, seen = [], set()
    for src, desc in [(df_pr, 'PR'), (df_po, 'PO')]:
        sub = src[['No Contract','No Item Contract','Vendor Code']].dropna(subset=['No Contract']).drop_duplicates()
        for _, row in tqdm(sub.iterrows(), total=len(sub), desc=f" Master Contract ({desc})", leave=False):
            cno = clean_string(row['No Contract'])
            if cno and cno.lower() != 'nan' and cno not in seen:
                vc = clean_string(row['Vendor Code'])
                try: vc = str(int(float(vc))) if vc else None
                except: vc = None
                contract_rows.append({'contract_no': cno,
                    'contract_item': clean_string(row['No Item Contract']), 'vendor_code': vc})
                seen.add(cno)
    i, u = upsert(engine, 'contracts', contract_rows, ['contract_no'], ['contract_item', 'vendor_code'])
    stats['Contracts'] = (i, u)

    return stats


# =====================================================
# PR UPSERT
# =====================================================

def sync_purchase_requisitions(df_pr, engine):
    pr_headers = df_pr.groupby('No PR').first().reset_index()

    # == HAPUS DATA LAMA YANG SUDAH TIDAK ADA DI FILE TERBARU =================
    # File Excel bersifat akumulatif & definitif: jika suatu No PR + Line Item PR
    # sudah tidak ada di file (misal karena dibatalkan / dihapus di SAP),
    # maka baris tersebut harus dihapus dari DB agar tidak menggembungkan hitungan.
    pr_items_in_file = set(
        (clean_string(row['No PR']), int(clean_numeric(row['Line/Item PR'])))
        for _, row in df_pr.drop_duplicates(subset=['No PR','Line/Item PR']).iterrows()
        if clean_string(row['No PR']) and pd.notna(row['Line/Item PR'])
    )
    pr_nos_in_file = set(clean_string(row['No PR']) for _, row in pr_headers.iterrows())

    # -- TAMBAHKAN PEMBATASAN RENTANG TANGGAL DARI FILE EXCEL --
    min_date = df_pr['Tgl Create PR'].min().strftime('%Y-%m-%d')
    max_date = df_pr['Tgl Create PR'].max().strftime('%Y-%m-%d')

    with engine.connect() as conn:
        # HANYA tarik data DB yang beririsan dengan tanggal di Excel
        db_pr_items = pd.read_sql(f"""
            SELECT pr_item_id, no_pr, line_item_pr 
            FROM pr_items 
            WHERE tgl_create_pr >= '{min_date}' AND tgl_create_pr <= '{max_date}'
        """, conn)
        
        db_pr_headers = pd.read_sql(f"""
            SELECT pr_id, no_pr 
            FROM purchase_requisitions 
            WHERE tgl_create_pr >= '{min_date}' AND tgl_create_pr <= '{max_date}'
        """, conn)

    # Items yang ada di DB tapi tidak ada di file → hapus
    obsolete_item_ids = [
        int(r['pr_item_id'])
        for _, r in db_pr_items.iterrows()
        if (clean_string(r['no_pr']), int(r['line_item_pr'])) not in pr_items_in_file
    ]
    if obsolete_item_ids:
        print(f"   🗑️  PR Items obsolete dihapus: {len(obsolete_item_ids)} baris")
        chunks = [obsolete_item_ids[i:i+500] for i in range(0, len(obsolete_item_ids), 500)]
        with engine.begin() as conn:
            for chunk in chunks:
                ph = ",".join(str(x) for x in chunk)
                conn.execute(text(f"UPDATE po_items SET pr_item_id = NULL WHERE pr_item_id IN ({ph})"))
                conn.execute(text(f"DELETE FROM pr_release_history WHERE pr_item_id IN ({ph})"))
                conn.execute(text(f"DELETE FROM pr_items WHERE pr_item_id IN ({ph})"))

    # PR Headers yang ada di DB tapi tidak ada di file → hapus beserta child-nya
    obsolete_pr_ids = [
        int(r['pr_id'])
        for _, r in db_pr_headers.iterrows()
        if clean_string(r['no_pr']) not in pr_nos_in_file
    ]
    if obsolete_pr_ids:
        print(f"   🗑️  PR Headers obsolete dihapus: {len(obsolete_pr_ids)} baris")
        chunks = [obsolete_pr_ids[i:i+500] for i in range(0, len(obsolete_pr_ids), 500)]
        with engine.begin() as conn:
            for chunk in chunks:
                ph = ",".join(str(x) for x in chunk)
                conn.execute(text(f"""
                    DELETE FROM pr_release_history WHERE pr_item_id IN (
                        SELECT pr_item_id FROM pr_items WHERE pr_id IN ({ph})
                    )
                """))
                conn.execute(text(f"DELETE FROM pr_items WHERE pr_id IN ({ph})"))
                conn.execute(text(f"DELETE FROM purchase_requisitions WHERE pr_id IN ({ph})"))

    # --- Headers ---
    header_rows = []
    for _, row in tqdm(pr_headers.iterrows(), total=len(pr_headers), desc=" PR Headers", leave=False):
        header_rows.append({
            'no_pr':            clean_string(row['No PR']),
            'tgl_create_pr':    clean_date(row['Tgl Create PR']),
            'department_code':  clean_string(row['Departement(Requisitioner)']),
            'plant_code':       clean_string(row['Plant']),
            'mrp_controller':   clean_string(row['MRP Controller']),
            'purchasing_group': clean_string(row['Purchasing Group']),
            'bulan_pr':         clean_numeric(row.get('BULAN PR')),
            'pr_deletion_flag': clean_string(row['PR Deletion Flag']),
            'pr_closed':        clean_string(row['PR Closed']),
            'bagian_pr':        clean_string(row.get('Bagian') if 'Bagian' in row else row.get('BAGIAN'))
        })

    hi, hu = upsert(engine, 'purchase_requisitions', header_rows, ['no_pr'],
                    ['tgl_create_pr','department_code','plant_code','mrp_controller',
                     'purchasing_group','bulan_pr','pr_deletion_flag','pr_closed','bagian_pr'])

    # --- Items ---
    with engine.connect() as conn:
        pr_id_map       = pd.read_sql("SELECT pr_id, no_pr FROM purchase_requisitions", conn)
        valid_contracts = set(pd.read_sql("SELECT contract_no FROM contracts", conn)['contract_no'].tolist())

    item_rows = []
    df_pr_items = df_pr.drop_duplicates(subset=['No PR','Line/Item PR'])
    for _, row in tqdm(df_pr_items.iterrows(), total=len(df_pr_items), desc=" PR Items", leave=False):
        no_pr = clean_string(row['No PR'])
        ids   = pr_id_map[pr_id_map['no_pr'] == no_pr]['pr_id'].values
        if len(ids) == 0: continue
        material_no = clean_numeric(row['Material No'])
        contract_no = clean_string(row['No Contract'])
        if contract_no and contract_no not in valid_contracts: contract_no = None
        item_rows.append({
            'pr_id':                       int(ids[0]),
            'no_pr':                       no_pr,
            'tgl_create_pr':               clean_date(row['Tgl Create PR']),
            'line_item_pr':                int(clean_numeric(row['Line/Item PR'])),
            'bagian_pr':                   classify_bagian(row),
            'department_code':             clean_string(row.get('Departement(Requisitioner)')),
            'plant_code':                  clean_string(row.get('Plant')),
            'material_no':                 str(int(material_no)) if material_no else None,
            'description':                 clean_string(row['Description']),
            'quantity_pr':                 clean_numeric(row['Quantity PR']),
            'satuan_pr':                   clean_string(row['Satuan PR']),
            'estimasi_pr':                 clean_numeric(row['Estimasi PR']),
            'currency_pr':                 clean_string(row['Currency PR']),
            'pr_release_status':           clean_string(row['PR Release Status']),
            'tracking_no':                 clean_string(row['Tracking No']),
            'cost_center':                 clean_string(row['Cost Center']),
            'gl_account':                  clean_string(row['GL Account']),
            'account_assignment':          clean_string(row['Account Assignment']),
            'contract_no':                 contract_no,
            'contract_item':               clean_string(row['No Item Contract']),
            'e_proc':                      clean_string(row['E-Proc']),
            'metode_pelelangan':           clean_string(row['Metode Pelelangan']),
            'inv_normal':                  clean_string(row.get('INV/NORMAL')),
            'turn_around':                 clean_string(row.get('turn around')),
            'pr_u':                        clean_boolean(row.get('PR U')),
            'kontrak':                     clean_string(row.get('KONTRAK')),
            'pupuk_organik':               clean_string(row.get('Pupuk Organik')),
            'batal':                       clean_boolean(row.get('BATAL')),
            'source_determination_via':    clean_string(row['Source Determination Via']),
            'status_source_determination': clean_string(row['Status Source Determination']),
            'first_full_release':          clean_date(row.get('1St Full Release'))
        })

    update_cols_pr_item = [
        'pr_id','tgl_create_pr','bagian_pr','department_code','plant_code','material_no','description','quantity_pr',
        'satuan_pr','estimasi_pr','currency_pr','pr_release_status','tracking_no',
        'cost_center','gl_account','account_assignment','contract_no','contract_item',
        'e_proc','metode_pelelangan','inv_normal','turn_around','pr_u','kontrak',
        'pupuk_organik','batal','source_determination_via','status_source_determination',
        'first_full_release'
    ]
    ii, iu = upsert(engine, 'pr_items', item_rows, ['no_pr','line_item_pr'], update_cols_pr_item)

    # --- Release History ---
    pr_nos_in_file = list(set(clean_string(r['no_pr']) for r in item_rows))
    pr_nos_set     = set(pr_nos_in_file)
    with engine.connect() as conn:
        pr_items_map = pd.read_sql("SELECT pr_item_id, no_pr, line_item_pr FROM pr_items", conn)
    pr_items_map = pr_items_map[pr_items_map['no_pr'].isin(pr_nos_set)]

    release_rows = []
    df_pr_release = df_pr[df_pr['No PR'].astype(str).isin(pr_nos_in_file)]
    for _, row in tqdm(df_pr_release.iterrows(), total=len(df_pr_release), desc=" PR Release History", leave=False):
        no_pr, line = clean_string(row['No PR']), clean_numeric(row['Line/Item PR'])
        pi = pr_items_map[(pr_items_map['no_pr'] == no_pr) & (pr_items_map['line_item_pr'] == line)]
        if pi.empty: continue
        pid = int(pi['pr_item_id'].values[0])
        for i in range(1, 5):
            col = f'PR RL{i}'
            if col in row.index and pd.notna(row[col]):
                release_rows.append({'pr_item_id': pid, 'release_level': col, 'release_date': clean_date(row[col])})

    if not pr_items_map.empty:
        pr_item_ids = pr_items_map['pr_item_id'].tolist()
        for i in range(0, len(pr_item_ids), 1000):
            chunk_ids = pr_item_ids[i:i+1000]
            placeholders = ','.join(str(x) for x in chunk_ids)
            with engine.begin() as conn:
                conn.execute(text(f"DELETE FROM pr_release_history WHERE pr_item_id IN ({placeholders})"))
    if release_rows:
        for i in range(0, len(release_rows), 1000):
            with engine.begin() as conn:
                pd.DataFrame(release_rows[i:i+1000]).to_sql('pr_release_history', conn, if_exists='append', index=False)

    return hi, hu, ii, iu


# =====================================================
# PO UPSERT
# =====================================================

def sync_purchase_orders(df_po, engine):
    # Ambil data header dari baris pertama per PO untuk kolom statis
    po_headers = df_po.groupby('Nomor PO').first().reset_index()

    # == HAPUS DATA LAMA YANG SUDAH TIDAK ADA DI FILE TERBARU =================
    # File Excel PO bersifat akumulatif & definitif. PO/item yang sudah tidak
    # ada (dibatalkan, dihapus, atau difilter karena Created By tidak dikenal)
    # harus dihapus dari DB agar hitungan Total PO tidak menggelembung.
    po_items_in_file = set(
        (clean_string(row["Nomor PO"]), int(clean_numeric(row["Item PO"])))
        for _, row in df_po.iterrows()
        if clean_string(row["Nomor PO"]) and pd.notna(row["Item PO"])
    )
    po_nos_in_file = set(clean_string(row["Nomor PO"]) for _, row in po_headers.iterrows())

    # -- TAMBAHKAN PEMBATASAN RENTANG TANGGAL DARI FILE EXCEL --
    min_date = po_headers['Date Ordered'].min().strftime('%Y-%m-%d')
    max_date = po_headers['Date Ordered'].max().strftime('%Y-%m-%d')

    with engine.connect() as conn:
        # HANYA tarik data DB yang beririsan dengan tanggal di Excel
        db_po_items = pd.read_sql(f"""
            SELECT poi.po_item_id, poi.nomor_po, poi.item_po 
            FROM po_items poi
            JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
            WHERE poh.date_ordered >= '{min_date}' AND poh.date_ordered <= '{max_date}'
        """, conn)
        
        db_po_headers = pd.read_sql(f"""
            SELECT po_id, nomor_po 
            FROM purchase_orders 
            WHERE date_ordered >= '{min_date}' AND date_ordered <= '{max_date}'
        """, conn)

    # PO Items yang ada di DB tapi tidak ada di file → hapus
    obsolete_po_item_ids = [
        int(r["po_item_id"])
        for _, r in db_po_items.iterrows()
        if (clean_string(r["nomor_po"]), int(r["item_po"])) not in po_items_in_file
    ]
    if obsolete_po_item_ids:
        print(f"   🗑️  PO Items obsolete dihapus: {len(obsolete_po_item_ids)} baris")
        chunks = [obsolete_po_item_ids[i:i+500] for i in range(0, len(obsolete_po_item_ids), 500)]
        with engine.begin() as conn:
            for chunk in chunks:
                ph = ",".join(str(x) for x in chunk)
                conn.execute(text(f"DELETE FROM po_release_history WHERE po_item_id IN ({ph})"))
                conn.execute(text(f"DELETE FROM goods_receipt WHERE po_item_id IN ({ph})"))
                conn.execute(text(f"DELETE FROM po_items WHERE po_item_id IN ({ph})"))

    # PO Headers yang ada di DB tapi tidak ada di file → hapus beserta child-nya
    obsolete_po_ids = [
        int(r["po_id"])
        for _, r in db_po_headers.iterrows()
        if clean_string(r["nomor_po"]) not in po_nos_in_file
    ]
    if obsolete_po_ids:
        print(f"   🗑️  PO Headers obsolete dihapus: {len(obsolete_po_ids)} baris")
        chunks = [obsolete_po_ids[i:i+500] for i in range(0, len(obsolete_po_ids), 500)]
        with engine.begin() as conn:
            for chunk in chunks:
                ph = ",".join(str(x) for x in chunk)
                conn.execute(text(f"""
                    DELETE FROM po_release_history WHERE po_item_id IN (
                        SELECT po_item_id FROM po_items WHERE po_id IN ({ph})
                    )
                """))
                conn.execute(text(f"""
                    DELETE FROM goods_receipt WHERE po_item_id IN (
                        SELECT po_item_id FROM po_items WHERE po_id IN ({ph})
                    )
                """))
                conn.execute(text(f"DELETE FROM po_items WHERE po_id IN ({ph})"))
                conn.execute(text(f"DELETE FROM purchase_orders WHERE po_id IN ({ph})"))

    # --- Hitung delivery_completed per Nomor PO secara tepat ---
    # 'X' hanya jika SEMUA item di PO tersebut sudah Delivery Completed = 'X'
    def _agg_delivery_completed(series):
        vals = series.fillna('').astype(str).str.strip().str.upper()
        return 'X' if (vals == 'X').all() else ''

    dc_agg = (df_po.groupby('Nomor PO')['Delivery Completed']
              .apply(_agg_delivery_completed)
              .reset_index()
              .rename(columns={'Delivery Completed': 'delivery_completed_agg'}))

    # --- Headers ---
    header_rows = []
    for _, row in tqdm(po_headers.iterrows(), total=len(po_headers), desc=" PO Headers", leave=False):
        nomor_po_str = clean_string(row['Nomor PO'])
        vc = clean_string(row['Vendor Code'])
        try: vc = str(int(float(vc))) if vc else None
        except: pass

        # Ambil delivery_completed dari aggregasi yang benar
        dc_match = dc_agg[dc_agg['Nomor PO'] == row['Nomor PO']]['delivery_completed_agg'].values
        delivery_completed_val = dc_match[0] if len(dc_match) > 0 else clean_string(row['Delivery Completed'])

        header_rows.append({
            'nomor_po':           nomor_po_str,
            'date_ordered':       clean_date(row['Date Ordered']),
            'vendor_code':        vc,
            'incoterm':           clean_string(row['Incoterm']),
            'del_date_po':        clean_date(row['Del Date PO']),
            'po_status':          clean_string(row['PO Status']),
            'po_deletion_flag':   clean_string(row['PO Deletion Flag']),
            'delivery_completed': delivery_completed_val,
            'purchasing_group':   clean_string(row['Purchasing Group']),
            'plant_code':         clean_string(row['Plant']),
            'bulan_po':           clean_numeric(row.get('BULAN PO')),
            'created_by':         clean_string(row.get('Created By')),
            'buyer':              clean_string(row.get('BUYER')),
            'our_reference':      clean_string(row.get('Our Reference')),
            'your_reference':     clean_string(row.get('Your Reference')),
            'bagian_po':          classify_bagian_by_creator(row.get('Created By'))
        })

    hi, hu = upsert(engine, 'purchase_orders', header_rows, ['nomor_po'],
                    ['date_ordered','vendor_code','incoterm','del_date_po','po_status',
                     'po_deletion_flag','delivery_completed','purchasing_group','plant_code',
                     'bulan_po','created_by','buyer','our_reference','your_reference','bagian_po'])

    # --- Items ---
    with engine.connect() as conn:
        po_id_map       = pd.read_sql("SELECT po_id, nomor_po FROM purchase_orders", conn)
        pr_items_map    = pd.read_sql("SELECT pr_item_id, no_pr, line_item_pr FROM pr_items", conn)
        valid_contracts = set(pd.read_sql("SELECT contract_no FROM contracts", conn)['contract_no'].tolist())

    po_headers_lookup = {}
    for _, row in po_headers.iterrows():
        po_headers_lookup[clean_string(row['Nomor PO'])] = {
            'purchasing_group': clean_string(row.get('Purchasing Group', '')),
            'department': clean_string(row.get('Departement(Requisitioner)', '')),
            'created_by': row.get('Created By')
        }

    item_rows = []
    for _, row in tqdm(df_po.iterrows(), total=len(df_po), desc=" PO Items", leave=False):
        nomor_po = clean_string(row['Nomor PO'])
        po_id    = po_id_map[po_id_map['nomor_po'] == nomor_po]['po_id'].values
        if len(po_id) == 0: continue

        no_pr, lpr = clean_string(row['No PR']), clean_numeric(row['Line/Item PR'])
        pr_item_id = None
        if no_pr and lpr:
            pi = pr_items_map[(pr_items_map['no_pr'] == no_pr) & (pr_items_map['line_item_pr'] == lpr)]
            if not pi.empty: pr_item_id = int(pi['pr_item_id'].values[0])

        material_no = clean_numeric(row['Material No'])
        contract_no = clean_string(row['No Contract'])
        if contract_no and contract_no not in valid_contracts: contract_no = None

        cls = row.copy()
        created_by_val = row.get('Created By')
        if nomor_po in po_headers_lookup:
            hd = po_headers_lookup[nomor_po]
            if pd.isna(row.get('Purchasing Group')) or row.get('Purchasing Group') == '':
                cls['Purchasing Group'] = hd['purchasing_group']
            if pd.isna(row.get('Departement(Requisitioner)')) or row.get('Departement(Requisitioner)') == '':
                cls['Departement(Requisitioner)'] = hd['department']
            if pd.isna(created_by_val) or str(created_by_val).strip() == '' or str(created_by_val).lower() == 'nan':
                created_by_val = hd['created_by']

        item_rows.append({
            'po_id':                      int(po_id[0]),
            'nomor_po':                   nomor_po,
            'item_po':                    int(clean_numeric(row['Item PO'])),
            'bagian_po':                  classify_bagian_by_creator(created_by_val),
            'pr_item_id':                 pr_item_id,
            'no_pr':                      no_pr,
            'line_item_pr':               lpr,
            'department_code':            clean_string(cls.get('Departement(Requisitioner)')),
            'material_no':                str(int(material_no)) if material_no else None,
            'description':                clean_string(row['Description']),
            'qty_po':                     clean_numeric(row['Qty PO']),
            'satuan_po':                  clean_string(row['Satuan PO']),
            'estimasi_pr':                clean_numeric(row.get('Estimasi PR')),
            'quantity_pr':                clean_numeric(row.get('Quantity PR')),
            'total_item_po_net_price':    clean_numeric(row['Total Item PO/Net Price']),
            'total_amount':               clean_numeric(row['Total Amount']),
            'total_amount_local_curr':    clean_numeric(row['Total Amount in Local Curr']),
            'currency_po':                clean_string(row['Currency PO']),
            'cost_center':                clean_string(row['Cost Center']),
            'gl_account':                 clean_string(row['GL Account']),
            'account_assignment':         clean_string(row['Account Assignment']),
            'item_category':              clean_string(row['Item Category']),
            'contract_no':                contract_no,
            'contract_item':              clean_string(row['No Item Contract']),
            'no_rfq':                     clean_string(row.get('No RFQ')),
            'rfq_item':                   clean_numeric(row.get('RFQ Item')),
            'del_date_po':                clean_date(row['Del Date PO']),
            'nomor_dur':                  clean_string(row['Nomor DUR']),
            'metode_pelelangan':          clean_string(row['Metode Pelelangan']),
            'auction_date':               clean_date(row['Auction Date']),
            'tgl_penutupan_penawaran':    clean_date(row['Tgl Penutupan Penawaran']),
            'tgl_pembukaan_penawaran':    clean_date(row['Tgl Pembukaan Penawaran']),
            'oe':                         clean_numeric(row.get('OE')),
            'efisiensi':                  clean_numeric(row.get('EFISIENSI')),
            'efisiensi_persen':           clean_numeric(row.get('EFISIENSI%')),
            'pr_po_days':                 int((clean_date(row['Date Ordered']) - clean_date(row.get('1St Full Release'))).days)
                                          if clean_date(row.get('Date Ordered')) and clean_date(row.get('1St Full Release'))
                                          else None,
            'first_full_release':         clean_date(row.get('1St Full Release')),
            'status_pengiriman':          'SELESAI' if str(row.get('Delivery Completed', '')).strip().upper() == 'X' else 'IN PROGRESS',
            'on_time_delivery':           calculate_ontime_delivery(row),
            'turn_around':                clean_string(row.get('Turn Around')),
            'invest':                     clean_string(row.get('invest?')),
            'pupuk_organik':              clean_boolean(row.get('PUPUK PGNK')),
            'batal':                      clean_boolean(row.get('L (batal)')),
            'kontrak':                    clean_string(row.get('KONTRAK?'))
        })

    update_cols_po_item = [
        'po_id','bagian_po','pr_item_id','no_pr','line_item_pr','department_code','material_no','description',
        'qty_po','satuan_po','estimasi_pr','quantity_pr','total_item_po_net_price','total_amount','total_amount_local_curr',
        'currency_po','cost_center','gl_account','account_assignment','item_category',
        'contract_no','contract_item','no_rfq','rfq_item','del_date_po','nomor_dur','metode_pelelangan',
        'auction_date','tgl_penutupan_penawaran','tgl_pembukaan_penawaran',
        'oe','efisiensi','efisiensi_persen',
        'pr_po_days','status_pengiriman','on_time_delivery','turn_around','invest',
        'pupuk_organik','batal','kontrak','first_full_release'
    ]
    ii, iu = upsert(engine, 'po_items', item_rows, ['nomor_po','item_po'], update_cols_po_item)

    # --- PO Release History & Goods Receipt ---
    # PENTING: po_items_map di-load SETELAH upsert po_items selesai agar
    # item baru (dari data bulan Maret) sudah terdaftar di DB dan terpetakan
    # dengan benar ke po_item_id yang sesungguhnya.
    po_nos_in_file = list(set(r['nomor_po'] for r in item_rows))
    po_nos_set     = set(po_nos_in_file)

    with engine.connect() as conn:
        po_items_map = pd.read_sql("SELECT po_item_id, nomor_po, item_po FROM po_items", conn)
    po_items_map = po_items_map[po_items_map['nomor_po'].isin(po_nos_set)]

    # DELETE berdasarkan JOIN ke nomor PO (bukan list po_item_id dari snapshot lama),
    # sehingga semua GR dan release history untuk PO yang ada di file ini
    # (termasuk yang sudah di-DB dari bulan sebelumnya) ikut di-refresh.
    if po_nos_in_file:
        po_nos_sql = "', '".join(po_nos_in_file)
        with engine.begin() as conn:
            conn.execute(text(f"""
                DELETE FROM po_release_history
                WHERE po_item_id IN (
                    SELECT po_item_id FROM po_items WHERE nomor_po IN ('{po_nos_sql}')
                )
            """))
            conn.execute(text(f"""
                DELETE FROM goods_receipt
                WHERE po_item_id IN (
                    SELECT po_item_id FROM po_items WHERE nomor_po IN ('{po_nos_sql}')
                )
            """))

    # --- PO Release History: INSERT ulang dari file Excel terbaru ---
    release_rows = []
    df_po_release = df_po[df_po['Nomor PO'].astype(str).isin(po_nos_in_file)]
    for _, row in tqdm(df_po_release.iterrows(), total=len(df_po_release), desc=" PO Release History", leave=False):
        nomor_po, item_po = clean_string(row['Nomor PO']), clean_numeric(row['Item PO'])
        pi = po_items_map[(po_items_map['nomor_po'] == nomor_po) & (po_items_map['item_po'] == item_po)]
        if pi.empty: continue
        pid = int(pi['po_item_id'].values[0])
        for i in range(1, 7):
            col = f'PO RL{i}'
            if col in row.index and pd.notna(row[col]):
                release_rows.append({'po_item_id': pid, 'release_level': col, 'release_date': clean_date(row[col])})

    if release_rows:
        for i in range(0, len(release_rows), 1000):
            with engine.begin() as conn:
                pd.DataFrame(release_rows[i:i+1000]).to_sql('po_release_history', conn, if_exists='append', index=False)

    # --- Goods Receipt: INSERT ulang dari file Excel terbaru ---
    gr_rows = []
    df_gr = df_po[df_po['Nomor PO'].astype(str).isin(po_nos_in_file)]
    for _, row in tqdm(df_gr.iterrows(), total=len(df_gr), desc=" Goods Receipt", leave=False):
        nomor_po, item_po = clean_string(row['Nomor PO']), clean_numeric(row['Item PO'])
        pi = po_items_map[(po_items_map['nomor_po'] == nomor_po) & (po_items_map['item_po'] == item_po)]
        if pi.empty: continue
        gr_rows.append({
            'po_item_id':           int(pi['po_item_id'].values[0]),
            'tgl_qc_103':           clean_date(row['Tgl QC(103)']),
            'tanggal_gr_103':       clean_date(row['Tanggal GR103']),
            'tgl_terima_barang':    clean_date(row['Tgl Terima Barang']),
            'service_acceptance':   clean_date(row['Service Acceptance']),
            'lead_time_process_po': (
                int((clean_date(row['Date Ordered']) - clean_date(row.get('1St Full Release'))).days)
                if clean_date(row.get('Date Ordered')) and clean_date(row.get('1St Full Release'))
                else None
            ),
            'lead_time_delivery':   clean_string(row['Lead Time Delivery']),
            'status_supply':        clean_string(row['Status Supply'])
        })

    if gr_rows:
        for i in range(0, len(gr_rows), 1000):
            with engine.begin() as conn:
                pd.DataFrame(gr_rows[i:i+1000]).to_sql('goods_receipt', conn, if_exists='append', index=False)

    return hi, hu, ii, iu


# =====================================================
# MAIN
# =====================================================

def run_etl():
    print("=" * 55)
    print("🚀 PR-PO MONITORING — ETL SAP (Lokal)")
    print(f"   PR : {Config.PR_FILE}")
    print(f"   PO : {Config.PO_FILE}")
    print("=" * 55)

    df_pr, df_po = load_excel_files()
    if df_pr is None or df_po is None:
        print("❌ ETL dibatalkan — gagal membaca file Excel")
        return

    try:
        engine = get_db_engine()
        with engine.connect() as conn: conn.execute(text("SELECT 1"))
        print("✅ Koneksi database OK\n")
    except Exception as e:
        print(f"❌ Koneksi database gagal: {e}"); return

    try:
        print("📦 Sinkronisasi Master Data:")
        mstats = sync_master_data(df_pr, df_po, engine)
        for name, (i, u) in mstats.items():
            print(f"   {name:<12}: +{i} baru, ~{u} update")

        print("\n📋 Sinkronisasi Purchase Requisitions:")
        hi, hu, ii, iu = sync_purchase_requisitions(df_pr, engine)
        print(f"   Headers : +{hi} baru, ~{hu} update")
        print(f"   Items   : +{ii} baru, ~{iu} update")

        print("\n🛒 Sinkronisasi Purchase Orders:")
        hi, hu, ii, iu = sync_purchase_orders(df_po, engine)
        print(f"   Headers : +{hi} baru, ~{hu} update")
        print(f"   Items   : +{ii} baru, ~{iu} update")

        print("\n" + "=" * 55)
        print("✅ ETL SELESAI")
        with engine.connect() as conn:
            pr_total  = conn.execute(text("SELECT COUNT(*) FROM purchase_requisitions")).scalar()
            po_total  = conn.execute(text("SELECT COUNT(*) FROM purchase_orders")).scalar()
            item_total= conn.execute(text("SELECT COUNT(*) FROM po_items")).scalar()
        print(f"   Total PR di DB : {pr_total:,}")
        print(f"   Total PO di DB : {po_total:,}")
        print(f"   Total PO Items : {item_total:,}")
        print("=" * 55)

    except Exception as e:
        print(f"\n❌ Error saat ETL: {e}")
        import traceback; traceback.print_exc()


if __name__ == "__main__":
    run_etl()