import pandas as pd
from sqlalchemy import text

class Config:
    EPROC_FILE = ""
    EPROC_SHEET = "EPROC"

db_get_engine = None

def get_engine():
    if db_get_engine:
        return db_get_engine()
    from config_db import get_db_engine
    return get_db_engine()

def run_etl():
    if not Config.EPROC_FILE:
        print("ERROR: File EPROC belum ditentukan.")
        return False
        
    print(f"Membaca file: {Config.EPROC_FILE} (Sheet: {Config.EPROC_SHEET})")
    try:
        df = pd.read_excel(Config.EPROC_FILE, sheet_name=Config.EPROC_SHEET)
    except Exception as e:
        print(f"ERROR: Gagal membaca file Excel. {e}")
        return False

    print("Membersihkan dan transformasi data...")
    df.columns = df.columns.str.strip()
    
    # Menyiapkan list untuk menampung data bersih
    records = []
    for _, row in df.iterrows():
        records.append({
            "metode": str(row.get('Metode', '')).lower().strip() if pd.notna(row.get('Metode')) else "",
            "status": str(row.get('Status Tender', '')) if pd.notna(row.get('Status Tender')) else "",
            "no_dokumen": str(row.get('Nomer Tender', '')) if pd.notna(row.get('Nomer Tender')) else "",
            "tgl_dokumen": pd.to_datetime(row.get('Tanggal Buat'), errors='coerce') if pd.notna(row.get('Tanggal Buat')) else None, 
            "kategori": str(row.get('Jenis', '')) if pd.notna(row.get('Jenis')) else "",
            "no_pr": "",
            "vendor": "",
            "nilai": 0.0,
            "keterangan": str(row.get('Type', '')) if pd.notna(row.get('Type')) else "",
            "pic": str(row.get('Buyer', '')) if pd.notna(row.get('Buyer')) else ""
        })

    if not records:
        print("WARNING: Tidak ada data yang ditemukan di sheet EPROC.")
        return False

    # Konversi kembali ke DataFrame agar bisa menggunakan to_sql yang super cepat
    df_clean = pd.DataFrame(records)

    print("Menghubungkan ke database...")
    engine = get_engine()
    
    try:
        with engine.begin() as conn:
            print("Mengosongkan tabel data_eproc (TRUNCATE)...")
            conn.execute(text("TRUNCATE TABLE data_eproc RESTART IDENTITY"))
            
            print(f"Memasukkan {len(df_clean)} baris data baru dengan Pandas to_sql...")
            # Menggunakan to_sql seperti di SIPS dengan mekanisme chunking
            for i in range(0, len(df_clean), 1000):
                chunk = df_clean.iloc[i:i+1000]
                chunk.to_sql('data_eproc', conn, if_exists='append', index=False)
            
        print("✅ PROSES ETL EPROC SELESAI DENGAN SUKSES!")
        return True
    except Exception as e:
        print(f"ERROR: Gagal menyimpan ke database. {e}")
        return False