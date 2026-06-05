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

    print("Membersihkan data...")
    df.columns = df.columns.str.strip()
    
    # Konversi tanggal (Dari kolom 'Tanggal Buat')
    if 'Tanggal Buat' in df.columns:
        df['Tanggal Buat'] = pd.to_datetime(df['Tanggal Buat'], errors='coerce')
        
    df = df.where(pd.notnull(df), None)
    
    records = []
    for _, row in df.iterrows():
        records.append({
            "metode": str(row.get('Metode', '')).lower().strip(),
            "status": str(row.get('Status Tender', '')),
            "no_dokumen": str(row.get('Nomer Tender', '')),
            "tgl_dokumen": row.get('Tanggal Buat'), 
            "kategori": str(row.get('Jenis', '')),
            "no_pr": "",
            "vendor": "",
            "nilai": 0.0,
            "keterangan": str(row.get('Type', '')),
            "pic": str(row.get('Buyer', '')) # SEKARANG MENGAMBIL DARI KOLOM 'Buyer'
        })

    if not records:
        print("WARNING: Tidak ada data yang ditemukan di sheet EPROC.")
        return False

    print("Menghubungkan ke database...")
    engine = get_engine()
    
    try:
        with engine.begin() as conn:
            print("Mengosongkan tabel data_eproc (TRUNCATE)...")
            conn.execute(text("TRUNCATE TABLE data_eproc RESTART IDENTITY"))
            
            print(f"Memasukkan {len(records)} baris data baru...")
            insert_query = text("""
                INSERT INTO data_eproc 
                (metode, status, no_dokumen, tgl_dokumen, kategori, no_pr, vendor, nilai, keterangan, pic)
                VALUES (:metode, :status, :no_dokumen, :tgl_dokumen, :kategori, :no_pr, :vendor, :nilai, :keterangan, :pic)
            """)
            conn.execute(insert_query, records)
            
        print("✅ PROSES ETL EPROC SELESAI DENGAN SUKSES!")
        return True
    except Exception as e:
        print(f"ERROR: Gagal menyimpan ke database. {e}")
        return False