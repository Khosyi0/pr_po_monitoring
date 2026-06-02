"""
etl_sips.py - ETL: Sync data Excel SIPS ke PostgreSQL (Lokal)

Cara pakai:
  1. Sesuaikan Config.PERIODE_IMPORT (bisa lebih dari 1 bulan)
  2. Jalankan: python etl_sips.py

Cara kerja (UPSERT):
  - Data baru   → INSERT
  - Data lama yang berubah → UPDATE otomatis
  - Aman dijalankan berkali-kali (idempotent)
  - Cocok untuk sync mingguan dari file Excel akumulatif

Catatan SIPS:
  - sips_data tidak punya UNIQUE constraint di DB, sehingga ETL ini
    menerapkan strategi DELETE + REINSERT per bulan/tahun setiap kali dijalankan.
    Ini memastikan data selalu sinkron dengan isi file Excel terbaru.

Catatan Bagian:
  - BAGIAN_MAP statis sudah dihapus.
  - Penentuan bagian karyawan sepenuhnya dikelola lewat tabel
    karyawan_bagian_history di database (diisi via UI v_profile_departemen).
  - ETL hanya bertanggung jawab sync data transaksi; view vw_sips
    yang melakukan lookup bagian berdasarkan tanggal transaksi.

Requirements:
  pip install pandas openpyxl sqlalchemy psycopg2-binary --break-system-packages
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import warnings
import os
warnings.filterwarnings('ignore')


# =====================================================================
# KONFIGURASI
# =====================================================================

class Config:
    DB_HOST     = 'localhost'
    DB_PORT     = '5432'
    DB_NAME     = 'pr_po_monitoring'
    DB_USER     = 'postgres'
    DB_PASSWORD = 'Hx4Khos2'

    SIPS_FILE   = 'SIPS.xlsx'
    SIPS_SHEET  = 'SIPS'

    # Isi sebagai list of tuple (bulan, tahun).
    # Contoh satu bulan  : PERIODE_IMPORT = [(1, 2026)]
    # Contoh dua bulan   : PERIODE_IMPORT = [(1, 2026), (2, 2026)]
    PERIODE_IMPORT = [(1, 2026), (2, 2026), (3, 2026)]


# =====================================================================
# DATABASE
# =====================================================================

def db_get_engine():
    cs = (f"postgresql://{Config.DB_USER}:{Config.DB_PASSWORD}"
          f"@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}")
    return create_engine(cs)


# =====================================================================
# HELPERS
# =====================================================================

def clean_str(v):
    if v is None or (isinstance(v, float) and np.isnan(v)): return None
    s = str(v).strip()
    return None if s.lower() in ('nan', 'none', '') else s

def clean_int(v):
    try:
        if pd.isna(v): return None
        return int(float(v))
    except: return None

def clean_float(v):
    if v is None: return None
    try:
        if pd.isna(v): return None
    except: pass

    if isinstance(v, (int, float)):
        return float(v)

    try:
        s = str(v).upper().replace('RP', '').replace(' ', '').replace('-', '').strip()
        if not s:
            return None
        if ',' in s:
            s = s.replace('.', '')
            s = s.replace(',', '.')
        else:
            s = s.replace('.', '')
        return float(s)
    except:
        return None

def clean_date(v):
    if v is None: return None
    try:
        if pd.isna(v): return None
    except: pass
    try: return pd.to_datetime(v, dayfirst=True).date()
    except: return None

def clean_persen(v):
    if v is None: return None
    try:
        if pd.isna(v): return None
    except: pass
    if isinstance(v, (int, float)):
        val = float(v)
        return val / 100.0 if val > 1.5 else val
    s = str(v).strip().replace('%', '').replace(',', '.').strip()
    try:
        val = float(s)
        return val / 100.0 if val > 1.5 else val
    except: return None

def clean_hari(v):
    if v is None: return None
    try:
        if pd.isna(v): return None
    except: pass
    if isinstance(v, (int, float)): return float(v)
    s = str(v).lower().replace('hari', '').replace(',', '.').strip()
    try: return float(s)
    except: return None


# =====================================================================
# EXTRACT
# =====================================================================

def load_sips_excel():
    if not os.path.exists(Config.SIPS_FILE):
        raise FileNotFoundError(f"File tidak ditemukan: '{Config.SIPS_FILE}'")

    df = pd.read_excel(Config.SIPS_FILE, sheet_name=Config.SIPS_SHEET, header=0)

    COL_MAP = {
        0: 'nik', 1: 'nama', 2: 'no_pr', 3: 'item_of', 4: 'status',
        5: 'material_number', 6: 'short_text', 7: 'purchasing_group',
        8: 'requisition_date', 9: 'release_date', 10: 'tgl_disposisi_buyer',
        11: 'tgl_po', 12: 'requisitioner', 13: 'pr_po_days', 14: 'no_po',
        15: 'prioritas', 16: 'outline_agreement', 17: 'kontrak_status',
        18: 'standar_sla', 19: 'realisasi_sla', 20: 'nilai_sla',
        21: 'nomor_mr_sr', 22: 'nilai_mr_sr', 23: 'oe_pr',
        24: 'nilai_item_po', 25: 'persen_po_sr_mr', 26: 'nilai_persen_po_sr_mr',
        27: 'bulan_dispo',
    }
    rename_map = {df.columns[i]: name for i, name in COL_MAP.items() if i < len(df.columns)}
    df = df.rename(columns=rename_map)
    print(f"   File    : {Config.SIPS_FILE}  ({len(df):,} baris raw)")
    return df


# =====================================================================
# TRANSFORM
# =====================================================================

def transform(df: pd.DataFrame):
    df = df.dropna(subset=['nik', 'nama'], how='all').copy()
    df = df[df['nama'].astype(str).str.strip().str.lower().isin(['nan', '']) == False].copy()

    records = []
    for _, row in df.iterrows():
        nama = clean_str(row.get('nama'))
        nik  = clean_str(row.get('nik'))
        if not nama: continue

        # Ekstrak bulan & tahun dari tanggal (prioritas: tgl_dispo → tgl_po → req_date)
        tgl_anchor = (
            clean_date(row.get('tgl_disposisi_buyer'))
            or clean_date(row.get('tgl_po'))
            or clean_date(row.get('requisition_date'))
        )

        if tgl_anchor:
            b_imp, t_imp = tgl_anchor.month, tgl_anchor.year
        else:
            b_imp, t_imp = 0, 0

        # Filter: hanya masukkan ke records jika periodenya terdaftar
        if Config.PERIODE_IMPORT and (b_imp, t_imp) not in Config.PERIODE_IMPORT:
            continue

        records.append({
            'nik':                   nik,
            'nama':                  nama,
            'no_pr':                 clean_str(row.get('no_pr')),
            'item_of':               clean_int(row.get('item_of')),
            'status':                clean_str(row.get('status')),
            'material_number':       clean_str(row.get('material_number')),
            'short_text':            clean_str(row.get('short_text')),
            'purchasing_group':      clean_str(row.get('purchasing_group')),
            'requisition_date':      clean_date(row.get('requisition_date')),
            'release_date':          clean_date(row.get('release_date')),
            'tgl_disposisi_buyer':   clean_date(row.get('tgl_disposisi_buyer')),
            'tgl_po':                clean_date(row.get('tgl_po')),
            'requisitioner':         clean_str(row.get('requisitioner')),
            'pr_po_days':            clean_hari(row.get('pr_po_days')),
            'no_po':                 clean_str(row.get('no_po')),
            'prioritas':             clean_str(row.get('prioritas')),
            'outline_agreement':     clean_str(row.get('outline_agreement')),
            'kontrak_status':        clean_str(row.get('kontrak_status')),
            'standar_sla':           clean_hari(row.get('standar_sla')),
            'realisasi_sla':         clean_hari(row.get('realisasi_sla')),
            'nilai_sla':             clean_float(row.get('nilai_sla')),
            'nomor_mr_sr':           clean_str(row.get('nomor_mr_sr')),
            'nilai_mr_sr':           clean_float(row.get('nilai_mr_sr')),
            'oe_pr':                 clean_float(row.get('oe_pr')),
            'nilai_item_po':         clean_float(row.get('nilai_item_po')),
            'persen_po_sr_mr':       clean_persen(row.get('persen_po_sr_mr')),
            'nilai_persen_po_sr_mr': clean_float(row.get('nilai_persen_po_sr_mr')),
            'bulan_dispo':           clean_str(row.get('bulan_dispo')),
            'bulan_import':          b_imp,
            'tahun_import':          t_imp,
        })

    if not records:
        print("   ⚠️ Peringatan: Tidak ada baris yang sesuai dengan PERIODE_IMPORT.")
        return pd.DataFrame()

    df_clean = pd.DataFrame(records)
    print(f"   Siap import : {len(df_clean):,} baris (terfilter sesuai PERIODE_IMPORT)")
    return df_clean


# =====================================================================
# LOAD
# =====================================================================

def sync_employees(df_clean: pd.DataFrame, engine):
    """
    Sync tabel sips_employees (hanya nik + nama).
    Kolom 'bagian' di sips_employees masih ada sebagai fallback,
    tapi TIDAK diupdate oleh ETL — dikelola lewat UI (karyawan_bagian_history).
    """
    if df_clean.empty:
        return

    employees = (df_clean[['nik', 'nama']]
                 .dropna(subset=['nik'])
                 .drop_duplicates(subset=['nik'])
                 .copy())

    # Cek NIK mana yang belum punya history bagian sama sekali
    with engine.connect() as conn:
        existing_history_niks = set(
            row[0] for row in conn.execute(text(
                "SELECT DISTINCT nik FROM karyawan_bagian_history"
            )).fetchall()
        )

    new_niks = employees[~employees['nik'].isin(existing_history_niks)]
    if not new_niks.empty:
        print(f"\n   ⚠️  NIK baru ditemukan — belum punya riwayat bagian:")
        for _, row in new_niks.iterrows():
            print(f"      - {row['nik']} : {row['nama']}")
        print(f"      → Silakan tambahkan bagian via UI Profile Departemen")
        print(f"        (menu Manajemen Riwayat Bagian)\n")

    inserted = updated = 0
    for i in range(0, len(employees), 1000):
        chunk = employees.iloc[i:i+1000]
        with engine.begin() as conn:
            for _, row in chunk.iterrows():
                result = conn.execute(text("""
                    INSERT INTO sips_employees (nik, nama)
                    VALUES (:nik, :nama)
                    ON CONFLICT (nik) DO UPDATE
                        SET nama       = EXCLUDED.nama,
                            updated_at = CURRENT_TIMESTAMP
                    RETURNING (xmax = 0) AS is_insert
                """), {'nik': row['nik'], 'nama': row['nama']})
                if result.fetchone()[0]: inserted += 1
                else: updated += 1

    print(f"   Karyawan    : +{inserted} baru, ~{updated} update")


def sync_sips_data(df_clean: pd.DataFrame, engine):
    """
    DELETE semua data untuk list bulan/tahun yang ada di PERIODE_IMPORT,
    lalu INSERT ulang data yang sudah di-filter.
    """
    if df_clean.empty:
        return

    periods = df_clean[['bulan_import', 'tahun_import']].drop_duplicates().values.tolist()
    deleted_total = 0
    for b, t in periods:
        with engine.begin() as conn:
            deleted = conn.execute(text("""
                DELETE FROM sips_data
                WHERE bulan_import = :b AND tahun_import = :t
            """), {'b': b, 't': t}).rowcount
            deleted_total += deleted

    for i in range(0, len(df_clean), 1000):
        chunk = df_clean.iloc[i:i+1000]
        with engine.begin() as conn:
            chunk.to_sql('sips_data', conn, if_exists='append', index=False)

    print(f"   Data SIPS   : {deleted_total} lama dihapus → {len(df_clean):,} baru diinsert")


# =====================================================================
# MAIN
# =====================================================================

def run_etl():
    periods_str = ", ".join([f"{b}/{t}" for b, t in Config.PERIODE_IMPORT])

    print("=" * 55)
    print("🚀 SIPS MONITORING - ETL")
    print(f"   Periode : {periods_str}")
    print("=" * 55)

    try:
        engine = db_get_engine()
        with engine.connect() as conn: conn.execute(text("SELECT 1"))
        print("✅ Koneksi database OK\n")
    except Exception as e:
        print(f"❌ Koneksi database gagal: {e}"); return

    try:
        df_raw   = load_sips_excel()
        df_clean = transform(df_raw)
        print()
        sync_employees(df_clean, engine)
        sync_sips_data(df_clean, engine)
    except FileNotFoundError as e:
        print(f"\n❌ {e}"); return
    except Exception as e:
        import traceback
        print(f"\n❌ Error: {e}"); traceback.print_exc(); return

    # Report Summary
    with engine.connect() as conn:
        total_emp  = conn.execute(text("SELECT COUNT(*) FROM sips_employees")).scalar()
        total_data = conn.execute(text("SELECT COUNT(*) FROM sips_data")).scalar()

        total_bln = 0
        for b, t in Config.PERIODE_IMPORT:
            total_bln += conn.execute(text(
                "SELECT COUNT(*) FROM sips_data WHERE bulan_import=:b AND tahun_import=:t"
            ), {'b': b, 't': t}).scalar()

    print("\n" + "=" * 55)
    print("✅ ETL SELESAI")
    print(f"   Total karyawan di DB   : {total_emp:,}")
    print(f"   Total data periode ini : {total_bln:,}  ({periods_str})")
    print(f"   Total semua data DB    : {total_data:,}")
    print("=" * 55)


if __name__ == "__main__":
    run_etl()