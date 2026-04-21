"""
v_summary.py - Executive Summary Dashboard
Halaman khusus presentasi direksi dengan satu tampilan (Single Page), Filter Bulan, dan Tren PR-PO.
"""

import streamlit as st
import pandas as pd
import numpy as np
import calendar
import plotly.graph_objects as go
from datetime import datetime
from config_db import get_setting
from utils import format_idr, format_number, format_idr_short, idr_axis

# =============================================================================
# CSS: tampilan kartu KPI yang bersih & print-friendly
# =============================================================================
SUMMARY_CSS = """
<style>
/* == Card KPI & Chart Wrapper ============================================== */
.sum-card, div[data-testid="stPlotlyChart"] {
    border-radius: 12px !important;
    background-color: var(--secondary-background-color) !important;
    background-image: linear-gradient(rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.08)) !important;
    border: 1px solid rgba(128, 128, 128, 0.25) !important;
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08) !important;
    page-break-inside: avoid;
    break-inside: avoid;
}

.sum-card {
    /* Memaksa spesifikasi sisi kiri untuk menimpa aturan border umum di atas */
    border-left-width: 6px !important;
    border-left-style: solid !important;
    border-left-color: var(--text-color) !important;
}

/* Kelas tambahan untuk warna dinamis */
.sum-card.border-green { border-left-color: #09ab3b !important; }
.sum-card.border-red   { border-left-color: #e03c3c !important; }

div[data-testid="stPlotlyChart"] {
    /* Jangan gunakan padding di sini agar iframe tidak overflow! */
    overflow: hidden !important; 
}

/* == Text Colors (Pasti Aman Mengikuti Tema Streamlit) == */
.sum-icon {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    border-radius: 10px;
    background: rgba(128, 128, 128, 0.1) !important;
    color: var(--text-color) !important; /* Warna ikon aman */
}

.sum-card {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    
    /* Hapus height: 145px yang kaku, ganti dengan ini: */
    min-height: 145px !important; 
    height: 100%; 
    
    padding: 20px 18px 16px 18px;
}

.sum-body { 
    flex: 1; 
    min-width: 0; 
}

.sum-label {
    font-size: 12.5px;
    margin: 0 0 6px 0 !important; /* Memaksa jarak judul ke angka hanya 6px */
    line-height: 1.3;
    font-weight: 500;
    color: var(--text-color) !important;
    opacity: 0.75;
    /* Pastikan TIDAK ADA min-height atau display: flex di sini */
}

.sum-value {
    font-size: 2rem !important;
    font-weight: 600 !important;
    margin: 0 0 4px 0 !important; /* Memaksa jarak angka ke Target hanya 4px */
    line-height: 1.1 !important;
    color: var(--text-color) !important;
    white-space: normal !important;
    word-wrap: break-word !important;
    display: block !important;
}

.sum-delta { 
    font-size: 12px; 
    margin: 0; 
    color: var(--text-color) !important;
    opacity: 0.6;
}

/* Warna KPI khusus (Hijau, Merah, Oranye) dipertahankan karena terlihat di kedua mode */
.sum-delta-green { font-size: 12px; color: #09ab3b !important; margin: 0; font-weight: 600; }
.sum-delta-red   { font-size: 12px; color: #e03c3c !important; margin: 0; font-weight: 600; }
.sum-delta-orange{ font-size: 12px; color: #f0a500 !important; margin: 0; font-weight: 600; }

.sum-row-label {
    font-size: 14px; font-weight: 700; letter-spacing: 0.04em;
    text-transform: uppercase; color: #1f77b4; margin: 32px 0 12px 4px;
}

@media screen { .pagebreak { display: none; } }

/* == Print styles =========================================================== */
@media print {
    body { zoom: 0.75 !important; }
    [data-testid="stSidebar"], [data-testid="stSidebarNav"], [data-testid="stToolbar"], footer, header { display: none !important; }
    @page { margin: 1.5cm; size: A4 portrait; }
    .pagebreak { page-break-before: always !important; display: block !important; height: 0; }
    .sum-card, div[data-testid="stPlotlyChart"] {
        page-break-inside: avoid !important; border: 1px solid #ccc !important;
        box-shadow: none !important; background: transparent !important;
    }
    .sum-value, .sum-label, .sum-delta { color: #111 !important; }
    [data-testid="stHorizontalBlock"], div[data-testid="stPlotlyChart"] { break-inside: avoid !important; }
}
</style>
"""

# =============================================================================
# Helpers
# =============================================================================

def _svg(path_d: str, size: int = 40) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'fill="currentColor" viewBox="0 0 16 16"><path d="{path_d}"/></svg>'
    )

def _card(icon_d: str, label: str, value: str,
          delta: str = "", delta_type: str = "neutral", border_class: str = "") -> str:
    delta_cls = {
        "green":  "sum-delta-green",
        "red":    "sum-delta-red",
        "orange": "sum-delta-orange",
    }.get(delta_type, "sum-delta")
    delta_html = f'<p class="{delta_cls}">{delta}</p>' if delta else ""
    return f"""<div class="sum-card {border_class}">
    <div class="sum-icon">{_svg(icon_d, 36)}</div>
    <div class="sum-body">
        <p class="sum-label">{label}</p>
        <p class="sum-value">{value}</p>{delta_html}
    </div>
</div>"""

def _row_label(text: str) -> None:
    st.markdown(f'<div class="sum-row-label">{text}</div>', unsafe_allow_html=True)

# =============================================================================
# Icon path constants (Bootstrap Icons)
# =============================================================================

ICONS = {
    "file_text":   "M5 4a.5.5 0 0 0 0 1h6a.5.5 0 0 0 0-1zm-.5 2.5A.5.5 0 0 1 5 6h6a.5.5 0 0 1 0 1H5a.5.5 0 0 1-.5-.5M5 8a.5.5 0 0 0 0 1h6a.5.5 0 0 0 0-1zm0 2a.5.5 0 0 0 0 1h3a.5.5 0 0 0 0-1zM3 0h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2m0 1a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1z",
    "bag":         "M8 1a2.5 2.5 0 0 1 2.5 2.5V4h-5v-.5A2.5 2.5 0 0 1 8 1m3.5 3v-.5a3.5 3.5 0 1 0-7 0V4H1v10a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V4zM2 5h12v9a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1z",
    "percent":     "M13.442 2.558a.625.625 0 0 1 0 .884l-10 10a.625.625 0 1 1-.884-.884l10-10a.625.625 0 0 1 .884 0M4.5 6a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3m0 1a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5m7 6a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3m0 1a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5",
    "house":       "M8.707 1.5a1 1 0 0 0-1.414 0L.646 8.146a.5.5 0 0 0 .708.708L2 8.207V13.5A1.5 1.5 0 0 0 3.5 15h9a1.5 1.5 0 0 0 1.5-1.5V8.207l.646.647a.5.5 0 0 0 .708-.708zM7 14V9h2v5zm3 0V9a1 1 0 0 0-1-1H7a1 1 0 0 0-1 1v5H3.5a.5.5 0 0 1-.5-.5V7.207l5-5 5 5V13.5a.5.5 0 0 1-.5.5z",
    "people":      "M7 14s-1 0-1-1 1-4 5-4 5 3 5 4-1 1-1 1zm4-6a3 3 0 1 0 0-6 3 3 0 0 0 0 6m-5.784 6A2.24 2.24 0 0 1 5 13c0-1.355.68-2.75 1.936-3.72A6.3 6.3 0 0 0 5 9c-4 0-5 3-5 4s1 1 1 1zM4.5 8a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5",
    "clock":       "M8 3.5a.5.5 0 0 0-1 0V9a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0 0 .496-.868L8 8.71zM8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16m7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0",
    "truck":       "M0 3.5A1.5 1.5 0 0 1 1.5 2h9A1.5 1.5 0 0 1 12 3.5V5h1.02a1.5 1.5 0 0 1 1.17.563l1.481 1.85a1.5 1.5 0 0 1 .329.938V10.5a1.5 1.5 0 0 1-1.5 1.5H14a2 2 0 1 1-4 0H5a2 2 0 1 1-3.998-.085A1.5 1.5 0 0 1 0 10.5zm1.294 7.456A2 2 0 0 1 4.732 11h5.536a2 2 0 0 1 .732-.732V3.5a.5.5 0 0 0-.5-.5h-9a.5.5 0 0 0-.5.5v7a.5.5 0 0 0 .294.456M12 10a2 2 0 0 1 1.732 1h.768a.5.5 0 0 0 .5-.5V8.35a.5.5 0 0 0-.11-.312l-1.48-1.85A.5.5 0 0 0 13.02 6H12zm-9 1a1 1 0 1 0 0 2 1 1 0 0 0 0-2m9 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2",
    "check_circle":"M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16M10.97 4.97a.235.235 0 0 0-.02.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-1.071-1.05",
    "search":      "M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001q.044.06.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1 1 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0",
    "refresh":     "M11.534 7h3.932a.25.25 0 0 1 .192.41l-1.966 2.36a.25.25 0 0 1-.384 0l-1.966-2.36a.25.25 0 0 1 .192-.41m-11 2h3.932a.25.25 0 0 0 .192-.41L2.692 6.23a.25.25 0 0 0-.384 0L.342 8.59A.25.25 0 0 0 .534 9 M8 3c-1.552 0-2.94.707-3.857 1.818a.5.5 0 1 1-.771-.636A6.002 6.002 0 0 1 13.917 7H12.9A5 5 0 0 0 8 3M3.1 9a5.002 5.002 0 0 0 8.757 2.182.5.5 0 1 1 .771.636A6.002 6.002 0 0 1 2.083 9z",
    "lock":        "M8 1a2 2 0 0 1 2 2v4H6V3a2 2 0 0 1 2-2m3 6V3a3 3 0 0 0-6 0v4a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2",
    "check_all":   "M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16 M10.97 4.97a.75.75 0 0 1 1.07 1.05l-3.99 4.99a.75.75 0 0 1-1.08.02L4.324 8.384a.75.75 0 1 1 1.06-1.06l2.094 2.093 3.473-4.425z",
    "graph_up":    "M0 0h1v15h15v1H0zm14.817 3.113a.5.5 0 0 1 .07.704l-4.5 5.5a.5.5 0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5 0 0 1 .758-.06l2.609 2.61 4.15-5.073a.5.5 0 0 1 .704-.07",
    "currency":    "M4 10.781c.148 1.667 1.513 2.85 3.591 3.003V15h1.043v-1.216c2.27-.179 3.678-1.438 3.678-3.3 0-1.59-.947-2.51-2.956-3.028l-.722-.187V3.467c1.122.11 1.879.714 2.07 1.616h1.47c-.166-1.6-1.54-2.748-3.54-2.875V1H7.591v1.233c-1.939.23-3.27 1.472-3.27 3.156 0 1.454.966 2.483 2.661 2.917l.61.162v4.031c-1.149-.17-1.94-.8-2.131-1.718zm3.391-3.836c-1.043-.263-1.6-.825-1.6-1.616 0-.944.704-1.641 1.8-1.828v3.495l-.2-.05zm1.591 1.872c1.287.323 1.852.859 1.852 1.769 0 1.097-.826 1.828-2.2 1.939V8.73z",
    "calendar":    "M3.5 0a.5.5 0 0 1 .5.5V1h8V.5a.5.5 0 0 1 1 0V1h1a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2h1V.5a.5.5 0 0 1 .5-.5M1 4v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V4z",
    "bar_chart":   "M1 11a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1zm5-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1zm5-5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1z",
    "box":         "M8.186 1.113a.5.5 0 0 0-.372 0L1.846 3.5 8 5.961 14.154 3.5zM15 4.239l-6.5 2.6v7.922l6.5-2.6V4.24zM7.5 14.762V6.838L1 4.239v7.923zM7.443.184a1.5 1.5 0 0 1 1.114 0l7.129 2.852A.5.5 0 0 1 16 3.5v8.662a1 1 0 0 1-.629.928l-7.185 2.874a.5.5 0 0 1-.372 0L.63 13.09a1 1 0 0 1-.63-.928V3.5a.5.5 0 0 1 .314-.464z",
    "building":    "M4 2.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm3 0a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm3.5-.5a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5v-1a.5.5 0 0 0-.5-.5zM4 5.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zM7.5 5a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5v-1a.5.5 0 0 0-.5-.5zm2.5.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zM4.5 8a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5v-1a.5.5 0 0 0-.5-.5zm2.5.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm3.5-.5a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5v-1a.5.5 0 0 0-.5-.5z M2 1a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1zm11 0H3v14h3v-2.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 .5.5V15h3z"
}

# =============================================================================
# RENDER
# =============================================================================

def render(load_data, **kwargs):
    st.markdown(SUMMARY_CSS, unsafe_allow_html=True)

    current_year = datetime.now().year

    sap_date_str = get_setting("DATA_UPDATE_SAP", "2026-03-31")
    try: DATA_UPDATE_SAP = datetime.strptime(sap_date_str, "%Y-%m-%d").date()
    except: DATA_UPDATE_SAP = datetime(2026, 3, 31).date()

    ink_date_str = get_setting("DATA_UPDATE_INKLARING", "2026-03-31")
    try: DATA_UPDATE_INKLARING = datetime.strptime(ink_date_str, "%Y-%m-%d").date()
    except: DATA_UPDATE_INKLARING = datetime(2026, 3, 31).date()

    # == Header Utama =========================================================
    st.markdown("""
        <h1 style='display:flex; align-items:center; font-size:52px; margin-bottom:0;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="42" height="42" fill="currentColor"
                 viewBox="0 0 16 16" style="margin-right:12px; margin-bottom:8px;">
                <path d="M0 0h1v15h15v1H0zm14.817 3.113a.5.5 0 0 1 .07.704l-4.5 5.5a.5.5
                         0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5
                         0 0 1 .758-.06l2.609 2.61 4.15-5.073a.5.5 0 0 1 .704-.07"/>
            </svg>
            Executive Summary
        </h1>
    """, unsafe_allow_html=True)
    st.markdown(
        "<p style='font-size:15px; opacity:0.55; margin-top:0; margin-bottom: 24px;'>"
        "Ringkasan dan Laporan Pengadaan Barang</p>",
        unsafe_allow_html=True
    )

    # == Filter Bulan Dinamis =================================================
    months_id = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    options = ["ALL"] + [f"{m} {current_year}" for m in months_id]
    
    # --- UI DROPDOWN DISEMBUNYIKAN SEMENTARA ---
    col_filter, _ = st.columns([1, 4])
    with col_filter:
        st.markdown(
            f"<p style='font-size:13px; font-weight:600; margin-bottom:2px; display:flex; align-items:center; gap:6px;'>"
            f"{_svg(ICONS['calendar'], 14)} Filter Bulan</p>", 
            unsafe_allow_html=True
        )
        selected_month = st.selectbox("Filter Bulan", options=options, label_visibility="collapsed")

    # Paksa nilai filter selalu "ALL"
    # selected_month = "ALL"

    # Menentukan rentang tanggal (date_from dan date_to)
    if selected_month != "ALL":
        month_str = selected_month.split(" ")[0]
        month_idx = months_id.index(month_str) + 1
        last_day = calendar.monthrange(current_year, month_idx)[1]
        date_from = datetime(current_year, month_idx, 1).date()
        date_to = datetime(current_year, month_idx, last_day).date()
        date_to_ink = date_to
    else:
        date_from = kwargs.get('date_from', datetime(current_year, 1, 1).date())
        date_to   = kwargs.get('date_to', DATA_UPDATE_SAP)
        date_to_ink = DATA_UPDATE_INKLARING

    # Info Teks Periode
    st.markdown(
        f"<p style='font-size:16px; margin-top:6px;'>"
        f"Periode: <b>{date_from.strftime('%d %B %Y')} s.d. {date_to.strftime('%d %B %Y')}</b> "
        f"&nbsp;|&nbsp; Data per {DATA_UPDATE_SAP.strftime('%d %B %Y')} "
        f"&nbsp;|&nbsp; Dicetak: {datetime.now().strftime('%d %B %Y %H:%M')}</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # == Eksekusi Kueri =======================================================
    pr_kpi_query = f"""
    WITH unique_pr AS (
        SELECT
            no_pr,
            line_item_pr,
            MAX(CASE WHEN nomor_po IS NOT NULL THEN 1 ELSE 0 END) AS has_po,
            MAX(estimasi_pr * quantity_pr) AS oe_val 
        FROM vw_pr_po_complete
        WHERE first_full_release >= '{date_from}'
          AND first_full_release <= '{date_to}'
          AND no_pr != 'No PR'
          AND first_full_release IS NOT NULL
        GROUP BY no_pr, line_item_pr
    )
    SELECT
        COUNT(*)                            AS total_pr,
        SUM(has_po)                         AS pr_with_po,
        COUNT(*) - SUM(has_po)              AS pr_without_po,
        COALESCE(SUM(oe_val), 0)            AS total_estimasi
    FROM unique_pr
    """

    po_kpi_query = f"""
    SELECT
        COUNT(poi.nomor_po)                                              AS total_po,
        COALESCE(SUM(poi.total_amount_local_curr), 0)                    AS total_po_amount,
        COALESCE(SUM(poi.quantity_pr * poi.estimasi_pr), 0)              AS total_oe_po,
        ROUND(AVG(
            CASE WHEN poi.first_full_release IS NOT NULL
                    AND poh.date_ordered   IS NOT NULL
            THEN (poh.date_ordered::date - poi.first_full_release::date)
            END
        )::numeric, 2)                                                   AS avg_lead_time,
        COUNT(DISTINCT poh.nomor_po)                                     AS total_po_distinct,
        COUNT(CASE WHEN poi.status_pengiriman = 'SELESAI' THEN 1 END)    AS po_delivered,
        COUNT(CASE WHEN poi.on_time_delivery  = 'TEPAT WAKTU' THEN 1 END) AS po_ontime,
        COUNT(CASE WHEN poi.on_time_delivery IN ('TEPAT WAKTU','TERLAMBAT')
                    THEN 1 END)                                          AS po_delivered_total,
        COALESCE(SUM(CASE WHEN poh.vendor_code IN ('4000000011', '4000000012') 
                    THEN poi.total_amount_local_curr ELSE 0 END), 0)     AS total_sinergi_pi
    FROM po_items poi
    JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
    WHERE poh.date_ordered >= '{date_from}'
      AND poh.date_ordered <= '{date_to}'
    """

    trend_query = f"""
    WITH pr_monthly AS (
        SELECT
            DATE_TRUNC('month', first_full_release) AS month_date,
            COUNT(DISTINCT CASE WHEN no_pr != 'No PR'
                THEN no_pr || '-' || line_item_pr::text END) AS total_pr
        FROM vw_pr_po_complete
        WHERE first_full_release >= '{date_from}' AND first_full_release <= '{date_to}'
        GROUP BY 1
    ),
    po_monthly AS (
        SELECT
            DATE_TRUNC('month', poh.date_ordered) AS month_date,
            COUNT(poi.nomor_po) AS total_po
        FROM po_items poi
        JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
        WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
        GROUP BY 1
    )
    SELECT
        COALESCE(pr.month_date, po.month_date) AS month,
        COALESCE(pr.total_pr, 0) AS total_pr,
        COALESCE(po.total_po, 0) AS total_po
    FROM pr_monthly pr
    FULL OUTER JOIN po_monthly po ON pr.month_date = po.month_date
    ORDER BY month
    """

    value_trend_query = f"""
    WITH pr_monthly_val AS (
        SELECT
            DATE_TRUNC('month', first_full_release) AS month_date,
            SUM(oe_val) AS total_oe
        FROM (
            SELECT
                no_pr, line_item_pr,
                MAX(first_full_release) AS first_full_release,
                MAX(estimasi_pr) AS oe_val
            FROM vw_pr_po_complete
            WHERE first_full_release >= '{date_from}' AND first_full_release <= '{date_to}'
              AND no_pr != 'No PR' AND first_full_release IS NOT NULL
            GROUP BY no_pr, line_item_pr
        ) sub
        GROUP BY 1
    ),
    po_monthly_val AS (
        SELECT
            DATE_TRUNC('month', poh.date_ordered) AS month_date,
            SUM(poi.total_amount_local_curr) AS total_po_val
        FROM po_items poi
        JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
        WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
        GROUP BY 1
    )
    SELECT
        COALESCE(pr.month_date, po.month_date) AS month,
        COALESCE(pr.total_oe, 0) AS total_oe,
        COALESCE(po.total_po_val, 0) AS total_po_val
    FROM pr_monthly_val pr
    FULL OUTER JOIN po_monthly_val po ON pr.month_date = po.month_date
    ORDER BY month
    """

    inklaring_query = f"""
    SELECT tgl_sppb, selesai_bongkar, spjm, komoditi
    FROM inklaring_impor
    WHERE tgl_eta >= '{date_from}' AND tgl_eta <= '{date_to_ink}'
    """

    sips_otobos_query = f"""
    SELECT
        COUNT(CASE WHEN status IN ('Closed','Proses PO') THEN 1 END) AS total_po,
        COALESCE(SUM(CASE WHEN status IN ('Closed','Proses PO') THEN nilai_sla END), 0) AS sla_ontime,
        COUNT(CASE WHEN persen_po_sr_mr <= 1.0 AND status IN ('Closed','Proses PO') THEN 1 END) AS on_budget_count
    FROM vw_sips
    WHERE tgl_disposisi_buyer >= '{date_from}' AND tgl_disposisi_buyer <= '{date_to}'
    """

    with st.spinner("Memuat data laporan..."):
        try:
            pr_kpi = load_data(pr_kpi_query)
            po_kpi = load_data(po_kpi_query)
            trend_data = load_data(trend_query)
            val_trend_data = load_data(value_trend_query)
            ink_data = load_data(inklaring_query)
            sips_otobos_data = load_data(sips_otobos_query)
        except Exception as e:
            st.error(f"Gagal memuat data: {e}")
            return

    # Proses tanggal untuk kedua chart (PENTING: dilakukan di luar kolom agar aman)
    today = datetime.now().date()
    def resolve_month_date(month_ts):
        y, m = month_ts.year, month_ts.month
        cy, cm = today.year, today.month
        if (y, m) == (cy, cm):
            return pd.Timestamp(today)
        elif (y, m) < (cy, cm):
            last_day = calendar.monthrange(y, m)[1]
            return pd.Timestamp(y, m, last_day)
        else:
            return month_ts

    def fmt_date(ts):
        return f"{ts.day} {ts.strftime('%b')} {ts.year}"

    if not trend_data.empty:
        trend_data['month'] = pd.to_datetime(trend_data['month'])
        trend_data = trend_data.sort_values('month')
        trend_data['month_display'] = trend_data['month'].apply(resolve_month_date)
        trend_data['hover_label'] = trend_data['month_display'].apply(fmt_date)

    if not val_trend_data.empty:
        val_trend_data['month'] = pd.to_datetime(val_trend_data['month'])
        val_trend_data = val_trend_data.sort_values('month')
        val_trend_data['month_display'] = val_trend_data['month'].apply(resolve_month_date)
        val_trend_data['hover_label'] = val_trend_data['month_display'].apply(fmt_date)
        val_trend_data['oe_fmt'] = val_trend_data['total_oe'].apply(format_idr)
        val_trend_data['po_fmt'] = val_trend_data['total_po_val'].apply(format_idr)

    # Kalkulasi nilai KPI
    total_pr      = int(pr_kpi['total_pr'][0]       or 0)
    pr_with_po    = int(pr_kpi['pr_with_po'][0]     or 0)
    pr_without    = int(pr_kpi['pr_without_po'][0]  or 0)
    estimasi_all  = float(pr_kpi['total_estimasi'][0] or 0)

    total_po      = int(po_kpi['total_po'][0]        or 0)
    po_amount     = float(po_kpi['total_po_amount'][0] or 0)
    oe_po         = float(po_kpi['total_oe_po'][0]   or 0)
    avg_lt        = po_kpi['avg_lead_time'][0]
    avg_lt_val    = float(avg_lt) if avg_lt is not None else 0.0
    total_po_dist = int(po_kpi['total_po_distinct'][0]  or 0)
    po_delivered  = int(po_kpi['po_delivered'][0]       or 0)
    po_ontime     = int(po_kpi['po_ontime'][0]          or 0)
    po_del_tot    = int(po_kpi['po_delivered_total'][0] or 0)
    sinergi_pi_val= float(po_kpi['total_sinergi_pi'][0] or 0)

    savings       = oe_po - po_amount
    savings_pct   = (savings / oe_po * 100)        if oe_po > 0        else 0.0
    produktivitas = (total_po / total_pr * 100)    if total_pr > 0     else 0.0
    pct_kirim     = (po_delivered / total_po * 100) if total_po > 0    else 0.0
    ketepatan     = (po_ontime / po_del_tot * 100)  if po_del_tot > 0  else 0.0

    # Performance flags for row 1
    color_produktivitas = "green" if produktivitas > 90 else "red"

    # Performance flags for row 2 to determine colors for row 2 and 3
    perf_kecepatan = avg_lt_val <= 55
    perf_pengiriman = pct_kirim > 80
    perf_ketepatan = ketepatan > 90

    # Perhitungan Kinerja SLA Pembebasan Barang (Inklaring SLA EPP)
    if not ink_data.empty:
        ink_data['tgl_sppb'] = pd.to_datetime(ink_data['tgl_sppb'], errors='coerce')
        ink_data['selesai_bongkar'] = pd.to_datetime(ink_data['selesai_bongkar'], errors='coerce')
        ink_data['Bebas_Hari'] = (ink_data['tgl_sppb'] - ink_data['selesai_bongkar'].dt.normalize()).dt.days
        
        is_hijau_mask = ink_data['spjm'].fillna('').astype(str).str.strip().isin(['', '0', '0.0'])
        ink_data['Keterangan_Jalur'] = np.where(is_hijau_mask, 'HIJAU', 'MERAH')
        ink_data['SLA_Target'] = np.where(ink_data['komoditi'] == 'SA', 15, 
                                    np.where(ink_data['Keterangan_Jalur'] == 'MERAH', 8, 0))
        ink_data['Score_SLA'] = np.where(
            ink_data['Bebas_Hari'].isna() | (ink_data['Bebas_Hari'] == 0), 
            0, 
            np.where(ink_data['SLA_Target'] >= ink_data['Bebas_Hari'], 1, 0)
        )
        total_ink_data = len(ink_data)
        total_score_1 = (ink_data['Score_SLA'] == 1).sum()
        sla_pembebasan_pct = (total_score_1 / total_ink_data) * 100 if total_ink_data > 0 else 0.0
    else:
        sla_pembebasan_pct = 0.0

    # Hardcoded values for row 4 KPIs
    otobos_val = 99.33
    # Perhitungan OTOBOS (SIPS)
    if not sips_otobos_data.empty:
        s_po = int(sips_otobos_data['total_po'][0] or 0)
        s_ontime = float(sips_otobos_data['sla_ontime'][0] or 0)
        s_onbudget = int(sips_otobos_data['on_budget_count'][0] or 0)
        
        sla_on_time_pct = (s_ontime / s_po * 100) if s_po > 0 else 0.0
        sla_on_budget_pct = (s_onbudget / s_po * 100) if s_po > 0 else 0.0
    else:
        sla_on_time_pct = 0.0
        sla_on_budget_pct = 0.0
        
    sla_on_spec_pct = 99.30
    otobos_val = (sla_on_time_pct + sla_on_budget_pct + sla_on_spec_pct) / 3

    # Dynamic color logic based on targets
    color_pembebasan = "green" if sla_pembebasan_pct >= 80 else "red"
    color_efisiensi_pengadaan = "green" if savings_pct > 2 else "red"
    color_izin_impor = "green"  # Value is 100%, target is 2/2 (100%)
    color_otobos = "green" if otobos_val > 90 else "red"

    # Map performance color names to CSS class names for borders
    border_class_map = {
        "green": "border-green",
        "red":   "border-red",
    }


    # ═════════════════════════════════════════════════════════════════════════
    # BAGIAN 1: KPI PENGADAAN BARANG
    # ═════════════════════════════════════════════════════════════════════════
    st.markdown(
        f"<h2 style='display:flex; align-items:center; font-size:32px; margin: 0 0 16px 0; font-weight:700; color:var(--text-color);'>"
        f"<span style='margin-right:12px; transform: translateY(4px); display:inline-flex; align-items:center;'>{_svg(ICONS['graph_up'], 32)}</span>"
        f"KPI Pengadaan Barang"
        f"</h2>", 
        unsafe_allow_html=True
    )
    
    # Baris 1
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(_card(ICONS["house"], "Pengelolaan Anggaran Operasional", "-", "Target: ≤ 100%", "neutral"), unsafe_allow_html=True)
    with c2:
        st.markdown(_card(ICONS["people"], "Sinergi PI Group", format_idr(sinergi_pi_val), "Target: -", "neutral"), unsafe_allow_html=True)
    with c3:
        st.markdown(_card(ICONS["percent"], "Produktivitas PR-PO", f"{format_number(produktivitas, decimals=2)}%", "Target: > 90%", color_produktivitas, border_class=border_class_map.get(color_produktivitas, "")), unsafe_allow_html=True)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # Baris 2
    c4, c5, c6 = st.columns(3)
    with c4:
        color_kecepatan = "green" if perf_kecepatan else "red"
        st.markdown(_card(ICONS["clock"], "Kecepatan Proses PO", f"{format_number(avg_lt_val, decimals=2)} Hari", "Target: ≤ 55 Hari", color_kecepatan, border_class=border_class_map.get(color_kecepatan, "")), unsafe_allow_html=True)
    with c5:
        color_pengiriman = "green" if perf_pengiriman else "red"
        st.markdown(_card(ICONS["truck"], "% Pengiriman Barang (GR/PO)", f"{format_number(pct_kirim, decimals=1)}%", "Target: > 80%", color_pengiriman, border_class=border_class_map.get(color_pengiriman, "")), unsafe_allow_html=True)
    with c6:
        color_ketepatan = "green" if perf_ketepatan else "red"
        st.markdown(_card(ICONS["check_circle"], "Ketepatan Pengiriman Barang", f"{format_number(ketepatan, decimals=1)}%", "Target: > 90%", color_ketepatan, border_class=border_class_map.get(color_ketepatan, "")), unsafe_allow_html=True)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # Baris 3
    c7, c8, c9 = st.columns(3)
    with c7:
        st.markdown(_card(ICONS["check_all"], "Pemenuhan SLA Pembebasan Barang", f"{format_number(sla_pembebasan_pct, decimals=2)}%", "Target: 80%", color_pembebasan, border_class=border_class_map.get(color_pembebasan, "")), unsafe_allow_html=True)
    with c8:
        st.markdown(_card(ICONS["refresh"], "Efisiensi Pengadaan (PO/OE)", f"{format_number(savings_pct, decimals=2)}%", "Target: > 2%", color_efisiensi_pengadaan, border_class=border_class_map.get(color_efisiensi_pengadaan, "")), unsafe_allow_html=True)
    with c9:
        st.markdown(_card(ICONS["lock"], "Pemenuhan Izin Impor", "100%", "Target: 2 / 2", color_izin_impor, border_class=border_class_map.get(color_izin_impor, "")), unsafe_allow_html=True)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # Baris 4: Rincian Pemenuhan SLA OTOBOS
    st.markdown(
        "<div style='font-size:13px; font-weight:700; color:var(--text-color); margin: 20px 0 10px 4px; opacity:0.8;'>"
        "RINCIAN PEMENUHAN SLA OTOBOS"
        "</div>", 
        unsafe_allow_html=True
    )
    
    c10, c11, c12, c13 = st.columns(4)
    with c10:
        st.markdown(_card(ICONS["search"], "Total SLA OTOBOS", f"{format_number(otobos_val, decimals=2)}%", "Target: > 90%", color_otobos, border_class=border_class_map.get(color_otobos, "")), unsafe_allow_html=True)
    with c11:
        st.markdown(_card(ICONS["clock"], "SLA - On Time", f"{format_number(sla_on_time_pct, decimals=2)}%"), unsafe_allow_html=True)
    with c12:
        st.markdown(_card(ICONS["currency"], "SLA - On Budget", f"{format_number(sla_on_budget_pct, decimals=2)}%"), unsafe_allow_html=True)
    with c13:
        st.markdown(_card(ICONS["check_all"], "SLA - On Spec", f"{format_number(sla_on_spec_pct, decimals=2)}%"), unsafe_allow_html=True)

    st.markdown("<hr style='margin: 24px 0 16px 0; border-color: rgba(128,128,128,0.2);'>", unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


    # ═════════════════════════════════════════════════════════════════════════
    # BAGIAN 2: LAPORAN PENGADAAN BARANG (Kiri: Volume | Kanan: Nilai)
    # ═════════════════════════════════════════════════════════════════════════
    
    # --- PEMBATAS HALAMAN 2 ---
    st.markdown('<div class="pagebreak"></div>', unsafe_allow_html=True)
    
    st.markdown(
        f"<h2 style='display:flex; align-items:center; font-size:32px; margin: 0 0 16px 0; font-weight:700; color:var(--text-color);'>"
        f"<span style='margin-right:12px; transform: translateY(4px); display:inline-flex; align-items:center;'>{_svg(ICONS['file_text'], 32)}</span>"
        f"Laporan Pengadaan Barang"
        f"</h2>", 
        unsafe_allow_html=True
    )

    # Membuat 2 kolom besar dengan jarak (gap) yang lebar sebagai "pembagi" tengah
    col_kiri, col_kanan = st.columns(2, gap="large")

    # == SISI KIRI: VOLUME PENGADAAN ==========================================
    with col_kiri:
        st.markdown(
            f"<h3 style='font-size:20px; margin-bottom:16px; color:var(--text-color);'>"
            f"<span style='margin-right:8px; vertical-align: middle;'>{_svg(ICONS['box'], 26)}</span>"
            f"<span style='vertical-align: middle;'>Realisasi Item PR-PO</span>"
            f"</h3>", 
            unsafe_allow_html=True
        )

        # Kartu Baris 1 (Kiri)
        c11, c12 = st.columns(2)
        with c11:
            st.markdown(_card(
                ICONS["file_text"], "Total PR", format_number(total_pr), 
                f"{format_number(pr_with_po)} sudah memiliki PO"
            ), unsafe_allow_html=True)
        with c12:
            st.markdown(_card(
                ICONS["bag"], "Total PO", format_number(total_po), 
                "Termasuk PR tahun sebelumnya"
            ), unsafe_allow_html=True)
        
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        # Kartu Baris 2 (Kiri)
        c13, c14 = st.columns(2)
        with c13:
            st.markdown(_card(
                ICONS["clock"], "PR On Progress", format_number(pr_without), ""
            ), unsafe_allow_html=True)
        with c14:
            pct_pr_po = (total_po / total_pr * 100) if total_pr > 0 else 0.0
            st.markdown(_card(
                ICONS["percent"], "% PR-PO", f"{format_number(pct_pr_po, decimals=2)}%", ""
            ), unsafe_allow_html=True)

        st.markdown("<hr style='margin: 24px 0 16px 0; border-color: rgba(128,128,128,0.2);'>", unsafe_allow_html=True)
        
        if not trend_data.empty:
            chart_type = st.pills(
                "Tampilan:", 
                options=["Per Bulan (Stacked Bar)", "Kumulatif (Line)"], 
                default="Per Bulan (Stacked Bar)",
                key="pills_trend_summary_count"
            )
        
            tick_vals = trend_data['month_display'].tolist()
            tick_text = trend_data['hover_label'].tolist()

            fig1 = go.Figure()

            if chart_type == "Kumulatif (Line)":
                fig1.add_trace(go.Scatter(
                    x=trend_data['month_display'], y=trend_data['total_pr'].cumsum(),
                    mode='lines+markers', name='PR Created', line=dict(color='#1f77b4', width=2),
                    customdata=trend_data[['hover_label']], hovertemplate='<b>%{customdata[0]}</b><br>Kumulatif PR: %{y}<extra></extra>'
                ))
                fig1.add_trace(go.Scatter(
                    x=trend_data['month_display'], y=trend_data['total_po'].cumsum(),
                    mode='lines+markers', name='PO Created', line=dict(color='#2ca02c', width=2),
                    customdata=trend_data[['hover_label']], hovertemplate='<b>%{customdata[0]}</b><br>Kumulatif PO: %{y}<extra></extra>'
                ))
                y_axis_title = 'Cumulative Count'
            else:
                fig1.add_trace(go.Bar(
                    x=trend_data['month_display'], y=trend_data['total_pr'],
                    name='PR Created', marker_color='#1f77b4',
                    customdata=trend_data[['hover_label']], hovertemplate='<b>%{customdata[0]}</b><br>PR Created: %{y}<extra></extra>'
                ))
                fig1.add_trace(go.Bar(
                    x=trend_data['month_display'], y=trend_data['total_po'],
                    name='PO Created', marker_color='#2ca02c',
                    customdata=trend_data[['hover_label']], hovertemplate='<b>%{customdata[0]}</b><br>PO Created: %{y}<extra></extra>'
                ))
                fig1.update_layout(barmode='group') 
                y_axis_title = 'Count per Month'
        
            fig1.update_layout(
                height=350, # Sedikit dinaikkan untuk menampung margin atas
                xaxis_title='', yaxis_title=y_axis_title,
                xaxis=dict(tickmode='array', tickvals=tick_vals, ticktext=tick_text, tickangle=-30),
                # t=60 memberi ruang di atas untuk legend & toolbar, r=30 mencegah kanan terpotong
                margin=dict(t=60, b=10, l=10, r=30), 
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("Tidak ada data tren.")

    # == SISI KANAN: NILAI PENGADAAN ==========================================
    with col_kanan:
        st.markdown(
            f"<h3 style='font-size:20px; margin-bottom:16px; color:var(--text-color);'>"
            f"<span style='margin-right:8px; vertical-align: middle;'>{_svg(ICONS['currency'], 26)}</span>"
            f"<span style='vertical-align: middle;'>Realisasi Nilai PR-PO</span>"
            f"</h3>", 
            unsafe_allow_html=True
        )

        # Kartu Baris 1 (Kanan)
        c15, c16 = st.columns(2)
        with c15:
            st.markdown(_card(
                ICONS["currency"], "Total Estimasi PR (OE)", format_idr(oe_po), 
                #ICONS["currency"], "Total Estimasi PR (OE)", "Rp 4,61 T",
                "OE dari PR yang sudah terbit PO"
            ), unsafe_allow_html=True)
        with c16:
            st.markdown(_card(
                ICONS["bag"], "Total Nilai PO", format_idr(po_amount), 
                "Seluruh PO pada periode ini"
            ), unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        # Kartu Baris 2 (Kanan)
        c17, c18 = st.columns(2)
        with c17:
            st.markdown(_card(
                ICONS["graph_up"], "Efisiensi", format_idr(savings)
                #ICONS["graph_up"], "Efisiensi", "Rp 23,57 M",
            ), unsafe_allow_html=True)
        with c18:
            st.markdown(_card(
                ICONS["percent"], "% Efisiensi", f"{format_number(savings_pct, decimals=2)}%"
                #ICONS["percent"], "% Efisiensi", "0,51%",
            ), unsafe_allow_html=True)

        st.markdown("<hr style='margin: 24px 0 16px 0; border-color: rgba(128,128,128,0.2);'>", unsafe_allow_html=True)

        if not val_trend_data.empty:
            # Pilihan jenis chart untuk Value Trend
            chart_type_val = st.pills(
                "Tampilan:", 
                options=["Per Bulan (Bar)", "Kumulatif (Line)"], 
                default="Per Bulan (Bar)",
                key="pills_trend_summary_val"
            )

            fig2 = go.Figure()

            if chart_type_val == "Kumulatif (Line)":
                y_oe_cum = val_trend_data['total_oe'].cumsum()
                y_po_cum = val_trend_data['total_po_val'].cumsum()
                
                # Format text untuk hover chart kumulatif
                val_trend_data['cum_oe_fmt'] = y_oe_cum.apply(format_idr)
                val_trend_data['cum_po_fmt'] = y_po_cum.apply(format_idr)

                fig2.add_trace(go.Scatter(
                    x=val_trend_data['month_display'], y=y_oe_cum,
                    mode='lines+markers', name='Estimasi PR (OE)',
                    line=dict(color='#1f77b4', width=3, shape='spline'),
                    fill='tozeroy', fillcolor='rgba(31,119,180,0.1)',
                    customdata=val_trend_data[['hover_label', 'cum_oe_fmt']],
                    hovertemplate='<b>%{customdata[0]}</b><br>Kumulatif Estimasi PR: %{customdata[1]}<extra></extra>'
                ))
                fig2.add_trace(go.Scatter(
                    x=val_trend_data['month_display'], y=y_po_cum,
                    mode='lines+markers', name='Nilai PO',
                    line=dict(color='#2ca02c', width=3, shape='spline'),
                    fill='tozeroy', fillcolor='rgba(44,160,44,0.1)',
                    customdata=val_trend_data[['hover_label', 'cum_po_fmt']],
                    hovertemplate='<b>%{customdata[0]}</b><br>Kumulatif Nilai PO: %{customdata[1]}<extra></extra>'
                ))
                
                max_val = max(y_oe_cum.max(), y_po_cum.max())
                
            else:
                # Per Bulan (Bar Bersebelahan / Group)
                fig2.add_trace(go.Bar(
                    x=val_trend_data['month_display'], y=val_trend_data['total_oe'],
                    name='Estimasi PR (OE)',
                    marker_color='#1f77b4',
                    customdata=val_trend_data[['hover_label', 'oe_fmt']],
                    hovertemplate='<b>%{customdata[0]}</b><br>Estimasi PR: %{customdata[1]}<extra></extra>'
                ))
                fig2.add_trace(go.Bar(
                    x=val_trend_data['month_display'], y=val_trend_data['total_po_val'],
                    name='Nilai PO',
                    marker_color='#2ca02c',
                    customdata=val_trend_data[['hover_label', 'po_fmt']],
                    hovertemplate='<b>%{customdata[0]}</b><br>Nilai PO: %{customdata[1]}<extra></extra>'
                ))
                
                fig2.update_layout(barmode='group')
                max_val = max(val_trend_data['total_oe'].max(), val_trend_data['total_po_val'].max())

            fig2.update_layout(
                height=350,
                xaxis_title='',
                yaxis_title='Total Value (IDR)',
                yaxis={**idr_axis(max_val), 'gridcolor': 'rgba(128,128,128,0.1)'},
                xaxis=dict(
                    tickmode='array', tickvals=val_trend_data['month_display'].tolist(),
                    ticktext=val_trend_data['hover_label'].tolist(), tickangle=-30, showgrid=False
                ),
                margin=dict(t=60, b=10, l=10, r=30), # <-- Tambahkan padding internal di sini
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Tidak ada data tren nilai.")

    st.markdown('</div>', unsafe_allow_html=True)

    # Garis pemisah besar sebelum masuk Laporan Bagian
    st.markdown("<hr style='margin: 24px 0 16px 0; border-color: rgba(128,128,128,0.2);'>", unsafe_allow_html=True)

    # ═════════════════════════════════════════════════════════════════════════
    # BAGIAN 3: LAPORAN BAGIAN
    # ═════════════════════════════════════════════════════════════════════════
    
    # --- PEMBATAS HALAMAN 3 ---
    st.markdown('<div class="pagebreak"></div>', unsafe_allow_html=True)

    st.markdown(
        f"<h2 style='display:flex; align-items:center; font-size:32px; margin: 0 0 24px 0; font-weight:700; color:var(--text-color);'>"
        f"<span style='margin-right:12px; transform: translateY(4px); display:inline-flex; align-items:center;'>{_svg(ICONS['building'], 32)}</span>"
        f"Laporan Bagian"
        f"</h2>", 
        unsafe_allow_html=True
    )

    # Tombol Pills untuk memilih bagian
    pilihan_bagian = st.pills(
        "Pilih Bagian:", 
        options=["ALPATA", "BARUM", "BB/BD/BP"], 
        default="ALPATA",
        key="pills_laporan_bagian",
        label_visibility="collapsed"
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Kueri khusus untuk mengambil metrik performa (On Time, On Budget, Efisiensi, Lead Time) per Bagian dari SIPS
    bagian_query = f"""
    SELECT
        COUNT(*) AS total_pr,
        COUNT(CASE WHEN status IN ('Closed','Proses PO') THEN 1 END) AS total_po,
        ROUND(AVG(CASE WHEN status = 'Closed' THEN pr_po_days END)::numeric, 2) AS avg_pr_po,
        COALESCE(SUM(CASE WHEN status IN ('Closed','Proses PO') THEN nilai_sla END), 0) AS sla_ontime,
        COALESCE(SUM(CASE WHEN status IN ('Closed', 'Proses PO') THEN oe_pr END), 0) AS sips_oe_total,
        COALESCE(SUM(CASE WHEN status IN ('Closed', 'Proses PO') THEN nilai_item_po END), 0) AS sips_po_total,
        COUNT(CASE WHEN persen_po_sr_mr <= 1.0 AND status IN ('Closed','Proses PO') THEN 1 END) AS on_budget_count
    FROM vw_sips
    WHERE tgl_disposisi_buyer >= '{date_from}' AND tgl_disposisi_buyer <= '{date_to}'
      AND bagian = '{pilihan_bagian}'
    """

    with st.spinner(f"Memuat performa bagian {pilihan_bagian}..."):
        try:
            b_data = load_data(bagian_query)
        except Exception as e:
            st.error(f"Gagal memuat data bagian: {e}")
            b_data = pd.DataFrame()

    if not b_data.empty:
        # Ekstraksi dan Kalkulasi Data
        b_total_pr  = int(b_data['total_pr'][0] or 0)
        b_total_po  = int(b_data['total_po'][0] or 0)
        b_ontime    = float(b_data['sla_ontime'][0] or 0)
        b_lt        = float(b_data['avg_pr_po'][0] or 0)
        b_onbudget  = int(b_data['on_budget_count'][0] or 0)

        pct_ontime   = (b_ontime / b_total_po * 100) if b_total_po > 0 else 0.0
        pct_onbudget = (b_onbudget / b_total_po * 100) if b_total_po > 0 else 0.0
        
        b_sips_oe = float(b_data['sips_oe_total'][0] or 0)
        b_sips_po = float(b_data['sips_po_total'][0] or 0)
            
        b_efis_val   = b_sips_oe - b_sips_po
        b_efis_pct   = (b_efis_val / b_sips_oe * 100) if b_sips_oe > 0 else 0.0

        # Logika Warna (Hijau jika baik, Oranye/Merah jika kurang)
        col_onbudget = "#09ab3b" if pct_onbudget >= 80 else "#f0a500"
        col_ontime   = "#09ab3b" if pct_ontime >= 80 else "#f0a500"
        col_efis     = "#09ab3b" if b_efis_val >= 0 else "#e03c3c"
        
        # Format string agar koma/titik rapi
        str_onbudget = f"{pct_onbudget:.2f}%".replace('.', ',')
        str_ontime   = f"{pct_ontime:.2f}%".replace('.', ',')
        str_efis_pct = f"{b_efis_pct:+.2f}%".replace('.', ',')


        str_onbudget_tampil = str_onbudget
        tipe_budget_tampil  = "green" if pct_onbudget >= 80 else "red"
        
        str_efis_pct_tampil = str_efis_pct
        str_efis_val_tampil = format_idr(b_efis_val)
        tipe_efis_tampil    = "green" if b_efis_val >= 0 else "red"


        # == 4 KARTU KPI LAPORAN BAGIAN ==
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            st.markdown(_card(ICONS["currency"], "On Budget", str_onbudget_tampil, "", tipe_budget_tampil), unsafe_allow_html=True)
            
        with c2:
            tipe_time = "green" if pct_ontime >= 80 else "red"
            st.markdown(_card(ICONS["check_circle"], "On Time", str_ontime, "", tipe_time), unsafe_allow_html=True)
            
        with c3:
            st.markdown(_card(ICONS["clock"], "Lead Time (PR → PO)", f"{format_number(b_lt, decimals=2)} Hari", "Rata-rata kecepatan", "neutral"), unsafe_allow_html=True)
            
        with c4:
            st.markdown(_card(ICONS["graph_up"], "Efisiensi", str_efis_pct_tampil, str_efis_val_tampil, tipe_efis_tampil), unsafe_allow_html=True)

        st.markdown("<hr style='margin: 32px 0; border-color: rgba(128,128,128,0.2);'>", unsafe_allow_html=True)

        # == TABEL KINERJA KARYAWAN PER BAGIAN ==
        st.markdown(
            f"<h3 style='font-size:20px; margin-bottom:16px; color:var(--text-color);'>"
            f"<span style='margin-right:8px; vertical-align: middle;'>{_svg(ICONS['people'], 26)}</span>"
            f"<span style='vertical-align: middle;'>Kinerja Karyawan</span>"
            f"</h3>", 
            unsafe_allow_html=True
        )

        karyawan_query = f"""
        SELECT
            nama,
            COUNT(*) AS total_pr,
            COUNT(CASE WHEN status IN ('Closed','Proses PO') THEN 1 END) AS total_po,
            ROUND(AVG(CASE WHEN status = 'Closed' THEN pr_po_days END)::numeric, 2) AS avg_pr_po,
            COALESCE(SUM(CASE WHEN status IN ('Closed','Proses PO') THEN nilai_sla END), 0) AS sla_ontime,
            COALESCE(SUM(CASE WHEN status IN ('Closed', 'Proses PO') THEN oe_pr END), 0) AS sips_oe_total,
            COALESCE(SUM(CASE WHEN status IN ('Closed', 'Proses PO') THEN nilai_item_po END), 0) AS sips_po_total,
            COUNT(CASE WHEN persen_po_sr_mr <= 1.0 AND status IN ('Closed','Proses PO') THEN 1 END) AS on_budget_count
        FROM vw_sips
        WHERE tgl_disposisi_buyer >= '{date_from}' AND tgl_disposisi_buyer <= '{date_to}'
          AND bagian = '{pilihan_bagian}'
        GROUP BY nama
        ORDER BY total_pr DESC
        """

        with st.spinner(f"Memuat kinerja karyawan {pilihan_bagian}..."):
            karyawan_data = load_data(karyawan_query)

        if not karyawan_data.empty:
            df_karyawan = karyawan_data.copy()
            df_karyawan['Total PR'] = df_karyawan['total_pr']
            df_karyawan['Total PO'] = df_karyawan['total_po']
            df_karyawan['PO/PR'] = (df_karyawan['total_po'] / df_karyawan['total_pr'].replace(0, float('nan')) * 100).fillna(0).apply(lambda x: f"{x:.1f}%")
            df_karyawan['PR-PO (Hari)'] = df_karyawan['avg_pr_po'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "0.0")
            df_karyawan['% On Time'] = (df_karyawan['sla_ontime'] / df_karyawan['total_po'].replace(0, float('nan')) * 100).fillna(0)
            df_karyawan['Efisiensi Rp_val'] = df_karyawan['sips_oe_total'] - df_karyawan['sips_po_total']
            df_karyawan['Efisiensi %'] = (df_karyawan['Efisiensi Rp_val'] / df_karyawan['sips_oe_total'].replace(0, float('nan')) * 100).fillna(0)
            df_karyawan['% On Budget'] = (df_karyawan['on_budget_count'] / df_karyawan['total_po'].replace(0, float('nan')) * 100).fillna(0)
            df_karyawan['% On Spec'] = 99.30
            df_karyawan['OTOBOS'] = ((df_karyawan['% On Time'] + df_karyawan['% On Budget'] + df_karyawan['% On Spec']) / 3).fillna(0)
            df_karyawan['% On Time'] = df_karyawan['% On Time'].apply(lambda x: f"{x:.2f}%")
            df_karyawan['Efisiensi %'] = df_karyawan['Efisiensi %'].apply(lambda x: f"{x:.2f}%")
            df_karyawan['Efisiensi Rp'] = df_karyawan['Efisiensi Rp_val'].apply(lambda x: format_idr_short(x) if pd.notna(x) else "0")
            df_karyawan['% On Budget'] = df_karyawan['% On Budget'].apply(lambda x: f"{x:.2f}%")
            df_karyawan['% On Spec'] = df_karyawan['% On Spec'].apply(lambda x: f"{x:.2f}%")
            df_karyawan['OTOBOS'] = df_karyawan['OTOBOS'].apply(lambda x: f"{x:.2f}%")
            df_table = df_karyawan[['nama', 'Total PR', 'Total PO', 'PO/PR', 'PR-PO (Hari)', '% On Time', 'Efisiensi %', 'Efisiensi Rp', '% On Budget', '% On Spec', 'OTOBOS']].rename(columns={'nama': 'Nama'})
            df_table.index = df_table.index + 1
            st.dataframe(df_table, use_container_width=True)
        else:
            st.info(f"Tidak ada data kinerja karyawan untuk bagian **{pilihan_bagian}** pada periode ini.")
            
        st.markdown("<hr style='margin: 32px 0; border-color: rgba(128,128,128,0.2);'>", unsafe_allow_html=True)

        # == CHART TREN REALISASI ITEM PR-PO BAGIAN ==
        st.markdown(
            f"<h3 style='font-size:20px; margin-bottom:16px; color:var(--text-color);'>"
            f"<span style='margin-right:8px; vertical-align: middle;'>{_svg(ICONS['box'], 26)}</span>"
            f"<span style='vertical-align: middle;'>Tren Realisasi Item PR-PO</span>"
            f"</h3>", 
            unsafe_allow_html=True
        )

        trend_bagian_query = f"""
        SELECT
            DATE_TRUNC('month', tgl_disposisi_buyer) AS month,
            COUNT(*) AS total_pr,
            COUNT(CASE WHEN status IN ('Closed','Proses PO') THEN 1 END) AS total_po
        FROM vw_sips
        WHERE tgl_disposisi_buyer >= '{date_from}' AND tgl_disposisi_buyer <= '{date_to}'
          AND bagian = '{pilihan_bagian}'
        GROUP BY 1
        ORDER BY month
        """

        with st.spinner(f"Memuat tren bagian {pilihan_bagian}..."):
            trend_bagian_data = load_data(trend_bagian_query)

        if not trend_bagian_data.empty:
            # Format Data
            trend_bagian_data['month'] = pd.to_datetime(trend_bagian_data['month'])
            trend_bagian_data = trend_bagian_data.sort_values('month')
            trend_bagian_data['month_display'] = trend_bagian_data['month'].apply(resolve_month_date)
            trend_bagian_data['hover_label'] = trend_bagian_data['month_display'].apply(fmt_date)

            # Gambar Chart Bar (Barmode = Group agar bersebelahan)
            fig_trend_bagian = go.Figure()
            fig_trend_bagian.add_trace(go.Bar(
                x=trend_bagian_data['month_display'], y=trend_bagian_data['total_pr'],
                name='PR Created', marker_color='#1f77b4',
                customdata=trend_bagian_data[['hover_label']], hovertemplate='<b>%{customdata[0]}</b><br>PR Created: %{y}<extra></extra>'
            ))
            fig_trend_bagian.add_trace(go.Bar(
                x=trend_bagian_data['month_display'], y=trend_bagian_data['total_po'],
                name='PO Created', marker_color='#2ca02c',
                customdata=trend_bagian_data[['hover_label']], hovertemplate='<b>%{customdata[0]}</b><br>PO Created: %{y}<extra></extra>'
            ))
            
            fig_trend_bagian.update_layout(
                barmode='group', height=360, xaxis_title='', yaxis_title='Jumlah Item',
                xaxis=dict(tickmode='array', tickvals=trend_bagian_data['month_display'].tolist(), ticktext=trend_bagian_data['hover_label'].tolist(), tickangle=-30),
                margin=dict(t=60, b=10, l=10, r=30), # <-- Tambahkan padding internal di sini
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_trend_bagian, use_container_width=True)
        else:
            st.info(f"Tidak ada data tren untuk bagian **{pilihan_bagian}**.")
            
        st.markdown("<br><br>", unsafe_allow_html=True) # Jarak aman di paling bawah halaman
        
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info(f"Tidak ada transaksi PO untuk bagian **{pilihan_bagian}** pada periode ini.")