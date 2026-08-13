"""
v_inklaring_manajemen.py - Halaman Manajemen Data Inklaring Barang Impor (Admin Only)

Halaman ini menggantikan tampilan "Detail" murni menjadi halaman manajemen data:
- Tab "Data Table": tabel editable (st.data_editor) untuk mengubah, menambah,
  atau menghapus baris, lalu disimpan ke database lewat tombol Save.
- Tab "Tambah Data Baru": form terstruktur untuk input satu dokumen PIB baru
  secara lengkap.

Kolom-kolom turunan/hasil rumus (No AJU, TOTAL, Lama Bongkar, BEBAS,
Keterangan Jalur, CHECK LIST, SLA, Score SLA, Kedatangan Kapal) selalu
read-only karena nilainya dihitung otomatis dari kolom lain, bukan disimpan
apa adanya ke database.

Primary key tabel `inklaring_impor` adalah kolom `aju_pib` (lihat constraint
ON CONFLICT (aju_pib) pada etl_inklaring.py). Simpan perubahan dilakukan per
baris:
- Baris yang datanya berubah -> UPDATE berdasarkan aju_pib.
- Baris baru (aju_pib belum ada di DB) -> INSERT.
- Baris yang dihapus dari editor -> DELETE berdasarkan aju_pib.
"""
import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime, date
from sqlalchemy import text

# Dipakai untuk menyalin baris baru (tab "Tambah Data Baru") ke Google Sheet
# sumber Inklaring, selain ke PostgreSQL. Kalau modul/kredensial ini belum
# tersedia di lingkungan tertentu, import dibiarkan gagal secara diam-diam di
# sini dan baru dicek ulang saat benar-benar dipakai (lihat pemanggilannya di
# tab Tambah Data Baru), supaya halaman ini tetap bisa jalan untuk fitur
# lain walau modul gdocs_export belum ter-setup.
try:
    import gdocs_export
except Exception:
    gdocs_export = None

# Dipakai untuk tab "Import dari PDF": mengekstrak field-field Inklaring dari
# 7 jenis dokumen PDF Bea Cukai. Sama seperti gdocs_export, import dibiarkan
# gagal secara diam-diam di sini dan baru dicek ulang saat tab tsb dipakai,
# supaya halaman ini tetap bisa jalan untuk fitur lain walau dependency OCR
# (pytesseract/Pillow) belum ter-install di lingkungan tertentu.
try:
    import pdf_extractor_inklaring
except Exception:
    pdf_extractor_inklaring = None


# ============================================================
# KONFIGURASI KOLOM
# ============================================================

# Kolom asli yang disimpan di database (bisa diedit langsung).
EDITABLE_DB_COLUMNS = [
    'tgl_pib', 'aju_pib', 'sap', 'ln', 'nama_kapal', 'tgl_eta',
    'quantity_mt', 'pemasok', 'pengirim', 'agent', 'komoditi', 'asal_negara',
    'port_of_load', 'hs_code', 'bea_masuk_rp', 'ppn_rp', 'pph_rp', 'bm_persen',
    'gudang_timbun', 'invoice', 'kurs', 'skep_bc',
    'start_bongkar', 'selesai_bongkar', 'ppjk', 'spjm', 'ambil_sampel',
    'no_pen_pib', 'tgl_no_pen_pib', 'no_sppb', 'tgl_sppb', 'status',
    'no_sptnp', 'tgl_sptnp', 'nilai_sptnp',
]

# Kolom turunan / hasil rumus, selalu read-only di editor.
DERIVED_COLUMNS = [
    'no_aju', 'total_rp', 'lama_bongkar_hari', 'bebas_hari',
    'keterangan_jalur', 'check_list', 'sla', 'score_sla',
    'kedatangan_kapal_hari',
]

DATE_DB_COLUMNS = [
    'tgl_pib', 'tgl_eta', 'start_bongkar', 'selesai_bongkar',
    'tgl_sppb', 'tgl_no_pen_pib', 'tgl_sptnp',
]

NUMERIC_DB_COLUMNS = [
    'quantity_mt', 'bea_masuk_rp', 'ppn_rp', 'pph_rp', 'bm_persen',
    'kurs', 'nilai_sptnp',
]

COLUMN_LABELS = {
    'tgl_pib': 'Tgl PIB',
    'aju_pib': 'AJU PIB',
    'no_aju': 'NO AJU',
    'sap': 'SAP',
    'ln': 'LN',
    'nama_kapal': 'NAMA KAPAL',
    'tgl_eta': 'Tgl ETA',
    'quantity_mt': 'QUANTITY (MT)',
    'pemasok': 'PEMASOK',
    'pengirim': 'PENGIRIM',
    'agent': 'AGENT',
    'komoditi': 'KOMODITI',
    'asal_negara': 'ASAL NEGARA',
    'port_of_load': 'Port of Load',
    'hs_code': 'HS',
    'bea_masuk_rp': 'Bea Masuk (Rp)',
    'ppn_rp': 'PPN',
    'pph_rp': 'PPH',
    'total_rp': 'TOTAL',
    'bm_persen': 'BM %',
    'gudang_timbun': 'GUDANG TIMBUN',
    'invoice': 'INVOICE',
    'kurs': 'Kurs',
    'skep_bc': 'SKEP BC',
    'start_bongkar': 'START BONGKAR',
    'selesai_bongkar': 'SELESAI BONGKAR',
    'lama_bongkar_hari': 'Lama Bongkar (Hari)',
    'ppjk': 'PPJK',
    'spjm': 'SPJM',
    'ambil_sampel': 'AMBIL SAMPEL',
    'no_pen_pib': 'No Pen PIB',
    'tgl_no_pen_pib': 'Tgl No Pen PIB',
    'no_sppb': 'No S P P B',
    'tgl_sppb': 'Tgl SPPB',
    'status': 'STATUS',
    'bebas_hari': 'BEBAS (Hari)',
    'no_sptnp': 'NO SPTNP',
    'tgl_sptnp': 'Tgl SPTNP',
    'nilai_sptnp': 'NILAI SPTNP',
    'keterangan_jalur': 'Keterangan Jalur',
    'check_list': 'CHECK LIST',
    'sla': 'SLA',
    'score_sla': 'Score SLA',
    'kedatangan_kapal_hari': 'Kedatangan Kapal (Hari)',
}

# Urutan tampilan penuh (kolom DB + kolom turunan) sesuai daftar yang diminta.
FULL_COLUMN_ORDER = [
    'tgl_pib', 'aju_pib', 'no_aju', 'sap', 'ln', 'nama_kapal', 'tgl_eta',
    'quantity_mt', 'pemasok', 'pengirim', 'agent', 'komoditi', 'asal_negara',
    'port_of_load', 'hs_code', 'bea_masuk_rp', 'ppn_rp', 'pph_rp', 'total_rp',
    'bm_persen', 'gudang_timbun', 'invoice', 'kurs', 'skep_bc',
    'start_bongkar', 'selesai_bongkar', 'lama_bongkar_hari', 'ppjk', 'spjm',
    'ambil_sampel', 'no_pen_pib', 'tgl_no_pen_pib', 'no_sppb', 'tgl_sppb',
    'status', 'bebas_hari', 'no_sptnp', 'tgl_sptnp', 'nilai_sptnp',
    'keterangan_jalur', 'check_list', 'sla', 'score_sla', 'kedatangan_kapal_hari',
]


def db_get_engine():
    """Engine untuk operasi tulis (insert/update/delete)."""
    from config_db import get_db_engine
    return get_db_engine()


# ============================================================
# KALKULASI KOLOM TURUNAN
# ============================================================

def hitung_kolom_turunan(df: pd.DataFrame) -> pd.DataFrame:
    """Menghitung seluruh kolom turunan dari kolom mentah database.
    df diasumsikan sudah memiliki kolom-kolom di EDITABLE_DB_COLUMNS.
    """
    df = df.copy()

    for col in EDITABLE_DB_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # Pastikan kolom tanggal bertipe datetime64 sebelum operasi .dt
    for col in DATE_DB_COLUMNS:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    # Pastikan kolom numerik bertipe numeric
    for col in NUMERIC_DB_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # No AJU = 6 digit terakhir dari AJU PIB
    df['no_aju'] = df['aju_pib'].astype(str).str.strip().str[-6:]
    df.loc[df['aju_pib'].isna(), 'no_aju'] = None

    # TOTAL = Bea Masuk + PPN + PPH
    df['total_rp'] = (
        df['bea_masuk_rp'].fillna(0) + df['ppn_rp'].fillna(0) + df['pph_rp'].fillna(0)
    )

    # Lama Bongkar (Hari) = Selesai Bongkar - Start Bongkar
    df['lama_bongkar_hari'] = (df['selesai_bongkar'] - df['start_bongkar']).dt.days

    # BEBAS (Hari) = Tgl SPPB - Selesai Bongkar
    df['bebas_hari'] = (df['tgl_sppb'] - df['selesai_bongkar']).dt.days

    # Keterangan Jalur = IF(SPJM kosong/0; HIJAU; MERAH)
    is_hijau_mask = df['spjm'].fillna('').astype(str).str.strip().isin(['', '0', '0.0', '-'])
    df['keterangan_jalur'] = is_hijau_mask.map({True: 'HIJAU', False: 'MERAH'})

    # CHECK LIST = IF(STATUS = "Done"; TRUE; FALSE)
    df['check_list'] = df['status'].astype(str).str.strip().str.lower() == 'done'

    # SLA = IF(KOMODITI = "SA"; 15; IF(Keterangan Jalur = "MERAH"; 8; 0))
    def hitung_sla(row):
        komoditi_val = str(row.get('komoditi', '')).strip().upper()
        if komoditi_val == 'SA':
            return 15
        if row.get('keterangan_jalur') == 'MERAH':
            return 8
        return 0
    df['sla'] = df.apply(hitung_sla, axis=1)

    # Score SLA = IF(BEBAS(Hari) = 0/NaN; "-"; IF(SLA >= BEBAS(Hari); 1; 0))
    def hitung_score_sla(row):
        bebas = row.get('bebas_hari')
        sla_val = row.get('sla')
        if pd.isna(bebas) or bebas == 0:
            return "-"
        return 1 if sla_val >= bebas else 0
    df['score_sla'] = df.apply(hitung_score_sla, axis=1)

    # Kedatangan Kapal (Hari) = Start Bongkar - Tgl PIB
    df['kedatangan_kapal_hari'] = (df['start_bongkar'] - df['tgl_pib']).dt.days

    return df


# ============================================================
# PENYIMPANAN KE DATABASE
# ============================================================

def _clean_value_for_db(val, is_date=False, is_numeric=False):
    """Normalisasi nilai dari data_editor sebelum dikirim ke SQL."""
    if val is None:
        return None
    if isinstance(val, float) and np.isnan(val):
        return None
    if isinstance(val, str) and val.strip() in ('', '-'):
        return None
    if is_date:
        if isinstance(val, (pd.Timestamp, datetime, date)):
            ts = pd.Timestamp(val)
            return None if pd.isna(ts) else ts.strftime('%Y-%m-%d')
        return None
    if is_numeric:
        try:
            f = float(val)
            return None if np.isnan(f) else f
        except (TypeError, ValueError):
            return None
    return val


def simpan_perubahan(df_edited: pd.DataFrame, df_original: pd.DataFrame):
    """Bandingkan df_edited dengan df_original (kunci = aju_pib) lalu
    lakukan INSERT/UPDATE/DELETE sesuai perbedaannya.
    Mengembalikan tuple (n_insert, n_update, n_delete).
    """
    engine = db_get_engine()

    orig_keys = set(df_original['aju_pib'].dropna().astype(str))
    edited_keys = set(df_edited['aju_pib'].dropna().astype(str))

    keys_to_delete = orig_keys - edited_keys
    keys_new = edited_keys - orig_keys
    keys_common = edited_keys & orig_keys

    n_insert, n_update, n_delete = 0, 0, 0

    df_orig_idx = df_original.set_index(df_original['aju_pib'].astype(str))
    df_edit_idx = df_edited.set_index(df_edited['aju_pib'].astype(str))

    with engine.begin() as conn:
        # --- DELETE ---
        for key in keys_to_delete:
            conn.execute(
                text("DELETE FROM inklaring_impor WHERE aju_pib = :aju_pib"),
                {"aju_pib": key}
            )
            n_delete += 1

        # --- INSERT baris baru ---
        for key in keys_new:
            row = df_edit_idx.loc[key]
            if isinstance(row, pd.DataFrame):  # duplikat aju_pib, ambil baris terakhir
                row = row.iloc[-1]
            values = {}
            for col in EDITABLE_DB_COLUMNS:
                values[col] = _clean_value_for_db(
                    row.get(col),
                    is_date=col in DATE_DB_COLUMNS,
                    is_numeric=col in NUMERIC_DB_COLUMNS,
                )
            cols_sql = ", ".join(values.keys())
            params_sql = ", ".join([f":{c}" for c in values.keys()])
            conn.execute(
                text(f"INSERT INTO inklaring_impor ({cols_sql}) VALUES ({params_sql})"),
                values
            )
            n_insert += 1

        # --- UPDATE baris yang berubah ---
        for key in keys_common:
            row_new = df_edit_idx.loc[key]
            row_old = df_orig_idx.loc[key]
            if isinstance(row_new, pd.DataFrame):
                row_new = row_new.iloc[-1]
            if isinstance(row_old, pd.DataFrame):
                row_old = row_old.iloc[-1]

            values = {}
            changed = False
            for col in EDITABLE_DB_COLUMNS:
                new_val = _clean_value_for_db(
                    row_new.get(col),
                    is_date=col in DATE_DB_COLUMNS,
                    is_numeric=col in NUMERIC_DB_COLUMNS,
                )
                old_val = _clean_value_for_db(
                    row_old.get(col),
                    is_date=col in DATE_DB_COLUMNS,
                    is_numeric=col in NUMERIC_DB_COLUMNS,
                )
                if new_val != old_val:
                    changed = True
                values[col] = new_val

            if not changed:
                continue

            set_clause = ", ".join([f"{c} = :{c}" for c in EDITABLE_DB_COLUMNS if c != 'aju_pib'])
            values['aju_pib_key'] = key
            conn.execute(
                text(f"UPDATE inklaring_impor SET {set_clause} WHERE aju_pib = :aju_pib_key"),
                values
            )
            n_update += 1

    return n_insert, n_update, n_delete


# ============================================================
# RENDER HALAMAN
# ============================================================

def render(load_data, date_from=None, date_to=None, **kwargs):
    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:60px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" fill="currentColor"
                 viewBox="0 0 16 16" style="margin-bottom:10px; margin-right:8px;">
                <path d="M9.293 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0
                         2-2V4.707A1 1 0 0 0 13.707 4L10 .293A1 1 0 0 0 9.293 0M9.5
                         3.5v-2l3 3h-2a1 1 0 0 1-1-1M4.5 9a.5.5 0 0 1 0-1h7a.5.5 0
                         0 1 0 1zM4 10.5a.5.5 0 0 1 .5-.5h7a.5.5 0 0 1 0 1h-7a.5.5
                         0 0 1-.5-.5m.5 2.5a.5.5 0 0 1 0-1h4a.5.5 0 0 1 0 1z"/>
            </svg>
            Manajemen Data Inklaring
        </h1>
    """, unsafe_allow_html=True)
    st.caption("Halaman ini khusus untuk Admin: ubah, tambah, atau hapus data dokumen PIB inklaring.")
    st.markdown("---")

    tab_table, tab_tambah, tab_import_pdf = st.tabs(["📋 Data Table", "➕ Tambah Data Baru", "📄 Import dari PDF"])

    # ================================================================
    # TAB 1: DATA TABLE (EDITABLE)
    # ================================================================
    with tab_table:
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:20px; font-weight: normal;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-search" viewBox="0 0 16 16" style="margin-bottom: 2px; margin-right: 4px;">
                    <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001q.044.06.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1 1 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0"/>
                </svg>
                Search (No AJU, SAP, Nama Kapal, Komoditi, Pemasok)
            </h1>
        """, unsafe_allow_html=True)

        search_term = st.text_input("Search", value="", placeholder="Ketik AJU PIB, Nomor SAP, nama kapal, atau komoditi...", label_visibility="collapsed")

        date_filter = ""
        if date_from and date_to:
            start_str = date_from.strftime('%Y-%m-%d')
            end_str = date_to.strftime('%Y-%m-%d')
            date_filter = f"WHERE tgl_eta >= '{start_str}' AND tgl_eta <= '{end_str}'"

        table_query = f"""
        SELECT {', '.join(EDITABLE_DB_COLUMNS)}
        FROM inklaring_impor
        {date_filter}
        ORDER BY tgl_eta DESC NULLS LAST
        """

        with st.spinner("Memuat data tabel inklaring..."):
            table_data_raw = load_data(table_query)

        if table_data_raw.empty:
            st.info("Tidak ada data inklaring yang ditemukan pada rentang tanggal ini.")
        else:
            if search_term:
                term = search_term.lower()
                mask = (
                    table_data_raw['aju_pib'].astype(str).str.lower().str.contains(term, na=False) |
                    table_data_raw['sap'].astype(str).str.lower().str.contains(term, na=False) |
                    table_data_raw['nama_kapal'].astype(str).str.lower().str.contains(term, na=False) |
                    table_data_raw['komoditi'].astype(str).str.lower().str.contains(term, na=False) |
                    table_data_raw['pemasok'].astype(str).str.lower().str.contains(term, na=False)
                )
                table_data_base = table_data_raw[mask].copy()
            else:
                table_data_base = table_data_raw.copy()

            if table_data_base.empty:
                st.info("Tidak ada data yang cocok dengan pencarian.")
            else:
                # Simpan salinan "original" (sebelum edit) di session_state supaya
                # bisa dibandingkan saat tombol Save ditekan, dan tidak berubah
                # setiap kali widget lain di halaman dipicu ulang (rerun).
                state_key = "inklaring_original_data"
                if state_key not in st.session_state:
                    st.session_state[state_key] = table_data_base.copy()

                df_original = st.session_state[state_key]

                # Hitung kolom turunan untuk ditampilkan (read-only)
                df_display = hitung_kolom_turunan(table_data_base)

                # Format tanggal jadi objek date murni supaya kompatibel dengan
                # st.column_config.DateColumn di data_editor
                for col in DATE_DB_COLUMNS:
                    df_display[col] = pd.to_datetime(df_display[col], errors='coerce').dt.date

                display_columns = [c for c in FULL_COLUMN_ORDER if c in df_display.columns]
                df_display = df_display[display_columns].rename(columns=COLUMN_LABELS)

                # Bangun column_config: kolom turunan & label yang sesuai jadi disabled
                column_config = {}
                for col in display_columns:
                    label = COLUMN_LABELS.get(col, col)
                    if col in DERIVED_COLUMNS:
                        if col == 'check_list':
                            column_config[label] = st.column_config.CheckboxColumn(label, disabled=True)
                        else:
                            column_config[label] = st.column_config.TextColumn(label, disabled=True)
                    elif col in DATE_DB_COLUMNS:
                        column_config[label] = st.column_config.DateColumn(label, format="YYYY-MM-DD")
                    elif col in NUMERIC_DB_COLUMNS:
                        column_config[label] = st.column_config.NumberColumn(label, format="%.2f")
                    elif col == 'aju_pib':
                        column_config[label] = st.column_config.TextColumn(label, help="Primary key — wajib unik, jangan dikosongkan")

                count_label = f"Menampilkan **{len(df_display):,}** baris dokumen impor"
                st.caption(count_label)
                st.caption("Kolom bertanda abu-abu (No AJU, TOTAL, Lama Bongkar, BEBAS, Keterangan Jalur, CHECK LIST, SLA, Score SLA, Kedatangan Kapal) dihitung otomatis dan tidak bisa diedit langsung.")

                edited_df = st.data_editor(
                    df_display,
                    use_container_width=True,
                    height=450,
                    num_rows="dynamic",
                    column_config=column_config,
                    key="inklaring_data_editor",
                )

                col_save, col_download, col_reset = st.columns([1, 1, 2])

                with col_save:
                    if st.button("💾 Save Perubahan", type="primary"):
                        # Balik label -> nama kolom DB, lalu buang kolom turunan
                        label_to_col = {v: k for k, v in COLUMN_LABELS.items()}
                        edited_db = edited_df.rename(columns=label_to_col)
                        edited_db = edited_db[[c for c in EDITABLE_DB_COLUMNS if c in edited_db.columns]]

                        # aju_pib wajib ada; buang baris yang aju_pib-nya kosong
                        # (baris baru kosong yang belum diisi user)
                        edited_db = edited_db[edited_db['aju_pib'].notna() & (edited_db['aju_pib'].astype(str).str.strip() != '')]

                        try:
                            with st.spinner("Menyimpan perubahan ke database..."):
                                n_ins, n_upd, n_del = simpan_perubahan(edited_db, df_original)
                            st.success(f"Berhasil disimpan — {n_ins} baris ditambahkan, {n_upd} baris diperbarui, {n_del} baris dihapus.")
                            # Reset cache original supaya sinkron dengan DB terbaru
                            del st.session_state[state_key]
                            if hasattr(st, "cache_data"):
                                st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal menyimpan perubahan: {e}")

                with col_download:
                    excel_buffer = io.BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        edited_df.to_excel(writer, index=False, sheet_name='Inklaring_Data')
                    excel_buffer.seek(0)
                    st.download_button(
                        label="Download XLSX",
                        icon=":material/download:",
                        data=excel_buffer,
                        file_name=f"inklaring_data_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

                with col_reset:
                    if st.button("↺ Batalkan perubahan yang belum disimpan"):
                        if state_key in st.session_state:
                            del st.session_state[state_key]
                        st.rerun()

    # ================================================================
    # FUNGSI BERSAMA: FORM TAMBAH DATA BARU
    # Dipakai baik di Tab 2 (form kosong / prefill dari sesi sebelumnya)
    # maupun di Tab 3 (form langsung tampil dengan prefill hasil ekstraksi
    # PDF, tanpa perlu pindah tab).
    # ================================================================
    def _render_form_tambah_data(prefill, form_key):
        if prefill:
            st.info(
                "📄 Form ini terisi otomatis dari hasil ekstraksi PDF. "
                "Periksa dan koreksi setiap field sebelum menyimpan -- terutama "
                "field yang bersumber dari OCR (Nama Kapal, Agent, Gudang Timbun, "
                "Start/Selesai Bongkar), karena OCR tidak selalu 100% akurat."
            )

        def _pf(key, default=None):
            """Ambil nilai prefill untuk key tertentu, fallback ke default."""
            val = prefill.get(key)
            return val if val is not None else default

        def _pf_str(key, default=""):
            """Ambil nilai prefill dan format sebagai string (untuk text_input),
            termasuk konversi date/float ke representasi teks yang wajar.
            Khusus 'invoice': ditampilkan sebagai angka bulat TANPA pemisah
            ribuan (mis. 3467200, bukan 3,467,200.00), karena field ini
            dimaksudkan untuk diisi nominal Rupiah polos."""
            val = prefill.get(key)
            if val is None:
                return default
            if key == 'invoice' and isinstance(val, (int, float)):
                return f"{val:.0f}"
            if isinstance(val, (date, datetime)):
                return val.strftime("%d-%m-%Y")
            if isinstance(val, float):
                return f"{val:,.2f}"
            return str(val)

        with st.form(form_key, clear_on_submit=True):
            c1, c2, c3 = st.columns(3)

            with c1:
                f_tgl_pib = st.date_input("Tgl PIB", value=_pf('tgl_pib'))
                f_aju_pib = st.text_input("AJU PIB *", value=_pf_str('aju_pib'), help="Wajib diisi, harus unik (primary key)")
                f_sap = st.text_input("SAP", value=_pf_str('sap'))
                f_ln = st.text_input("LN", value=_pf_str('ln'))
                f_nama_kapal = st.text_input("Nama Kapal", value=_pf_str('nama_kapal'))
                f_tgl_eta = st.date_input("Tgl ETA", value=_pf('tgl_eta'))
                f_quantity_mt = st.number_input("Quantity (MT)", value=float(_pf('quantity_mt', 0.0)), step=0.01, format="%.2f")
                f_pemasok = st.text_input("Pemasok", value=_pf_str('pemasok'))
                f_pengirim = st.text_input("Pengirim", value=_pf_str('pengirim'))
                f_agent = st.text_input("Agent", value=_pf_str('agent'))
                f_komoditi = st.text_input("Komoditi", value=_pf_str('komoditi'))
                f_asal_negara = st.text_input("Asal Negara", value=_pf_str('asal_negara'))

            with c2:
                f_port_of_load = st.text_input("Port of Load", value=_pf_str('port_of_load'))
                f_hs_code = st.text_input("HS", value=_pf_str('hs_code'))
                f_bea_masuk_rp = st.number_input("Bea Masuk (Rp)", value=float(_pf('bea_masuk_rp', 0.0)), step=1000.0, format="%.2f")
                f_ppn_rp = st.number_input("PPN (Rp)", value=float(_pf('ppn_rp', 0.0)), step=1000.0, format="%.2f")
                f_pph_rp = st.number_input("PPH (Rp)", value=float(_pf('pph_rp', 0.0)), step=1000.0, format="%.2f")
                f_bm_persen = st.number_input("BM %", value=float(_pf('bm_persen', 0.0)), step=0.1, format="%.2f")
                f_gudang_timbun = st.text_input("Gudang Timbun", value=_pf_str('gudang_timbun'))
                f_invoice = st.text_input("Invoice", value=_pf_str('invoice'))
                f_kurs = st.number_input("Kurs", value=float(_pf('kurs', 0.0)), step=1.0, format="%.2f")
                f_skep_bc = st.date_input("Skep BC", value=_pf('skep_bc'))
                f_start_bongkar = st.date_input("Start Bongkar", value=_pf('start_bongkar'))
                f_selesai_bongkar = st.date_input("Selesai Bongkar", value=_pf('selesai_bongkar'))

            with c3:
                f_ppjk = st.text_input("PPJK", value=_pf_str('ppjk'))
                f_spjm = st.date_input("SPJM", value=_pf('spjm'), help="Kosongkan jika Jalur Hijau; isi tanggal jika Jalur Merah")
                f_ambil_sampel = st.date_input("Ambil Sampel", value=_pf('ambil_sampel'))
                f_no_pen_pib = st.text_input("No Pen PIB", value=_pf_str('no_pen_pib'))
                f_tgl_no_pen_pib = st.date_input("Tgl No Pen PIB", value=_pf('tgl_no_pen_pib'))
                f_no_sppb = st.text_input("No SPPB", value=_pf_str('no_sppb'))
                f_tgl_sppb = st.date_input("Tgl SPPB", value=_pf('tgl_sppb'))
                f_status = st.text_input("Status", value=_pf_str('status'))
                f_no_sptnp = st.text_input("No SPTNP", value=_pf_str('no_sptnp'))
                f_tgl_sptnp = st.date_input("Tgl SPTNP", value=_pf('tgl_sptnp'))
                f_nilai_sptnp = st.number_input("Nilai SPTNP", value=float(_pf('nilai_sptnp', 0.0)), step=1000.0, format="%.2f")

            submitted = st.form_submit_button("💾 Simpan Data Baru", type="primary")

            if submitted:
                if not f_aju_pib or not f_aju_pib.strip():
                    st.error("AJU PIB wajib diisi karena merupakan primary key.")
                else:
                    # skep_bc, spjm, ambil_sampel adalah kolom TEKS di database
                    # (bukan DATE), tapi diinput lewat date_input di form untuk
                    # kenyamanan -- dikonversi balik ke string "DD-MM-YYYY" di
                    # sini sebelum disimpan. None (field dikosongkan) tetap None.
                    def _date_ke_str(val):
                        if val is None:
                            return None
                        return val.strftime("%d-%m-%Y")

                    new_row = {
                        'tgl_pib': f_tgl_pib, 'aju_pib': f_aju_pib.strip(), 'sap': f_sap or None,
                        'ln': f_ln or None, 'nama_kapal': f_nama_kapal or None, 'tgl_eta': f_tgl_eta,
                        'quantity_mt': f_quantity_mt, 'pemasok': f_pemasok or None,
                        'pengirim': f_pengirim or None, 'agent': f_agent or None,
                        'komoditi': f_komoditi or None, 'asal_negara': f_asal_negara or None,
                        'port_of_load': f_port_of_load or None, 'hs_code': f_hs_code or None,
                        'bea_masuk_rp': f_bea_masuk_rp, 'ppn_rp': f_ppn_rp, 'pph_rp': f_pph_rp,
                        'bm_persen': f_bm_persen, 'gudang_timbun': f_gudang_timbun or None,
                        'invoice': f_invoice or None, 'kurs': f_kurs, 'skep_bc': _date_ke_str(f_skep_bc),
                        'start_bongkar': f_start_bongkar, 'selesai_bongkar': f_selesai_bongkar,
                        'ppjk': f_ppjk or None, 'spjm': _date_ke_str(f_spjm),
                        'ambil_sampel': _date_ke_str(f_ambil_sampel), 'no_pen_pib': f_no_pen_pib or None,
                        'tgl_no_pen_pib': f_tgl_no_pen_pib, 'no_sppb': f_no_sppb or None,
                        'tgl_sppb': f_tgl_sppb, 'status': f_status or None,
                        'no_sptnp': f_no_sptnp or None, 'tgl_sptnp': f_tgl_sptnp,
                        'nilai_sptnp': f_nilai_sptnp,
                    }

                    values = {}
                    for col in EDITABLE_DB_COLUMNS:
                        values[col] = _clean_value_for_db(
                            new_row.get(col),
                            is_date=col in DATE_DB_COLUMNS,
                            is_numeric=col in NUMERIC_DB_COLUMNS,
                        )

                    insert_db_berhasil = False
                    try:
                        engine = db_get_engine()
                        with engine.begin() as conn:
                            existing = conn.execute(
                                text("SELECT 1 FROM inklaring_impor WHERE aju_pib = :aju_pib"),
                                {"aju_pib": values['aju_pib']}
                            ).fetchone()
                            if existing:
                                st.error(f"AJU PIB '{values['aju_pib']}' sudah ada di database. Gunakan tab Data Table untuk mengedit data yang sudah ada.")
                            else:
                                cols_sql = ", ".join(values.keys())
                                params_sql = ", ".join([f":{c}" for c in values.keys()])
                                conn.execute(
                                    text(f"INSERT INTO inklaring_impor ({cols_sql}) VALUES ({params_sql})"),
                                    values
                                )
                                insert_db_berhasil = True
                                st.success(f"Data baru dengan AJU PIB '{values['aju_pib']}' berhasil disimpan ke database.")
                                if "inklaring_original_data" in st.session_state:
                                    del st.session_state["inklaring_original_data"]
                                # Bersihkan prefill hasil ekstraksi PDF (kalau ada),
                                # supaya form kosong lagi untuk entri berikutnya.
                                if "inklaring_pdf_extracted" in st.session_state:
                                    del st.session_state["inklaring_pdf_extracted"]
                    except Exception as e:
                        st.error(f"Gagal menyimpan data baru: {e}")

                    # Salin baris yang sama ke Google Sheet sumber Inklaring, HANYA
                    # jika data sudah berhasil masuk PostgreSQL. Kegagalan di
                    # langkah ini TIDAK membatalkan data yang sudah tersimpan di
                    # database -- cukup ditampilkan sebagai peringatan terpisah,
                    # supaya admin tahu perlu menambahkan barisnya secara manual
                    # ke spreadsheet.
                    if insert_db_berhasil:
                        if gdocs_export is None or not hasattr(gdocs_export, "append_row_inklaring_ke_sheet"):
                            st.warning(
                                "Data tersimpan di database, tetapi belum bisa disalin otomatis ke "
                                "Google Sheet karena modul gdocs_export belum mendukung fitur ini "
                                "(lihat gdocs_export_PATCH.py). Tambahkan baris ini secara manual ke sheet."
                            )
                        else:
                            try:
                                with st.spinner("Menyalin data ke Google Sheet..."):
                                    gdocs_export.append_row_inklaring_ke_sheet(values)
                                st.success("Data juga berhasil disalin ke Google Sheet '2026 - BB/BD/BP'.")
                            except Exception as e:
                                st.warning(
                                    f"Data tersimpan di database, tetapi gagal disalin ke Google Sheet: {e}. "
                                    "Tambahkan baris ini secara manual ke sheet jika diperlukan."
                                )

    # ================================================================
    # TAB 2: TAMBAH DATA BARU (FORM)
    # ================================================================
    with tab_tambah:
        st.markdown("#### Input Dokumen PIB Baru")
        st.caption("Isi seluruh data dokumen PIB inklaring baru di bawah ini. Kolom turunan (No AJU, TOTAL, dsb.) akan otomatis dihitung ulang oleh sistem.")

        # Nilai pre-fill dari hasil ekstraksi PDF (tab "Import dari PDF"),
        # kalau user memilih untuk membuka form di sini alih-alih langsung
        # dari tab Import (mis. reload halaman). Dibersihkan otomatis setelah
        # submit sukses (lihat _render_form_tambah_data).
        prefill_tab2 = st.session_state.get('inklaring_pdf_extracted', {})
        _render_form_tambah_data(prefill_tab2, form_key="form_tambah_inklaring")

    # ================================================================
    # TAB 3: IMPORT DARI PDF
    # ================================================================
    with tab_import_pdf:
        st.markdown("#### Ekstrak Data dari 7 Dokumen PDF")
        st.caption(
            "Upload ketujuh dokumen di bawah untuk 1 dokumen PIB. Sistem akan "
            "membaca nilai-nilai yang relevan secara otomatis (sebagian lewat OCR "
            "untuk dokumen hasil scan), lalu langsung menampilkan formnya di bawah "
            "-- hasil ekstraksi WAJIB diperiksa dan dikoreksi manual sebelum "
            "disimpan, karena pembacaan otomatis (terutama OCR) tidak selalu "
            "100% akurat."
        )

        if pdf_extractor_inklaring is None:
            st.error(
                "Modul pdf_extractor_inklaring tidak tersedia di lingkungan ini. "
                "Pastikan file pdf_extractor_inklaring.py sudah ada di folder yang sama "
                "dengan v_inklaring_detail.py, dan dependency pdfplumber, pytesseract, "
                "serta Pillow sudah terinstall."
            )
        else:
            st.markdown("##### Upload Dokumen")
            col_up1, col_up2 = st.columns(2)

            with col_up1:
                file_pib = st.file_uploader(
                    "1. PIB Nopen", type=["pdf"], key="upload_pib_nopen",
                    help="Sumber: AJU PIB, Tgl PIB, Pemasok, Pengirim, Komoditi, Asal Negara, "
                         "Port of Load, HS, Bea Masuk, PPN, PPH, BM%, Invoice, Kurs, No/Tgl Pen PIB"
                )
                file_inward = st.file_uploader(
                    "2. INWARD (BC 1.1)", type=["pdf"], key="upload_inward",
                    help="Sumber: Nama Kapal (dibaca lewat OCR)"
                )
                file_laporan_penimbunan = st.file_uploader(
                    "3. Laporan Penimbunan MV", type=["pdf"], key="upload_laporan_penimbunan",
                    help="Sumber: Agent, Gudang Timbun, Start/Selesai Bongkar (dibaca lewat OCR)"
                )
                file_spjm = st.file_uploader(
                    "4. SPJM", type=["pdf"], key="upload_spjm",
                    help="Sumber: SPJM (tanggal penerbitan surat)"
                )

            with col_up2:
                file_skep = st.file_uploader(
                    "5. SKEP", type=["pdf"], key="upload_skep",
                    help="Sumber: SKEP BC (tanggal pojok kanan atas)"
                )
                file_sppb = st.file_uploader(
                    "6. SPPB", type=["pdf"], key="upload_sppb",
                    help="Sumber: No/Tgl SPPB, Tgl ETA (pendekatan), Quantity (MT)"
                )
                file_sptnp = st.file_uploader(
                    "7. SPTNP", type=["pdf"], key="upload_sptnp",
                    help="Sumber: No/Tgl SPTNP, Nilai SPTNP"
                )

            semua_file = {
                'pib_nopen': file_pib,
                'inward': file_inward,
                'laporan_penimbunan': file_laporan_penimbunan,
                'spjm': file_spjm,
                'skep': file_skep,
                'sppb': file_sppb,
                'sptnp': file_sptnp,
            }
            jumlah_terupload = sum(1 for f in semua_file.values() if f is not None)
            st.caption(f"Terupload: {jumlah_terupload}/7 dokumen")

            tombol_disabled = jumlah_terupload < 7
            if st.button(
                "🔍 Ekstrak Data dari PDF",
                type="primary",
                disabled=tombol_disabled,
                help="Upload ketujuh dokumen terlebih dahulu" if tombol_disabled else None,
            ):
                file_bytes_dict = {
                    nama: f.getvalue() for nama, f in semua_file.items() if f is not None
                }
                with st.spinner("Membaca dokumen PDF (proses OCR bisa memakan waktu beberapa detik)..."):
                    hasil_ekstraksi, errors_ekstraksi = pdf_extractor_inklaring.extract_all(file_bytes_dict)

                if errors_ekstraksi:
                    for nama_dok, pesan_error in errors_ekstraksi.items():
                        st.warning(f"Gagal memproses dokumen '{nama_dok}': {pesan_error}")

                if hasil_ekstraksi:
                    st.session_state['inklaring_pdf_extracted'] = hasil_ekstraksi
                    st.success(f"Berhasil mengekstrak {len(hasil_ekstraksi)} field. Periksa dan koreksi form di bawah, lalu simpan.")
                    with st.expander("Lihat hasil ekstraksi mentah"):
                        for k, v in sorted(hasil_ekstraksi.items()):
                            st.write(f"**{COLUMN_LABELS.get(k, k)}**: {v}")
                else:
                    st.error("Tidak ada field yang berhasil diekstrak dari dokumen yang diupload.")

            # Form langsung ditampilkan di tab yang sama begitu ada hasil
            # ekstraksi tersimpan di session_state -- tidak perlu pindah tab.
            # Dibaca dari session_state (bukan variabel lokal hasil_ekstraksi)
            # supaya form tetap tampil pada rerun berikutnya juga (mis. saat
            # user mengetik di salah satu field form, Streamlit rerun ulang
            # seluruh script dari atas, dan blok "if st.button(...)" di atas
            # tidak akan tereksekusi lagi karena tombolnya tidak diklik ulang).
            prefill_tab3 = st.session_state.get('inklaring_pdf_extracted', {})
            if prefill_tab3:
                st.markdown("---")
                st.markdown("#### Periksa & Simpan Data")
                _render_form_tambah_data(prefill_tab3, form_key="form_tambah_inklaring_dari_pdf")