"""
v_sips_dashboard.py - Dashboard Monitoring SIPS
"""

import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from utils import format_idr, format_idr_short, format_number, format_currency, render_chat_analyst, build_sips_where, build_sips_bagian_cond

KPI_CSS = """
<style>
/* Copied from v_dashboard.py for consistency */
.dash-card, div[data-testid="stPlotlyChart"] {
    border-radius: 12px !important;
    background-color: var(--secondary-background-color) !important;
    background-image: linear-gradient(rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.08)) !important;
    border: 1px solid rgba(128, 128, 128, 0.25) !important;
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08) !important;
    page-break-inside: avoid;
    break-inside: avoid;
}

.dash-card {
    border-left-width: 6px !important;
    border-left-style: solid !important;
    border-left-color: var(--text-color) !important;
    display: flex;
    align-items: center;
    gap: 14px;
    min-height: 120px !important;
    height: 100%;
    padding: 20px 18px 16px 18px;
}

div[data-testid="stPlotlyChart"] {
    overflow: hidden !important;
}

.dash-icon {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    border-radius: 10px;
    background: rgba(128, 128, 128, 0.1) !important;
    color: var(--text-color) !important;
}

.dash-body { flex: 1; min-width: 0; }

.dash-label {
    font-size: 12.5px;
    margin: 0 0 6px 0 !important;
    padding-right: 25px;
    line-height: 1.3;
    font-weight: 500;
    color: var(--text-color) !important;
    opacity: 0.75;
}

.dash-value {
    font-size: 2rem !important;
    font-weight: 600 !important;
    margin: 0 0 4px 0 !important;
    padding: 0 !important;
    line-height: 1.1 !important;
    display: block !important;
}

.dash-delta { font-size: 12px; margin: 0; color: var(--text-color) !important; opacity: 0.6; }
.dash-delta-green { font-size: 12px; color: #09ab3b !important; margin: 0; font-weight: 600; }
.dash-delta-red   { font-size: 12px; color: #e03c3c !important; margin: 0; font-weight: 600; }
.dash-delta-orange{ font-size: 12px; color: #f0a500 !important; margin: 0; font-weight: 600; }

/* Posisi tombol popover di dalam kartu KPI */
div[data-testid="stHorizontalBlock"] > div {
    position: relative; /* Membuat setiap kolom menjadi container relatif */
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

ICONS = {
    "file-text":         "M5 4a.5.5 0 0 0 0 1h6a.5.5 0 0 0 0-1zm-.5 2.5A.5.5 0 0 1 5 6h6a.5.5 0 0 1 0 1H5a.5.5 0 0 1-.5-.5M5 8a.5.5 0 0 0 0 1h6a.5.5 0 0 0 0-1zm0 2a.5.5 0 0 0 0 1h3a.5.5 0 0 0 0-1zM3 0h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2m0 1a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1z",
    "bag":               "M8 1a2.5 2.5 0 0 1 2.5 2.5V4h-5v-.5A2.5 2.5 0 0 1 8 1m3.5 3v-.5a3.5 3.5 0 1 0-7 0V4H1v10a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V4zM2 5h12v9a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1z",
    "percent":           "M13.442 2.558a.625.625 0 0 1 0 .884l-10 10a.625.625 0 1 1-.884-.884l10-10a.625.625 0 0 1 .884 0M4.5 6a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3m0 1a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5m7 6a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3m0 1a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5",
    "clock":             "M8 3.5a.5.5 0 0 0-1 0V9a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0 0 .496-.868L8 8.71zM8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16m7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0",
    "check-circle":      "M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16M10.97 4.97a.235.235 0 0 0-.02.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-1.071-1.05",
    "currency-exchange": "M0 5a5 5 0 0 0 4.027 4.905 6.5 6.5 0 0 1 .544-2.073C3.231 7.51 1 6.44 1 5a3 3 0 0 1 3-3 3 3 0 0 1 2.959 2.516A6.5 6.5 0 0 1 8.975 3.59 4 4 0 0 0 4 1 4 4 0 0 0 0 5m13-1a3 3 0 0 1 0 6 3 3 0 0 1-2.959-2.516A6.5 6.5 0 0 1 7.025 8.41 4 4 0 0 0 12 11a4 4 0 0 0 4-4 4 4 0 0 0-3-3.874V1.5a.5.5 0 0 0-1 0v1.626A4 4 0 0 0 12 3a4 4 0 0 0-.941.11L9.65 1.7a.5.5 0 1 0-.707.707l1.41 1.41A4 4 0 0 0 8 5.5a3.5 3.5 0 0 1 7 0",
    "graph-up":          "M0 0h1v15h15v1H0zm14.817 3.113a.5.5 0 0 1 .07.704l-4.5 5.5a.5.5 0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5 0 0 1 .758-.06l2.609 2.61 4.15-5.073a.5.5 0 0 1 .704-.07",
    "graph-down":        "M0 0h1v15h15v1H0zm10 11.5a.5.5 0 0 0 .5.5h4a.5.5 0 0 0 .5-.5v-4a.5.5 0 0 0-1 0v2.6l-3.613-4.417a.5.5 0 0 0-.74-.037L7.06 8.233 3.404 3.206a.5.5 0 0 0-.808.588l4 5.5a.5.5 0 0 0 .758.06l2.609-2.61L13.445 11H10.5a.5.5 0 0 0-.5.5",
    "award":             "M9.669.864 8 0 6.331.864l-1.858.282-.842 1.68-1.337 1.32L2.6 6l-.306 1.854 1.337 1.32.842 1.68 1.858.282L8 12l1.669-.864 1.858-.282.842-1.68 1.337-1.32L13.4 6l.306-1.854-1.337-1.32-.842-1.68zm1.196 1.193.684 1.365 1.086 1.072L12.387 6l.248 1.506-1.086 1.072-.684 1.365-1.51.229L8 10.874l-1.355-.702-1.51-.229-.684-1.365-1.086-1.072L3.614 6l-.25-1.506 1.087-1.072.684-1.365 1.51-.229L8 1.126l1.356.702zM4 11.5a.5.5 0 0 0-.5.5v2.5a.5.5 0 0 0 1 0v-2H6a.5.5 0 0 0 0-1zm8 2H10v-2a.5.5 0 0 0-1 0V14.5a.5.5 0 0 0 .5.5H12a.5.5 0 0 0 0-1",
    "piggy-bank":        "M5.5 7.5a.5.5 0 1 0 0 1 .5.5 0 0 0 0-1M11 7.5a.5.5 0 1 0 0 1 .5.5 0 0 0 0-1M8 9.5a.5.5 0 1 0 0 1 .5.5 0 0 0 0-1m-3.5.5a.5.5 0 1 0 0 1 .5.5 0 0 0 0-1m7 0a.5.5 0 1 0 0 1 .5.5 0 0 0 0-1M4 0h8a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2zm8 1H4a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1",
    "budget":            "M0 3a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2zm2-1a1 1 0 0 0-1 1v1h14V3a1 1 0 0 0-1-1zm13 4H1v2h.5a.5.5 0 0 1 0 1H1v2h.5a.5.5 0 0 1 0 1H1v1a1 1 0 0 0 1 1h1v-1a.5.5 0 0 1 1 0v1h3v-1a.5.5 0 0 1 1 0v1h3v-1a.5.5 0 0 1 1 0v1h1a1 1 0 0 0 1-1v-1h-.5a.5.5 0 0 1 0-1H15V9h-.5a.5.5 0 0 1 0-1H15V6z",
}

def _svg(path_d: str, size: int = 40) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'fill="currentColor" viewBox="0 0 16 16"><path d="{path_d}"/></svg>')

def _card(icon_d: str, label: str, value: str,
          delta: str = "", delta_type: str = "neutral") -> str:
    delta_class = {
        "green":  "dash-delta-green",
        "red":    "dash-delta-red",
        "orange": "dash-delta-orange",
    }.get(delta_type, "dash-delta")
    delta_html = f'<p class="{delta_class}">{delta}</p>' if delta else ""
    return f"""<div class="dash-card">
    <div class="dash-icon">{_svg(icon_d, 36)}</div>
    <div class="dash-body">
        <p class="dash-label">{label}</p>
        <p class="dash-value">{value}</p>{delta_html}
        </div>
    </div>"""

def section_header(title, subtitle=""):
    sub_html = f"<p style='opacity:0.55; font-size:13px; margin:2px 0 0 0;'>{subtitle}</p>" if subtitle else ""
    st.markdown(f"""
        <div style='margin: 28px 0 12px 0;'>
            <h3 style='font-size:18px; font-weight:700; margin:0;'>{title}</h3>
            {sub_html}
        </div>
    """, unsafe_allow_html=True)

def render(load_data, date_from, date_to, selected_nama, selected_bagian=None, **kwargs):
    st.markdown(KPI_CSS, unsafe_allow_html=True)

    info_filter      = kwargs.get('info_filter', 'Tidak ada filter spesifik')
    selected_pgroup  = kwargs.get('selected_pgroup', ['All'])

    # == Header ================================================================
    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:60px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" fill="currentColor"
                 viewBox="0 0 16 16" style="margin-bottom:10px; margin-right:8px;">
                <path d="M10 .5a.5.5 0 0 0-.5-.5h-3a.5.5 0 0 0-.5.5.5.5 0 0 1-.5.5.5.5 0 0
                         0-.5.5V2a.5.5 0 0 0 .5.5h5A.5.5 0 0 0 11 2v-.5a.5.5 0 0 0-.5-.5.5.5
                         0 0 1-.5-.5"/>
                <path d="M4.085 1H3.5A1.5 1.5 0 0 0 2 2.5v12A1.5 1.5 0 0 0 3.5 16h9a1.5 1.5
                         0 0 0 1.5-1.5v-12A1.5 1.5 0 0 0 12.5 1h-.585q.084.236.085.5V2a1.5 1.5
                         0 0 1-1.5 1.5h-5A1.5 1.5 0 0 1 4 2v-.5q.001-.264.085-.5M10 7a1 1 0 1
                         1 2 0v5a1 1 0 1 1-2 0zm-6 4a1 1 0 1 1 2 0v1a1 1 0 1 1-2 0zm4-3a1 1 0
                         0 1 1 1v3a1 1 0 1 1-2 0V9a1 1 0 0 1 1-1"/>
            </svg>
            SIPS Monitoring Dashboard
        </h1>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # == WHERE clause ==========================================================
    # 1. Standard Where (menggunakan filter tanggal, untuk menghitung PR)
    where_pr = build_sips_where(
        date_from=date_from, date_to=date_to,
        selected_nama=selected_nama, selected_bagian=selected_bagian,
        selected_pgroup=selected_pgroup
    )

    # 2. Where khusus PO (tanpa filter tanggal pada tgl_disposisi_buyer,
    #    namun tetap meneruskan date_to agar filter bagian berbasis mutasi
    #    menggunakan date_to sebagai acuan — bukan tanggal transaksi)
    where_po = build_sips_where(
        date_from=None, date_to=None,
        selected_nama=selected_nama, selected_bagian=selected_bagian,
        selected_pgroup=selected_pgroup,
        extra=[build_sips_bagian_cond(selected_bagian, date_to=date_to)]
        if (selected_bagian and 'All' not in selected_bagian) else None
    )

    # 3. Kondisi filter tanggal PO untuk meniru behavior "COUNTIFS" di Excel secara harfiah
    po_date_cond = f"""(
        (tgl_po >= '{date_from}'::date AND tgl_po <= '{date_to}'::date)
        OR tgl_po IS NULL 
        OR tgl_po::text IN ('', '-')
    )"""

    # == Query KPI (Menggunakan pendekatan Subquery Mandiri) ====================
    kpi_query = f"""
        SELECT
            -- TOTAL PR: menggunakan filter tanggal global (where_pr)
            (SELECT COUNT(*) FROM vw_sips 
             WHERE {where_pr} 
            ) AS total_pr,

            -- TOTAL PO:
            (SELECT COUNT(*) FROM vw_sips 
             WHERE {where_po} 
               AND UPPER(TRIM(status)) IN ('CLOSED','PROSES PO')
               AND {po_date_cond}
            ) AS total_po,

            -- AVG PR PO
            (SELECT ROUND(AVG(pr_po_days)::numeric, 2) FROM vw_sips 
             WHERE {where_po} 
               AND UPPER(TRIM(status)) = 'CLOSED'
               AND {po_date_cond}
            ) AS avg_pr_po,

            -- SLA ONTIME
            (SELECT COALESCE(SUM(nilai_sla), 0) FROM vw_sips 
             WHERE {where_po} 
               AND UPPER(TRIM(status)) IN ('CLOSED','PROSES PO')
               AND {po_date_cond}
            ) AS sla_ontime,

            -- OE PROSES
            (SELECT COALESCE(SUM(oe_pr), 0) FROM vw_sips 
             WHERE {where_po} 
               AND UPPER(TRIM(status)) = 'PROSES PO'
               AND {po_date_cond}
            ) AS oe_proses,

            -- OE CLOSED
            (SELECT COALESCE(SUM(oe_pr), 0) FROM vw_sips 
             WHERE {where_po} 
               AND UPPER(TRIM(status)) = 'CLOSED'
               AND {po_date_cond}
            ) AS oe_closed,

            -- PO PROSES
            (SELECT COALESCE(SUM(nilai_item_po), 0) FROM vw_sips 
             WHERE {where_po} 
               AND UPPER(TRIM(status)) = 'PROSES PO'
               AND {po_date_cond}
            ) AS po_proses,

            -- PO CLOSED
            (SELECT COALESCE(SUM(nilai_item_po), 0) FROM vw_sips 
             WHERE {where_po} 
               AND UPPER(TRIM(status)) = 'CLOSED'
               AND {po_date_cond}
            ) AS po_closed,

            -- ON BUDGET COUNT
            (SELECT COUNT(*) FROM vw_sips 
             WHERE {where_po} 
               AND persen_po_sr_mr <= 1.0
               AND UPPER(TRIM(status)) IN ('CLOSED','PROSES PO')
               AND {po_date_cond}
            ) AS on_budget_count,

            -- SLA MISS
            (SELECT COUNT(*) FROM vw_sips 
             WHERE {where_po} 
               AND nilai_sla = 0
               AND UPPER(TRIM(status)) IN ('CLOSED','PROSES PO')
               AND {po_date_cond}
            ) AS sla_miss,

            -- Non Agreement variants
            (SELECT COALESCE(SUM(oe_pr), 0) FROM vw_sips 
             WHERE {where_po} 
               AND UPPER(TRIM(status)) = 'PROSES PO'
               AND {po_date_cond}
               AND (outline_agreement IS NULL OR TRIM(outline_agreement) = '')
            ) AS oe_proses_na,

            (SELECT COALESCE(SUM(oe_pr), 0) FROM vw_sips 
             WHERE {where_po} 
               AND UPPER(TRIM(status)) = 'CLOSED'
               AND {po_date_cond}
               AND (outline_agreement IS NULL OR TRIM(outline_agreement) = '')
            ) AS oe_closed_na,

            (SELECT COALESCE(SUM(nilai_item_po), 0) FROM vw_sips 
             WHERE {where_po} 
               AND UPPER(TRIM(status)) = 'PROSES PO'
               AND {po_date_cond}
               AND (outline_agreement IS NULL OR TRIM(outline_agreement) = '')
            ) AS po_proses_na,

            (SELECT COALESCE(SUM(nilai_item_po), 0) FROM vw_sips 
             WHERE {where_po} 
               AND UPPER(TRIM(status)) = 'CLOSED'
               AND {po_date_cond}
               AND (outline_agreement IS NULL OR TRIM(outline_agreement) = '')
            ) AS po_closed_na
    """

    # Query untuk breakdown SLA per prioritas
    sla_prio_query = f"""
        SELECT
            prioritas,
            COUNT(*) AS total_po,
            COALESCE(SUM(nilai_sla), 0) AS sla_ontime
        FROM vw_sips
        WHERE {where_po}
            AND UPPER(TRIM(status)) IN ('CLOSED', 'PROSES PO')
            AND {po_date_cond}
        GROUP BY prioritas
    """

    # == Query chart data ==
    chart_query = f"""
        SELECT
            nama,
            status,
            pr_po_days,
            COALESCE(nilai_sla, 0)   AS nilai_sla,
            CASE WHEN UPPER(TRIM(status)) IN ('CLOSED','PROSES PO')
                AND {po_date_cond}
            THEN 1 ELSE 0 END        AS is_po,
            CASE WHEN {where_pr} THEN 1 ELSE 0 END AS is_pr,  -- <--- TAMBAHKAN BARIS INI
            COALESCE(oe_pr, 0)       AS oe_pr,
            COALESCE(nilai_item_po, 0) AS nilai_item_po,
            b.bulan,
            outline_agreement
        FROM vw_sips
        LEFT JOIN LATERAL (
            SELECT TO_CHAR(DATE_TRUNC('month', tgl_disposisi_buyer), 'YYYY-MM') AS bulan
        ) AS b ON true
        WHERE ({where_pr}) OR ({where_po} AND {po_date_cond})
    """

    with st.spinner("Memuat data..."):
        try:
            df_kpi   = load_data(kpi_query)
            df_chart = load_data(chart_query)
            df_sla_prio = load_data(sla_prio_query)
        except Exception as e:
            st.error(f"Gagal memuat data: {e}")
            return

    no_data = df_kpi.empty or df_kpi.iloc[0].isnull().all()
    if no_data:
        st.info("Tidak ada data untuk filter yang dipilih.")

    if not no_data:
        r = df_kpi.iloc[0]

        # == Kalkulasi KPI =========================================================
        total_pr      = int(r['total_pr']       or 0)
        total_po      = int(r['total_po']       or 0)
        avg_pr_po     = float(r['avg_pr_po']    or 0)
        sla_ontime    = float(r['sla_ontime']   or 0)
        
        # Variabel General
        oe_proses     = float(r['oe_proses']    or 0)
        oe_closed     = float(r['oe_closed']    or 0)
        po_proses     = float(r['po_proses']    or 0)
        po_closed     = float(r['po_closed']    or 0)
        oe_total      = oe_proses + oe_closed
        po_total      = po_proses + po_closed

        # Variabel khusus Efisiensi (Non Agreement)
        oe_proses_na  = float(r['oe_proses_na'] or 0)
        oe_closed_na  = float(r['oe_closed_na'] or 0)
        po_proses_na  = float(r['po_proses_na'] or 0)
        po_closed_na  = float(r['po_closed_na'] or 0)
        oe_total_na   = oe_proses_na + oe_closed_na
        po_total_na   = po_proses_na + po_closed_na

        on_budget_cnt = int(r['on_budget_count']or 0)
        sla_miss      = int(r['sla_miss']       or 0)
        
        po_pr_pct     = (total_po / total_pr * 100)   if total_pr > 0 else 0.0
        pct_ontime    = (sla_ontime / total_po * 100) if total_po > 0 else 0.0
        
        # Perhitungan Efisiensi menggunakan data Non Agreement
        efisiensi_pct = (1 - po_total_na / oe_total_na) * 100 if oe_total_na > 0 else 0.0
        efisiensi_rp  = oe_total_na - po_total_na
        
        pct_on_budget = (on_budget_cnt / total_po * 100) if total_po > 0 else 0.0

        # Proses data SLA per prioritas
        sla_by_prio = {}
        sla_details_by_prio = {}
        if not df_sla_prio.empty and total_po > 0:
            for _, row in df_sla_prio.iterrows():
                prio = row['prioritas']
                ontime_prio = row['sla_ontime']
                total_po_prio = row['total_po']
                # (Jumlah on-time per prioritas / Total PO keseluruhan) * 100
                contribution_pct = (ontime_prio / total_po) * 100
                sla_by_prio[prio] = contribution_pct

                # Kalkulasi detail untuk delta text
                pct_memenuhi = (ontime_prio / total_po_prio * 100) if total_po_prio > 0 else 0.0
                sla_details_by_prio[prio] = {"pct_memenuhi": pct_memenuhi, "item_memenuhi": ontime_prio, "total_item": total_po_prio}

        prio_normal_pct = sla_by_prio.get('Normal', 0.0)
        prio_ta_pct = sla_by_prio.get('TA', 0.0)
        prio_investasi_pct = sla_by_prio.get('Investasi', 0.0)
        prio_urgent_pct = sla_by_prio.get('Urgent', 0.0)
        prio_emergency_pct = sla_by_prio.get('Emergency', 0.0)
        
        # == KPI_DASH: definisi 15 KPI dengan formula masing-masing ==============
        KPI_DASH = [
            # == Baris 1: PR / PO / PO-PR =========================================
            {
                "key":      "sips_kpi_total_pr",
                "icon":     "file-text",
                "label":    "Total PR",
                "value":    f"{format_number(total_pr)}",
                "delta":    "Semua status",
                "dtype":    "neutral",
                "formula":  f"""\
    **Total PR**: Jumlah Purchase Requisition dalam periode filter (semua status).

    **Formula Excel:**
    - Filter nama karyawan yang ingin dicari
    - Hitung seluruh baris

    **Target:** -""",
            },
            {
                "key":      "sips_kpi_total_po",
                "icon":     "bag",
                "label":    "Total PO",
                "value":    f"{format_number(total_po)}",
                "delta":    "Closed + Proses PO",
                "dtype":    "neutral",
                "formula":  f"""\
    **Total PO**: Jumlah PR yang sudah memiliki PO, yaitu yang berstatus *Closed* atau *Proses PO*.

    **Formula Excel:**
    - Filter nama karyawan yang ingin dicari
    - Filter **Status** menjadi `Closed` dan `Proses PO`
    - Hitung seluruh baris

    **Target:** -""",
            },
            {
                "key":      "sips_kpi_po_pr",
                "icon":     "percent",
                "label":    "PO/PR",
                "value":    f"{format_number(po_pr_pct, decimals=2)}%",
                "delta":    f"{format_number(total_po)} dari {format_number(total_pr)} PR",
                "dtype":    "positive" if po_pr_pct >= 80 else ("negative" if po_pr_pct < 60 else "neutral"),
                "formula":  f"""\
    **PO/PR**: Persentase PR yang sudah dikonversi menjadi PO.

    **Kalkulasi:**
    ```
    PO/PR = Total PO / Total PR x 100%
          = {total_po:,} / {total_pr:,} x 100%
          = {po_pr_pct:.1f}%
    ```

    | % | Interpretasi |
    |---|---|
    | ≥ 80% | 🟢 Baik |
    | 60–79% | 🟡 Perlu perhatian |
    | < 60% | 🔴 Banyak PR belum jadi PO |

    **Target:** -""",
            },
            # == Baris 2: PR-PO / SLA On Time / % On Time =========================
            {
                "key":      "sips_kpi_avg_pr_po",
                "icon":     "clock",
                "label":    "Rata-rata PR-PO",
                "value":    f"{format_number(avg_pr_po, decimals=2)} hari",
                "delta":    "Waktu PR → PO (Closed)",
                "dtype":    "neutral",
                "formula":  f"""\
    **Rata-rata PR-PO**: Rata-rata jumlah hari semua PR-PO dari **Tanggal Disposisi Buyer** hingga **Tanggal PO** per karyawan, khusus untuk dokumen yang sudah selesai/ditutup.

    **Formula Excel:**
    - Filter nama karyawan yang ingin dicari
    - Filter **Status** menjadi `Closed`
    - Hitung rata-rata **PR-PO**

    **Target:** -""",
            },
            {
                "key":      "sips_kpi_sla_ontime",
                "icon":     "check-circle",
                "label":    "SLA On Time",
                "value":    f"{format_number(int(sla_ontime))}",
                "delta":    f"dari {format_number(total_po)} PO",
                "dtype":    "neutral",
                "formula":  f"""\
    **SLA On Time**: Jumlah PO yang diselesaikan dalam batas SLA standar.

    **Formula Excel:**
    - Filter nama karyawan yang ingin dicari
    - Hitung nilai **1** pada **Nilai SLA**

    **Target:** -""",
            },
            # == Baris 3: OE =======================================================
            {
                "key":      "sips_kpi_oe_proses",
                "icon":     "currency-exchange",
                "label":    "OE Proses PO",
                "value":    format_idr(oe_proses),
                "delta":    "Nilai OE status Proses PO",
                "dtype":    "neutral",
                "formula":  f"""\
    **OE Proses PO**: Total nilai Owner's Estimate (anggaran) untuk PR yang sudah berstatus *Proses PO*.

    **Nilai saat ini: {format_currency(oe_proses)}**

    **Formula Excel:**
    - Filter nama karyawan yang ingin dicari
    - Filter **Status** menjadi `Proses PO`
    - Jumlahkan **OE PR**

    **Target:** -""",
            },
            {
                "key":      "sips_kpi_oe_closed",
                "icon":     "currency-exchange",
                "label":    "OE Closed",
                "value":    format_idr(oe_closed),
                "delta":    "Nilai OE status Closed",
                "dtype":    "neutral",
                "formula":  f"""\
    **OE Closed**: Total nilai Owner's Estimate untuk PR yang sudah berstatus *Closed*.

    **Nilai saat ini: {format_currency(oe_closed)}**

    **Formula Excel:**
    - Filter nama karyawan yang ingin dicari
    - Filter **Status** menjadi `Closed`
    - Jumlahkan **OE PR**

    **Target:** -""",
            },
            {
                "key":      "sips_kpi_oe_total",
                "icon":     "currency-exchange",
                "label":    "Total OE",
                "value":    format_idr(oe_total),
                "delta":    "OE Proses PO + OE Closed",
                "dtype":    "neutral",
                "formula":  f"""\
    **Total OE**: Gabungan OE untuk status *Proses PO* dan *Closed*.

    **Nilai saat ini: {format_currency(oe_total)}**

    **Kalkulasi:**
    ```
    Total OE = OE Proses PO + OE Closed
             = {format_currency(oe_proses)} + {format_currency(oe_closed)}
             = {format_currency(oe_total)}
    ```

    **Target:** -""",
            },
            # == Baris 4: Nilai PO =================================================
            {
                "key":      "sips_kpi_po_proses",
                "icon":     "budget",
                "label":    "PO Proses PO",
                "value":    format_idr(po_proses),
                "delta":    "Nilai PO status Proses PO",
                "dtype":    "neutral",
                "formula":  f"""\
    **PO Proses PO**: Total nilai realisasi PO untuk yang berstatus *Proses PO*.

    **Nilai saat ini: {format_currency(po_proses)}**

    **Formula Excel:**
    - Filter nama karyawan yang ingin dicari
    - Filter **Status** menjadi `Proses PO`
    - Jumlahkan **Nilai Item PO**

    **Target:** -""",
            },
            {
                "key":      "sips_kpi_po_closed",
                "icon":     "budget",
                "label":    "PO Closed",
                "value":    format_idr(po_closed),
                "delta":    "Nilai PO status Closed",
                "dtype":    "neutral",
                "formula":  f"""\
    **PO Closed**: Total nilai realisasi PO untuk yang berstatus *Closed*.

    **Nilai saat ini: {format_currency(po_closed)}**

    **Formula Excel:**
    - Filter nama karyawan yang ingin dicari
    - Filter **Status** menjadi `Closed`
    - Jumlahkan **Nilai Item PO**

    **Target:** -""",
            },
            {
                "key":      "sips_kpi_po_total",
                "icon":     "budget",
                "label":    "Total PO",
                "value":    format_idr(po_total),
                "delta":    "PO Proses PO + PO Closed",
                "dtype":    "neutral",
                "formula":  f"""\
    **Total PO (Nilai)**: Gabungan realisasi nilai PO untuk status *Proses PO* dan *Closed*.

    **Nilai saat ini: {format_currency(po_total)}**

    **Kalkulasi:**
    ```
    Total PO = PO Proses PO + PO Closed
             = {format_currency(po_proses)} + {format_currency(po_closed)}
             = {format_currency(po_total)}
    ```

    **Target:** -""",
            },
            # == Baris 5: Efisiensi & On Budget ===================================
            {
                "key":      "sips_kpi_efisiensi_pct",
                "icon":     "graph-up",
                "label":    "Efisiensi %",
                "value":    f"{format_number(efisiensi_pct, decimals=2)}%",
                "delta":    "PO Non Agreement",
                "dtype":    "positive" if efisiensi_pct > 0 else "negative",
                "formula":  f"""\
    **Efisiensi %**: Persentase penghematan dari selisih OE dengan realisasi nilai PO (Hanya untuk jenis kontrak Non Agreement).

    **Formula Excel:**
    ```
    = 1 - (PO Proses PO + PO Closed) / (OE Proses PO + OE Closed)
    ```
    *(Difilter hanya untuk baris dengan status Non Agreement)*

    **Kalkulasi:**
    ```
    Efisiensi % = 1 - (Total PO NA / Total OE NA) x 100%
                = 1 - ({format_currency(po_total_na)} / {format_currency(oe_total_na)}) x 100%
                = {efisiensi_pct:.2f}%
    ```

    | % | Interpretasi |
    |---|---|
    | > 0% | 🟢 Ada penghematan |
    | = 0% | 🟡 Tepat anggaran |
    | < 0% | 🔴 Over budget |

    **Target:** -""",
            },
            {
                "key":      "sips_kpi_efisiensi_rp",
                "icon":     "piggy-bank",
                "label":    "Efisiensi Rp",
                "value":    format_idr(efisiensi_rp),
                "delta":    "PO Non Agreement",
                "dtype":    "positive" if efisiensi_rp > 0 else "negative",
                "formula":  f"""\
    **Efisiensi Rp**: Nominal penghematan dalam Rupiah (Hanya untuk jenis kontrak Non Agreement).

    **Nilai saat ini: {format_currency(efisiensi_rp)}**

    **Formula Excel:**
    ```
    = (OE Proses PO + OE Closed) - (PO Proses PO + PO Closed)
    ```
    *(Difilter hanya untuk baris dengan status Non Agreement)*

    **Kalkulasi:**
    ```
    Efisiensi Rp = Total OE NA - Total PO NA
                 = {format_currency(oe_total_na)} - {format_currency(po_total_na)}
                 = {format_currency(efisiensi_rp)}
    ```

    Nilai positif berarti realisasi PO lebih rendah dari anggaran OE.

**Target:** -""",
        },
        {
            "key":      "sips_kpi_on_budget",
            "icon":     "check-circle",
            "label":    "% On Budget",
            "value":    f"{format_number(pct_on_budget)}%",
            "delta":    f"{format_number(on_budget_cnt)} dari {format_number(total_po)} PO ≤ 100%",
            "dtype":    "positive" if pct_on_budget >= 80 else ("negative" if pct_on_budget < 60 else "neutral"),
            "formula":  f"""\
**% On Budget**: Persentase PO yang nilai realisasinya tidak melebihi nilai MR/SR (kolom Z ≤ 100%).

**Formula Excel:**
- Filter nama karyawan yang ingin dicari
- Filter **Status** menjadi `Proses PO` dan `Closed`
- Filter **Persentase PO/SR atau PO/MR** kurang dari sama dengan 100% lalu dibagi **Total PO**

| % | Interpretasi |
|---|---|
| ≥ 80% | 🟢 Baik |
| 60–79% | 🟡 Perlu perhatian |
| < 60% | 🔴 Banyak over budget |

**Target:** -""",
        },
    ]

    # == Helper: render satu baris (max 3 KPI) dengan tombol formula ==========
    def render_kpi_row(items):
        cols = st.columns(3)
        for i, col in enumerate(cols):
            with col:
                if i >= len(items):
                    continue
                kpi     = items[i]

                delta_type_map = {"positive": "green", "negative": "red"}
                delta_type = delta_type_map.get(kpi["dtype"], "neutral")
                st.markdown(_card(ICONS[kpi["icon"]], kpi["label"], kpi["value"], kpi["delta"], delta_type), unsafe_allow_html=True)
                with st.popover(":material/visibility:", help="Lihat Formula"):
                    st.info(kpi["formula"])

    # == Render 5 baris x 3 KPI ===============================================
    for row_start in range(0, len(KPI_DASH), 3):
        row_items = KPI_DASH[row_start:row_start + 3]
        render_kpi_row(row_items)
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # == Bagian Baru: Pemenuhan SLA berdasarkan Prioritas =====================
    title_col, btn_col = st.columns([9, 1])
    with title_col:
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:24px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                    <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16M8 13A5 5 0 1 1 8 3a5 5 0 0 1 0 10m0 1A6 6 0 1 0 8 2a6 6 0 0 0 0 12m0-9a3 3 0 1 1 0 6 3 3 0 0 1 0-6m0 1a2 2 0 1 0 0 4 2 2 0 0 0 0-4"/>
                </svg>
                Pemenuhan SLA berdasarkan Prioritas
            </h1>
        """, unsafe_allow_html=True)
    with btn_col:
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Lihat Formula"):
            st.info("""**Pemenuhan SLA berdasarkan Prioritas**: Kontribusi persentase dari PO dengan prioritas tertentu yang on-time terhadap total PO keseluruhan.

**Kalkulasi:**
% Kontribusi = (Total PO On Time Prioritas X) / (Total PO Keseluruhan) x 100%""")

    # Data untuk kartu-kartu dipisah agar lebih mudah diatur layout-nya
    card_overall = {"label": "% On Time SLA", "value": pct_ontime, "icon": "award", "prio": "Overall"}
    
    sla_prio_cards = [
        {"label": "% Kontribusi Normal", "value": prio_normal_pct, "icon": "check-circle", "prio": "Normal"},
        {"label": "% Kontribusi TA", "value": prio_ta_pct, "icon": "check-circle", "prio": "TA"},
        {"label": "% Kontribusi Investasi", "value": prio_investasi_pct, "icon": "check-circle", "prio": "Investasi"},
        {"label": "% Kontribusi Urgent", "value": prio_urgent_pct, "icon": "check-circle", "prio": "Urgent"},
        {"label": "% Kontribusi Emergency", "value": prio_emergency_pct, "icon": "check-circle", "prio": "Emergency"},
    ]

    # Buat layout kolom utama: Kiri (Besar), Kanan (List Prioritas)
    col_main_left, col_main_right = st.columns([1, 3], gap="small")

    # ==========================================
    # 1. KARTU UTAMA DI KIRI (Besar & Memanjang)
    # ==========================================
    with col_main_left:
        # Ubah delta_text di bawah ini
        delta_text = f"{format_number(sla_miss)} Item dari {format_number(total_po)} Tidak Memenuhi"
        
        delta_type = "positive" if card_overall["value"] >= 80 else "negative"
        delta_class = "dash-delta-green" if delta_type == "positive" else "dash-delta-red"
        
        # Memanipulasi CSS agar memanjang (min-height ~256px), flex-col (atas bawah), dan divider di kanan
        st.markdown(f"""
        <div style="border-right: 2px solid rgba(128,128,128,0.2); padding-right: 20px; height: 100%;">
            <div class="dash-card" style="min-height: 256px !important; flex-direction: column; justify-content: center; text-align: center; align-items: center;">
                <div class="dash-icon" style="margin-bottom: 16px; width: 64px; height: 64px;">
                    {_svg(ICONS[card_overall["icon"]], 40)}
                </div>
                <div class="dash-body">
                    <p class="dash-label" style="font-size: 14px; margin-bottom: 8px !important;">{card_overall["label"]}</p>
                    <p class="dash-value" style="font-size: 3rem !important;">{format_number(card_overall['value'], decimals=2)}%</p>
                    <p class="{delta_class}">{delta_text}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.popover(":material/visibility:", help="Lihat Formula"):
            st.info(f"""**% On Time SLA (Overall)**: Persentase PO yang diselesaikan tepat waktu dari total PO.

**Kalkulasi:**
```
% On Time = SLA On Time / Total PO × 100%
= {format_number(int(sla_ontime))} / {format_number(total_po)} × 100%
= {format_number(pct_ontime, decimals=2)}%
```""")
                
        # ==========================================
        # 2. KARTU PRIORITAS DI KANAN (2 Baris)
        # ==========================================
        with col_main_right:
            # Fungsi bantuan untuk render kartu kecil agar kode tidak berulang
            def render_small_card(card_data):
                prio_details = sla_details_by_prio.get(card_data["prio"], {"pct_memenuhi": 0.0, "item_memenuhi": 0, "total_item": 0})
                pct_memenuhi = prio_details["pct_memenuhi"]
                item_memenuhi = prio_details["item_memenuhi"]
                total_item_prio = prio_details["total_item"]
                
                c_delta_text = f"{format_number(pct_memenuhi, decimals=1)}% | {format_number(int(item_memenuhi))} dari {format_number(int(total_item_prio))} Item"
                c_delta_type = "positive" if card_data["value"] >= 80 else "negative"
                
                st.markdown(_card(
                    ICONS[card_data["icon"]], 
                    card_data["label"], 
                    f"{format_number(card_data['value'], decimals=2)}%",
                    c_delta_text, 
                    c_delta_type
                ), unsafe_allow_html=True)
                
                with st.popover(":material/visibility:", help="Lihat Formula"):
                    st.info(f"""**Kontribusi SLA (Prioritas {card_data['prio']})**: Kontribusi persentase dari PO prioritas '{card_data['prio']}' yang on-time terhadap total PO keseluruhan.

**Kalkulasi:**
% On Time = (Total PO On Time Prioritas '{card_data['prio']}') / (Total PO Prioritas '{card_data['prio']}') × 100%
                    """)

        # --- Baris 1: 3 Kartu (Normal, TA, Investasi) ---
            r1_cols = st.columns(3)
            for j in range(3):
                with r1_cols[j]:
                    render_small_card(sla_prio_cards[j])
            
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True) # Spacing antar baris
            
            # --- Baris 2: 2 Kartu (Urgent, Emergency) ---
            r2_cols = st.columns(3) # Tetap pakai 3 kolom agar ukurannya konsisten dengan atasnya
            for j in range(3, 5):
                with r2_cols[j-3]: # Index 0 dan 1 (kolom kiri dan tengah)
                    render_small_card(sla_prio_cards[j])
            
            # Kolom ke-3 di baris 2 dibiarkan kosong secara otomatis oleh Streamlit


    # =========================================================================
    # CHARTS
    # =========================================================================

    COLORS = {
        "Open":      "#6c8ebf",
        "Proses PO": "#f0a500",
        "Closed":    "#09ab3b",
    }

    # == ROW 1: PR-PO Trend & Distribusi Status =============================
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    # == KIRI: LINE CHART TREND ==
    with col1:
        title_col, btn_col = st.columns([9, 1])
        with title_col:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:24px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-graph-up" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                        <path fill-rule="evenodd" d="M0 0h1v15h15v1H0zm14.817 3.113a.5.5 0 0 1 .07.704l-4.5 5.5a.5.5 0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5 0 0 1 .758-.06l2.609 2.61 4.15-5.073a.5.5 0 0 1 .704-.07"/>
                    </svg>
                    Pipeline & Trend PR-PO SIPS
                </h1>
            """, unsafe_allow_html=True)
        with btn_col:
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Lihat Formula"):
                st.info("""\
**Pipeline & Trend PR-PO SIPS**: Line chart jumlah PR dan PO yang dibuat per bulan.
                    
**Formula Excel:**
- Filter nama karyawan yang ingin dicari
- Filter **Requisition Date** sesuai bulan yang diinginkan
- Hitung seluruh baris untuk menghitung **Total PR**
- Filter **Status** menjadi `Proses PO` dan `Closed` untuk menghitung **Total PO** """)

        st.caption("Distribusi volume PR-PO per bulan.")
        
        if 'bulan' in df_chart.columns and df_chart['bulan'].notna().any():
            trend = (df_chart.groupby('bulan')
                     .agg(Total_PR=('is_pr', 'sum'),
                          Total_PO=('is_po', 'sum'))
                     .reset_index()
                     .sort_values('bulan'))
            
            # 1. Konversi 'YYYY-MM' ke tanggal 1 awal bulan terlebih dahulu
            trend['bulan'] = pd.to_datetime(trend['bulan'])

            # 2. Hitung kumulatif SEBELUM filter. 
            # (Agar backlog/saldo awal sebelum date_from tetap masuk ke total kumulatif)
            trend['Cum_PR'] = trend['Total_PR'].cumsum()
            trend['Cum_PO'] = trend['Total_PO'].cumsum()

            # 3. Sesuaikan batas filter agar hanya mengecek Tahun & Bulannya saja
            dt_from = pd.to_datetime(date_from).replace(day=1)
            dt_to_month = pd.to_datetime(date_to).replace(day=1)

            # 4. Eksekusi filter untuk memotong tampilan chart
            trend = trend[(trend['bulan'] >= dt_from) & (trend['bulan'] <= dt_to_month)]

            # 5. Geser ke akhir bulan, TAPI batasi maksimal ke tanggal akhir filter (date_to)
            dt_to_exact = pd.to_datetime(date_to)
            trend['bulan'] = (trend['bulan'] + pd.offsets.MonthEnd(0)).clip(upper=dt_to_exact)

            if trend.empty:
                st.info("Tidak ada data tren untuk filter tanggal yang dipilih.")
            else:
                show_cumulative = st.toggle("Tampilkan Kumulatif", value=False, key="toggle_trend_sips")
                
                if show_cumulative:
                    y_pr = trend['Cum_PR']
                    y_po = trend['Cum_PO']
                    y_axis_title = 'Total Akumulasi'
                else:
                    y_pr = trend['Total_PR']
                    y_po = trend['Total_PO']
                    y_axis_title = 'Jumlah per Bulan'

                fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=trend['bulan'], y=y_pr,
                name='Total PR', mode='lines+markers',
                line=dict(color='#6c8ebf', width=2),
                marker=dict(size=6),
                hovertemplate='<b>%{x|%b %d, %Y}</b><br>Total PR: %{y}<extra></extra>'
            ))
            fig_trend.add_trace(go.Scatter(
                x=trend['bulan'], y=y_po,
                name='Total PO', mode='lines+markers',
                line=dict(color='#f0a500', width=2),
                marker=dict(size=6),
                hovertemplate='<b>%{x|%b %d, %Y}</b><br>Total PO: %{y}<extra></extra>'
            ))
            
            fig_trend.update_layout(
                height=300, 
                margin=dict(t=40, b=40, l=20, r=20),
                legend=dict(orientation='h', yanchor='bottom', y=1.02),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='gray',
                xaxis=dict(
                    gridcolor='rgba(128,128,128,0.15)',
                    tickmode='array',
                    tickvals=trend['bulan'],
                    ticktext=trend['bulan'].dt.strftime('%b %Y') # Memastikan sumbu X bawah tetap "Jan 2026"
                ),
                yaxis=dict(title=y_axis_title, gridcolor='rgba(128,128,128,0.15)'),
                separators=",."
            )
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("Tidak ada data untuk filter yang dipilih.")

    # == KANAN: PIE CHART DISTRIBUSI STATUS ==
    with col2:
        title_col, btn_col = st.columns([9, 1])
        with title_col:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:24px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-pie-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                        <path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16m.93-9.412-1 4.705c-.07.34.029.533.304.533.194 0 .487-.07.686-.246l-.088.416c-.287.346-.92.598-1.465.598-.703 0-1.002-.422-.808-1.319l.738-3.468c.064-.293.006-.399-.287-.47l-.451-.081.082-.381 2.29-.287zM8 5.5a1 1 0 1 1 0-2 1 1 0 0 1 0 2"/>
                    </svg>
                    Distribusi Status PR SIPS
                </h1>
            """, unsafe_allow_html=True)
        with btn_col:
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Lihat Formula"):
                st.info("""\
**Distribusi Status PR SIPS**: Pie chart persentase jumlah dokumen berdasarkan status akhirnya.

**Formula Excel:**
- Filter nama karyawan yang ingin dicari
- Filter **Status** sesuai yang diinginkan
                    
""")
        st.caption("Distribusi status PR SIPS.")

        if df_chart.empty:
            st.info("Tidak ada data untuk filter yang dipilih.")
        else:
            pr_data = df_chart[df_chart['is_pr'] == 1]
            status_counts = pr_data['status'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Jumlah']
            fig_donut = px.pie(
                status_counts, names='Status', values='Jumlah',
                hole=0.4, color='Status', color_discrete_map=COLORS,
            )
            fig_donut.update_traces(
                textposition='inside', textinfo='percent',
                hovertemplate='<b>%{label}</b><br>Jumlah: %{value}<br>Persorsi: %{percent}<extra></extra>'
            )
            fig_donut.update_layout(
                showlegend=True,
                legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05),
                margin=dict(t=40, b=40, l=20, r=20), height=300,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font_color='gray', separators=",."
            )
            st.plotly_chart(fig_donut, use_container_width=True)

    # == ROW 2: Performa SLA & Histori Lead Time =============================
    st.markdown("---")

    col_l, col_r = st.columns(2)
    # == KIRI: HORIZONTAL BAR % ON TIME ==
    with col_l:
        title_col, btn_col = st.columns([9, 1])
        with title_col:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:24px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-award-fill" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                        <path d="m8 0 1.669.864 1.858.282.842 1.68 1.337 1.32L13.4 6l.306 1.854-1.337 1.32-.842 1.68-1.858.282L8 12l-1.669-.864-1.858-.282-.842-1.68-1.337-1.32L2.6 6l-.306-1.854 1.337-1.32.842-1.68 1.858-.282z"/>
                        <path d="M4 11.794V16l4-1 4 1v-4.206l-2.018.306L8 13.126 6.018 12.1z"/>
                    </svg>
                    Performa SLA per Karyawan
                </h1>
            """, unsafe_allow_html=True)
        with btn_col:
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Lihat Formula"):
                st.info("""\
    **Performa SLA per Karyawan**: Bar chart persentase pencapaian SLA tepat waktu untuk setiap karyawan.
                    
    **Kalkulasi:**
    ```
    % On Time = SLA On Time / Total PO × 100%
    ```

    Dihitung khusus untuk PR yang berstatus Closed atau Proses PO.
        """)
        
        st.caption("Persentase pencapaian SLA tepat waktu untuk setiap karyawan.")

        if 'nama' in df_chart.columns:
            perf = (df_chart[df_chart['is_po'] == 1]
                    .groupby('nama')
                    .agg(total_po=('is_po', 'sum'),
                        sla_ok=('nilai_sla', 'sum'))
                    .reset_index())
            if not perf.empty:
                perf['pct_ontime'] = (perf['sla_ok'] / perf['total_po'] * 100).round(2)
                perf = perf.sort_values('pct_ontime', ascending=True)

                fig_ontime = px.bar(
                    perf, y='nama', x='pct_ontime', orientation='h',
                    text=perf['pct_ontime'].apply(lambda x: f"{format_number(x, decimals=2)}%"),
                    color='pct_ontime',
                    color_continuous_scale=[[0, '#e03c3c'], [0.6, '#f0a500'], [1, '#09ab3b']],
                    range_color=[0, 100],
                )
                fig_ontime.update_traces(textposition='outside')
                fig_ontime.update_coloraxes(showscale=False)
                fig_ontime.update_layout(
                    height=max(250, len(perf) * 38),
                    margin=dict(t=20, b=20, l=20, r=60),
                    xaxis=dict(title='% On Time', range=[0, 115],
                            gridcolor='rgba(128,128,128,0.15)'),
                    yaxis=dict(title=''),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='gray',
                    separators=",."
                )
                st.plotly_chart(fig_ontime, use_container_width=True)
            else:
                st.info("Tidak ada data untuk filter yang dipilih.")
        else:
            st.info("Tidak ada data untuk filter yang dipilih.")

    # == KANAN: HISTOGRAM PR-PO DAYS ==
    with col_r:
        title_col, btn_col = st.columns([9, 1])
        with title_col:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:24px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-clock-history" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                        <path d="M8.515 1.019A7 7 0 0 0 8 1V0a8 8 0 0 1 .589.022zm2.004.45a7 7 0 0 0-.985-.299l.219-.976q.576.129 1.126.342zm1.37.71a7 7 0 0 0-.439-.27l.493-.87a8 8 0 0 1 .979.654l-.615.789a7 7 0 0 0-.418-.302zm1.834 1.79a7 7 0 0 0-.653-.796l.724-.69q.406.429.747.91zm.744 1.352a7 7 0 0 0-.214-.468l.893-.45a8 8 0 0 1 .45 1.088l-.95.313a7 7 0 0 0-.179-.483m.53 2.507a7 7 0 0 0-.1-1.025l.985-.17q.1.58.116 1.17zm-.131 1.538q.05-.254.081-.51l.993.123a8 8 0 0 1-.23 1.155l-.964-.267q.069-.247.12-.501m-.952 2.379q.276-.436.486-.908l.914.405q-.24.54-.555 1.038zm-.964 1.205q.183-.183.35-.378l.758.653a8 8 0 0 1-.401.432z"/>
                        <path d="M8 1a7 7 0 1 0 4.95 11.95l.707.707A8.001 8.001 0 1 1 8 0z"/>
                        <path d="M7.5 3a.5.5 0 0 1 .5.5v5.21l3.248 1.856a.5.5 0 0 1-.496.868l-3.5-2A.5.5 0 0 1 7 9V3.5a.5.5 0 0 1 .5-.5"/>
                    </svg>
                    Distribusi Waktu PR → PO
                </h1>
            """, unsafe_allow_html=True)
        with btn_col:
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Lihat Formula"):
                st.info("""\
    **Distribusi Waktu PR → PO**: Histogram persebaran jumlah PR berdasarkan lama proses pembuatannya (dalam satuan hari).

    Membantu mengidentifikasi apakah mayoritas dokumen selesai dalam rentang waktu yang normal, atau terdapat banyak outlier yang memakan waktu sangat lama (ekor grafik yang panjang ke kanan).
    """)
            
        st.caption("Persebaran hari PR→PO seluruh karyawan.")

        days_data = df_chart[
            (df_chart['is_po'] == 1) & 
            (df_chart['status'].str.upper() == 'CLOSED') & 
            df_chart['pr_po_days'].notna() & 
            (df_chart['pr_po_days'] > 0)
        ]
        if not days_data.empty:
            fig_hist = px.histogram(
                days_data, x='pr_po_days', nbins=30,
                color_discrete_sequence=['#6c8ebf'],
            )
            avg_days = days_data['pr_po_days'].mean()
            fig_hist.add_vline(x=avg_days, line_dash='dash', line_color='#f0a500',
                            annotation_text=f"Rata-rata {format_number(avg_days, decimals=2)} hari",
                            annotation_position='top right')
            fig_hist.update_layout(
                height=max(250, len(perf) * 38) if ('perf' in locals() and not perf.empty) else 320,
                margin=dict(t=20, b=20, l=20, r=20),
                xaxis=dict(title='Hari PR → PO', gridcolor='rgba(128,128,128,0.15)'),
                yaxis=dict(title='Jumlah PR', gridcolor='rgba(128,128,128,0.15)'),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='gray',
                showlegend=False,
                separators=",."
            )
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("Tidak ada data untuk filter yang dipilih.")

    # == ROW 3: Beban Kerja (Volume PR & PO) per Karyawan ====================
    st.markdown("---")

    title_col, btn_col = st.columns([19, 1])
    with title_col:
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:24px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-person-lines-fill" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                    <path d="M6 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm-5 6s-1 0-1-1 1-4 6-4 6 3 6 4-1 1-1 1H1zM11 3.5a.5.5 0 0 1 .5-.5h4a.5.5 0 0 1 0 1h-4a.5.5 0 0 1-.5-.5zm.5 2.5a.5.5 0 0 0 0 1h4a.5.5 0 0 0 0-1h-4zm2 3a.5.5 0 0 0 0 1h2a.5.5 0 0 0 0-1h-2zm0 3a.5.5 0 0 0 0 1h2a.5.5 0 0 0 0-1h-2z"/>
                </svg>
                Beban Kerja (Volume Dokumen) per Karyawan
            </h1>
        """, unsafe_allow_html=True)
    with btn_col:
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Lihat Formula"):
            st.info("""\
    **Beban Kerja per Karyawan**: Bar chart ini menghitung frekuensi dokumen PR yang ditangani oleh masing-masing karyawan, serta seberapa banyak yang sudah berhasil dikonversi menjadi PO.
    """)
        
    st.caption("Perbandingan total dokumen PR yang ditugaskan and diselesaikan (PO) oleh masing-masing karyawan.")

    if 'nama' in df_chart.columns:
        vol = (df_chart.groupby('nama')
            .agg(Total_PR=('is_pr', 'sum'), Total_PO=('is_po', 'sum'))
            .reset_index())
        
        if not vol.empty:
            vol = vol.sort_values('Total_PR', ascending=True)

            fig_vol = go.Figure()
            fig_vol.add_bar(y=vol['nama'], x=vol['Total_PR'], name='Total PR', text=vol['Total_PR'],
                            orientation='h', marker_color='#6c8ebf', opacity=0.85)
            fig_vol.add_bar(y=vol['nama'], x=vol['Total_PO'], name='Total PO', text=vol['Total_PO'],
                            orientation='h', marker_color='#f0a500', opacity=0.85)
            
            fig_vol.update_traces(textposition='outside')
            fig_vol.update_layout(
                barmode='group',
                height=max(250, len(vol) * 48),
                margin=dict(t=20, b=20, l=20, r=40), 
                legend=dict(orientation='h', yanchor='bottom', y=1.01),
                xaxis=dict(title='Jumlah Dokumen', gridcolor='rgba(128,128,128,0.15)'), 
                yaxis=dict(title=''),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='gray',
                separators=",."
            )
            st.plotly_chart(fig_vol, use_container_width=True)
        else:
            st.info("Tidak ada data untuk filter yang dipilih.")
    else:
        st.info("Tidak ada data untuk filter yang dipilih.")

    # == ROW 4: Proporsi PO Kontrak vs Non-Kontrak ============================
    st.markdown("---")

    title_col_k, btn_col_k = st.columns([19, 1])
    with title_col_k:
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:24px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-file-earmark-check-fill" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                    <path d="M9.293 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4.707A1 1 0 0 0 13.707 4L10 .293A1 1 0 0 0 9.293 0zM9.5 3.5v-2l3 3h-2a1 1 0 0 1-1-1zm1.354 4.354-3 3a.5.5 0 0 1-.708 0l-1.5-1.5a.5.5 0 1 1 .708-.708L7.5 9.793l2.646-2.647a.5.5 0 0 1 .708.708z"/>
                </svg>
                Proporsi PO Kontrak vs Non-Kontrak per Karyawan
            </h1>
        """, unsafe_allow_html=True)
    with btn_col_k:
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Lihat Formula"):
            st.info("""\
**Proporsi PO Kontrak vs Non-Kontrak**: Stacked bar chart ini menunjukkan berapa banyak item PO yang dibuat menggunakan kontrak payung (*Outline Agreement*) dibandingkan yang tidak.

**Formula Excel:**
- Filter nama karyawan yang ingin dicari
- Filter **Status** menjadi `Proses PO` dan `Closed`
- Hitung jumlah `Non Agreement` dan `Agreement` di **Kontrak/Non kontrak**

Karyawan dengan porsi PO Kontrak yang tinggi cenderung bekerja lebih efisien karena tidak perlu melakukan proses lelang atau negosiasi berulang.
""")

    st.caption("Jumlah item PO yang diterbitkan dengan dasar Outline Agreement (Kontrak) per karyawan.")

    if 'nama' in df_chart.columns and 'outline_agreement' in df_chart.columns:
        df_po = df_chart[df_chart['is_po'] == 1].copy()
        df_po['is_kontrak'] = (df_po['outline_agreement'].notna() & (df_po['outline_agreement'].astype(str).str.strip() != '')).astype(int)
        
        kontrak_df = (df_po.groupby('nama')
                    .agg(Total_PO=('is_po', 'sum'),
                        PO_Kontrak=('is_kontrak', 'sum'))
                    .reset_index())
        
        if not kontrak_df.empty:
            kontrak_df['PO_Non_Kontrak'] = kontrak_df['Total_PO'] - kontrak_df['PO_Kontrak']
            kontrak_df = kontrak_df.sort_values('Total_PO', ascending=True)

            fig_kontrak = go.Figure()
            fig_kontrak.add_bar(y=kontrak_df['nama'], x=kontrak_df['PO_Non_Kontrak'], name='PO Non-Kontrak', 
                                orientation='h', marker_color='#6c8ebf', 
                                text=kontrak_df['PO_Non_Kontrak'].apply(lambda x: str(x) if x > 0 else ''))
            fig_kontrak.add_bar(y=kontrak_df['nama'], x=kontrak_df['PO_Kontrak'], name='PO Kontrak', 
                                orientation='h', marker_color='#09ab3b', 
                                text=kontrak_df['PO_Kontrak'].apply(lambda x: str(x) if x > 0 else ''))

            fig_kontrak.update_traces(textposition='inside', textfont=dict(color='white'))
            fig_kontrak.update_layout(
                barmode='stack',
                height=max(250, len(kontrak_df) * 48),
                margin=dict(t=20, b=20, l=20, r=40), 
                legend=dict(orientation='h', yanchor='bottom', y=1.01),
                xaxis=dict(title='Jumlah Item PO', gridcolor='rgba(128,128,128,0.15)'), 
                yaxis=dict(title=''),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='gray'
            )
            st.plotly_chart(fig_kontrak, use_container_width=True)
        else:
            st.info("Tidak ada data untuk filter yang dipilih.")
    else:
        st.info("Tidak ada data untuk filter yang dipilih.")

    # == ROW 5: Efisiensi Nilai (OE vs PO) ===================================
    st.markdown("---")

    title_col, btn_col = st.columns([19, 1])
    with title_col:
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:24px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-wallet-fill" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                    <path d="M1.5 2A1.5 1.5 0 0 0 0 3.5v2h6a.5.5 0 0 1 .5.5c0 .253.08.644.306.958.207.288.557.542 1.194.542s.987-.254 1.194-.542C9.42 6.644 9.5 6.253 9.5 6a.5.5 0 0 1 .5-.5h6v-2A1.5 1.5 0 0 0 14.5 2z"/>
                    <path d="M16 6.5h-5.551a2.7 2.7 0 0 1-.443 1.042C9.613 8.088 8.963 8.5 8 8.5s-1.613-.412-2.006-.958A2.7 2.7 0 0 1 5.551 6.5H0v6A1.5 1.5 0 0 0 1.5 14h13a1.5 1.5 0 0 0 1.5-1.5z"/>
                </svg>
                Perbandingan Nilai OE vs PO (Non Agreement) per Karyawan
            </h1>
        """, unsafe_allow_html=True)
    with btn_col:
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Lihat Formula"):
            st.info("""\
    **Perbandingan Nilai OE vs PO (Non Agreement)**: Grouped bar chart yang membandingkan total nilai anggaran (OE) dengan realisasi aktual (PO) untuk setiap karyawan. Chart ini dikhususkan untuk melihat efisiensi item Non Agreement.

    Bar **Biru** (OE PR) = Total nilai estimasi sebelum PO diproses.

    Bar **Hijau** (Nilai PO) = Total nilai final setelah negosiasi dan PO diterbitkan.

    Jika bar Hijau lebih pendek dari Biru, artinya karyawan tersebut berhasil melakukan penghematan pengadaan.
    """)
        
    st.caption("Perbandingan total nilai anggaran (OE) dengan realisasi aktual (PO) untuk dokumen pengadaan Non Agreement.")

    if 'nama' in df_chart.columns:

        df_chart['oe_pr'] = pd.to_numeric(df_chart['oe_pr'], errors='coerce').fillna(0).astype(float)
        df_chart['nilai_item_po'] = pd.to_numeric(df_chart['nilai_item_po'], errors='coerce').fillna(0).astype(float)
        df_chart['is_po'] = pd.to_numeric(df_chart['is_po'], errors='coerce').fillna(0).astype(int)
        
        # Filter Khusus Non Agreement untuk efisiensi
        df_na = df_chart[(df_chart['is_po'] == 1) & 
                        (df_chart['outline_agreement'].isna() | (df_chart['outline_agreement'].astype(str).str.strip() == ''))]
        
        eff = (df_na.groupby('nama')
            .agg(oe=('oe_pr', 'sum'), po=('nilai_item_po', 'sum'))
            .reset_index())
        
        if not eff.empty:
            eff = eff.sort_values('oe', ascending=True)
            
            eff['oe_text'] = eff['oe'].apply(format_idr_short)
            eff['po_text'] = eff['po'].apply(format_idr_short)

            fig_eff = go.Figure()
            fig_eff.add_bar(
                y=eff['nama'], x=eff['oe'], name='OE PR', text=eff['oe_text'],
                orientation='h', marker_color='#6c8ebf', opacity=0.85,
                customdata=eff['oe_text'],
                hovertemplate='<b>%{y}</b><br>OE PR: Rp %{customdata}<extra></extra>'
            )
            fig_eff.add_bar(
                y=eff['nama'], x=eff['po'], name='Nilai PO', text=eff['po_text'],
                orientation='h', marker_color='#09ab3b', opacity=0.85,
                customdata=eff['po_text'],
                hovertemplate='<b>%{y}</b><br>Nilai PO: Rp %{customdata}<extra></extra>'
            )
            
            fig_eff.update_traces(textposition='outside')
            fig_eff.update_layout(
                barmode='group',
                height=max(250, len(eff) * 48),
                margin=dict(t=20, b=20, l=20, r=60), 
                legend=dict(orientation='h', yanchor='bottom', y=1.01),
                xaxis=dict(title='Total Nilai (IDR)', gridcolor='rgba(128,128,128,0.15)'), 
                yaxis=dict(title=''),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='gray',
                separators=",."
            )
            st.plotly_chart(fig_eff, use_container_width=True)
        else:
            st.info("Tidak ada data untuk filter yang dipilih.")
    else:
        st.info("Tidak ada data untuk filter yang dipilih.")

    st.markdown("---")

    # =====================================================================
    # INTEGRASI AI: PANGGIL MELATI DENGAN KONTEKS GLOBAL
    # =====================================================================

    global_context = kwargs.get("global_context", "")

    suplemen_lines = [
        "# SUPLEMEN - DETAIL CHART HALAMAN INI (SIPS Dashboard)",
    ]

    if 'status_counts' in locals() and not status_counts.empty:
        suplemen_lines.append("## DISTRIBUSI STATUS DOKUMEN")
        suplemen_lines.append(status_counts.to_csv(index=False))
        suplemen_lines.append("")

    if 'vol' in locals() and not vol.empty:
        suplemen_lines.append("## BEBAN KERJA (VOLUME PR & PO) PER KARYAWAN")
        df_vol_simple = vol.sort_values('Total_PR', ascending=False)
        suplemen_lines.append(df_vol_simple.to_csv(index=False))
        suplemen_lines.append("")

    if 'perf' in locals() and not perf.empty:
        suplemen_lines.append("## PERFORMA KETEPATAN WAKTU (SLA) PER KARYAWAN")
        df_perf_simple = perf[['nama', 'total_po', 'sla_ok', 'pct_ontime']].sort_values('pct_ontime', ascending=False)
        suplemen_lines.append(df_perf_simple.to_csv(index=False))
        suplemen_lines.append("")

    if 'eff' in locals() and not eff.empty:
        suplemen_lines.append("## EFISIENSI (OE VS PO KHUSUS NON AGREEMENT) PER KARYAWAN")
        eff_ai = eff.copy()
        eff_ai['efisiensi_rp']  = eff_ai['oe'] - eff_ai['po']
        eff_ai['efisiensi_pct'] = ((eff_ai['efisiensi_rp'] / eff_ai['oe']) * 100).round(1).fillna(0)
        df_eff_simple = eff_ai[['nama', 'oe', 'po', 'efisiensi_rp', 'efisiensi_pct']].sort_values('efisiensi_rp', ascending=False)
        suplemen_lines.append(df_eff_simple.to_csv(index=False))
        suplemen_lines.append("")

    # Download button untuk semua data chart
    if not df_chart.empty:
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df_chart.to_excel(writer, index=False, sheet_name='SIPS_Dashboard_Data')
        excel_buffer.seek(0)
        st.download_button(
            label="Download Semua Data Chart (XLSX)",
            data=excel_buffer,
            file_name=f"sips_dashboard_data_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    konteks_final = global_context + "\n---\n" + "\n".join(suplemen_lines)

    with st.expander("Tanya ke Melati (Monitoring, Evaluasi, Laporan Terintegrasi)"):
        render_chat_analyst(
            konteks_data_teks=konteks_final,
            nama_halaman="Dashboard SIPS",
            load_data_fn=load_data,
        )