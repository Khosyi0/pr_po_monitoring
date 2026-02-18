"""
PR-PO Monitoring Dashboard
File: dashboard.py

Run with: streamlit run dashboard.py
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
    
    # Mengambil data dari st.secrets (sesuai nama di file TOML tadi)
    db_config = st.secrets["postgres"]
    
    # Membuat Connection String untuk PostgreSQL
    # Format: postgresql://user:password@host:port/dbname
    connection_url = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
    
    # Membuat engine
    engine = create_engine(connection_url)
    return engine

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_data(query):
    """Load data from database with caching"""
    engine = get_db_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
    return df

# =====================================================
# CUSTOM CSS
# =====================================================

st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    h1 {
        color: #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

# =====================================================
# NAVIGATION MENU
# =====================================================
st.sidebar.title("🧭 Navigation")
page = st.sidebar.radio(
    "Pilih Halaman:",
    ["📊 Dashboard Monitoring", "🚨 Halaman Alert"],
    index=0
)
st.sidebar.markdown("---")

# =====================================================
# SIDEBAR FILTERS
# =====================================================

st.sidebar.header("🔍 Filters")

# Load filter options
# Load filter options
try:
    departments = load_data("SELECT DISTINCT department_code FROM departments ORDER BY department_code")
    
    # 🎯 PERBAIKAN: Mengambil data Bagian langsung dari View Transaksi (vw_pr_po_complete)
    # Ini memastikan 'Alpata', 'BB/BD/BP' muncul jika mereka ada di data PR/PO
    bagian_query = """
    SELECT DISTINCT bagian_pr as bagian FROM vw_pr_po_complete WHERE bagian_pr IS NOT NULL
    UNION
    SELECT DISTINCT bagian_po as bagian FROM vw_pr_po_complete WHERE bagian_po IS NOT NULL
    ORDER BY 1
    """
    bagian_data = load_data(bagian_query)
    
    vendors = load_data("SELECT DISTINCT vendor_name FROM vendors ORDER BY vendor_name")
    
    # --- FILTER DEPARTMENT ---
    selected_department = st.sidebar.multiselect(
        "Department",
        options=['All'] + departments['department_code'].tolist(),
        default=['All']
    )
    
    exclude_dept = False
    if 'All' not in selected_department and len(selected_department) > 0:
        exclude_dept = st.sidebar.checkbox("🚫 Exclude selected Department")
    
    # --- 🎯 FILTER BAGIAN (PENGGANTI PLANT) ---
    selected_bagian = st.sidebar.multiselect(
        "Bagian",
        options=['All'] + bagian_data['bagian'].tolist(),
        default=['All']
    )
    
    exclude_bagian = False
    if 'All' not in selected_bagian and len(selected_bagian) > 0:
        exclude_bagian = st.sidebar.checkbox("🚫 Exclude selected Bagian")
    
    # --- Date range ---
    st.sidebar.subheader("📅 Date Range")
    date_from = st.sidebar.date_input(
        "From",
        value=datetime.now() - timedelta(days=90)
    )
    date_to = st.sidebar.date_input(
        "To",
        value=datetime.now()
    )
    
    # Refresh button
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
        
except Exception as e:
    st.sidebar.error(f"Error loading filters: {e}")

# =====================================================
# BUILD FILTER QUERY
# =====================================================

def build_filter_conditions():
    """Build WHERE clause based on selected filters"""
    conditions = []
    conditions.append(f"tgl_create_pr >= '{date_from}'")
    conditions.append(f"tgl_create_pr <= '{date_to}'")
    
    # Filter Department & Plant tetap sama...
    if 'All' not in selected_department and len(selected_department) > 0:
        dept_list = "','".join(selected_department)
        conditions.append(f"(department_code NOT IN ('{dept_list}') OR department_code IS NULL)" if exclude_dept else f"department_code IN ('{dept_list}')")
        
    return " AND ".join(conditions) if conditions else "1=1"

filter_conditions = build_filter_conditions()

# 🎯 TAMBAHAN BARU: Pisahkan filter untuk PR dan PO
bagian_pr_cond = "1=1"
bagian_po_cond = "1=1"

if 'All' not in selected_bagian and len(selected_bagian) > 0:
    bagian_list = "','".join(selected_bagian)
    if exclude_bagian:
        bagian_pr_cond = f"(bagian_pr NOT IN ('{bagian_list}') OR bagian_pr IS NULL)"
        bagian_po_cond = f"(bagian_po NOT IN ('{bagian_list}') OR bagian_po IS NULL)"
    else:
        bagian_pr_cond = f"bagian_pr IN ('{bagian_list}')"
        bagian_po_cond = f"bagian_po IN ('{bagian_list}')"

# =====================================================
# MAIN DASHBOARD & ALERTS
# =====================================================

try:
    # Test connection
    engine = get_db_engine()
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    
    # Build filter
    filter_conditions = build_filter_conditions()

    # =====================================================
    # HALAMAN 1: DASHBOARD MONITORING
    # =====================================================

    if page == "📊 Dashboard Monitoring":

        st.title("📊 PR-PO Monitoring Dashboard")
        st.markdown("---")
    
        # =====================================================
        # KPI METRICS
        # =====================================================
        
        st.header("📈 Key Performance Indicators")
        
        # Query KPIs
        kpi_query = f"""
        SELECT 
            COUNT(DISTINCT CASE WHEN no_pr != 'No PR' AND {bagian_pr_cond} THEN (no_pr, line_item_pr) END) as total_pr, 
            
            COUNT(CASE WHEN {bagian_po_cond} THEN nomor_po END) as total_po,
            
            COUNT(DISTINCT CASE WHEN nomor_po IS NOT NULL AND no_pr != 'No PR' AND {bagian_pr_cond} THEN (no_pr, line_item_pr) END) as pr_with_po,
            COUNT(DISTINCT CASE WHEN nomor_po IS NULL AND {bagian_pr_cond} THEN (no_pr, line_item_pr) END) as pr_without_po,
            
            SUM(CASE WHEN {bagian_pr_cond} THEN estimasi_pr ELSE 0 END) as total_estimasi,
            SUM(CASE WHEN {bagian_po_cond} THEN total_amount_local_curr ELSE 0 END) as total_po_amount,
            
            SUM(CASE WHEN {bagian_pr_cond} THEN estimasi_pr ELSE 0 END - 
                CASE WHEN {bagian_po_cond} THEN COALESCE(total_amount_local_curr, 0) ELSE 0 END) as total_savings,
                
            AVG(CASE 
                WHEN total_amount_local_curr IS NOT NULL AND {bagian_pr_cond} AND {bagian_po_cond}
                THEN (estimasi_pr - total_amount_local_curr) / NULLIF(estimasi_pr, 0) * 100 
                END) as avg_savings_pct
                
        FROM vw_pr_po_complete
        WHERE {filter_conditions}
        """
        
        kpi_data = load_data(kpi_query)
        
        # Display metrics in columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Total PR",
                value=f"{kpi_data['total_pr'][0]:,}",
                delta=f"{kpi_data['pr_with_po'][0]:,} with PO"
            )
        
        with col2:
            st.metric(
                label="Total PO",
                value=f"{kpi_data['total_po'][0]:,}",
                delta=f"{kpi_data['pr_without_po'][0]:,} PR pending"
            )
        
        with col3:
            estimasi = kpi_data['total_estimasi'][0] or 0
            
            # Logika format angka Indonesia (Triliun, Miliar, Juta)
            if abs(estimasi) >= 1e12:
                est_str = f"Rp {estimasi/1e12:.2f} T"
            elif abs(estimasi) >= 1e9:
                est_str = f"Rp {estimasi/1e9:.2f} M"
            elif abs(estimasi) >= 1e6:
                est_str = f"Rp {estimasi/1e6:.2f} Jt"
            else:
                est_str = f"Rp {estimasi:,.0f}"
                
            st.metric(label="Total Estimasi PR", value=est_str)
        
        with col4:
            savings = kpi_data['total_savings'][0] or 0
            savings_pct = kpi_data['avg_savings_pct'][0] or 0
            
            # Logika format angka Indonesia (Triliun, Miliar, Juta)
            if abs(savings) >= 1e12:
                sav_str = f"Rp {savings/1e12:.2f} T"
            elif abs(savings) >= 1e9:
                sav_str = f"Rp {savings/1e9:.2f} M"
            elif abs(savings) >= 1e6:
                sav_str = f"Rp {savings/1e6:.2f} Jt"
            else:
                sav_str = f"Rp {savings:,.0f}"
                
            st.metric(
                label="Total Savings", 
                value=sav_str, 
                delta=f"{savings_pct:.1f}% avg"
            )
        
        st.markdown("---")
        
        # =====================================================
        # CHARTS ROW 1
        # =====================================================
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 PR Status by Department")
            
            dept_query = f"""
            SELECT 
                COALESCE(department_code, 'Unknown') as department,
                COUNT(DISTINCT no_pr) as total_pr,
                COUNT(DISTINCT CASE WHEN nomor_po IS NOT NULL THEN no_pr END) as pr_with_po
            FROM vw_pr_po_complete
            WHERE {filter_conditions} AND {bagian_pr_cond}
            GROUP BY department_code
            ORDER BY total_pr DESC
            LIMIT 10
            """
            
            dept_data = load_data(dept_query)
            
            if not dept_data.empty:
                fig = go.Figure(data=[
                    go.Bar(name='PR with PO', x=dept_data['department'], y=dept_data['pr_with_po']),
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
                COALESCE(vendor_name, 'Unknown') as vendor,
                COUNT(DISTINCT nomor_po) as total_po,
                SUM(total_amount_local_curr) as total_value
            FROM vw_pr_po_complete
            WHERE {filter_conditions} AND nomor_po IS NOT NULL AND {bagian_po_cond}
            GROUP BY vendor_name
            ORDER BY total_value DESC
            LIMIT 10
            """
            
            vendor_data = load_data(vendor_query)
            
            if not vendor_data.empty:
                fig = px.bar(
                    vendor_data,
                    x='total_value',
                    y='vendor',
                    orientation='h',
                    title='',
                    labels={'total_value': 'Total Value (IDR)', 'vendor': 'Vendor'}
                )
                fig.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data available")
        
        # =====================================================
        # CHARTS ROW 2
        # =====================================================
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📅 PR-PO Creation Trend")
            
            trend_query = f"""
            WITH pr_monthly AS (
                SELECT 
                    DATE_TRUNC('month', tgl_create_pr) as month_date,
                    COUNT(DISTINCT CASE WHEN no_pr != 'No PR' AND {bagian_pr_cond} THEN (no_pr, line_item_pr) END) as total_pr
                FROM vw_pr_po_complete
                WHERE tgl_create_pr IS NOT NULL AND {filter_conditions}
                GROUP BY 1
            ),
            po_monthly AS (
                SELECT 
                    DATE_TRUNC('month', date_ordered) as month_date,
                    COUNT(CASE WHEN {bagian_po_cond} THEN nomor_po END) as total_po
                FROM vw_pr_po_complete
                WHERE date_ordered IS NOT NULL AND {filter_conditions}
                GROUP BY 1
            )
            SELECT 
                COALESCE(pr.month_date, po.month_date) as month,
                COALESCE(pr.total_pr, 0) as total_pr,
                COALESCE(po.total_po, 0) as total_po
            FROM pr_monthly pr
            FULL OUTER JOIN po_monthly po ON pr.month_date = po.month_date
            ORDER BY month
            """
            
            trend_data = load_data(trend_query)
            
            if not trend_data.empty:
                trend_data['month'] = pd.to_datetime(trend_data['month'])
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=trend_data['month'],
                    y=trend_data['total_pr'],
                    mode='lines+markers',
                    name='PR Created',
                    line=dict(color='#1f77b4', width=2)
                ))
                fig.add_trace(go.Scatter(
                    x=trend_data['month'],
                    y=trend_data['total_po'],
                    mode='lines+markers',
                    name='PO Created',
                    line=dict(color='#2ca02c', width=2)
                ))
                fig.update_layout(height=400, xaxis_title='Month', yaxis_title='Count')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data available")
        
        with col2:
            st.subheader("⏱️ Lead Time Distribution")
            
            # PERBAIKAN QUERY: Mengganti ORDER BY yang error
            leadtime_query = f"""
            SELECT 
                CASE 
                    WHEN lead_time_process_po <= 7 THEN '0-7 days'
                    WHEN lead_time_process_po <= 14 THEN '8-14 days'
                    WHEN lead_time_process_po <= 30 THEN '15-30 days'
                    WHEN lead_time_process_po <= 60 THEN '31-60 days'
                    ELSE '60+ days'
                END as lead_time_range,
                COUNT(*) as count
            FROM vw_pr_po_complete
            WHERE {filter_conditions} AND lead_time_process_po IS NOT NULL AND {bagian_po_cond}
            GROUP BY 
                CASE 
                    WHEN lead_time_process_po <= 7 THEN '0-7 days'
                    WHEN lead_time_process_po <= 14 THEN '8-14 days'
                    WHEN lead_time_process_po <= 30 THEN '15-30 days'
                    WHEN lead_time_process_po <= 60 THEN '31-60 days'
                    ELSE '60+ days'
                END
            ORDER BY MIN(lead_time_process_po) ASC
            """
            
            leadtime_data = load_data(leadtime_query)
            
            if not leadtime_data.empty:
                fig = px.pie(
                    leadtime_data,
                    values='count',
                    names='lead_time_range',
                    title='',
                    hole=0.4
                )
                fig.update_traces(sort=False)
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data available")
        
        # =====================================================
        # DATA TABLE
        # =====================================================
        
        st.markdown("---")
        st.header("📋 Detailed PR-PO Data")
        
        # Add search
        search_term = st.text_input("🔍 Search (PR No, PO No, Material, Vendor)", "")
        
        # Query with search
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
            no_pr,
            line_item_pr,
            tgl_create_pr,
            department_code,
            material_no,
            pr_description,
            quantity_pr,
            satuan_pr,
            estimasi_pr,
            nomor_po,
            date_ordered,
            vendor_name,
            qty_po,
            total_amount_local_curr,
            efisiensi,
            lead_time_process_po,
            status_pengiriman,
            on_time_delivery
        FROM vw_pr_po_complete
        WHERE {filter_conditions} {search_condition} AND ({bagian_pr_cond} OR {bagian_po_cond})
        ORDER BY tgl_create_pr DESC
        LIMIT 100
        """
        
        table_data = load_data(table_query)
        
        if not table_data.empty:
            # Format currency columns
            currency_cols = ['estimasi_pr', 'total_amount_local_curr', 'efisiensi']
            for col in currency_cols:
                if col in table_data.columns:
                    table_data[col] = table_data[col].apply(
                        lambda x: f"Rp {x:,.0f}" if pd.notna(x) else ""
                    )
            
            # Format date columns
            date_cols = ['tgl_create_pr', 'date_ordered']
            for col in date_cols:
                if col in table_data.columns:
                    table_data[col] = pd.to_datetime(table_data[col]).dt.strftime('%Y-%m-%d')
            
            st.dataframe(table_data, use_container_width=True, height=400)
            
            # Download button
            csv = table_data.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"pr_po_data_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No data found matching your filters")
        
        # =====================================================
        # ADDITIONAL INSIGHTS
        # =====================================================
        
        st.markdown("---")
        st.header("💡 Additional Insights")
        
        # --- BARIS ATAS: Tabel PR Without PO (Melebar Penuh) ---
        # Kita tidak pakai 'with col:' di sini agar dia mengambil lebar penuh
        
        st.subheader("⚠️ Top 10 PR Without PO (Pending)")
        
        pr_without_po_query = f"""
        SELECT 
            no_pr,
            tgl_create_pr,
            department_code as department,
            bagian_pr as bagian,
            SUM(estimasi_pr) as total_estimasi
        FROM vw_pr_po_complete
        WHERE {filter_conditions} AND nomor_po IS NULL AND no_pr != 'No PR' AND {bagian_pr_cond}
        GROUP BY no_pr, tgl_create_pr, department_code, bagian_pr
        ORDER BY tgl_create_pr ASC
        LIMIT 10
        """
        
        pr_without_po = load_data(pr_without_po_query)
        
        if not pr_without_po.empty:
            # Format tanggal dan mata uang agar tabel lebih cantik
            pr_without_po['tgl_create_pr'] = pd.to_datetime(pr_without_po['tgl_create_pr']).dt.strftime('%Y-%m-%d')
            pr_without_po['total_estimasi'] = pr_without_po['total_estimasi'].apply(lambda x: f"Rp {x:,.0f}")
            # Tampilkan tabel dengan tinggi tetap agar rapi
            st.dataframe(pr_without_po, use_container_width=True, height=300)
        else:
            st.success("Great job! All PRs have been processed into POs. 🎉")
            
        # Beri sedikit jarak vertikal
        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- BARIS BAWAH: Dua Chart Berdampingan ---
        # Kita buat 2 kolom baru di bawah tabel
        col_chart1, col_chart2 = st.columns(2)
        
        # Kolom Kiri: Delivery Performance
        with col_chart1:
            st.subheader("🚚 Delivery Performance")
            
            delivery_query = f"""
            SELECT 
                COALESCE(on_time_delivery, 'PENDING') as status_delivery,
                COUNT(*) as count
            FROM vw_pr_po_complete
            WHERE {filter_conditions} AND {bagian_po_cond} 
            AND nomor_po IS NOT NULL  -- Pastikan ini PO, bukan PR yang belum jadi PO
            GROUP BY COALESCE(on_time_delivery, 'PENDING')
            """
            delivery_data = load_data(delivery_query)
            
            if not delivery_data.empty:
                # Update map warna untuk status PENDING
                color_map = {
                    'TEPAT WAKTU': '#2ca02c',   # Hijau
                    'IN PROGRESS': '#ff7f0e',   # Oranye
                    'TERLAMBAT': '#d62728',     # Merah
                    'PENDING': '#7f7f7f'        # Abu-abu (untuk data NULL)
                }
                
                fig = px.pie(
                    delivery_data,
                    values='count',
                    names='status_delivery', # Sesuaikan dengan alias di query
                    title='',
                    color='status_delivery',
                    color_discrete_map=color_map,
                    hole=0.4
                )
                fig.update_layout(height=350, margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No delivery data available for selected criteria.")
        
        # Kolom Kanan: Material Category
        with col_chart2:
            st.subheader("📊 Material Category Value")
            
            material_query = f"""
            SELECT 
                abc_indicator,
                SUM(total_amount_local_curr) as total_value
            FROM vw_pr_po_complete
            WHERE {filter_conditions} AND abc_indicator IS NOT NULL AND {bagian_po_cond}
            GROUP BY abc_indicator
            ORDER BY abc_indicator
            """
            
            material_data = load_data(material_query)
            
            if not material_data.empty:
                material_data['total_value'] = material_data['total_value'].fillna(0)
                
                # --- FUNGSI FORMAT ANGKA INDONESIA KHUSUS GRAFIK ---
                def format_idr_short(x):
                    if abs(x) >= 1e12:
                        return f"{x/1e12:.1f} T"
                    elif abs(x) >= 1e9:
                        return f"{x/1e9:.1f} M"
                    elif abs(x) >= 1e6:
                        return f"{x/1e6:.1f} Jt"
                    else:
                        return f"{x:,.0f}"
                
                # Terapkan fungsi di atas ke kolom baru bernama 'label_text'
                material_data['label_text'] = material_data['total_value'].apply(format_idr_short)
                
                fig = px.bar(
                    material_data,
                    x='abc_indicator',
                    y='total_value',
                    title='',
                    labels={'abc_indicator': 'ABC Category', 'total_value': 'Total PO Value (IDR)'},
                    text='label_text' # GANTI text_auto menjadi text kustom kita
                )
                fig.update_layout(height=350, margin=dict(t=20, b=0, l=0, r=0))
                
                # Modifikasi tampilan teks dan saat kursor diarahkan (hover)
                fig.update_traces(
                    textfont_size=12, 
                    textangle=0, 
                    textposition="outside", 
                    cliponaxis=False,
                    hovertemplate="<b>ABC Category: %{x}</b><br>Total PO Value: Rp %{text}<extra></extra>"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No material data available for selected criteria.")

    # -------------------------------------------------------------------
    # HALAMAN 2: HALAMAN ALERT (Baru)
    # -------------------------------------------------------------------
    elif page == "🚨 Halaman Alert":
        
        st.title("🚨 Warning & Action Required")
        st.markdown("Halaman ini menampilkan anomali data dan dokumen yang membutuhkan tindakan segera.")
        st.markdown("---")
        
        # ALERT 1: PR KADALUARSA (Contoh: PR sudah lebih dari 30 hari tapi belum ada PO)
        st.subheader("1️⃣ PR Pending Mendekati Kadaluarsa (> 30 Hari)")
        st.info("Menampilkan PR yang belum diproses menjadi PO selama lebih dari 30 hari sejak dibuat.")
        
        alert_pr_query = f"""
        SELECT 
            no_pr,
            tgl_create_pr,
            department_code as department,
            bagian_pr as bagian,
            estimasi_pr,
            CURRENT_DATE - tgl_create_pr::DATE as umur_hari
        FROM vw_pr_po_complete
        WHERE {filter_conditions} AND nomor_po IS NULL AND no_pr != 'No PR'
        AND (CURRENT_DATE - tgl_create_pr::DATE) > 30 
        ORDER BY umur_hari DESC
        """
        alert_pr_data = load_data(alert_pr_query)
        if not alert_pr_data.empty:
            alert_pr_data['tgl_create_pr'] = pd.to_datetime(alert_pr_data['tgl_create_pr']).dt.strftime('%Y-%m-%d')
            alert_pr_data['estimasi_pr'] = alert_pr_data['estimasi_pr'].apply(lambda x: f"Rp {x:,.0f}" if pd.notna(x) else "")
            st.dataframe(alert_pr_data, use_container_width=True)
        else:
            st.success("✅ Aman! Tidak ada PR Pending yang umurnya lebih dari 30 hari.")
            
        st.markdown("<br>", unsafe_allow_html=True)
            
        # ALERT 2 & 3: PO OVERDUE DAN AGING RECAP
        col_alert1, col_alert2 = st.columns([2, 1])
        
        with col_alert1:
            st.subheader("2️⃣ PO Overdue (Melewati Delivery Date)")
            st.error("Menampilkan PO yang tanggal kirimnya (Delivery Date) sudah lewat hari ini namun barang belum diterima penuh.")
            
            # Catatan: Karena kita butuh Delivery Date PO, kita Join langsung ke tabel purchase_orders
            alert_po_query = f"""
            SELECT 
                v.nomor_po,
                v.date_ordered,
                p.del_date_po as target_delivery,
                v.vendor_name,
                v.on_time_delivery,
                CURRENT_DATE - p.del_date_po::DATE as hari_terlambat
            FROM vw_pr_po_complete v
            LEFT JOIN purchase_orders p ON v.nomor_po = p.nomor_po
            WHERE v.{filter_conditions} AND v.nomor_po IS NOT NULL 
            AND p.del_date_po::DATE < CURRENT_DATE
            AND v.on_time_delivery IN ('TERLAMBAT', 'IN PROGRESS') 
            GROUP BY 1, 2, 3, 4, 5, 6
            ORDER BY hari_terlambat DESC
            """
            alert_po_data = load_data(alert_po_query)
            if not alert_po_data.empty:
                alert_po_data['date_ordered'] = pd.to_datetime(alert_po_data['date_ordered']).dt.strftime('%Y-%m-%d')
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
                COUNT(DISTINCT nomor_po) as total_po
            FROM vw_pr_po_complete
            WHERE {filter_conditions} AND nomor_po IS NOT NULL 
            AND on_time_delivery IN ('TERLAMBAT', 'IN PROGRESS')
            GROUP BY 1
            ORDER BY 1
            """
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

except Exception as e:
    st.error(f"❌ Error: {e}")
    st.info("""
    **Troubleshooting:**
    1. Check database connection in code
    2. Make sure PostgreSQL is running
    3. Verify database credentials
    4. Ensure ETL process completed successfully
    """)
    
    import traceback
    with st.expander("Show error details"):
        st.code(traceback.format_exc())

# =====================================================
# FOOTER
# =====================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>PR-PO Monitoring System | Last updated: {}</p>
</div>
""".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')), unsafe_allow_html=True)
