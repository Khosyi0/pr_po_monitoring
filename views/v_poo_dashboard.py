"""
v_poo_monitoring.py - Halaman "Monitoring PO Outstanding"

3 tab:
  1. Dashboard      -> KPI cards (bergaya sama seperti Executive Summary) + chart
                       breakdown per klasifikasi keterlambatan & per Bagian
  2. Data ALL       -> tabel view (read-only) dari po_all_raw, seluruh data mentah
                       hasil upload (termasuk yang sudah Clear -- untuk keperluan audit)
  3. Perlu Email    -> tabel view (read-only) dari po_outstanding, hasil filter otomatis
                       (yang juga dipakai halaman "PO Outstanding - Reminder Email")

Upload data mentah (sheet ALL bulanan) TIDAK ada di halaman ini -- dilakukan
di halaman "Manajemen Data" sebagai Modul ETL "PO Outstanding (ALL)".
Halaman ini murni untuk MELIHAT hasilnya.
"""

import streamlit as st
import pandas as pd
import io
import plotly.graph_objects as go
from datetime import datetime


# =============================================================================
# CSS: kartu KPI, mengikuti gaya persis v_summary.py (Executive Summary)
# =============================================================================
POO_DASHBOARD_CSS = """
<style>
.poo-card {
    border-radius: 12px !important;
    background-color: var(--secondary-background-color) !important;
    background-image: linear-gradient(rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.08)) !important;
    border: 1px solid rgba(128, 128, 128, 0.25) !important;
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08) !important;
    border-left-width: 6px !important;
    border-left-style: solid !important;
    border-left-color: var(--text-color) !important;
    display: flex;
    align-items: flex-start;
    gap: 14px;
    min-height: 120px !important;
    height: 100%;
    padding: 18px 16px 14px 16px;
    margin-bottom: 12px;
}
.poo-card.border-green  { border-left-color: #09ab3b !important; }
.poo-card.border-red    { border-left-color: #e03c3c !important; }
.poo-card.border-orange { border-left-color: #f0a500 !important; }
.poo-card.border-blue   { border-left-color: #1f77b4 !important; }
.poo-card.border-gray   { border-left-color: #888888 !important; }

.poo-icon {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    border-radius: 10px;
    background: rgba(128, 128, 128, 0.1) !important;
    color: var(--text-color) !important;
}
.poo-body { flex: 1; min-width: 0; }
.poo-label {
    font-size: 12.5px;
    margin: 0 0 6px 0 !important;
    line-height: 1.3;
    font-weight: 500;
    color: var(--text-color) !important;
    opacity: 0.75;
}
.poo-value {
    font-size: 1.9rem !important;
    font-weight: 600 !important;
    margin: 0 !important;
    line-height: 1.1 !important;
    color: var(--text-color) !important;
    white-space: normal !important;
    word-wrap: break-word !important;
    display: block !important;
}
.poo-value-small { font-size: 1.4rem !important; }

.poo-row-label {
    font-size: 14px; font-weight: 700; letter-spacing: 0.04em;
    text-transform: uppercase; color: var(--text-color); margin: 18px 0 8px 4px;
}

/* Posisi tombol popover di dalam kartu KPI (mengikuti pola v_sips_dashboard.py) */
div[data-testid="stHorizontalBlock"] > div {
    position: relative;
}
div[data-testid="stPopover"] {
    position: absolute;
    top: 10px;
    right: 10px;
    width: 40px;
    z-index: 10;
}
</style>
"""

_ICONS = {
    "inventory":    "M20 2H4c-1.1 0-2 .9-2 2v3.01c0 .72.39 1.34 1 1.69V20c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V8.7c.61-.35 1-.97 1-1.69V4c0-1.1-.9-2-2-2m-5 12H9v-2h6zm5-6H4V4h16z",
    "check_circle": "M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16M10.97 4.97a.235.235 0 0 0-.02.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-1.071-1.05",
    "hourglass":    "M2 1.5A1.5 1.5 0 0 1 3.5 0h9A1.5 1.5 0 0 1 14 1.5c0 .823-.174 1.605-.489 2.303-.317.703-.777 1.31-1.331 1.744-.552.433-1.196.703-1.855.79A2.7 2.7 0 0 1 10.5 6.5c0 .13.01.257.028.379.615.099 1.203.316 1.727.641.554.343.99.782 1.331 1.286.34.502.489 1.052.489 1.694h-1c0-.35-.096-.681-.31-1.003-.212-.32-.523-.62-.914-.862a3 3 0 0 0-1.13-.454A1.5 1.5 0 0 1 9.5 8h-3a1.5 1.5 0 0 1-1.231.681 3 3 0 0 0-1.13.454c-.391.243-.702.542-.914.862-.214.322-.31.652-.31 1.003h-1c0-.642.15-1.192.489-1.694.34-.504.777-.943 1.331-1.286a4.9 4.9 0 0 1 1.727-.64A2.7 2.7 0 0 1 5.5 6.5c0-.13-.01-.257-.028-.379a4.9 4.9 0 0 1-1.727-.641c-.554-.343-.99-.782-1.331-1.286C2.174 3.605 2 2.823 2 1.5",
    "mail":         "M0 4a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2zm2-1a1 1 0 0 0-1 1v.217l7 4.2 7-4.2V4a1 1 0 0 0-1-1zm13 2.383-4.708 2.825L15 11.105zm-.034 6.876-5.64-3.383L8 9.583l-1.326-.795-5.64 3.383A1 1 0 0 0 2 13h12a1 1 0 0 0 .966-.741M1 11.105l4.708-2.897L1 5.383z",
    "send":         "M15.964.686a.5.5 0 0 0-.65-.65L.767 5.855H.766l-.452.18a.5.5 0 0 0-.082.887l.41.26.001.002 4.995 3.178 3.178 4.995.002.002.26.41a.5.5 0 0 0 .886-.083zm-1.833 1.89L6.637 10.07l-.215-.338a.5.5 0 0 0-.154-.154l-.338-.215 7.494-7.494 1.178-.471z",
    "reply":        "M9.5 3a.5.5 0 0 1 0 1V3zm0 9v.5a.5.5 0 0 0 .5-.5h-.5m-3-9H2v1h4.5zM2 3H1.5A.5.5 0 0 1 2 2.5zm0 9h-.5a.5.5 0 0 1 .5-.5zM12 5.5a5.5 5.5 0 0 1-5.5 5.5v1a6.5 6.5 0 0 0 6.5-6.5zM6.5 11A5.5 5.5 0 0 1 1 5.5H0A6.5 6.5 0 0 0 6.5 12zM1 5.5A5.5 5.5 0 0 1 6.5 0v-1A6.5 6.5 0 0 0 0 5.5z",
    "alert":        "M8.982 1.566a1.13 1.13 0 0 0-1.964 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.437-.99.98-1.767zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5m.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2",
    "clock":        "M8 3.5a.5.5 0 0 0-1 0V9a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0 0 .496-.868L8 8.71zM8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16m7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0",
}


def _svg(path_d, size=32):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'fill="currentColor" viewBox="0 0 16 16"><path d="{path_d}"/></svg>'
    )


def _card(icon_key, label, value, border="border-gray", small=False):
    value_cls = "poo-value poo-value-small" if small else "poo-value"
    icon_d = _ICONS.get(icon_key, _ICONS["inventory"])
    return f"""<div class="poo-card {border}">
    <div class="poo-icon">{_svg(icon_d, 28)}</div>
    <div class="poo-body">
        <p class="poo-label">{label}</p>
        <p class="{value_cls}">{value}</p>
    </div>
</div>"""


def _row_label(text):
    st.markdown(f'<div class="poo-row-label">{text}</div>', unsafe_allow_html=True)


def _fmt(n):
    return f"{int(n):,}".replace(",", ".")


def _rapikan_tanggal(df, kolom_list):
    for col in kolom_list:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%d-%m-%Y')
    return df


def _tombol_unduh(df, nama_file, key):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=nama_file[:30])
    st.download_button(
        label=f"Unduh Data yang Ditampilkan (.xlsx)",
        data=buffer.getvalue(),
        file_name=f"{nama_file}_{datetime.today().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        icon=":material/download:",
        key=key,
    )


# =============================================================================
# TAB 1: DASHBOARD (KPI cards bergaya + chart Plotly berwarna)
# =============================================================================

def _tab_dashboard(load_data):
    st.markdown(POO_DASHBOARD_CSS, unsafe_allow_html=True)

    if load_data is None:
        st.error("Koneksi data tidak tersedia (load_data tidak ditemukan).")
        return

    query = """
        SELECT
            r.purchasing_document,
            r.item,
            r.status_email,
            r.status_jawaban,
            r.bagian,
            r.delivery_date,
            (CURRENT_DATE - r.delivery_date)::INTEGER AS pending_time,
            CASE WHEN c.purchasing_document IS NOT NULL THEN TRUE ELSE FALSE END AS sudah_clear
        FROM po_all_raw r
        LEFT JOIN po_clear_history c
            ON r.purchasing_document = c.purchasing_document
           AND r.item = c.item
    """

    try:
        df = load_data(query)
    except Exception as e:
        st.warning(
            ":material/warning: Data belum tersedia (kemungkinan belum ada upload). "
            "Silakan upload sheet ALL melalui halaman **Manajemen Data** "
            "(Modul ETL: PO Outstanding (ALL)) terlebih dahulu.\n\n"
            f"Detail teknis: {e}"
        )
        return

    if df.empty:
        st.info(
            "Belum ada data PO Outstanding. Silakan upload sheet ALL melalui halaman "
            "**Manajemen Data** (Modul ETL: PO Outstanding (ALL)) terlebih dahulu."
        )
        return

    # -------------------------------------------------------------------
    # Klasifikasi keterlambatan untuk SEMUA baris (bukan cuma yang lolos
    # filter Perlu Email), supaya dashboard menunjukkan gambaran utuh
    # -------------------------------------------------------------------
    urutan_klasifikasi = ["0-7 Hari", "8-14 Hari", "15-30 Hari", "31-50 Hari", "51-90 Hari", ">90 Hari"]
    warna_klasifikasi = {
        "0-7 Hari":   "#09ab3b",
        "8-14 Hari":  "#8bc34a",
        "15-30 Hari": "#f0d500",
        "31-50 Hari": "#f0a500",
        "51-90 Hari": "#e07b39",
        ">90 Hari":   "#e03c3c",
    }

    def _klasifikasi(hari):
        if pd.isna(hari):
            return None
        if hari <= 7:
            return "0-7 Hari"
        elif hari <= 14:
            return "8-14 Hari"
        elif hari <= 30:
            return "15-30 Hari"
        elif hari <= 50:
            return "31-50 Hari"
        elif hari <= 90:
            return "51-90 Hari"
        else:
            return ">90 Hari"

    df["klasifikasi"] = df["pending_time"].apply(_klasifikasi)

    df_belum_clear = df[~df["sudah_clear"]]
    df_clear = df[df["sudah_clear"]]

    total_item = len(df)
    total_clear = len(df_clear)
    total_belum_clear = len(df_belum_clear)

    mask_perlu_email = (
        (df_belum_clear["pending_time"] > 7)
        & (df_belum_clear["status_jawaban"] != "Sudah Ada Jawaban")
    )
    total_perlu_remind = mask_perlu_email.sum()

    total_sudah_email = (df["status_email"] == "Sudah di-Email").sum()
    total_belum_email = (df_belum_clear["status_email"] != "Sudah di-Email").sum()

    total_sudah_jawab = (df["status_jawaban"] == "Sudah Ada Jawaban").sum()
    total_belum_jawab = (df_belum_clear["status_jawaban"] == "Belum Ada Jawaban").sum()
    total_tidak_terkirim = (df_belum_clear["status_jawaban"] == "Tidak Dapat Terkirim").sum()

    jumlah_per_klas = df_belum_clear["klasifikasi"].value_counts().reindex(urutan_klasifikasi, fill_value=0)

    _row_label("Item PO")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(_card("inventory", "Total Item PO (Semua)", _fmt(total_item), "border-blue"), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Lihat Formula"):
            st.info(
                "**Total Item PO (Semua)**: Jumlah seluruh baris PO+Item yang pernah "
                "tercatat di database (tabel `po_all_raw`), termasuk yang sudah berstatus "
                "Clear maupun yang masih outstanding.\n\n"
                "**Formula:**\n```\nTotal Item PO = COUNT(*) dari po_all_raw\n```"
            )
    with c2:
        st.markdown(_card("check_circle", "Sudah Clear", _fmt(total_clear), "border-green"), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Lihat Formula"):
            st.info(
                "**Sudah Clear**: Jumlah PO+Item yang tercatat permanen di "
                "`po_clear_history` -- yaitu PO+Item yang pernah terdeteksi memenuhi salah "
                "satu kondisi Clear (Keterangan/Rencana Kirim terisi, atau Status Jawaban "
                "= 'Sudah Ada Jawaban'). Sekali tercatat Clear, PO+Item ini tidak akan "
                "pernah dihitung lagi sebagai outstanding di upload bulan berikutnya."
            )
    with c3:
        st.markdown(_card("hourglass", "Belum Clear (Outstanding)", _fmt(total_belum_clear), "border-orange"), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Lihat Formula"):
            st.info(
                "**Belum Clear (Outstanding)**: Jumlah PO+Item yang belum tercatat di "
                "`po_clear_history` -- artinya item ini masih aktif dipantau.\n\n"
                "**Formula:**\n```\nBelum Clear = Total Item PO - Sudah Clear\n```"
            )

    st.caption("Breakdown Item PO Belum Clear berdasarkan lama keterlambatan:")
    cols_klas = st.columns(len(urutan_klasifikasi))
    _border_by_klas = {
        "0-7 Hari": "border-green", "8-14 Hari": "border-green",
        "15-30 Hari": "border-orange", "31-50 Hari": "border-orange",
        "51-90 Hari": "border-red", ">90 Hari": "border-red",
    }
    for col, label in zip(cols_klas, urutan_klasifikasi):
        with col:
            st.markdown(
                _card("clock", label, _fmt(jumlah_per_klas[label]), _border_by_klas[label], small=True),
                unsafe_allow_html=True
            )

    _row_label("Remind / Email")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(_card("mail", "Perlu Di-Remind", _fmt(total_perlu_remind), "border-red"), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Lihat Formula"):
            st.info(
                "**Perlu Di-Remind**: Dari PO+Item yang Belum Clear, dihitung yang "
                "keterlambatannya lebih dari 7 hari DAN belum ada jawaban 'Sudah Ada "
                "Jawaban' dari vendor.\n\n"
                "**Formula:**\n```\nPerlu Di-Remind = COUNT(Belum Clear\n"
                "  WHERE pending_time > 7\n"
                "  AND status_jawaban != 'Sudah Ada Jawaban')\n```\n\n"
                "Catatan: angka ini tidak mensyaratkan alamat email vendor terisi "
                "(berbeda dari tab **Perlu Email**, yang juga mensyaratkan email tersedia)."
            )
    with c2:
        st.markdown(_card("send", "Sudah Di-Email", _fmt(total_sudah_email), "border-green"), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Lihat Formula"):
            st.info(
                "**Sudah Di-Email**: Dihitung dari SELURUH PO+Item (baik yang sudah "
                "Clear maupun yang masih outstanding), berapa yang kolom **Status Email** "
                "di sheet ALL sudah bernilai 'Sudah di-Email'.\n\n"
                "**Formula:**\n```\nSudah Di-Email = COUNT(SEMUA data\n"
                "  WHERE status_email = 'Sudah di-Email')\n```\n\n"
                "Catatan: berbeda dari kartu 'Belum Di-Email' di sebelahnya yang hanya "
                "menghitung dari PO+Item yang masih Belum Clear, kartu ini sengaja "
                "menghitung dari seluruh data supaya mencerminkan total riwayat email "
                "yang sudah pernah dikirim, termasuk yang PO-nya sudah tuntas (Clear)."
            )
    with c3:
        st.markdown(_card("send", "Belum Di-Email", _fmt(total_belum_email), "border-orange"), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Lihat Formula"):
            st.info(
                "**Belum Di-Email**: Dari PO+Item yang Belum Clear (masih perlu "
                "ditindaklanjuti), dihitung yang kolom **Status Email** BUKAN 'Sudah "
                "di-Email' (termasuk kosong atau nilai lain).\n\n"
                "**Formula:**\n```\nBelum Di-Email = COUNT(Belum Clear\n"
                "  WHERE status_email != 'Sudah di-Email')\n```"
            )

    _row_label("Balasan Vendor")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(_card("reply", "Sudah Ada Jawaban", _fmt(total_sudah_jawab), "border-green"), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Lihat Formula"):
            st.info(
                "**Sudah Ada Jawaban**: Dihitung dari SELURUH PO+Item (baik yang sudah "
                "Clear maupun yang masih outstanding), berapa yang **Status Jawaban** = "
                "'Sudah Ada Jawaban'.\n\n"
                "**Formula:**\n```\nSudah Ada Jawaban = COUNT(SEMUA data\n"
                "  WHERE status_jawaban = 'Sudah Ada Jawaban')\n```\n\n"
                "Catatan: berbeda dari 2 kartu di sebelahnya (Belum Ada Jawaban, Tidak "
                "Dapat Terkirim) yang hanya menghitung dari PO+Item yang masih Belum "
                "Clear, kartu ini sengaja menghitung dari seluruh data -- karena begitu "
                "vendor menjawab, PO+Item itu langsung tercatat Clear dan tidak akan "
                "muncul lagi di kelompok Belum Clear."
            )
    with c2:
        st.markdown(_card("reply", "Belum Ada Jawaban", _fmt(total_belum_jawab), "border-orange"), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Lihat Formula"):
            st.info(
                "**Belum Ada Jawaban**: Dari PO+Item yang Belum Clear, dihitung yang "
                "**Status Jawaban** = 'Belum Ada Jawaban'."
            )
    with c3:
        st.markdown(_card("alert", "Tidak Dapat Terkirim", _fmt(total_tidak_terkirim), "border-red"), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Lihat Formula"):
            st.info(
                "**Tidak Dapat Terkirim**: Dari PO+Item yang Belum Clear, dihitung yang "
                "**Status Jawaban** = 'Tidak Dapat Terkirim' (misal karena alamat email "
                "vendor tidak valid/bounce). Untuk kriteria filter 'Perlu Email', status "
                "ini diperlakukan sama seperti 'Belum Ada Jawaban'."
            )

    st.markdown("<hr style='margin: 24px 0 8px 0; border-color: rgba(128,128,128,0.2);'>", unsafe_allow_html=True)

    col_chart1, col_chart2 = st.columns(2, gap="large")

    with col_chart1:
        st.markdown("#### :material/bar_chart: Item PO Belum Clear per Klasifikasi Keterlambatan")
        fig1 = go.Figure()
        fig1.add_trace(go.Bar(
            x=urutan_klasifikasi,
            y=[jumlah_per_klas[k] for k in urutan_klasifikasi],
            marker_color=[warna_klasifikasi[k] for k in urutan_klasifikasi],
            text=[jumlah_per_klas[k] for k in urutan_klasifikasi],
            textposition='outside',
        ))
        fig1.update_layout(
            height=350,
            xaxis_title='',
            yaxis_title='Jumlah Item PO',
            margin=dict(t=20, b=10, l=10, r=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col_chart2:
        st.markdown("#### :material/apartment: Item PO Belum Clear per Bagian")

        df_bagian = df_belum_clear.copy()
        df_bagian["bagian"] = df_bagian["bagian"].fillna("(Tidak Ada Bagian)")
        jumlah_per_bagian = df_bagian.groupby("bagian").size().sort_values(ascending=False)

        if jumlah_per_bagian.empty:
            st.info("Tidak ada data untuk ditampilkan.")
        else:
            palet_bagian = ["#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd", "#e03c3c", "#17becf", "#f0d500"]
            warna_bar = [palet_bagian[i % len(palet_bagian)] for i in range(len(jumlah_per_bagian))]

            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=jumlah_per_bagian.index.tolist(),
                y=jumlah_per_bagian.values.tolist(),
                marker_color=warna_bar,
                text=jumlah_per_bagian.values.tolist(),
                textposition='outside',
            ))
            fig2.update_layout(
                height=350,
                xaxis_title='',
                yaxis_title='Jumlah Item PO',
                margin=dict(t=20, b=10, l=10, r=10),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                showlegend=False,
            )
            st.plotly_chart(fig2, use_container_width=True)


# =============================================================================
# TAB 2: DATA ALL (dari po_all_raw -- data mentah apa adanya, termasuk Clear)
# =============================================================================

def _tab_data_all(load_data):
    st.markdown(
        "<p style='font-size:14px; opacity:0.7; margin-top:4px; margin-bottom:20px;'>"
        "Menampilkan seluruh data mentah PO Outstanding (sheet <b>ALL</b>) apa adanya dari "
        "database, termasuk PO+Item yang sudah berstatus <b>Clear</b>. Data ini bertambah "
        "setiap kali sheet ALL bulan baru diupload -- PO+Item yang sudah ada sebelumnya "
        "diperbarui, PO+Item baru ditambahkan, tidak ada yang dihapus otomatis."
        "</p>",
        unsafe_allow_html=True
    )

    if load_data is None:
        st.error("Koneksi data tidak tersedia (load_data tidak ditemukan).")
        return

    query = """
        SELECT
            r.purchasing_document        AS "Purchasing Document",
            r.item                       AS "Item",
            r.buyer                      AS "Buyer",
            r.purchase_requisition       AS "Purchase Requisition",
            r.short_text                 AS "Short Text",
            r.document_date              AS "Document Date",
            r.delivery_date              AS "Delivery Date",
            r.vendor_code                AS "Vendor Code",
            r.vendor_name                AS "Vendor Name",
            r.vendor_email               AS "Vendor email",
            r.tindak_lanjut_no_surat     AS "Tindak Lanjut (No. Surat)",
            r.keterangan_rencana_kirim   AS "Keterangan / Rencana Kirim",
            r.status_email               AS "Status Email",
            r.status_jawaban             AS "Status Jawaban",
            r.keterangan_email           AS "Keterangan Email",
            r.bagian                     AS "Bagian",
            r.upload_month               AS "Upload Month",
            CASE WHEN c.purchasing_document IS NOT NULL THEN 'Clear' ELSE 'Belum Clear' END AS "Status Clear",
            (CURRENT_DATE - r.delivery_date)::INTEGER AS "Keterlambatan (Hari)"
        FROM po_all_raw r
        LEFT JOIN po_clear_history c
            ON r.purchasing_document = c.purchasing_document
           AND r.item = c.item
        ORDER BY r.purchasing_document, r.item
    """

    try:
        df_all = load_data(query)
    except Exception as e:
        st.warning(
            ":material/warning: Tabel data mentah belum tersedia atau belum terisi "
            "(kemungkinan belum ada upload). Silakan upload sheet ALL melalui halaman "
            "**Manajemen Data** (Modul ETL: PO Outstanding (ALL)) terlebih dahulu.\n\n"
            f"Detail teknis: {e}"
        )
        return

    if df_all.empty:
        st.info(
            "Belum ada data mentah PO Outstanding. Silakan upload sheet ALL melalui halaman "
            "**Manajemen Data** (Modul ETL: PO Outstanding (ALL)) terlebih dahulu."
        )
        return

    df_all = _rapikan_tanggal(df_all, ["Document Date", "Delivery Date"])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Baris (PO + Item)", f"{len(df_all):,}".replace(",", "."))
    with col2:
        total_clear = (df_all["Status Clear"] == "Clear").sum()
        st.metric("Sudah Clear", f"{total_clear:,}".replace(",", "."))
    with col3:
        total_belum = (df_all["Status Clear"] == "Belum Clear").sum()
        st.metric("Belum Clear", f"{total_belum:,}".replace(",", "."))

    col_search, col_filter_clear, col_filter_bagian = st.columns([3, 2, 2])
    with col_search:
        keyword = st.text_input(
            ":material/search: Cari (No. PO / Vendor / Deskripsi, dll)",
            placeholder="Ketik kata kunci untuk memfilter tabel...",
            key="poo_all_search"
        )
    with col_filter_clear:
        filter_clear = st.selectbox(
            "Filter Status Clear",
            options=["Semua", "Clear", "Belum Clear"],
            key="poo_all_filter_clear"
        )
    with col_filter_bagian:
        opsi_bagian_all = ["Semua"] + sorted([b for b in df_all["Bagian"].dropna().unique().tolist()])
        filter_bagian_all = st.selectbox(
            "Filter Bagian",
            options=opsi_bagian_all,
            key="poo_all_filter_bagian"
        )

    df_display = df_all.copy()
    if filter_clear != "Semua":
        df_display = df_display[df_display["Status Clear"] == filter_clear]
    if filter_bagian_all != "Semua":
        df_display = df_display[df_display["Bagian"] == filter_bagian_all]

    if keyword:
        mask = df_display.apply(
            lambda row: row.astype(str).str.contains(keyword, case=False, na=False).any(),
            axis=1
        )
        df_display = df_display[mask]

    st.caption(f"Menampilkan {len(df_display)} dari {len(df_all)} baris.")

    st.dataframe(df_display, use_container_width=True, hide_index=True, height=600)

    _tombol_unduh(df_display, "PO_ALL_Raw", key="poo_all_download")


# =============================================================================
# TAB 3: PERLU EMAIL (dari po_outstanding -- hasil filter otomatis)
# =============================================================================

def _tab_perlu_email(load_data):
    st.markdown(
        "<p style='font-size:14px; opacity:0.7; margin-top:4px; margin-bottom:20px;'>"
        "Menampilkan daftar PO+Item yang <b>perlu dikirim reminder email</b> ke vendor -- "
        "hasil filter otomatis (belum pernah Clear, keterlambatan &gt; 7 hari, belum ada "
        "jawaban vendor, dan punya alamat email). Data ini yang dipakai di halaman "
        "<b>PO Outstanding - Reminder Email</b>."
        "</p>",
        unsafe_allow_html=True
    )

    if load_data is None:
        st.error("Koneksi data tidak tersedia (load_data tidak ditemukan).")
        return

    query = """
        SELECT
            purchasing_document          AS "Purchasing Document",
            item                          AS "Item",
            purchase_requisition          AS "Purchase Requisition",
            short_text                    AS "Short Text",
            document_date                  AS "Document Date",
            delivery_date                   AS "Delivery Date",
            vendor_code                    AS "Vendor Code",
            vendor_name                    AS "Vendor Name",
            vendor_email                   AS "Vendor email",
            bagian                        AS "Bagian",
            pending_time                    AS "PENDING TIME",
            pending_time_classification      AS "PENDING TIME Classification"
        FROM po_outstanding
        ORDER BY pending_time DESC, purchasing_document, item
    """

    try:
        df_pe = load_data(query)
    except Exception as e:
        st.warning(
            ":material/warning: Tabel Perlu Email belum tersedia atau belum terisi "
            "(kemungkinan belum ada upload & filter). Silakan upload sheet ALL melalui "
            "halaman **Manajemen Data** (Modul ETL: PO Outstanding (ALL)) terlebih dahulu.\n\n"
            f"Detail teknis: {e}"
        )
        return

    if df_pe.empty:
        st.info(
            "Tidak ada PO+Item yang perlu dikirim email saat ini -- baik karena belum ada "
            "data, atau semua sudah tertangani. Silakan upload/generate ulang dari halaman "
            "**Manajemen Data** jika ini tidak sesuai perkiraan."
        )
        return

    df_pe = _rapikan_tanggal(df_pe, ["Document Date", "Delivery Date"])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Perlu Email", f"{len(df_pe):,}".replace(",", "."))
    with col2:
        total_vendor = df_pe["Vendor Code"].nunique()
        st.metric("Jumlah Vendor Terdampak", f"{total_vendor:,}".replace(",", "."))
    with col3:
        if "PENDING TIME" in df_pe.columns and not df_pe["PENDING TIME"].isna().all():
            st.metric("Keterlambatan Tertinggi", f"{int(df_pe['PENDING TIME'].max())} hari")

    col_search, col_bagian = st.columns([3, 2])
    with col_search:
        keyword_pe = st.text_input(
            ":material/search: Cari (No. PO / Vendor / Deskripsi, dll)",
            placeholder="Ketik kata kunci untuk memfilter tabel...",
            key="poo_pe_search"
        )
    with col_bagian:
        opsi_bagian = ["Semua"] + sorted([b for b in df_pe["Bagian"].dropna().unique().tolist()])
        filter_bagian = st.selectbox("Filter Bagian", options=opsi_bagian, key="poo_pe_filter_bagian")

    df_display = df_pe.copy()
    if filter_bagian != "Semua":
        df_display = df_display[df_display["Bagian"] == filter_bagian]

    if keyword_pe:
        mask = df_display.apply(
            lambda row: row.astype(str).str.contains(keyword_pe, case=False, na=False).any(),
            axis=1
        )
        df_display = df_display[mask]

    st.caption(f"Menampilkan {len(df_display)} dari {len(df_pe)} baris.")

    st.dataframe(df_display, use_container_width=True, hide_index=True, height=600)

    _tombol_unduh(df_display, "PO_Perlu_Email", key="poo_pe_download")


# =============================================================================
# RENDER: tiga tab -> Dashboard, Data ALL, Perlu Email
# =============================================================================

def render(**kwargs):
    load_data = kwargs.get('load_data')

    st.markdown("""
        <h1 style='display:flex; align-items:center; font-size:38px; margin-bottom:0;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor"
                 viewBox="0 0 16 16" style="margin-right:12px; margin-bottom:4px;">
                <path d="M8.515 1.019A7 7 0 0 0 8 1V0a8 8 0 0 1 .589.022zm2.004.45a7 7 0 0 0-.985-.299l.219-.976q.576.129 1.126.342zm1.37.71a7 7 0 0 0-.439-.27l.493-.87a8 8 0 0 1 .979.654l-.615.789a7 7 0 0 0-.418-.302zm1.834 1.79a7 7 0 0 0-.653-.796l.724-.69q.406.429.747.91zm.744 1.352a7 7 0 0 0-.214-.468l.893-.45a8 8 0 0 1 .45 1.088l-.95.313a7 7 0 0 0-.179-.483m.53 2.507a7 7 0 0 0-.1-1.025l.985-.17q.1.58.116 1.17zm-.131 1.538q.05-.254.081-.51l.993.123a8 8 0 0 1-.23 1.155l-.964-.267q.069-.247.12-.501m-.952 2.379q.276-.436.486-.908l.914.405q-.24.54-.555 1.038zm-.964 1.205q.183-.183.35-.378l.758.653a8 8 0 0 1-.401.432z"/>
                <path d="M8 1a7 7 0 1 0 4.95 11.95l.707.707A8.001 8.001 0 1 1 8 0z"/>
                <path d="M7.5 3a.5.5 0 0 1 .5.5v5.21l3.248 1.856a.5.5 0 0 1-.496.868l-3.5-2A.5.5 0 0 1 7 9V3.5a.5.5 0 0 1 .5-.5"/>
            </svg>
            Monitoring PO Outstanding
        </h1>
    """, unsafe_allow_html=True)

    st.markdown(
        "<p style='font-size:15px; opacity:0.6; margin-top:4px; margin-bottom:24px;'>"
        "Ringkasan dan tampilan data PO Outstanding: KPI summary, data mentah apa adanya, "
        "dan daftar yang perlu dikirim reminder email ke vendor. Untuk mengupload data "
        "mentah bulanan (sheet ALL), gunakan halaman <b>Manajemen Data</b>."
        "</p>",
        unsafe_allow_html=True
    )

    tab_dashboard, tab_all, tab_perlu_email = st.tabs([
        ":material/dashboard: Dashboard",
        ":material/table_view: Data ALL",
        ":material/mail: Perlu Email",
    ])

    with tab_dashboard:
        _tab_dashboard(load_data)

    with tab_all:
        _tab_data_all(load_data)

    with tab_perlu_email:
        _tab_perlu_email(load_data)