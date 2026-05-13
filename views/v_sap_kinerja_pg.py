"""
v_sap_kinerja_pg.py - Halaman Kinerja Purchasing Group
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from utils import format_idr, format_idr_short, format_number, format_currency, render_chat_analyst, idr_axis

KINERJA_CSS = """
<style>
/* ── Card KPI & Chart Wrapper ─────────────────────────────────────────── */
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
    align-items: flex-start;
    gap: 14px;
    min-height: 145px !important;
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
    line-height: 1.3;
    font-weight: 500;
    color: var(--text-color) !important;
    opacity: 0.75;
}

.dash-value {
    font-size: 2rem !important;
    font-weight: 600 !important;
    margin: 0 0 4px 0 !important;
    line-height: 1.1 !important;
    color: var(--text-color) !important;
    white-space: normal !important;
    word-wrap: break-word !important;
    display: block !important;
}

.dash-delta { font-size: 12px; margin: 0; color: var(--text-color) !important; opacity: 0.6; }
.dash-delta-green  { font-size: 12px; color: #09ab3b !important; margin: 0; font-weight: 600; }
.dash-delta-red    { font-size: 12px; color: #e03c3c !important; margin: 0; font-weight: 600; }
.dash-delta-orange { font-size: 12px; color: #f0a500 !important; margin: 0; font-weight: 600; }

/* ── Tombol popover di dalam kartu KPI ───────────────────────────────── */
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

ICONS = {
    "kpi_item_pr":   "M5 10.5a.5.5 0 0 1 .5-.5h2a.5.5 0 0 1 0 1h-2a.5.5 0 0 1-.5-.5m0-2a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5m0-2a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5 M3 0h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2m0 1a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1z",
    "kpi_item_po":   "M8 1a2.5 2.5 0 0 1 2.5 2.5V4h-5v-.5A2.5 2.5 0 0 1 8 1m3.5 3v-.5a3.5 3.5 0 1 0-7 0V4H1v10a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V4zM2 5h12v9a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1z",
    "kpi_oe":        "M4 10.781c.148 1.667 1.513 2.85 3.591 3.003V15h1.043v-1.216c2.27-.179 3.678-1.438 3.678-3.3 0-1.59-.947-2.51-2.956-3.028l-.722-.187V3.467c1.122.11 1.879.714 2.07 1.616h1.47c-.166-1.6-1.54-2.748-3.54-2.875V1H7.591v1.233c-1.939.23-3.27 1.472-3.27 3.156 0 1.454.966 2.483 2.661 2.917l.61.162v4.031c-1.149-.17-1.94-.8-2.131-1.718zm3.391-3.836c-1.043-.263-1.6-.825-1.6-1.616 0-.944.704-1.641 1.8-1.828v3.495l-.2-.05zm1.591 1.872c1.287.323 1.852.859 1.852 1.769 0 1.097-.826 1.828-2.2 1.939V8.73z",
    "kpi_realisasi": "M1 3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1zm7 8a2 2 0 1 0 0-4 2 2 0 0 0 0 4 M0 5a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H1a1 1 0 0 1-1-1zm3 0a2 2 0 0 1-2 2v4a2 2 0 0 1 2 2h10a2 2 0 0 1 2-2V7a2 2 0 0 1-2-2z",
    "kpi_efisiensi": "M11.534 7h3.932a.25.25 0 0 1 .192.41l-1.966 2.36a.25.25 0 0 1-.384 0l-1.966-2.36a.25.25 0 0 1 .192-.41m-11 2h3.932a.25.25 0 0 0 .192-.41L2.692 6.23a.25.25 0 0 0-.384 0L.342 8.59A.25.25 0 0 0 .534 9 M8 3c-1.552 0-2.94.707-3.857 1.818a.5.5 0 1 1-.771-.636A6.002 6.002 0 0 1 13.917 7H12.9A5 5 0 0 0 8 3M3.1 9a5.002 5.002 0 0 0 8.757 2.182.5.5 0 1 1 .771.636A6.002 6.002 0 0 1 2.083 9z",
    "kpi_lead_time": "M8 3.5a.5.5 0 0 0-1 0V9a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0 0 .496-.868L8 8.71V3.5z M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0z",
    "kpi_ontime":    "M10.97 4.97a.75.75 0 0 1 1.07 1.05l-3.99 4.99a.75.75 0 0 1-1.08.02L4.324 8.384a.75.75 0 1 1 1.06-1.06l2.094 2.093 3.473-4.425z M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0z",
    "kpi_late":      "M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5m.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2",
    "kpi_median":    "M0 0h1v15h15v1H0zm14.817 3.113a.5.5 0 0 1 .07.704l-4.5 5.5a.5.5 0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5 0 0 1 .758-.06l2.609 2.61 4.15-5.073a.5.5 0 0 1 .704-.07",
    "kpi_rentang":   "M3.5 0a.5.5 0 0 1 .5.5V1h8V.5a.5.5 0 0 1 1 0V1h1a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2h1V.5a.5.5 0 0 1 .5-.5M1 4v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V4z",
}


def _svg(path_d: str, size: int = 40) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'fill="currentColor" viewBox="0 0 16 16"><path d="{path_d}"/></svg>'
    )


def _card(icon_d: str, label: str, value: str,
          delta: str = "", delta_type: str = "neutral") -> str:
    delta_cls = {
        "green":  "dash-delta-green",
        "red":    "dash-delta-red",
        "orange": "dash-delta-orange",
    }.get(delta_type, "dash-delta")
    delta_html = f'<p class="{delta_cls}">{delta}</p>' if delta else ""
    return f"""<div class="dash-card">
    <div class="dash-icon">{_svg(icon_d, 36)}</div>
    <div class="dash-body">
        <p class="dash-label">{label}</p>
        <p class="dash-value">{value}</p>{delta_html}
    </div>
</div>"""


def render(filter_conditions, bagian_pr_cond, bagian_po_cond, load_data, **kwargs):

    info_filter = kwargs.get('info_filter', 'Tidak ada filter spesifik')
    dept_cond   = kwargs.get('dept_cond', '1=1')
    pg_cond     = kwargs.get('pg_cond',   '1=1')

    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:50px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" fill="currentColor" class="bi bi-briefcase-fill" viewBox="0 0 16 16" style="margin-bottom: 8px; margin-right: 12px;">
                <path d="M6.5 1A1.5 1.5 0 0 0 5 2.5V3H1.5A1.5 1.5 0 0 0 0 4.5v1.384l7.614 2.03a1.5 1.5 0 0 0 .772 0L16 5.884V4.5A1.5 1.5 0 0 0 14.5 3H11v-.5A1.5 1.5 0 0 0 9.5 1h-3zm0 1h3a.5.5 0 0 1 .5.5V3H6v-.5a.5.5 0 0 1 .5-.5z"/>
                <path d="M0 12.5A1.5 1.5 0 0 0 1.5 14h13a1.5 1.5 0 0 0 1.5-1.5V6.85L8.129 8.947a.5.5 0 0 1-.258 0L0 6.85v5.65z"/>
            </svg>
            Kinerja per Purchasing Group
        </h1>
    """, unsafe_allow_html=True)
    st.markdown("Analisis komprehensif jumlah item, nilai pengadaan (OE vs Realisasi), efisiensi, dan kecepatan proses per Purchasing Group, termasuk breakdown per metode tender.")
    st.markdown(KINERJA_CSS, unsafe_allow_html=True)
    st.markdown("---")

    date_from     = kwargs.get('date_from')
    date_to       = kwargs.get('date_to')
    bagian_po_poh = bagian_po_cond.replace('bagian_po', 'poh.bagian_po')

    # ── Query KPI PR ──────────────────────────────────────────────────────────
    pg_kpi_query = f"""
    SELECT
        COUNT(DISTINCT CASE WHEN no_pr != 'No PR' AND {bagian_pr_cond}
            THEN no_pr || '-' || line_item_pr::text END)                     AS total_item_pr,
        COUNT(DISTINCT CASE WHEN nomor_po IS NOT NULL AND no_pr != 'No PR' AND {bagian_pr_cond}
            THEN no_pr || '-' || line_item_pr::text END)                     AS pr_with_po
    FROM vw_pr_po_complete
    WHERE {filter_conditions}
      AND first_full_release IS NOT NULL
    """

    # ── Query KPI OE dari po_items ────────────────────────────────────────────
    pg_oe_kpi_query = f"""
    SELECT
        COALESCE(SUM(poi.estimasi_pr * poi.quantity_pr), 0) AS total_oe
    FROM po_items poi
    JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
    WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
      AND poi.estimasi_pr IS NOT NULL AND poi.estimasi_pr > 0
      AND poi.quantity_pr IS NOT NULL AND poi.quantity_pr > 0
      AND {bagian_po_poh}
      AND {dept_cond}
      AND {pg_cond}
    """

    # ── Query KPI PO ──────────────────────────────────────────────────────────
    pg_po_kpi_query = f"""
    SELECT
        COUNT(DISTINCT poi.nomor_po || '-' || poi.item_po::text)             AS total_item_po,
        COALESCE(SUM(poi.total_amount_local_curr), 0)                        AS total_realisasi,
        ROUND(AVG(
            CASE WHEN poi.first_full_release IS NOT NULL AND poh.date_ordered IS NOT NULL
            THEN (poh.date_ordered::date - poi.first_full_release::date)
            END
        )::numeric, 1)                                                       AS avg_lead_time_overall
    FROM po_items poi
    JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
    WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
      AND {bagian_po_poh}
      AND {dept_cond}
      AND {pg_cond}
    """

    with st.spinner("Memuat KPI..."):
        pg_kpi    = load_data(pg_kpi_query)
        pg_po_kpi = load_data(pg_po_kpi_query)
        pg_oe_kpi = load_data(pg_oe_kpi_query)

    # ── Ekstrak nilai KPI ─────────────────────────────────────────────────────
    t_item_pr    = int(pg_kpi['total_item_pr'][0] or 0)   if not pg_kpi.empty    else 0
    pr_with_po   = int(pg_kpi['pr_with_po'][0] or 0)      if not pg_kpi.empty    else 0
    t_item_po    = int(pg_po_kpi['total_item_po'][0] or 0) if not pg_po_kpi.empty else 0
    t_oe         = float(pg_oe_kpi['total_oe'][0] or 0)   if not pg_oe_kpi.empty else 0
    t_real       = float(pg_po_kpi['total_realisasi'][0] or 0) if not pg_po_kpi.empty else 0
    t_efis       = t_oe - t_real
    t_efis_pct   = (t_efis / t_oe * 100) if t_oe > 0 else 0
    avg_lt_raw   = pg_po_kpi['avg_lead_time_overall'][0] if not pg_po_kpi.empty else None
    avg_lt       = float(avg_lt_raw) if pd.notna(avg_lt_raw) else None
    konversi_pct = (pr_with_po / t_item_pr * 100) if t_item_pr > 0 else 0

    # ── Definisi kartu KPI ringkasan ──────────────────────────────────────────
    KPI_RINGKASAN = [
        {
            "key":   "kpi_item_pr",
            "label": "Total Item PR",
            "value": format_number(t_item_pr),
            "delta": f"{format_number(konversi_pct, decimals=1)}% terkonversi ke PO",
            "delta_type": "neutral",
            "formula": """\
**Total Item PR**: Jumlah item PR unik dalam periode filter yang sudah memiliki `1St Full Release`.

**Formula Excel:** (PR SAP)
- Filter **1St Full Release** selain `blanks`
- Filter **Material No** selain `1000076`
- Filter **PR Deletion Flag** selain `X`
- Hitung baris unik `No PR + Line Item PR`
"""
        },
        {
            "key":   "kpi_item_po",
            "label": "Total Item PO",
            "value": format_number(t_item_po),
            "delta": f"{format_number(pr_with_po)} PR dgn PO",
            "delta_type": "neutral",
            "formula": """\
**Total Item PO**: Jumlah item PO unik dalam periode filter berdasarkan `Date Ordered`.

**Formula Excel:** (PO SAP)
- Filter **Material No** selain `1000076`
- Filter **PO Deletion Flag** selain `L`
- Hitung baris unik `Nomor PO + Item PO`
"""
        },
        {
            "key":   "kpi_oe",
            "label": "Total OE",
            "value": format_idr(t_oe),
            "delta": "Anggaran Estimasi",
            "delta_type": "neutral",
            "formula": f"""\
**Total OE**: Total nilai Owner's Estimate dari semua PO dalam periode filter.

**Total OE saat ini:** Rp {t_oe:,.0f}

**Formula Excel:** (PO SAP)
- Filter **Material No** selain `1000076`
- Filter **PO Deletion Flag** selain `L`
- Buat kolom **OE**: `= Quantity PR × Estimasi PR`
- Jumlahkan kolom **OE**
"""
        },
        {
            "key":   "kpi_realisasi",
            "label": "Total Realisasi PO",
            "value": format_idr(t_real),
            "delta": "Nilai Aktual PO",
            "delta_type": "neutral",
            "formula": f"""\
**Total Realisasi PO**: Total nilai aktual PO yang diterbitkan dalam periode filter.

**Total Realisasi saat ini:** Rp {t_real:,.0f}

**Formula Excel:** (PO SAP)
- Filter **Material No** selain `1000076`
- Filter **PO Deletion Flag** selain `L`
- Jumlahkan kolom **Total Amount in Local Curr**
"""
        },
        {
            "key":   "kpi_efisiensi",
            "label": "Efisiensi",
            "value": format_idr(t_efis),
            "delta": f"{format_number(t_efis_pct, decimals=2)}% {'efisien' if t_efis >= 0 else 'over budget'}",
            "delta_type": "green" if t_efis >= 0 else "red",
            "formula": f"""\
**Efisiensi**: Selisih antara total OE dan total realisasi PO.

**Efisiensi saat ini:** Rp {t_efis:,.0f} ({t_efis_pct:.1f}%)

**Formula:**
```
= Total OE - Total Realisasi PO
```

| Kondisi | Artinya |
|---|---|
| Positif | Realisasi < OE → penghematan ✅ |
| Negatif | Realisasi > OE → over budget ❌ |
"""
        },
        {
            "key":   "kpi_lead_time",
            "label": "Avg Lead Time",
            "value": f"{format_number(avg_lt, decimals=1)} Hari" if avg_lt is not None else "N/A",
            "delta": "On Target" if (avg_lt and avg_lt <= 55) else "Over Target",
            "delta_type": "green" if (avg_lt and avg_lt <= 55) else "red",
            "formula": """\
**Avg Lead Time**: Rata-rata hari dari `1St Full Release` PR hingga PO diterbitkan (`Date Ordered`).

**Formula Excel:** (PO SAP)
- Filter **Material No** selain `1000076`
- Filter **PO Deletion Flag** selain `L`
- Buat kolom: `= Date Ordered - 1St Full Release`
- Hitung rata-rata kolom tersebut

**Target SLA = 55 hari.**
"""
        },
    ]

    # ── Render KPI ringkasan (3 per baris) ────────────────────────────────────
    st.markdown("""
        <h1 style='display: flex; align-items: center;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor" viewBox="0 0 16 16" style="margin-bottom: 8px; margin-right: 8px;">
                <path fill-rule="evenodd" d="M0 0h1v15h15v1H0zm14.817 3.113a.5.5 0 0 1 .07.704l-4.5 5.5a.5.5 0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5 0 0 1 .758-.06l2.609 2.61 4.15-5.073a.5.5 0 0 1 .704-.07"/>
            </svg>
            KPI Ringkasan
        </h1>
    """, unsafe_allow_html=True)

    for row_start in range(0, len(KPI_RINGKASAN), 3):
        cols = st.columns(3, gap="medium")
        for i, kpi in enumerate(KPI_RINGKASAN[row_start:row_start + 3]):
            with cols[i]:
                st.markdown(
                    _card(ICONS[kpi["key"]], kpi["label"], kpi["value"],
                          kpi["delta"], kpi["delta_type"]),
                    unsafe_allow_html=True
                )
                with st.popover(":material/visibility:", help="Lihat Formula"):
                    st.info(kpi["formula"])
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB: OVERVIEW | BREAKDOWN
    # ══════════════════════════════════════════════════════════════════════════
    tab1, tab2 = st.tabs([
        ":material/overview: Overview per Purchasing Group",
        ":material/sell: Breakdown Metode Tender & Kecepatan",
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1: OVERVIEW PER PURCHASING GROUP
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        bagian_pr_cond_pri = bagian_pr_cond.replace('bagian_pr', 'pri.bagian_pr')

        pg_pr_query = f"""
        SELECT
            COALESCE(poh.purchasing_group, 'Unassigned')                     AS purchasing_group,
            COUNT(DISTINCT pri.no_pr || '-' || pri.line_item_pr::text)
                FILTER (WHERE pri.material_no IS NOT NULL
                          AND (pri.batal IS NULL OR pri.batal = FALSE))       AS jml_item_pr,
            COUNT(DISTINCT pri.no_pr || '-' || pri.line_item_pr::text)
                FILTER (WHERE pri.material_no IS NOT NULL
                          AND (pri.batal IS NULL OR pri.batal = FALSE))       AS pr_with_po
        FROM pr_items pri
        JOIN po_items poi
            ON pri.no_pr = poi.no_pr AND pri.line_item_pr = poi.line_item_pr
        JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
        WHERE pri.first_full_release >= '{date_from}'
          AND pri.first_full_release <= '{date_to}'
          AND pri.first_full_release IS NOT NULL
          AND ({bagian_pr_cond_pri})
        GROUP BY COALESCE(poh.purchasing_group, 'Unassigned')
        """

        pg_query = f"""
        SELECT
            COALESCE(poh.purchasing_group, 'Unassigned')                     AS purchasing_group,
            COUNT(DISTINCT poi.nomor_po || '-' || poi.item_po::text)         AS jml_item_po,
            COALESCE(SUM(poi.estimasi_pr * poi.quantity_pr)
                FILTER (WHERE poi.estimasi_pr > 0 AND poi.quantity_pr > 0), 0) AS nilai_oe,
            COALESCE(SUM(poi.total_amount_local_curr), 0)                    AS nilai_po,
            COALESCE(SUM(poi.estimasi_pr * poi.quantity_pr)
                FILTER (WHERE poi.estimasi_pr > 0 AND poi.quantity_pr > 0), 0)
                - COALESCE(SUM(poi.total_amount_local_curr), 0)              AS efisiensi,
            CASE
                WHEN COALESCE(SUM(poi.estimasi_pr * poi.quantity_pr)
                    FILTER (WHERE poi.estimasi_pr > 0 AND poi.quantity_pr > 0), 0) > 0
                THEN ROUND(
                    (COALESCE(SUM(poi.estimasi_pr * poi.quantity_pr)
                        FILTER (WHERE poi.estimasi_pr > 0 AND poi.quantity_pr > 0), 0)
                     - COALESCE(SUM(poi.total_amount_local_curr), 0))
                    / COALESCE(SUM(poi.estimasi_pr * poi.quantity_pr)
                        FILTER (WHERE poi.estimasi_pr > 0 AND poi.quantity_pr > 0), 0) * 100, 1)
                ELSE NULL
            END                                                              AS efisiensi_pct,
            ROUND(AVG(
                CASE WHEN poi.first_full_release IS NOT NULL AND poh.date_ordered IS NOT NULL
                THEN (poh.date_ordered::date - poi.first_full_release::date) END
            )::numeric, 1)                                                   AS avg_lead_time,
            MIN(CASE WHEN poi.first_full_release IS NOT NULL
                THEN (poh.date_ordered::date - poi.first_full_release::date) END) AS min_lead_time,
            MAX(CASE WHEN poi.first_full_release IS NOT NULL
                THEN (poh.date_ordered::date - poi.first_full_release::date) END) AS max_lead_time
        FROM po_items poi
        JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
        WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
          AND ({bagian_po_cond.replace('bagian_po', 'poh.bagian_po')})
          AND {dept_cond}
          AND {pg_cond}
        GROUP BY COALESCE(poh.purchasing_group, 'Unassigned')
        ORDER BY nilai_oe DESC
        """

        with st.spinner("Memuat data per Purchasing Group..."):
            pg_po_data = load_data(pg_query)
            pg_pr_data = load_data(pg_pr_query)

        if not pg_po_data.empty:
            if not pg_pr_data.empty:
                pg_data = pg_po_data.merge(
                    pg_pr_data[['purchasing_group', 'jml_item_pr', 'pr_with_po']],
                    on='purchasing_group', how='left'
                )
            else:
                pg_data = pg_po_data.copy()
                pg_data['jml_item_pr'] = 0
                pg_data['pr_with_po']  = 0
            pg_data['jml_item_pr'] = pg_data['jml_item_pr'].fillna(0).astype(int)
            pg_data['pr_with_po']  = pg_data['pr_with_po'].fillna(0).astype(int)
        else:
            pg_data = pd.DataFrame()

        if not pg_data.empty:
            # == Tabel Ringkasan ================================================
            title_col, btn_col = st.columns([9, 1])
            with title_col:
                st.markdown("""
                    <h1 style='display: flex; align-items: center; font-size:22px;'>
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                            <path d="M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2zm15 2h-4v3h4zm0 4h-4v3h4zm0 4h-4v3h3a1 1 0 0 0 1-1zm-5 3v-3H6v3zm-5 0v-3H1v2a1 1 0 0 0 1 1zm-4-4h4V8H1zm0-4h4V4H1zm5-3v3h4V4zm4 4H6v3h4z"/>
                        </svg>
                        Tabel Ringkasan per Purchasing Group
                    </h1>
                """, unsafe_allow_html=True)
            with btn_col:
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                with st.popover(":material/visibility:", help="Lihat Formula"):
                    st.info("""\
**Tabel Ringkasan per Purchasing Group**: Ringkasan metrik kinerja per Purchasing Group.

**Kalkulasi:**
| Kolom | Formula |
|---|---|
| Item PO | `COUNT(DISTINCT nomor_po + item_po)` dari `po_items` |
| Total OE | `SUM(estimasi_pr × quantity_pr)` dari `po_items` |
| Realisasi PO | `SUM(total_amount_local_curr)` dari `po_items` |
| Efisiensi | `OE - Realisasi` |
| % Efisiensi | `(OE - Realisasi) / OE × 100` |
| Lead Time Avg | `AVG(date_ordered - first_full_release)` |
""")

            df_table = pg_data.copy()
            df_table['konversi_pct'] = (
                df_table['pr_with_po'] / df_table['jml_item_pr'].replace(0, float('nan')) * 100
            ).round(1).fillna(0)
            df_table['efisiensi_pct'] = df_table['efisiensi_pct'].fillna(0)

            df_display = df_table.copy()
            df_display.index = df_display.index + 1
            df_display['jml_item_pr']   = df_display['jml_item_pr'].apply(format_number)
            df_display['jml_item_po']   = df_display['jml_item_po'].apply(format_number)
            df_display['nilai_oe']      = df_display['nilai_oe'].apply(format_currency)
            df_display['nilai_po']      = df_display['nilai_po'].apply(format_currency)
            df_display['efisiensi']     = df_display['efisiensi'].apply(format_currency)
            df_display['efisiensi_pct'] = df_display['efisiensi_pct'].apply(lambda x: f"{format_number(x, decimals=1)}%")
            df_display['avg_lead_time'] = df_display['avg_lead_time'].apply(
                lambda x: f"{format_number(x, decimals=1)} Hari" if pd.notna(x) else "N/A")
            df_display['min_lead_time'] = df_display['min_lead_time'].apply(
                lambda x: f"{format_number(x)} Hari" if pd.notna(x) else "N/A")
            df_display['max_lead_time'] = df_display['max_lead_time'].apply(
                lambda x: f"{format_number(x)} Hari" if pd.notna(x) else "N/A")
            df_display['konversi_pct']  = df_display['konversi_pct'].apply(lambda x: f"{format_number(x, decimals=1)}%")

            col_order = [
                'purchasing_group', 'jml_item_po', 'jml_item_pr', 'pr_with_po', 'konversi_pct',
                'nilai_oe', 'nilai_po', 'efisiensi', 'efisiensi_pct',
                'avg_lead_time', 'min_lead_time', 'max_lead_time',
            ]
            df_display = df_display[[c for c in col_order if c in df_display.columns]]
            st.dataframe(
                df_display.rename(columns={
                    'purchasing_group': 'Purchasing Group',
                    'jml_item_po'     : 'Item PO',
                    'jml_item_pr'     : 'Item PR',
                    'pr_with_po'      : 'PR dgn PO',
                    'konversi_pct'    : '% PR→PO',
                    'nilai_oe'        : 'Total OE',
                    'nilai_po'        : 'Realisasi PO',
                    'efisiensi'       : 'Efisiensi',
                    'efisiensi_pct'   : '% Efisiensi',
                    'avg_lead_time'   : 'Lead Time Avg',
                    'min_lead_time'   : 'Lead Time Min',
                    'max_lead_time'   : 'Lead Time Max',
                }),
                use_container_width=True, height=320
            )

            st.markdown("<br>", unsafe_allow_html=True)

            # == Row 1: Nilai OE vs PO + % Efisiensi ===========================
            col1, col2 = st.columns(2)
            with col1:
                title_col, btn_col = st.columns([9, 1])
                with title_col:
                    st.markdown("""
                        <h1 style='display: flex; align-items: center; font-size:22px;'>
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                                <path d="M1 3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1zm7 8a2 2 0 1 0 0-4 2 2 0 0 0 0 4"/>
                                <path d="M0 5a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H1a1 1 0 0 1-1-1zm3 0a2 2 0 0 1-2 2v4a2 2 0 0 1 2 2h10a2 2 0 0 1 2-2V7a2 2 0 0 1-2-2z"/>
                            </svg>
                            Perbandingan Nilai OE vs Realisasi PO
                        </h1>
                    """, unsafe_allow_html=True)
                with btn_col:
                    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                    with st.popover(":material/visibility:", help="Lihat Formula"):
                        st.info("""\
**Perbandingan Nilai OE vs Realisasi PO**: Grouped bar chart OE vs realisasi per Purchasing Group.

**Formula Excel:** (PO SAP)
- Filter sesuai Purchasing Group
- Kolom **OE**: `= Estimasi PR × Quantity PR`
- Jumlahkan kolom **OE** dan **Total Amount in Local Curr**

Bar Realisasi **lebih pendek** dari OE = ada penghematan ✅. Lebih panjang = over budget ❌.
""")
                st.caption("Perbandingan estimasi anggaran (OE) vs realisasi PO per Purchasing Group.")

                df_melted = pg_data.melt(
                    id_vars=['purchasing_group'],
                    value_vars=['nilai_oe', 'nilai_po'],
                    var_name='Jenis', value_name='Nilai'
                )
                df_melted['Jenis'] = df_melted['Jenis'].replace(
                    {'nilai_oe': 'OE (Estimasi)', 'nilai_po': 'Realisasi PO'})
                df_melted['label'] = df_melted['Nilai'].apply(format_idr_short)
                fig_val = px.bar(
                    df_melted, x='purchasing_group', y='Nilai',
                    color='Jenis', barmode='group', text='label',
                    color_discrete_map={'OE (Estimasi)': '#ff7f0e', 'Realisasi PO': '#1f77b4'},
                    labels={'purchasing_group': 'Purchasing Group', 'Nilai': 'Total Nilai (IDR)'}
                )
                fig_val.update_traces(textposition='outside', textfont_size=10)
                fig_val.update_layout(
                    height=400,
                    margin=dict(t=40, b=20, l=20, r=20),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    separators=",."
                )
                st.plotly_chart(fig_val, use_container_width=True)

            with col2:
                title_col, btn_col = st.columns([9, 1])
                with title_col:
                    st.markdown("""
                        <h1 style='display: flex; align-items: center; font-size:22px;'>
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                                <path d="M6.5 1A1.5 1.5 0 0 0 5 2.5V3H1.5A1.5 1.5 0 0 0 0 4.5v1.384l7.614 2.03a1.5 1.5 0 0 0 .772 0L16 5.884V4.5A1.5 1.5 0 0 0 14.5 3H11v-.5A1.5 1.5 0 0 0 9.5 1h-3zm0 1h3a.5.5 0 0 1 .5.5V3H6v-.5a.5.5 0 0 1 .5-.5z"/>
                                <path d="M0 12.5A1.5 1.5 0 0 0 1.5 14h13a1.5 1.5 0 0 0 1.5-1.5V6.85L8.129 8.947a.5.5 0 0 1-.258 0L0 6.85v5.65z"/>
                            </svg>
                            % Efisiensi per Purchasing Group
                        </h1>
                    """, unsafe_allow_html=True)
                with btn_col:
                    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                    with st.popover(":material/visibility:", help="Lihat Formula"):
                        st.info("""\
**% Efisiensi per Purchasing Group**: Bar chart horizontal persentase penghematan tiap Purchasing Group.

**Formula Excel:** (PO SAP)
- Kolom OE: `= Estimasi PR × Quantity PR`
- Kolom Efisiensi: `= OE - Total Amount in Local Curr`
- % Efisiensi: `= Total Efisiensi / Total OE`

🟢 Positif = hemat. 🔴 Negatif = over budget.
""")
                st.caption("Persentase penghematan yang dicapai tiap Purchasing Group.")

                pg_efis = pg_data[pg_data['efisiensi_pct'].notna()].copy()
                pg_efis['label'] = pg_efis['efisiensi_pct'].apply(lambda x: f"{format_number(x, decimals=1)}%")
                pg_efis = pg_efis.sort_values('efisiensi_pct', ascending=True)
                fig_efis = px.bar(
                    pg_efis, x='efisiensi_pct', y='purchasing_group',
                    orientation='h', text='label',
                    color='efisiensi_pct',
                    color_continuous_scale=['#d62728', '#ffdd57', '#2ca02c'],
                    labels={'efisiensi_pct': '% Efisiensi', 'purchasing_group': 'Purchasing Group'}
                )
                fig_efis.add_vline(x=0, line_dash="dash", line_color="gray")
                fig_efis.update_traces(textposition='outside')
                fig_efis.update_layout(
                    height=400,
                    margin=dict(t=20, b=20, l=20, r=20),
                    coloraxis_showscale=False,
                    xaxis_title="% Efisiensi (positif = hemat, negatif = over budget)"
                )
                st.plotly_chart(fig_efis, use_container_width=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # == Row 2: Lead Time + % Konversi PR→PO ==========================
            col1, col2 = st.columns(2)
            with col1:
                title_col, btn_col = st.columns([9, 1])
                with title_col:
                    st.markdown("""
                        <h1 style='display: flex; align-items: center; font-size:22px;'>
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                                <path d="M6 .5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1H9v1.07a7.001 7.001 0 0 1 3.274 12.474l.601.602a.5.5 0 0 1-.707.708l-.746-.746A6.97 6.97 0 0 1 8 16a6.97 6.97 0 0 1-3.422-.892l-.746.746a.5.5 0 0 1-.707-.708l.602-.602A7.001 7.001 0 0 1 7 2.07V1h-.5A.5.5 0 0 1 6 .5m2.5 5a.5.5 0 0 0-1 0v3.362l-1.429 2.38a.5.5 0 1 0 .858.515l1.5-2.5A.5.5 0 0 0 8.5 9zM.86 5.387A2.5 2.5 0 1 1 4.387 1.86 8.04 8.04 0 0 0 .86 5.387M11.613 1.86a2.5 2.5 0 1 1 3.527 3.527 8.04 8.04 0 0 0-3.527-3.527"/>
                            </svg>
                            Rata-rata Lead Time per Purchasing Group
                        </h1>
                    """, unsafe_allow_html=True)
                with btn_col:
                    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                    with st.popover(":material/visibility:", help="Lihat Formula"):
                        st.info("""\
**Rata-rata Lead Time per Purchasing Group**: Bar chart horizontal rata-rata waktu proses PR→PO per Purchasing Group.

**Formula Excel:** (PO SAP)
- Lead Time `= Date Ordered - 1St Full Release`
- Rata-rata kolom tersebut per Purchasing Group

**Target:** Garis merah = **55 hari**.
""")
                st.caption("Rata-rata waktu proses PR→PO per Purchasing Group.")

                pg_lt = pg_data[pg_data['avg_lead_time'].notna()].copy()
                pg_lt['label'] = pg_lt['avg_lead_time'].apply(lambda x: f"{x} Hr")
                pg_lt = pg_lt.sort_values('avg_lead_time', ascending=True)
                fig_lt = px.bar(
                    pg_lt, x='avg_lead_time', y='purchasing_group',
                    orientation='h', text='label',
                    color='avg_lead_time',
                    color_continuous_scale=['#2ca02c', '#ffdd57', '#d62728'],
                    labels={'avg_lead_time': 'Hari', 'purchasing_group': 'Purchasing Group'}
                )
                fig_lt.add_vline(x=55, line_dash="dash", line_color="red",
                                 annotation_text="Target 55 Hari",
                                 annotation_position="top right")
                fig_lt.update_traces(textposition='outside')
                fig_lt.update_layout(
                    height=400,
                    margin=dict(t=20, b=20, l=20, r=20),
                    coloraxis_showscale=False
                )
                st.plotly_chart(fig_lt, use_container_width=True)

            with col2:
                title_col, btn_col = st.columns([9, 1])
                with title_col:
                    st.markdown("""
                        <h1 style='display: flex; align-items: center; font-size:22px;'>
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                                <path fill-rule="evenodd" d="M8 3a5 5 0 1 0 4.546 2.914.5.5 0 0 1 .908-.417A6 6 0 1 1 8 2z"/>
                                <path d="M8 4.466V.534a.25.25 0 0 1 .41-.192l2.36 1.966c.12.1.12.284 0 .384L8.41 4.658A.25.25 0 0 1 8 4.466"/>
                            </svg>
                            % Konversi PR → PO per Purchasing Group
                        </h1>
                    """, unsafe_allow_html=True)
                with btn_col:
                    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                    with st.popover(":material/visibility:", help="Lihat Formula"):
                        st.info("""\
**% Konversi PR → PO per Purchasing Group**: Bar chart horizontal persentase item PR yang berhasil dikonversi menjadi PO.

**Formula Excel:** (PR SAP + PO SAP)
- Item PR = `COUNT(DISTINCT No PR + Line Item PR)` dari PR SAP
- PR dgn PO = item PR yang juga ada di PO SAP
- `% Konversi = PR dgn PO / Item PR × 100`

% **tinggi** = hampir semua PR sudah diproses ✅. % **rendah** = banyak PR pending ⚠️.
""")
                st.caption("Persentase PR yang berhasil dikonversi menjadi PO.")

                pg_data['konversi_pct'] = (
                    pg_data['pr_with_po'] /
                    pg_data['jml_item_pr'].replace(0, float('nan')) * 100
                ).round(1).fillna(0)
                pg_konv = pg_data.sort_values('konversi_pct', ascending=True)
                pg_konv['label'] = pg_konv['konversi_pct'].apply(lambda x: f"{x:.1f}%")
                fig_konv = px.bar(
                    pg_konv, x='konversi_pct', y='purchasing_group',
                    orientation='h', text='label',
                    color='konversi_pct',
                    color_continuous_scale=['#d62728', '#ffdd57', '#2ca02c'],
                    range_x=[0, 110],
                    labels={'konversi_pct': '% Konversi', 'purchasing_group': 'Purchasing Group'}
                )
                fig_konv.add_vline(x=100, line_dash="dash", line_color="gray",
                                   annotation_text="100%", annotation_position="top left")
                fig_konv.update_traces(textposition='outside')
                fig_konv.update_layout(
                    height=400,
                    margin=dict(t=20, b=20, l=20, r=20),
                    coloraxis_showscale=False
                )
                st.plotly_chart(fig_konv, use_container_width=True)

        else:
            st.info("Tidak ada data kinerja Purchasing Group pada rentang waktu ini.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2: BREAKDOWN METODE TENDER, TURN AROUND & KECEPATAN PROSES
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("Breakdown pengadaan berdasarkan **jenis tender** dan **Turn Around**, lengkap dengan analisis kecepatan proses dan tren lead time.")

        # ── KPI Kecepatan ─────────────────────────────────────────────────────
        speed_kpi_query = f"""
        SELECT
            ROUND(AVG(poi.pr_po_days)::numeric, 1)                           AS avg_lt_overall,
            ROUND(MIN(poi.pr_po_days)::numeric, 0)                           AS min_lt,
            ROUND(MAX(poi.pr_po_days)::numeric, 0)                           AS max_lt,
            ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP
                (ORDER BY poi.pr_po_days)::numeric, 1)                        AS median_lt,
            COUNT(CASE WHEN poi.pr_po_days <= 55 THEN 1 END)                 AS jml_ontime,
            COUNT(CASE WHEN poi.pr_po_days > 55 THEN 1 END)                  AS jml_late,
            COUNT(poi.pr_po_days)                                             AS total_lt
        FROM po_items poi
        JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
        WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
          AND poi.pr_po_days IS NOT NULL
          AND ({bagian_po_cond.replace('bagian_po', 'poh.bagian_po')})
          AND {dept_cond}
          AND {pg_cond}
        """

        with st.spinner("Memuat KPI kecepatan..."):
            speed_kpi = load_data(speed_kpi_query)

        spd_avg_lt = spd_med_lt = spd_min_lt = spd_max_lt = None
        spd_ontime = spd_late = spd_total = 0
        spd_ontime_pct = 0.0

        if not speed_kpi.empty and speed_kpi['total_lt'][0]:
            spd_avg_lt     = float(speed_kpi['avg_lt_overall'][0] or 0)
            spd_med_lt     = float(speed_kpi['median_lt'][0] or 0)
            spd_min_lt     = int(speed_kpi['min_lt'][0] or 0)
            spd_max_lt     = int(speed_kpi['max_lt'][0] or 0)
            spd_ontime     = int(speed_kpi['jml_ontime'][0] or 0)
            spd_late       = int(speed_kpi['jml_late'][0] or 0)
            spd_total      = int(speed_kpi['total_lt'][0] or 1)
            spd_ontime_pct = spd_ontime / spd_total * 100

            SPEED_KPI = [
                {
                    "key":        "kpi_lead_time",
                    "label":      "Avg Lead Time",
                    "value":      f"{format_number(spd_avg_lt, decimals=1)} Hari",
                    "delta":      "On Target" if spd_avg_lt <= 55 else "Over Target",
                    "delta_type": "green" if spd_avg_lt <= 55 else "red",
                    "formula": """\
**Avg Lead Time**: Rata-rata waktu proses PR→PO untuk semua Purchasing Group.

**Formula Excel:** (PO SAP)
- Buat kolom `= Date Ordered - 1St Full Release`
- Rata-rata kolom tersebut

**Target SLA = 55 hari.**
"""
                },
                {
                    "key":        "kpi_median",
                    "label":      "Median Lead Time",
                    "value":      f"{format_number(spd_med_lt, decimals=1)} Hari",
                    "delta":      "Nilai tengah distribusi",
                    "delta_type": "neutral",
                    "formula": """\
**Median Lead Time**: Nilai tengah distribusi lead time PO.

Jika median jauh lebih rendah dari rata-rata, berarti ada sejumlah kecil PO dengan lead time ekstrem. Gunakan median sebagai ukuran "kecepatan tipikal".
"""
                },
                {
                    "key":        "kpi_rentang",
                    "label":      "Rentang Lead Time",
                    "value":      f"{format_number(spd_min_lt)} - {format_number(spd_max_lt)} Hari",
                    "delta":      "Min - Maks",
                    "delta_type": "neutral",
                    "formula": """\
**Rentang Lead Time**: Selisih antara lead time terpendek dan terpanjang.

**Rentang sempit** = proses konsisten. **Rentang lebar** = variabilitas tinggi, perlu investigasi outlier.
"""
                },
                {
                    "key":        "kpi_ontime",
                    "label":      "On-Time (≤55 Hari)",
                    "value":      format_number(spd_ontime),
                    "delta":      f"{format_number(spd_ontime_pct, decimals=1)}% dari total",
                    "delta_type": "green" if spd_ontime_pct >= 80 else ("orange" if spd_ontime_pct >= 60 else "red"),
                    "formula": """\
**On-Time (≤55 Hari)**: Jumlah PO yang diproses dalam batas SLA 55 hari.

| % On-Time | Status |
|---|---|
| ≥ 80% | 🟢 Baik |
| 60–79% | 🟡 Perlu perhatian |
| < 60% | 🔴 Kritis |
"""
                },
                {
                    "key":        "kpi_late",
                    "label":      "Terlambat (>55 Hari)",
                    "value":      format_number(spd_late),
                    "delta":      f"{format_number(100 - spd_ontime_pct, decimals=1)}% dari total",
                    "delta_type": "red" if spd_ontime_pct < 60 else ("orange" if spd_ontime_pct < 80 else "green"),
                    "formula": """\
**Terlambat (>55 Hari)**: Jumlah PO yang melebihi batas SLA 55 hari.

Lihat tabel **Ringkasan Kecepatan per Purchasing Group** di bawah untuk identifikasi Purchasing Group dengan % terlambat tertinggi.
"""
                },
            ]

            st.markdown("""
                <h1 style='display: flex; align-items: center;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="currentColor" viewBox="0 0 16 16" style="margin-bottom: 8px; margin-right: 8px;">
                        <path d="M8 3.5a.5.5 0 0 0-1 0V9a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0 0 .496-.868L8 8.71V3.5z"/>
                        <path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0z"/>
                    </svg>
                    KPI Kecepatan Proses
                </h1>
            """, unsafe_allow_html=True)

            for row_start in range(0, len(SPEED_KPI), 3):
                cols = st.columns(3, gap="medium")
                for i, kpi in enumerate(SPEED_KPI[row_start:row_start + 3]):
                    with cols[i]:
                        st.markdown(
                            _card(ICONS[kpi["key"]], kpi["label"], kpi["value"],
                                  kpi["delta"], kpi["delta_type"]),
                            unsafe_allow_html=True
                        )
                        with st.popover(":material/visibility:", help="Lihat Formula"):
                            st.info(kpi["formula"])
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

        st.markdown("---")

        # ── Row 1: Kontrak vs Non-Kontrak + Distribusi Turn Around ────────────
        col1, col2 = st.columns(2)
        with col1:
            title_col, btn_col = st.columns([9, 1])
            with title_col:
                st.markdown("""
                    <h1 style='display: flex; align-items: center; font-size:22px;'>
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                            <path d="M9.293 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4.707A1 1 0 0 0 13.707 4L10 .293A1 1 0 0 0 9.293 0M9.5 3.5v-2l3 3h-2a1 1 0 0 1-1-1M4.5 9a.5.5 0 0 1 0-1h7a.5.5 0 0 1 0 1zM4 10.5a.5.5 0 0 1 .5-.5h7a.5.5 0 0 1 0 1h-7a.5.5 0 0 1-.5-.5m.5 2.5a.5.5 0 0 1 0-1h4a.5.5 0 0 1 0 1z"/>
                        </svg>
                        Kontrak vs Non-Kontrak per Purchasing Group
                    </h1>
                """, unsafe_allow_html=True)
            with btn_col:
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                with st.popover(":material/visibility:", help="Lihat Formula"):
                    st.info("""\
**Kontrak vs Non-Kontrak per Purchasing Group**: Stacked bar chart komposisi nilai realisasi berdasarkan jenis tender per Purchasing Group.

**Formula Excel:** (PO SAP)
- Kolom Jenis Tender: `= IF(LEFT(No Contract, 1) = "4", "PR - PO Kontrak", "Tender Normal")`
- Total Realisasi: `= SUM(Total Amount in Local Curr)`

| Jenis | Karakteristik |
|---|---|
| PR - PO Kontrak | Menggunakan kontrak → lebih cepat |
| Tender Normal | Proses penawaran baru → biasanya lebih lama |
""")
            st.caption("Komposisi nilai realisasi berdasarkan jenis tender per Purchasing Group.")

            kontrak_query = f"""
            SELECT
                CASE
                    WHEN poi.contract_no IS NOT NULL AND poi.contract_no <> ''
                     AND LEFT(poi.contract_no, 1) = '4' THEN 'PR - PO Kontrak'
                    ELSE 'Tender Normal'
                END                                                          AS jenis_kontrak,
                COALESCE(poh.purchasing_group, 'Unassigned')                 AS purchasing_group,
                COUNT(DISTINCT poi.nomor_po || '-' || poi.item_po::text)     AS jml_item,
                COALESCE(SUM(poi.total_amount_local_curr), 0)                AS total_realisasi,
                ROUND(AVG(poi.pr_po_days)::numeric, 1)                       AS avg_lead_time
            FROM po_items poi
            JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
            WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
              AND poi.first_full_release IS NOT NULL
              AND ({bagian_po_cond.replace('bagian_po', 'poh.bagian_po')})
              AND {dept_cond} AND {pg_cond}
            GROUP BY 1, COALESCE(poh.purchasing_group, 'Unassigned')
            ORDER BY jenis_kontrak, purchasing_group
            """

            kontrak_global_query = f"""
            SELECT
                CASE
                    WHEN poi.contract_no IS NOT NULL AND poi.contract_no <> ''
                     AND LEFT(poi.contract_no, 1) = '4' THEN 'PR - PO Kontrak'
                    ELSE 'Tender Normal'
                END                                                          AS jenis_kontrak,
                COUNT(DISTINCT poi.nomor_po || '-' || poi.item_po::text)     AS jml_item,
                COALESCE(SUM(poi.total_amount_local_curr), 0)                AS total_realisasi,
                ROUND(AVG(poi.pr_po_days)::numeric, 1)                       AS avg_lead_time
            FROM po_items poi
            JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
            WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
              AND poi.first_full_release IS NOT NULL
              AND ({bagian_po_cond.replace('bagian_po', 'poh.bagian_po')})
              AND {dept_cond} AND {pg_cond}
            GROUP BY 1
            ORDER BY jenis_kontrak
            """

            with st.spinner("Memuat data kontrak..."):
                kontrak_data   = load_data(kontrak_query)
                kontrak_global = load_data(kontrak_global_query)

            if not kontrak_data.empty:
                kontrak_sum = kontrak_global if not kontrak_global.empty else kontrak_data.groupby('jenis_kontrak').agg(
                    jml_item=('jml_item', 'sum'),
                    total_realisasi=('total_realisasi', 'sum'),
                    avg_lead_time=('avg_lead_time', 'mean')
                ).reset_index()

                c1, c2 = st.columns(2)
                for i, (_, row) in enumerate(kontrak_sum.iterrows()):
                    col_m = c1 if i == 0 else c2
                    with col_m:
                        lt = f"{row['avg_lead_time']:.1f} Hari" if pd.notna(row['avg_lead_time']) else "N/A"
                        st.metric(
                            f"{':material/assignment:' if 'Kontrak' in str(row['jenis_kontrak']) else ':material/lock_open:'} {row['jenis_kontrak']}",
                            format_idr(row['total_realisasi']),
                            delta=f"{int(row['jml_item']):,} item | {lt}"
                        )

                kontrak_data['label'] = kontrak_data['total_realisasi'].apply(format_idr_short)
                fig_k = px.bar(
                    kontrak_data,
                    x='purchasing_group', y='total_realisasi',
                    color='jenis_kontrak', barmode='stack',
                    text='label',
                    color_discrete_map={'PR - PO Kontrak': '#1f77b4', 'Tender Normal': '#ff7f0e'},
                    labels={
                        'purchasing_group': 'Purchasing Group',
                        'total_realisasi' : 'Total Realisasi (IDR)',
                        'jenis_kontrak'   : 'Jenis'
                    }
                )
                fig_k.update_traces(textposition='inside', textfont_size=9)
                fig_k.update_layout(
                    height=420,
                    margin=dict(t=40, b=20, l=20, r=20),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02)
                )
                st.plotly_chart(fig_k, use_container_width=True)
            else:
                st.info("Tidak ada data kontrak pada periode ini.")

        with col2:
            title_col, btn_col = st.columns([9, 1])
            with title_col:
                st.markdown("""
                    <h1 style='display: flex; align-items: center; font-size:22px;'>
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                            <path d="M11.251.068a.5.5 0 0 1 .227.58L9.677 6.5H13a.5.5 0 0 1 .364.843l-8 8.5a.5.5 0 0 1-.842-.49L6.323 9.5H3a.5.5 0 0 1-.364-.843l8-8.5a.5.5 0 0 1 .615-.09z"/>
                        </svg>
                        Distribusi Turn Around per Purchasing Group
                    </h1>
                """, unsafe_allow_html=True)
            with btn_col:
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                with st.popover(":material/visibility:", help="Lihat Formula"):
                    st.info("""\
**Distribusi Turn Around per Purchasing Group**: Komposisi item PO berdasarkan kategori Turn Around (TA vs non-TA).

**Formula Excel:**
- Kolom TA: `= IF(LEFT(Departement(Requisitioner), 2) = "TA", "TA", "non")`

| Kategori | Keterangan |
|---|---|
| TA | Turn Around, pemeliharaan besar/shutdown periodik |
| non | Operasional rutin harian |
""")
            st.caption("Komposisi item PO berdasarkan kategori Turn Around (TA vs non-TA).")

            ta_query = f"""
            SELECT
                COALESCE(poh.purchasing_group, 'Unassigned')                 AS purchasing_group,
                CASE WHEN LEFT(COALESCE(poi.department_code, ''), 2) = 'TA'
                     THEN 'TA' ELSE 'non' END                                AS turn_around,
                COUNT(DISTINCT poi.nomor_po || '-' || poi.item_po::text)     AS jml_item,
                COALESCE(SUM(poi.total_amount_local_curr), 0)                AS total_realisasi,
                ROUND(AVG(poi.pr_po_days)::numeric, 1)                       AS avg_lead_time
            FROM po_items poi
            JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
            WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
              AND poi.first_full_release IS NOT NULL
              AND ({bagian_po_cond.replace('bagian_po', 'poh.bagian_po')})
              AND {dept_cond} AND {pg_cond}
            GROUP BY COALESCE(poh.purchasing_group, 'Unassigned'),
                     CASE WHEN LEFT(COALESCE(poi.department_code, ''), 2) = 'TA' THEN 'TA' ELSE 'non' END
            ORDER BY purchasing_group, jml_item DESC
            """

            ta_global_query = f"""
            SELECT
                CASE WHEN LEFT(COALESCE(poi.department_code, ''), 2) = 'TA'
                     THEN 'TA' ELSE 'non' END                                AS turn_around,
                COUNT(DISTINCT poi.nomor_po || '-' || poi.item_po::text)     AS jml_item,
                COALESCE(SUM(poi.total_amount_local_curr), 0)                AS total_realisasi,
                ROUND(AVG(poi.pr_po_days)::numeric, 1)                       AS avg_lead_time
            FROM po_items poi
            JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
            WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
              AND poi.first_full_release IS NOT NULL
              AND ({bagian_po_cond.replace('bagian_po', 'poh.bagian_po')})
              AND {dept_cond} AND {pg_cond}
            GROUP BY 1
            ORDER BY jml_item DESC
            """

            with st.spinner("Memuat data turn around..."):
                ta_data   = load_data(ta_query)
                ta_global = load_data(ta_global_query)

            if not ta_data.empty:
                ta_sum = ta_global if not ta_global.empty else ta_data.groupby('turn_around').agg(
                    jml_item=('jml_item', 'sum'),
                    total_realisasi=('total_realisasi', 'sum'),
                    avg_lead_time=('avg_lead_time', 'mean')
                ).reset_index()
                ta_sum = ta_sum.sort_values('jml_item', ascending=False)

                fig_ta_pie = px.pie(
                    ta_sum, values='jml_item', names='turn_around', hole=0.4,
                    title="Distribusi Jumlah Item per Turn Around"
                )
                fig_ta_pie.update_layout(height=320, margin=dict(t=40, b=20, l=20, r=20))
                st.plotly_chart(fig_ta_pie, use_container_width=True)

                ta_lt = ta_sum[ta_sum['avg_lead_time'].notna()].copy()
                ta_lt['avg_lead_time'] = ta_lt['avg_lead_time'].round(1)
                ta_lt['label'] = ta_lt['avg_lead_time'].apply(lambda x: f"{x} Hr")
                ta_lt = ta_lt.sort_values('avg_lead_time')
                fig_ta_lt = px.bar(
                    ta_lt, x='avg_lead_time', y='turn_around',
                    orientation='h', text='label',
                    color='avg_lead_time',
                    color_continuous_scale=['#2ca02c', '#ffdd57', '#d62728'],
                    labels={
                        'avg_lead_time': 'Lead Time Rata-rata (Hari)',
                        'turn_around'  : 'Turn Around'
                    },
                    title="Lead Time Rata-rata per Kategori Turn Around"
                )
                fig_ta_lt.add_vline(x=55, line_dash="dash", line_color="red",
                                    annotation_text="Target 55 Hari",
                                    annotation_position="top right")
                fig_ta_lt.update_traces(textposition='outside')
                fig_ta_lt.update_layout(
                    height=350,
                    margin=dict(t=40, b=20, l=20, r=20),
                    coloraxis_showscale=False
                )
                st.plotly_chart(fig_ta_lt, use_container_width=True)
            else:
                st.info("Tidak ada data turn around pada periode ini.")

        # ── Tabel Detail Turn Around (full width) ─────────────────────────────
        if 'ta_data' in locals() and not ta_data.empty:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:22px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                        <path d="M9.293 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4.707A1 1 0 0 0 13.707 4L10 .293A1 1 0 0 0 9.293 0M9.5 3.5v-2l3 3h-2a1 1 0 0 1-1-1M4.5 9a.5.5 0 0 1 0-1h7a.5.5 0 0 1 0 1zM4 10.5a.5.5 0 0 1 .5-.5h7a.5.5 0 0 1 0 1h-7a.5.5 0 0 1-.5-.5m.5 2.5a.5.5 0 0 1 0-1h4a.5.5 0 0 1 0 1z"/>
                    </svg>
                    Detail per Purchasing Group × Turn Around
                </h1>
            """, unsafe_allow_html=True)
            df_ta_disp = ta_data.copy()
            df_ta_disp['total_realisasi'] = df_ta_disp['total_realisasi'].apply(format_idr)
            df_ta_disp['avg_lead_time']   = df_ta_disp['avg_lead_time'].apply(
                lambda x: f"{x} Hari" if pd.notna(x) else "N/A")
            st.dataframe(
                df_ta_disp.rename(columns={
                    'purchasing_group': 'Purchasing Group',
                    'turn_around'     : 'Turn Around',
                    'jml_item'        : 'Jml Item',
                    'total_realisasi' : 'Total Realisasi',
                    'avg_lead_time'   : 'Lead Time Avg',
                }),
                use_container_width=True, height=280
            )

        if 'kontrak_data' in locals() and not kontrak_data.empty:
            st.markdown("---")

            # ── Row 2: Lead Time Kontrak + Tren Lead Time ─────────────────────
            col1, col2 = st.columns(2)
            with col1:
                title_col, btn_col = st.columns([9, 1])
                with title_col:
                    st.markdown("""
                        <h1 style='display: flex; align-items: center; font-size:22px;'>
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                                <path d="M6 .5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1H9v1.07a7.001 7.001 0 0 1 3.274 12.474l.601.602a.5.5 0 0 1-.707.708l-.746-.746A6.97 6.97 0 0 1 8 16a6.97 6.97 0 0 1-3.422-.892l-.746.746a.5.5 0 0 1-.707-.708l.602-.602A7.001 7.001 0 0 1 7 2.07V1h-.5A.5.5 0 0 1 6 .5m2.5 5a.5.5 0 0 0-1 0v3.362l-1.429 2.38a.5.5 0 1 0 .858.515l1.5-2.5A.5.5 0 0 0 8.5 9zM.86 5.387A2.5 2.5 0 1 1 4.387 1.86 8.04 8.04 0 0 0 .86 5.387M11.613 1.86a2.5 2.5 0 1 1 3.527 3.527 8.04 8.04 0 0 0-3.527-3.527"/>
                            </svg>
                            Lead Time: Kontrak vs Non-Kontrak
                        </h1>
                    """, unsafe_allow_html=True)
                with btn_col:
                    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                    with st.popover(":material/visibility:", help="Lihat Formula"):
                        st.info("""\
**Lead Time: Kontrak vs Non-Kontrak per Purchasing Group**: Grouped bar chart rata-rata lead time per jenis tender.

**Ekspektasi:**
- **PR - PO Kontrak** → lebih pendek (vendor & harga sudah disepakati)
- **Tender Normal** → lebih panjang (perlu negosiasi)

**Target:** Garis merah = **55 hari**.
""")
                st.caption("Rata-rata lead time per jenis tender per Purchasing Group.")

                kontrak_lt = kontrak_data[kontrak_data['avg_lead_time'].notna()]
                fig_klt = px.bar(
                    kontrak_lt,
                    x='purchasing_group', y='avg_lead_time',
                    color='jenis_kontrak', barmode='group',
                    text=kontrak_lt['avg_lead_time'].apply(lambda x: f"{x} Hr"),
                    color_discrete_map={'PR - PO Kontrak': '#1f77b4', 'Tender Normal': '#ff7f0e'},
                    labels={
                        'purchasing_group': 'Purchasing Group',
                        'avg_lead_time'   : 'Lead Time Avg (Hari)',
                        'jenis_kontrak'   : 'Jenis'
                    }
                )
                fig_klt.add_hline(y=55, line_dash="dash", line_color="red",
                                  annotation_text="Target 55 Hari",
                                  annotation_position="bottom right")
                fig_klt.update_traces(textposition='outside', textfont_size=9)
                fig_klt.update_layout(
                    height=380,
                    margin=dict(t=40, b=20, l=20, r=20),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02)
                )
                st.plotly_chart(fig_klt, use_container_width=True)

            with col2:
                title_col, btn_col = st.columns([9, 1])
                with title_col:
                    st.markdown("""
                        <h1 style='display: flex; align-items: center; font-size:22px;'>
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                                <path d="M10.854 7.146a.5.5 0 0 1 0 .708l-3 3a.5.5 0 0 1-.708 0l-1.5-1.5a.5.5 0 1 1 .708-.708L7.5 9.793l2.646-2.647a.5.5 0 0 1 .708 0"/>
                                <path d="M3.5 0a.5.5 0 0 1 .5.5V1h8V.5a.5.5 0 0 1 1 0V1h1a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2h1V.5a.5.5 0 0 1 .5-.5M1 4v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V4z"/>
                            </svg>
                            Tren Lead Time per Bulan
                        </h1>
                    """, unsafe_allow_html=True)
                with btn_col:
                    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                    with st.popover(":material/visibility:", help="Lihat Formula"):
                        st.info("""\
**Tren Lead Time per Bulan**: Line chart rata-rata kecepatan proses per bulan, dibedakan antara Tender Normal dan PR-PO Kontrak.

**Cara membaca:**
- Tren **turun** = proses semakin efisien ✅
- Tren **naik** = ada hambatan sistemik ⚠️
- **Lonjakan bulan tertentu** = cek event khusus (TA, audit, akhir tahun)

**Target:** Garis merah = **55 hari**.
""")
                st.caption("Rata-rata kecepatan proses per bulan, dibedakan antara Tender Normal dan PR-PO Kontrak.")

                trend_lt_query = f"""
                SELECT
                    DATE_TRUNC('month', poh.date_ordered)::DATE                  AS bulan,
                    CASE
                        WHEN poi.contract_no IS NOT NULL AND poi.contract_no <> ''
                         AND LEFT(poi.contract_no, 1) = '4' THEN 'PR - PO Kontrak'
                        ELSE 'Tender Normal'
                    END                                                          AS jenis_kontrak,
                    ROUND(AVG(poi.pr_po_days)::numeric, 1)                       AS avg_lt,
                    COUNT(DISTINCT poi.nomor_po || '-' || poi.item_po::text)     AS jml_item
                FROM po_items poi
                JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
                WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
                  AND poi.pr_po_days IS NOT NULL
                  AND ({bagian_po_cond.replace('bagian_po', 'poh.bagian_po')})
                  AND {dept_cond} AND {pg_cond}
                GROUP BY 1, 2
                ORDER BY 1, 2
                """
                with st.spinner("Memuat tren lead time..."):
                    trend_lt_data = load_data(trend_lt_query)

                if not trend_lt_data.empty:
                    trend_lt_data['bulan'] = pd.to_datetime(trend_lt_data['bulan'])
                    fig_trend_lt = px.line(
                        trend_lt_data, x='bulan', y='avg_lt',
                        color='jenis_kontrak', markers=True,
                        color_discrete_map={
                            'PR - PO Kontrak': '#1f77b4',
                            'Tender Normal'  : '#ff7f0e'
                        },
                        labels={
                            'bulan'        : 'Bulan',
                            'avg_lt'       : 'Lead Time Avg (Hari)',
                            'jenis_kontrak': 'Jenis'
                        }
                    )
                    fig_trend_lt.add_hline(y=55, line_dash="dash", line_color="red",
                                           annotation_text="Target 55 Hari",
                                           annotation_position="bottom right")
                    fig_trend_lt.update_layout(
                        height=380,
                        margin=dict(t=20, b=20, l=20, r=20),
                        hovermode='x unified',
                        legend=dict(orientation="h", yanchor="bottom", y=1.02)
                    )
                    st.plotly_chart(fig_trend_lt, use_container_width=True)
                else:
                    st.info("Tidak ada data tren lead time.")

            st.markdown("---")

            # ── Tabel Ringkasan Kecepatan (full width) ────────────────────────
            title_col, btn_col = st.columns([9, 1])
            with title_col:
                st.markdown("""
                    <h1 style='display: flex; align-items: center; font-size:22px;'>
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                            <path d="M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2zm15 2h-4v3h4zm0 4h-4v3h4zm0 4h-4v3h3a1 1 0 0 0 1-1zm-5 3v-3H6v3zm-5 0v-3H1v2a1 1 0 0 0 1 1zm-4-4h4V8H1zm0-4h4V4H1zm5-3v3h4V4zm4 4H6v3h4z"/>
                        </svg>
                        Ringkasan Kecepatan per Purchasing Group × Jenis Tender
                    </h1>
                """, unsafe_allow_html=True)
            with btn_col:
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                with st.popover(":material/visibility:", help="Lihat Formula"):
                    st.info("""\
**Ringkasan Kecepatan**: Detail ketepatan waktu (On-Time vs Terlambat) per Purchasing Group dan jenis tender.

**On-Time** = PO diproses dalam ≤ 55 hari dari `1St Full Release` ke `Date Ordered`.
""")
            st.caption("Detail ketepatan waktu (On-Time vs Terlambat) per Purchasing Group dan jenis tender.")

            lt_tender_query = f"""
            SELECT
                COALESCE(poh.purchasing_group, 'Unassigned')                 AS purchasing_group,
                CASE
                    WHEN poi.contract_no IS NOT NULL AND poi.contract_no <> ''
                     AND LEFT(poi.contract_no, 1) = '4' THEN 'PR - PO Kontrak'
                    ELSE 'Tender Normal'
                END                                                          AS jenis_tender,
                COUNT(DISTINCT poi.nomor_po || '-' || poi.item_po::text)     AS jml_item,
                ROUND(AVG(poi.pr_po_days)::numeric, 1)                       AS avg_lt,
                ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP
                    (ORDER BY poi.pr_po_days)::numeric, 1)                    AS median_lt,
                COUNT(CASE WHEN poi.pr_po_days <= 55 THEN 1 END)             AS jml_ontime,
                COUNT(CASE WHEN poi.pr_po_days > 55 THEN 1 END)              AS jml_late
            FROM po_items poi
            JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
            WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
              AND poi.pr_po_days IS NOT NULL
              AND ({bagian_po_cond.replace('bagian_po', 'poh.bagian_po')})
              AND {dept_cond} AND {pg_cond}
            GROUP BY COALESCE(poh.purchasing_group, 'Unassigned'),
                     CASE
                         WHEN poi.contract_no IS NOT NULL AND poi.contract_no <> ''
                          AND LEFT(poi.contract_no, 1) = '4' THEN 'PR - PO Kontrak'
                         ELSE 'Tender Normal'
                     END
            ORDER BY purchasing_group, jenis_tender
            """
            with st.spinner("Memuat ringkasan kecepatan..."):
                lt_tender_data = load_data(lt_tender_query)

            if not lt_tender_data.empty:
                lt_tender_data['ontime_pct'] = (
                    lt_tender_data['jml_ontime'] /
                    (lt_tender_data['jml_ontime'] + lt_tender_data['jml_late'])
                    .replace(0, float('nan')) * 100
                ).round(1).fillna(0)

                df_speed_disp = lt_tender_data.copy()
                df_speed_disp['avg_lt']     = df_speed_disp['avg_lt'].apply(
                    lambda x: f"{x} Hari" if pd.notna(x) else "N/A")
                df_speed_disp['median_lt']  = df_speed_disp['median_lt'].apply(
                    lambda x: f"{x} Hari" if pd.notna(x) else "N/A")
                df_speed_disp['ontime_pct'] = df_speed_disp['ontime_pct'].apply(
                    lambda x: f"{x:.1f}%")
                st.dataframe(
                    df_speed_disp.rename(columns={
                        'purchasing_group': 'Purchasing Group',
                        'jenis_tender'    : 'Jenis Tender',
                        'jml_item'        : 'Jml Item',
                        'avg_lt'          : 'Lead Time Avg',
                        'median_lt'       : 'Lead Time Median',
                        'jml_ontime'      : 'On-Time (≤55 Hr)',
                        'jml_late'        : 'Terlambat (>55 Hr)',
                        'ontime_pct'      : '% On-Time',
                    }),
                    use_container_width=True, height=320
                )
            else:
                lt_tender_data = pd.DataFrame()
                st.info("Tidak ada data ringkasan kecepatan.")

            # ── Download ──────────────────────────────────────────────────────
            # Tambahkan import io
            import io

            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                # Ubah ke XLSX
                excel_buffer_kontrak = io.BytesIO()
                with pd.ExcelWriter(excel_buffer_kontrak, engine='openpyxl') as writer:
                    kontrak_data.to_excel(writer, index=False, sheet_name='Breakdown_Kontrak')
                excel_buffer_kontrak.seek(0) # Kembali ke awal buffer
                st.download_button(
                    label="Download Data Kontrak (XLSX)",
                    icon=":material/download:",
                    data=excel_buffer_kontrak,
                    file_name=f"breakdown_kontrak_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

                )
            with col_dl2:
                if not lt_tender_data.empty:
                    excel_buffer_speed = io.BytesIO()
                    with pd.ExcelWriter(excel_buffer_speed, engine='openpyxl') as writer:
                        lt_tender_data.to_excel(writer, index=False, sheet_name='Kecepatan_Proses')
                    excel_buffer_speed.seek(0)
                    st.download_button(
                        label="Download Ringkasan Kecepatan (XLSX)",
                        icon=":material/download:",
                        data=excel_buffer_speed,
                        file_name=f"kecepatan_proses_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════════
    # INTEGRASI AI
    # ══════════════════════════════════════════════════════════════════════════
    konteks_lines = []

    konteks_lines.append("## 0. FILTER YANG SEDANG DITERAPKAN USER")
    konteks_lines.append(info_filter)
    konteks_lines.append("\n")

    konteks_lines.append("## 1. RINGKASAN KPI GLOBAL KINERJA PURCHASING GROUP")
    konteks_lines.append(f"- Total Item PR: {t_item_pr} (Terkonversi ke PO: {konversi_pct:.1f}%)")
    konteks_lines.append(f"- Total OE: {format_idr(t_oe)}")
    konteks_lines.append(f"- Total Realisasi PO: {format_idr(t_real)}")
    konteks_lines.append(f"- Efisiensi Total: {format_idr(t_efis)} ({t_efis_pct:.1f}%)")
    if spd_avg_lt is not None:
        konteks_lines.append(f"- Rata-rata Lead Time: {spd_avg_lt:.1f} Hari | Median: {spd_med_lt:.1f} Hari")
        konteks_lines.append(f"- On-Time (≤55 Hari): {spd_ontime} ({spd_ontime_pct:.1f}%) | Terlambat: {spd_late}")
    konteks_lines.append("\n")

    if 'df_table' in locals() and not df_table.empty:
        konteks_lines.append("## 2. KINERJA PER PURCHASING GROUP (OVERVIEW)")
        df_pg_simple = df_table[['purchasing_group', 'nilai_po', 'efisiensi_pct', 'avg_lead_time']]
        konteks_lines.append(df_pg_simple.to_csv(index=False))
        konteks_lines.append("\n")

    if 'kontrak_data' in locals() and not kontrak_data.empty:
        konteks_lines.append("## 3. BREAKDOWN JENIS TENDER (KONTRAK VS NORMAL) PER PG")
        df_kontrak_simple = kontrak_data[['purchasing_group', 'jenis_kontrak', 'total_realisasi', 'avg_lead_time']]
        konteks_lines.append(df_kontrak_simple.to_csv(index=False))
        konteks_lines.append("\n")

    if 'lt_tender_data' in locals() and not lt_tender_data.empty:
        konteks_lines.append("## 4. DETAIL KETEPATAN WAKTU PER PG × JENIS TENDER")
        df_speed_simple = lt_tender_data[['purchasing_group', 'jenis_tender', 'jml_ontime', 'jml_late', 'ontime_pct']]
        konteks_lines.append(df_speed_simple.to_csv(index=False))
        konteks_lines.append("\n")

    suplemen = "\n# SUPLEMEN - DETAIL HALAMAN INI (Kinerja Purchasing Group)\n" + "\n".join(konteks_lines)
    konteks_final = kwargs.get("global_context", "") + "\n---\n" + suplemen

    with st.expander("Tanya ke Melati (Monitoring, Evaluasi, Laporan Terintegrasi)"):
        render_chat_analyst(
            konteks_data_teks=konteks_final,
            nama_halaman="Kinerja Purchasing Group",
            load_data_fn=load_data,
        )