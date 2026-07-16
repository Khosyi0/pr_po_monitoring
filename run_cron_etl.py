# run_cron_etl.py
import os
import sys
import requests
from datetime import datetime

# Masukkan folder ETL ke dalam system path agar script bisa di-import
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'ETL')))
from ETL import etl_harga_bahan_baku as etl_bb
from ETL import etl_inklaring as etl_ink

def run_automation():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Memulai Otomasi ETL Harian...")

    # Kredensial & ID Sheet
    SHEET_ID_BB = "11QKLfNWhV7mFpwgJJ-6Zg8HWWs3yEmHCGszNuwDXl5o"
    SHEET_ID_INK = "1MD8RCYEeY_VC_NHjNfxiNKOTWyTNdgJscJL_thOZVtQ" 

    # --- 1. PROSES ETL HARGA BAHAN BAKU ---
    print("\n[*] Menarik data Harga Bahan Baku...")
    url_bb = f"https://docs.google.com/spreadsheets/d/{SHEET_ID_BB}/export?format=xlsx"
    try:
        # Typo di baris ini sudah dirapikan menjadi url_bb
        res = requests.get(url_bb, timeout=30) 
        if res.status_code == 200:
            path_bb = "cron_temp_bahan_baku.xlsx"
            with open(path_bb, "wb") as f:
                f.write(res.content)
            
            # Override konfigurasi file di modul ETL
            etl_bb.Config.EXCEL_FILE = path_bb
            etl_bb.run_etl()
            print("✅ ETL Harga Bahan Baku Berhasil!")
            if os.path.exists(path_bb): os.remove(path_bb)
        else:
            print(f"❌ Gagal unduh Bahan Baku. Status: {res.status_code}")
    except Exception as e:
        print(f"❌ Error pada ETL Bahan Baku: {e}")

    # --- 2. PROSES ETL INKLARING BARANG IMPOR ---
    print("\n[*] Menarik data Inklaring...")
    url_ink = f"https://docs.google.com/spreadsheets/d/{SHEET_ID_INK}/export?format=xlsx"
    try:
        res = requests.get(url_ink, timeout=30)
        if res.status_code == 200:
            path_ink = "cron_temp_inklaring.xlsx"
            with open(path_ink, "wb") as f:
                f.write(res.content)
            
            # Override konfigurasi file di modul ETL
            etl_ink.Config.INKLARING_FILE = path_ink
            etl_ink.run_etl()
            print("✅ ETL Inklaring Berhasil!")
            if os.path.exists(path_ink): os.remove(path_ink)
        else:
            print(f"❌ Gagal unduh Inklaring. Status: {res.status_code}")
    except Exception as e:
        print(f"❌ Error pada ETL Inklaring: {e}")

if __name__ == "__main__":
    run_automation()