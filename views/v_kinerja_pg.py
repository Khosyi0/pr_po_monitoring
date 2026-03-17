"""
v_kinerja_pg.py - Halaman Kinerja Purchasing Group
"""
import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
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

        date_from = kwargs.get('date_from')
        date_to   = kwargs.get('date_to')
        bagian_po_poh = bagian_po_cond.replace('bagian_po', 'poh.bagian_po')

        # PR KPI: filter by first_full_release (hanya PR yang sudah full release)
        pg_kpi_query = f"""
        SELECT
            COUNT(DISTINCT CASE WHEN no_pr != 'No PR' AND {bagian_pr_cond}
                THEN no_pr || '-' || line_item_pr::text END)                         AS total_item_pr,
            COUNT(DISTINCT CASE WHEN nomor_po IS NOT NULL AND no_pr != 'No PR' AND {bagian_pr_cond}
                THEN no_pr || '-' || line_item_pr::text END)                         AS pr_with_po
        FROM vw_pr_po_complete
        WHERE {filter_conditions}
          AND first_full_release IS NOT NULL
        """

        # OE dari po_items langsung (PO SAP), hindari double-count dari join PR-PO di view
        pg_oe_kpi_query = f"""
        SELECT
            COALESCE(SUM(poi.estimasi_pr * poi.quantity_pr), 0) AS total_oe
        FROM po_items poi
        JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
        WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
          AND poi.estimasi_pr IS NOT NULL AND poi.estimasi_pr > 0
          AND poi.quantity_pr IS NOT NULL AND poi.quantity_pr > 0
          AND {bagian_po_poh}
        """

        # PO KPI: filter by date_ordered langsung dari tabel po_items
        pg_po_kpi_query = f"""
        SELECT
            COUNT(DISTINCT poi.nomor_po || '-' || poi.item_po::text)                 AS total_item_po,
            COALESCE(SUM(poi.total_amount_local_curr), 0)                            AS total_realisasi,
            ROUND(AVG(
                CASE WHEN poi.first_full_release IS NOT NULL AND poh.date_ordered IS NOT NULL
                THEN (poh.date_ordered::date - poi.first_full_release::date)
                END
            )::numeric, 1)                                                           AS avg_lead_time_overall
        FROM po_items poi
        JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
        WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
          AND {bagian_po_poh}
        """

        with st.spinner("Memuat KPI..."):
            pg_kpi    = load_data(pg_kpi_query)
            pg_po_kpi = load_data(pg_po_kpi_query)
            pg_oe_kpi = load_data(pg_oe_kpi_query)

        if not pg_kpi.empty:
            t_item_pr    = int(pg_kpi['total_item_pr'][0] or 0)
            t_item_po    = int(pg_po_kpi['total_item_po'][0] or 0)
            pr_with_po   = int(pg_kpi['pr_with_po'][0] or 0)
            t_oe         = float(pg_oe_kpi['total_oe'][0] or 0)
            t_real       = float(pg_po_kpi['total_realisasi'][0] or 0)
            t_efis       = t_oe - t_real
            t_efis_pct   = (t_efis / t_oe * 100) if t_oe > 0 else 0
            avg_lt        = pg_po_kpi['avg_lead_time_overall'][0]
            konversi_pct = (pr_with_po / t_item_pr * 100) if t_item_pr > 0 else 0
            delta_efis = "efisien" if t_efis >= 0 else "over budget"
            lt_label   = f"{avg_lt} Hari" if pd.notna(avg_lt) else "N/A"
            lt_delta   = "✅ On Target" if (avg_lt and avg_lt <= 55) else "⚠️ Over Target"

            KPI_PG = []

            if KPI_PG:
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

        # ── TAB: OVERVIEW | BREAKDOWN ───────────────────
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
                var pgTabs = tabs.slice(0, 2);
                if (pgTabs.length === 2) {
                    restoreTab(pgTabs);
                } else {
                    setTimeout(init, 100);
                }
            }

            window.addEventListener('load', function() { setTimeout(init, 150); });
        })();
        </script>
        """, height=0)

        tab1, tab2 = st.tabs([
            ":material/overview: Overview per Purchasing Group",
            ":material/sell: Breakdown Metode Tender & Kecepatan",
        ])

        # ══════════════════════════════════════════════════════════════════════
        # TAB 1: OVERVIEW PER PURCHASING GROUP
        # ══════════════════════════════════════════════════════════════════════
        with tab1:
            bagian_pr_cond_pri = bagian_pr_cond.replace('bagian_pr', 'pri.bagian_pr')

            pg_pr_query = f"""
            SELECT
                COALESCE(poh.purchasing_group, 'Unassigned')                         AS purchasing_group,
                COUNT(DISTINCT pri.no_pr || '-' || pri.line_item_pr::text)
                    FILTER (WHERE pri.material_no IS NOT NULL
                              AND (pri.batal IS NULL OR pri.batal = FALSE))           AS jml_item_pr,
                COUNT(DISTINCT pri.no_pr || '-' || pri.line_item_pr::text)
                    FILTER (WHERE pri.material_no IS NOT NULL
                              AND (pri.batal IS NULL OR pri.batal = FALSE))           AS pr_with_po
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
                COALESCE(poh.purchasing_group, 'Unassigned')                         AS purchasing_group,
                COUNT(DISTINCT poi.nomor_po || '-' || poi.item_po::text)             AS jml_item_po,
                COALESCE(SUM(poi.estimasi_pr * poi.quantity_pr)
                    FILTER (WHERE poi.estimasi_pr > 0 AND poi.quantity_pr > 0), 0)   AS nilai_oe,
                COALESCE(SUM(poi.total_amount_local_curr), 0)                        AS nilai_po,
                COALESCE(SUM(poi.estimasi_pr * poi.quantity_pr)
                    FILTER (WHERE poi.estimasi_pr > 0 AND poi.quantity_pr > 0), 0)
                    - COALESCE(SUM(poi.total_amount_local_curr), 0)                  AS efisiensi,
                CASE
                    WHEN COALESCE(SUM(poi.estimasi_pr * poi.quantity_pr)
                        FILTER (WHERE poi.estimasi_pr > 0 AND poi.quantity_pr > 0), 0) > 0
                    THEN ROUND(
                        (COALESCE(SUM(poi.estimasi_pr * poi.quantity_pr)
                            FILTER (WHERE poi.estimasi_pr > 0 AND poi.quantity_pr > 0), 0)
                         - COALESCE(SUM(poi.total_amount_local_curr), 0))
                        / COALESCE(SUM(poi.estimasi_pr * poi.quantity_pr)
                            FILTER (WHERE poi.estimasi_pr > 0 AND poi.quantity_pr > 0), 0) * 100,
                        1)
                    ELSE NULL
                END                                                                  AS efisiensi_pct,
                ROUND(AVG(
                    CASE WHEN poi.first_full_release IS NOT NULL AND poh.date_ordered IS NOT NULL
                    THEN (poh.date_ordered::date - poi.first_full_release::date)
                    END
                )::numeric, 1)                                                       AS avg_lead_time,
                MIN(CASE WHEN poi.first_full_release IS NOT NULL
                    THEN (poh.date_ordered::date - poi.first_full_release::date) END) AS min_lead_time,
                MAX(CASE WHEN poi.first_full_release IS NOT NULL
                    THEN (poh.date_ordered::date - poi.first_full_release::date) END) AS max_lead_time
            FROM po_items poi
            JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
            WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
              AND ({bagian_po_cond.replace('bagian_po', 'poh.bagian_po')})
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
                df_display['nilai_oe']     = df_display['nilai_oe'].apply(format_currency)
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

                col_order = [
                    'purchasing_group',
                    'jml_item_po', 'jml_item_pr', 'pr_with_po', 'konversi_pct',
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

**Formula Excel:** (PO SAP)
- Filter sesuai Purchasing Group yang ingin dicari
- Kolom **OE**: `= Estimasi PR × Quantity PR`
- Jumlahkan masing-masing kolom **OE** dan **Total Amount in Local Curr** menggunakan `SUM`

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
| Metrik | Formula |
|---|---|
| Nilai OE | `SUM(estimasi_pr × quantity_pr)` |
| Nilai Realisasi | `SUM(total_amount_local_curr)` |
| % Efisiensi | `(Nilai OE - Nilai Realisasi) × 100%` |

**Formula Excel:** (PO SAP)
- Filter sesuai Purchasing Group yang ingin dicari
- Kolom OE: = `Estimasi PR × Quantity PR`
- Kolom Efisiensi: = `OE - Total Amount in Local Curr`
- Jumlahkan masing-masing kolom **OE** dan **Efisiensi** menggunakan `SUM`
- % Efisiensi: = `Total Efisiensi / Total OE`
- Format cell sebagai **persentase (%)**.

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
| Metrik | Formula |
|---|---|
| Lead Time | AVG(`date_ordered - tgl_create_pr`) per purchasing_group |

**Formula Excel:** (PO SAP) 
- Filter sesuai Purchasing Group yang ingin dicari
- Lead Time `= Date Ordered - Tgl Create PR`
- Lalu **Lead Time** dirata-rata

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
**% Konversi PR → PO per Purchasing Group**: Bar chart horizontal persentase item PR yang berhasil dikonversi menjadi PO, per Purchasing Group.

**Kalkulasi SQL:**
```sql
-- Item PR: dari tabel pr_items, filter tgl_create_pr sesuai rentang tanggal
--          JOIN ke po_items via no_pr + line_item_pr untuk mendapatkan purchasing_group
Item PR     = COUNT(DISTINCT no_pr || '-' || line_item_pr)
              FROM pr_items
              WHERE material_no IS NOT NULL AND batal IS NULL/FALSE

-- PR dgn PO: item PR di atas yang sudah memiliki pasangan di po_items
PR dgn PO   = COUNT(DISTINCT no_pr || '-' || line_item_pr)
              FROM pr_items JOIN po_items ON no_pr + line_item_pr

% Konversi  = PR dgn PO / Item PR × 100
```

**Catatan penting:** PR yang **belum punya PO sama sekali** tidak dapat ditampilkan per Purchasing Group karena data purchasing group hanya tersedia setelah PR dikonversi ke PO. Oleh karena itu, `% Konversi` di sini mencerminkan **seberapa besar porsi item PR (yang sudah terhubung ke PO) dibandingkan total item PR yang ada dalam filter tanggal**.

**Formula Excel:** (PR SAP + PO SAP, digabung via No PR + Line Item PR)
- Filter Purchasing Group sesuai yang ingin dicari (dari kolom PO SAP)
- Hitung jumlah unik `No PR + Line Item PR` dari PR SAP = **Item PR**
- Hitung jumlah unik `No PR + Line Item PR` yang juga ada di PO SAP = **PR dgn PO**
- `% Konversi = PR dgn PO / Item PR`

**Cara membaca:**
- % **tinggi** (mendekati 100%) = hampir semua PR dalam periode ini sudah terkonversi ke PO ✅
- % **rendah** = banyak PR yang belum diproses → perlu investigasi (anggaran, kelengkapan dokumen, dll)
- **0,0%** = tidak ada item PR yang ditemukan dalam rentang tanggal filter untuk Purchasing Group ini
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
        # TAB 2: BREAKDOWN METODE TENDER, TURN AROUND & KECEPATAN PROSES
        # ══════════════════════════════════════════════════════════════════════
        with tab2:
            st.markdown("Breakdown pengadaan berdasarkan **jenis tender** dan **Turn Around**, lengkap dengan analisis kecepatan proses dan tren lead time.")

            # ── KPI Kecepatan ──────────────────────────
            speed_kpi_query = f"""
            SELECT
                ROUND(AVG(poi.pr_po_days)::numeric, 1)                               AS avg_lt_overall,
                ROUND(MIN(poi.pr_po_days)::numeric, 0)                               AS min_lt,
                ROUND(MAX(poi.pr_po_days)::numeric, 0)                               AS max_lt,
                ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP
                    (ORDER BY poi.pr_po_days)::numeric, 1)                            AS median_lt,
                COUNT(CASE WHEN poi.pr_po_days <= 55 THEN 1 END)                     AS jml_ontime,
                COUNT(CASE WHEN poi.pr_po_days > 55 THEN 1 END)                      AS jml_late,
                COUNT(poi.pr_po_days)                                                 AS total_lt
            FROM po_items poi
            JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
            WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
              AND poi.pr_po_days IS NOT NULL
              AND ({bagian_po_cond.replace('bagian_po', 'poh.bagian_po')})
            """

            with st.spinner("Memuat KPI kecepatan..."):
                speed_kpi = load_data(speed_kpi_query)

            spd_avg_lt = spd_med_lt = spd_min_lt = spd_max_lt = None
            spd_ontime = spd_late = spd_total = 0
            spd_ontime_pct = 0
            spd_d_color = "normal"

            if not speed_kpi.empty and speed_kpi['total_lt'][0]:
                spd_avg_lt     = float(speed_kpi['avg_lt_overall'][0] or 0)
                spd_med_lt     = float(speed_kpi['median_lt'][0] or 0)
                spd_min_lt     = int(speed_kpi['min_lt'][0] or 0)
                spd_max_lt     = int(speed_kpi['max_lt'][0] or 0)
                spd_ontime     = int(speed_kpi['jml_ontime'][0] or 0)
                spd_late       = int(speed_kpi['jml_late'][0] or 0)
                spd_total      = int(speed_kpi['total_lt'][0] or 1)
                spd_ontime_pct = spd_ontime / spd_total * 100

                if spd_ontime_pct >= 80:
                    spd_d_color = "normal"
                elif 60 <= spd_ontime_pct < 80:
                    spd_d_color = "off"
                else:
                    spd_d_color = "inverse"

                SPEED_KPI = [
                    {
                        "key": "kpi_speed_avg",
                        "label": "Avg Lead Time",
                        "value": f"{format_number(spd_avg_lt, decimals=1)} Hari",
                        "delta": "✅ On Target" if spd_avg_lt <= 55 else "⚠️ Over Target",
                        "formula": """\
**Avg Lead Time**: Rata-rata waktu proses dari PR dibuat hingga PO diterbitkan, untuk semua Purchasing Group.

**Formula Excel:** (PO SAP)
- Filter Material No selain `1000076` dan PO Deletion Flag selain `L`
- Buat kolom baru untuk perhitungan `Date Ordered - Tgl Create PR`
- Dirata-rata

**Target SLA = 55 hari.** Rata-rata lebih sensitif terhadap outlier dibanding median, bandingkan keduanya untuk gambaran lengkap.
"""
                    },
                    {
                        "key": "kpi_speed_median",
                        "label": "Median Lead Time",
                        "value": f"{format_number(spd_med_lt, decimals=1)} Hari",
                        "delta": None,
                        "formula": """\
**Median Lead Time**: Nilai tengah dari seluruh distribusi lead time PO dalam periode filter.

**Formula Excel:** (PO SAP)
- Filter Material No selain `1000076` dan PO Deletion Flag selain `L`
- Buat kolom baru untuk perhitungan `Date Ordered - Tgl Create PR`
- Dicari `mean`nya

Jika median jauh lebih rendah dari rata-rata, berarti ada sejumlah kecil PO dengan lead time ekstrem. Gunakan median sebagai ukuran "kecepatan tipikal".
"""
                    },
                    {
                        "key": "kpi_speed_rentang",
                        "label": "Rentang Lead Time",
                        "value": f"{format_number(spd_min_lt)} - {format_number(spd_max_lt)} Hari",
                        "delta": None,
                        "formula": """\
**Rentang Lead Time**: Selisih antara lead time terpendek dan terpanjang dalam periode filter.

**Formula Excel:** (PO SAP)
- Filter Material No selain `1000076` dan PO Deletion Flag selain `L`
- Buat kolom baru untuk perhitungan `Date Ordered - Tgl Create PR`
- Dicari terbesar dan terkecilnya

**Rentang sempit** = proses konsisten. **Rentang lebar** = variabilitas tinggi, perlu investigasi outlier.
"""
                    },
                    {
                        "key": "kpi_speed_ontime",
                        "label": "On-Time (≤55 Hari)",
                        "value": f"{format_number(spd_ontime)}",
                        "delta": f"{format_number(spd_ontime_pct, decimals=1)}% dari total",
                        "formula": """\
**On-Time (≤55 Hari)**: Jumlah PO yang diproses dalam batas SLA 55 hari.

**Formula Excel:** (PO SAP)
- Filter Material No selain `1000076` dan PO Deletion Flag selain `L`
- Buat kolom baru untuk perhitungan `Date Ordered - Tgl Create PR`
- FIlter `countif` kurang dari sama dengan 55

| % On-Time | Status |
|---|---|
| ≥ 80% | 🟢 Proses berjalan baik |
| 60–79% | 🟡 Perlu perhatian |
| < 60% | 🔴 Kritis |
"""
                    },
                    {
                        "key": "kpi_speed_late",
                        "label": "Terlambat (>55 Hari)",
                        "value": f"{format_number(spd_late)}",
                        "delta": f"{format_number(100 - spd_ontime_pct, decimals=1)}% dari total",
                        "formula": """\
**Terlambat (>55 Hari)**: Jumlah PO yang melebihi batas SLA 55 hari.

**Formula Excel:** (PO SAP)
- Filter Material No selain `1000076` dan PO Deletion Flag selain `L`
- Buat kolom baru untuk perhitungan `Date Ordered - Tgl Create PR`
- FIlter `countif` lebih dari sama dengan 55

Drill-down ke tabel **Ringkasan Kecepatan per Purchasing Group** di bawah untuk identifikasi Purchasing Group dengan % terlambat tertinggi.
"""
                    },
                ]

                for kpi in SPEED_KPI:
                    if kpi["key"] not in st.session_state:
                        st.session_state[kpi["key"]] = False

                speed_cols = st.columns(len(SPEED_KPI))
                for col, kpi in zip(speed_cols, SPEED_KPI):
                    with col:
                        m_col, btn_col = st.columns([5, 1])
                        with m_col:
                            st.metric(label=kpi["label"], value=kpi["value"],
                                      delta=kpi["delta"], delta_color=spd_d_color)
                        with btn_col:
                            st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
                            is_open = st.session_state[kpi["key"]]
                            icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                            st.button(icon, key=f"btn_{kpi['key']}", help="Hide Formula" if is_open else "Show Formula",
                                      on_click=toggle_state, kwargs={"state_key": kpi["key"]})

                import streamlit.components.v1 as _comp
                _ontime_color = "#09ab3b" if spd_ontime_pct >= 80 else ("#ffa500" if spd_ontime_pct >= 60 else "#ff4b4b")
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
                            if (text.indexOf("Terlambat") !== -1) color = "{_ontime_color}";
                            if (!color) return;
                            var metric = label.closest('[data-testid="stMetric"]');
                            if (!metric) return;
                            var delta = metric.querySelector('[data-testid="stMetricDelta"]');
                            if (!delta) return;
                            [delta].concat(Array.from(delta.querySelectorAll("*"))).forEach(function(el) {{
                                el.style.setProperty("color", color, "important");
                                el.style.setProperty("-webkit-text-fill-color", color, "important");
                            }});
                            found++;
                        }});
                        if (found < 2) setTimeout(applyColors, 150);
                    }}
                    setTimeout(applyColors, 250);
                    window.addEventListener("load", function() {{ setTimeout(applyColors, 250); }});
                }})();
                </script>
                """, height=0)

                for kpi in SPEED_KPI:
                    if st.session_state[kpi["key"]]:
                        st.info(kpi["formula"])

            st.markdown("---")

            col1, col2 = st.columns(2)
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

**Formula Excel:** (PO SAP)
- Filter sesuai Purchasing Group yang ingin dicari
- Kolom Jenis Tender: `= IF(LEFT(No Contract, 1) = "4", "PR - PO Kontrak", "Tender Normal")`
- Total Realisasi: `= (SUM(Total Amount in Local Curr))`
- Lead Time: `= AVERAGE(Date Ordered - 1St Full Release)` (hanya baris yang `1St Full Release` terisi)

Kalkulasi jenis tender, dihitung dari kolom `contract_no` di `po_items`: diawali angka '4' = PR - PO Kontrak, selainnya = Tender Normal.

**Perbedaan kedua jenis:**
| Jenis | Karakteristik |
|---|---|
| PR - PO Kontrak | Menggunakan kontrak yang sudah ada → lebih cepat, harga lebih stabil |
| Tender Normal | Proses penawaran/negosiasi baru setiap transaksi → biasanya lebih lama |
                    """)

                st.caption("Komposisi nilai realisasi berdasarkan jenis tender per Purchasing Group.")

                kontrak_query = f"""
                SELECT
                    CASE
                        WHEN poi.contract_no IS NOT NULL
                         AND poi.contract_no <> ''
                         AND LEFT(poi.contract_no, 1) = '4'
                        THEN 'PR - PO Kontrak'
                        ELSE 'Tender Normal'
                    END                                                        AS jenis_kontrak,
                    COALESCE(poh.purchasing_group, 'Unassigned')               AS purchasing_group,
                    COUNT(DISTINCT poi.nomor_po || '-' || poi.item_po::text)   AS jml_item,
                    COALESCE(SUM(poi.total_amount_local_curr), 0)               AS total_realisasi,
                    ROUND(AVG(poi.pr_po_days)::numeric, 1)                     AS avg_lead_time
                FROM po_items poi
                JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
                WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
                    AND poi.first_full_release IS NOT NULL
                    AND ({bagian_po_cond.replace('bagian_po', 'poh.bagian_po')})
                GROUP BY
                    CASE
                        WHEN poi.contract_no IS NOT NULL
                         AND poi.contract_no <> ''
                         AND LEFT(poi.contract_no, 1) = '4'
                        THEN 'PR - PO Kontrak'
                        ELSE 'Tender Normal'
                    END,
                    COALESCE(poh.purchasing_group, 'Unassigned')
                ORDER BY jenis_kontrak, purchasing_group
                """
                # Query terpisah untuk global avg (hindari mean-of-means per purchasing_group)
                kontrak_global_query = f"""
                SELECT
                    CASE
                        WHEN poi.contract_no IS NOT NULL
                         AND poi.contract_no <> ''
                         AND LEFT(poi.contract_no, 1) = '4'
                        THEN 'PR - PO Kontrak'
                        ELSE 'Tender Normal'
                    END                                                        AS jenis_kontrak,
                    COUNT(DISTINCT poi.nomor_po || '-' || poi.item_po::text)   AS jml_item,
                    COALESCE(SUM(poi.total_amount_local_curr), 0)               AS total_realisasi,
                    ROUND(AVG(poi.pr_po_days)::numeric, 1)                     AS avg_lead_time
                FROM po_items poi
                JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
                WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
                    AND poi.first_full_release IS NOT NULL
                    AND ({bagian_po_cond.replace('bagian_po', 'poh.bagian_po')})
                GROUP BY
                    CASE
                        WHEN poi.contract_no IS NOT NULL
                         AND poi.contract_no <> ''
                         AND LEFT(poi.contract_no, 1) = '4'
                        THEN 'PR - PO Kontrak'
                        ELSE 'Tender Normal'
                    END
                ORDER BY jenis_kontrak
                """
                with st.spinner("Memuat data kontrak..."):
                    kontrak_data   = load_data(kontrak_query)
                    kontrak_global = load_data(kontrak_global_query)

                if not kontrak_data.empty:
                    kontrak_sum = kontrak_global if not kontrak_global.empty else kontrak_data.groupby('jenis_kontrak').agg(
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

**Formula Excel:** 
- Total Item: `= IF(LEFT(Departement(Requisitioner), 2) = "TA", "TA", "non")`
- Lead Time: `= AVERAGE(Date Ordered - 1St Full Release)` (hanya baris yang `1St Full Release` terisi)
- Total Realisasi: `= (SUM(Total Amount in Local Curr))`

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
                    COALESCE(poh.purchasing_group, 'Unassigned')               AS purchasing_group,
                    CASE
                        WHEN LEFT(COALESCE(poi.department_code, ''), 2) = 'TA' THEN 'TA'
                        ELSE 'non'
                    END                                                        AS turn_around,
                    COUNT(DISTINCT poi.nomor_po || '-' || poi.item_po::text)   AS jml_item,
                    COALESCE(SUM(poi.total_amount_local_curr), 0)               AS total_realisasi,
                    ROUND(AVG(poi.pr_po_days)::numeric, 1)                     AS avg_lead_time
                FROM po_items poi
                JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
                WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
                    AND poi.first_full_release IS NOT NULL
                    AND ({bagian_po_cond.replace('bagian_po', 'poh.bagian_po')})
                GROUP BY COALESCE(poh.purchasing_group, 'Unassigned'),
                         CASE
                             WHEN LEFT(COALESCE(poi.department_code, ''), 2) = 'TA' THEN 'TA'
                             ELSE 'non'
                         END
                ORDER BY purchasing_group, jml_item DESC
                """
                # Query global untuk ringkasan (hindari mean-of-means)
                ta_global_query = f"""
                SELECT
                    CASE
                        WHEN LEFT(COALESCE(poi.department_code, ''), 2) = 'TA' THEN 'TA'
                        ELSE 'non'
                    END                                                        AS turn_around,
                    COUNT(DISTINCT poi.nomor_po || '-' || poi.item_po::text)   AS jml_item,
                    COALESCE(SUM(poi.total_amount_local_curr), 0)               AS total_realisasi,
                    ROUND(AVG(poi.pr_po_days)::numeric, 1)                     AS avg_lead_time
                FROM po_items poi
                JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
                WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
                    AND poi.first_full_release IS NOT NULL
                    AND ({bagian_po_cond.replace('bagian_po', 'poh.bagian_po')})
                GROUP BY
                    CASE
                        WHEN LEFT(COALESCE(poi.department_code, ''), 2) = 'TA' THEN 'TA'
                        ELSE 'non'
                    END
                ORDER BY jml_item DESC
                """
                with st.spinner("Memuat data turn around..."):
                    ta_data   = load_data(ta_query)
                    ta_global = load_data(ta_global_query)

                if not ta_data.empty:
                    # Ringkasan global, pakai query global agar AVG tidak terdistorsi
                    ta_sum = ta_global if not ta_global.empty else ta_data.groupby('turn_around').agg(
                        jml_item       =('jml_item',        'sum'),
                        total_realisasi=('total_realisasi', 'sum'),
                        avg_lead_time  =('avg_lead_time',   'mean')
                    ).reset_index()
                    ta_sum = ta_sum.sort_values('jml_item', ascending=False)

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

                else:
                    st.info("Tidak ada data turn around pada periode ini.")

            # ── Tabel Detail Turn Around (full width, di luar col1/col2) ─────
            if 'ta_data' in locals() and not ta_data.empty:
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
                    use_container_width=True, height=280
                )

            if not kontrak_data.empty:
                st.markdown("---")

                col1, col2 = st.columns(2)
                with col1:
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

**Formula Excel:** (PO SAP)
- Filter sesuai Purchasing Group yang ingin dicari
- Kolom Jenis Tender: `= IF(LEFT(No Contract, 1) = "4", "PR - PO Kontrak", "Tender Normal")`
- Lead Time: `= AVERAGE(Date Ordered - 1St Full Release)` (hanya baris yang `1St Full Release` terisi)

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

                with col2:
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
**Tren Lead Time per Bulan**: Line chart rata-rata kecepatan proses per bulan, dibedakan antara Tender Normal dan PR-PO Kontrak.

**Formula Excel:** (PO SAP)
- Filter per bulan
- Kolom Jenis Tender: `= IF(LEFT(No Contract, 1) = "4", "PR - PO Kontrak", "Tender Normal")`
- Lead Time: `= AVERAGE(Date Ordered - 1St Full Release)` (hanya baris yang `1St Full Release` terisi)

**Cara membaca:**
- Tren **turun konsisten** = proses semakin efisien ✅
- Tren **naik** = ada hambatan sistemik yang perlu dievaluasi ⚠️
- **Lonjakan bulan tertentu** = cek event khusus (TA, audit, akhir tahun anggaran)
- Garis Kontrak **jauh di bawah** Tender Normal = strategi kontrak terbukti efektif

**Target:** Garis merah putus-putus = **55 hari**.
                        """)

                    st.caption("Rata-rata kecepatan proses per bulan, dibedakan antara Tender Normal dan PR-PO Kontrak.")

                    trend_lt_query = f"""
                    SELECT
                        DATE_TRUNC('month', poh.date_ordered)::DATE                      AS bulan,
                        CASE
                            WHEN poi.contract_no IS NOT NULL
                             AND poi.contract_no <> ''
                             AND LEFT(poi.contract_no, 1) = '4'
                            THEN 'PR - PO Kontrak'
                            ELSE 'Tender Normal'
                        END                                                              AS jenis_kontrak,
                        ROUND(AVG(poi.pr_po_days)::numeric, 1)                          AS avg_lt,
                        COUNT(DISTINCT poi.nomor_po || '-' || poi.item_po::text)        AS jml_item
                    FROM po_items poi
                    JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
                    WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
                      AND poi.pr_po_days IS NOT NULL
                      AND ({bagian_po_cond.replace('bagian_po', 'poh.bagian_po')})
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
                            hovermode='x unified',
                            legend=dict(orientation="h", yanchor="bottom", y=1.02)
                        )
                        st.plotly_chart(fig_trend_lt, use_container_width=True)
                    else:
                        st.info("Tidak ada data tren lead time.")

                st.markdown("---")

                # ── ROW 3: Tabel Ringkasan Kecepatan (full width) ─────────────
                st.markdown("""
                    <h1 style='display: flex; align-items: center; font-size:22px;'>
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-table" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                            <path d="M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2zm15 2h-4v3h4zm0 4h-4v3h4zm0 4h-4v3h3a1 1 0 0 0 1-1zm-5 3v-3H6v3zm-5 0v-3H1v2a1 1 0 0 0 1 1zm-4-4h4V8H1zm0-4h4V4H1zm5-3v3h4V4zm4 4H6v3h4z"/>
                        </svg>
                        Ringkasan Kecepatan per Purchasing Group × Jenis Tender
                    </h1>
                """, unsafe_allow_html=True)
                st.caption("Detail ketepatan waktu (On-Time vs Terlambat) per Purchasing Group dan jenis tender.")

                # Query: pakai po_items agar konsisten, group by purchasing_group × jenis_kontrak
                lt_tender_query = f"""
                SELECT
                    COALESCE(poh.purchasing_group, 'Unassigned')                     AS purchasing_group,
                    CASE
                        WHEN poi.contract_no IS NOT NULL
                         AND poi.contract_no <> ''
                         AND LEFT(poi.contract_no, 1) = '4'
                        THEN 'PR - PO Kontrak'
                        ELSE 'Tender Normal'
                    END                                                              AS jenis_tender,
                    COUNT(DISTINCT poi.nomor_po || '-' || poi.item_po::text)        AS jml_item,
                    ROUND(AVG(poi.pr_po_days)::numeric, 1)                          AS avg_lt,
                    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP
                        (ORDER BY poi.pr_po_days)::numeric, 1)                      AS median_lt,
                    COUNT(CASE WHEN poi.pr_po_days <= 55 THEN 1 END)               AS jml_ontime,
                    COUNT(CASE WHEN poi.pr_po_days > 55 THEN 1 END)                AS jml_late
                FROM po_items poi
                JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
                WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
                  AND poi.pr_po_days IS NOT NULL
                  AND ({bagian_po_cond.replace('bagian_po', 'poh.bagian_po')})
                GROUP BY COALESCE(poh.purchasing_group, 'Unassigned'),
                         CASE
                             WHEN poi.contract_no IS NOT NULL
                              AND poi.contract_no <> ''
                              AND LEFT(poi.contract_no, 1) = '4'
                             THEN 'PR - PO Kontrak'
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

                # Download gabungan
                col_dl1, col_dl2 = st.columns(2)
                with col_dl1:
                    csv_k = kontrak_data.to_csv(index=False)
                    st.download_button(
                        label="Download Data Kontrak (CSV)",
                        icon=":material/download:",
                        data=csv_k,
                        file_name=f"breakdown_kontrak_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                with col_dl2:
                    if not lt_tender_data.empty:
                        csv_speed = lt_tender_data.to_csv(index=False)
                        st.download_button(
                            label="Download Ringkasan Kecepatan (CSV)",
                            icon=":material/download:",
                            data=csv_speed,
                            file_name=f"kecepatan_proses_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )

        # =====================================================================
        # INTEGRASI AI: KUMPULKAN KONTEKS & PANGGIL CHAT
        # Di luar semua tab agar Melati selalu muncul di bawah halaman
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
        if spd_avg_lt is not None:
            konteks_lines.append(f"- Rata-rata Lead Time Keseluruhan: {spd_avg_lt:.1f} Hari | Median: {spd_med_lt:.1f} Hari")
            konteks_lines.append(f"- On-Time (≤55 Hari): {spd_ontime} ({spd_ontime_pct:.1f}%) | Terlambat: {spd_late}")
        konteks_lines.append("\n")

        # 2. Rangkuman Tab 1: Overview per PG
        if 'df_table' in locals() and not df_table.empty:
            konteks_lines.append("## 2. KINERJA PER PURCHASING GROUP (OVERVIEW)")
            df_pg_simple = df_table[['purchasing_group', 'nilai_po', 'efisiensi_pct', 'avg_lead_time']]
            konteks_lines.append(df_pg_simple.to_csv(index=False))
            konteks_lines.append("\n")

        # 3. Rangkuman Tab 2: Breakdown Kontrak & Kecepatan
        if 'kontrak_data' in locals() and not kontrak_data.empty:
            konteks_lines.append("## 3. BREAKDOWN JENIS TENDER (KONTRAK VS NORMAL) PER PG")
            df_kontrak_simple = kontrak_data[['purchasing_group', 'jenis_kontrak', 'total_realisasi', 'avg_lead_time']]
            konteks_lines.append(df_kontrak_simple.to_csv(index=False))
            konteks_lines.append("\n")

        if 'lt_tender_data' in locals() and not lt_tender_data.empty:
            konteks_lines.append("## 4. DETAIL KETEPATAN WAKTU (ON-TIME VS LATE) PER PG × JENIS TENDER")
            df_speed_simple = lt_tender_data[['purchasing_group', 'jenis_tender', 'jml_ontime', 'jml_late', 'ontime_pct']]
            konteks_lines.append(df_speed_simple.to_csv(index=False))
            konteks_lines.append("\n")

        # Gabungkan konteks lokal dengan konteks global lintas sistem
        suplemen = "\n# SUPLEMEN - DETAIL HALAMAN INI (Kinerja Purchasing Group)\n" + "\n".join(konteks_lines)
        konteks_final = kwargs.get("global_context", "") + "\n---\n" + suplemen

        # Render chat di bawah semua tab
        render_chat_analyst(
            konteks_data_teks=konteks_final,
            nama_halaman="Kinerja Purchasing Group",
            load_data_fn=load_data,
        )