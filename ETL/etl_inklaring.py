"""
etl_inklaring.py - ETL untuk Modul Inklaring Barang Impor
Membaca file Excel/CSV inklaring, membersihkan format angka dan tanggal,
lalu menyimpannya ke PostgreSQL:
  1. Sheet utama (mis. "2026 - BB/BD/BP") -> tabel inklaring_impor (Upsert)
  2. Sheet "Monitoring"                  -> tabel inklaring_monitoring (Replace total)
"""

import re
import os
import datetime as dt

import pandas as pd
import numpy as np
from sqlalchemy import text
from sqlalchemy.types import Date, Integer


class Config:
    INKLARING_FILE = None
    INKLARING_SHEET = None          # None = sheet pertama (perilaku lama)
    MONITORING_SHEET = "Monitoring"


def db_get_engine():
    """Default database engine getter, bisa di-override oleh caller."""
    from config_db import get_db_engine
    return get_db_engine()


# =============================================================================
# BAGIAN 1: ETL INKLARING UTAMA (tidak berubah, hanya ganti nama fungsi)
# =============================================================================
def run_etl_inklaring():
    if not Config.INKLARING_FILE or not os.path.exists(Config.INKLARING_FILE):
        print(f"ERROR: File {Config.INKLARING_FILE} tidak ditemukan!")
        return False

    print(f"[*] Membaca file Inklaring dari {Config.INKLARING_FILE}...")
    if Config.INKLARING_FILE.endswith('.csv'):
        df = pd.read_csv(Config.INKLARING_FILE)
    else:
        sheet = Config.INKLARING_SHEET if Config.INKLARING_SHEET is not None else 0
        df = pd.read_excel(Config.INKLARING_FILE, sheet_name=sheet)

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


# =============================================================================
# BAGIAN 2: ETL MONITORING (BARU)
# =============================================================================
SENTINEL_NOL = pd.Timestamp("1900-01-01")   # penanda untuk isian angka 0
BULAN_ID = {"Okt": "Oct", "Des": "Dec", "Agu": "Aug", "Agt": "Aug", "Mei": "May"}

MONITORING_DDL = """
CREATE TABLE IF NOT EXISTS inklaring_monitoring (
    id SERIAL PRIMARY KEY,
    no_baris_sheet INT,
    nama_kapal TEXT NOT NULL,
    no_po_ln TEXT, po_sap TEXT, incoterm TEXT, komoditi TEXT, pemasok TEXT, agent TEXT,
    tgl_eta DATE, tgl_terima_order DATE, tgl_po_sap DATE,
    tgl_terima_bl DATE, tgl_terima_invoice DATE,
    tgl_draft_manifest DATE, tgl_manifest DATE, tgl_ijin_timbun DATE, tgl_truck_lossing DATE,
    pib TEXT, tgl_pib DATE, tgl_memo_bayar_pib DATE, tgl_pkm DATE, tgl_bpn DATE,
    no_pen_pib TEXT, tgl_no_pen_pib DATE, penjaluran TEXT, tgl_spjm DATE,
    no_sppb TEXT, tgl_sppb DATE, tgl_polis DATE, tgl_laporan_penimbunan DATE, tgl_sptnp DATE,
    status TEXT, buyer TEXT, expeditor TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);
"""

# Kunci = header di sheet (sudah di-uppercase & spasi dirapikan)
MONITORING_COLUMNS = {
    "NAMA KAPAL": "nama_kapal", "NO. PO LN": "no_po_ln", "PO SAP": "po_sap",
    "INCOTERM": "incoterm", "KOMODITI": "komoditi", "PEMASOK": "pemasok", "AGENT": "agent",
    "ETA": "tgl_eta", "TERIMA ORDER": "tgl_terima_order", "TGL PO SAP": "tgl_po_sap",
    "TERIMA DOKUMEN ORI (BL)": "tgl_terima_bl",
    "TERIMA DOKUMEN ORI (INVOICE)": "tgl_terima_invoice",
    "DRAFT MANIFEST": "tgl_draft_manifest", "MANIFEST": "tgl_manifest",
    "IJIN TIMBUN": "tgl_ijin_timbun", "TRUCK LOSSING": "tgl_truck_lossing",
    "PIB": "pib", "TGL PIB": "tgl_pib", "MEMO BAYAR PIB": "tgl_memo_bayar_pib",
    "PKM": "tgl_pkm", "BPN": "tgl_bpn", "NO PEN PIB": "no_pen_pib",
    "TGL NO PEN PIB": "tgl_no_pen_pib", "PENJALURAN": "penjaluran", "SPJM": "tgl_spjm",
    "NO SPPB": "no_sppb", "TGL SPPB": "tgl_sppb", "POLIS": "tgl_polis",
    "LAPORAN PENIMBUNAN": "tgl_laporan_penimbunan", "SPTNP": "tgl_sptnp",
    "STATUS": "status", "BUYER": "buyer", "EXPEDITOR": "expeditor",
}
TEXT_COLS = ["nama_kapal", "no_po_ln", "po_sap", "incoterm", "komoditi", "pemasok", "agent",
             "pib", "no_pen_pib", "penjaluran", "no_sppb", "status", "buyer", "expeditor"]
DATE_COLS = [c for c in MONITORING_COLUMNS.values() if c.startswith("tgl_")]


def _parse_tahap(v):
    """Tanggal -> Timestamp, angka 0 -> SENTINEL_NOL (1900-01-01), kosong -> NaT."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return pd.NaT
    if isinstance(v, dt.time):            # serial 0 kadang terbaca sebagai time(0,0)
        return SENTINEL_NOL
    if isinstance(v, (int, float, np.number)):
        if v == 0:
            return SENTINEL_NOL
        return pd.to_datetime(v, unit="D", origin="1899-12-30", errors="coerce")
    if isinstance(v, str):
        s = v.strip()
        if s in ("", "-", "nan", "NaN", "None", "NaT"):
            return pd.NaT
        if s == "0":
            return SENTINEL_NOL
        for k, val in BULAN_ID.items():
            s = s.replace(k, val)
        v = s
    ts = pd.to_datetime(v, errors="coerce", dayfirst=True)
    if pd.isna(ts):
        return pd.NaT
    if ts.year < 1950:                    # 30-Des-1899 dari Google Sheets = angka 0
        return SENTINEL_NOL
    return ts.normalize()


def run_etl_monitoring():
    if not Config.INKLARING_FILE or not os.path.exists(Config.INKLARING_FILE):
        print(f"ERROR: File {Config.INKLARING_FILE} tidak ditemukan!")
        return False

    if Config.INKLARING_FILE.endswith(".csv"):
        print("[*] File CSV tidak punya sheet Monitoring, bagian Monitoring dilewati.")
        return True

    try:
        df = pd.read_excel(Config.INKLARING_FILE, sheet_name=Config.MONITORING_SHEET)
    except ValueError:
        print(f"[!] Sheet '{Config.MONITORING_SHEET}' tidak ditemukan, bagian Monitoring dilewati.")
        return True

    print(f"[*] Membaca sheet Monitoring: {len(df)} baris mentah.")

    # Normalisasi header (spasi ganda / enter di dalam sel header)
    df.columns = [re.sub(r"\s+", " ", str(c)).strip().upper() for c in df.columns]
    df["no_baris_sheet"] = df.index + 2   # baris 1 = header

    kurang = [k for k in MONITORING_COLUMNS if k not in df.columns]
    if kurang:
        print(f"[!] Kolom tidak ditemukan di sheet Monitoring (diisi kosong): {kurang}")
        for k in kurang:
            df[k] = None

    df = df[["no_baris_sheet"] + list(MONITORING_COLUMNS)].rename(columns=MONITORING_COLUMNS)

    for c in TEXT_COLS:
        df[c] = (df[c].astype(str).str.strip()
                 .str.replace(r"\.0$", "", regex=True)
                 .replace({"nan": None, "NaN": None, "None": None, "": None}))
    df["nama_kapal"] = df["nama_kapal"].str.upper().str.replace(r"\s+", " ", regex=True)

    awal = len(df)
    df = df[df["nama_kapal"].notna()].copy()
    print(f"[*] Dihapus {awal - len(df)} baris karena NAMA KAPAL kosong.")

    for c in DATE_COLS:
        df[c] = df[c].apply(_parse_tahap).apply(lambda x: x.date() if pd.notna(x) else None)

    print("[*] Menyimpan data Monitoring ke database (ganti total)...")
    engine = db_get_engine()
    with engine.begin() as conn:          # satu transaksi: gagal = rollback, data lama aman
        conn.execute(text(MONITORING_DDL))
        conn.execute(text("TRUNCATE TABLE inklaring_monitoring RESTART IDENTITY;"))
        tipe_kolom = {c: Date() for c in DATE_COLS}
        tipe_kolom["no_baris_sheet"] = Integer()
        df.to_sql("inklaring_monitoring", conn, if_exists="append", index=False,
                  dtype=tipe_kolom)

    print(f"[*] Monitoring: {len(df)} baris tersimpan (data lama diganti).")
    return True


# =============================================================================
# ENTRY POINT (dipanggil oleh halaman Manajemen Data)
# =============================================================================
def run_etl():
    ok_utama = run_etl_inklaring()
    if not ok_utama:
        return False
    try:
        return run_etl_monitoring()
    except Exception as e:
        # Transaksi Monitoring terpisah: data inklaring utama sudah aman tersimpan
        print(f"[!] ETL Monitoring gagal: {e}")
        return False


if __name__ == "__main__":
    run_etl()