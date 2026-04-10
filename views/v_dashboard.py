"""
v_dashboard.py - Halaman Dashboard Monitoring SAP
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import calendar
from utils import format_idr, format_idr_short, format_number, format_currency, render_chat_analyst, idr_axis

def render(filter_conditions, bagian_pr_cond, bagian_po_cond, load_data, **kwargs):
        
        info_filter = kwargs.get('info_filter', 'Tidak ada filter spesifik')
        dept_cond   = kwargs.get('dept_cond', '1=1')
        pg_cond     = kwargs.get('pg_cond',   '1=1')
        
        def toggle_state(state_key):
            st.session_state[state_key] = not st.session_state[state_key]

        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:60px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" fill="currentColor" class="bi bi-clipboard2-data-fill" viewBox="0 0 16 16" style="margin-bottom: 10px; margin-right: 8px;">
                    <path d="M10 .5a.5.5 0 0 0-.5-.5h-3a.5.5 0 0 0-.5.5.5.5 0 0 1-.5.5.5.5 0 0 0-.5.5V2a.5.5 0 0 0 .5.5h5A.5.5 0 0 0 11 2v-.5a.5.5 0 0 0-.5-.5.5.5 0 0 1-.5-.5"/>
                    <path d="M4.085 1H3.5A1.5 1.5 0 0 0 2 2.5v12A1.5 1.5 0 0 0 3.5 16h9a1.5 1.5 0 0 0 1.5-1.5v-12A1.5 1.5 0 0 0 12.5 1h-.585q.084.236.085.5V2a1.5 1.5 0 0 1-1.5 1.5h-5A1.5 1.5 0 0 1 4 2v-.5q.001-.264.085-.5M10 7a1 1 0 1 1 2 0v5a1 1 0 1 1-2 0zm-6 4a1 1 0 1 1 2 0v1a1 1 0 1 1-2 0zm4-3a1 1 0 0 1 1 1v3a1 1 0 1 1-2 0V9a1 1 0 0 1 1-1"/>
                </svg>
                PR-PO SAP Monitoring Dashboard
            </h1>
        """, unsafe_allow_html=True)
        st.markdown("""
            <style>
            [data-testid="stMetricValue"] > div {
                font-size: 2rem !important; /* Ukuran font standar yang nyaman dibaca, tidak terlalu besar/kecil */
                white-space: normal !important; /* KUNCI: Mencegah teks dipotong (...) dan memungkinkannya turun baris */
                word-wrap: break-word !important; /* Memastikan angka/kata panjang bisa patah dengan rapi */
                line-height: 1.2 !important; /* Mengatur jarak vertikal jika teks menjadi 2 baris */
            }
            </style>
        """, unsafe_allow_html=True)
        st.markdown("---")

        # ── KPI ──────────────────────────────────────────
        st.markdown("""
            <h1 style='display: flex; align-items: center;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor" class="bi bi-graph-up" viewBox="0 0 16 16" style="margin-bottom: 8px; margin-right: 8px;">
                    <path fill-rule="evenodd" d="M0 0h1v15h15v1H0zm14.817 3.113a.5.5 0 0 1 .07.704l-4.5 5.5a.5.5 0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5 0 0 1 .758-.06l2.609 2.61 4.15-5.073a.5.5 0 0 1 .704-.07"/>
                </svg>
                Key Performance Indicators
            </h1>
        """, unsafe_allow_html=True)

        date_from = kwargs.get('date_from')
        date_to   = kwargs.get('date_to')

        # ── Query PR: filter by first_full_release (hanya PR yang sudah full release) ─
        pr_kpi_query = f"""
        WITH unique_pr AS (
            SELECT 
                no_pr, 
                line_item_pr,
                MAX(CASE WHEN nomor_po IS NOT NULL THEN 1 ELSE 0 END) AS has_po,
                MAX(estimasi_pr) AS oe_val
            FROM vw_pr_po_complete
            WHERE {filter_conditions} AND {bagian_pr_cond} AND no_pr != 'No PR'
              AND first_full_release IS NOT NULL
            GROUP BY no_pr, line_item_pr
        )
        SELECT
            COUNT(*) AS total_pr,
            SUM(has_po) AS pr_with_po,
            COUNT(*) - SUM(has_po) AS pr_without_po,
            COALESCE(SUM(oe_val), 0) AS total_estimasi
        FROM unique_pr
        """

        # ── Query PO: filter by date_ordered langsung dari tabel po_items ──────
        bagian_po_poi = bagian_po_cond.replace('bagian_po', 'poi.bagian_po')
        filter_po = filter_conditions.replace('department_code', 'poi.department_code').replace('plant_code', 'poi.plant_code').replace('tgl_create_pr', 'poh.date_ordered').replace('first_full_release', 'poh.date_ordered')

        po_kpi_query = f"""
        SELECT
            COUNT(poi.nomor_po)                                           AS total_po,
            COALESCE(SUM(poi.total_amount_local_curr), 0)                 AS total_po_amount,
            COALESCE(SUM(poi.quantity_pr * poi.estimasi_pr), 0)           AS total_oe_po,
            ROUND(AVG(
                CASE WHEN poi.first_full_release IS NOT NULL AND poh.date_ordered IS NOT NULL
                THEN (poh.date_ordered::date - poi.first_full_release::date)
                END
            )::numeric, 2)                                                        AS avg_lead_time,
            COUNT(DISTINCT poh.nomor_po)                                  AS total_po_distinct,
            COUNT(CASE WHEN poi.status_pengiriman = 'SELESAI'
                THEN 1 END)                                               AS po_delivered,
            COUNT(CASE WHEN poi.on_time_delivery = 'TEPAT WAKTU'
                THEN 1 END)                                               AS po_ontime,
            COUNT(CASE WHEN poi.on_time_delivery IN ('TEPAT WAKTU','TERLAMBAT')
                THEN 1 END)                                               AS po_delivered_total,
            COALESCE(SUM(poi.total_amount_local_curr), 0)                 AS realisasi_po,
            COALESCE(SUM(CASE WHEN poh.vendor_code IN ('4000000011', '4000000012') 
                         THEN poi.total_amount_local_curr ELSE 0 END), 0) AS total_sinergi_pi
        FROM po_items poi
        JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
        WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
          AND {bagian_po_poi}
          AND {filter_po}
        """

        with st.spinner("Memuat KPI..."):
            pr_kpi = load_data(pr_kpi_query)
            po_kpi = load_data(po_kpi_query)

        total_pr         = int(pr_kpi['total_pr'][0] or 0)
        total_po         = int(po_kpi['total_po'][0] or 0)
        pr_with_po       = int(pr_kpi['pr_with_po'][0] or 0)
        pr_without       = int(pr_kpi['pr_without_po'][0] or 0)
        estimasi_pr_all  = float(pr_kpi['total_estimasi'][0] or 0)
        oe_po_val        = float(po_kpi['total_oe_po'][0] or 0)
        po_amount_val    = float(po_kpi['total_po_amount'][0] or 0)
        savings          = oe_po_val - po_amount_val
        savings_pct      = ((savings / oe_po_val) * 100) if oe_po_val > 0 else 0.0
        _alt             = po_kpi['avg_lead_time'][0]
        avg_lt_val       = float(_alt) if _alt is not None else 0.0
        total_po_dist    = int(po_kpi['total_po_distinct'][0] or 0)
        po_delivered     = int(po_kpi['po_delivered'][0] or 0)
        po_ontime        = int(po_kpi['po_ontime'][0] or 0)
        po_del_tot       = int(po_kpi['po_delivered_total'][0] or 0)
        produktivitas    = (total_po / total_pr * 100) if total_po > 0 else 0.0
        pct_pengiriman   = (po_delivered / total_po * 100) if total_po > 0 else 0.0
        ketepatan_pct    = (po_ontime / po_del_tot * 100) if po_del_tot > 0 else 0.0
        sinergi_pi_val   = float(po_kpi['total_sinergi_pi'][0] or 0)

        # ── KPI_DASH: 14 item, 3 per baris ────────────────────────────────────
        KPI_DASH = [
            {
                "key": "kpi_total_pr",
                "icon_path": "M5 10.5a.5.5 0 0 1 .5-.5h2a.5.5 0 0 1 0 1h-2a.5.5 0 0 1-.5-.5m0-2a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5m0-2a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5 M3 0h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2m0 1a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1z",
                "label": "Total PR",
                "value": f"{format_number(total_pr)}",
                "delta": f"{format_number(pr_with_po)} with PO",
                "formula": """\
**Total PR**: Jumlah Purchase Requisition unik dalam periode filter. Dihitung dari baris yang memiliki `1St Full Release` terisi dan tanggalnya masuk dalam rentang periode yang dipilih.

**Formula Excel:** (PR SAP)
- Filter **1St Full Release** selain `blanks`
- Filter **Material No** selain `1000076`
- Filter **PR Deletion Flag** selain `X`
- Filter **Account Assignment** selain `U`
- Hitung barisnya (multi winners dihitung **1**)

**Target:** -\
""",
            },
            {
                "key": "kpi_total_po",
                "icon_path": "M8 1a2.5 2.5 0 0 1 2.5 2.5V4h-5v-.5A2.5 2.5 0 0 1 8 1m3.5 3v-.5a3.5 3.5 0 1 0-7 0V4H1v10a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V4zM2 5h12v9a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1z",
                "label": "Total PO",
                "value": f"{format_number(total_po)}",
                "delta": f"{format_number(pr_without)} PR pending",
                "formula": """\
**Total PO**: Jumlah Purchase Order dalam periode filter.

**Formula Excel:** (PO SAP)
- Filter **Material No** selain `1000076`
- Filter **PO Deletion Flag** selain `L`
- Hitung barisnya

**Target:** -\
""",
            },
            {
                "key": "kpi_produktivitas",
                "icon_path": "M0 0h1v15h15v1H0zm14.817 3.113a.5.5 0 0 1 .07.704l-4.5 5.5a.5.5 0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5 0 0 1 .758-.06l2.609 2.61 4.15-5.073a.5.5 0 0 1 .704-.07",
                "label": "Produktivitas PR-PO",
                "value": f"{format_number(produktivitas, decimals=2)}%",
                "delta": "Target: -%",
                "formula": """\
**Produktivitas PR-PO**: Persentase total item PO dibanding total item PR.

**Formula:**
```
= Total PO / Total PR × 100%
```

| % | Interpretasi |
|---|---|
| ≥ 90% | 🟢 Sangat baik |
| 70–89% | 🟡 Perlu perhatian |
| < 70% | 🔴 Banyak PR pending |

**Target:** -\
""",
            },
            {
                "key": "kpi_savings",
                "icon_path": "M8 3.293 4 7.293V13a1 1 0 0 0 1 1h2v-3h2v3h2a1 1 0 0 0 1-1V7.293zM13.207 6 8 .793 2.793 6H1l7-7 7 7z",
                "label": "Total Savings",
                "value": format_idr(savings),
                "delta": f"{format_number(savings_pct, decimals=1)}% avg",
                "formula": f"""\
**Total Savings**: Selisih OE dengan realisasi PO.

**Formula Excel:** (PO SAP)
- Filter **Material No** selain `1000076`
- Filter **PO Deletion Flag** selain `L`
- Buat Kolom **OE**: `= Quantity PR × Estimasi PR`
- Hitung selisih dari jumlah **OE** dan jumlah **Total Amount in Local Curr**

| Kondisi | Artinya |
|---|---|
| Positif | Realisasi < OE → penghematan ✅ |
| Negatif | Realisasi > OE → over budget ❌ |

**Total Savings saat ini:** Rp {int(savings):,}

**Target:** -\
""",
            },
            {
                "key": "kpi_estimasi",
                "icon_path": "M4 10.781c.148 1.667 1.513 2.85 3.591 3.003V15h1.043v-1.216c2.27-.179 3.678-1.438 3.678-3.3 0-1.59-.947-2.51-2.956-3.028l-.722-.187V3.467c1.122.11 1.879.714 2.07 1.616h1.47c-.166-1.6-1.54-2.748-3.54-2.875V1H7.591v1.233c-1.939.23-3.27 1.472-3.27 3.156 0 1.454.966 2.483 2.661 2.917l.61.162v4.031c-1.149-.17-1.94-.8-2.131-1.718zm3.391-3.836c-1.043-.263-1.6-.825-1.6-1.616 0-.944.704-1.641 1.8-1.828v3.495l-.2-.05zm1.591 1.872c1.287.323 1.852.859 1.852 1.769 0 1.097-.826 1.828-2.2 1.939V8.73z",
                "label": "Total Estimasi PR",
                "value": format_idr(oe_po_val),
                "delta": "Owner's Estimate (OE)",
                "formula": f"""\
**Total Estimasi PR (OE)**: Total nilai OE dari semua PR.

**Total Estimasi PR saat ini:** {int(oe_po_val):,}

**Formula Excel:** (PO SAP)
- Filter **Material No** selain `1000076`
- Filter **PO Deletion Flag** selain `L`
- Buat kolom **OE**: `= Quantity PR × Estimasi PR`
- Hitung jumlah **OE**

**Target:** -\
""",
            },
            {
                "key": "kpi_anggaran",
                "icon_path": "M1 2.828c.885-.37 2.154-.769 3.388-.893 1.33-.134 2.458.063 3.112.752v9.746c-.935-.53-2.12-.603-3.213-.493-1.18.12-2.37.461-3.287.811zm7.5-.141c.654-.689 1.782-.886 3.112-.752 1.234.124 2.503.523 3.388.893v9.923c-.918-.35-2.107-.692-3.287-.81-1.094-.111-2.278-.039-3.213.492zM8 1.783C7.015.936 5.587.81 4.287.94c-1.514.153-3.042.672-3.994 1.105A.5.5 0 0 0 0 2.5v11a.5.5 0 0 0 .707.455c.882-.4 2.303-.881 3.68-1.02 1.409-.142 2.59.087 3.223.877a.5.5 0 0 0 .78 0c.633-.79 1.814-1.019 3.222-.877 1.378.139 2.8.62 3.681 1.02A.5.5 0 0 0 16 13.5v-11a.5.5 0 0 0-.293-.455c-.952-.433-2.48-.952-3.994-1.105C10.413.809 8.985.936 8 1.783",
                "label": "Pengelolaan Anggaran Operasional",
                "value": "-",
                "delta": "Target: ≤ 100%",
                "formula": """\
**Pengelolaan Anggaran Operasional**: Persentase realisasi anggaran operasional terhadap anggaran yang ditetapkan.

**Status:** Data anggaran/budget tidak tersedia di `vw_pr_po_complete`. Membutuhkan tabel anggaran terpisah.

**Formula Excel (jika data tersedia):**
```
= Realisasi_Anggaran / Total_Anggaran × 100%
```

**Target:** -\
""",
            },
            {
                "key": "kpi_sinergi",
                "icon_path": "M7 14s-1 0-1-1 1-4 5-4 5 3 5 4-1 1-1 1zm4-6a3 3 0 1 0 0-6 3 3 0 0 0 0 6m-5.784 6A2.24 2.24 0 0 1 5 13c0-1.355.68-2.75 1.936-3.72A6.3 6.3 0 0 0 5 9c-4 0-5 3-5 4s1 1 1 1zM4.5 8a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5",
                "label": "Sinergi PI Group",
                "value": format_idr(sinergi_pi_val),
                "delta": "Target: -",
                "formula": """\
**Sinergi PI Group**: Jumlah nilai realisasi PO (Total Amount in Local Curr) yang ditransaksikan dengan entitas PI Group lainnya.

**Formula Excel:** (PO SAP)
- Filter **Material No** selain `1000076`
- Filter **PO Deletion Flag** selain `L`
- Filter **Vendor Code** hanya `4000000011` dan `4000000012`
- Jumlahkan **Total Amount in Local Curr**

**Target:** -\
""",
            },
            {
                "key": "kpi_kecepatan_po",
                "icon_path": "M8 3.5a.5.5 0 0 0-1 0V9a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0 0 .496-.868L8 8.71V3.5z M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0z",
                "label": "Kecepatan Proses PO",
                "value": f"{format_number(avg_lt_val, decimals=2)} Hari",
                "delta": "Target: ≤ 55 Hari",
                "formula": """\
**Kecepatan Proses PO**: Rata-rata hari dari `1St Full Release` PR hingga PO diterbitkan (`Date Ordered`).
 
**Formula Excel:** (PO SAP)
- Filter **Material No** selain `1000076`
- Filter **PO Deletion Flag** selain `L`
- Hitung rata-rata dari **Date Ordered** dikurangi dengan **1St Full Release**

| Benchmark | Status |
|---|---|
| ≤ 30 hari | 🟢 Sangat cepat |
| 31–55 hari | 🟡 Dalam SLA |
| > 55 hari | 🔴 Melebihi SLA |

**Target:** -\
""",
            },
            {
                "key": "kpi_pengiriman",
                "icon_path": "M0 3.5A1.5 1.5 0 0 1 1.5 2h9A1.5 1.5 0 0 1 12 3.5V5h1.02a1.5 1.5 0 0 1 1.17.563l1.481 1.85a1.5 1.5 0 0 1 .329.938V10.5a1.5 1.5 0 0 1-1.5 1.5H14a2 2 0 1 1-4 0H5a2 2 0 1 1-3.998-.085A1.5 1.5 0 0 1 0 10.5zm1.294 7.456A2 2 0 0 1 4.732 11h5.536a2 2 0 0 1 .732-.732V3.5a.5.5 0 0 0-.5-.5h-9a.5.5 0 0 0-.5.5v7a.5.5 0 0 0 .294.456M12 10a2 2 0 0 1 1.732 1h.768a.5.5 0 0 0 .5-.5V8.35a.5.5 0 0 0-.11-.312l-1.48-1.85A.5.5 0 0 0 13.02 6H12zm-9 1a1 1 0 1 0 0 2 1 1 0 0 0 0-2m9 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2",
                "label": "% Pengiriman Barang",
                "value": f"{format_number(pct_pengiriman, decimals=1)}%",
                "delta": "Target: > 80%",
                "formula": """\
**% Pengiriman Barang (GR/PO)**: Persentase item PO yang sudah diterima barangnya.

**Formula Excel:** (PO SAP)
- Filter **Material No** selain `1000076`
- Filter **PO Deletion Flag** selain `L`
- Jumlahkan **Delivery Completed** yang isinya `X`
- Lalu dibagi dengan **Total PO**

*Catatan: Setiap Item PO dihitung tersendiri (1 Nomor PO bisa memiliki banyak Item PO).*

**Target:** -\
""",
            },
            {
                "key": "kpi_ketepatan",
                "icon_path": "M10.97 4.97a.75.75 0 0 1 1.07 1.05l-3.99 4.99a.75.75 0 0 1-1.08.02L4.324 8.384a.75.75 0 1 1 1.06-1.06l2.094 2.093 3.473-4.425z M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0z",
                "label": "Ketepatan Pengiriman Barang",
                "value": f"{format_number(ketepatan_pct, decimals=1)}%",
                "delta": "Target: > 90%",
                "formula": """\
**Ketepatan Pengiriman Barang**: Persentase item PO diterima tepat waktu dari total item yang sudah dikirim.

**Formula Excel:** (PO SAP)
- Filter **Material No** selain `1000076`
- Filter **PO Deletion Flag** selain `L`
- Jumlahkan **Delivery Completed** yang isinya `X`
- Filter hanya yang **Tgl Terima Barang** sebelum **Del Date PO**
- Lalu dibagi dengan total data tanpa filter **Tgl Terima Barang** sebelum **Del Date PO**

*Catatan: Setiap Item PO dihitung tersendiri (1 Nomor PO bisa memiliki banyak Item PO).*

**Target:** -\
""",
            },
            {
                "key": "kpi_otobos",
                "icon_path": "M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001q.044.06.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1 1 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0",
                "label": "Pemenuhan SLA OTOBOS",
                "value": "99,33%",
                "delta": "Target: > 90%",
                "formula": """\
**Pemenuhan SLA OTOBOS**: Tingkat pemenuhan SLA sistem OTOBOS.

**Status:** OTOBOS adalah sistem terpisah, tidak terhubung ke database PR-PO ini.

**Formula Excel (jika data tersedia):**
```
= COUNT(request selesai dalam SLA) / COUNT(total request) × 100%
```

**Target:** -\
""",
            },
            {
                "key": "kpi_efisiensi_pengadaan",
                "icon_path": "M11.534 7h3.932a.25.25 0 0 1 .192.41l-1.966 2.36a.25.25 0 0 1-.384 0l-1.966-2.36a.25.25 0 0 1 .192-.41m-11 2h3.932a.25.25 0 0 0 .192-.41L2.692 6.23a.25.25 0 0 0-.384 0L.342 8.59A.25.25 0 0 0 .534 9 M8 3c-1.552 0-2.94.707-3.857 1.818a.5.5 0 1 1-.771-.636A6.002 6.002 0 0 1 13.917 7H12.9A5 5 0 0 0 8 3M3.1 9a5.002 5.002 0 0 0 8.757 2.182.5.5 0 1 1 .771.636A6.002 6.002 0 0 1 2.083 9z",
                "label": "Efisiensi Pengadaan",
                "value": f"{format_number(savings_pct, decimals=2)}%",
                "delta": "Target: > 2%",
                "formula": """\
**Efisiensi Pengadaan (PO/OE)**: Rata-rata persentase penghematan dari nilai OE per item PO.

**Formula Excel:** (PO SAP)
- Filter **Material No** selain `1000076`
- Filter **PO Deletion Flag** selain `L`
- Buat kolom **Efisiensi**: =`(Estimasi PR × Quantity PR) - Total Amount in Local Curr`
- Bagi jumlah **Efisiensi** dengan jumlah **Total Amount in Local Curr**

Nilai ini setara dengan **Total Savings %**. Detail per material: halaman Evaluasi Harga Barang.

**Target:** -\
""",
            },
            {
                "key": "kpi_izin_impor",
                "icon_path": "M8 1a2 2 0 0 1 2 2v4H6V3a2 2 0 0 1 2-2m3 6V3a3 3 0 0 0-6 0v4a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2",
                "label": "Pemenuhan Izin Impor",
                "value": "100%",
                "delta": "Target: 2 / 2",
                "formula": """\
**Pemenuhan Izin Impor**: Persentase PO impor yang memiliki izin impor lengkap dan valid.

**Status:** Tidak ada kolom izin impor di `vw_pr_po_complete`. Membutuhkan tabel dokumen kepabeanan.

**Formula Excel (jika data tersedia):**
```
= COUNT(PO impor dengan izin lengkap) / COUNT(total PO impor) × 100%
```

**Target:** -\
""",
            },
            {
                "key": "kpi_pembebasan",
                "icon_path": "M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16 M10.97 4.97a.75.75 0 0 1 1.07 1.05l-3.99 4.99a.75.75 0 0 1-1.08.02L4.324 8.384a.75.75 0 1 1 1.06-1.06l2.094 2.093 3.473-4.425z",
                "label": "Pemenuhan SLA Pembebasan Barang",
                "value": "85,71%",
                "delta": "Target: 80%",
                "formula": """\
**Pemenuhan SLA Pembebasan Barang**: Persentase pengajuan pembebasan barang selesai dalam SLA.

**Status:** Tidak ada kolom pembebasan barang di `vw_pr_po_complete`. Membutuhkan tabel proses bea cukai.

**Formula Excel (jika data tersedia):**
```
= COUNT(selesai dalam SLA) / COUNT(total pengajuan) × 100%
```

**Target:** -\
""",
            },
        ]

        # ── Session state ──────────────────────────────────────────────────────
        for kpi in KPI_DASH:
            if kpi["key"] not in st.session_state:
                st.session_state[kpi["key"]] = False

        # ── CSS card ───────────────────────────────────────────────────────────
        st.markdown("""
        <style>
        .kpi-card {
            display: flex;
            align-items: center;
            background: var(--secondary-background-color);
            border-radius: 10px;
            padding: 16px 14px;
            gap: 12px; /* Dipersempit agar lebih rapat */
            height: 100%;
        }
        .kpi-icon {
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            opacity: 1; /* Icon sekarang full color */
        }
        .kpi-body {
            flex: 1;
            min-width: 0;
        }
        .kpi-label {
            font-size: 13px;
            opacity: 0.9;
            margin: 0 0 2px 0;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .kpi-value {
            font-size: 2rem !important;
            font-weight: 600 !important;
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1.1 !important;
            display: block !important;
        }
        .kpi-delta {
            font-size: 12px;
            color: #09ab3b;
            margin: 0;
        }
        .kpi-delta-neutral {
            font-size: 12px;
            opacity: 0.55;
            margin: 0;
        }
        /* Menghilangkan padding default streamlit pada kolom tombol agar bisa lebih mepet */
        [data-testid="column"]:nth-child(2) {
            display: flex;
            align-items: center;
            justify-content: flex-start;
        }
        </style>
        """, unsafe_allow_html=True)

        # ── Helper: render satu baris (max 3 KPI) ─────────────────────────────
        def render_kpi_row(items):
            n = len(items)
            cols = st.columns(3)
            for i, col in enumerate(cols):
                with col:
                    if i >= n:
                        continue
                    kpi = items[i]
                    is_open = st.session_state[kpi["key"]]
                    
                    # Logika panah: sembunyikan panah '↑' jika teks berupa Target atau value kosong
                    no_arrow = kpi["value"] == "-" or kpi["delta"].startswith("Target:")
                    delta_arrow = "" if no_arrow else "↑ "
                    
                    # --- KUNCI PERBAIKAN: Paksa semua tulisan bawah menggunakan class hijau ---
                    delta_cls = "kpi-delta" 

                    card_html = f"""
                    <div class="kpi-card">
                        <div class="kpi-icon">
                            <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"
                                 fill="currentColor" viewBox="0 0 16 16">
                                <path d="{kpi['icon_path']}"/>
                            </svg>
                        </div>
                        <div class="kpi-body">
                            <p class="kpi-label">{kpi['label']}</p>
                            <p class="kpi-value">{kpi['value']}</p>
                            <p class="{delta_cls}">{delta_arrow}{kpi['delta']}</p>
                        </div>
                    </div>"""

                    # Menggunakan perbandingan 10:2 agar tombol "Mata" lebih masuk ke kiri
                    c_card, c_btn = st.columns([10, 2])
                    with c_card:
                        st.markdown(card_html, unsafe_allow_html=True)
                    with c_btn:
                        # Mengurangi margin top agar icon mata sejajar dengan tengah kartu
                        st.markdown("<div style='height:25px'></div>", unsafe_allow_html=True)
                        tooltip = "Hide Formula" if is_open else "Show Formula"
                        btn_icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                        st.button(btn_icon, key=f"btn_{kpi['key']}", help=tooltip,
                                  on_click=toggle_state, kwargs={"state_key": kpi["key"]})

        # ── Render 5 baris × 3 kolom ──────────────────────────────────────────
        for row in range(0, len(KPI_DASH), 3):
            # 1. Ambil 3 item untuk baris saat ini
            current_row_items = KPI_DASH[row:row + 3]
            
            # 2. Render ketiga kartu tersebut
            render_kpi_row(current_row_items)
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            
            # 3. Cek apakah ada tombol dari baris INI yang sedang aktif
            # Jika aktif, tampilkan infonya tepat di bawah baris ini
            for kpi in current_row_items:
                if st.session_state[kpi["key"]]:
                    st.info(kpi["formula"])

        st.markdown("---")

        # ── CHARTS ROW 1 ─────────────────────────────────
        col1, col2 = st.columns(2)

        with col1:
            title_col, btn_col = st.columns([9, 1])
            with title_col:
                st.markdown("""
                    <h1 style='display: flex; align-items: center; font-size:30px;'>
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 6px; margin-right: 8px;">
                            <path d="M1 11a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1zm5-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1zm5-5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1z"/>
                        </svg>
                        PR Status by Department
                    </h1>
                """, unsafe_allow_html=True)
            with btn_col:
                st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
                key1 = "show_formula_pr_status_dept"
                if key1 not in st.session_state:
                    st.session_state[key1] = False
                is_open = st.session_state[key1]
                icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                tooltip = "Hide Formula" if is_open else "Show Formula"
                st.button(icon, key=f"btn_{key1}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key1})

            if st.session_state.get(key1, False):
                st.info("""
**PR Status by Department**: Stacked bar chart jumlah PR per departemen, dibedakan antara PR yang sudah memiliki PO dan yang belum.

**Formula Excel:** (PR SAP)
- Filter **1St Full Release** selain `blanks`
- Filter **Material No** selain `1000076`
- Filter **PR Deletion Flag** selain `X`
- Filter **Account Assignment** selain `U`
- Filter **Departement(Requisitioner)** sesuai yang diinginkan

**Kalkulasi:**
| Metrik | Keterangan |
|---|---|
| Total PR | Semua PR unik di periode filter |
| PR with PO | PR yang sudah ada PO-nya |
| PR without PO | PR yang belum diproses |

⚠️ **Catatan:** Jika suatu **Nomor PR** sudah memiliki **Nomor PO** di excel **PR SAP**, namun di **Nomor PO** tersebut belum terbit di excel **PO SAP**, maka **Nomor PR** tersebut akan masuk kategori `pr wihtout po`.

                """)

            st.caption("Jumlah PR per departemen, dibedakan antara PR yang sudah memiliki PO dan yang belum.")

            dept_query = f"""
            SELECT
                COALESCE(department_code, 'Unknown') AS department,
                -- Ubah dari COUNT(DISTINCT no_pr) menjadi per-item:
                COUNT(DISTINCT no_pr || '-' || line_item_pr::text) AS total_pr,
                -- Ubah juga penghitungan With PO-nya:
                COUNT(DISTINCT CASE WHEN nomor_po IS NOT NULL THEN no_pr || '-' || line_item_pr::text END) AS pr_with_po
            FROM vw_pr_po_complete
            WHERE {filter_conditions} AND {bagian_pr_cond} AND no_pr != 'No PR'
              AND first_full_release IS NOT NULL
            GROUP BY department_code
            ORDER BY total_pr DESC
            LIMIT 10
            """
            with st.spinner("Memuat chart department..."):
                dept_data = load_data(dept_query)

            if not dept_data.empty:
                pr_without_po_series = dept_data['total_pr'] - dept_data['pr_with_po']
                fig = go.Figure(data=[
                    go.Bar(name='PR with PO', x=dept_data['department'], y=dept_data['pr_with_po'], marker_color='#1f77b4'),
                    
                    go.Bar(name='PR without PO', x=dept_data['department'], y=pr_without_po_series, marker_color='#ff7f0e')
                ])
                fig.update_layout(barmode='group', height=400, separators=",.")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Tidak ada data yang tersedia.")

        with col2:
            title_col, btn_col = st.columns([9, 1])
            with title_col:
                st.markdown("""
                    <h1 style='display: flex; align-items: center; font-size:30px;'>
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-cash-stack" viewBox="0 0 16 16" style="margin-bottom: 6px; margin-right: 8px;">
                            <path d="M1 3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1zm7 8a2 2 0 1 0 0-4 2 2 0 0 0 0 4"/>
                            <path d="M0 5a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H1a1 1 0 0 1-1-1zm3 0a2 2 0 0 1-2 2v4a2 2 0 0 1 2 2h10a2 2 0 0 1 2-2V7a2 2 0 0 1-2-2z"/>
                        </svg>
                        Top 10 Vendors by PO Value
                    </h1>
                """, unsafe_allow_html=True)
            with btn_col:
                st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
                key2 = "show_formula_top_10_vendors_by_po_value"
                if key2 not in st.session_state:
                    st.session_state[key2] = False
                is_open = st.session_state[key2]
                icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                tooltip = "Hide Formula" if is_open else "Show Formula"
                st.button(icon, key=f"btn_{key2}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key2})

            if st.session_state.get(key2, False):
                st.info("""\
**Top 10 Vendors by PO Value**: Bar chart horizontal 10 vendor dengan total nilai PO terbesar.

**Formula Excel:** (PO SAP)
- Filter **Material No** selain `1000076`
- Filter **PO Deletion Flag** selain `L`
- Filter **Vendor Name** sesuai yang diinginkan
- Jumlahkan **Total Amount in Local Curr**
                """)

            st.caption("Top 10 vendor dengan total nilai PO terbesar.")

            # ── Filter lokal vendor ───────────────────────────────────────────
            vendor_filter_key = "vendor_chart_filter"
            if vendor_filter_key not in st.session_state:
                st.session_state[vendor_filter_key] = "ALL"

            vendor_filter_opts = ["ALL", "B01", "Investasi", "Lainnya"]
            selected_vendor_filter = st.pills(
                "Filter Vendor",
                options=vendor_filter_opts,
                key=vendor_filter_key,
                label_visibility="collapsed"
            )
            if not selected_vendor_filter:
                selected_vendor_filter = "ALL"

            # Bangun kondisi tambahan berdasarkan filter lokal
            if selected_vendor_filter == "B01":
                vendor_extra_cond = "AND poh.purchasing_group = 'B01'"
            elif selected_vendor_filter == "Investasi":
                vendor_extra_cond = "AND poi.department_code LIKE 'INV%' AND poi.department_code != 'INV'"
            elif selected_vendor_filter == "Lainnya":
                vendor_extra_cond = (
                    "AND poh.purchasing_group != 'B01' "
                    "AND NOT (poi.department_code LIKE 'INV%' AND poi.department_code != 'INV')"
                )
            else:  # ALL
                vendor_extra_cond = ""

            # Bangun filter_conditions untuk PO (ganti kolom ke alias tabel yang benar)
            vendor_filter_cond = (
                filter_conditions
                .replace('department_code', 'poi.department_code')
                .replace('plant_code', 'poi.plant_code')
                .replace('tgl_create_pr', 'poh.date_ordered')
                .replace('first_full_release', 'poh.date_ordered')
            )

            vendor_query = f"""
            SELECT
                COALESCE(v.vendor_name, 'Unknown') AS vendor,
                COUNT(DISTINCT poi.nomor_po)           AS total_po,
                SUM(poi.total_amount_local_curr)       AS total_value
            FROM po_items poi
            JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
            LEFT JOIN vendors v ON poh.vendor_code = v.vendor_code
            WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
              AND {bagian_po_poi}
              AND {vendor_filter_cond}
              {vendor_extra_cond}
            GROUP BY v.vendor_name
            ORDER BY total_value DESC
            LIMIT 10
            """
            with st.spinner("Memuat chart vendor..."):
                vendor_data = load_data(vendor_query)

            if not vendor_data.empty:
                vendor_data['label_text'] = vendor_data['total_value'].apply(format_idr_short)
                fig = px.bar(
                    vendor_data, x='total_value', y='vendor', orientation='h',
                    labels={'total_value': 'Total Value (IDR)', 'vendor': 'Vendor'},
                    text='label_text'
                )
                max_vendor_val = vendor_data['total_value'].max()
                fig.update_layout(
                    height=400,
                    yaxis={'categoryorder': 'total ascending'},
                    xaxis=idr_axis(max_vendor_val),
                    separators=",."
                )
                fig.update_traces(
                    textfont_size=11, textposition="outside", cliponaxis=False,
                    hovertemplate="<b>%{y}</b><br>Total: Rp %{text}<extra></extra>"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Tidak ada data yang tersedia.")

        # ── CHARTS ROW 2 ─────────────────────────────────
        col1, col2 = st.columns(2)

        with col1:
            title_col, btn_col = st.columns([9, 1])
            with title_col:
                st.markdown("""
                    <h1 style='display: flex; align-items: center; font-size:30px;'>
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 6px; margin-right: 8px;">
                            <path d="M11 6.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5z"/>
                            <path d="M3.5 0a.5.5 0 0 1 .5.5V1h8V.5a.5.5 0 0 1 1 0V1h1a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2h1V.5a.5.5 0 0 1 .5-.5M1 4v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V4z"/>
                        </svg>
                        PR-PO Creation Trend
                    </h1>
                """, unsafe_allow_html=True)
            with btn_col:
                st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
                key3 = "show_formula_pr_po_trend"
                if key3 not in st.session_state:
                    st.session_state[key3] = False
                is_open = st.session_state[key3]
                icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                tooltip = "Hide Formula" if is_open else "Show Formula"
                st.button(icon, key=f"btn_{key3}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key3})

            if st.session_state.get(key3, False):
                st.info("""\
**PR-PO Creation Trend**: Line chart jumlah PR dan PO yang dibuat per bulan.

**Formula Excel** mengikuti KPI **Total PR** dan **Total PO** di atas.
                """)

            st.caption("Jumlah PR dan PO yang dibuat per bulan.")
        
            trend_query = f"""
            WITH pr_monthly AS (
                SELECT
                    DATE_TRUNC('month', first_full_release) AS month_date,
                    COUNT(DISTINCT CASE WHEN no_pr != 'No PR' AND {bagian_pr_cond}
                        THEN no_pr || '-' || line_item_pr::text END) AS total_pr
                FROM vw_pr_po_complete
                WHERE first_full_release IS NOT NULL AND {filter_conditions}
                GROUP BY 1
            ),
            po_monthly AS (
                SELECT
                    DATE_TRUNC('month', poh.date_ordered) AS month_date,
                    COUNT(poi.nomor_po) AS total_po
                FROM po_items poi
                JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
                WHERE poh.date_ordered IS NOT NULL
                  AND poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
                  AND {bagian_po_poi}
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
        
            with st.spinner("Memuat trend..."):
                trend_data = load_data(trend_query)

            if not trend_data.empty:
                trend_data['month'] = pd.to_datetime(trend_data['month'])
                trend_data = trend_data.sort_values('month')
                
                # Konversi tanggal: bulan lewat → akhir bulan, bulan ini → hari ini
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
 
                trend_data['month_display'] = trend_data['month'].apply(resolve_month_date)
 
                # Format label hover & tick: cross-platform (tidak pakai %-d)
                def fmt_date(ts):
                    return f"{ts.day} {ts.strftime('%b')} {ts.year}"
 
                trend_data['hover_label'] = trend_data['month_display'].apply(fmt_date)
 
                show_cumulative = st.toggle("Tampilkan secara Kumulatif (Running Total)", value=False)
            
                if show_cumulative:
                    y_pr = trend_data['total_pr'].cumsum()
                    y_po = trend_data['total_po'].cumsum()
                    y_axis_title = 'Cumulative Count'
                else:
                    y_pr = trend_data['total_pr']
                    y_po = trend_data['total_po']
                    y_axis_title = 'Count per Month'
 
                # Paksa tickvals & ticktext agar sumbu X hanya tampilkan titik data
                tick_vals = trend_data['month_display'].tolist()
                tick_text = trend_data['hover_label'].tolist()
 
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=trend_data['month_display'], y=y_pr,
                    mode='lines+markers', name='PR Created',
                    line=dict(color='#1f77b4', width=2),
                    customdata=trend_data[['hover_label']],
                    hovertemplate='<b>%{customdata[0]}</b><br>PR Created: %{y}<extra></extra>'
                ))
                fig.add_trace(go.Scatter(
                    x=trend_data['month_display'], y=y_po,
                    mode='lines+markers', name='PO Created',
                    line=dict(color='#2ca02c', width=2),
                    customdata=trend_data[['hover_label']],
                    hovertemplate='<b>%{customdata[0]}</b><br>PO Created: %{y}<extra></extra>'
                ))
            
                fig.update_layout(
                    height=400,
                    xaxis_title='Month',
                    yaxis_title=y_axis_title,
                    xaxis=dict(
                        tickmode='array',
                        tickvals=tick_vals,
                        ticktext=tick_text,
                        tickangle=-30
                    )
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Tidak ada data yang tersedia.")

        with col2:
            title_col, btn_col = st.columns([9, 1])
            with title_col:
                st.markdown("""
                    <h1 style='display: flex; align-items: center; font-size:30px;'>
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 6px; margin-right: 8px;">
                            <path d="M6 .5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1H9v1.07a7.001 7.001 0 0 1 3.274 12.474l.601.602a.5.5 0 0 1-.707.708l-.746-.746A6.97 6.97 0 0 1 8 16a6.97 6.97 0 0 1-3.422-.892l-.746.746a.5.5 0 0 1-.707-.708l.602-.602A7.001 7.001 0 0 1 7 2.07V1h-.5A.5.5 0 0 1 6 .5m2.5 5a.5.5 0 0 0-1 0v3.362l-1.429 2.38a.5.5 0 1 0 .858.515l1.5-2.5A.5.5 0 0 0 8.5 9zM.86 5.387A2.5 2.5 0 1 1 4.387 1.86 8.04 8.04 0 0 0 .86 5.387M11.613 1.86a2.5 2.5 0 1 1 3.527 3.527 8.04 8.04 0 0 0-3.527-3.527"/>
                        </svg>
                        Lead Time Distribution
                    </h1>
                """, unsafe_allow_html=True)
            with btn_col:
                st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
                key4 = "show_formula_lead_time"
                if key4 not in st.session_state:
                    st.session_state[key4] = False
                is_open = st.session_state[key4]
                icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                tooltip = "Hide Formula" if is_open else "Show Formula"
                st.button(icon, key=f"btn_{key4}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key4})

            if st.session_state.get(key4, False):
                st.info("""\
**Lead Time Distribution**: Pie chart distribusi PO berdasarkan rentang waktu proses (dari `1St Full Release` PR hingga `Date Ordered` PO terbit).
 
**Formula Excel:** (PO SAP)
- Filter **Material No** selain `1000076`
- Filter **PO Deletion Flag** selain `L`
- Buat kolom **PR-PO**: `=Date Ordered - 1St Full Release**
- Filter sesuai range yang diinginkan
                """)
 
            st.caption("Distribusi PO berdasarkan rentang waktu proses (dari PR dibuat **1St Full Release** sampai PO terbit **Date Ordered**).")
                
            leadtime_query = f"""
            SELECT
                CASE
                    WHEN (poh.date_ordered::date - poi.first_full_release::date) <= 7  THEN '0-7 days'
                    WHEN (poh.date_ordered::date - poi.first_full_release::date) <= 14 THEN '8-14 days'
                    WHEN (poh.date_ordered::date - poi.first_full_release::date) <= 30 THEN '15-30 days'
                    WHEN (poh.date_ordered::date - poi.first_full_release::date) <= 60 THEN '31-60 days'
                    ELSE '60+ days'
                END AS lead_time_range,
                COUNT(*) AS count,
                MIN(poh.date_ordered::date - poi.first_full_release::date) AS sort_order
            FROM po_items poi
            JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
            WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
              AND poi.first_full_release IS NOT NULL
              AND (poh.date_ordered::date - poi.first_full_release::date) >= 0
              AND poi.no_pr IS NOT NULL
              AND {bagian_po_cond.replace('bagian_po', 'poi.bagian_po')}
            GROUP BY 1
            ORDER BY sort_order ASC
            """
            with st.spinner("Memuat lead time..."):
                leadtime_data = load_data(leadtime_query)

            if not leadtime_data.empty:
                category_order = ['0-7 days', '8-14 days', '15-30 days', '31-60 days', '60+ days']
                leadtime_data['lead_time_range'] = pd.Categorical(
                    leadtime_data['lead_time_range'], categories=category_order, ordered=True
                )
                leadtime_data = leadtime_data.sort_values('lead_time_range')
                fig = px.pie(leadtime_data, values='count', names='lead_time_range', hole=0.4,
                            category_orders={'lead_time_range': category_order})
                fig.update_traces(sort=False)
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Tidak ada data yang tersedia.")

        # ── ADDITIONAL INSIGHTS ──────────────────────────
        st.markdown("---")
        st.markdown("""
            <h1 style='display: flex; align-items: center;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor" class="bi bi-graph-up" viewBox="0 0 16 16" style="margin-bottom: 8px; margin-right: 8px;">
                    <path d="M2 6a6 6 0 1 1 10.174 4.31c-.203.196-.359.4-.453.619l-.762 1.769A.5.5 0 0 1 10.5 13h-5a.5.5 0 0 1-.46-.302l-.761-1.77a2 2 0 0 0-.453-.618A5.98 5.98 0 0 1 2 6m3 8.5a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1l-.224.447a1 1 0 0 1-.894.553H6.618a1 1 0 0 1-.894-.553L5.5 15a.5.5 0 0 1-.5-.5"/>
                </svg>
                Additional Insights
            </h1>
        """, unsafe_allow_html=True)

        title_col, btn_col = st.columns([19, 1])
        with title_col:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:30px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 6px; margin-right: 8px;">
                        <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5m.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2"/>
                    </svg>
                    Top 10 PR Without PO (Pending)
                </h1>
            """, unsafe_allow_html=True)
        with btn_col:
            st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
            key5 = "show_formula_top_10_pending"
            if key5 not in st.session_state:
                st.session_state[key5] = False
            is_open = st.session_state[key5]
            icon = ":material/visibility_off:" if is_open else ":material/visibility:"
            tooltip = "Hide Formula" if is_open else "Show Formula"
            st.button(icon, key=f"btn_{key5}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key5})

        if st.session_state.get(key5, False):
            st.info("""\
**Top 10 PR Without PO (Pending)**: Tabel 10 PR tertua yang belum diproses menjadi PO.

**Formula Excel:** (PR SAP)
- Filter **Material No** selain `1000076`
- Filter **PR Deletion Flag** selain `X`
- Filter **Account Assignment** selain `U`
- Filter **Nomor PO** yang kosong
- Urutkan **Tgl Create PR** dari yang paling lama ke paling baru
            """)

        st.caption("Tabel 10 PR tertua yang belum diproses menjadi PO.")

        pr_without_po_query = f"""
        SELECT
            no_pr,
            line_item_pr,
            tgl_create_pr,
            department_code AS department,
            bagian_pr AS bagian,
            COALESCE(oe, 0) AS total_estimasi
        FROM vw_pr_po_complete
        WHERE {filter_conditions} AND nomor_po IS NULL
        AND no_pr != 'No PR' AND {bagian_pr_cond}
        ORDER BY tgl_create_pr ASC, no_pr ASC, line_item_pr ASC
        LIMIT 10
        """
        with st.spinner("Memuat PR pending..."):
            pr_without_po = load_data(pr_without_po_query)

        if not pr_without_po.empty:
            pr_without_po['tgl_create_pr'] = pd.to_datetime(pr_without_po['tgl_create_pr']).dt.strftime('%Y-%m-%d')
            pr_without_po['total_estimasi'] = pr_without_po['total_estimasi'].apply(
                lambda x: format_currency(x) if pd.notna(x) else ""
            )
            st.dataframe(
                pr_without_po.rename(columns={
                    'no_pr':          'No PR',
                    'line_item_pr':   'Item',
                    'tgl_create_pr':  'Tgl Dibuat',
                    'department':     'Department',
                    'bagian':         'Bagian',
                    'total_estimasi': 'Estimasi (Rp)',
                }),
                use_container_width=True, height=300
            )
        else:
            st.success("Kerja bagus! Semua PR telah diproses menjadi PO.")

        st.markdown("<br>", unsafe_allow_html=True)

        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            title_col, btn_col = st.columns([9, 1])
            with title_col:
                st.markdown("""
                    <h1 style='display: flex; align-items: center; font-size:30px;'>
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 6px; margin-right: 8px;">
                            <path d="M0 3.5A1.5 1.5 0 0 1 1.5 2h9A1.5 1.5 0 0 1 12 3.5V5h1.02a1.5 1.5 0 0 1 1.17.563l1.481 1.85a1.5 1.5 0 0 1 .329.938V10.5a1.5 1.5 0 0 1-1.5 1.5H14a2 2 0 1 1-4 0H5a2 2 0 1 1-3.998-.085A1.5 1.5 0 0 1 0 10.5zm1.294 7.456A2 2 0 0 1 4.732 11h5.536a2 2 0 0 1 .732-.732V3.5a.5.5 0 0 0-.5-.5h-9a.5.5 0 0 0-.5.5v7a.5.5 0 0 0 .294.456M12 10a2 2 0 0 1 1.732 1h.768a.5.5 0 0 0 .5-.5V8.35a.5.5 0 0 0-.11-.312l-1.48-1.85A.5.5 0 0 0 13.02 6H12zm-9 1a1 1 0 1 0 0 2 1 1 0 0 0 0-2m9 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2"/>
                        </svg>
                        Delivery Performance
                    </h1>
                """, unsafe_allow_html=True)
            with btn_col:
                st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
                key6 = "show_formula_delivery_perf"
                if key6 not in st.session_state:
                    st.session_state[key6] = False
                is_open = st.session_state[key6]
                icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                tooltip = "Hide Formula" if is_open else "Show Formula"
                st.button(icon, key=f"btn_{key6}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key6})

            if st.session_state.get(key6, False):
                st.info("""\
**Delivery Performance**: Pie chart status pengiriman PO (tepat waktu vs terlambat vs pending).

| Status | Kondisi |
|---|---|
| TEPAT WAKTU | Barang tiba `Tgl Terima Barang` ≤ `Delivery Completed` |
| TERLAMBAT | Barang tiba `Tgl Terima Barang` > `Delivery Completed` |
| IN PROGRESS | PO sudah terbit, namun belum Delivery Completed |
| PENDING | Belum ada informasi delivery sama sekali |

**Formula Excel TEPAT WAKTU:** (PO SAP)
- Filter **Material No** selain `1000076`
- Filter **PO Deletion Flag** selain `L`
- Jumlahkan **Delivery Completed** yang isinya `X`
- Filter hanya yang **Tgl Terima Barang** sebelum **Del Date PO**
                        
**Formula Excel IN PROGRESS:** (PO SAP)
- Filter **Material No** selain `1000076`
- Filter **PO Deletion Flag** selain `L`
- Jumlahkan **Delivery Completed** yang isinya selain `X`
                        
**Formula Excel TERLAMBAT:** (PO SAP)
- Filter **Material No** selain `1000076`
- Filter **PO Deletion Flag** selain `L`
- Jumlahkan **Delivery Completed** yang isinya `X`
- Filter hanya yang **Tgl Terima Barang** sesudah **Del Date PO**
                """)

            st.caption("Status pengiriman PO (tepat waktu vs terlambat vs pending).")
                
            delivery_query = f"""
            SELECT
                COALESCE(poi.on_time_delivery, 'PENDING') AS status_delivery,
                COUNT(*) AS count
            FROM po_items poi
            JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
            WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
              AND {bagian_po_poi}
              AND {dept_cond}
              AND {pg_cond}
            GROUP BY 1
            """
            with st.spinner("Memuat delivery performance..."):
                delivery_data = load_data(delivery_query)

            if not delivery_data.empty:
                color_map = {
                    'TEPAT WAKTU': '#2ca02c',
                    'IN PROGRESS': '#ff7f0e',
                    'TERLAMBAT':   '#d62728',
                    'PENDING':     '#7f7f7f'
                }
                fig = px.pie(
                    delivery_data, values='count', names='status_delivery',
                    color='status_delivery', color_discrete_map=color_map, hole=0.4
                )
                fig.update_layout(height=350, margin=dict(t=0, b=0, l=0, r=0), separators=",.")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Tidak ada data yang tersedia.")

        with col_chart2:
            title_col, btn_col = st.columns([9, 1])
            with title_col:
                st.markdown("""
                    <h1 style='display: flex; align-items: center; font-size:30px;'>
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 6px; margin-right: 8px;">
                            <path d="M11 2a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v12h.5a.5.5 0 0 1 0 1H.5a.5.5 0 0 1 0-1H1v-3a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3h1V7a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v7h1z"/>
                        </svg>
                        Material Category Value
                    </h1>
                """, unsafe_allow_html=True)
            with btn_col:
                st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
                key7 = "show_formula_material_cat"
                if key7 not in st.session_state:
                    st.session_state[key7] = False
                is_open = st.session_state[key7]
                icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                tooltip = "Hide Formula" if is_open else "Show Formula"
                st.button(icon, key=f"btn_{key7}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key7})

            if st.session_state.get(key7, False):
                st.info("""\
**Material Category Value**: Bar chart total nilai PO per kategori ABC material.

**Formula Excel:** (PO SAP)
- Filter **Material No** selain `1000076`
- Filter **PO Deletion Flag** selain `L`
- Filter **ABC Indicator** sesuai keinginan
- Jumlahkan nilai **Total Amount in Local Curr**

**Arti klasifikasi ABC (Analisis Pareto):**
| Kategori | Proporsi Item | Proporsi Nilai |
|---|---|---|
| A | ~20% | ~80% - material strategis, harga tinggi |
| B | ~30% | ~15% - material menengah |
| C | ~50% | ~5% - material umum, harga rendah |
                """)

            st.caption("Total nilai PO per kategori ABC material.")
                
            material_query = f"""
            SELECT
                abc_indicator,
                SUM(total_amount_local_curr) AS total_value
            FROM vw_pr_po_complete
            WHERE date_ordered >= '{date_from}' AND date_ordered <= '{date_to}'
              AND abc_indicator IS NOT NULL
              AND {bagian_po_cond}
              AND ({dept_cond.replace('poi.department_code', 'department_code')})
              AND ({pg_cond.replace('poh.purchasing_group', 'purchasing_group')})
            GROUP BY abc_indicator
            ORDER BY abc_indicator
            """
            with st.spinner("Memuat material category..."):
                material_data = load_data(material_query)

            if not material_data.empty:
                material_data['total_value'] = material_data['total_value'].fillna(0)
                material_data['label_text'] = material_data['total_value'].apply(format_idr_short)
                fig = px.bar(
                    material_data, x='abc_indicator', y='total_value',
                    labels={'abc_indicator': 'ABC Category', 'total_value': 'Total PO Value (IDR)'},
                    text='label_text'
                )
                max_mat_val = material_data['total_value'].max()
                fig.update_layout(
                    height=350, margin=dict(t=20, b=0, l=0, r=0), separators=",.",
                    yaxis=idr_axis(max_mat_val)
                )
                fig.update_traces(
                    textfont_size=12, textangle=0, textposition="outside", cliponaxis=False,
                    hovertemplate="<b>ABC: %{x}</b><br>Total: Rp %{text}<extra></extra>"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Tidak ada data yang tersedia.")

        # =====================================================================
        # INTEGRASI AI: PANGGIL MELATI DENGAN KONTEKS GLOBAL
        # =====================================================================

        # Ambil konteks global (SAP default + SIPS aktif) yang sudah dibangun di app.py
        global_context = kwargs.get("global_context", "")

        # Tambahkan detail chart halaman ini sebagai suplemen konteks lokal
        suplemen_lines = [
            "# SUPLEMEN - DETAIL CHART HALAMAN INI (PR-PO SAP Dashboard)",
        ]

        # 0. Filter aktif
        suplemen_lines.append("## 0. FILTER AKTIF")
        suplemen_lines.append(info_filter)
        suplemen_lines.append("")

        # 1. KPI Utama (selalu tersedia karena diambil di awal render)
        suplemen_lines.append("## 1. KPI UTAMA DASHBOARD")
        suplemen_lines.append(f"- Total PR: {format_number(total_pr)} | PR dengan PO: {format_number(pr_with_po)} | PR Pending: {format_number(pr_without)}")
        suplemen_lines.append(f"- Total PO (baris): {format_number(total_po)} | Total PO Unik: {format_number(total_po_dist)}")
        suplemen_lines.append(f"- Produktivitas PR→PO: {format_number(produktivitas, decimals=2)}%")
        suplemen_lines.append(f"- Total Estimasi (OE): {format_idr(estimasi_pr_all)}")
        suplemen_lines.append(f"- Total Savings: {format_idr(savings)} ({format_number(savings_pct, decimals=1)}%)")
        suplemen_lines.append(f"- Avg Lead Time Proses PO: {format_number(avg_lt_val, decimals=1)} hari")
        suplemen_lines.append(f"- % Pengiriman Selesai: {format_number(pct_pengiriman, decimals=1)}% ({format_number(po_delivered)} item GR / {format_number(total_po)} item PO)")
        suplemen_lines.append(f"- % Ketepatan Pengiriman: {format_number(ketepatan_pct, decimals=1)}% ({format_number(po_ontime)} item tepat / {format_number(po_del_tot)} item selesai)")
        suplemen_lines.append("")

        # 2. Top 10 Vendor
        if 'vendor_data' in locals() and not vendor_data.empty:
            suplemen_lines.append("## 2. TOP 10 VENDOR (Berdasarkan Nilai PO)")
            suplemen_lines.append(vendor_data.to_csv(index=False))
            suplemen_lines.append("")

        # 3. Top PR Pending Tertua
        if 'pr_without_po' in locals() and not pr_without_po.empty:
            suplemen_lines.append("## 3. TOP PR PENDING TERTUA (Belum diproses ke PO)")
            df_pending_simple = pr_without_po[['no_pr', 'department', 'total_estimasi']]
            suplemen_lines.append(df_pending_simple.to_csv(index=False))
            suplemen_lines.append("")

        # 4. Status Pengiriman
        if 'delivery_data' in locals() and not delivery_data.empty:
            suplemen_lines.append("## 4. STATUS PENGIRIMAN PO")
            suplemen_lines.append(delivery_data.to_csv(index=False))
            suplemen_lines.append("")

        # 5. Tren PR-PO per Bulan
        if 'trend_data' in locals() and not trend_data.empty:
            suplemen_lines.append("## 5. TREN PEMBUATAN PR & PO PER BULAN")
            df_trend_simple = trend_data.copy()
            df_trend_simple['month'] = df_trend_simple['month'].astype(str).str[:7]
            suplemen_lines.append(df_trend_simple.to_csv(index=False))
            suplemen_lines.append("")

        # 6. Distribusi Lead Time
        if 'leadtime_data' in locals() and not leadtime_data.empty:
            suplemen_lines.append("## 6. DISTRIBUSI LEAD TIME PROSES PO")
            suplemen_lines.append(leadtime_data[['lead_time_range', 'count']].to_csv(index=False))
            suplemen_lines.append("")

        # 7. Distribusi PR per Department
        if 'dept_data' in locals() and not dept_data.empty:
            suplemen_lines.append("## 7. DISTRIBUSI PR PER DEPARTMENT (TOP 10)")
            suplemen_lines.append(dept_data.head(10).to_csv(index=False))
            suplemen_lines.append("")

        # 8. Kategori Material ABC
        if 'material_data' in locals() and not material_data.empty:
            suplemen_lines.append("## 8. TOTAL NILAI PO PER KATEGORI MATERIAL (ABC)")
            suplemen_lines.append(material_data[['abc_indicator', 'total_value']].to_csv(index=False))
            suplemen_lines.append("")

        konteks_final = global_context + "\n---\n" + "\n".join(suplemen_lines)

        render_chat_analyst(
            konteks_data_teks=konteks_final,
            nama_halaman="PR-PO Monitoring Dashboard",
            load_data_fn=load_data,
        )