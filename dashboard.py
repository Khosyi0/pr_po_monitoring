"""
PR-PO Monitoring Dashboard (Optimized)
File: dashboard.py

Run with: streamlit run dashboard.py

Optimasi:
- Semua query di-load HANYA saat halaman yang relevan dibuka (lazy loading)
- KPI digabung menjadi 1 query besar (bukan banyak query kecil)
- Sidebar filter pakai tabel kecil (departments), bukan scan view besar
- Default variable values sebelum try block (fix NameError)
- Connection pool settings untuk Neon
- Typo fix pada alert_po_query (v.{filter_conditions} → {filter_conditions})
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# =====================================================
# PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="PR-PO Monitoring Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# DATABASE CONNECTION
# =====================================================

@st.cache_resource
def get_db_engine():
    """Create database connection (cached)"""
    db_config = st.secrets["postgres"]
    connection_url = (
        f"postgresql://{db_config['user']}:{db_config['password']}"
        f"@{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
    )
    engine = create_engine(
        connection_url,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={"connect_timeout": 30}
    )
    return engine

@st.cache_data(ttl=300)
def load_data(query):
    """Load data from database with caching"""
    engine = get_db_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
    return df

# =====================================================
# HELPER: Format IDR
# =====================================================

def format_idr(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "Rp 0"
    if abs(x) >= 1e12:
        return f"Rp {x/1e12:.2f} T"
    elif abs(x) >= 1e9:
        return f"Rp {x/1e9:.2f} M"
    elif abs(x) >= 1e6:
        return f"Rp {x/1e6:.2f} Jt"
    return f"Rp {x:,.0f}"

def format_idr_short(x):
    if abs(x) >= 1e12:
        return f"{x/1e12:.1f} T"
    elif abs(x) >= 1e9:
        return f"{x/1e9:.1f} M"
    elif abs(x) >= 1e6:
        return f"{x/1e6:.1f} Jt"
    return f"{x:,.0f}"

# =====================================================
# CUSTOM CSS
# =====================================================

st.markdown("""
<style>
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    h1 { color: #1f77b4; }
</style>
""", unsafe_allow_html=True)

# =====================================================
# NAVIGATION
# =====================================================

st.sidebar.title("🧭 Navigation")
page = st.sidebar.radio(
    "Pilih Halaman:",
    ["📊 Dashboard Monitoring", "🚨 Halaman Alert"],
    index=0
)
st.sidebar.markdown("---")

# =====================================================
# DEFAULT VALUES (wajib ada sebelum try block)
# =====================================================

date_from = datetime.now().date() - timedelta(days=90)
date_to = datetime.now().date()
selected_department = ['All']
selected_bagian = ['All']
exclude_dept = False
exclude_bagian = False

# =====================================================
# SIDEBAR FILTERS
# =====================================================

st.sidebar.header("🔍 Filters")

try:
    # Pakai tabel kecil untuk filter, bukan scan view besar
    departments = load_data(
        "SELECT DISTINCT department_code FROM departments ORDER BY department_code"
    )
    bagian_data = load_data(
        "SELECT DISTINCT bagian FROM departments WHERE bagian IS NOT NULL ORDER BY bagian"
    )

    selected_department = st.sidebar.multiselect(
        "Department",
        options=['All'] + departments['department_code'].tolist(),
        default=['All']
    )

    exclude_dept = False
    if 'All' not in selected_department and len(selected_department) > 0:
        exclude_dept = st.sidebar.checkbox("🚫 Exclude selected Department")

    selected_bagian = st.sidebar.multiselect(
        "Bagian",
        options=['All'] + bagian_data['bagian'].tolist(),
        default=['All']
    )

    exclude_bagian = False
    if 'All' not in selected_bagian and len(selected_bagian) > 0:
        exclude_bagian = st.sidebar.checkbox("🚫 Exclude selected Bagian")

    st.sidebar.subheader("📅 Date Range")
    date_from = st.sidebar.date_input("From", value=datetime.now().date() - timedelta(days=90))
    date_to = st.sidebar.date_input("To", value=datetime.now().date())

    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

except Exception as e:
    st.sidebar.error(f"Error loading filters: {e}")

# =====================================================
# BUILD FILTER CONDITIONS
# =====================================================

def build_filter_conditions():
    conditions = [
        f"tgl_create_pr >= '{date_from}'",
        f"tgl_create_pr <= '{date_to}'"
    ]
    if 'All' not in selected_department and selected_department:
        dept_list = "','".join(selected_department)
        if exclude_dept:
            conditions.append(f"(department_code NOT IN ('{dept_list}') OR department_code IS NULL)")
        else:
            conditions.append(f"department_code IN ('{dept_list}')")
    return " AND ".join(conditions)

filter_conditions = build_filter_conditions()

# Bagian filter untuk PR dan PO
bagian_pr_cond = "1=1"
bagian_po_cond = "1=1"

if 'All' not in selected_bagian and selected_bagian:
    bagian_list = "','".join(selected_bagian)
    if exclude_bagian:
        bagian_pr_cond = f"(bagian_pr NOT IN ('{bagian_list}') OR bagian_pr IS NULL)"
        bagian_po_cond = f"(bagian_po NOT IN ('{bagian_list}') OR bagian_po IS NULL)"
    else:
        bagian_pr_cond = f"bagian_pr IN ('{bagian_list}')"
        bagian_po_cond = f"bagian_po IN ('{bagian_list}')"

# =====================================================
# HALAMAN 1: DASHBOARD MONITORING
# =====================================================

if page == "📊 Dashboard Monitoring":

    st.title("📊 PR-PO Monitoring Dashboard")
    st.markdown("---")

    # ── KPI ──────────────────────────────────────────
    st.header("📈 Key Performance Indicators")

    # 1 query besar untuk semua KPI sekaligus
    kpi_query = f"""
    SELECT
        COUNT(DISTINCT CASE WHEN no_pr != 'No PR' AND {bagian_pr_cond}
              THEN no_pr || '-' || line_item_pr::text END)              AS total_pr,
        COUNT(CASE WHEN {bagian_po_cond} THEN nomor_po END)             AS total_po,
        COUNT(DISTINCT CASE WHEN nomor_po IS NOT NULL AND no_pr != 'No PR' AND {bagian_pr_cond}
              THEN no_pr || '-' || line_item_pr::text END)              AS pr_with_po,
        COUNT(DISTINCT CASE WHEN nomor_po IS NULL AND no_pr != 'No PR' AND {bagian_pr_cond}
              THEN no_pr || '-' || line_item_pr::text END)              AS pr_without_po,
        COALESCE(SUM(CASE WHEN {bagian_pr_cond} THEN estimasi_pr ELSE 0 END), 0)             AS total_estimasi,
        COALESCE(SUM(CASE WHEN {bagian_po_cond} THEN total_amount_local_curr ELSE 0 END), 0) AS total_po_amount,
        COALESCE(SUM(CASE WHEN {bagian_pr_cond} THEN estimasi_pr ELSE 0 END -
                     CASE WHEN {bagian_po_cond} THEN COALESCE(total_amount_local_curr, 0) ELSE 0 END), 0) AS total_savings,
        COALESCE(AVG(CASE
                WHEN total_amount_local_curr IS NOT NULL AND {bagian_pr_cond} AND {bagian_po_cond}
                THEN (estimasi_pr - total_amount_local_curr) / NULLIF(estimasi_pr, 0) * 100
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
        st.subheader("📊 PR Status by Department")
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
            st.info("No data available")

    with col2:
        st.subheader("💰 Top 10 Vendors by PO Value")
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
            st.info("No data available")

    # ── CHARTS ROW 2 ─────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📅 PR-PO Creation Trend")
        trend_query = f"""
        SELECT
            DATE_TRUNC('month', tgl_create_pr) AS month,
            COUNT(DISTINCT CASE WHEN no_pr != 'No PR' AND {bagian_pr_cond}
                  THEN no_pr || '-' || line_item_pr::text END) AS total_pr,
            COUNT(DISTINCT CASE WHEN nomor_po IS NOT NULL AND {bagian_po_cond}
                  THEN nomor_po END)                           AS total_po
        FROM vw_pr_po_complete
        WHERE {filter_conditions} AND tgl_create_pr IS NOT NULL
        GROUP BY 1
        ORDER BY 1
        """
        with st.spinner("Memuat trend..."):
            trend_data = load_data(trend_query)

        if not trend_data.empty:
            trend_data['month'] = pd.to_datetime(trend_data['month'])
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=trend_data['month'], y=trend_data['total_pr'],
                                     mode='lines+markers', name='PR Created',
                                     line=dict(color='#1f77b4', width=2)))
            fig.add_trace(go.Scatter(x=trend_data['month'], y=trend_data['total_po'],
                                     mode='lines+markers', name='PO Created',
                                     line=dict(color='#2ca02c', width=2)))
            fig.update_layout(height=400, xaxis_title='Month', yaxis_title='Count')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available")

    with col2:
        st.subheader("⏱️ Lead Time Distribution")
        leadtime_query = f"""
        SELECT
            CASE
                WHEN lead_time_process_po <= 7  THEN '1. 0-7 days'
                WHEN lead_time_process_po <= 14 THEN '2. 8-14 days'
                WHEN lead_time_process_po <= 30 THEN '3. 15-30 days'
                WHEN lead_time_process_po <= 60 THEN '4. 31-60 days'
                ELSE '5. 60+ days'
            END AS lead_time_range,
            COUNT(*) AS count
        FROM vw_pr_po_complete
        WHERE {filter_conditions} AND lead_time_process_po IS NOT NULL AND {bagian_po_cond}
        GROUP BY 1
        ORDER BY 1
        """
        with st.spinner("Memuat lead time..."):
            leadtime_data = load_data(leadtime_query)

        if not leadtime_data.empty:
            fig = px.pie(leadtime_data, values='count', names='lead_time_range', hole=0.4)
            fig.update_traces(sort=False)
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available")

    # ── DATA TABLE ───────────────────────────────────
    st.markdown("---")
    st.header("📋 Detailed PR-PO Data")

    search_term = st.text_input("🔍 Search (PR No, PO No, Material, Vendor)", "")
    search_condition = ""
    if search_term:
        search_condition = f"""
        AND (
            no_pr ILIKE '%{search_term}%' OR
            nomor_po ILIKE '%{search_term}%' OR
            pr_description ILIKE '%{search_term}%' OR
            vendor_name ILIKE '%{search_term}%'
        )
        """

    table_query = f"""
    SELECT
        no_pr, line_item_pr, tgl_create_pr, department_code,
        material_no, pr_description, quantity_pr, satuan_pr, estimasi_pr,
        nomor_po, date_ordered, vendor_name, qty_po,
        total_amount_local_curr, efisiensi, lead_time_process_po,
        status_pengiriman, on_time_delivery
    FROM vw_pr_po_complete
    WHERE {filter_conditions} {search_condition}
      AND ({bagian_pr_cond} OR {bagian_po_cond})
    ORDER BY tgl_create_pr DESC
    LIMIT 100
    """

    with st.spinner("Memuat data tabel..."):
        table_data = load_data(table_query)

    if not table_data.empty:
        for col in ['estimasi_pr', 'total_amount_local_curr', 'efisiensi']:
            if col in table_data.columns:
                table_data[col] = table_data[col].apply(
                    lambda x: f"Rp {x:,.0f}" if pd.notna(x) else ""
                )
        for col in ['tgl_create_pr', 'date_ordered']:
            if col in table_data.columns:
                table_data[col] = pd.to_datetime(table_data[col]).dt.strftime('%Y-%m-%d')

        st.dataframe(table_data, use_container_width=True, height=400)
        csv = table_data.to_csv(index=False)
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name=f"pr_po_data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No data found matching your filters")

    # ── ADDITIONAL INSIGHTS ──────────────────────────
    st.markdown("---")
    st.header("💡 Additional Insights")

    st.subheader("⚠️ Top 10 PR Without PO (Pending)")
    pr_without_po_query = f"""
    SELECT
        no_pr, tgl_create_pr,
        department_code AS department,
        bagian_pr AS bagian,
        SUM(estimasi_pr) AS total_estimasi
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
        st.success("Great job! All PRs have been processed into POs. 🎉")

    st.markdown("<br>", unsafe_allow_html=True)

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("🚚 Delivery Performance")
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
        st.subheader("📊 Material Category Value")
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

# =====================================================
# HALAMAN 2: HALAMAN ALERT
# =====================================================

elif page == "🚨 Halaman Alert":

    st.title("🚨 Warning & Action Required")
    st.markdown("Halaman ini menampilkan anomali data dan dokumen yang membutuhkan tindakan segera.")
    st.markdown("---")

    # ALERT 1: PR > 30 hari belum ada PO
    st.subheader("1️⃣ PR Pending Mendekati Kadaluarsa (> 30 Hari)")
    st.info("Menampilkan PR yang belum diproses menjadi PO selama lebih dari 30 hari sejak dibuat.")

    alert_pr_query = f"""
    SELECT
        no_pr, tgl_create_pr,
        department_code AS department,
        bagian_pr AS bagian,
        estimasi_pr,
        CURRENT_DATE - tgl_create_pr::DATE AS umur_hari
    FROM vw_pr_po_complete
    WHERE {filter_conditions} AND nomor_po IS NULL AND no_pr != 'No PR'
      AND (CURRENT_DATE - tgl_create_pr::DATE) > 30
    ORDER BY umur_hari DESC
    """
    with st.spinner("Memuat alert PR..."):
        alert_pr_data = load_data(alert_pr_query)

    if not alert_pr_data.empty:
        alert_pr_data['tgl_create_pr'] = pd.to_datetime(alert_pr_data['tgl_create_pr']).dt.strftime('%Y-%m-%d')
        alert_pr_data['estimasi_pr'] = alert_pr_data['estimasi_pr'].apply(
            lambda x: f"Rp {x:,.0f}" if pd.notna(x) else ""
        )
        st.dataframe(alert_pr_data, use_container_width=True)
    else:
        st.success("✅ Aman! Tidak ada PR Pending yang umurnya lebih dari 30 hari.")

    st.markdown("<br>", unsafe_allow_html=True)

    col_alert1, col_alert2 = st.columns([2, 1])

    with col_alert1:
        st.subheader("2️⃣ PO Overdue (Melewati Delivery Date)")
        st.error("Menampilkan PO yang tanggal kirimnya sudah lewat namun barang belum diterima.")

        # FIX: hapus 'v.' prefix yang salah pada filter_conditions
        alert_po_query = f"""
        SELECT
            v.nomor_po,
            v.date_ordered,
            p.del_date_po AS target_delivery,
            v.vendor_name,
            v.on_time_delivery,
            CURRENT_DATE - p.del_date_po::DATE AS hari_terlambat
        FROM vw_pr_po_complete v
        LEFT JOIN purchase_orders p ON v.nomor_po = p.nomor_po
        WHERE {filter_conditions}
          AND v.nomor_po IS NOT NULL
          AND p.del_date_po::DATE < CURRENT_DATE
          AND v.on_time_delivery IN ('TERLAMBAT', 'IN PROGRESS')
        GROUP BY 1, 2, 3, 4, 5, 6
        ORDER BY hari_terlambat DESC
        """
        with st.spinner("Memuat PO overdue..."):
            alert_po_data = load_data(alert_po_query)

        if not alert_po_data.empty:
            alert_po_data['date_ordered']    = pd.to_datetime(alert_po_data['date_ordered']).dt.strftime('%Y-%m-%d')
            alert_po_data['target_delivery'] = pd.to_datetime(alert_po_data['target_delivery']).dt.strftime('%Y-%m-%d')
            st.dataframe(alert_po_data, use_container_width=True)
        else:
            st.success("✅ Aman! Tidak ada PO yang terlambat dari jadwal.")

    with col_alert2:
        st.subheader("3️⃣ Rekap Aging PO (Belum Dikirim)")

        aging_query = f"""
        SELECT
            CASE
                WHEN CURRENT_DATE - date_ordered::DATE <= 15 THEN '1. 0-15 Hari'
                WHEN CURRENT_DATE - date_ordered::DATE <= 30 THEN '2. 16-30 Hari'
                WHEN CURRENT_DATE - date_ordered::DATE <= 60 THEN '3. 31-60 Hari'
                ELSE '4. > 60 Hari'
            END AS umur_po,
            COUNT(DISTINCT nomor_po) AS total_po
        FROM vw_pr_po_complete
        WHERE {filter_conditions} AND nomor_po IS NOT NULL
          AND on_time_delivery IN ('TERLAMBAT', 'IN PROGRESS')
        GROUP BY 1
        ORDER BY 1
        """
        with st.spinner("Memuat aging PO..."):
            aging_data = load_data(aging_query)

        if not aging_data.empty:
            fig = px.bar(
                aging_data, x='umur_po', y='total_po',
                title="Umur PO Belum Diterima",
                labels={'umur_po': 'Aging (Hari)', 'total_po': 'Jumlah PO'},
                text_auto=True
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Tidak ada data aging PO.")

# =====================================================
# FOOTER
# =====================================================

st.markdown("---")
st.markdown(
    f"<div style='text-align:center;color:#666;'>"
    f"PR-PO Monitoring System | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    f"</div>",
    unsafe_allow_html=True
)
