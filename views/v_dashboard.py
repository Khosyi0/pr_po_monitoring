"""
v_dashboard.py - Halaman Dashboard Monitoring
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from utils import format_idr, format_idr_short


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
                    END), 0) AS avg_savings_pct
        FROM vw_pr_po_complete
        WHERE {filter_conditions}
        """

        with st.spinner("Memuat KPI..."):
            kpi_data = load_data(kpi_query)

        col1, col2, col3, col4 = st.columns(4)

        total_pr     = int(kpi_data['total_pr'][0] or 0)
        total_po     = int(kpi_data['total_po'][0] or 0)
        pr_with_po   = int(kpi_data['pr_with_po'][0] or 0)
        pr_without   = int(kpi_data['pr_without_po'][0] or 0)
        estimasi     = float(kpi_data['total_estimasi'][0] or 0)
        savings      = float(kpi_data['total_savings'][0] or 0)
        savings_pct  = float(kpi_data['avg_savings_pct'][0] or 0)

        with col1:
            st.metric("Total PR", f"{total_pr:,}", delta=f"{pr_with_po:,} with PO")
        with col2:
            st.metric("Total PO", f"{total_po:,}", delta=f"{pr_without:,} PR pending")
        with col3:
            st.metric("Total Estimasi PR", format_idr(estimasi))
        with col4:
            st.metric("Total Savings", format_idr(savings), delta=f"{savings_pct:.1f}% avg")

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
                fig.update_layout(barmode='stack', height=400)
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
                fig.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
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
                # Pastikan urutan kategori benar
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
                lambda x: f"Rp {x:,.0f}" if pd.notna(x) else ""
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
                fig.update_layout(height=350, margin=dict(t=0, b=0, l=0, r=0))
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
                fig.update_layout(height=350, margin=dict(t=20, b=0, l=0, r=0))
                fig.update_traces(
                    textfont_size=12, textangle=0, textposition="outside", cliponaxis=False,
                    hovertemplate="<b>ABC: %{x}</b><br>Total: Rp %{text}<extra></extra>"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No material data available.")