"""
v_manajemen_harga_majalah_bb.py - Manajemen Data Harga Majalah Bahan Baku
Halaman khusus admin untuk Impor (ETL) / Tambah / Edit / Hapus data harga bahan baku
dari majalah/referensi, langsung ke tabel master_harga_bahan_baku.

Primary key alami tabel ini adalah kombinasi:
    (tanggal_terbit, nama_majalah, bahan_baku, incoterm)
karena ada UNIQUE constraint pada kombinasi tersebut (dipakai untuk ON CONFLICT
upsert oleh ETL). Tidak ada kolom id/serial.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import text
import os
import sys
import time
from contextlib import redirect_stdout, redirect_stderr

try:
    from .v_bahan_baku import BAHAN_BAKU_CONFIG, get_daftar_bahan_baku
except ImportError:  # fallback saat file dijalankan langsung
    from v_bahan_baku import BAHAN_BAKU_CONFIG, get_daftar_bahan_baku


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
        # Abaikan output dari tqdm yang menggunakan \r (carriage return)
        if '\r' in text:
            return

        self.buffer += text

        # Jika ada baris baru, pisahkan dan masukkan ke daftar baris
        if '\n' in self.buffer:
            parts = self.buffer.split('\n')
            self.lines.extend(parts[:-1])
            self.buffer = parts[-1]

        # Refresh UI max 1 detik sekali
        if time.time() - self.last_update > 1.0:
            self.flush()

    def flush(self):
        if not self.lines and not self.buffer:
            return

        # Tampilkan maksimal 25 baris terakhir agar UI tidak berat
        display_lines = self.lines[-25:]
        if self.buffer:
            display_lines.append(self.buffer)

        self.placeholder.code('\n'.join(display_lines), language='bash')
        self.last_update = time.time()


# =============================================================================
# HELPER: daftar nilai bahan_baku yang valid untuk disimpan ke DB
# Menggunakan label utama dari BAHAN_BAKU_CONFIG (bukan alias), supaya data baru
# yang ditambahkan lewat halaman ini konsisten dengan satu nilai standar.
# =============================================================================
def _get_bahan_baku_db_options():
    """
    Return list nilai bahan_baku yang bisa dipilih saat tambah/edit data.
    Untuk bahan baku dengan alias (db_value berupa list), gunakan label-nya
    sebagai nilai standar yang disimpan (bukan salah satu alias).
    """
    options = []
    for label in get_daftar_bahan_baku():
        cfg = BAHAN_BAKU_CONFIG[label]
        db_value = cfg["db_value"]
        if isinstance(db_value, (list, tuple)):
            # Simpan pakai label utama (Title Case), bukan salah satu alias lowercase
            options.append(cfg["label"])
        else:
            options.append(db_value)
    return sorted(set(options))


# =============================================================================
# QUERY HELPERS
# =============================================================================
def _load_data(load_data_fn, filter_bahan_baku=None, filter_majalah=None,
               filter_start=None, filter_end=None, limit=500):
    where_clauses = []
    if filter_bahan_baku and filter_bahan_baku != "Semua":
        cfg = BAHAN_BAKU_CONFIG.get(filter_bahan_baku)
        if cfg:
            db_value = cfg["db_value"]
            if isinstance(db_value, (list, tuple)):
                alias_list = "', '".join([a.lower().strip() for a in db_value])
                where_clauses.append(f"lower(trim(bahan_baku)) IN ('{alias_list}')")
            else:
                where_clauses.append(f"bahan_baku = '{db_value}'")
    if filter_majalah and filter_majalah != "Semua":
        majalah_escaped = filter_majalah.replace("'", "''")
        where_clauses.append(f"nama_majalah = '{majalah_escaped}'")
    if filter_start:
        where_clauses.append(f"tanggal_terbit >= '{filter_start}'")
    if filter_end:
        where_clauses.append(f"tanggal_terbit <= '{filter_end}'")

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    query = f"""
        SELECT tanggal_terbit, nama_majalah, bahan_baku, incoterm, harga_min, harga_max
        FROM master_harga_bahan_baku
        {where_sql}
        ORDER BY tanggal_terbit DESC, bahan_baku ASC, nama_majalah ASC
        LIMIT {int(limit)}
    """
    return load_data_fn(query)


def _row_exists(engine, tanggal_terbit, nama_majalah, bahan_baku, incoterm):
    query = text("""
        SELECT 1 FROM master_harga_bahan_baku
        WHERE tanggal_terbit = :tanggal_terbit
          AND nama_majalah = :nama_majalah
          AND bahan_baku = :bahan_baku
          AND incoterm = :incoterm
        LIMIT 1
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {
            "tanggal_terbit": tanggal_terbit,
            "nama_majalah": nama_majalah,
            "bahan_baku": bahan_baku,
            "incoterm": incoterm,
        })
        return result.first() is not None


def _insert_row(engine, tanggal_terbit, nama_majalah, bahan_baku, incoterm, harga_min, harga_max):
    query = text("""
        INSERT INTO master_harga_bahan_baku
            (tanggal_terbit, nama_majalah, bahan_baku, incoterm, harga_min, harga_max)
        VALUES
            (:tanggal_terbit, :nama_majalah, :bahan_baku, :incoterm, :harga_min, :harga_max)
    """)
    with engine.begin() as conn:
        conn.execute(query, {
            "tanggal_terbit": tanggal_terbit,
            "nama_majalah": nama_majalah,
            "bahan_baku": bahan_baku,
            "incoterm": incoterm,
            "harga_min": harga_min,
            "harga_max": harga_max,
        })


def _update_row(engine, original_key, new_values):
    """
    original_key: dict berisi (tanggal_terbit, nama_majalah, bahan_baku, incoterm) LAMA
    new_values: dict berisi seluruh kolom BARU (termasuk key yang mungkin berubah)
    """
    query = text("""
        UPDATE master_harga_bahan_baku
        SET tanggal_terbit = :new_tanggal_terbit,
            nama_majalah   = :new_nama_majalah,
            bahan_baku     = :new_bahan_baku,
            incoterm       = :new_incoterm,
            harga_min      = :new_harga_min,
            harga_max      = :new_harga_max
        WHERE tanggal_terbit = :old_tanggal_terbit
          AND nama_majalah   = :old_nama_majalah
          AND bahan_baku     = :old_bahan_baku
          AND incoterm       = :old_incoterm
    """)
    with engine.begin() as conn:
        conn.execute(query, {
            "new_tanggal_terbit": new_values["tanggal_terbit"],
            "new_nama_majalah": new_values["nama_majalah"],
            "new_bahan_baku": new_values["bahan_baku"],
            "new_incoterm": new_values["incoterm"],
            "new_harga_min": new_values["harga_min"],
            "new_harga_max": new_values["harga_max"],
            "old_tanggal_terbit": original_key["tanggal_terbit"],
            "old_nama_majalah": original_key["nama_majalah"],
            "old_bahan_baku": original_key["bahan_baku"],
            "old_incoterm": original_key["incoterm"],
        })


def _delete_row(engine, tanggal_terbit, nama_majalah, bahan_baku, incoterm):
    query = text("""
        DELETE FROM master_harga_bahan_baku
        WHERE tanggal_terbit = :tanggal_terbit
          AND nama_majalah   = :nama_majalah
          AND bahan_baku     = :bahan_baku
          AND incoterm       = :incoterm
    """)
    with engine.begin() as conn:
        conn.execute(query, {
            "tanggal_terbit": tanggal_terbit,
            "nama_majalah": nama_majalah,
            "bahan_baku": bahan_baku,
            "incoterm": incoterm,
        })


def _get_unique_options(engine, column):
    query = text(f"SELECT DISTINCT {column} FROM master_harga_bahan_baku WHERE {column} IS NOT NULL ORDER BY {column}")
    with engine.connect() as conn:
        res = conn.execute(query)
        return [r[0] for r in res]


# =============================================================================
# HELPER ETL: dipakai oleh tab "Impor Data (ETL)"
# =============================================================================
def _jalankan_etl_bahan_baku(file_path, update_tanggal):
    from config_db import set_setting

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../ETL')))
    import etl_harga_bahan_baku as etl_bb  # type: ignore

    etl_bb.Config.EXCEL_FILE = file_path
    etl_bb.db_get_engine = _get_engine

    terminal = st.empty()
    capture_bb = StreamlitCapture(terminal)
    with redirect_stdout(capture_bb), redirect_stderr(capture_bb):
        try:
            etl_bb.run_etl()
            capture_bb.flush()

            if update_tanggal:
                set_setting("DATA_UPDATE_BAHAN_BAKU", datetime.today().strftime("%Y-%m-%d"))

            st.success("Proses sinkronisasi Harga Bahan Baku selesai! Tekan tombol Refresh Data agar data terbaru muncul.")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Gagal memproses data Harga Bahan Baku: {e}")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)


# =============================================================================
# DIALOG KONFIRMASI HAPUS
# =============================================================================
@st.dialog("Konfirmasi Hapus Data")
def _dialog_confirm_delete(row):
    st.markdown(
        f"Yakin ingin menghapus data berikut?\n\n"
        f"- **Bahan Baku:** {row['bahan_baku']}\n"
        f"- **Majalah:** {row['nama_majalah']}\n"
        f"- **Incoterm:** {row['incoterm']}\n"
        f"- **Tanggal Terbit:** {row['tanggal_terbit']}\n"
        f"- **Harga:** {row['harga_min']} - {row['harga_max']} USD/MT\n\n"
        f"Tindakan ini **tidak bisa dibatalkan**."
    )
    col_ya, col_batal = st.columns(2)
    with col_ya:
        if st.button("Ya, Hapus", type="primary", use_container_width=True, icon=":material/delete:"):
            try:
                engine = _get_engine()
                _delete_row(
                    engine,
                    row['tanggal_terbit'], row['nama_majalah'],
                    row['bahan_baku'], row['incoterm']
                )
                st.session_state['_bb_manajemen_msg'] = ("success", "Data berhasil dihapus.")
                st.session_state.pop('_bb_row_to_delete', None)
                st.rerun()
            except Exception as e:
                st.error(f"Gagal menghapus data: {e}")
    with col_batal:
        if st.button("Batal", use_container_width=True):
            st.session_state.pop('_bb_row_to_delete', None)
            st.rerun()


# =============================================================================
# RENDER UTAMA
# =============================================================================
def render(load_data, global_context=None):
    st.markdown("### :material/edit_document: Manajemen Harga Majalah Bahan Baku")
    st.markdown(
        "<p style='font-size:14px; opacity:0.65; margin-top:-6px; margin-bottom:16px;'>"
        "Halaman khusus admin untuk mengimpor (ETL), menambah, mengubah, atau menghapus data harga "
        "bahan baku hasil rekapan majalah/referensi."
        "</p>",
        unsafe_allow_html=True
    )

    engine = _get_engine()
    daftar_bb_label = get_daftar_bahan_baku()
    daftar_bb_db_options = _get_bahan_baku_db_options()

    list_majalah = _get_unique_options(engine, "nama_majalah")
    list_incoterm = _get_unique_options(engine, "incoterm")

    # Tampilkan pesan sukses/error dari aksi sebelumnya (delete dialog, dsb)
    if '_bb_manajemen_msg' in st.session_state:
        level, msg = st.session_state.pop('_bb_manajemen_msg')
        getattr(st, level)(msg)

    tab_impor, tab_tambah, tab_lihat_edit_hapus = st.tabs([
        ":material/cloud_upload: Impor Data (ETL)",
        ":material/add_circle: Tambah Data Baru",
        ":material/table_chart: Lihat / Edit / Hapus Data"
    ])

    # =========================================================================
    # TAB 0: IMPOR DATA (ETL)
    # =========================================================================
    with tab_impor:
        st.markdown("#### Impor Data dari File Rekapan Majalah")
        st.markdown(
            "<p style='font-size:13px; opacity:0.65; margin-top:-4px; margin-bottom:16px;'>"
            "Gunakan proses ETL untuk mengunggah file "
            "rekapan Harga Bahan Baku (.xlsx), baik lewat upload manual maupun langsung dari Google Sheets."
            "</p>",
            unsafe_allow_html=True
        )

        metode_input = st.radio(
            "Metode Input Data",
            ["Upload File Manual", "Tarik Langsung dari Google Sheets"],
            horizontal=True,
            key="bb_manajemen_metode_input"
        )
        update_tgl_bahan_baku = st.checkbox(
            "Update Tanggal Data Menjadi Hari Ini",
            value=False,
            key="bb_manajemen_chk_update_tgl"
        )

        if metode_input == "Upload File Manual":
            file_bahan_baku = st.file_uploader(
                "Upload File Rekapan Majalah (.xlsx)",
                type=["xlsx"],
                key="bb_manajemen_file_uploader"
            )
            if file_bahan_baku:
                if st.button(
                    "Jalankan ETL Harga Bahan Baku",
                    type="primary",
                    icon=":material/cloud_upload:",
                    key="bb_manajemen_btn_etl_upload"
                ):
                    bb_path = "temp_bahan_baku_manajemen.xlsx"
                    with open(bb_path, "wb") as f:
                        f.write(file_bahan_baku.getbuffer())

                    _jalankan_etl_bahan_baku(bb_path, update_tgl_bahan_baku)

        else:
            st.info("Pastikan Google Sheet memiliki akses 'Anyone with the link can view' agar sistem bisa mengunduhnya.")

            sheet_id = st.text_input(
                "ID Google Sheet",
                value="11QKLfNWhV7mFpwgJJ-6Zg8HWWs3yEmHCGszNuwDXl5o",
                placeholder="Contoh: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                key="bb_manajemen_sheet_id"
            )

            if st.button(
                "Tarik Data & Jalankan ETL",
                type="primary",
                icon=":material/cloud_download:",
                key="bb_manajemen_btn_etl_gsheet"
            ):
                if not sheet_id:
                    st.error("Masukkan ID Google Sheet terlebih dahulu!")
                else:
                    with st.spinner("Mengunduh data dari Google Sheets..."):
                        import requests
                        try:
                            export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
                            response = requests.get(export_url)

                            if response.status_code == 200:
                                bb_path = "temp_bahan_baku_manajemen_gsheet.xlsx"
                                with open(bb_path, "wb") as f:
                                    f.write(response.content)

                                st.success("File berhasil diunduh. Memulai proses ETL...")
                                _jalankan_etl_bahan_baku(bb_path, update_tgl_bahan_baku)
                            else:
                                st.error(f"Gagal mengunduh file. Status code: {response.status_code}. Pastikan ID benar dan akses terbuka.")
                        except Exception as e:
                            st.error(f"Terjadi kesalahan saat mengunduh: {e}")

    # =========================================================================
    # TAB 1: TAMBAH DATA BARU
    # =========================================================================
    with tab_tambah:
        st.markdown("#### Tambah Data Harga Baru")
        with st.form("form_tambah_harga_bb", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                bahan_baku_baru = st.selectbox("Bahan Baku", daftar_bb_db_options, key="tambah_bahan_baku")
                majalah_opt = st.selectbox("Nama Majalah", ["-- Tambah Baru --"] + list_majalah, key="tambah_majalah_opt")
                majalah_baru = st.text_input("Ketik Nama Majalah (jika tambah baru)", key="tambah_majalah_baru")

                incoterm_opt = st.selectbox("Incoterm", ["-- Tambah Baru --"] + list_incoterm, key="tambah_incoterm_opt")
                incoterm_baru = st.text_input("Ketik Incoterm (jika tambah baru)", key="tambah_incoterm_baru")
            with c2:
                tanggal_terbit_baru = st.date_input("Tanggal Terbit", value=datetime.today(), key="tambah_tanggal")
                harga_min_baru = st.number_input("Harga Min (USD/MT)", min_value=0.0, step=0.5, format="%.2f", key="tambah_harga_min")
                harga_max_baru = st.number_input("Harga Max (USD/MT)", min_value=0.0, step=0.5, format="%.2f", key="tambah_harga_max")

            submit_tambah = st.form_submit_button("Simpan Data Baru", type="primary", icon=":material/save:")

            if submit_tambah:
                nama_majalah_clean = majalah_baru.strip() if majalah_opt == "-- Tambah Baru --" else majalah_opt
                incoterm_clean = incoterm_baru.strip() if incoterm_opt == "-- Tambah Baru --" else incoterm_opt

                if not nama_majalah_clean or not incoterm_clean:
                    st.error("Nama Majalah dan Incoterm wajib diisi.")
                elif harga_max_baru < harga_min_baru:
                    st.error("Harga Max tidak boleh lebih kecil dari Harga Min.")
                else:
                    try:
                        if _row_exists(engine, tanggal_terbit_baru, nama_majalah_clean, bahan_baku_baru, incoterm_clean):
                            st.error(
                                "Data dengan kombinasi Tanggal Terbit, Majalah, Bahan Baku, dan Incoterm ini "
                                "sudah ada. Gunakan tab 'Lihat / Edit / Hapus Data' untuk mengubahnya."
                            )
                        else:
                            _insert_row(
                                engine, tanggal_terbit_baru, nama_majalah_clean,
                                bahan_baku_baru, incoterm_clean, harga_min_baru, harga_max_baru
                            )
                            st.success("Data baru berhasil disimpan!")
                    except Exception as e:
                        st.error(f"Gagal menyimpan data: {e}")

    # =========================================================================
    # TAB 2: LIHAT / EDIT / HAPUS DATA
    # =========================================================================
    with tab_lihat_edit_hapus:
        st.markdown("#### Filter Data")
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            filter_bb = st.selectbox("Bahan Baku", ["Semua"] + daftar_bb_label, key="filter_bb_manajemen")
        with col_f2:
            filter_majalah = st.selectbox("Nama Majalah", ["Semua"] + list_majalah, key="filter_majalah_manajemen")
        with col_f3:
            default_start_date = (pd.Timestamp.today() - pd.DateOffset(months=3)).date()
            filter_start = st.date_input("Dari Tanggal", value=default_start_date, key="filter_start_manajemen")
        with col_f4:
            filter_end = st.date_input("Sampai Tanggal", value=None, key="filter_end_manajemen")

        try:
            df = _load_data(
                load_data,
                filter_bahan_baku=filter_bb,
                filter_majalah=filter_majalah if filter_majalah else None,
                filter_start=filter_start if filter_start else None,
                filter_end=filter_end if filter_end else None,
                limit=500
            )
        except Exception as e:
            st.error(f"Gagal memuat data: {e}")
            return

        if df.empty:
            st.info("Tidak ada data yang cocok dengan filter di atas.")
            return

        st.caption(f"Menampilkan {len(df)} baris (maksimal 500 baris terakhir sesuai filter).")

        # == Dialog konfirmasi hapus, jika ada baris yang dipilih untuk dihapus ==
        if '_bb_row_to_delete' in st.session_state:
            _dialog_confirm_delete(st.session_state['_bb_row_to_delete'])

        # == Tabel data dengan tombol Edit & Hapus per baris ==
        st.markdown("<br>", unsafe_allow_html=True)

        header_cols = st.columns([2, 2, 2, 1.5, 1.5, 1.5, 1, 1])
        headers = ["Tanggal Terbit", "Majalah", "Bahan Baku", "Incoterm", "Harga Min", "Harga Max", "", ""]
        for col, h in zip(header_cols, headers):
            col.markdown(f"**{h}**")

        st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)

        for idx, row in df.iterrows():
            row_key = f"{row['tanggal_terbit']}_{row['nama_majalah']}_{row['bahan_baku']}_{row['incoterm']}"
            is_editing = st.session_state.get('_bb_editing_row') == row_key

            if not is_editing:
                c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([2, 2, 2, 1.5, 1.5, 1.5, 1, 1])
                c1.write(str(row['tanggal_terbit']))
                c2.write(row['nama_majalah'])
                c3.write(row['bahan_baku'])
                c4.write(row['incoterm'])
                c5.write(f"{row['harga_min']:.2f}")
                c6.write(f"{row['harga_max']:.2f}")
                if c7.button("", icon=":material/edit:", key=f"edit_{idx}_{row_key}", help="Edit baris ini"):
                    st.session_state['_bb_editing_row'] = row_key
                    st.rerun()
                if c8.button("", icon=":material/delete:", key=f"del_{idx}_{row_key}", help="Hapus baris ini"):
                    st.session_state['_bb_row_to_delete'] = row.to_dict()
                    st.rerun()
            else:
                # == Form edit inline untuk baris ini ==
                with st.container(border=True):
                    st.markdown(f"**Edit Data:** {row['bahan_baku']} — {row['nama_majalah']} — {row['incoterm']} — {row['tanggal_terbit']}")
                    with st.form(f"form_edit_{row_key}"):
                        e1, e2 = st.columns(2)
                        with e1:
                            edit_bahan_baku = st.selectbox(
                                "Bahan Baku", daftar_bb_db_options,
                                index=daftar_bb_db_options.index(row['bahan_baku']) if row['bahan_baku'] in daftar_bb_db_options else 0,
                                key=f"edit_bb_{row_key}"
                            )
                            # Index selectbox diarahkan ke data eksisting (jika ada) + 1 (karena ada opsi -- Tambah Baru -- di awal)
                            idx_maj = list_majalah.index(row['nama_majalah']) + 1 if row['nama_majalah'] in list_majalah else 0
                            edit_majalah_opt = st.selectbox("Nama Majalah", ["-- Tambah Baru --"] + list_majalah, index=idx_maj, key=f"edit_maj_opt_{row_key}")
                            edit_majalah_baru = st.text_input("Ketik Majalah Baru", value=row['nama_majalah'] if idx_maj == 0 else "", key=f"edit_maj_baru_{row_key}")

                            idx_inc = list_incoterm.index(row['incoterm']) + 1 if row['incoterm'] in list_incoterm else 0
                            edit_incoterm_opt = st.selectbox("Incoterm", ["-- Tambah Baru --"] + list_incoterm, index=idx_inc, key=f"edit_inc_opt_{row_key}")
                            edit_incoterm_baru = st.text_input("Ketik Incoterm Baru", value=row['incoterm'] if idx_inc == 0 else "", key=f"edit_inc_baru_{row_key}")
                        with e2:
                            edit_tanggal = st.date_input("Tanggal Terbit", value=pd.to_datetime(row['tanggal_terbit']).date(), key=f"edit_tanggal_{row_key}")
                            edit_harga_min = st.number_input("Harga Min", min_value=0.0, step=0.5, format="%.2f", value=float(row['harga_min']), key=f"edit_hmin_{row_key}")
                            edit_harga_max = st.number_input("Harga Max", min_value=0.0, step=0.5, format="%.2f", value=float(row['harga_max']), key=f"edit_hmax_{row_key}")

                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            submit_edit = st.form_submit_button("Simpan Perubahan", type="primary", icon=":material/save:", use_container_width=True)
                        with col_cancel:
                            cancel_edit = st.form_submit_button("Batal", use_container_width=True)

                        if submit_edit:
                            edit_majalah_clean = edit_majalah_baru.strip() if edit_majalah_opt == "-- Tambah Baru --" else edit_majalah_opt
                            edit_incoterm_clean = edit_incoterm_baru.strip() if edit_incoterm_opt == "-- Tambah Baru --" else edit_incoterm_opt
                            if not edit_majalah_clean or not edit_incoterm_clean:
                                st.error("Nama Majalah dan Incoterm wajib diisi.")
                            elif edit_harga_max < edit_harga_min:
                                st.error("Harga Max tidak boleh lebih kecil dari Harga Min.")
                            else:
                                try:
                                    original_key = {
                                        "tanggal_terbit": row['tanggal_terbit'],
                                        "nama_majalah": row['nama_majalah'],
                                        "bahan_baku": row['bahan_baku'],
                                        "incoterm": row['incoterm'],
                                    }
                                    new_key = {
                                        "tanggal_terbit": edit_tanggal,
                                        "nama_majalah": edit_majalah_clean,
                                        "bahan_baku": edit_bahan_baku,
                                        "incoterm": edit_incoterm_clean,
                                    }
                                    key_changed = original_key != new_key
                                    if key_changed and _row_exists(engine, **new_key):
                                        st.error(
                                            "Kombinasi Tanggal Terbit, Majalah, Bahan Baku, dan Incoterm baru "
                                            "sudah ada di data lain. Tidak bisa disimpan."
                                        )
                                    else:
                                        _update_row(
                                            engine,
                                            original_key,
                                            {
                                                "tanggal_terbit": edit_tanggal,
                                                "nama_majalah": edit_majalah_clean,
                                                "bahan_baku": edit_bahan_baku,
                                                "incoterm": edit_incoterm_clean,
                                                "harga_min": edit_harga_min,
                                                "harga_max": edit_harga_max,
                                            }
                                        )
                                        st.session_state.pop('_bb_editing_row', None)
                                        st.session_state['_bb_manajemen_msg'] = ("success", "Data berhasil diperbarui.")
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"Gagal memperbarui data: {e}")

                        if cancel_edit:
                            st.session_state.pop('_bb_editing_row', None)
                            st.rerun()