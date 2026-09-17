import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import text
import os
import sys
import time
from contextlib import redirect_stdout, redirect_stderr

def _get_engine():
    from config_db import get_db_engine
    return get_db_engine()

class StreamlitCapture:
    """Menangkap output terminal dengan efisien, mengabaikan spam dari tqdm."""
    def __init__(self, placeholder):
        self.placeholder = placeholder
        self.lines = []
        self.buffer = ""
        self.last_update = time.time()
        
    def write(self, text):
        if '\r' in text:
            return  
        self.buffer += text
        if '\n' in self.buffer:
            parts = self.buffer.split('\n')
            self.lines.extend(parts[:-1])  
            self.buffer = parts[-1]        
        if time.time() - self.last_update > 1.0:
            self.flush()
            
    def flush(self):
        if not self.lines and not self.buffer:
            return
        display_lines = self.lines[-25:] 
        if self.buffer:
            display_lines.append(self.buffer)
        self.placeholder.code('\n'.join(display_lines), language='bash')
        self.last_update = time.time()

def _jalankan_etl_kondisi_stock_bb(file_path, rencana_bb_path, tahun_data):
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../ETL')))
    import etl_kondisi_stock_bb as etl_ksb

    etl_ksb.Config.EXCEL_FILE      = file_path
    etl_ksb.Config.SHEET_PUPUK     = 'Pupuk'
    etl_ksb.Config.SHEET_BB        = 'Bahan Baku'
    etl_ksb.Config.SHEET_CHART     = 'Stock Chart'
    etl_ksb.Config.RENCANA_BB_FILE = rencana_bb_path
    etl_ksb.Config.TAHUN_DATA      = tahun_data
    etl_ksb.db_get_engine          = _get_engine

    terminal = st.empty()
    capture_ksb = StreamlitCapture(terminal)
    with redirect_stdout(capture_ksb), redirect_stderr(capture_ksb):
        try:
            sukses = etl_ksb.run_etl()
            capture_ksb.flush()

            if sukses:
                st.success("Proses sinkronisasi Kondisi Stock BB selesai! Buka menu Kondisi Stock BB untuk melihat hasilnya.")
                st.cache_data.clear()
            else:
                st.error("Proses ETL Kondisi Stock BB gagal, periksa terminal di atas.")
        except Exception as e:
            st.error(f"Gagal memproses data Kondisi Stock BB: {e}")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
            if rencana_bb_path and os.path.exists(rencana_bb_path):
                os.remove(rencana_bb_path)

def render(**kwargs):
    st.markdown("""
        <h1 style='display:flex; align-items:center; font-size:38px; margin-bottom:0;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="34" height="34" fill="currentColor" 
                 viewBox="0 0 16 16" style="margin-right:12px; margin-bottom:4px;">
                <path d="M14 14V4.5L9.5 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2M9.5 3A1.5 1.5 0 0 0 11 4.5h2V14a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1h5.5z"/>
                <path d="M3 12.5h3.5v1H3zm0-2h7v1H3zm0-2h7v1H3z"/>
            </svg>
            Manajemen Kondisi Stock BB
        </h1>
    """, unsafe_allow_html=True)
    st.markdown(
        "<p style='font-size:15px; opacity:0.6; margin-top:4px; margin-bottom:24px;'>"
        "Sinkronisasi data stok bulanan, rencana kebutuhan bahan baku, serta pengaturan data per tahun."
        "</p>", 
        unsafe_allow_html=True
    )

    st.info(
        "ℹ️ ETL modul ini hanya menghapus & mengganti data untuk **tahun yang dipilih** "
        "di bawah ini. Data tahun-tahun lain di database tetap aman dan tidak tersentuh."
    )

    tahun_sekarang = datetime.today().year
    tahun_data_ksb = st.selectbox(
        "Tahun Data",
        options=list(range(tahun_sekarang - 2, tahun_sekarang + 2)),
        index=2,
        key="sel_tahun_page_ksb",
        help="Tahun data yang direkap di dalam file. Tahun ini juga dipakai untuk mencari sheet 'Data BB <tahun>' di file Rencana Kebutuhan BB."
    )

    metode_input = st.radio("Metode Input Data", ["Upload File Manual", "Tarik Langsung dari Google Sheets"], horizontal=True, key="rad_page_ksb")

    if metode_input == "Upload File Manual":
        file_ksb = st.file_uploader(
            "Upload File Utama — harus ada sheet 'Pupuk' dan 'Bahan Baku'",
            type=["xlsx"],
            key="uploader_page_ksb"
        )
        file_rencana_bb = st.file_uploader(
            f"Upload File Rencana Kebutuhan BB — harus ada sheet 'Data BB {tahun_data_ksb}' (opsional)",
            type=["xlsx"],
            key="uploader_page_rencana_bb"
        )
        if file_ksb:
            if st.button("Jalankan ETL Kondisi Stock BB", type="primary", icon=":material/cloud_upload:"):
                ksb_path = "temp_kondisi_stock_bb.xlsx"
                with open(ksb_path, "wb") as f:
                    f.write(file_ksb.getbuffer())

                rencana_bb_path = None
                if file_rencana_bb:
                    rencana_bb_path = "temp_rencana_bb.xlsx"
                    with open(rencana_bb_path, "wb") as f:
                        f.write(file_rencana_bb.getbuffer())

                _jalankan_etl_kondisi_stock_bb(ksb_path, rencana_bb_path, tahun_data_ksb)

    else:
        st.info("Pastikan Google Sheet memiliki akses 'Anyone with the link can view' agar sistem bisa mengunduhnya. Sheet 'Pupuk' dan 'Bahan Baku' harus ada di dalamnya.")

        sheet_id_ksb = st.text_input(
            "ID Google Sheet (Kondisi Stock BB)",
            value="1vlBMT1FzSYEhtU3iabkpG1rMZpIGoyE_5EF3ZVYqk3g",
            placeholder="Contoh: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
            key="txt_sheet_page_ksb"
        )
        sheet_id_rencana_bb = st.text_input(
            f"ID Google Sheet (Rencana Kebutuhan BB, sheet 'Data BB {tahun_data_ksb}') — opsional",
            value="",
            placeholder="Kosongkan kalau tidak ingin sinkronisasi Rencana Kebutuhan BB",
            key="txt_sheet_page_rencana_bb"
        )

        if st.button("Tarik Data & Jalankan ETL Kondisi Stock BB", type="primary", icon=":material/cloud_download:"):
            if not sheet_id_ksb:
                st.error("Masukkan ID Google Sheet Kondisi Stock BB terlebih dahulu!")
            else:
                with st.spinner("Mengunduh data dari Google Sheets..."):
                    import requests
                    try:
                        export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id_ksb}/export?format=xlsx"
                        response = requests.get(export_url)

                        if response.status_code == 200:
                            ksb_path = "temp_kondisi_stock_bb_gsheet.xlsx"
                            with open(ksb_path, "wb") as f:
                                f.write(response.content)

                            rencana_bb_path = None
                            if sheet_id_rencana_bb:
                                export_url_rbb = f"https://docs.google.com/spreadsheets/d/{sheet_id_rencana_bb}/export?format=xlsx"
                                response_rbb = requests.get(export_url_rbb)
                                if response_rbb.status_code == 200:
                                    rencana_bb_path = "temp_rencana_bb_gsheet.xlsx"
                                    with open(rencana_bb_path, "wb") as f:
                                        f.write(response_rbb.content)
                                else:
                                    st.warning(f"Gagal mengunduh file Rencana Kebutuhan BB (status {response_rbb.status_code}) -- lanjut tanpa data ini.")

                            st.success("File berhasil diunduh. Memulai proses ETL...")
                            _jalankan_etl_kondisi_stock_bb(ksb_path, rencana_bb_path, tahun_data_ksb)
                        else:
                            st.error(f"Gagal mengunduh file. Status code: {response.status_code}. Pastikan ID benar dan akses terbuka.")
                    except Exception as e:
                        st.error(f"Terjadi kesalahan saat mengunduh: {e}")

    # == Bagian Reset Data Khusus Modul Ini =====================================
    st.markdown("<hr style='margin: 32px 0 24px 0; border-color: rgba(128,128,128,0.2);'>", unsafe_allow_html=True)
    st.markdown("<h3 style='color:#ff4b4b; font-size:18px;'>Zona Berbahaya (Reset Data)</h3>", unsafe_allow_html=True)

    c_del_ksb, c_del_rbb = st.columns(2)

    with c_del_ksb:
        with st.expander("🗑️ Hapus Kondisi Stock BB"):
            st.write("Menghapus data Kondisi Stock BB per tahun tertentu, atau kosongkan seluruhnya.")
            del_mode = st.radio("Cakupan hapus", ["Hapus tahun tertentu", "Hapus SEMUA tahun"], key="del_mode_ksb")
            if del_mode == "Hapus tahun tertentu":
                del_thn = st.selectbox("Pilih tahun yang akan dihapus", options=list(range(tahun_sekarang - 3, tahun_sekarang + 2)), index=3, key="del_thn_ksb")
            chk_ksb = st.checkbox("Saya yakin ingin menghapus data stock", key="chk_del_page_ksb")
            if st.button("Hapus Kondisi Stock BB", type="primary", disabled=not chk_ksb, use_container_width=True):
                with st.spinner("Menghapus data..."):
                    try:
                        engine = _get_engine()
                        if del_mode == "Hapus tahun tertentu":
                            with engine.begin() as conn:
                                deleted = conn.execute(text("DELETE FROM kondisi_stock_bb_raw WHERE tahun_data = :tahun"), {'tahun': del_thn}).rowcount
                            st.success(f"Data Kondisi Stock BB tahun {del_thn} berhasil dihapus ({deleted} baris)!")
                        else:
                            with engine.begin() as conn:
                                conn.execute(text("TRUNCATE TABLE kondisi_stock_bb_raw RESTART IDENTITY CASCADE;"))
                            st.success("SELURUH data Kondisi Stock BB berhasil dikosongkan!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menghapus data: {e}")

    with c_del_rbb:
        with st.expander("🗑️ Hapus Rencana BB"):
            st.write("Menghapus data Rencana Kebutuhan BB per tahun tertentu, atau kosongkan seluruhnya.")
            del_rbb_mode = st.radio("Cakupan hapus", ["Hapus tahun tertentu", "Hapus SEMUA tahun"], key="del_mode_rbb")
            if del_rbb_mode == "Hapus tahun tertentu":
                del_rbb_thn = st.selectbox("Pilih tahun yang akan dihapus", options=list(range(tahun_sekarang - 3, tahun_sekarang + 2)), index=3, key="del_thn_rbb")
            chk_rbb = st.checkbox("Saya yakin ingin menghapus data rencana", key="chk_del_page_rbb")
            if st.button("Hapus Rencana BB", type="primary", disabled=not chk_rbb, use_container_width=True):
                with st.spinner("Menghapus data..."):
                    try:
                        engine = _get_engine()
                        if del_rbb_mode == "Hapus tahun tertentu":
                            with engine.begin() as conn:
                                deleted = conn.execute(text("DELETE FROM rencana_bb_raw WHERE tahun_data = :tahun"), {'tahun': del_rbb_thn}).rowcount
                            st.success(f"Data Rencana BB tahun {del_rbb_thn} berhasil dihapus ({deleted} baris)!")
                        else:
                            with engine.begin() as conn:
                                conn.execute(text("TRUNCATE TABLE rencana_bb_raw RESTART IDENTITY CASCADE;"))
                            st.success("SELURUH data Rencana BB berhasil dikosongkan!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menghapus data: {e}")