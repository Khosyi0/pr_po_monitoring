"""
v_kinerja_pg.py - Halaman Kinerja Purchasing Group
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from utils import format_idr, format_idr_short, format_number, format_currency, render_chat_analyst


def render(filter_conditions, bagian_pr_cond, bagian_po_cond, load_data, **kwargs):
        
        info_filter = kwargs.get('info_filter', 'Tidak ada filter spesifik')
        
        # Fungsi helper untuk tombol toggle formula
        def toggle_state(state_key):
            st.session_state[state_key] = not st.session_state[state_key]

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
        st.markdown("""
            <style>
            [data-testid="stMetricValue"] > div {
                font-size: 1.8rem !important; /* Ukuran font standar yang nyaman dibaca, tidak terlalu besar/kecil */
                white-space: normal !important; /* KUNCI: Mencegah teks dipotong (...) dan memungkinkannya turun baris */
                word-wrap: break-word !important; /* Memastikan angka/kata panjang bisa patah dengan rapi */
                line-height: 1.2 !important; /* Mengatur jarak vertikal jika teks menjadi 2 baris */
            }
            </style>
        """, unsafe_allow_html=True)
        st.markdown(f"""
            <style>
            /* Warna Hijau */
            .metric-green div[data-testid="stMetricDelta"] > div {{
                color: #09ab3b !important;
            }}
            /* Warna Oranye - Targetkan sampai ke teks terdalam */
            .metric-orange div[data-testid="stMetricDelta"] > div,
            .metric-orange span[data-testid="stMetricDeltaText"] {{
                color: #ffa500 !important;
                -webkit-text-fill-color: #ffa500 !important;
            }}
            /* Warna Merah */
            .metric-red div[data-testid="stMetricDelta"] > div {{
                color: #ff4b4b !important;
            }}
            </style>
        """, unsafe_allow_html=True)
        st.markdown("---")

        # ── KPI RINGKASAN ─────────────────────────────────────────────────────
        pg_kpi_query = f"""
        SELECT
            COUNT(DISTINCT CASE WHEN no_pr != 'No PR' AND {bagian_pr_cond}
                THEN no_pr || '-' || line_item_pr::text END)                        AS total_item_pr,
            COUNT(DISTINCT CASE WHEN nomor_po IS NOT NULL AND {bagian_po_cond}
                THEN nomor_po || '-' || item_po::text END)                          AS total_item_po,
            COALESCE(SUM(CASE WHEN {bagian_pr_cond} THEN oe ELSE 0 END), 0)        AS total_oe,
            COALESCE(SUM(CASE WHEN {bagian_po_cond} THEN total_amount_local_curr ELSE 0 END), 0) AS total_realisasi,
            ROUND(AVG(CASE WHEN {bagian_po_cond} AND lead_time_process_po IS NOT NULL
                THEN lead_time_process_po END)::numeric, 1)                         AS avg_lead_time_overall,
            COUNT(DISTINCT CASE WHEN nomor_po IS NOT NULL AND {bagian_po_cond}
                THEN po_items_metode END) FILTER (WHERE po_items_metode IS NOT NULL) AS jml_metode
        FROM (
            SELECT *, po.metode_pelelangan AS po_items_metode
            FROM vw_pr_po_complete v
            LEFT JOIN po_items po ON v.nomor_po = po.nomor_po AND v.item_po = po.item_po
        ) sub
        WHERE {filter_conditions}
        """

        # Query lebih sederhana untuk KPI, langsung dari view
        pg_kpi_query = f"""
        SELECT
            COUNT(DISTINCT CASE WHEN no_pr != 'No PR' AND {bagian_pr_cond}
                THEN no_pr || '-' || line_item_pr::text END)                         AS total_item_pr,
            COUNT(DISTINCT CASE WHEN nomor_po IS NOT NULL AND {bagian_po_cond}
                THEN nomor_po || '-' || item_po::text END)                           AS total_item_po,
            COUNT(DISTINCT CASE WHEN nomor_po IS NOT NULL AND no_pr != 'No PR' AND {bagian_pr_cond}
                THEN no_pr || '-' || line_item_pr::text END)                         AS pr_with_po,
            COALESCE(SUM(CASE WHEN {bagian_pr_cond} THEN oe ELSE 0 END), 0)         AS total_oe,
            COALESCE(SUM(CASE WHEN {bagian_po_cond}
                THEN total_amount_local_curr ELSE 0 END), 0)                         AS total_realisasi,
            ROUND(AVG(CASE WHEN {bagian_po_cond} AND lead_time_process_po IS NOT NULL
                THEN lead_time_process_po END)::numeric, 1)                          AS avg_lead_time_overall
        FROM vw_pr_po_complete
        WHERE {filter_conditions}
        """

        with st.spinner("Memuat KPI..."):
            pg_kpi = load_data(pg_kpi_query)

        if not pg_kpi.empty:
            t_item_pr    = int(pg_kpi['total_item_pr'][0] or 0)
            t_item_po    = int(pg_kpi['total_item_po'][0] or 0)
            pr_with_po   = int(pg_kpi['pr_with_po'][0] or 0)
            t_oe         = float(pg_kpi['total_oe'][0] or 0)
            t_real       = float(pg_kpi['total_realisasi'][0] or 0)
            t_efis       = t_oe - t_real
            t_efis_pct   = (t_efis / t_oe * 100) if t_oe > 0 else 0
            avg_lt        = pg_kpi['avg_lead_time_overall'][0]
        
            # MENGGUNAKAN PR_WITH_PO AGAR SINKRON DENGAN DASHBOARD
            konversi_pct = (pr_with_po / t_item_pr * 100) if t_item_pr > 0 else 0
            delta_efis = "efisien" if t_efis >= 0 else "over budget"
            lt_label   = f"{avg_lt} Hari" if pd.notna(avg_lt) else "N/A"
            lt_delta   = "✅ On Target" if (avg_lt and avg_lt <= 55) else "⚠️ Over Target"

            KPI_PG = [
                {"key": "kpi_pg_item_pr",   "metric_args": ("Total Item PR", f"{format_number(t_item_pr)}"),   "metric_kwargs": {"delta": f"{format_number(konversi_pct, decimals=1)}% sudah PO"},          "formula": """**Total Item PR**: Jumlah baris item Purchase Requisition unik dalam periode filter.

**Kalkulasi SQL:**
```sql
COUNT(DISTINCT CASE
    WHEN no_pr != 'No PR' AND {bagian_pr_cond}
    THEN no_pr || '-' || line_item_pr::text
END) AS total_item_pr
```

**% sudah PO** = `pr_with_po / total_item_pr × 100` - persentase item PR yang sudah berhasil dikonversi menjadi PO."""},
                {"key": "kpi_pg_item_po",   "metric_args": ("Total Item PO", f"{format_number(t_item_po)}"),   "metric_kwargs": {},                                                   "formula": """**Total Item PO**: Jumlah baris item Purchase Order dalam periode filter.

**Kalkulasi SQL:**
```sql
COUNT(CASE WHEN {bagian_po_cond} THEN nomor_po END) AS total_item_po
```

Menghitung semua baris PO per line item, bukan COUNT DISTINCT nomor PO. Satu nomor PO bisa memiliki banyak baris item material yang berbeda."""},
                {"key": "kpi_pg_oe",        "metric_args": ("Total OE", format_idr(t_oe)),        "metric_kwargs": {},                                                   "formula": """**Total OE (Owner's Estimate)**: Total nilai anggaran estimasi dari semua PR dalam periode filter.

**Kalkulasi SQL:**
```sql
COALESCE(SUM(CASE WHEN {bagian_pr_cond} THEN oe ELSE 0 END), 0) AS total_oe
```

**Sumber kolom `oe`:** `estimasi_pr × quantity_pr` - nilai estimasi harga satuan dikali kuantitas yang diminta pemohon PR."""},
                {"key": "kpi_pg_efisiensi", "metric_args": ("Efisiensi", format_idr(t_efis)),     "metric_kwargs": {"delta": f"{format_number(t_efis_pct, decimals=1)}% {delta_efis}"},         "formula": """**Efisiensi**: Selisih antara total OE dan total realisasi PO.

**Kalkulasi:**
```
Efisiensi   = Total OE − Total Realisasi PO
% Efisiensi = Efisiensi / Total OE × 100
```

| Kondisi | Interpretasi |
|---|---|
| **Positif** | Realisasi lebih murah dari anggaran → penghematan ✅ |
| **Negatif** | Realisasi melebihi anggaran → perlu evaluasi ❌ |"""},
                {"key": "kpi_pg_lead_time", "metric_args": ("Avg Lead Time", f"{format_number(avg_lt, decimals=1)} Hari" if pd.notna(avg_lt) else "N/A"), "metric_kwargs": {"delta": lt_delta},                                  "formula": """**Avg Lead Time**: Rata-rata waktu proses dari PR dibuat hingga PO diterbitkan, untuk semua Purchasing Group.

**Kalkulasi SQL:**
```sql
ROUND(AVG(CASE WHEN {bagian_po_cond} AND lead_time_process_po IS NOT NULL
    THEN lead_time_process_po END)::numeric, 1) AS avg_lead_time_overall
```

**Sumber `lead_time_process_po`:** Selisih hari antara `tgl_create_pr` dan `date_ordered`.

**Target SLA = 55 hari.** Informasi detail per bulan dan per jenis tender tersedia di tab **Kecepatan Proses**."""},
            ]

            for kpi in KPI_PG:
                if kpi["key"] not in st.session_state:
                    st.session_state[kpi["key"]] = False

            kpi_cols = st.columns(len(KPI_PG))
            for col, kpi in zip(kpi_cols, KPI_PG):
                with col:
                    m_col, btn_col = st.columns([5, 1])
                    with m_col:
                        st.metric(*kpi["metric_args"], **kpi["metric_kwargs"])
                    with btn_col:
                        st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
                        is_open = st.session_state[kpi["key"]]
                        icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                        tooltip = "Hide Formula" if is_open else "Show Formula"
                        st.button(icon, key=f"btn_{kpi['key']}", help=tooltip,
                                  on_click=toggle_state, kwargs={"state_key": kpi["key"]})

            for kpi in KPI_PG:
                if st.session_state[kpi["key"]]:
                    st.info(kpi["formula"])

        st.markdown("---")

        # ── TAB: OVERVIEW | TENDER TYPE | KECEPATAN PROSES ───────────────────
        # ── Inject JS: simpan & pulihkan tab aktif via localStorage ─────────
        # Streamlit versi lama tidak support key= di st.tabs().
        # JS ini menyimpan tab yang diklik ke localStorage dan memulihkannya
        # setelah rerun, sehingga tab tidak kembali ke tab 1 saat tombol ditekan.
        import streamlit.components.v1 as components
        components.html("""
        <script>
        (function() {
            var STORAGE_KEY = 'pg_active_tab';
            var SELECTOR    = 'button[data-baseweb="tab"]';

            function restoreTab(tabs) {
                var saved = parseInt(localStorage.getItem(STORAGE_KEY) || '0', 10);
                if (saved > 0 && tabs[saved]) {
                    setTimeout(function() { tabs[saved].click(); }, 80);
                }
                tabs.forEach(function(tab, idx) {
                    tab.addEventListener('click', function() {
                        localStorage.setItem(STORAGE_KEY, idx);
                    });
                });
            }

            function init() {
                var tabs = Array.from(window.parent.document.querySelectorAll(SELECTOR));
                var pgTabs = tabs.slice(0, 3);
                if (pgTabs.length === 3) {
                    restoreTab(pgTabs);
                } else {
                    setTimeout(init, 100);
                }
            }

            window.addEventListener('load', function() { setTimeout(init, 150); });
        })();
        </script>
        """, height=0)

        tab1, tab2, tab3 = st.tabs([
            ":material/overview: Overview per Purchasing Group",
            ":material/sell: Breakdown per Metode Tender",
            ":material/speed: Kecepatan Proses"
        ])

        # ══════════════════════════════════════════════════════════════════════
        # TAB 1: OVERVIEW PER PURCHASING GROUP
        # ══════════════════════════════════════════════════════════════════════
        with tab1:

            pg_query = f"""
            SELECT
                COALESCE(purchasing_group, 'Unassigned')                             AS purchasing_group,
                COUNT(DISTINCT CASE WHEN no_pr != 'No PR' AND {bagian_pr_cond}
                    THEN no_pr || '-' || line_item_pr::text END)                     AS jml_item_pr,
                COUNT(DISTINCT CASE WHEN nomor_po IS NOT NULL AND {bagian_po_cond}
                    THEN nomor_po || '-' || item_po::text END)                       AS jml_item_po,
                COUNT(DISTINCT CASE WHEN nomor_po IS NOT NULL AND no_pr != 'No PR' AND {bagian_pr_cond}
                    THEN no_pr || '-' || line_item_pr::text END)                     AS pr_with_po,
                COALESCE(SUM(CASE WHEN {bagian_pr_cond} THEN oe ELSE 0 END), 0)     AS nilai_oe,
                COALESCE(SUM(CASE WHEN {bagian_po_cond}
                    THEN total_amount_local_curr ELSE 0 END), 0)                     AS nilai_po,
                COALESCE(SUM(CASE WHEN {bagian_pr_cond} THEN oe ELSE 0 END), 0)
                    - COALESCE(SUM(CASE WHEN {bagian_po_cond}
                    THEN total_amount_local_curr ELSE 0 END), 0)                     AS efisiensi,
                CASE
                    WHEN COALESCE(SUM(CASE WHEN {bagian_pr_cond} THEN oe ELSE 0 END), 0) > 0
                    THEN ROUND(
                        (COALESCE(SUM(CASE WHEN {bagian_pr_cond} THEN oe ELSE 0 END), 0)
                         - COALESCE(SUM(CASE WHEN {bagian_po_cond}
                           THEN total_amount_local_curr ELSE 0 END), 0))
                        / COALESCE(SUM(CASE WHEN {bagian_pr_cond} THEN oe ELSE 0 END), 0) * 100,
                        1)
                    ELSE NULL
                END                                                                  AS efisiensi_pct,
                ROUND(AVG(CASE WHEN {bagian_po_cond} AND lead_time_process_po IS NOT NULL
                    THEN lead_time_process_po END)::numeric, 1)                      AS avg_lead_time,
                MIN(CASE WHEN {bagian_po_cond} AND lead_time_process_po IS NOT NULL
                    THEN lead_time_process_po END)                                   AS min_lead_time,
                MAX(CASE WHEN {bagian_po_cond} AND lead_time_process_po IS NOT NULL
                    THEN lead_time_process_po END)                                   AS max_lead_time
            FROM vw_pr_po_complete
            WHERE {filter_conditions}
            GROUP BY COALESCE(purchasing_group, 'Unassigned')
            ORDER BY nilai_oe DESC
            """

            with st.spinner("Memuat data per Purchasing Group..."):
                pg_data = load_data(pg_query)

            if not pg_data.empty:
                # ── Tabel Ringkasan ───────────────────────────────────────────
                st.markdown("""
                    <h1 style='display: flex; align-items: center; font-size:22px;'>
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-table" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                            <path d="M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2zm15 2h-4v3h4zm0 4h-4v3h4zm0 4h-4v3h3a1 1 0 0 0 1-1zm-5 3v-3H6v3zm-5 0v-3H1v2a1 1 0 0 0 1 1zm-4-4h4V8H1zm0-4h4V4H1zm5-3v3h4V4zm4 4H6v3h4z"/>
                        </svg>
                        Tabel Ringkasan per Purchasing Group
                    </h1>
                """, unsafe_allow_html=True)

                df_table = pg_data.copy()
                df_table['konversi_pct'] = (
                    df_table['pr_with_po'] / df_table['jml_item_pr'].replace(0, float('nan')) * 100
                ).round(1).fillna(0)
                df_table['efisiensi_pct'] = df_table['efisiensi_pct'].fillna(0)

                df_display = df_table.copy()
                df_display['jml_item_pr']  = df_display['jml_item_pr'].apply(format_number)
                df_display['jml_item_po']  = df_display['jml_item_po'].apply(format_number)
                df_display['nilai_oe']     = df_display['nilai_oe'].apply(format_currency) # Ganti jadi format_currency jika tidak ingin ada T/M/Jt
                df_display['nilai_po']     = df_display['nilai_po'].apply(format_currency)
                df_display['efisiensi']    = df_display['efisiensi'].apply(format_currency)
                df_display['efisiensi_pct']= df_display['efisiensi_pct'].apply(lambda x: f"{format_number(x, decimals=1)}%")
                df_display['avg_lead_time']= df_display['avg_lead_time'].apply(
                    lambda x: f"{format_number(x, decimals=1)} Hari" if pd.notna(x) else "N/A")
                df_display['min_lead_time']= df_display['min_lead_time'].apply(
                    lambda x: f"{format_number(x)} Hari" if pd.notna(x) else "N/A")
                df_display['max_lead_time']= df_display['max_lead_time'].apply(
                    lambda x: f"{format_number(x)} Hari" if pd.notna(x) else "N/A")
                df_display['konversi_pct'] = df_display['konversi_pct'].apply(lambda x: f"{format_number(x, decimals=1)}%")

                st.dataframe(
                    df_display.rename(columns={
                        'purchasing_group': 'Purchasing Group',
                        'jml_item_pr'     : 'Item PR',
                        'jml_item_po'     : 'Item PO',
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

                # ── Row 1: Nilai OE vs PO + Efisiensi % ──────────────────────
                col1, col2 = st.columns(2)

                with col1:
                    title_col, btn_col = st.columns([9, 1])
                    with title_col:
                        st.markdown("""
                            <h1 style='display: flex; align-items: center; font-size:22px;'>
                                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-table" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                                    <path d="M1 3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1zm7 8a2 2 0 1 0 0-4 2 2 0 0 0 0 4"/>
                                    <path d="M0 5a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H1a1 1 0 0 1-1-1zm3 0a2 2 0 0 1-2 2v4a2 2 0 0 1 2 2h10a2 2 0 0 1 2-2V7a2 2 0 0 1-2-2z"/>
                                </svg>
                                Perbandingan Nilai OE vs Realisasi PO
                            </h1>
                        """, unsafe_allow_html=True)
                    with btn_col:
                        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                        key_val = "show_formula_pg_val"
                        if key_val not in st.session_state:
                            st.session_state[key_val] = False
                        is_open = st.session_state[key_val]
                        icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                        tooltip = "Hide Formula" if is_open else "Show Formula"
                        st.button(icon, key=f"btn_{key_val}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_val})

                    if st.session_state.get(key_val, False):
                        st.info("""\
**Perbandingan Nilai OE vs Realisasi PO**: Grouped bar chart perbandingkan estimasi anggaran (OE) vs realisasi PO per Purchasing Group.

**Kalkulasi SQL:**
| Metrik | Formula |
|---|---|
| Nilai OE | `SUM(estimasi_pr × quantity_pr)` |
| Nilai Realisasi | `SUM(total_amount_local_curr)` |
| Efisiensi | `Nilai OE − Nilai Realisasi` |

**Formula Excel:**
- Kolom **OE**: `= Estimasi_PR × Qty_PR`
- Kolom **Efisiensi**: `= OE − Total_Amount_in_Local_Curr`
- Lalu `=SUMIF(kolom_pg, nama_pg, kolom_oe)` dan `=SUMIF(kolom_pg, nama_pg, kolom_realisasi)`

**Cara membaca:** Bar Realisasi (biru) **lebih pendek** dari OE (oranye) = ada penghematan ✅. Lebih panjang = over budget ❌.
                        """)

                    st.caption("Perbandingkan estimasi anggaran (OE) vs realisasi PO per Purchasing Group")

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
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        separators=",."
                    )
                    st.plotly_chart(fig_val, use_container_width=True)

                with col2:
                    title_col, btn_col = st.columns([9, 1])
                    with title_col:
                        st.markdown("""
                            <h1 style='display: flex; align-items: center; font-size:22px;'>
                                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-table" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                                    <path d="M6.5 1A1.5 1.5 0 0 0 5 2.5V3H1.5A1.5 1.5 0 0 0 0 4.5v1.384l7.614 2.03a1.5 1.5 0 0 0 .772 0L16 5.884V4.5A1.5 1.5 0 0 0 14.5 3H11v-.5A1.5 1.5 0 0 0 9.5 1h-3zm0 1h3a.5.5 0 0 1 .5.5V3H6v-.5a.5.5 0 0 1 .5-.5z"/>
                                    <path d="M0 12.5A1.5 1.5 0 0 0 1.5 14h13a1.5 1.5 0 0 0 1.5-1.5V6.85L8.129 8.947a.5.5 0 0 1-.258 0L0 6.85v5.65z"/>
                                </svg>
                                % Efisiensi per Purchasing Group
                            </h1>
                        """, unsafe_allow_html=True)
                    with btn_col:
                        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                        key_efis = "show_formula_pg_efis"
                        if key_efis not in st.session_state:
                            st.session_state[key_efis] = False
                        is_open = st.session_state[key_efis]
                        icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                        tooltip = "Hide Formula" if is_open else "Show Formula"
                        st.button(icon, key=f"btn_{key_efis}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_efis})

                    if st.session_state.get(key_efis, False):
                        st.info("""\
**% Efisiensi per Purchasing Group**: Bar chart horizontal persentase penghematan yang dicapai tiap Purchasing Group.

**Kalkulasi SQL:**
```sql
% Efisiensi = (SUM(oe) - SUM(total_amount_local_curr))
            / NULLIF(SUM(oe), 0) * 100
```

**Formula Excel (kolom % Efisiensi):**
```
= (OE - Total_Amount) / OE
```
Format cell sebagai **persentase (%)**.

**Interpretasi warna:**
- 🟢 **Positif** = realisasi di bawah anggaran → Purchasing Group berhasil hemat
- 🔴 **Negatif** = realisasi melebihi anggaran → Purchasing Group over budget

Semakin tinggi %, semakin besar penghematan yang dicapai Purchasing Group tersebut.
                        """)

                    st.caption("Persentase penghematan yang dicapai tiap Purchasing Group.")

                    pg_efis = pg_data[pg_data['efisiensi_pct'].notna()].copy()
                    pg_efis['warna'] = pg_efis['efisiensi_pct'].apply(
                        lambda x: '#2ca02c' if x >= 0 else '#d62728')
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
                        coloraxis_showscale=False,
                        xaxis_title="% Efisiensi (positif = hemat, negatif = over budget)"
                    )
                    st.plotly_chart(fig_efis, use_container_width=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # ── Row 2: Lead Time ──────────────────────────────────────────
                col1, col2 = st.columns(2)

                with col1:
                    title_col, btn_col = st.columns([9, 1])
                    with title_col:
                        st.markdown("""
                            <h1 style='display: flex; align-items: center; font-size:22px;'>
                                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-table" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                                    <path d="M6 .5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1H9v1.07a7.001 7.001 0 0 1 3.274 12.474l.601.602a.5.5 0 0 1-.707.708l-.746-.746A6.97 6.97 0 0 1 8 16a6.97 6.97 0 0 1-3.422-.892l-.746.746a.5.5 0 0 1-.707-.708l.602-.602A7.001 7.001 0 0 1 7 2.07V1h-.5A.5.5 0 0 1 6 .5m2.5 5a.5.5 0 0 0-1 0v3.362l-1.429 2.38a.5.5 0 1 0 .858.515l1.5-2.5A.5.5 0 0 0 8.5 9zM.86 5.387A2.5 2.5 0 1 1 4.387 1.86 8.04 8.04 0 0 0 .86 5.387M11.613 1.86a2.5 2.5 0 1 1 3.527 3.527 8.04 8.04 0 0 0-3.527-3.527"/>
                                </svg>
                                Rata-rata Lead Time per Purchasing Group
                            </h1>
                        """, unsafe_allow_html=True)
                    with btn_col:
                        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                        key_lt = "show_formula_pg_lt"
                        if key_lt not in st.session_state:
                            st.session_state[key_lt] = False
                        is_open = st.session_state[key_lt]
                        icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                        tooltip = "Hide Formula" if is_open else "Show Formula"
                        st.button(icon, key=f"btn_{key_lt}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_lt})

                    if st.session_state.get(key_lt, False):
                        st.info("""\
**Rata-rata Lead Time per Purchasing Group**: Bar chart horizontal rata-rata waktu proses PR→PO per Purchasing Group.

**Kalkulasi SQL:**
```sql
AVG(lead_time_process_po) per purchasing_group
```

**Sumber kolom `lead_time_process_po`:**
Dihitung sebagai selisih hari antara `tgl_create_pr` (PR dibuat di SAP) dan `date_ordered` (tanggal PO diterbitkan).

Di Excel: `= date_ordered - tgl_create_pr` per baris → `=AVERAGEIF(kolom_pg, nama_pg, kolom_lead_time)`.

**Target:** Garis merah putus-putus = **55 hari**. Purchasing Group yang melampaui garis ini perlu evaluasi alur proses pengadaannya.
                        """)

                    st.caption("Rata-rata waktu proses PR→PO per Purchasing Group.")

                    pg_lt = pg_data[pg_data['avg_lead_time'].notna()].copy()
                    pg_lt['warna'] = pg_lt['avg_lead_time'].apply(
                        lambda x: '#2ca02c' if x <= 55 else '#d62728')
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
                    fig_lt.update_layout(height=400, coloraxis_showscale=False)
                    st.plotly_chart(fig_lt, use_container_width=True)

                with col2:
                    title_col, btn_col = st.columns([9, 1])
                    with title_col:
                        st.markdown("""
                            <h1 style='display: flex; align-items: center; font-size:22px;'>
                                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-table" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                                    <path fill-rule="evenodd" d="M8 3a5 5 0 1 0 4.546 2.914.5.5 0 0 1 .908-.417A6 6 0 1 1 8 2z"/>
                                    <path d="M8 4.466V.534a.25.25 0 0 1 .41-.192l2.36 1.966c.12.1.12.284 0 .384L8.41 4.658A.25.25 0 0 1 8 4.466"/>
                                </svg>
                                % Konversi PR → PO per Purchasing Group
                            </h1>
                        """, unsafe_allow_html=True)
                    with btn_col:
                        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                        key_konv = "show_formula_pg_konv"
                        if key_konv not in st.session_state:
                            st.session_state[key_konv] = False
                        is_open = st.session_state[key_konv]
                        icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                        tooltip = "Hide Formula" if is_open else "Show Formula"
                        st.button(icon, key=f"btn_{key_konv}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_konv})

                    if st.session_state.get(key_konv, False):
                        st.info("""\
**% Konversi PR → PO per Purchasing Group**: Bar chart horizontal persentase PR yang berhasil dikonversi menjadi PO.

**Kalkulasi SQL:**
```sql
% Konversi = COUNT(DISTINCT no_pr yang memiliki nomor_po)
           / COUNT(DISTINCT total no_pr)
           × 100
```

PR dianggap "sudah PO" jika setidaknya satu baris di `vw_pr_po_complete` memiliki `nomor_po IS NOT NULL`.

Di Excel:
```
= COUNTIFS(kolom_no_pr, no_pr_x, kolom_nomor_po, "<>")
/ COUNTIF(kolom_no_pr, no_pr_x)
```

**Cara membaca:**
- % **tinggi** (mendekati 100%) = hampir semua PR sudah diproses menjadi PO ✅
- % **rendah** = banyak PR tertahan/pending → perlu investigasi penyebab (kekurangan dokumen, anggaran, dll)
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
                    fig_konv.update_layout(height=400, coloraxis_showscale=False)
                    st.plotly_chart(fig_konv, use_container_width=True)

            else:
                st.info("Tidak ada data kinerja Purchasing Group pada rentang waktu ini.")

        # ══════════════════════════════════════════════════════════════════════
        # TAB 2: BREAKDOWN KONTRAK & TURN AROUND
        # ══════════════════════════════════════════════════════════════════════
        with tab2:
            st.markdown("Breakdown pengadaan berdasarkan **jenis tender** dan **Turn Around**.")
            
            col1, col2 = st.columns(2)

            # ── Kiri: Breakdown Kontrak vs Non-Kontrak ────────────────────
            with col1:
                title_col, btn_col = st.columns([9, 1])
                with title_col:
                    st.markdown("""
                            <h1 style='display: flex; align-items: center; font-size:22px;'>
                                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-table" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                                    <path d="M9.293 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4.707A1 1 0 0 0 13.707 4L10 .293A1 1 0 0 0 9.293 0M9.5 3.5v-2l3 3h-2a1 1 0 0 1-1-1M4.5 9a.5.5 0 0 1 0-1h7a.5.5 0 0 1 0 1zM4 10.5a.5.5 0 0 1 .5-.5h7a.5.5 0 0 1 0 1h-7a.5.5 0 0 1-.5-.5m.5 2.5a.5.5 0 0 1 0-1h4a.5.5 0 0 1 0 1z"/>
                                </svg>
                                Kontrak vs Non-Kontrak per Purchasing Group
                            </h1>
                    """, unsafe_allow_html=True)
                with btn_col:
                    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                    key_kontrak = "show_formula_pg_kontrak"
                    if key_kontrak not in st.session_state:
                        st.session_state[key_kontrak] = False
                    is_open = st.session_state[key_kontrak]
                    icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                    tooltip = "Hide Formula" if is_open else "Show Formula"
                    st.button(icon, key=f"btn_{key_kontrak}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_kontrak})

                if st.session_state.get(key_kontrak, False):
                    st.info("""\
**Kontrak vs Non-Kontrak per Purchasing Group**: Stacked bar chart komposisi nilai realisasi berdasarkan jenis tender per Purchasing Group.

**Kalkulasi `jenis_tender` di `vw_pr_po_complete`:**
```sql
CASE
  WHEN LEFT(contract_no, 1) = '4' THEN 'PR - PO Kontrak'
  ELSE 'Tender Normal'
END
```
Dihitung dari No. Contract: diawali angka '4' = PR - PO Kontrak, selainnya = Tender Normal.

**Formula Excel (kolom Jenis Tender):**
```
= IF(LEFT(contract_no, 1) = "4", "PR - PO Kontrak", "Tender Normal")
```

**Perbedaan kedua jenis:**
| Jenis | Karakteristik |
|---|---|
| PR - PO Kontrak | Menggunakan kontrak yang sudah ada → lebih cepat, harga lebih stabil |
| Tender Normal | Proses penawaran/negosiasi baru setiap transaksi → biasanya lebih lama |
                    """)

                st.caption("Komposisi nilai realisasi berdasarkan jenis tender per Purchasing Group.")

                kontrak_query = f"""
                SELECT
                    COALESCE(purchasing_group, 'Unassigned')              AS purchasing_group,
                    jenis_tender                                           AS jenis_kontrak,
                    COUNT(DISTINCT CASE WHEN {bagian_po_cond}
                        THEN nomor_po || '-' || item_po::text END)         AS jml_item,
                    COALESCE(SUM(CASE WHEN {bagian_po_cond}
                        THEN total_amount_local_curr ELSE 0 END), 0)       AS total_realisasi,
                    ROUND(AVG(CASE WHEN {bagian_po_cond} AND lead_time_process_po IS NOT NULL
                        THEN lead_time_process_po END)::numeric, 1)        AS avg_lead_time
                FROM vw_pr_po_complete
                WHERE {filter_conditions}
                  AND nomor_po IS NOT NULL
                GROUP BY COALESCE(purchasing_group, 'Unassigned'),
                         jenis_tender
                ORDER BY purchasing_group, jenis_kontrak
                """
                with st.spinner("Memuat data kontrak..."):
                    kontrak_data = load_data(kontrak_query)

                if not kontrak_data.empty:
                    # Ringkasan global
                    kontrak_sum = kontrak_data.groupby('jenis_kontrak').agg(
                        jml_item       =('jml_item',        'sum'),
                        total_realisasi=('total_realisasi', 'sum'),
                        avg_lead_time  =('avg_lead_time',   'mean')
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

                    # Chart stacked bar
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
                        legend=dict(orientation="h", yanchor="bottom", y=1.02)
                    )
                    st.plotly_chart(fig_k, use_container_width=True)

                    # Lead time kontrak vs non-kontrak per Purchasing Group
                    title_col, btn_col = st.columns([9, 1])
                    with title_col:
                        st.markdown("""
                            <h1 style='display: flex; align-items: center; font-size:22px;'>
                                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-table" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                                    <path d="M6 .5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1H9v1.07a7.001 7.001 0 0 1 3.274 12.474l.601.602a.5.5 0 0 1-.707.708l-.746-.746A6.97 6.97 0 0 1 8 16a6.97 6.97 0 0 1-3.422-.892l-.746.746a.5.5 0 0 1-.707-.708l.602-.602A7.001 7.001 0 0 1 7 2.07V1h-.5A.5.5 0 0 1 6 .5m2.5 5a.5.5 0 0 0-1 0v3.362l-1.429 2.38a.5.5 0 1 0 .858.515l1.5-2.5A.5.5 0 0 0 8.5 9zM.86 5.387A2.5 2.5 0 1 1 4.387 1.86 8.04 8.04 0 0 0 .86 5.387M11.613 1.86a2.5 2.5 0 1 1 3.527 3.527 8.04 8.04 0 0 0-3.527-3.527"/>
                                </svg>
                                Lead Time: Kontrak vs Non-Kontrak
                            </h1>
                        """, unsafe_allow_html=True)
                    with btn_col:
                        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                        key_lt_kontrak = "show_formula_pg_lt_kontrak"
                        if key_lt_kontrak not in st.session_state:
                            st.session_state[key_lt_kontrak] = False
                        is_open = st.session_state[key_lt_kontrak]
                        icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                        tooltip = "Hide Formula" if is_open else "Show Formula"
                        st.button(icon, key=f"btn_{key_lt_kontrak}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_lt_kontrak})

                    if st.session_state.get(key_lt_kontrak, False):
                        st.info("""\
**Lead Time: Kontrak vs Non-Kontrak per Purchasing Group**: Grouped bar chart rata-rata lead time per jenis tender per Purchasing Group.

**Kalkulasi SQL:**
```sql
AVG(lead_time_process_po)
GROUP BY purchasing_group, jenis_tender
```

**Ekspektasi umum:**
- **PR - PO Kontrak** → lead time **lebih pendek**: vendor & harga sudah disepakati di awal kontrak, tidak perlu proses negosiasi ulang
- **Tender Normal** → lead time **lebih panjang**: perlu tahap penawaran, evaluasi vendor, dan negosiasi harga

Jika Tender Normal di suatu Purchasing Group jauh di atas target, pertimbangkan untuk mengonversi material yang sering dipesan ke skema kontrak.

**Target:** Garis merah putus-putus = **55 hari**.
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
                        legend=dict(orientation="h", yanchor="bottom", y=1.02)
                    )
                    st.plotly_chart(fig_klt, use_container_width=True)
                else:
                    st.info("Tidak ada data kontrak pada periode ini.")

            # ── Kanan: Breakdown Turn Around ─────────────────────────────
            with col2:
                title_col, btn_col = st.columns([9, 1])
                with title_col:
                    st.markdown("""
                            <h1 style='display: flex; align-items: center; font-size:22px;'>
                                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-table" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                                    <path d="M11.251.068a.5.5 0 0 1 .227.58L9.677 6.5H13a.5.5 0 0 1 .364.843l-8 8.5a.5.5 0 0 1-.842-.49L6.323 9.5H3a.5.5 0 0 1-.364-.843l8-8.5a.5.5 0 0 1 .615-.09z"/>
                                </svg>
                                Distribusi Turn Around per Purchasing Group
                            </h1>
                    """, unsafe_allow_html=True)
                with btn_col:
                    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                    key_ta = "show_formula_pg_ta"
                    if key_ta not in st.session_state:
                        st.session_state[key_ta] = False
                    is_open = st.session_state[key_ta]
                    icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                    tooltip = "Hide Formula" if is_open else "Show Formula"
                    st.button(icon, key=f"btn_{key_ta}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_ta})

                if st.session_state.get(key_ta, False):
                    st.info("""\
**Distribusi Turn Around per Purchasing Group**: Komposisi item PO berdasarkan kategori Turn Around (TA vs non-TA).

**Kalkulasi `turn_around_calc` di `vw_pr_po_complete`:**
```sql
CASE
  WHEN LEFT(department_code, 2) = 'TA' THEN 'TA'
  ELSE 'non'
END
```
**Turn Around** dikalkulasi dari department_code: diawali 'TA' = Turn Around.

**Formula Excel (kolom Turn Around):**
```
= IF(LEFT(Department, 2) = "TA", "TA", "non")
```

**Penjelasan kategori:**
| Kategori | Keterangan |
|---|---|
| TA | Turn Around, pemeliharaan besar/shutdown pabrik periodik. Volume pengadaan tinggi dalam waktu singkat. |
| non | Operasional rutin harian |

Purchasing Group dengan proporsi TA tinggi memiliki karakteristik pengadaan berbeda dari Purchasing Group operasional, wajar jika lead time-nya lebih ketat.
                    """)
            
                st.caption("Komposisi item PO berdasarkan kategori Turn Around (TA vs non-TA).")

                ta_query = f"""
                SELECT
                    COALESCE(purchasing_group, 'Unassigned')              AS purchasing_group,
                    turn_around_calc                                       AS turn_around,
                    COUNT(DISTINCT CASE WHEN {bagian_po_cond}
                        THEN nomor_po || '-' || item_po::text END)         AS jml_item,
                    COALESCE(SUM(CASE WHEN {bagian_po_cond}
                        THEN total_amount_local_curr ELSE 0 END), 0)       AS total_realisasi,
                    ROUND(AVG(CASE WHEN {bagian_po_cond} AND lead_time_process_po IS NOT NULL
                        THEN lead_time_process_po END)::numeric, 1)        AS avg_lead_time
                FROM vw_pr_po_complete
                WHERE {filter_conditions}
                  AND nomor_po IS NOT NULL
                GROUP BY COALESCE(purchasing_group, 'Unassigned'),
                         turn_around_calc
                ORDER BY purchasing_group, jml_item DESC
                """
                with st.spinner("Memuat data turn around..."):
                    ta_data = load_data(ta_query)

                if not ta_data.empty:
                    # Ringkasan global per kategori turn around
                    ta_sum = ta_data.groupby('turn_around').agg(
                        jml_item       =('jml_item',        'sum'),
                        total_realisasi=('total_realisasi', 'sum'),
                        avg_lead_time  =('avg_lead_time',   'mean')
                    ).reset_index().sort_values('jml_item', ascending=False)

                    # Pie chart distribusi item per turn around
                    fig_ta_pie = px.pie(
                        ta_sum,
                        values='jml_item',
                        names='turn_around',
                        hole=0.4,
                        title="Distribusi Jumlah Item per Turn Around"
                    )
                    fig_ta_pie.update_layout(height=320)
                    st.plotly_chart(fig_ta_pie, use_container_width=True)

                    # Bar chart lead time per turn around
                    ta_lt = ta_sum[ta_sum['avg_lead_time'].notna()].copy()
                    ta_lt['avg_lead_time'] = ta_lt['avg_lead_time'].round(1)
                    ta_lt['label'] = ta_lt['avg_lead_time'].apply(lambda x: f"{x} Hr")
                    ta_lt = ta_lt.sort_values('avg_lead_time')
                    fig_ta_lt = px.bar(
                        ta_lt,
                        x='avg_lead_time', y='turn_around',
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
                    fig_ta_lt.update_layout(height=350, coloraxis_showscale=False)
                    st.plotly_chart(fig_ta_lt, use_container_width=True)

                    # Tabel detail
                    st.markdown("""
                        <h1 style='display: flex; align-items: center; font-size:22px;'>
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-table" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
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
                        use_container_width=True, height=300
                    )
                else:
                    st.info("Tidak ada data turn around pada periode ini.")

            # Download gabungan
            if not kontrak_data.empty:
                st.markdown("---")
                csv_k = kontrak_data.to_csv(index=False)
                st.download_button(
                    label="Download Data Kontrak sebagai CSV",
                    icon=":material/download:",
                    data=csv_k,
                    file_name=f"breakdown_kontrak_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )

        # ══════════════════════════════════════════════════════════════════════
        # TAB 3: KECEPATAN PROSES OVERALL, TENDER NORMAL VS KONTRAK
        # ══════════════════════════════════════════════════════════════════════
        with tab3:
            st.markdown("Analisis kecepatan waktu proses pengadaan secara keseluruhan, perbandingan antara **Tender Normal** dan **PR-PO Kontrak**, serta distribusi lead time per Purchasing Group.")

            # KPI Kecepatan
            speed_kpi_query = f"""
            SELECT
                ROUND(AVG(lead_time_process_po)::numeric, 1)                          AS avg_lt_overall,
                ROUND(MIN(lead_time_process_po)::numeric, 0)                          AS min_lt,
                ROUND(MAX(lead_time_process_po)::numeric, 0)                          AS max_lt,
                ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP
                    (ORDER BY lead_time_process_po)::numeric, 1)                      AS median_lt,
                COUNT(CASE WHEN lead_time_process_po <= 55 THEN 1 END)                AS jml_ontime,
                COUNT(CASE WHEN lead_time_process_po > 55 THEN 1 END)                 AS jml_late,
                COUNT(lead_time_process_po)                                            AS total_lt
            FROM vw_pr_po_complete
            WHERE {filter_conditions}
              AND nomor_po IS NOT NULL
              AND lead_time_process_po IS NOT NULL
              AND {bagian_po_cond}
            """

            with st.spinner("Memuat KPI kecepatan..."):
                speed_kpi = load_data(speed_kpi_query)

            if not speed_kpi.empty and speed_kpi['total_lt'][0]:
                avg_lt     = float(speed_kpi['avg_lt_overall'][0] or 0)
                med_lt     = float(speed_kpi['median_lt'][0] or 0)
                min_lt     = int(speed_kpi['min_lt'][0] or 0)
                max_lt     = int(speed_kpi['max_lt'][0] or 0)
                ontime     = int(speed_kpi['jml_ontime'][0] or 0)
                late       = int(speed_kpi['jml_late'][0] or 0)
                total      = int(speed_kpi['total_lt'][0] or 1)
                ontime_pct = ontime / total * 100

                if ontime_pct >= 80:
                    color_class = "green"
                    d_color = "normal"   # Biarkan hijau bawaan
                elif 60 <= ontime_pct < 80:
                    color_class = "orange"
                    d_color = "off"      # Matikan warna bawaan agar CSS kita masuk
                else:
                    color_class = "red"
                    d_color = "inverse"  # Biarkan merah bawaan

                SPEED_KPI = [
                    {
                        "key": "kpi_speed_median",
                        "metric_args": ("Median Lead Time", f"{format_number(med_lt, decimals=1)} Hari"),
                        "metric_kwargs": {},
                        "formula": """\
**Median Lead Time**: Nilai tengah dari seluruh distribusi lead time PO dalam periode filter.

**Kalkulasi SQL:**
```sql
ROUND(
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY lead_time_process_po)::numeric,
1) AS median_lt
```

**Mengapa median, bukan rata-rata?**

| Metrik | Sifat |
|---|---|
| **Rata-rata (AVG)** | Mudah terpengaruh outlier, satu PO dengan lead time 500 hari bisa menarik rata-rata jauh ke atas |
| **Median** | Nilai yang tepat di tengah data, 50% PO selesai lebih cepat, 50% lebih lambat |

Jika median jauh lebih rendah dari rata-rata, berarti ada sejumlah kecil PO dengan lead time ekstrem yang mendistorsi gambaran keseluruhan. Gunakan median sebagai ukuran "kecepatan tipikal" proses pengadaan.
"""
                    },
                    {
                        "key": "kpi_speed_rentang",
                        "metric_args": ("Rentang Lead Time", f"{format_number(min_lt)} - {format_number(max_lt)} Hari"),
                        "metric_kwargs": {},
                        "formula": """\
**Rentang Lead Time**: Selisih antara lead time terpendek dan terpanjang dalam periode filter.

**Kalkulasi SQL:**
```sql
ROUND(MIN(lead_time_process_po)::numeric, 0) AS min_lt,
ROUND(MAX(lead_time_process_po)::numeric, 0) AS max_lt
```

**Cara membaca:**
- **Rentang sempit** (mis. 5-30 hari) → proses pengadaan konsisten dan terprediksi
- **Rentang lebar** (mis. 0-500 hari) → ada variabilitas tinggi, perlu investigasi outlier

**Penyebab umum rentang sangat lebar:**
- PO kontrak (cepat) vs tender terbuka (lama) dalam satu periode
- PR darurat vs pengadaan rutin
- Kendala dokumen / approval yang berlarut-larut pada sebagian PO

Filter: hanya baris dengan `nomor_po IS NOT NULL AND lead_time_process_po IS NOT NULL`
"""
                    },
                    {
                        "key": "kpi_speed_ontime",
                        "metric_args": ("On-Time (<=55 Hari)", f"{format_number(ontime)}"),
                        "metric_kwargs": {
                            "delta": f"{format_number(ontime_pct, decimals=1)}% dari total",
                            "delta_color": d_color
                        },
                        "formula": """\
**On-Time (≤55 Hari)**: Jumlah PO yang berhasil diproses dalam batas SLA 55 hari.

**Kalkulasi SQL:**
```sql
COUNT(CASE WHEN lead_time_process_po <= 55 THEN 1 END) AS jml_ontime
```

**% dari total** = `jml_ontime / total_lt × 100`

**Target SLA = 55 hari** dihitung dari tanggal PR dibuat (`tgl_create_pr`) hingga tanggal PO diterbitkan (`date_ordered`).

| % On-Time | Interpretasi |
|---|---|
| ≥ 80% | 🟢 Proses pengadaan berjalan baik |
| 60–79% | 🟡 Perlu perhatian, identifikasi bottleneck |
| < 60% | 🔴 Kritis, evaluasi menyeluruh diperlukan |

Untuk melihat distribusi lengkap per rentang waktu, lihat chart **Distribusi Lead Time Overall** di bawah.
"""
                    },
                    {
                        "key": "kpi_speed_late",
                        "metric_args": ("Terlambat (>55 Hari)", f"{format_number(late)}"),
                        "metric_kwargs": {
                            "delta": f"{format_number(100-ontime_pct, decimals=1)}% dari total",
                            "delta_color": d_color
                        },
                        "formula": """\
**Terlambat (>55 Hari)**: Jumlah PO yang melebihi batas SLA 55 hari.

**Kalkulasi SQL:**
```sql
COUNT(CASE WHEN lead_time_process_po > 55 THEN 1 END) AS jml_late
```

**% dari total** = `jml_late / total_lt × 100`

**Penyebab umum keterlambatan:**
- Proses approval PR yang panjang (multi-level signatory)
- Tender/lelang yang memerlukan waktu lama (>30 hari)
- Vendor tidak responsif atau dokumen tidak lengkap
- PO lintas departemen dengan koordinasi rumit

**Tindak lanjut yang disarankan:**
1. Drill-down ke tabel **Ringkasan Kecepatan per PG** di bawah untuk identifikasi PG dengan % terlambat tertinggi
2. Bandingkan lead time kontrak vs tender di tab **Breakdown per Metode Tender**
3. Cek chart **Tren Lead Time per Bulan** untuk melihat apakah keterlambatan memburuk atau membaik
"""
                    }
                ]

                for kpi in SPEED_KPI:
                    if kpi["key"] not in st.session_state:
                        st.session_state[kpi["key"]] = False

                speed_cols = st.columns(len(SPEED_KPI))
                for col, kpi in zip(speed_cols, SPEED_KPI):
                    with col:
                        m_col, btn_col = st.columns([5, 1])
                        with m_col:
                            st.metric(
                                label=kpi["metric_args"][0], 
                                value=kpi["metric_args"][1], 
                                delta=kpi["metric_kwargs"].get("delta"),
                                delta_color=d_color
                            )
                        with btn_col:
                            st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
                            is_open = st.session_state[kpi["key"]]
                            icon = ":material/visibility_off:" if is_open else ":material/visibility:"

                            tooltip = "Hide Formula" if is_open else "Show Formula"
                            
                            st.button(
                                icon, 
                                key=f"btn_{kpi['key']}", 
                                help=tooltip,
                                on_click=toggle_state, 
                                kwargs={"state_key": kpi["key"]}
                            )
                        # ── JS: paksa warna delta On-Time & Terlambat sesuai threshold ──
                # st.markdown('<div class="...">') tidak bisa membungkus st.metric()
                # karena setiap widget Streamlit dirender sebagai elemen DOM independen.
                # Satu-satunya cara reliable: JS langsung cari elemen via label teks.
                import streamlit.components.v1 as _comp
                _ontime_color = "#09ab3b" if ontime_pct >= 80 else ("#ffa500" if ontime_pct >= 60 else "#ff4b4b")
                _late_color   = _ontime_color
                _comp.html(f"""
                <script>
                (function() {{
                    function applyColors() {{
                        var doc    = window.parent.document;
                        var labels = doc.querySelectorAll('[data-testid="stMetricLabel"]');
                        var found  = 0;
                        labels.forEach(function(label) {{
                            var text = (label.innerText || label.textContent || "").trim();
                            var color = null;
                            if (text.indexOf("On-Time")   !== -1) color = "{_ontime_color}";
                            if (text.indexOf("Terlambat") !== -1) color = "{_late_color}";
                            if (!color) return;
                            var metric = label.closest('[data-testid="stMetric"]');
                            if (!metric) return;
                            var delta = metric.querySelector('[data-testid="stMetricDelta"]');
                            if (!delta) return;
                            // Set warna di semua elemen dalam delta (termasuk ikon panah)
                            [delta].concat(Array.from(delta.querySelectorAll("*"))).forEach(function(el) {{
                                el.style.setProperty("color", color, "important");
                                el.style.setProperty("-webkit-text-fill-color", color, "important");
                            }});
                            found++;
                        }});
                        // DOM belum siap, coba lagi
                        if (found < 2) setTimeout(applyColors, 150);
                    }}
                    // Jalankan saat load dan juga langsung (untuk handle rerun Streamlit)
                    setTimeout(applyColors, 250);
                    window.addEventListener("load", function() {{ setTimeout(applyColors, 250); }});
                }})();
                </script>
                """, height=0)

                for kpi in SPEED_KPI:
                    if st.session_state[kpi["key"]]:
                        st.info(kpi["formula"])

            st.markdown("---")

            # Row 1: Distribusi + Perbandingan Tender Normal vs Kontrak
            col1, col2 = st.columns(2)

            with col1:
                title_col, btn_col = st.columns([9, 1])
                with title_col:
                    st.markdown("""
                        <h1 style='display: flex; align-items: center; font-size:22px;'>
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                                <path d="M6 .5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1H9v1.07a7.001 7.001 0 0 1 3.274 12.474l.601.602a.5.5 0 0 1-.707.708l-.746-.746A6.97 6.97 0 0 1 8 16a6.97 6.97 0 0 1-3.422-.892l-.746.746a.5.5 0 0 1-.707-.708l.602-.602A7.001 7.001 0 0 1 7 2.07V1h-.5A.5.5 0 0 1 6 .5m2.5 5a.5.5 0 0 0-1 0v3.362l-1.429 2.38a.5.5 0 1 0 .858.515l1.5-2.5A.5.5 0 0 0 8.5 9zM.86 5.387A2.5 2.5 0 1 1 4.387 1.86 8.04 8.04 0 0 0 .86 5.387M11.613 1.86a2.5 2.5 0 1 1 3.527 3.527 8.04 8.04 0 0 0-3.527-3.527"/>
                            </svg>
                            Distribusi Lead Time Overall
                        </h1>
                    """, unsafe_allow_html=True)
                with btn_col:
                    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                    key_dist_lt = "show_formula_dist_lt"
                    if key_dist_lt not in st.session_state:
                        st.session_state[key_dist_lt] = False
                    is_open = st.session_state[key_dist_lt]
                    icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                    tooltip = "Hide Formula" if is_open else "Show Formula"
                    st.button(icon, key=f"btn_{key_dist_lt}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_dist_lt})

                if st.session_state.get(key_dist_lt, False):
                    st.info("""\
**Distribusi Lead Time Overall**: Bar chart jumlah PO per bucket rentang waktu proses, untuk semua Purchasing Group.

**Bucket klasifikasi SQL:**
```sql
CASE
  WHEN lead_time_process_po <= 14 THEN '≤14 Hari'
  WHEN lead_time_process_po <= 30 THEN '15–30 Hari'
  WHEN lead_time_process_po <= 55 THEN '31–55 Hari'
  WHEN lead_time_process_po <= 90 THEN '56–90 Hari'
  ELSE                                  '>90 Hari'
END
```

**Target SLA = 55 hari:**
| Bucket | Status |
|---|---|
| ≤55 Hari (Bucket 1–3) | 🟢 On Target |
| 56–90 Hari | 🟡 Perlu perhatian |
| >90 Hari | 🔴 Kritis |

Di Excel: `=IFS(lt<=14,"≤14",lt<=30,"15-30",lt<=55,"31-55",lt<=90,"56-90",TRUE,">90")`
                    """)

                st.caption("Jumlah PO per bucket rentang waktu proses, untuk semua Purchasing Group.")

                dist_query = f"""
                SELECT
                    CASE
                        WHEN lead_time_process_po <= 14  THEN '<=14 Hari'
                        WHEN lead_time_process_po <= 30  THEN '15-30 Hari'
                        WHEN lead_time_process_po <= 55  THEN '31-55 Hari'
                        WHEN lead_time_process_po <= 90  THEN '56-90 Hari'
                        ELSE                                  '>90 Hari'
                    END                    AS bucket,
                    COUNT(*)               AS jumlah,
                    MIN(lead_time_process_po) AS sort_key
                FROM vw_pr_po_complete
                WHERE {filter_conditions}
                  AND nomor_po IS NOT NULL
                  AND lead_time_process_po IS NOT NULL
                  AND {bagian_po_cond}
                GROUP BY 1
                ORDER BY sort_key
                """
                with st.spinner("Memuat distribusi..."):
                    dist_data = load_data(dist_query)

                if not dist_data.empty:
                    category_order = ['<=14 Hari', '15-30 Hari', '31-55 Hari', '56-90 Hari', '>90 Hari']
                    dist_data['bucket'] = pd.Categorical(
                        dist_data['bucket'], categories=category_order, ordered=True
                    )
                    dist_data = dist_data.sort_values('bucket')
                    color_map_dist = {
                        '<=14 Hari' : '#2ca02c',
                        '15-30 Hari': '#98df8a',
                        '31-55 Hari': '#ffdd57',
                        '56-90 Hari': '#ff7f0e',
                        '>90 Hari'  : '#d62728',
                    }
                    fig_dist = px.pie(
                        dist_data, 
                        values='jumlah', 
                        names='bucket', 
                        hole=0.4,
                        category_orders={'bucket': category_order},
                        color='bucket',
                        color_discrete_map=color_map_dist
                    )
                    fig_dist.update_traces(sort=False)
                    fig_dist.update_layout(height=400)
                    st.plotly_chart(fig_dist, use_container_width=True)
                else:
                    st.info("Tidak ada data distribusi lead time.")

            with col2:
                title_col, btn_col = st.columns([9, 1])
                with title_col:
                    st.markdown("""
                        <h1 style='display: flex; align-items: center; font-size:22px;'>
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-graph-up" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                                <path fill-rule="evenodd" d="M0 0h1v15h15v1H0zm14.817 3.113a.5.5 0 0 1 .07.704l-4.5 5.5a.5.5 0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5 0 0 1 .758-.06l2.609 2.61 4.15-5.073a.5.5 0 0 1 .704-.07"/>
                            </svg>
                            Lead Time: Tender Normal vs PR-PO Kontrak
                        </h1>
                    """, unsafe_allow_html=True)
                with btn_col:
                    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                    key_tender_lt = "show_formula_tender_lt"
                    if key_tender_lt not in st.session_state:
                        st.session_state[key_tender_lt] = False
                    is_open = st.session_state[key_tender_lt]
                    icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                    tooltip = "Hide Formula" if is_open else "Show Formula"
                    st.button(icon, key=f"btn_{key_tender_lt}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_tender_lt})

                if st.session_state.get(key_tender_lt, False):
                    st.info("""\
**Lead Time: Tender Normal vs PR-PO Kontrak**: Grouped bar chart perbandingan rata-rata waktu proses berdasarkan jenis tender per Purchasing Group., dilengkapi statistik median dan % on-time.

**Kalkulasi SQL:**
```sql
AVG(lead_time_process_po)   AS avg_lt
PERCENTILE_CONT(0.5) WITHIN GROUP
  (ORDER BY lead_time_process_po) AS median_lt
COUNT(CASE WHEN lead_time_process_po <= 55 THEN 1 END) AS jml_ontime
COUNT(CASE WHEN lead_time_process_po >  55 THEN 1 END) AS jml_late
GROUP BY purchasing_group, jenis_tender
```

**Mengapa ada Median di samping Average?**
Average bisa terdistorsi oleh satu outlier ekstrem (misal: satu PO terlupakan 500 hari). Median lebih representatif untuk menggambarkan lead time "tipikal" yang sesungguhnya dialami tim.

**Target:** Garis merah putus-putus = **55 hari**.
                    """)

                st.caption("Perbandingan rata-rata waktu proses berdasarkan jenis tender per Purchasing Group.")

                lt_tender_query = f"""
                SELECT
                    COALESCE(purchasing_group, 'Unassigned')                     AS purchasing_group,
                    jenis_tender,
                    COUNT(*)                                                      AS jml_po,
                    ROUND(AVG(lead_time_process_po)::numeric, 1)                 AS avg_lt,
                    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP
                        (ORDER BY lead_time_process_po)::numeric, 1)             AS median_lt,
                    COUNT(CASE WHEN lead_time_process_po <= 55 THEN 1 END)       AS jml_ontime,
                    COUNT(CASE WHEN lead_time_process_po > 55 THEN 1 END)        AS jml_late
                FROM vw_pr_po_complete
                WHERE {filter_conditions}
                  AND nomor_po IS NOT NULL
                  AND lead_time_process_po IS NOT NULL
                  AND {bagian_po_cond}
                GROUP BY COALESCE(purchasing_group, 'Unassigned'), jenis_tender
                ORDER BY purchasing_group, jenis_tender
                """
                with st.spinner("Memuat perbandingan tender..."):
                    lt_tender_data = load_data(lt_tender_query)

                if not lt_tender_data.empty:
                    fig_lt_tender = px.bar(
                        lt_tender_data,
                        x='purchasing_group', y='avg_lt',
                        color='jenis_tender', barmode='group',
                        text=lt_tender_data['avg_lt'].apply(lambda x: f"{x} Hr"),
                        color_discrete_map={
                            'PR - PO Kontrak': '#1f77b4',
                            'Tender Normal'  : '#ff7f0e'
                        },
                        labels={
                            'purchasing_group': 'Purchasing Group',
                            'avg_lt'          : 'Lead Time Avg (Hari)',
                            'jenis_tender'    : 'Jenis Tender'
                        }
                    )
                    fig_lt_tender.add_hline(y=55, line_dash="dash", line_color="red",
                                            annotation_text="Target 55 Hari",
                                            annotation_position="bottom right")
                    fig_lt_tender.update_traces(textposition='outside', textfont_size=9)
                    fig_lt_tender.update_layout(
                        height=400,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02)
                    )
                    st.plotly_chart(fig_lt_tender, use_container_width=True)
                else:
                    st.info("Tidak ada data perbandingan tender.")
                    lt_tender_data = pd.DataFrame()

            st.markdown("---")

            # Row 2: Tren per Bulan + Tabel Detail
            col1, col2 = st.columns(2)

            with col1:
                title_col, btn_col = st.columns([9, 1])
                with title_col:
                    st.markdown("""
                        <h1 style='display: flex; align-items: center; font-size:22px;'>
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-calendar-check" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                                <path d="M10.854 7.146a.5.5 0 0 1 0 .708l-3 3a.5.5 0 0 1-.708 0l-1.5-1.5a.5.5 0 1 1 .708-.708L7.5 9.793l2.646-2.647a.5.5 0 0 1 .708 0"/>
                                <path d="M3.5 0a.5.5 0 0 1 .5.5V1h8V.5a.5.5 0 0 1 1 0V1h1a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2h1V.5a.5.5 0 0 1 .5-.5M1 4v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V4z"/>
                            </svg>
                            Tren Lead Time per Bulan
                        </h1>
                    """, unsafe_allow_html=True)
                with btn_col:
                    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                    key_trend_lt = "show_formula_trend_lt"
                    if key_trend_lt not in st.session_state:
                        st.session_state[key_trend_lt] = False
                    is_open = st.session_state[key_trend_lt]
                    icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                    tooltip = "Hide Formula" if is_open else "Show Formula"
                    st.button(icon, key=f"btn_{key_trend_lt}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_trend_lt})

                if st.session_state.get(key_trend_lt, False):
                    st.info("""\
**Tren Lead Time per Bulan**: Line chart rata-rata kecepatan proses per bulan, dibedakan antara Tender Normal dan PR-PO Kontrak..

**Kalkulasi SQL:**
```sql
AVG(lead_time_process_po) AS avg_lt
GROUP BY DATE_TRUNC('month', date_ordered),
         jenis_tender
ORDER BY bulan
```

**Cara membaca chart:**
- Tren **turun konsisten** = proses pengadaan semakin efisien dari waktu ke waktu ✅
- Tren **naik** = ada hambatan sistemik yang perlu dievaluasi ⚠️
- **Lonjakan di bulan tertentu** = cek apakah ada event khusus (pelaksanaan TA, audit, akhir tahun anggaran)
- Jika garis Kontrak **jauh di bawah** Tender Normal secara konsisten = strategi kontrak terbukti efektif

**Target:** Garis merah putus-putus = **55 hari**.
                    """)

                st.caption("Rata-rata kecepatan proses per bulan, dibedakan antara Tender Normal dan PR-PO Kontrak.")

                trend_lt_query = f"""
                SELECT
                    DATE_TRUNC('month', date_ordered)::DATE                          AS bulan,
                    jenis_tender,
                    ROUND(AVG(lead_time_process_po)::numeric, 1)                     AS avg_lt,
                    COUNT(*)                                                          AS jml_po
                FROM vw_pr_po_complete
                WHERE {filter_conditions}
                  AND nomor_po IS NOT NULL
                  AND date_ordered IS NOT NULL
                  AND lead_time_process_po IS NOT NULL
                  AND {bagian_po_cond}
                GROUP BY 1, 2
                ORDER BY 1, 2
                """
                with st.spinner("Memuat tren lead time..."):
                    trend_lt_data = load_data(trend_lt_query)

                if not trend_lt_data.empty:
                    trend_lt_data['bulan'] = pd.to_datetime(trend_lt_data['bulan'])
                    fig_trend_lt = px.line(
                        trend_lt_data,
                        x='bulan', y='avg_lt',
                        color='jenis_tender', markers=True,
                        color_discrete_map={
                            'PR - PO Kontrak': '#1f77b4',
                            'Tender Normal'  : '#ff7f0e'
                        },
                        labels={
                            'bulan'       : 'Bulan',
                            'avg_lt'      : 'Lead Time Avg (Hari)',
                            'jenis_tender': 'Jenis Tender'
                        }
                    )
                    fig_trend_lt.add_hline(y=55, line_dash="dash", line_color="red",
                                           annotation_text="Target 55 Hari",
                                           annotation_position="bottom right")
                    fig_trend_lt.update_layout(
                        height=400,
                        hovermode='x unified',
                        legend=dict(orientation="h", yanchor="bottom", y=1.02)
                    )
                    st.plotly_chart(fig_trend_lt, use_container_width=True)
                else:
                    st.info("Tidak ada data tren lead time.")

            with col2:
                st.markdown("""
                    <h1 style='display: flex; align-items: center; font-size:22px;'>
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-table" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                            <path d="M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2zm15 2h-4v3h4zm0 4h-4v3h4zm0 4h-4v3h3a1 1 0 0 0 1-1zm-5 3v-3H6v3zm-5 0v-3H1v2a1 1 0 0 0 1 1zm-4-4h4V8H1zm0-4h4V4H1zm5-3v3h4V4zm4 4H6v3h4z"/>
                        </svg>
                        Ringkasan Kecepatan per Purchasing Group x Jenis Tender
                    </h1>
                """, unsafe_allow_html=True)
                
                # Tambahan sedikit padding agar tabel sejajar dengan visual di sebelahnya
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

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
                            'jml_po'          : 'Jml PO',
                            'avg_lt'          : 'Lead Time Avg',
                            'median_lt'       : 'Lead Time Median',
                            'jml_ontime'      : 'On-Time (<=55 Hr)',
                            'jml_late'        : 'Terlambat (>55 Hr)',
                            'ontime_pct'      : '% On-Time',
                        }),
                        use_container_width=True, height=420
                    )
                    csv_speed = lt_tender_data.to_csv(index=False)
                    st.download_button(
                        label="Download sebagai CSV",
                        icon=":material/download:",
                        data=csv_speed,
                        file_name=f"kecepatan_proses_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("Tidak ada data kecepatan proses.")

        # =====================================================================
        # INTEGRASI AI: KUMPULKAN KONTEKS & PANGGIL CHAT
        # Di luar semua tab agar Mia selalu muncul di bawah halaman
        # =====================================================================

        konteks_lines = []

        # 0. Rangkuman Filter
        konteks_lines.append("## 0. FILTER YANG SEDANG DITERAPKAN USER")
        konteks_lines.append(info_filter)
        konteks_lines.append("\n")

        # 1. Rangkuman KPI Global
        konteks_lines.append("## 1. RINGKASAN KPI GLOBAL KINERJA PURCHASING GROUP")
        konteks_lines.append(f"- Total Item PR: {t_item_pr} (Terkonversi ke PO: {konversi_pct:.1f}%)")
        konteks_lines.append(f"- Total OE: {format_idr(t_oe)}")
        konteks_lines.append(f"- Total Realisasi PO: {format_idr(t_real)}")
        konteks_lines.append(f"- Efisiensi Total: {format_idr(t_efis)} ({t_efis_pct:.1f}%)")
        if pd.notna(avg_lt):
            konteks_lines.append(f"- Rata-rata Lead Time Keseluruhan: {avg_lt:.1f} Hari")
        konteks_lines.append("\n")

        # 2. Rangkuman Tab 1: Overview per PG
        if 'df_table' in locals() and not df_table.empty:
            konteks_lines.append("## 2. KINERJA PER PURCHASING GROUP (OVERVIEW)")
            df_pg_simple = df_table[['purchasing_group', 'nilai_po', 'efisiensi_pct', 'avg_lead_time']]
            konteks_lines.append(df_pg_simple.to_markdown(index=False))
            konteks_lines.append("\n")

        # 3. Rangkuman Tab 2: Breakdown Kontrak vs Non-Kontrak
        if 'kontrak_data' in locals() and not kontrak_data.empty:
            konteks_lines.append("## 3. BREAKDOWN JENIS TENDER (KONTRAK VS NORMAL) PER PG")
            df_kontrak_simple = kontrak_data[['purchasing_group', 'jenis_kontrak', 'total_realisasi', 'avg_lead_time']]
            konteks_lines.append(df_kontrak_simple.to_markdown(index=False))
            konteks_lines.append("\n")

        # 4. Rangkuman Tab 3: Detail Kecepatan
        if 'lt_tender_data' in locals() and not lt_tender_data.empty:
            konteks_lines.append("## 4. DETAIL KETEPATAN WAKTU (ON-TIME VS LATE) PER PG")
            df_speed_simple = lt_tender_data[['purchasing_group', 'jml_ontime', 'jml_late', 'ontime_pct']]
            konteks_lines.append(df_speed_simple.to_markdown(index=False))
            konteks_lines.append("\n")

        # Gabungkan konteks lokal dengan konteks global lintas sistem
        suplemen = "\n# SUPLEMEN — DETAIL HALAMAN INI (Kinerja Purchasing Group)\n" + "\n".join(konteks_lines)
        konteks_final = kwargs.get("global_context", "") + "\n---\n" + suplemen

        # Render chat di bawah semua tab
        render_chat_analyst(
            konteks_data_teks=konteks_final,
            nama_halaman="Kinerja Purchasing Group"
        )