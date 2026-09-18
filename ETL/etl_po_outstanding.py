"""
etl_po_outstanding.py - ETL untuk Modul PO Outstanding (sheet "ALL" bulanan)

TUGAS TUNGGAL: baca sheet ALL bulanan, upsert ke po_all_raw, catat PO+Item
yang baru terdeteksi Clear ke po_clear_history (memori permanen).

PENTING -- kenapa file ini TIDAK menghitung/menyimpan keterlambatan atau
mengisi tabel po_outstanding: keterlambatan (CURRENT_DATE - delivery_date)
berubah nilainya setiap hari walau delivery_date tidak berubah. Kalau
angka itu dihitung sekali lalu disimpan di ETL, dia langsung basi begitu
hari berganti. Karena itu po_outstanding TIDAK LAGI berupa tabel fisik --
dia dibuat sebagai VIEW (lihat schema_po_outstanding_v3.sql), yang meng-
hitung ulang keterlambatan secara otomatis SETIAP KALI dibaca (persis
seperti rumus =TODAY()-tanggal di Google Sheets). Jadi halaman Streamlit
mana pun yang query dari po_outstanding akan selalu dapat angka yang
akurat per hari ini, tanpa perlu proses "generate ulang" terpisah.

Alur:
1. Baca file Excel sheet ALL bulanan (misal "ALL (September 2026)") apa adanya
   -- data mentah yang sudah kamu isi manual kolom W-AC di Google Sheets.
2. Untuk tiap baris, cek apakah baris ini sudah "Clear":
      Clear jika  keterangan_rencana_kirim (kolom X) TERISI
               ATAU status_jawaban (kolom Z) == 'Sudah Ada Jawaban'
3. Baris yang baru terdeteksi Clear -> dicatat ke po_clear_history (permanen,
   tidak akan pernah dihapus oleh ETL ini di masa depan).
4. SEMUA baris (baik yang clear maupun belum) di-upsert ke po_all_raw, supaya
   po_all_raw selalu mencerminkan kondisi TERBARU tiap PO+Item apa adanya.
"""

import pandas as pd
import numpy as np
from sqlalchemy import text
import os
from datetime import datetime


class Config:
    PO_ALL_FILE = None
    SHEET_NAME = None          # misal "ALL (September 2026)"
    UPLOAD_MONTH = None        # misal "2026-09"; kalau None, diambil dari SHEET_NAME atau hari ini


def db_get_engine():
    """Default database engine getter, bisa di-override oleh caller."""
    from config_db import get_db_engine
    return get_db_engine()


def _guess_upload_month(sheet_name):
    """Coba tebak bulan-tahun dari nama sheet, misal 'ALL (September 2026)' -> '2026-09'.
    Kalau gagal, pakai bulan berjalan saat ETL dijalankan."""
    bulan_map = {
        'januari': '01', 'februari': '02', 'maret': '03', 'april': '04',
        'mei': '05', 'juni': '06', 'juli': '07', 'agustus': '08',
        'september': '09', 'oktober': '10', 'november': '11', 'desember': '12'
    }
    if sheet_name:
        lower = sheet_name.lower()
        for nama, angka in bulan_map.items():
            if nama in lower:
                import re
                match = re.search(r'(20\d{2})', sheet_name)
                tahun = match.group(1) if match else str(datetime.today().year)
                return f"{tahun}-{angka}"
    return datetime.today().strftime("%Y-%m")


def run_etl():
    if not Config.PO_ALL_FILE or not os.path.exists(Config.PO_ALL_FILE):
        print(f"ERROR: File {Config.PO_ALL_FILE} tidak ditemukan!")
        return False

    sheet_name = Config.SHEET_NAME
    upload_month = Config.UPLOAD_MONTH or _guess_upload_month(sheet_name)

    print(f"[*] Membaca file PO ALL dari {Config.PO_ALL_FILE}, sheet '{sheet_name}'...")
    try:
        if sheet_name:
            df = pd.read_excel(Config.PO_ALL_FILE, sheet_name=sheet_name)
        else:
            df = pd.read_excel(Config.PO_ALL_FILE)
    except ValueError as e:
        print(f"ERROR: Sheet '{sheet_name}' tidak ditemukan di file. Detail: {e}")
        return False

    print(f"[*] Total data mentah dimuat: {len(df)} baris.")
    print(f"[*] Upload month terdeteksi: {upload_month}")

    print("[*] Membersihkan dan memetakan kolom...")
    # Pemetaan header sheet ALL -> nama kolom database.
    # Sesuaikan key di sebelah kiri jika header di Excel sedikit berbeda.
    column_mapping = {
        "Purchasing Document": "purchasing_document",
        "Item": "item",
        "Buyer": "buyer",
        "Purchase Requisition": "purchase_requisition",
        "Short Text": "short_text",
        "Document Date": "document_date",
        "Delivery Date": "delivery_date",
        "Vendor Code": "vendor_code",
        "Vendor Name": "vendor_name",
        "Vendor email": "vendor_email",
        "Tindak Lanjut (No. Surat)": "tindak_lanjut_no_surat",
        "Keterangan / Rencana Kirim": "keterangan_rencana_kirim",
        "Status Email": "status_email",
        "Status Jawaban": "status_jawaban",
        "Link Dokumentasi Balasan": "link_dokumentasi_balasan",
        "Keterangan Email": "keterangan_email",
        "Bagian": "bagian",
    }

    # ---------------------------------------------------------------------
    # Pencocokan header TOLERAN terhadap perbedaan kecil (spasi ganda,
    # spasi di sekitar '/', kapitalisasi, spasi di awal/akhir). Header Excel
    # sering sedikit berbeda antar bulan (misal "Keterangan/Rencana Kirim"
    # vs "Keterangan / Rencana Kirim") walau maksudnya sama -- exact match
    # akan gagal diam-diam dan mengosongkan seluruh kolom itu tanpa error.
    # ---------------------------------------------------------------------
    def _normalize_header(h):
        import re
        h = str(h).strip().lower()
        h = re.sub(r'\s*/\s*', '/', h)   # "a / b" atau "a/ b" -> "a/b"
        h = re.sub(r'\s+', ' ', h)        # spasi ganda -> satu spasi
        return h

    kolom_asli_di_file = list(df.columns)
    normalized_to_actual = {_normalize_header(c): c for c in kolom_asli_di_file}

    kolom_wajib = ["Purchasing Document", "Item"]
    kolom_hilang = [
        k for k in kolom_wajib
        if _normalize_header(k) not in normalized_to_actual
    ]
    if kolom_hilang:
        print(f"ERROR: Kolom wajib tidak ditemukan di sheet: {kolom_hilang}")
        print(f"       Kolom yang tersedia: {kolom_asli_di_file}")
        return False

    # Bangun pemetaan (nama kolom ASLI di file -> nama kolom db) memakai
    # perbandingan yang sudah dinormalisasi, tapi rename tetap pakai nama
    # kolom asli persis seperti tertulis di file (supaya df[...] tidak error).
    kolom_tersedia = {}
    kolom_tidak_ketemu = []
    for header_target, kolom_db in column_mapping.items():
        norm_target = _normalize_header(header_target)
        if norm_target in normalized_to_actual:
            nama_asli_di_file = normalized_to_actual[norm_target]
            kolom_tersedia[nama_asli_di_file] = kolom_db
        else:
            kolom_tidak_ketemu.append(header_target)

    if kolom_tidak_ketemu:
        print(f"[!] Kolom berikut tidak ditemukan di file dan akan dikosongkan: {kolom_tidak_ketemu}")
        print(f"    (Header yang tersedia di file: {kolom_asli_di_file})")

    df_clean = df[list(kolom_tersedia.keys())].rename(columns=kolom_tersedia)

    # Tambahkan kolom yang tidak ketemu sebagai kosong, supaya struktur tetap konsisten
    for kolom_asli, kolom_db in column_mapping.items():
        if kolom_db not in df_clean.columns:
            df_clean[kolom_db] = None

    # Cleansing teks dasar
    kolom_teks = [
        "purchasing_document", "item", "buyer", "purchase_requisition", "short_text",
        "vendor_code", "vendor_name", "vendor_email", "tindak_lanjut_no_surat",
        "keterangan_rencana_kirim", "status_email", "status_jawaban",
        "link_dokumentasi_balasan", "keterangan_email", "bagian"
    ]
    for col in kolom_teks:
        df_clean[col] = df_clean[col].astype(str).str.strip()
        df_clean[col] = df_clean[col].replace({'nan': None, 'NaN': None, 'None': None, '': None})

    # Purchasing Document & Item adalah kombinasi kunci -> hapus baris tanpa keduanya
    awal_len = len(df_clean)
    df_clean = df_clean[df_clean['purchasing_document'].notna() & df_clean['item'].notna()]
    print(f"[*] Dihapus {awal_len - len(df_clean)} baris karena Purchasing Document/Item kosong.")

    # Format tanggal
    date_columns = ['document_date', 'delivery_date']
    for col in date_columns:
        df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce')

    df_clean['upload_month'] = upload_month

    df_clean = df_clean.replace({np.nan: None, 'NaT': None})
    df_clean = df_clean.drop_duplicates(subset=['purchasing_document', 'item'], keep='last')
    print(f"[*] Total data siap simpan: {len(df_clean)} baris (unik berdasarkan Purchasing Document + Item).")

    # -------------------------------------------------------------------
    # Deteksi baris yang Clear (menurut definisi yang disepakati):
    #   Clear jika keterangan_rencana_kirim TERISI
    #          ATAU status_jawaban == 'Sudah Ada Jawaban'
    # -------------------------------------------------------------------
    def _is_clear(row):
        if row['keterangan_rencana_kirim'] is not None and str(row['keterangan_rencana_kirim']).strip() != '':
            return 'keterangan_rencana_kirim_terisi'
        if row['status_jawaban'] == 'Sudah Ada Jawaban':
            return 'vendor_sudah_jawab'
        return None

    df_clean['_clear_reason'] = df_clean.apply(_is_clear, axis=1)
    df_baru_clear = df_clean[df_clean['_clear_reason'].notna()][
        ['purchasing_document', 'item', '_clear_reason']
    ].copy()
    print(f"[*] Terdeteksi {len(df_baru_clear)} baris berstatus Clear pada upload ini.")

    engine = db_get_engine()

    with engine.begin() as conn:
        # ---------------------------------------------------------------
        # 1. Upsert ke po_clear_history (memori permanen, tidak pernah dihapus)
        #    ON CONFLICT DO NOTHING -> kalau sudah pernah tercatat clear di
        #    bulan sebelumnya, cleared_date & source_upload_month TIDAK diubah
        #    (mempertahankan kapan PERTAMA KALI dia clear).
        # ---------------------------------------------------------------
        if not df_baru_clear.empty:
            df_baru_clear['source_upload_month'] = upload_month
            df_baru_clear.to_sql('temp_clear_history', conn, if_exists='replace', index=False)

            conn.execute(text("""
                INSERT INTO po_clear_history (purchasing_document, item, cleared_reason, source_upload_month)
                SELECT purchasing_document, item, "_clear_reason", source_upload_month
                FROM temp_clear_history
                ON CONFLICT (purchasing_document, item) DO NOTHING;
            """))
            conn.execute(text("DROP TABLE temp_clear_history;"))
            print(f"[*] po_clear_history diperbarui (baris baru saja ditambahkan, baris lama tidak diubah).")

        # ---------------------------------------------------------------
        # 2. Upsert SEMUA baris ke po_all_raw (data mentah apa adanya)
        # ---------------------------------------------------------------
        df_upsert = df_clean.drop(columns=['_clear_reason'])
        columns = list(df_upsert.columns)

        df_upsert.to_sql('temp_po_all_raw', conn, if_exists='replace', index=False)

        set_clause = ", ".join([
            f"{col} = EXCLUDED.{col}" for col in columns
            if col not in ('purchasing_document', 'item')
        ])

        select_clause_items = []
        for col in columns:
            if col in date_columns:
                select_clause_items.append(f"CAST({col} AS TIMESTAMP)")
            else:
                select_clause_items.append(col)
        select_clause = ", ".join(select_clause_items)

        upsert_query = f"""
            INSERT INTO po_all_raw ({', '.join(columns)})
            SELECT {select_clause} FROM temp_po_all_raw
            ON CONFLICT (purchasing_document, item) DO UPDATE SET {set_clause};
        """
        conn.execute(text(upsert_query))
        conn.execute(text("DROP TABLE temp_po_all_raw;"))

    print("[*] Proses ETL PO Outstanding selesai dengan sukses!")
    print("[*] Tabel po_outstanding (VIEW) otomatis ter-update -- tidak perlu proses tambahan.")
    return True


if __name__ == "__main__":
    run_etl()