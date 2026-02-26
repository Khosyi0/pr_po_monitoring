"""
v_dashboard.py - Halaman Dashboard Monitoring
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from utils import format_idr, format_idr_short, format_number, format_currency


def render(filter_conditions, bagian_pr_cond, bagian_po_cond, load_data, **kwargs):
        
        def toggle_state(state_key):
            st.session_state[state_key] = not st.session_state[state_key]

        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:60px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" fill="currentColor" class="bi bi-clipboard2-data-fill" viewBox="0 0 16 16" style="margin-bottom: 10px; margin-right: 8px;">
                    <path d="M10 .5a.5.5 0 0 0-.5-.5h-3a.5.5 0 0 0-.5.5.5.5 0 0 1-.5.5.5.5 0 0 0-.5.5V2a.5.5 0 0 0 .5.5h5A.5.5 0 0 0 11 2v-.5a.5.5 0 0 0-.5-.5.5.5 0 0 1-.5-.5"/>
                    <path d="M4.085 1H3.5A1.5 1.5 0 0 0 2 2.5v12A1.5 1.5 0 0 0 3.5 16h9a1.5 1.5 0 0 0 1.5-1.5v-12A1.5 1.5 0 0 0 12.5 1h-.585q.084.236.085.5V2a1.5 1.5 0 0 1-1.5 1.5h-5A1.5 1.5 0 0 1 4 2v-.5q.001-.264.085-.5M10 7a1 1 0 1 1 2 0v5a1 1 0 1 1-2 0zm-6 4a1 1 0 1 1 2 0v1a1 1 0 1 1-2 0zm4-3a1 1 0 0 1 1 1v3a1 1 0 1 1-2 0V9a1 1 0 0 1 1-1"/>
                </svg>
                PR-PO Monitoring Dashboard
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

        kpi_query = f"""
        SELECT
            COUNT(DISTINCT CASE WHEN no_pr != 'No PR' AND {bagian_pr_cond}
                THEN no_pr || '-' || line_item_pr::text END)              AS total_pr,
            COUNT(CASE WHEN {bagian_po_cond} THEN nomor_po END)             AS total_po,
            COUNT(DISTINCT CASE WHEN nomor_po IS NOT NULL AND no_pr != 'No PR' AND {bagian_pr_cond}
                THEN no_pr || '-' || line_item_pr::text END)              AS pr_with_po,
            COUNT(DISTINCT CASE WHEN nomor_po IS NULL AND no_pr != 'No PR' AND {bagian_pr_cond}
                THEN no_pr || '-' || line_item_pr::text END)              AS pr_without_po,
            COALESCE(SUM(CASE WHEN {bagian_pr_cond} THEN oe ELSE 0 END), 0)                      AS total_estimasi,
            COALESCE(SUM(CASE WHEN {bagian_po_cond} THEN total_amount_local_curr ELSE 0 END), 0) AS total_po_amount,
            COALESCE(SUM(CASE WHEN {bagian_pr_cond} THEN COALESCE(oe, 0) ELSE 0 END -
                        CASE WHEN {bagian_po_cond} THEN COALESCE(total_amount_local_curr, 0) ELSE 0 END), 0) AS total_savings,
            COALESCE(AVG(CASE
                    WHEN total_amount_local_curr IS NOT NULL AND oe IS NOT NULL AND oe > 0
                    AND {bagian_pr_cond} AND {bagian_po_cond}
                    THEN (oe - total_amount_local_curr) / oe * 100
                    END), 0)                                                              AS avg_savings_pct,
            ROUND(AVG(CASE WHEN {bagian_po_cond} AND lead_time_process_po IS NOT NULL
                THEN lead_time_process_po END)::numeric, 2)                              AS avg_lead_time,
            COUNT(DISTINCT CASE WHEN {bagian_po_cond} AND nomor_po IS NOT NULL
                THEN nomor_po END)                                                        AS total_po_distinct,
            COUNT(DISTINCT CASE WHEN {bagian_po_cond} AND nomor_po IS NOT NULL
                AND status_pengiriman = 'SELESAI' THEN nomor_po END)                     AS po_delivered,
            COUNT(DISTINCT CASE WHEN {bagian_po_cond} AND nomor_po IS NOT NULL
                AND on_time_delivery = 'TEPAT WAKTU' THEN nomor_po END)                  AS po_ontime,
            COUNT(DISTINCT CASE WHEN {bagian_po_cond} AND nomor_po IS NOT NULL
                AND on_time_delivery IN ('TEPAT WAKTU','TERLAMBAT')
                THEN nomor_po END)                                                        AS po_delivered_total
        FROM vw_pr_po_complete
        WHERE {filter_conditions}
        """

        with st.spinner("Memuat KPI..."):
            kpi_data = load_data(kpi_query)

        total_pr     = int(kpi_data['total_pr'][0] or 0)
        total_po     = int(kpi_data['total_po'][0] or 0)
        pr_with_po   = int(kpi_data['pr_with_po'][0] or 0)
        pr_without   = int(kpi_data['pr_without_po'][0] or 0)
        estimasi     = float(kpi_data['total_estimasi'][0] or 0)
        savings      = float(kpi_data['total_savings'][0] or 0)
        savings_pct  = float(kpi_data['avg_savings_pct'][0] or 0)

        with st.spinner("Memuat KPI..."):
            kpi_data = load_data(kpi_query)

        total_pr         = int(kpi_data['total_pr'][0] or 0)
        total_po         = int(kpi_data['total_po'][0] or 0)
        pr_with_po       = int(kpi_data['pr_with_po'][0] or 0)
        pr_without       = int(kpi_data['pr_without_po'][0] or 0)
        estimasi         = float(kpi_data['total_estimasi'][0] or 0)
        savings          = float(kpi_data['total_savings'][0] or 0)
        savings_pct      = float(kpi_data['avg_savings_pct'][0] or 0)
        _alt             = kpi_data['avg_lead_time'][0]
        avg_lt_val       = float(_alt) if _alt is not None else 0.0
        total_po_dist    = int(kpi_data['total_po_distinct'][0] or 0)
        po_delivered     = int(kpi_data['po_delivered'][0] or 0)
        po_ontime        = int(kpi_data['po_ontime'][0] or 0)
        po_del_tot       = int(kpi_data['po_delivered_total'][0] or 0)
        produktivitas    = (pr_with_po / total_pr * 100) if total_pr > 0 else 0.0
        pct_pengiriman   = (po_delivered / total_po_dist * 100) if total_po_dist > 0 else 0.0
        ketepatan_pct    = (po_ontime / po_del_tot * 100) if po_del_tot > 0 else 0.0

        # ── KPI_DASH: 14 item, 3 per baris ────────────────────────────────────
        KPI_DASH = [
            {
                "key": "kpi_total_pr",
                "icon_path": "M5 10.5a.5.5 0 0 1 .5-.5h2a.5.5 0 0 1 0 1h-2a.5.5 0 0 1-.5-.5m0-2a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5m0-2a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5 M3 0h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2m0 1a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1z",
                "label": "Total PR",
                "value": f"{format_number(total_pr)}",
                "delta": f"{format_number(pr_with_po)} with PO",
                "formula": """\
**Total PR**: Jumlah baris Purchase Requisition unik dalam periode filter.

**Kalkulasi SQL:**
```sql
COUNT(DISTINCT CASE
    WHEN no_pr != 'No PR' AND {bagian_pr_cond}
    THEN no_pr || '-' || line_item_pr::text
END) AS total_pr
```

| Sub-metrik | Kalkulasi |
|---|---|
| PR with PO | COUNT DISTINCT dimana `nomor_po IS NOT NULL` |
| PR pending | Total PR − PR with PO |

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
**Total PO**: Jumlah baris Purchase Order dalam periode filter.

**Kalkulasi SQL:**
```sql
COUNT(CASE WHEN {bagian_po_cond} THEN nomor_po END) AS total_po
```

PR pending = jumlah PR yang belum memiliki PO. Semakin kecil = semakin baik.

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
**Produktivitas PR-PO**: Persentase item PR yang berhasil dikonversi menjadi PO.

**Kalkulasi SQL:**
```sql
COUNT(pr_with_po) / COUNT(total_pr) * 100 AS produktivitas_pct
```

**Formula Excel:**
```
= PR_with_PO / Total_PR × 100%
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
                "formula": """\
**Total Savings**: Selisih OE dengan realisasi PO.

**Kalkulasi SQL:**
```sql
SUM(oe_pr) - SUM(total_amount_po) AS total_savings
AVG((oe - realisasi) / oe * 100)  AS avg_savings_pct
```

| Kondisi | Artinya |
|---|---|
| Positif | Realisasi < OE → penghematan ✅ |
| Negatif | Realisasi > OE → over budget ❌ |

**Target:** -\
""",
            },
            {
                "key": "kpi_estimasi",
                "icon_path": "M4 10.781c.148 1.667 1.513 2.85 3.591 3.003V15h1.043v-1.216c2.27-.179 3.678-1.438 3.678-3.3 0-1.59-.947-2.51-2.956-3.028l-.722-.187V3.467c1.122.11 1.879.714 2.07 1.616h1.47c-.166-1.6-1.54-2.748-3.54-2.875V1H7.591v1.233c-1.939.23-3.27 1.472-3.27 3.156 0 1.454.966 2.483 2.661 2.917l.61.162v4.031c-1.149-.17-1.94-.8-2.131-1.718zm3.391-3.836c-1.043-.263-1.6-.825-1.6-1.616 0-.944.704-1.641 1.8-1.828v3.495l-.2-.05zm1.591 1.872c1.287.323 1.852.859 1.852 1.769 0 1.097-.826 1.828-2.2 1.939V8.73z",
                "label": "Total Estimasi PR",
                "value": format_idr(estimasi),
                "delta": "Owner's Estimate (OE)",
                "formula": """\
**Total Estimasi PR (OE)**: Total nilai Owner's Estimate dari semua PR.

**Kalkulasi SQL:**
```sql
COALESCE(SUM(CASE WHEN {bagian_pr_cond} THEN oe ELSE 0 END), 0) AS total_estimasi
```

Sumber: `estimasi_pr × quantity_pr`. Anggaran yang disiapkan sebelum proses pengadaan dimulai.

**Target:** -\
""",
            },
            {
                "key": "kpi_anggaran",
                "icon_path": "M1 2.828c.885-.37 2.154-.769 3.388-.893 1.33-.134 2.458.063 3.112.752v9.746c-.935-.53-2.12-.603-3.213-.493-1.18.12-2.37.461-3.287.811zm7.5-.141c.654-.689 1.782-.886 3.112-.752 1.234.124 2.503.523 3.388.893v9.923c-.918-.35-2.107-.692-3.287-.81-1.094-.111-2.278-.039-3.213.492zM8 1.783C7.015.936 5.587.81 4.287.94c-1.514.153-3.042.672-3.994 1.105A.5.5 0 0 0 0 2.5v11a.5.5 0 0 0 .707.455c.882-.4 2.303-.881 3.68-1.02 1.409-.142 2.59.087 3.223.877a.5.5 0 0 0 .78 0c.633-.79 1.814-1.019 3.222-.877 1.378.139 2.8.62 3.681 1.02A.5.5 0 0 0 16 13.5v-11a.5.5 0 0 0-.293-.455c-.952-.433-2.48-.952-3.994-1.105C10.413.809 8.985.936 8 1.783",
                "label": "Pengelolaan Anggaran Operasional",
                "value": "-",
                "delta": "Target: -",
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
                "value": "-",
                "delta": "Target: -",
                "formula": """\
**Sinergi PI Group**: Jumlah atau nilai kolaborasi/transaksi dengan entitas PI Group lainnya.

**Status:** Tidak ada kolom sinergi di `vw_pr_po_complete`. Membutuhkan data dari sistem terpisah.

**Formula Excel (jika data tersedia):**
```
= COUNT(PO ke vendor PI Group)
  atau SUM(nilai PO ke vendor PI Group)
```

**Target:** -\
""",
            },
            {
                "key": "kpi_kecepatan_po",
                "icon_path": "M8 3.5a.5.5 0 0 0-1 0V9a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0 0 .496-.868L8 8.71V3.5z M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0z",
                "label": "Kecepatan Proses PO",
                "value": f"{format_number(avg_lt_val, decimals=2)} Hari",
                "delta": "Target: - Hari Kalender",
                "formula": """\
**Kecepatan Proses PO**: Rata-rata hari dari PR dibuat hingga PO diterbitkan.

**Kalkulasi SQL:**
```sql
ROUND(AVG(lead_time_process_po)::numeric, 2) AS avg_lead_time
```

**Formula Excel:**
```
= AVERAGE(date_ordered - tgl_create_pr)
```

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
                "delta": f"{format_number(po_delivered)} GR / {format_number(total_po_dist)} PO",
                "formula": """\
**% Pengiriman Barang (GR/PO)**: Persentase PO yang sudah diterima barangnya.

**Kalkulasi SQL:**
```sql
COUNT(DISTINCT CASE WHEN delivery_completed = 'X' THEN nomor_po END)
/ COUNT(DISTINCT nomor_po) * 100
```

**Formula Excel:**
```
= COUNTIF(delivery_completed,"X") / COUNT(nomor_po) × 100%
```

**Target:** -\
""",
            },
            {
                "key": "kpi_ketepatan",
                "icon_path": "M10.97 4.97a.75.75 0 0 1 1.07 1.05l-3.99 4.99a.75.75 0 0 1-1.08.02L4.324 8.384a.75.75 0 1 1 1.06-1.06l2.094 2.093 3.473-4.425z M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0z",
                "label": "Ketepatan Pengiriman Barang",
                "value": f"{format_number(ketepatan_pct, decimals=1)}%",
                "delta": f"{format_number(po_ontime)} tepat / {format_number(po_del_tot)} selesai",
                "formula": """\
**Ketepatan Pengiriman Barang**: Persentase PO diterima tepat waktu dari total yang sudah dikirim.

**Kalkulasi SQL:**
```sql
COUNT(DISTINCT CASE WHEN on_time_delivery = 'TEPAT WAKTU' THEN nomor_po END)
/ COUNT(DISTINCT CASE WHEN on_time_delivery IN ('TEPAT WAKTU','TERLAMBAT')
    THEN nomor_po END) * 100
```

**Formula Excel:**
```
= COUNTIF(on_time_delivery,"TEPAT WAKTU")
  / COUNTIF(on_time_delivery,"<>IN PROGRESS") × 100%
```

**Target:** -\
""",
            },
            {
                "key": "kpi_otobos",
                "icon_path": "M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001q.044.06.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1 1 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0",
                "label": "Pemenuhan SLA OTOBOS",
                "value": "-",
                "delta": "Average (OTOBOS)",
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
                "delta": "PO/OE",
                "formula": """\
**Efisiensi Pengadaan (PO/OE)**: Rata-rata persentase penghematan dari nilai OE per item PO.

**Kalkulasi SQL:**
```sql
AVG(CASE WHEN oe > 0
    THEN (oe - total_amount_local_curr) / oe * 100
END) AS efisiensi_pct
```

**Formula Excel:**
```
= AVERAGEIF(oe,">0",(oe-realisasi)/oe*100%)
```

Nilai ini setara dengan **Total Savings %**. Detail per material: halaman Evaluasi Harga Barang.

**Target:** -\
""",
            },
            {
                "key": "kpi_izin_impor",
                "icon_path": "M8 1a2 2 0 0 1 2 2v4H6V3a2 2 0 0 1 2-2m3 6V3a3 3 0 0 0-6 0v4a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2",
                "label": "Pemenuhan Izin Impor",
                "value": "-",
                "delta": "Target: -",
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
                "value": "-",
                "delta": "Target: -",
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
                    neutral = kpi["value"] == "-" or kpi["delta"].startswith("Target:")
                    delta_cls = "kpi-delta-neutral" if neutral else "kpi-delta"
                    delta_arrow = "" if neutral else "↑ "

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

**Kolom yang digunakan:**
- `department_code`: kode departemen dari tabel `purchase_requisitions`
- `no_pr`: nomor PR, di-COUNT DISTINCT untuk menghitung jumlah PR unik
- `nomor_po`: digunakan untuk menentukan apakah PR sudah terkonversi ke PO

**Kalkulasi:**
| Metrik | Formula SQL | Keterangan |
|---|---|---|
| Total PR | `COUNT(DISTINCT no_pr)` | Semua PR unik di periode filter |
| PR with PO | `COUNT(DISTINCT no_pr) WHERE nomor_po IS NOT NULL` | PR yang sudah ada PO-nya |
| PR without PO | `Total PR - PR with PO` | PR yang belum diproses |

**Tidak ada formula Excel langsung** untuk chart ini, data diambil dari relasi tabel `pr_items` ↔ `po_items` di database. Di Excel, padanannya adalah `COUNTIF` atau `SUMIF` dengan kondisi apakah kolom *No PO* di sheet PO SAP terisi atau kosong untuk setiap *No PR*.
                """)

            st.caption("Jumlah PR per departemen, dibedakan antara PR yang sudah memiliki PO dan yang belum.")

            dept_query = f"""
            SELECT
                COALESCE(department_code, 'Unknown') AS department,
                COUNT(DISTINCT no_pr)                                                AS total_pr,
                COUNT(DISTINCT CASE WHEN nomor_po IS NOT NULL THEN no_pr END)        AS pr_with_po
            FROM vw_pr_po_complete
            WHERE {filter_conditions} AND {bagian_pr_cond}
            GROUP BY department_code
            ORDER BY total_pr DESC
            LIMIT 10
            """
            with st.spinner("Memuat chart department..."):
                dept_data = load_data(dept_query)

            if not dept_data.empty:
                fig = go.Figure(data=[
                    go.Bar(name='PR with PO',    x=dept_data['department'], y=dept_data['pr_with_po']),
                    go.Bar(name='PR without PO', x=dept_data['department'],
                        y=dept_data['total_pr'] - dept_data['pr_with_po'])
                ])
                fig.update_layout(barmode='stack', height=400, separators=",.")
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

**Kalkulasi SQL:**
| Metrik | Formula |
|---|---|
| Jumlah PO | `COUNT(DISTINCT nomor_po)` |
| Total Nilai | `SUM(total_amount_local_curr)` |

Diurutkan descending berdasarkan `total_value`, lalu diambil 10 teratas.

**Sumber kolom:** `total_amount_local_curr` dari tabel `po_items`, di-join ke tabel `vendors`.

Di Excel: `=SUMIF(kolom_vendor, nama_vendor, kolom_total_amount)` untuk tiap vendor, urutkan descending, ambil 10 teratas.
                """)

            st.caption("Top 10 vendor dengan total nilai PO terbesar.")

            vendor_query = f"""
            SELECT
                COALESCE(vendor_name, 'Unknown') AS vendor,
                COUNT(DISTINCT nomor_po)         AS total_po,
                SUM(total_amount_local_curr)     AS total_value
            FROM vw_pr_po_complete
            WHERE {filter_conditions} AND nomor_po IS NOT NULL AND {bagian_po_cond}
            GROUP BY vendor_name
            ORDER BY total_value DESC
            LIMIT 10
            """
            with st.spinner("Memuat chart vendor..."):
                vendor_data = load_data(vendor_query)

            if not vendor_data.empty:
                fig = px.bar(
                    vendor_data, x='total_value', y='vendor', orientation='h',
                    labels={'total_value': 'Total Value (IDR)', 'vendor': 'Vendor'}
                )
                fig.update_layout(height=400, yaxis={'categoryorder': 'total ascending'}, separators=",.")
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

**Kalkulasi SQL:**
| Metrik | Formula |
|---|---|
| PR per bulan | `COUNT(DISTINCT no_pr \|\| '-' \|\| line_item_pr)` GROUP BY `DATE_TRUNC('month', tgl_create_pr)` |
| PO per bulan | `COUNT(nomor_po)` GROUP BY `DATE_TRUNC('month', date_ordered)` |

Kedua sumber digabung dengan `FULL OUTER JOIN` agar bulan tanpa PR atau tanpa PO tetap muncul.

Mode **Kumulatif**: menggunakan `.cumsum()` di Python setelah data diambil, cocok untuk memantau pencapaian target tahunan.

Di Excel: `=COUNTIFS(kolom_tgl_pr,">="&awal_bulan, kolom_tgl_pr,"<="&akhir_bulan)` per baris bulan.
                """)

            st.caption("Jumlah PR dan PO yang dibuat per bulan.")
        
            trend_query = f"""
            WITH pr_monthly AS (
                SELECT
                    DATE_TRUNC('month', tgl_create_pr) AS month_date,
                    COUNT(DISTINCT CASE WHEN no_pr != 'No PR' AND {bagian_pr_cond}
                        THEN no_pr || '-' || line_item_pr::text END) AS total_pr
                FROM vw_pr_po_complete
                WHERE tgl_create_pr IS NOT NULL AND {filter_conditions}
                GROUP BY 1
            ),
            po_monthly AS (
                SELECT
                    DATE_TRUNC('month', date_ordered) AS month_date,
                    COUNT(CASE WHEN {bagian_po_cond} THEN nomor_po END) AS total_po
                FROM vw_pr_po_complete
                WHERE date_ordered IS NOT NULL AND {filter_conditions}
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
            
                show_cumulative = st.toggle("Tampilkan secara Kumulatif (Running Total)", value=False)
            
                if show_cumulative:
                    y_pr = trend_data['total_pr'].cumsum()
                    y_po = trend_data['total_po'].cumsum()
                    y_axis_title = 'Cumulative Count'
                else:
                    y_pr = trend_data['total_pr']
                    y_po = trend_data['total_po']
                    y_axis_title = 'Count per Month'

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=trend_data['month'], y=y_pr,
                                        mode='lines+markers', name='PR Created',
                                        line=dict(color='#1f77b4', width=2)))
                fig.add_trace(go.Scatter(x=trend_data['month'], y=y_po,
                                        mode='lines+markers', name='PO Created',
                                        line=dict(color='#2ca02c', width=2)))
            
                fig.update_layout(height=400, xaxis_title='Month', yaxis_title=y_axis_title)
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
**Lead Time Distribution**: Pie chart distribusi PO berdasarkan rentang waktu proses (dari PR dibuat sampai PO terbit).

**Bucket klasifikasi SQL:**
```
CASE
  WHEN lead_time_process_po <= 7  THEN '0-7 days'
  WHEN lead_time_process_po <= 14 THEN '8-14 days'
  WHEN lead_time_process_po <= 30 THEN '15-30 days'
  WHEN lead_time_process_po <= 60 THEN '31-60 days'
  ELSE                                 '60+ days'
END
```

**Sumber kolom:** `lead_time_process_po` di `vw_pr_po_complete`, dihitung sebagai selisih hari antara `tgl_create_pr` dan `date_ordered` (tanggal PO diterbitkan).

Di Excel: `=date_ordered - tgl_create_pr`, lalu klasifikasikan dengan `=IFS(...)` atau nested `=IF(...)`.
                """)

            st.caption("Distribusi PO berdasarkan rentang waktu proses (dari PR dibuat sampai PO terbit).")
                
            leadtime_query = f"""
            SELECT
                CASE
                    WHEN lead_time_process_po <= 7  THEN '0-7 days'
                    WHEN lead_time_process_po <= 14 THEN '8-14 days'
                    WHEN lead_time_process_po <= 30 THEN '15-30 days'
                    WHEN lead_time_process_po <= 60 THEN '31-60 days'
                    ELSE '60+ days'
                END AS lead_time_range,
                COUNT(*) AS count,
                MIN(lead_time_process_po) AS sort_order
            FROM vw_pr_po_complete
            WHERE {filter_conditions} AND lead_time_process_po IS NOT NULL AND {bagian_po_cond}
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

**Kalkulasi SQL:**
```sql
SELECT no_pr, tgl_create_pr, department_code, bagian_pr,
       SUM(oe) AS total_estimasi
FROM vw_pr_po_complete
WHERE nomor_po IS NULL
  AND no_pr != 'No PR'
GROUP BY no_pr, tgl_create_pr, department_code, bagian_pr
ORDER BY tgl_create_pr ASC   -- yang paling lama muncul di atas
LIMIT 10
```

**Kolom `total_estimasi`:** `SUM(oe)`: total nilai estimasi seluruh baris item pada PR tersebut.

Di Excel: filter kolom *No PO* yang kosong → urutkan *Tgl Create PR* ascending → ambil 10 baris teratas.
            """)

        st.caption("Tabel 10 PR tertua yang belum diproses menjadi PO.")

        pr_without_po_query = f"""
        SELECT
            no_pr, tgl_create_pr,
            department_code AS department,
            bagian_pr AS bagian,
            COALESCE(SUM(oe), 0) AS total_estimasi
        FROM vw_pr_po_complete
        WHERE {filter_conditions} AND nomor_po IS NULL
        AND no_pr != 'No PR' AND {bagian_pr_cond}
        GROUP BY no_pr, tgl_create_pr, department_code, bagian_pr
        ORDER BY tgl_create_pr ASC
        LIMIT 10
        """
        with st.spinner("Memuat PR pending..."):
            pr_without_po = load_data(pr_without_po_query)

        if not pr_without_po.empty:
            pr_without_po['tgl_create_pr'] = pd.to_datetime(pr_without_po['tgl_create_pr']).dt.strftime('%Y-%m-%d')
            pr_without_po['total_estimasi'] = pr_without_po['total_estimasi'].apply(
                lambda x: format_currency(x) if pd.notna(x) else ""
            )
            st.dataframe(pr_without_po, use_container_width=True, height=300)
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

**Sumber:** Kolom `on_time_delivery` di `vw_pr_po_complete`, diisi berdasarkan perbandingan tanggal aktual vs target delivery.

| Status | Kondisi |
|---|---|
| TEPAT WAKTU | Barang tiba (tanggal GR) ≤ `del_date_po` |
| TERLAMBAT | Barang tiba (tanggal GR) > `del_date_po` |
| IN PROGRESS | PO sudah terbit, Good Receipt belum masuk |
| PENDING | Belum ada informasi delivery sama sekali |

Di Excel: `=IF(tgl_gr="","IN PROGRESS",IF(tgl_gr<=del_date_po,"TEPAT WAKTU","TERLAMBAT"))`
                """)

            st.caption("Status pengiriman PO (tepat waktu vs terlambat vs pending).")
                
            delivery_query = f"""
            SELECT
                COALESCE(on_time_delivery, 'PENDING') AS status_delivery,
                COUNT(*) AS count
            FROM vw_pr_po_complete
            WHERE {filter_conditions} AND {bagian_po_cond} AND nomor_po IS NOT NULL
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
                st.info("No delivery data available.")

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

**Kalkulasi SQL:**
```sql
SELECT abc_indicator,
       SUM(total_amount_local_curr) AS total_value
FROM vw_pr_po_complete
WHERE abc_indicator IS NOT NULL
GROUP BY abc_indicator
ORDER BY abc_indicator
```

**Arti klasifikasi ABC (Analisis Pareto):**
| Kategori | Proporsi Item | Proporsi Nilai |
|---|---|---|
| A | ~20% | ~80% - material strategis, harga tinggi |
| B | ~30% | ~15% - material menengah |
| C | ~50% | ~5% - material umum, harga rendah |

**Sumber:** Kolom `abc_indicator` dari master material SAP, tersedia di kolom *ABC Ind.* pada data PO SAP.
                """)

            st.caption("Total nilai PO per kategori ABC material.")
                
            material_query = f"""
            SELECT
                abc_indicator,
                SUM(total_amount_local_curr) AS total_value
            FROM vw_pr_po_complete
            WHERE {filter_conditions} AND abc_indicator IS NOT NULL AND {bagian_po_cond}
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
                fig.update_layout(height=350, margin=dict(t=20, b=0, l=0, r=0), separators=",.")
                fig.update_traces(
                    textfont_size=12, textangle=0, textposition="outside", cliponaxis=False,
                    hovertemplate="<b>ABC: %{x}</b><br>Total: Rp %{text}<extra></extra>"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No material data available.")