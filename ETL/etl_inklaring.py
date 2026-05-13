"""
etl_inklaring.py - ETL untuk Modul Inklaring Barang Impor
Membaca file Excel/CSV inklaring, membersihkan format angka dan tanggal,
lalu menyimpannya ke tabel inklaring_impor di PostgreSQL menggunakan Upsert.
"""

import pandas as pd
import numpy as np
from sqlalchemy import text
import os

class Config:
    INKLARING_FILE = None

def db_get_engine():
    """Default database engine getter, bisa di-override oleh caller."""
    from config_db import get_db_engine
    return get_db_engine()

def run_etl():
    if not Config.INKLARING_FILE or not os.path.exists(Config.INKLARING_FILE):
        print(f"ERROR: File {Config.INKLARING_FILE} tidak ditemukan!")
        return False

    print(f"[*] Membaca file Inklaring dari {Config.INKLARING_FILE}...")
    if Config.INKLARING_FILE.endswith('.csv'):
        df = pd.read_csv(Config.INKLARING_FILE)
    else:
        df = pd.read_excel(Config.INKLARING_FILE)

    print(f"[*] Total data mentah dimuat: {len(df)} baris.")

    print("[*] Membersihkan dan memetakan kolom...")
    column_mapping = {
        "Tgl PIB": "tgl_pib", "AJU PIB": "aju_pib", "NO AJU": "no_aju",
        "SAP": "sap", "LN": "ln", "NAMA KAPAL": "nama_kapal",
        "Tgl ETA": "tgl_eta", "QUANTITY (MT)": "quantity_mt", "PEMASOK": "pemasok",
        "PENGIRIM": "pengirim", "AGENT": "agent", "KOMODITI": "komoditi",
        "ASAL NEGARA": "asal_negara", "Port of Load": "port_of_load", "HS": "hs_code",
        "Bea Masuk (Rp)": "bea_masuk_rp", "PPN": "ppn_rp", "PPH": "pph_rp",
        "BM % ": "bm_persen", "GUDANG TIMBUN": "gudang_timbun", "INVOICE": "invoice",
        "Kurs": "kurs", "SKEP BC": "skep_bc", "START BONGKAR": "start_bongkar",
        "SELESAI BONGKAR": "selesai_bongkar", "PPJK": "ppjk", "SPJM": "spjm",
        "AMBIL SAMPEL": "ambil_sampel", "No Pen PIB": "no_pen_pib", 
        "Tgl No Pen PIB": "tgl_no_pen_pib", "No S P P B": "no_sppb", 
        "Tgl SPPB": "tgl_sppb", "STATUS": "status", "NO SPTNP": "no_sptnp",
        "Tgl SPTNP": "tgl_sptnp", "NILAI SPTNP": "nilai_sptnp"
    }
    
    df_clean = df[list(column_mapping.keys())].rename(columns=column_mapping)
    
    # Cleansing Text
    kolom_teks = ['sap', 'no_aju', 'ln']
    for col in kolom_teks:
        df_clean[col] = df_clean[col].astype(str).str.replace(r'\.0$', '', regex=True)
        df_clean[col] = df_clean[col].replace({'nan': None, 'NaN': None, 'None': None})
    
    # Abaikan data tanpa No AJU
    awal_len = len(df_clean)
    df_clean = df_clean[df_clean['no_aju'].notna() & (df_clean['no_aju'].astype(str).str.strip() != '')]
    print(f"[*] Dihapus {awal_len - len(df_clean)} baris karena 'No AJU' kosong.")

    # Isi aju_pib jika kosong
    df_clean['aju_pib'] = df_clean['aju_pib'].fillna(
        'TEMP-' + df_clean['sap'].astype(str) + '-' + df_clean['no_aju'].astype(str)
    )

    date_columns = ['tgl_pib', 'tgl_eta', 'tgl_no_pen_pib', 'tgl_sppb', 'tgl_sptnp', 'start_bongkar', 'selesai_bongkar']
    numeric_columns = ['quantity_mt', 'bea_masuk_rp', 'ppn_rp', 'pph_rp', 'bm_persen', 'kurs', 'nilai_sptnp']

    print("[*] Memformat data Tanggal dan Angka...")
    for col in date_columns:
        df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce')

    for col in numeric_columns:
        if df_clean[col].dtype == 'object':
            df_clean[col] = df_clean[col].astype(str).str.replace(r'[\.,]00$', '', regex=True)
            df_clean[col] = df_clean[col].str.replace(r'[,\.]', '', regex=True)
        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

    df_clean = df_clean.replace({np.nan: None, 'NaT': None})
    df_clean = df_clean.drop_duplicates(subset=['aju_pib'], keep='last')
    print(f"[*] Total data siap simpan: {len(df_clean)} baris (unik berdasarkan AJU PIB).")

    print("[*] Menyimpan data ke database (Upsert)...")
    engine = db_get_engine()
    
    with engine.begin() as conn:
        # Load ke temp_table
        df_clean.to_sql('temp_inklaring', conn, if_exists='replace', index=False)
        
        columns = list(df_clean.columns)
        set_clause = ", ".join([f"{col} = EXCLUDED.{col}" for col in columns if col != 'aju_pib'])
        
        select_clause_items = []
        for col in columns:
            if col in numeric_columns:
                select_clause_items.append(f"CAST({col} AS NUMERIC)")
            elif col in date_columns:
                select_clause_items.append(f"CAST({col} AS TIMESTAMP)")
            else:
                select_clause_items.append(col)
                
        select_clause = ", ".join(select_clause_items)
        
        upsert_query = f"""
            INSERT INTO inklaring_impor ({', '.join(columns)})
            SELECT {select_clause} FROM temp_inklaring
            ON CONFLICT (aju_pib) DO UPDATE SET {set_clause};
        """
        conn.execute(text(upsert_query))
        conn.execute(text("DROP TABLE temp_inklaring;"))
        
    print("[*] Proses Inklaring selesai dengan sukses!")
    return True

if __name__ == "__main__":
    run_etl()