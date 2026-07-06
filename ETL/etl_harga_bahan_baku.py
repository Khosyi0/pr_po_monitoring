"""
etl_harga_bahan_baku.py - ETL untuk Modul Harga Pasar Bahan Baku
Membaca file Excel rekapan majalah (3-level header: Majalah, Incoterm, Min/Max/Avg),
lalu menyimpannya ke PostgreSQL menggunakan Upsert.
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

    EXCEL_FILE  = 'Majalah Harga Bahan Baku.xlsx'
    
    SHEET_MAPPING = {
        'Ammonia': 'Ammonia',
        'ZA': 'ZA'
    }

# =====================================================================
# DATABASE
# =====================================================================

def db_get_engine():
    cs = (f"postgresql://{Config.DB_USER}:{Config.DB_PASSWORD}"
          f"@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}")
    return create_engine(cs)

# =====================================================================
# EXTRACT & TRANSFORM
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

# =====================================================================
# MAIN
# =====================================================================

def run_etl():
    print("=" * 55)
    print("🚀 ETL HARGA BAHAN BAKU (v2 - 3 Level Header)")
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

    total_rows = 0
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

    print("\n" + "=" * 55)
    print("✅ ETL SELESAI")
    print(f"   Total baris berhasil dimasukkan : {total_rows:,}")
    print("=" * 55)

if __name__ == "__main__":
    run_etl()