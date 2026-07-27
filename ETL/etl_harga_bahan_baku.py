"""
etl_harga_bahan_baku.py - ETL untuk Modul Harga Pasar Bahan Baku
Membaca file Excel rekapan majalah (3-level header: Majalah, Incoterm, Min/Max/Avg),
lalu menyimpannya ke PostgreSQL menggunakan Upsert.

Selain itu, setiap sheet juga bisa memiliki satu kolom tunggal "Harga Perolehan"
(posisi kolom berbeda-beda tiap sheet, tidak selalu di kolom terakhir) yang
disimpan per (tanggal_terbit, bahan_baku) ke tabel terpisah
`harga_perolehan_bahan_baku`.
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import warnings
import os
import re

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

    EXCEL_FILE  = 'Majalah Harga Bahan Baku.xlsx'

    SHEET_MAPPING = {
        'Ammonia': 'Ammonia',
        'DAP': 'DAP',
        'NH4CL': 'NH4Cl',
        'MOP-KCl': 'MOP-KCl',
        'NPK': 'NPK',
        'Phos Acid': 'Phosphoric Acid',
        'Phos Rock': 'Phosphate Rock',
        'Sulfur New': 'Sulfur',
        'Sulfuric Acid': 'Sulfuric Acid',
        'TSP': 'TSP',
        'UREA': 'Urea',
        'ZA': 'ZA'
    }

    # Nama header kolom "Harga Perolehan" di baris pertama tiap sheet.
    # Pencarian bersifat case-insensitive dan mengabaikan spasi berlebih,
    # jadi variasi penulisan seperti "Harga  Perolehan" atau "HARGA PEROLEHAN"
    # tetap akan cocok.
    HARGA_PEROLEHAN_HEADER = "Harga Perolehan"

# =====================================================================
# DATABASE
# =====================================================================

def db_get_engine():
    cs = (f"postgresql://{Config.DB_USER}:{Config.DB_PASSWORD}"
          f"@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}")
    return create_engine(cs)


def ensure_harga_perolehan_table(engine):
    """Membuat tabel harga_perolehan_bahan_baku jika belum ada."""
    ddl = """
        CREATE TABLE IF NOT EXISTS harga_perolehan_bahan_baku (
            tanggal_terbit   DATE NOT NULL,
            bahan_baku       TEXT NOT NULL,
            harga_perolehan  NUMERIC,
            CONSTRAINT uq_harga_perolehan UNIQUE (tanggal_terbit, bahan_baku)
        );
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))

# =====================================================================
# EXTRACT & TRANSFORM - MIN/MAX/AVERAGE (proses lama, tidak diubah)
# =====================================================================

def clean_num(val):
    """Fungsi sederhana untuk mengubah string angka dengan koma menjadi float"""
    if pd.isna(val) or val == '' or str(val).strip() == '-':
        return None
    try:
        return float(str(val).replace(',', '.'))
    except ValueError:
        return None

def extract_and_transform_sheet(file_path, sheet_name, bahan_baku):
    print(f"   Membaca sheet '{sheet_name}'...")
    try:
        # Membaca excel dengan 3 baris header (Baris 1: Majalah, Baris 2: Incoterm, Baris 3: Min/Max/Avg)
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=[0, 1, 2])
    except ValueError:
        print(f"   ⚠️ Sheet '{sheet_name}' tidak ditemukan.")
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    # Jadikan kolom pertama (Tanggal) sebagai index
    kolom_tanggal = df.columns[0]
    df = df.set_index(kolom_tanggal)

    # PERBAIKAN: Hapus dropna=True karena tidak lagi didukung pada Multi-level stacking di Pandas versi baru
    df_stacked = df.stack(level=[0, 1]).reset_index()

    # Rename kolom identitas dasar
    df_stacked = df_stacked.rename(columns={
        df_stacked.columns[0]: 'tanggal_terbit',
        df_stacked.columns[1]: 'nama_majalah',
        df_stacked.columns[2]: 'incoterm'
    })

    # Samakan format nama kolom Min/Max (berjaga-jaga jika ada typo huruf besar/kecil di Excel)
    col_mapping = {c: str(c).strip().lower() for c in df_stacked.columns}
    df_stacked = df_stacked.rename(columns=col_mapping)

    if df_stacked.columns.duplicated().any():
        df_stacked = df_stacked.loc[:, ~df_stacked.columns.duplicated(keep='first')]

    # Cek apakah kolom min dan max benar-benar ada
    if 'min' not in df_stacked.columns or 'max' not in df_stacked.columns:
        print(f"   ⚠️ Format kolom Min/Max tidak ditemukan pada sheet {sheet_name}.")
        return pd.DataFrame()

    # Bersihkan nama majalah & incoterm dari kata "Unnamed" (efek sel kosong di Excel)
    df_stacked = df_stacked[~df_stacked['nama_majalah'].astype(str).str.contains('Unnamed', na=False, case=False)]
    df_stacked = df_stacked[~df_stacked['incoterm'].astype(str).str.contains('Unnamed', na=False, case=False)]

    # Format Tanggal
    df_stacked['tanggal_terbit'] = pd.to_datetime(df_stacked['tanggal_terbit'], errors='coerce').dt.date
    df_stacked = df_stacked.dropna(subset=['tanggal_terbit'])

    # Ekstrak & bersihkan angka Harga Min dan Max
    df_stacked['harga_min'] = df_stacked['min'].apply(clean_num)
    df_stacked['harga_max'] = df_stacked['max'].apply(clean_num)

    # Di sini baris data yang kosong atau tidak memiliki harga valid akan otomatis terhapus
    df_stacked = df_stacked.dropna(subset=['harga_min', 'harga_max'])

    # Tambahkan kolom statis bahan baku
    df_stacked['bahan_baku'] = bahan_baku

    # Susun kolom final untuk database
    final_cols = ['tanggal_terbit', 'nama_majalah', 'bahan_baku', 'incoterm', 'harga_min', 'harga_max']
    df_clean = df_stacked[final_cols].copy()

    # Bersihkan spasi berlebih
    df_clean['nama_majalah'] = df_clean['nama_majalah'].astype(str).str.strip()
    df_clean['incoterm'] = df_clean['incoterm'].astype(str).str.strip()

    return df_clean

# =====================================================================
# EXTRACT & TRANSFORM - HARGA PEROLEHAN (kolom tunggal, posisi bebas)
# =====================================================================

def _normalize_header_text(val):
    """Ubah teks header jadi bentuk sederhana untuk dibandingkan (lowercase, spasi tunggal)."""
    if val is None:
        return ""
    text_val = str(val)
    if text_val.strip().lower().startswith('unnamed'):
        return ""
    text_val = re.sub(r'\s+', ' ', text_val).strip().lower()
    return text_val

def extract_harga_perolehan(file_path, sheet_name, bahan_baku):
    """
    Mencari kolom 'Harga Perolehan' di sheet, di mana posisi kolomnya bisa
    berbeda-beda per sheet. Pencarian dilakukan dengan membaca baris pertama
    (header level 0) saja lalu mencocokkan nama kolomnya, terlepas dari
    posisi/index kolom tersebut.
    """
    try:
        # Baca hanya header baris pertama untuk menemukan posisi kolom target,
        # tanpa ikut memuat baris data sebagai header tambahan.
        df_header_only = pd.read_excel(file_path, sheet_name=sheet_name, header=0, nrows=0)
    except ValueError:
        return pd.DataFrame()

    target_norm = _normalize_header_text(Config.HARGA_PEROLEHAN_HEADER)
    kolom_target = None
    for col in df_header_only.columns:
        if _normalize_header_text(col) == target_norm:
            kolom_target = col
            break

    if kolom_target is None:
        print(f"   ℹ️ Kolom 'Harga Perolehan' tidak ditemukan pada sheet {sheet_name} (dilewati).")
        return pd.DataFrame()

    # Baca ulang sheet dengan header tunggal untuk mengambil kolom tanggal + kolom target
    try:
        df_full = pd.read_excel(file_path, sheet_name=sheet_name, header=0)
    except ValueError:
        return pd.DataFrame()

    kolom_tanggal = df_full.columns[0]
    df_hp = df_full[[kolom_tanggal, kolom_target]].copy()
    df_hp.columns = ['tanggal_terbit', 'harga_perolehan']

    df_hp['tanggal_terbit'] = pd.to_datetime(df_hp['tanggal_terbit'], errors='coerce').dt.date
    df_hp['harga_perolehan'] = df_hp['harga_perolehan'].apply(clean_num)

    # Baris tanpa tanggal valid atau tanpa nilai harga perolehan tidak disimpan
    df_hp = df_hp.dropna(subset=['tanggal_terbit', 'harga_perolehan'])

    if df_hp.empty:
        return pd.DataFrame()

    df_hp['bahan_baku'] = bahan_baku
    return df_hp[['tanggal_terbit', 'bahan_baku', 'harga_perolehan']]

# =====================================================================
# LOAD
# =====================================================================

def load_to_db(df_clean: pd.DataFrame, engine):
    if df_clean.empty:
        return

    print(f"   [*] Menyimpan {len(df_clean)} baris data (Upsert)...")
    with engine.begin() as conn:
        df_clean.to_sql('temp_harga_bahan_baku', conn, if_exists='replace', index=False)

        upsert_query = """
            INSERT INTO master_harga_bahan_baku 
                (tanggal_terbit, nama_majalah, bahan_baku, incoterm, harga_min, harga_max)
            SELECT 
                CAST(tanggal_terbit AS DATE), nama_majalah, bahan_baku, incoterm, 
                CAST(harga_min AS NUMERIC), CAST(harga_max AS NUMERIC)
            FROM temp_harga_bahan_baku
            ON CONFLICT (tanggal_terbit, nama_majalah, bahan_baku, incoterm) 
            DO UPDATE SET 
                harga_min = EXCLUDED.harga_min,
                harga_max = EXCLUDED.harga_max;
        """
        conn.execute(text(upsert_query))
        conn.execute(text("DROP TABLE temp_harga_bahan_baku;"))


def load_harga_perolehan_to_db(df_hp: pd.DataFrame, engine):
    if df_hp.empty:
        return

    print(f"   [*] Menyimpan {len(df_hp)} baris Harga Perolehan (Upsert)...")
    with engine.begin() as conn:
        df_hp.to_sql('temp_harga_perolehan', conn, if_exists='replace', index=False)

        upsert_query = """
            INSERT INTO harga_perolehan_bahan_baku
                (tanggal_terbit, bahan_baku, harga_perolehan)
            SELECT
                CAST(tanggal_terbit AS DATE), bahan_baku, CAST(harga_perolehan AS NUMERIC)
            FROM temp_harga_perolehan
            ON CONFLICT (tanggal_terbit, bahan_baku)
            DO UPDATE SET
                harga_perolehan = EXCLUDED.harga_perolehan;
        """
        conn.execute(text(upsert_query))
        conn.execute(text("DROP TABLE temp_harga_perolehan;"))

# =====================================================================
# MAIN
# =====================================================================

def run_etl():
    print("=" * 55)
    print("ETL HARGA BAHAN BAKU")
    print("=" * 55)

    if not os.path.exists(Config.EXCEL_FILE):
        print(f"❌ Error: File {Config.EXCEL_FILE} tidak ditemukan!")
        return

    try:
        engine = db_get_engine()
        with engine.connect() as conn: conn.execute(text("SELECT 1"))
        print("✅ Koneksi database OK\n")
    except Exception as e:
        print(f"❌ Koneksi database gagal: {e}"); return

    ensure_harga_perolehan_table(engine)

    total_rows = 0
    total_rows_hp = 0
    for sheet_name, bahan in Config.SHEET_MAPPING.items():
        try:
            df_clean = extract_and_transform_sheet(Config.EXCEL_FILE, sheet_name, bahan)
            if not df_clean.empty:
                load_to_db(df_clean, engine)
                total_rows += len(df_clean)
        except Exception as e:
            print(f"   ❌ Gagal memproses sheet '{sheet_name}': {e}")
            import traceback
            traceback.print_exc()

        try:
            df_hp = extract_harga_perolehan(Config.EXCEL_FILE, sheet_name, bahan)
            if not df_hp.empty:
                load_harga_perolehan_to_db(df_hp, engine)
                total_rows_hp += len(df_hp)
        except Exception as e:
            print(f"   ❌ Gagal memproses Harga Perolehan sheet '{sheet_name}': {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 55)
    print("✅ ETL SELESAI")
    print(f"   Total baris berhasil dimasukkan (Min/Max)     : {total_rows:,}")
    print(f"   Total baris berhasil dimasukkan (Harga Perolehan) : {total_rows_hp:,}")
    print("=" * 55)

if __name__ == "__main__":
    run_etl()