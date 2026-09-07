"""
etl_po_outstanding.py - ETL untuk Modul PO Outstanding (Reminder Email Vendor)
Membaca file Excel PO Outstanding (Perlu Email), membersihkan format angka dan
tanggal, membuang kolom/baris bukan-data, lalu MENGGANTI TOTAL isi tabel
po_outstanding di PostgreSQL (TRUNCATE + INSERT).

Kenapa TRUNCATE + INSERT (bukan Upsert seperti Inklaring)?
-----------------------------------------------------------
Data ini adalah representasi PO Outstanding "saat file diambil". PO yang
sudah selesai akan hilang begitu saja dari file sumber berikutnya (tidak
ditandai "selesai" secara eksplisit). Supaya tabel po_outstanding selalu
mencerminkan kondisi outstanding TERKINI, seluruh isi tabel diganti total
setiap kali ETL dijalankan.
"""

import pandas as pd
import numpy as np
from sqlalchemy import text
import os


class Config:
    PO_OUTSTANDING_FILE = None
    SHEET_NAME = "Perlu Email"


def db_get_engine():
    """Default database engine getter, bisa di-override oleh caller."""
    from config_db import get_db_engine
    return get_db_engine()


def run_etl():
    if not Config.PO_OUTSTANDING_FILE or not os.path.exists(Config.PO_OUTSTANDING_FILE):
        print(f"ERROR: File {Config.PO_OUTSTANDING_FILE} tidak ditemukan!")
        return False

    print(f"[*] Membaca file PO Outstanding dari {Config.PO_OUTSTANDING_FILE} (sheet: {Config.SHEET_NAME})...")
    if Config.PO_OUTSTANDING_FILE.endswith('.csv'):
        df = pd.read_csv(Config.PO_OUTSTANDING_FILE)
    else:
        df = pd.read_excel(Config.PO_OUTSTANDING_FILE, sheet_name=Config.SHEET_NAME)

    print(f"[*] Total data mentah dimuat: {len(df)} baris.")

    print("[*] Membersihkan dan memetakan kolom...")
    # Hanya kolom yang relevan yang dipetakan. Kolom lain di file sumber
    # (mis. 'Unnamed: 21', 'Unnamed: 22', 'Kategori', 'Jumlah') adalah
    # sisa ringkasan/pivot yang menempel di sheet dan diabaikan di sini.
    column_mapping = {
        "Purchasing Document": "purchasing_document",
        "Item": "item",
        "Purchase Requisition": "purchase_requisition",
        "Short Text": "short_text",
        "Document Date": "document_date",
        "Delivery Date": "delivery_date",
        "Vendor Code": "vendor_code",
        "Vendor Name": "vendor_name",
        "Vendor email": "vendor_email",
        "Purchasing Group": "purchasing_group",
        "Order Quantity": "order_quantity",
        "Still to be delivered (qty)": "still_to_be_delivered_qty",
        "Order Unit": "order_unit",
        "Net Order Value": "net_order_value",
        "Currency": "currency",
        "Still to be delivered (value)": "still_to_be_delivered_value",
        "Outline Agreement": "outline_agreement",
        "Deletion Indicator": "deletion_indicator",
        "Requisitioner": "requisitioner",
        "PENDING TIME": "pending_time",
        "PENDING TIME Classification": "pending_time_classification",
    }

    kolom_hilang = [k for k in column_mapping if k not in df.columns]
    if kolom_hilang:
        print(f"ERROR: Kolom berikut tidak ditemukan di file sumber: {kolom_hilang}")
        return False

    df_clean = df[list(column_mapping.keys())].rename(columns=column_mapping)

    # --- Buang baris yang tidak punya Nomor PO (data kosong / baris sampah) ---
    awal_len = len(df_clean)
    df_clean = df_clean[
        df_clean['purchasing_document'].notna() &
        (df_clean['purchasing_document'].astype(str).str.strip() != '')
    ]
    print(f"[*] Dihapus {awal_len - len(df_clean)} baris karena 'Purchasing Document' kosong.")

    # --- Cleansing kolom teks/kode yang berpotensi punya sisa '.0' (dari Excel) ---
    kolom_teks_kode = [
        'purchasing_document', 'item', 'purchase_requisition', 'vendor_code',
        'outline_agreement', 'deletion_indicator'
    ]
    for col in kolom_teks_kode:
        df_clean[col] = df_clean[col].astype(str).str.replace(r'\.0$', '', regex=True)
        df_clean[col] = df_clean[col].replace({'nan': None, 'NaN': None, 'None': None})

    # --- Rapikan teks bebas (nama vendor, deskripsi, email, dll) ---
    kolom_teks_bebas = [
        'short_text', 'vendor_name', 'vendor_email', 'purchasing_group',
        'order_unit', 'currency', 'requisitioner', 'pending_time_classification'
    ]
    for col in kolom_teks_bebas:
        df_clean[col] = df_clean[col].astype(str).str.strip()
        df_clean[col] = df_clean[col].replace({'nan': None, 'NaN': None, 'None': None, '': None})

    # Email vendor: lowercase-kan supaya konsisten untuk pencarian/join nanti
    df_clean['vendor_email'] = df_clean['vendor_email'].apply(
        lambda x: x.lower() if isinstance(x, str) else x
    )

    # --- Kolom tanggal ---
    date_columns = ['document_date', 'delivery_date']
    print("[*] Memformat data Tanggal...")
    for col in date_columns:
        df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce')

    # --- Kolom numerik ---
    numeric_columns = [
        'order_quantity', 'still_to_be_delivered_qty', 'net_order_value',
        'still_to_be_delivered_value', 'pending_time'
    ]
    print("[*] Memformat data Angka...")
    for col in numeric_columns:
        if df_clean[col].dtype == 'object':
            df_clean[col] = df_clean[col].astype(str).str.replace(r'[,\.]', '', regex=True)
        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

    df_clean = df_clean.replace({np.nan: None, 'NaT': None})

    # --- Unique key: (purchasing_document, item) ---
    # Nomor PO (purchasing_document) bisa sama untuk beberapa baris karena
    # satu PO bisa punya banyak Item; pembedanya adalah kolom 'item'.
    awal_len = len(df_clean)
    df_clean = df_clean.drop_duplicates(subset=['purchasing_document', 'item'], keep='last')
    print(f"[*] Dihapus {awal_len - len(df_clean)} baris duplikat (purchasing_document + item sama).")
    print(f"[*] Total data siap simpan: {len(df_clean)} baris.")

    if df_clean.empty:
        print("ERROR: Tidak ada data valid untuk disimpan setelah proses cleansing.")
        return False

    print("[*] Mengganti total isi tabel po_outstanding (TRUNCATE + INSERT)...")
    engine = db_get_engine()

    with engine.begin() as conn:
        # Kosongkan tabel dulu -> PO yang sudah tidak outstanding (selesai)
        # otomatis tidak akan muncul lagi setelah insert data baru.
        conn.execute(text("TRUNCATE TABLE po_outstanding RESTART IDENTITY;"))

        df_clean.to_sql('po_outstanding', conn, if_exists='append', index=False)

    print("[*] Proses ETL PO Outstanding selesai dengan sukses!")
    return True


if __name__ == "__main__":
    run_etl()