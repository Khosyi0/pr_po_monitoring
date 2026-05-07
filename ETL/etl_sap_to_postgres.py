"""
etl_sap_to_postgres.py - ETL: Sync PR & PO dari Excel ke PostgreSQL (Lokal)
(Versi Super Bulk Upsert - Cloud Optimized Tanpa Deadlock)
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import warnings
import time
warnings.filterwarnings('ignore')

class Config:
    DB_HOST     = 'localhost'
    DB_PORT     = '5432'
    DB_NAME     = 'pr_po_monitoring'
    DB_USER     = 'postgres'
    DB_PASSWORD = 'Hx4Khos2'

    PR_FILE = 'PR SAP - 2026 - Mar.xlsx'
    PO_FILE = 'PO SAP - 2026 - Mar.xlsx'

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
        try: return pd.to_datetime(int(float(value)), unit='D', origin='1899-12-30')
        except: pass
            
    try: return pd.to_datetime(value, dayfirst=True)
    except: return None

def clean_boolean(value):
    if pd.isna(value): return False
    if isinstance(value, bool): return value
    return str(value).upper() in ['TRUE', 'YES', 'X', '1']

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

def classify_bagian_by_creator(created_by_raw):
    if pd.isna(created_by_raw) or str(created_by_raw).lower() == 'nan': return 'UNKNOWN'
    cb = str(created_by_raw).strip().upper()
    if cb.endswith('.0'): cb = cb[:-2]
        
    alpata_users = {'2135855', '2145923', '2146001', '2166521', '2190478', 'B3410000ST04', 'B3410000ST05', 'B3410000ST06', 'B3410000ST08', 'B3410000ST13', 'SYS_EPROC'}
    barum_users = {'2095185', '2156378', '2180261', '2115464', 'B3410000ST07', 'B3410000ST09', 'B3410000ST10', 'B3410000ST11'}
    bb_users = {'2156257', 'B3410000ST01', 'B3410000ST02', '2190583'}

    if cb in alpata_users: return 'ALPATA'
    elif cb in barum_users: return 'BARUM'
    elif cb in bb_users: return 'BB/BD/BP'
    return 'UNKNOWN'

def calculate_ontime_delivery(row):
    try: mat_no = str(int(float(row.get('Material No', ''))))
    except: mat_no = str(row.get('Material No', '')).strip()

    if mat_no == '1000076' or str(row.get('PO Deletion Flag', '')).strip().upper() == 'L': return None
    if str(row.get('Delivery Completed', '')).strip().upper() != 'X': return 'IN PROGRESS'

    tgl_terima = clean_date(row.get('Tgl Terima Barang'))
    tgl_janji  = clean_date(row.get('Del Date PO'))
    if pd.isna(tgl_terima) or pd.isna(tgl_janji): return None
    return 'TEPAT WAKTU' if tgl_terima <= tgl_janji else 'TERLAMBAT'

# =====================================================
# EXTRACT
# =====================================================
def load_excel_files():
    print("📂 Membaca file Excel...")
    try:
        df_pr = pd.read_excel(Config.PR_FILE)
        col_flag = df_pr['PR Deletion Flag'].fillna('').astype(str).str.strip().str.upper() if 'PR Deletion Flag' in df_pr.columns else pd.Series([''] * len(df_pr))
        col_acc  = df_pr['Account Assignment'].fillna('').astype(str).str.strip().str.upper() if 'Account Assignment' in df_pr.columns else pd.Series([''] * len(df_pr))
        pr_mat   = 'Material No' if 'Material No' in df_pr.columns else 'Material'
        col_mat  = df_pr[pr_mat].astype(str).str.replace('.0', '', regex=False).str.strip() if pr_mat in df_pr.columns else pd.Series([''] * len(df_pr))
        df_pr = df_pr[~(col_flag == 'X') & ~col_acc.str.startswith('U') & ~col_mat.str.contains('1000076', na=False)].dropna(subset=['No PR'])
        print(f"   PR  : {len(df_pr):,} baris bersih")
    except Exception as e:
        print(f"❌ Gagal membaca PR: {e}"); return None, None

    try:
        df_po = pd.read_excel(Config.PO_FILE)
        po_mat   = 'Material No' if 'Material No' in df_po.columns else 'Material'
        col_mp   = df_po[po_mat].astype(str).str.replace('.0', '', regex=False).str.strip() if po_mat in df_po.columns else pd.Series([''] * len(df_po))
        tdc      = next((c for c in ['PO Deletion Flag', 'Deletion Indicator', 'D', 'L'] if c in df_po.columns), None)
        col_del  = df_po[tdc].fillna('').astype(str).str.strip().str.upper() if tdc else pd.Series([''] * len(df_po))
        df_po = df_po[~col_mp.str.contains('1000076', na=False) & ~(col_del == 'L')].dropna(subset=['Nomor PO'])
        print(f"   PO  : {len(df_po):,} baris bersih")
    except Exception as e:
        print(f"❌ Gagal membaca PO: {e}"); return df_pr, None

    return df_pr, df_po

# =====================================================
# SUPER BULK UPSERT (Tanpa Deadlock & Auto-Type Cast)
# =====================================================
def bulk_upsert(engine, table, df, conflict_cols, update_cols):
    if df.empty: return
    
    # 1. Pastikan NaN/NaT menjadi standar None agar masuk ke DB sebagai NULL murni
    df = df.astype(object).where(pd.notnull(df), None)
    
    # Generate unique temp table name
    temp_table = f"temp_{table}_upsert_{int(time.time()*1000)}"

    all_cols = list(df.columns)
    col_names = ', '.join(all_cols)
    set_clause = ', '.join(f"{c} = EXCLUDED.{c}" for c in update_cols)
    conflict   = ', '.join(conflict_cols)
    
    with engine.begin() as conn:
        # 2. Tuang ke temp table menggunakan Pandas
        df.to_sql(temp_table, conn, if_exists='replace', index=False)
        
        # 3. Intip struktur tipe data dari tabel target secara dinamis!
        type_query = text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = :t")
        target_types = {row[0]: row[1] for row in conn.execute(type_query, {'t': table}).fetchall()}
        
        # 4. Bangun perintah SELECT dengan AUTO CASTING agar tipe data cocok 100%
        select_items = []
        for col in all_cols:
            t_type = target_types.get(col, 'text') # default text jika gagal
            select_items.append(f"CAST(\"{col}\" AS {t_type})")
            
        select_clause = ', '.join(select_items)
        
        # 5. Eksekusi Upsert
        upsert_sql = f"""
            INSERT INTO {table} ({col_names})
            SELECT {select_clause} FROM {temp_table}
            ON CONFLICT ({conflict}) DO UPDATE SET {set_clause};
        """
        conn.execute(text(upsert_sql))
        conn.execute(text(f"DROP TABLE {temp_table};"))

# =====================================================
# SYNC MASTER DATA
# =====================================================
def sync_master_data(df_pr, df_po, engine):
    print("📦 Sinkronisasi Master Data...")
    
    # Plants
    plants = set(df_pr['Plant'].dropna().astype(str).unique()) | set(df_po['Plant'].dropna().astype(str).unique())
    df_plants = pd.DataFrame([{'plant_code': p.strip(), 'plant_name': f'Plant {p.strip()}'} for p in plants if p.strip()])
    bulk_upsert(engine, 'plants', df_plants, ['plant_code'], ['plant_name'])

    # Departments
    df_dept_pr = df_pr[['Departement(Requisitioner)', 'Tracking No', 'Purchasing Group', 'Material No']].dropna(subset=['Departement(Requisitioner)'])
    df_dept_po = df_po[['Departement(Requisitioner)', 'Tracking No', 'Purchasing Group', 'Material No']].dropna(subset=['Departement(Requisitioner)'])
    df_dept_all = pd.concat([df_dept_pr, df_dept_po])
    dept_records = [{'department_code': clean_string(r['Departement(Requisitioner)']), 'department_name': clean_string(r['Departement(Requisitioner)']), 'bagian': classify_bagian(r)} for r in df_dept_all.to_dict('records')]
    df_departments = pd.DataFrame(dept_records).drop_duplicates(subset=['department_code']).dropna(subset=['department_code'])
    bulk_upsert(engine, 'departments', df_departments, ['department_code'], ['department_name', 'bagian'])

    # Vendors
    df_po_v = df_po[['Vendor Code','Vendor Name','Vendor Account Group','City','Salesperson']].dropna(subset=['Vendor Code'])
    df_pr_v = df_pr[['Vendor Code','Vendor Name','Vendor Account Group','City']].dropna(subset=['Vendor Code'])
    df_po_v['salesperson'] = df_po_v['Salesperson'].apply(clean_string)
    df_pr_v['salesperson'] = None
    df_vendor_all = pd.concat([df_po_v, df_pr_v])
    df_vendor_all['vendor_code'] = df_vendor_all['Vendor Code'].apply(lambda x: str(int(float(x))) if pd.notna(x) else None)
    df_vendor_all['vendor_name'] = df_vendor_all['Vendor Name'].apply(clean_string)
    df_vendor_all['vendor_account_group'] = df_vendor_all['Vendor Account Group'].apply(clean_string)
    df_vendor_all['city'] = df_vendor_all['City'].apply(clean_string)
    df_vendors = df_vendor_all[['vendor_code', 'vendor_name', 'vendor_account_group', 'city', 'salesperson']].drop_duplicates(subset=['vendor_code']).dropna(subset=['vendor_code'])
    bulk_upsert(engine, 'vendors', df_vendors, ['vendor_code'], ['vendor_name', 'vendor_account_group', 'city', 'salesperson'])

    # Materials
    df_mat_pr = df_pr[['Material No','Description','Material Group','ABC Indicator', 'Satuan PR']].rename(columns={'Satuan PR': 'base_unit'})
    df_mat_po = df_po[['Material No','Description','Material Group','ABC Indicator', 'Satuan PO']].rename(columns={'Satuan PO': 'base_unit'})
    df_mat_all = pd.concat([df_mat_pr, df_mat_po]).dropna(subset=['Material No'])
    df_mat_all['material_no'] = df_mat_all['Material No'].apply(lambda x: str(int(float(x))) if pd.notna(x) else None)
    df_mat_all['description'] = df_mat_all['Description'].apply(clean_string)
    df_mat_all['material_group'] = df_mat_all['Material Group'].apply(clean_string)
    df_mat_all['abc_indicator'] = df_mat_all['ABC Indicator'].apply(clean_string)
    df_mat_all['base_unit'] = df_mat_all['base_unit'].apply(clean_string)
    df_materials = df_mat_all[['material_no', 'description', 'material_group', 'abc_indicator', 'base_unit']].drop_duplicates(subset=['material_no']).dropna(subset=['material_no'])
    bulk_upsert(engine, 'materials', df_materials, ['material_no'], ['description', 'material_group', 'abc_indicator', 'base_unit'])

    # Contracts
    df_c_pr = df_pr[['No Contract','No Item Contract','Vendor Code']]
    df_c_po = df_po[['No Contract','No Item Contract','Vendor Code']]
    df_c_all = pd.concat([df_c_pr, df_c_po]).dropna(subset=['No Contract'])
    df_c_all['contract_no'] = df_c_all['No Contract'].apply(clean_string)
    df_c_all['contract_item'] = df_c_all['No Item Contract'].apply(clean_string)
    df_c_all['vendor_code'] = df_c_all['Vendor Code'].apply(lambda x: str(int(float(x))) if pd.notna(x) else None)
    df_contracts = df_c_all[['contract_no', 'contract_item', 'vendor_code']].drop_duplicates(subset=['contract_no']).dropna(subset=['contract_no'])
    df_contracts = df_contracts[df_contracts['contract_no'].str.lower() != 'nan']
    bulk_upsert(engine, 'contracts', df_contracts, ['contract_no'], ['contract_item', 'vendor_code'])

# =====================================================
# TRANSAKSI UPSERT
# =====================================================
def sync_purchase_requisitions(df_pr, engine):
    print("📋 Sinkronisasi Purchase Requisitions...")
    
    # Headers
    pr_headers = df_pr.groupby('No PR').first().reset_index()
    header_rows = [{
        'no_pr': clean_string(r['No PR']), 'tgl_create_pr': clean_date(r['Tgl Create PR']),
        'department_code': clean_string(r['Departement(Requisitioner)']), 'plant_code': clean_string(r['Plant']),
        'mrp_controller': clean_string(r['MRP Controller']), 'purchasing_group': clean_string(r['Purchasing Group']),
        'bulan_pr': clean_numeric(r.get('BULAN PR')), 'pr_deletion_flag': clean_string(r['PR Deletion Flag']),
        'pr_closed': clean_string(r['PR Closed']), 'bagian_pr': clean_string(r.get('BAGIAN', r.get('Bagian')))
    } for r in pr_headers.to_dict('records')]
    
    df_headers = pd.DataFrame(header_rows).dropna(subset=['no_pr'])
    bulk_upsert(engine, 'purchase_requisitions', df_headers, ['no_pr'], ['tgl_create_pr','department_code','plant_code','mrp_controller','purchasing_group','bulan_pr','pr_deletion_flag','pr_closed','bagian_pr'])

    # Ambil pemetaan pr_id dari DB
    with engine.connect() as conn:
        pr_id_map = pd.read_sql("SELECT pr_id, no_pr FROM purchase_requisitions", conn).set_index('no_pr')['pr_id'].to_dict()
        valid_contracts = set(pd.read_sql("SELECT contract_no FROM contracts", conn)['contract_no'].tolist())

    # Items
    df_pr_items = df_pr.drop_duplicates(subset=['No PR','Line/Item PR'])
    item_rows = []
    for r in df_pr_items.to_dict('records'):
        no_pr = clean_string(r['No PR'])
        if no_pr not in pr_id_map: continue
        mat_no = clean_numeric(r['Material No'])
        cno = clean_string(r['No Contract'])
        cno = cno if cno in valid_contracts else None
        item_rows.append({
            'pr_id': pr_id_map[no_pr], 'no_pr': no_pr, 'tgl_create_pr': clean_date(r['Tgl Create PR']),
            'line_item_pr': int(clean_numeric(r['Line/Item PR'])), 'bagian_pr': classify_bagian(r),
            'department_code': clean_string(r.get('Departement(Requisitioner)')), 'plant_code': clean_string(r.get('Plant')),
            'material_no': str(int(mat_no)) if mat_no else None, 'description': clean_string(r['Description']),
            'quantity_pr': clean_numeric(r['Quantity PR']), 'satuan_pr': clean_string(r['Satuan PR']),
            'estimasi_pr': clean_numeric(r['Estimasi PR']), 'currency_pr': clean_string(r['Currency PR']),
            'pr_release_status': clean_string(r['PR Release Status']), 'tracking_no': clean_string(r['Tracking No']),
            'cost_center': clean_string(r['Cost Center']), 'gl_account': clean_string(r['GL Account']),
            'account_assignment': clean_string(r['Account Assignment']), 'contract_no': cno,
            'contract_item': clean_string(r['No Item Contract']), 'e_proc': clean_string(r['E-Proc']),
            'metode_pelelangan': clean_string(r['Metode Pelelangan']), 'inv_normal': clean_string(r.get('INV/NORMAL')),
            'turn_around': clean_string(r.get('turn around')), 'pr_u': clean_boolean(r.get('PR U')),
            'kontrak': clean_string(r.get('KONTRAK')), 'pupuk_organik': clean_string(r.get('Pupuk Organik')),
            'batal': clean_boolean(r.get('BATAL')), 'source_determination_via': clean_string(r['Source Determination Via']),
            'status_source_determination': clean_string(r['Status Source Determination']), 'first_full_release': clean_date(r.get('1St Full Release'))
        })

    df_items = pd.DataFrame(item_rows)
    update_cols_pr = ['pr_id','tgl_create_pr','bagian_pr','department_code','plant_code','material_no','description','quantity_pr','satuan_pr','estimasi_pr','currency_pr','pr_release_status','tracking_no','cost_center','gl_account','account_assignment','contract_no','contract_item','e_proc','metode_pelelangan','inv_normal','turn_around','pr_u','kontrak','pupuk_organik','batal','source_determination_via','status_source_determination','first_full_release']
    bulk_upsert(engine, 'pr_items', df_items, ['no_pr','line_item_pr'], update_cols_pr)

    # --- Release History ---
    with engine.connect() as conn:
        pr_item_map = pd.read_sql("SELECT pr_item_id, no_pr, line_item_pr FROM pr_items", conn)
        
    # SAMAKAN TIPE DATA SEBELUM MERGE
    df_pr['No PR'] = df_pr['No PR'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    df_pr['Line/Item PR'] = pd.to_numeric(df_pr['Line/Item PR'], errors='coerce').fillna(0).astype(int)
    
    pr_item_map['no_pr'] = pr_item_map['no_pr'].astype(str)
    pr_item_map['line_item_pr'] = pr_item_map['line_item_pr'].astype(int)

    df_merged = df_pr.merge(pr_item_map, left_on=['No PR', 'Line/Item PR'], right_on=['no_pr', 'line_item_pr'], how='inner')
    
    release_rows = []
    for r in df_merged.to_dict('records'):
        for i in range(1, 5):
            col = f'PR RL{i}'
            if col in r and pd.notna(r[col]):
                release_rows.append({'pr_item_id': r['pr_item_id'], 'release_level': col, 'release_date': clean_date(r[col])})
                
    df_release = pd.DataFrame(release_rows).dropna(subset=['release_date'])
    
    # Hapus release history yang lama & Replace dengan bulk insert append
    if not df_release.empty:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM pr_release_history WHERE pr_item_id IN (SELECT pr_item_id FROM pr_items WHERE no_pr IN :n)"), {'n': tuple(df_headers['no_pr'].tolist())})
            df_release.to_sql('pr_release_history', conn, if_exists='append', index=False)


def sync_purchase_orders(df_po, engine):
    print("🛒 Sinkronisasi Purchase Orders...")
    
    # Agg delivery completed
    def _agg_delivery_completed(series):
        vals = series.fillna('').astype(str).str.strip().str.upper()
        return 'X' if (vals == 'X').all() else ''
    dc_agg = df_po.groupby('Nomor PO')['Delivery Completed'].apply(_agg_delivery_completed).to_dict()

    # Headers
    po_headers = df_po.groupby('Nomor PO').first().reset_index()
    header_rows = []
    po_hd_lookup = {}
    for r in po_headers.to_dict('records'):
        nomor_po = clean_string(r['Nomor PO'])
        try: vc = str(int(float(clean_string(r['Vendor Code']))))
        except: vc = None
        cb_val = clean_string(r.get('Created By'))
        
        po_hd_lookup[nomor_po] = {'pg': clean_string(r.get('Purchasing Group', '')), 'dept': clean_string(r.get('Departement(Requisitioner)', '')), 'cb': cb_val}
        header_rows.append({
            'nomor_po': nomor_po, 'date_ordered': clean_date(r['Date Ordered']), 'vendor_code': vc,
            'incoterm': clean_string(r['Incoterm']), 'del_date_po': clean_date(r['Del Date PO']),
            'po_status': clean_string(r['PO Status']), 'po_deletion_flag': clean_string(r['PO Deletion Flag']),
            'delivery_completed': dc_agg.get(nomor_po, ''), 'purchasing_group': clean_string(r['Purchasing Group']),
            'plant_code': clean_string(r['Plant']), 'bulan_po': clean_numeric(r.get('BULAN PO')),
            'created_by': cb_val, 'buyer': clean_string(r.get('BUYER')),
            'our_reference': clean_string(r.get('Our Reference')), 'your_reference': clean_string(r.get('Your Reference')),
            'bagian_po': classify_bagian_by_creator(cb_val)
        })

    df_headers = pd.DataFrame(header_rows).dropna(subset=['nomor_po'])
    bulk_upsert(engine, 'purchase_orders', df_headers, ['nomor_po'], ['date_ordered','vendor_code','incoterm','del_date_po','po_status','po_deletion_flag','delivery_completed','purchasing_group','plant_code','bulan_po','created_by','buyer','our_reference','your_reference','bagian_po'])

    # Ambil pemetaan id dari DB
    with engine.connect() as conn:
        po_id_map = pd.read_sql("SELECT po_id, nomor_po FROM purchase_orders", conn).set_index('nomor_po')['po_id'].to_dict()
        pr_items_map = pd.read_sql("SELECT pr_item_id, no_pr, line_item_pr FROM pr_items", conn)
        valid_contracts = set(pd.read_sql("SELECT contract_no FROM contracts", conn)['contract_no'].tolist())
        
    # Helper dict untuk mapping pr_item_id kilat
    pr_lookup = pr_items_map.set_index(['no_pr', 'line_item_pr'])['pr_item_id'].to_dict()

    # Items
    item_rows = []
    for r in df_po.to_dict('records'):
        nomor_po = clean_string(r['Nomor PO'])
        if nomor_po not in po_id_map: continue
            
        no_pr, lpr = clean_string(r['No PR']), clean_numeric(r['Line/Item PR'])
        pr_item_id = pr_lookup.get((no_pr, lpr), None) if no_pr and lpr else None
        mat_no = clean_numeric(r['Material No'])
        cno = clean_string(r['No Contract'])
        cno = cno if cno in valid_contracts else None

        hd = po_hd_lookup.get(nomor_po, {})
        cb_val = r.get('Created By') if pd.notna(r.get('Created By')) else hd.get('cb')

        d_ord = clean_date(r.get('Date Ordered'))
        f_rel = clean_date(r.get('1St Full Release'))
        pr_po_days = int((d_ord - f_rel).days) if d_ord and f_rel else None

        item_rows.append({
            'po_id': po_id_map[nomor_po], 'nomor_po': nomor_po, 'item_po': int(clean_numeric(r['Item PO'])),
            'bagian_po': classify_bagian_by_creator(cb_val), 'pr_item_id': pr_item_id, 'no_pr': no_pr, 'line_item_pr': lpr,
            'department_code': clean_string(r.get('Departement(Requisitioner)')) or hd.get('dept'),
            'material_no': str(int(mat_no)) if mat_no else None, 'description': clean_string(r['Description']),
            'qty_po': clean_numeric(r['Qty PO']), 'satuan_po': clean_string(r['Satuan PO']),
            'estimasi_pr': clean_numeric(r.get('Estimasi PR')), 'quantity_pr': clean_numeric(r.get('Quantity PR')),
            'total_item_po_net_price': clean_numeric(r['Total Item PO/Net Price']), 'total_amount': clean_numeric(r['Total Amount']),
            'total_amount_local_curr': clean_numeric(r['Total Amount in Local Curr']), 'currency_po': clean_string(r['Currency PO']),
            'cost_center': clean_string(r['Cost Center']), 'gl_account': clean_string(r['GL Account']),
            'account_assignment': clean_string(r['Account Assignment']), 'item_category': clean_string(r['Item Category']),
            'contract_no': cno, 'contract_item': clean_string(r['No Item Contract']), 'no_rfq': clean_string(r.get('No RFQ')),
            'rfq_item': clean_numeric(r.get('RFQ Item')), 'del_date_po': clean_date(r['Del Date PO']),
            'nomor_dur': clean_string(r['Nomor DUR']), 'metode_pelelangan': clean_string(r['Metode Pelelangan']),
            'auction_date': clean_date(r['Auction Date']), 'tgl_penutupan_penawaran': clean_date(r['Tgl Penutupan Penawaran']),
            'tgl_pembukaan_penawaran': clean_date(r['Tgl Pembukaan Penawaran']), 'oe': clean_numeric(r.get('OE')),
            'efisiensi': clean_numeric(r.get('EFISIENSI')), 'efisiensi_persen': clean_numeric(r.get('EFISIENSI%')),
            'pr_po_days': pr_po_days, 'first_full_release': f_rel,
            'status_pengiriman': 'SELESAI' if str(r.get('Delivery Completed', '')).strip().upper() == 'X' else 'IN PROGRESS',
            'on_time_delivery': calculate_ontime_delivery(r), 'turn_around': clean_string(r.get('Turn Around')),
            'invest': clean_string(r.get('invest?')), 'pupuk_organik': clean_boolean(r.get('PUPUK PGNK')),
            'batal': clean_boolean(r.get('L (batal)')), 'kontrak': clean_string(r.get('KONTRAK?'))
        })

    df_items = pd.DataFrame(item_rows)
    update_cols_po = ['po_id','bagian_po','pr_item_id','no_pr','line_item_pr','department_code','material_no','description','qty_po','satuan_po','estimasi_pr','quantity_pr','total_item_po_net_price','total_amount','total_amount_local_curr','currency_po','cost_center','gl_account','account_assignment','item_category','contract_no','contract_item','no_rfq','rfq_item','del_date_po','nomor_dur','metode_pelelangan','auction_date','tgl_penutupan_penawaran','tgl_pembukaan_penawaran','oe','efisiensi','efisiensi_persen','pr_po_days','status_pengiriman','on_time_delivery','turn_around','invest','pupuk_organik','batal','kontrak','first_full_release']
    bulk_upsert(engine, 'po_items', df_items, ['nomor_po','item_po'], update_cols_po)

    # --- Release History & Goods Receipt ---
    with engine.connect() as conn:
        po_item_map = pd.read_sql("SELECT po_item_id, nomor_po, item_po FROM po_items", conn)
    
    # SAMAKAN TIPE DATA SEBELUM MERGE
    df_po['Nomor PO'] = df_po['Nomor PO'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    df_po['Item PO'] = pd.to_numeric(df_po['Item PO'], errors='coerce').fillna(0).astype(int)
    
    po_item_map['nomor_po'] = po_item_map['nomor_po'].astype(str)
    po_item_map['item_po'] = po_item_map['item_po'].astype(int)
    
    df_merged = df_po.merge(po_item_map, left_on=['Nomor PO', 'Item PO'], right_on=['nomor_po', 'item_po'], how='inner')
    
    release_rows, gr_rows = [], []
    for r in df_merged.to_dict('records'):
        pid = r['po_item_id']
        for i in range(1, 7):
            col = f'PO RL{i}'
            if col in r and pd.notna(r[col]):
                release_rows.append({'po_item_id': pid, 'release_level': col, 'release_date': clean_date(r[col])})
                
        d_ord, f_rel = clean_date(r.get('Date Ordered')), clean_date(r.get('1St Full Release'))
        gr_rows.append({
            'po_item_id': pid, 'tgl_qc_103': clean_date(r.get('Tgl QC(103)')),
            'tanggal_gr_103': clean_date(r.get('Tanggal GR103')), 'tgl_terima_barang': clean_date(r.get('Tgl Terima Barang')),
            'service_acceptance': clean_date(r.get('Service Acceptance')),
            'lead_time_process_po': int((d_ord - f_rel).days) if d_ord and f_rel else None,
            'lead_time_delivery': clean_string(r.get('Lead Time Delivery')), 'status_supply': clean_string(r.get('Status Supply'))
        })

    df_release = pd.DataFrame(release_rows).dropna(subset=['release_date'])
    df_gr = pd.DataFrame(gr_rows)

    # Wipe & Append untuk sub-table
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM po_release_history WHERE po_item_id IN (SELECT po_item_id FROM po_items WHERE nomor_po IN :n)"), {'n': tuple(df_headers['nomor_po'].tolist())})
        conn.execute(text("DELETE FROM goods_receipt WHERE po_item_id IN (SELECT po_item_id FROM po_items WHERE nomor_po IN :n)"), {'n': tuple(df_headers['nomor_po'].tolist())})
        
        if not df_release.empty: df_release.to_sql('po_release_history', conn, if_exists='append', index=False)
        if not df_gr.empty: df_gr.to_sql('goods_receipt', conn, if_exists='append', index=False)


# =====================================================
# MAIN
# =====================================================
def run_etl():
    print("=" * 55)
    print("🚀 PR-PO MONITORING — ETL SAP (Lokal)")
    print("=" * 55)

    df_pr, df_po = load_excel_files()
    if df_pr is None or df_po is None: return

    try:
        engine = get_db_engine()
        with engine.connect() as conn: conn.execute(text("SELECT 1"))
        print("✅ Koneksi database OK\n")
    except Exception as e: print(f"❌ Koneksi database gagal: {e}"); return

    try:
        sync_master_data(df_pr, df_po, engine)
        sync_purchase_requisitions(df_pr, engine)
        sync_purchase_orders(df_po, engine)

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
