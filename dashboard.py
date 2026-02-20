"""
PR-PO Monitoring Dashboard (Update v1.7 - Halaman Kinerja Purchasing Group)
File: dashboard.py

Run with: streamlit run dashboard.py

Update:
- Sebelumnya langsung tabel, sekarang ada ringkasan angka besar dulu
- Tab 1 — Overview per Purchasing Group
- Menambah kolom % PR→PO, % Efisiensi, Lead Time Min/Max
- Chart bar horizontal % Efisiensi, Chart bar horizontal Lead Time, Chart bar horizontal % Konversi PR→PO
- Tab 2 — Breakdown per Metode Tender
- Metric cards per metode tender (Tender Normal / Kontrak / dll)
- Stacked bar: komposisi nilai realisasi per PG berdasarkan metode
- Grouped bar: lead time per metode per PG
- Tabel detail PG × Metode Tender + tombol download CSV

"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
from streamlit_option_menu import option_menu
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
# SESSION STATE INITIALIZATION
# =====================================================
if 'show_changelog' not in st.session_state:
    st.session_state.show_changelog = False

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
    
    # Tentukan skala dan suffix
    if abs(x) >= 1e12:
        val = x / 1e12
        suffix = "T"
    elif abs(x) >= 1e9:
        val = x / 1e9
        suffix = "M"
    elif abs(x) >= 1e6:
        val = x / 1e6
        suffix = "Jt"
    else:
        # Di bawah 1 Juta, tampilkan tanpa desimal dan koma
        formatted = f"{x:,.0f}".replace(',', '.')
        return f"Rp {formatted}"
        
    # Format angka dengan separator koma bawaan Python (standar US)
    # Contoh output awal: "231,312.80"
    formatted = f"{val:,.2f}" 
    
    # Tukar koma menjadi titik (ribuan), dan titik menjadi koma (desimal)
    # Menjadi: "231.312,80"
    formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
    
    return f"Rp {formatted} {suffix}"

def format_idr_short(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "0"
        
    if abs(x) >= 1e12:
        val = x / 1e12
        suffix = "T"
    elif abs(x) >= 1e9:
        val = x / 1e9
        suffix = "M"
    elif abs(x) >= 1e6:
        val = x / 1e6
        suffix = "Jt"
    else:
        return f"{x:,.0f}".replace(',', '.')
        
    # Format untuk chart/grafik, biasanya cukup 1 angka di belakang koma
    formatted = f"{val:,.1f}" 
    formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
    
    return f"{formatted} {suffix}"

# =====================================================
# CUSTOM CSS (ADAPTIVE)
# =====================================================

st.markdown("""
<style>
    /* Sidebar Text */
    /* Gunakan var(--text-color) agar otomatis:
       - Hitam saat Light Mode
       - Putih saat Dark Mode */
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] div {
        color: var(--text-color);
    }
    
    /* Heading Utama */
    /* Warna biru #1f77b4 cukup aman di kedua mode (kontras cukup).
       Jika ingin otomatis ikut tema warna primer, ganti dengan var(--primary-color) */
    h1 { 
        color: #1f77b4; 
    }
    
    /* Opsional: Memperbaiki tampilan widget di sidebar agar konsisten */
    .stMultiSelect, .stDateInput {
        background-color: transparent;
    }
</style>
""", unsafe_allow_html=True)

# =====================================================
# NAVIGATION (MODIFIED STYLE - ADAPTIVE COLOR)
# =====================================================

with st.sidebar:
    # Menggunakan streamlit-option-menu
    page = option_menu(
        menu_title="Main Menu",  # Judul Menu
        options=["Dashboard Monitoring", "Detailed PR-PO Data", "Evaluasi Harga Barang", "Kinerja Purchasing Group", "Halaman Alert"],
        icons=["bar-chart-fill", "file-earmark-text-fill", "tag-fill", "briefcase-fill", "exclamation-triangle-fill"],
        menu_icon="cast", 
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            
            # Ganti "white" menjadi "var(--text-color)"
            # Ini agar icon otomatis hitam di Light Mode dan putih di Dark Mode
            "icon": {"color": "var(--text-color)", "font-size": "18px"}, 
            
            "nav-link": {
                "font-size": "16px", 
                "text-align": "left", 
                "margin": "5px", 
                
                # Ganti "white" menjadi "var(--text-color)"
                "color": "var(--text-color)",
                
                # Warna saat mouse hover (opsional: #eee cocok untuk light mode)
                "--hover-color": "var(--secondary-background-color)"
            },
            
            "nav-link-selected": {"background-color": "#ff4b4b", "color": "white"}, # Tetap merah & putih saat dipilih
            
            # Judul menu juga ikut variabel
            "menu-title": {"color": "var(--text-color)", "font-size": "18px", "font-weight": "bold"}
        }
    )
    st.markdown("---")

    # Logic agar Changelog otomatis tertutup jika menu sidebar diklik
    if 'last_page' not in st.session_state:
        st.session_state.last_page = page
        
    if page != st.session_state.last_page:
        st.session_state.show_changelog = False
        st.session_state.last_page = page

# =====================================================
# DEFAULT VALUES (wajib ada sebelum try block)
# =====================================================

date_from = datetime.now().date() - timedelta(days=90)
date_to = datetime.now().date()
selected_department = ['All']
selected_bagian = ['All']
exclude_dept = False
exclude_purchasing_group = False
exclude_bagian = False

# =====================================================
# SIDEBAR FILTERS
# =====================================================

st.sidebar.markdown(f"""
    <h2 style='display: flex; align-items: center; font-size: 20px; color: var(--text-color); margin-top: -20px;'>
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-funnel-fill" viewBox="0 0 16 16" style="margin-right: 10px;">
            <path d="M1.5 1.5A.5.5 0 0 1 2 1h12a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-.128.334L10 8.692V13.5a.5.5 0 0 1-.342.474l-3 1A.5.5 0 0 1 6 14.5V8.692L1.628 3.834A.5.5 0 0 1 1.5 3.5z"/>
        </svg>
        Filters
    </h2>
    """, unsafe_allow_html=True)

try:
    # 1. Load Data
    departments = load_data(
        "SELECT DISTINCT department_code FROM departments ORDER BY department_code"
    )
    
    bagian_data = load_data("""
        SELECT DISTINCT bagian_pr AS bagian FROM vw_pr_po_complete 
        WHERE bagian_pr IS NOT NULL
        UNION
        SELECT DISTINCT bagian_po AS bagian FROM vw_pr_po_complete 
        WHERE bagian_po IS NOT NULL
        ORDER BY 1
    """)
    
    options_bagian = ['All'] + bagian_data['bagian'].tolist()

    p_group_data = load_data("""
        SELECT DISTINCT purchasing_group FROM purchase_requisitions 
        WHERE purchasing_group IS NOT NULL
        UNION
        SELECT DISTINCT purchasing_group FROM purchase_orders 
        WHERE purchasing_group IS NOT NULL
        ORDER BY 1
    """)
    options_p_group = ['All'] + p_group_data['purchasing_group'].tolist()

    # -------------------------------------------------------------------------
    # LOGIC HANDLING 'ALL' vs 'LAINNYA'
    # -------------------------------------------------------------------------
    
    # Inisialisasi state jika belum ada
    if 'filter_bagian' not in st.session_state:
        st.session_state.filter_bagian = ['All']
    if 'prev_filter_bagian' not in st.session_state:
        st.session_state.prev_filter_bagian = ['All']

    def update_bagian_logic():
        """Callback untuk mengatur logika eksklusif 'All'"""
        current = st.session_state.filter_bagian
        prev = st.session_state.prev_filter_bagian
        
        # Skenario 1: User baru saja klik 'All' (sebelumnya tidak ada 'All')
        if 'All' in current and 'All' not in prev:
            st.session_state.filter_bagian = ['All']
            
        # Skenario 2: User klik opsi lain saat 'All' masih aktif
        elif 'All' in current and len(current) > 1:
            # Hapus 'All' dari list, sisakan yang baru dipilih
            st.session_state.filter_bagian = [x for x in current if x != 'All']
            
        # Skenario 3: User uncheck semua (kosong) -> paksa kembali ke 'All'
        elif not current:
            st.session_state.filter_bagian = ['All']
            
        # Update state 'sebelumnya' untuk perbandingan berikutnya
        st.session_state.prev_filter_bagian = st.session_state.filter_bagian

    # -------------------------------------------------------------------------
    # WIDGETS
    # -------------------------------------------------------------------------

    # Filter Department
    st.sidebar.markdown(f"""
    <h2 style='display: flex; align-items: center; font-size: 16px; color: var(--text-color);'>
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-calendar-event" viewBox="0 0 16 16" style="margin-right: 8px; margin-bottom: 3px;">
            <path d="M3 0a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h3v-3.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 .5.5V16h3a1 1 0 0 0 1-1V1a1 1 0 0 0-1-1zm1 2.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm3 0a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm3.5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5M4 5.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zM7.5 5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5m2.5.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zM4.5 8h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5m2.5.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm3.5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5"/>
        </svg>
        Department
    </h2>
    """, unsafe_allow_html=True)
    selected_department = st.sidebar.multiselect(
        "Department",
        options=['All'] + departments['department_code'].tolist(),
        default=['All'],
        label_visibility="collapsed"
    )

    exclude_dept = False
    if 'All' not in selected_department and len(selected_department) > 0:
        exclude_dept = st.sidebar.checkbox(":material/block: Exclude selected Department")

    # Filter Purchasing Group
    st.sidebar.markdown(f"""
    <h2 style='display: flex; align-items: center; font-size: 16px; color: var(--text-color); margin-bottom: -10px;'>
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-people-fill" viewBox="0 0 16 16" style="margin-right: 8px; margin-bottom: 3px;">
            <path d="M7 14s-1 0-1-1 1-4 5-4 5 3 5 4-1 1-1 1zm4-6a3 3 0 1 0 0-6 3 3 0 0 0 0 6m-5.784 6A2.24 2.24 0 0 1 5 13c0-1.355.68-2.75 1.936-3.72A6.3 6.3 0 0 0 5 9c-4 0-5 3-5 4s1 1 1 1zM4.5 8a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5"/>
        </svg>
        Purchasing Group
    </h2>
    """, unsafe_allow_html=True)

    selected_p_group = st.sidebar.multiselect(
        "Purchasing Group Selection",
        options=options_p_group,
        default=['All'],
        label_visibility="collapsed"
    )

    exclude_purchasing_group = False
    if 'All' not in selected_p_group and len(selected_p_group) > 0:
        exclude_purchasing_group = st.sidebar.checkbox(":material/block: Exclude selected Purchasing Group")


    # Filter Bagian (Dengan Logic Baru)
    # Perhatikan: kita pakai 'key' dan 'on_change', tidak pakai 'default' lagi
    st.sidebar.markdown(f"""
    <h2 style='display: flex; align-items: center; font-size: 16px; color: var(--text-color);'>
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-calendar-event" viewBox="0 0 16 16" style="margin-right: 8px; margin-bottom: 3px;">
            <path d="M7 14s-1 0-1-1 1-4 5-4 5 3 5 4-1 1-1 1zm4-6a3 3 0 1 0 0-6 3 3 0 0 0 0 6m-5.784 6A2.24 2.24 0 0 1 5 13c0-1.355.68-2.75 1.936-3.72A6.3 6.3 0 0 0 5 9c-4 0-5 3-5 4s1 1 1 1zM4.5 8a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5"/>
        </svg>
        Bagian
    </h2>
    """, unsafe_allow_html=True)
    st.sidebar.pills(
        "Bagian",
        options=options_bagian,
        selection_mode="multi",
        key="filter_bagian",           # Terhubung ke st.session_state
        on_change=update_bagian_logic,  # Jalankan fungsi logic tiap kali diklik
        label_visibility="collapsed"
    )
    
    # Ambil nilai final dari session state untuk dipakai di query
    selected_bagian = st.session_state.filter_bagian

    # Filter Tanggal
    st.sidebar.markdown(f"""
    <h2 style='display: flex; align-items: center; font-size: 16px; color: var(--text-color); margin-bottom: -10px;'>
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-calendar-event" viewBox="0 0 16 16" style="margin-right: 8px; margin-bottom: 3px;">
            <path d="M11 6.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5z"/>
            <path d="M3.5 0a.5.5 0 0 1 .5.5V1h8V.5a.5.5 0 0 1 1 0V1h1a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2h1V.5a.5.5 0 0 1 .5-.5M1 4v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V4z"/>
        </svg>
        Date Range
    </h2>
    """, unsafe_allow_html=True)
    date_from = st.sidebar.date_input("From", value=datetime.now().date() - timedelta(days=90))
    date_to = st.sidebar.date_input("To", value=datetime.now().date())

    if st.sidebar.button("Refresh Data", icon=":material/refresh:"):
        st.cache_data.clear()
        st.rerun()

except Exception as e:
    st.sidebar.error(f"Error loading filters: {e}")

# =====================================================
# BUILD FILTER CONDITIONS
# =====================================================

def build_filter_conditions(date_from, date_to, selected_department, exclude_dept, selected_p_group, exclude_purchasing_group):
    conditions = [
        f"tgl_create_pr >= '{date_from}'",
        f"tgl_create_pr <= '{date_to}'"
    ]

    # Filter department
    if selected_department and 'All' not in selected_department:
        dept_list = "','".join(selected_department)
        if exclude_dept:
            conditions.append(f"(department_code NOT IN ('{dept_list}') OR department_code IS NULL)")
        else:
            conditions.append(f"department_code IN ('{dept_list}')")

    # Filter purchasing group
    if selected_p_group and 'All' not in selected_p_group:
        p_group_list = "','".join(selected_p_group)
        if exclude_purchasing_group:
            conditions.append(f"(purchasing_group NOT IN ('{p_group_list}') OR purchasing_group IS NULL)")
        else:
            conditions.append(f"purchasing_group IN ('{p_group_list}')")

    return " AND ".join(conditions)

filter_conditions = build_filter_conditions(date_from, date_to, selected_department, exclude_dept, selected_p_group, exclude_purchasing_group)

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
# RENDER HALAMAN LOG PERUBAHAN
# =====================================================
if st.session_state.show_changelog:
    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:40px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="35" height="35" fill="currentColor" class="bi bi-journal-code" viewBox="0 0 16 16" style="margin-bottom: 8px; margin-right: 12px;">
                <path fill-rule="evenodd" d="M8.646 5.646a.5.5 0 0 1 .708 0l2 2a.5.5 0 0 1 0 .708l-2 2a.5.5 0 0 1-.708-.708L10.293 8 8.646 6.354a.5.5 0 1 1 .708-.708zm-1.292 0a.5.5 0 0 0-.708 0l-2 2a.5.5 0 0 0 0 .708l2 2a.5.5 0 0 0 .708-.708L5.707 8l1.647-1.646a.5.5 0 0 0 0-.708z"/>
                <path d="M3 0h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2v-1h1v1a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1H3a1 1 0 0 0-1 1v1H1V2a2 2 0 0 1 2-2z"/>
                <path d="M1 5v-.5a.5.5 0 0 1 1 0V5h.5a.5.5 0 0 1 0 1h-2a.5.5 0 0 1 0-1H1zm0 3v-.5a.5.5 0 0 1 1 0V8h.5a.5.5 0 0 1 0 1h-2a.5.5 0 0 1 0-1H1zm0 3v-.5a.5.5 0 0 1 1 0v.5h.5a.5.5 0 0 1 0 1h-2a.5.5 0 0 1 0-1H1z"/>
            </svg>
            System Changelog
        </h1>
    """, unsafe_allow_html=True)
    st.markdown("Catatan pembaruan, perbaikan bug, dan penambahan fitur pada dashboard PR-PO Monitoring.")
    st.markdown("---")

    # Data tabel diisi manual di sini
    changelog_data = [
        {"Tanggal": "20 Feb 2026", "Versi": "v1.7", "Perubahan": "Memperkaya info di Halaman Kinerja Purchasing Group"},
        {"Tanggal": "19 Feb 2026", "Versi": "v1.6", "Perubahan": "Memperbarui tampilan UI, menambahkan halaman Kinerja Purchasing Group, dan menambahkan Changelog."},
        {"Tanggal": "18 Feb 2026", "Versi": "v1.5", "Perubahan": "Optimisasi Query, Deployment Website, dan menambahkan halaman Evaluasi Harga Barang."},
        {"Tanggal": "17 Feb 2026", "Versi": "v1.4", "Perubahan": "Update Struktur Database dan Persiapan Deployment Website."},
        {"Tanggal": "13 Feb 2026", "Versi": "v1.3", "Perubahan": "Menambahkan halaman alert."},
        {"Tanggal": "12 Feb 2026", "Versi": "v1.2", "Perubahan": "Perbaikan logika select Total PR dan Total PO."},
        {"Tanggal": "11 Feb 2026", "Versi": "v1.1", "Perubahan": "Menampilkan beberapa info monitoring."},
        {"Tanggal": "10 Feb 2026", "Versi": "v1.0", "Perubahan": "Rilis awal dashboard monitoring."}
    ]
    
    df_changelog = pd.DataFrame(changelog_data)
    st.dataframe(df_changelog, width="stretch", hide_index=True)

# =====================================================
# HALAMAN 1: DASHBOARD MONITORING
# =====================================================

else:
    if page == "Dashboard Monitoring":

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
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:30px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 6px; margin-right: 8px;">
                        <path d="M1 11a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1zm5-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1zm5-5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1z"/>
                    </svg>
                    PR Status by Department
                </h1>
            """, unsafe_allow_html=True)
            
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
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("Tidak ada data yang tersedia.")

        with col2:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:30px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-cash-stack" viewBox="0 0 16 16" style="margin-bottom: 6px; margin-right: 8px;">
                        <path d="M1 3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1zm7 8a2 2 0 1 0 0-4 2 2 0 0 0 0 4"/>
                        <path d="M0 5a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H1a1 1 0 0 1-1-1zm3 0a2 2 0 0 1-2 2v4a2 2 0 0 1 2 2h10a2 2 0 0 1 2-2V7a2 2 0 0 1-2-2z"/>
                    </svg>
                    Top 10 Vendors by PO Value
                </h1>
            """, unsafe_allow_html=True)

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
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("Tidak ada data yang tersedia.")

        # ── CHARTS ROW 2 ─────────────────────────────────
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:30px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 6px; margin-right: 8px;">
                        <path d="M11 6.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5z"/>
                        <path d="M3.5 0a.5.5 0 0 1 .5.5V1h8V.5a.5.5 0 0 1 1 0V1h1a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2h1V.5a.5.5 0 0 1 .5-.5M1 4v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V4z"/>
                    </svg>
                    PR-PO Creation Trend
                </h1>
            """, unsafe_allow_html=True)
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
                
                trend_data['total_pr'] = trend_data['total_pr'].cumsum()
                trend_data['total_po'] = trend_data['total_po'].cumsum()

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=trend_data['month'], y=trend_data['total_pr'],
                                        mode='lines+markers', name='PR Created',
                                        line=dict(color='#1f77b4', width=2)))
                fig.add_trace(go.Scatter(x=trend_data['month'], y=trend_data['total_po'],
                                        mode='lines+markers', name='PO Created',
                                        line=dict(color='#2ca02c', width=2)))
                
                fig.update_layout(height=400, xaxis_title='Month', yaxis_title='Cumulative Count')
                
                st.plotly_chart(fig, use_container_width=True) 
            else:
                st.info("Tidak ada data yang tersedia.")

        with col2:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:30px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 6px; margin-right: 8px;">
                        <path d="M6 .5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1H9v1.07a7.001 7.001 0 0 1 3.274 12.474l.601.602a.5.5 0 0 1-.707.708l-.746-.746A6.97 6.97 0 0 1 8 16a6.97 6.97 0 0 1-3.422-.892l-.746.746a.5.5 0 0 1-.707-.708l.602-.602A7.001 7.001 0 0 1 7 2.07V1h-.5A.5.5 0 0 1 6 .5m2.5 5a.5.5 0 0 0-1 0v3.362l-1.429 2.38a.5.5 0 1 0 .858.515l1.5-2.5A.5.5 0 0 0 8.5 9zM.86 5.387A2.5 2.5 0 1 1 4.387 1.86 8.04 8.04 0 0 0 .86 5.387M11.613 1.86a2.5 2.5 0 1 1 3.527 3.527 8.04 8.04 0 0 0-3.527-3.527"/>
                    </svg>
                    Lead Time Distribution
                </h1>
            """, unsafe_allow_html=True)
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
                st.plotly_chart(fig, width="stretch")
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

        st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:30px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 6px; margin-right: 8px;">
                        <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5m.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2"/>
                    </svg>
                    Top 10 PR Without PO (Pending)
                </h1>
            """, unsafe_allow_html=True)
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
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:30px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 6px; margin-right: 8px;">
                        <path d="M0 3.5A1.5 1.5 0 0 1 1.5 2h9A1.5 1.5 0 0 1 12 3.5V5h1.02a1.5 1.5 0 0 1 1.17.563l1.481 1.85a1.5 1.5 0 0 1 .329.938V10.5a1.5 1.5 0 0 1-1.5 1.5H14a2 2 0 1 1-4 0H5a2 2 0 1 1-3.998-.085A1.5 1.5 0 0 1 0 10.5zm1.294 7.456A2 2 0 0 1 4.732 11h5.536a2 2 0 0 1 .732-.732V3.5a.5.5 0 0 0-.5-.5h-9a.5.5 0 0 0-.5.5v7a.5.5 0 0 0 .294.456M12 10a2 2 0 0 1 1.732 1h.768a.5.5 0 0 0 .5-.5V8.35a.5.5 0 0 0-.11-.312l-1.48-1.85A.5.5 0 0 0 13.02 6H12zm-9 1a1 1 0 1 0 0 2 1 1 0 0 0 0-2m9 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2"/>
                    </svg>
                    Delivery Performance
                </h1>
            """, unsafe_allow_html=True)
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
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("No delivery data available.")

        with col_chart2:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:30px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 6px; margin-right: 8px;">
                        <path d="M11 2a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v12h.5a.5.5 0 0 1 0 1H.5a.5.5 0 0 1 0-1H1v-3a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3h1V7a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v7h1z"/>
                    </svg>
                    Material Category Value
                </h1>
            """, unsafe_allow_html=True)
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
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("No material data available.")

    # =====================================================
    # HALAMAN 2: Detailed PR-PO Data
    # =====================================================

    elif page == "Detailed PR-PO Data":
        # ── DATA TABLE ───────────────────────────────────
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:60px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" fill="currentColor" class="bi bi-clipboard2-data-fill" viewBox="0 0 16 16" style="margin-bottom: 10px; margin-right: 8px;">
                    <path d="M9.293 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4.707A1 1 0 0 0 13.707 4L10 .293A1 1 0 0 0 9.293 0M9.5 3.5v-2l3 3h-2a1 1 0 0 1-1-1M4.5 9a.5.5 0 0 1 0-1h7a.5.5 0 0 1 0 1zM4 10.5a.5.5 0 0 1 .5-.5h7a.5.5 0 0 1 0 1h-7a.5.5 0 0 1-.5-.5m.5 2.5a.5.5 0 0 1 0-1h4a.5.5 0 0 1 0 1z"/>
                </svg>
                Detailed PR-PO Data
            </h1>
        """, unsafe_allow_html=True)
        st.markdown("---")

        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:20px; font-weight: normal;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-graph-up" viewBox="0 0 16 16" style="margin-bottom: 2px; margin-right: 4px;">
                    <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001q.044.06.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1 1 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0"/>
                </svg>
                Search (PR No, PO No, Material, Vendor)
            </h1>
        """, unsafe_allow_html=True)
        search_term = st.text_input("Search", value="", label_visibility="collapsed")
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

            st.dataframe(table_data, width="stretch", height=400)
            csv = table_data.to_csv(index=False)
            st.download_button(
                label="Download as CSV",
                icon=":material/download:",
                data=csv,
                file_name=f"pr_po_data_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No data found matching your filters")


    # =====================================================
    # HALAMAN 3: EVALUASI HARGA BARANG
    # =====================================================

    elif page == "Evaluasi Harga Barang":

        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:60px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" fill="currentColor" class="bi bi-tag-fill" viewBox="0 0 16 16" style="margin-bottom: 10px; margin-right: 8px;">
                    <path d="M2 1a1 1 0 0 0-1 1v4.586a1 1 0 0 0 .293.707l7 7a1 1 0 0 0 1.414 0l4.586-4.586a1 1 0 0 0 0-1.414l-7-7A1 1 0 0 0 6.586 1zm4 3.5a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0"/>
                </svg>
                Evaluasi PO per Harga Barang
            </h1>
        """, unsafe_allow_html=True)
        st.markdown("Analisis harga barang pada PO: perbandingan terhadap OE, variasi harga antar vendor, dan tren harga historis.")
        st.markdown("---")

        # ── KPI HARGA ─────────────────────────────────────
        # Kolom oe sudah tersedia di vw_pr_po_complete (= estimasi_pr × quantity_pr)
        harga_kpi_query = f"""
        SELECT
            COUNT(DISTINCT material_no)                                                        AS total_material,
            COUNT(DISTINCT nomor_po)                                                           AS total_po,
            COALESCE(SUM(oe), 0)                                                               AS total_oe,
            COALESCE(SUM(total_amount_local_curr), 0)                                          AS total_realisasi,
            COALESCE(SUM(oe) - SUM(total_amount_local_curr), 0)                                AS total_efisiensi,
            COUNT(CASE WHEN total_amount_local_curr > oe AND oe > 0 THEN 1 END)                AS po_melebihi_oe,
            COUNT(CASE WHEN total_amount_local_curr <= oe AND oe > 0 THEN 1 END)               AS po_dibawah_oe
        FROM vw_pr_po_complete
        WHERE {filter_conditions}
        AND nomor_po IS NOT NULL
        AND oe IS NOT NULL
        AND ({bagian_po_cond})
        """
        with st.spinner("Memuat KPI harga..."):
            harga_kpi = load_data(harga_kpi_query)

        col1, col2, col3, col4 = st.columns(4)
        total_oe_val   = float(harga_kpi['total_oe'][0] or 0)
        total_real_val = float(harga_kpi['total_realisasi'][0] or 0)
        total_efis_val = float(harga_kpi['total_efisiensi'][0] or 0)
        po_over        = int(harga_kpi['po_melebihi_oe'][0] or 0)
        po_under       = int(harga_kpi['po_dibawah_oe'][0] or 0)

        with col1:
            st.metric("Total Material Unik", f"{int(harga_kpi['total_material'][0] or 0):,}")
        with col2:
            st.metric("Total OE", format_idr(total_oe_val))
        with col3:
            st.metric("Total Realisasi PO", format_idr(total_real_val))
        with col4:
            delta_label = "efisien" if total_efis_val >= 0 else "melebihi OE"
            st.metric("Selisih OE vs Realisasi", format_idr(total_efis_val), delta=delta_label)

        col_a, col_b, _ = st.columns([1, 1, 2])
        with col_a:
            st.metric("⚠️ Item PO Melebihi OE", f"{po_over:,} item")
        with col_b:
            st.metric("✅ Item PO Di Bawah / Sesuai OE", f"{po_under:,} item")

        st.markdown("---")

        # ── ROW 1: Scatter OE vs Realisasi & Bar Top Material Overspend ───────────
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:22px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                        <path d="M1 11a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1zm5-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1zm5-5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1z"/>
                    </svg>
                    OE vs Realisasi Harga PO (per Material)
                </h1>
            """, unsafe_allow_html=True)

            scatter_query = f"""
            SELECT
                v.material_no,
                COALESCE(m.description, v.pr_description, 'Unknown') AS nama_material,
                ROUND(AVG(v.oe)::numeric, 2)                           AS avg_oe,
                ROUND(AVG(v.total_amount_local_curr)::numeric, 2)      AS avg_realisasi,
                COUNT(DISTINCT v.nomor_po)                             AS jumlah_po
            FROM vw_pr_po_complete v
            LEFT JOIN materials m USING (material_no)
            WHERE {filter_conditions}
            AND v.nomor_po IS NOT NULL
            AND v.oe IS NOT NULL AND v.oe > 0
            AND v.total_amount_local_curr > 0
            AND ({bagian_po_cond})
            GROUP BY v.material_no, m.description, v.pr_description
            ORDER BY jumlah_po DESC
            LIMIT 50
            """
            with st.spinner("Memuat scatter chart..."):
                scatter_data = load_data(scatter_query)

            if not scatter_data.empty:
                scatter_data['status'] = scatter_data.apply(
                    lambda r: 'Melebihi OE' if r['avg_realisasi'] > r['avg_oe'] else 'Di Bawah / Sesuai OE',
                    axis=1
                )
                max_val = max(scatter_data['avg_oe'].max(), scatter_data['avg_realisasi'].max()) * 1.1
                fig = px.scatter(
                    scatter_data,
                    x='avg_oe', y='avg_realisasi',
                    color='status',
                    size='jumlah_po',
                    hover_name='nama_material',
                    hover_data={'material_no': True, 'jumlah_po': True,
                                'avg_oe': ':,.0f', 'avg_realisasi': ':,.0f'},
                    color_discrete_map={'Melebihi OE': '#d62728', 'Di Bawah / Sesuai OE': '#2ca02c'},
                    labels={'avg_oe': 'Rata-rata OE (IDR)', 'avg_realisasi': 'Rata-rata Realisasi PO (IDR)'}
                )
                fig.add_shape(type='line', x0=0, y0=0, x1=max_val, y1=max_val,
                            line=dict(color='gray', dash='dash', width=1))
                fig.add_annotation(x=max_val * 0.85, y=max_val * 0.9,
                                    text="Batas OE", showarrow=False,
                                    font=dict(color='gray', size=11))
                fig.update_layout(height=420, legend=dict(orientation='h', yanchor='bottom', y=1.02))
                st.plotly_chart(fig, width="stretch")
                st.caption("Titik di atas garis diagonal = realisasi melebihi OE. Ukuran titik = jumlah PO.")
            else:
                st.info("Tidak ada data yang tersedia.")

        with col2:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:22px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-exclamation-triangle-fill" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                        <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5m.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2"/>
                    </svg>
                    Top 10 Material: Overspend Terbesar
                </h1>
            """, unsafe_allow_html=True)

            overspend_query = f"""
            SELECT
                v.material_no,
                COALESCE(m.description, v.pr_description, 'Unknown')          AS nama_material,
                SUM(v.total_amount_local_curr - v.oe)                          AS total_overspend,
                ROUND(AVG(
                    CASE WHEN v.oe > 0
                    THEN ((v.total_amount_local_curr - v.oe) / v.oe * 100)
                    END
                )::numeric, 1)                                                  AS persen_overspend,
                COUNT(DISTINCT v.nomor_po)                                      AS jumlah_po
            FROM vw_pr_po_complete v
            LEFT JOIN materials m USING (material_no)
            WHERE {filter_conditions}
            AND v.nomor_po IS NOT NULL
            AND v.oe IS NOT NULL AND v.oe > 0
            AND v.total_amount_local_curr > v.oe
            AND ({bagian_po_cond})
            GROUP BY v.material_no, m.description, v.pr_description
            ORDER BY total_overspend DESC
            LIMIT 10
            """
            with st.spinner("Memuat top overspend..."):
                overspend_data = load_data(overspend_query)

            if not overspend_data.empty:
                overspend_data['label'] = overspend_data['nama_material'].str[:30]
                overspend_data['label_text'] = overspend_data['total_overspend'].apply(format_idr_short)
                fig = px.bar(
                    overspend_data,
                    x='total_overspend', y='label', orientation='h',
                    text='label_text',
                    color='persen_overspend',
                    color_continuous_scale='Reds',
                    labels={'total_overspend': 'Total Overspend (IDR)',
                            'label': 'Material', 'persen_overspend': '% di atas OE'}
                )
                fig.update_layout(height=420, yaxis={'categoryorder': 'total ascending'},
                                coloraxis_colorbar=dict(title='% Overspend'))
                fig.update_traces(textposition='outside')
                st.plotly_chart(fig, width="stretch")
            else:
                st.success("Tidak ada material dengan realisasi melebihi OE pada periode ini.")

        st.markdown("---")

        # ── ROW 2: Harga per Vendor & Tren Harga Historis ─────────────────────────
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:22px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-people-fill" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                        <path d="M7 14s-1 0-1-1 1-4 5-4 5 3 5 4-1 1-1 1zm4-6a3 3 0 1 0 0-6 3 3 0 0 0 0 6m-5.784 6A2.24 2.24 0 0 1 5 13c0-1.355.68-2.75 1.936-3.72A6.3 6.3 0 0 0 5 9c-4 0-5 3-5 4s1 1 1 1zM4.5 8a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5"/>
                    </svg>
                    Variasi Harga Antar Vendor (Top 10 Material)
                </h1>
            """, unsafe_allow_html=True)
            st.caption("10 material dengan jumlah vendor terbanyak. Perbandingan harga satuan rata-rata per vendor.")

            vendor_price_query = f"""
            WITH ranked AS (
                SELECT
                    v.material_no,
                    COALESCE(m.description, v.pr_description, 'Unknown') AS nama_material,
                    COUNT(DISTINCT v.vendor_name) AS jumlah_vendor
                FROM vw_pr_po_complete v
                LEFT JOIN materials m USING (material_no)
                WHERE {filter_conditions}
                AND v.nomor_po IS NOT NULL
                AND v.qty_po > 0
                AND v.total_amount_local_curr > 0
                AND ({bagian_po_cond})
                GROUP BY v.material_no, m.description, v.pr_description
                ORDER BY jumlah_vendor DESC
                LIMIT 10
            )
            SELECT
                r.material_no,
                r.nama_material,
                v.vendor_name,
                ROUND((SUM(v.total_amount_local_curr) / NULLIF(SUM(v.qty_po), 0))::numeric, 2) AS harga_satuan_avg,
                COUNT(DISTINCT v.nomor_po) AS jumlah_po
            FROM ranked r
            JOIN vw_pr_po_complete v USING (material_no)
            WHERE {filter_conditions}
            AND v.nomor_po IS NOT NULL
            AND v.qty_po > 0
            AND v.total_amount_local_curr > 0
            AND ({bagian_po_cond})
            GROUP BY r.material_no, r.nama_material, v.vendor_name
            ORDER BY r.material_no, harga_satuan_avg
            """
            with st.spinner("Memuat variasi harga vendor..."):
                vendor_price_data = load_data(vendor_price_query)

            material_options = []
            material_labels  = {}

            if not vendor_price_data.empty:
                material_options = vendor_price_data['material_no'].unique().tolist()
                material_labels  = {
                    row['material_no']: f"{row['material_no']} – {row['nama_material'][:40]}"
                    for _, row in vendor_price_data.drop_duplicates('material_no').iterrows()
                }
                selected_mat = st.selectbox(
                    "Pilih Material:",
                    options=material_options,
                    format_func=lambda x: material_labels.get(x, x),
                    key="select_material_vendor"
                )
                df_mat = vendor_price_data[vendor_price_data['material_no'] == selected_mat]
                fig = px.bar(
                    df_mat,
                    x='vendor_name', y='harga_satuan_avg',
                    text=df_mat['harga_satuan_avg'].apply(format_idr_short),
                    color='harga_satuan_avg',
                    color_continuous_scale='Blues',
                    labels={'vendor_name': 'Vendor', 'harga_satuan_avg': 'Harga Satuan Rata-rata (IDR)'}
                )
                fig.update_layout(height=380, showlegend=False,
                                coloraxis_showscale=False, xaxis_tickangle=-30)
                fig.update_traces(textposition='outside')
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("Tidak ada data variasi harga yang tersedia.")

        with col2:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:22px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-graph-up" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                        <path fill-rule="evenodd" d="M0 0h1v15h15v1H0zm14.817 3.113a.5.5 0 0 1 .07.704l-4.5 5.5a.5.5 0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5 0 0 1 .758-.06l2.609 2.61 4.15-5.073a.5.5 0 0 1 .704-.07"/>
                    </svg>
                    Tren Harga Historis per Material
                </h1>
            """, unsafe_allow_html=True)
            st.caption("Rata-rata harga satuan per bulan. Berguna untuk mendeteksi kenaikan harga yang tidak wajar.")

            if material_options:
                selected_mat_trend = st.selectbox(
                    "Pilih Material:",
                    options=material_options,
                    format_func=lambda x: material_labels.get(x, x),
                    key="select_material_trend"
                )
                trend_harga_query = f"""
                SELECT
                    DATE_TRUNC('month', date_ordered)::DATE                               AS bulan,
                    ROUND((SUM(total_amount_local_curr) / NULLIF(SUM(qty_po), 0))::numeric, 2) AS harga_satuan_avg,
                    COUNT(DISTINCT nomor_po)                                              AS jumlah_po,
                    ROUND(AVG(oe)::numeric, 2)                                            AS avg_oe
                FROM vw_pr_po_complete
                WHERE material_no = '{selected_mat_trend}'
                AND date_ordered IS NOT NULL
                AND qty_po > 0
                AND total_amount_local_curr > 0
                AND nomor_po IS NOT NULL
                GROUP BY 1
                ORDER BY 1
                """
                with st.spinner("Memuat tren harga..."):
                    trend_harga_data = load_data(trend_harga_query)

                if not trend_harga_data.empty:
                    trend_harga_data['bulan'] = pd.to_datetime(trend_harga_data['bulan'])
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=trend_harga_data['bulan'],
                        y=trend_harga_data['harga_satuan_avg'],
                        mode='lines+markers',
                        name='Harga Satuan Realisasi',
                        line=dict(color='#1f77b4', width=2),
                        hovertemplate='%{x|%b %Y}<br>Harga: Rp %{y:,.0f}<extra></extra>'
                    ))
                    if trend_harga_data['avg_oe'].notna().any() and trend_harga_data['avg_oe'].sum() > 0:
                        fig.add_trace(go.Scatter(
                            x=trend_harga_data['bulan'],
                            y=trend_harga_data['avg_oe'],
                            mode='lines',
                            name='OE Rata-rata',
                            line=dict(color='#ff7f0e', dash='dash', width=1.5),
                            hovertemplate='%{x|%b %Y}<br>OE: Rp %{y:,.0f}<extra></extra>'
                        ))
                    fig.update_layout(
                        height=380,
                        xaxis_title='Bulan',
                        yaxis_title='Harga Satuan (IDR)',
                        legend=dict(orientation='h', yanchor='bottom', y=1.02),
                        hovermode='x unified'
                    )
                    st.plotly_chart(fig, width="stretch")
                else:
                    st.info("Tidak ada data historis untuk material ini.")
            else:
                st.info("Tidak ada material yang bisa dipilih untuk tren historis.")

        st.markdown("---")

        # ── ROW 3: Tabel Detail Evaluasi Harga ────────────────────────────────────
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:22px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-table" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                    <path d="M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2zm15 2h-4v3h4zm0 4h-4v3h4zm0 4h-4v3h3a1 1 0 0 0 1-1zm-5 3v-3H6v3zm-5 0v-3H1v2a1 1 0 0 0 1 1zm-4-4h4V8H1zm0-4h4V4H1zm5-3v3h4V4zm4 4H6v3h4z"/>
                </svg>
                Detail Evaluasi Harga per Material
            </h1>
        """, unsafe_allow_html=True)
        st.caption("Ringkasan perbandingan OE vs realisasi per material. Kolom 'Status' menandai item yang perlu perhatian.")

        detail_harga_query = f"""
        SELECT
            v.material_no,
            COALESCE(m.description, v.pr_description, 'Unknown')                AS nama_material,
            m.material_group                                                      AS grup_material,
            COUNT(DISTINCT v.nomor_po)                                            AS jumlah_po,
            COUNT(DISTINCT v.vendor_name)                                         AS jumlah_vendor,
            ROUND(AVG(v.oe)::numeric, 0)                                          AS rata_oe,
            ROUND(AVG(v.total_amount_local_curr)::numeric, 0)                     AS rata_realisasi,
            ROUND(AVG(CASE WHEN v.oe > 0
                THEN (v.total_amount_local_curr - v.oe) / v.oe * 100
                END)::numeric, 1)                                                AS persen_selisih_avg,
            ROUND((SUM(v.oe) - SUM(v.total_amount_local_curr))::numeric, 0)       AS total_selisih,
            ROUND(MIN(v.total_amount_local_curr / NULLIF(v.qty_po, 0))::numeric, 0)   AS harga_satuan_min,
            ROUND(MAX(v.total_amount_local_curr / NULLIF(v.qty_po, 0))::numeric, 0)   AS harga_satuan_max
        FROM vw_pr_po_complete v
        LEFT JOIN materials m USING (material_no)
        WHERE {filter_conditions}
        AND v.nomor_po IS NOT NULL
        AND v.oe IS NOT NULL AND v.oe > 0
        AND v.qty_po > 0
        AND ({bagian_po_cond})
        GROUP BY v.material_no, m.description, v.pr_description, m.material_group
        ORDER BY persen_selisih_avg DESC NULLS LAST
        LIMIT 100
        """
        with st.spinner("Memuat tabel detail harga..."):
            detail_harga_data = load_data(detail_harga_query)

        if not detail_harga_data.empty:
            def status_harga(persen):
                if pd.isna(persen):       return "—"
                elif persen > 10:         return "🔴 Jauh Melebihi OE"
                elif persen > 0:          return "🟡 Melebihi OE"
                elif persen >= -5:        return "🟢 Sesuai OE"
                else:                     return "✅ Efisien"

            detail_harga_data['status'] = detail_harga_data['persen_selisih_avg'].apply(status_harga)

            for col in ['rata_oe', 'rata_realisasi', 'total_selisih', 'harga_satuan_min', 'harga_satuan_max']:
                detail_harga_data[col] = detail_harga_data[col].apply(
                    lambda x: f"Rp {x:,.0f}" if pd.notna(x) else ""
                )
            detail_harga_data['persen_selisih_avg'] = detail_harga_data['persen_selisih_avg'].apply(
                lambda x: f"{x:+.1f}%" if pd.notna(x) else ""
            )

            st.dataframe(
                detail_harga_data.rename(columns={
                    'material_no':        'Material No',
                    'nama_material':      'Nama Material',
                    'grup_material':      'Grup',
                    'jumlah_po':          'Jml PO',
                    'jumlah_vendor':      'Jml Vendor',
                    'rata_oe':            'Rata-rata OE',
                    'rata_realisasi':     'Rata-rata Realisasi',
                    'persen_selisih_avg': '% Selisih',
                    'total_selisih':      'Total Selisih',
                    'harga_satuan_min':   'Harga Satuan Min',
                    'harga_satuan_max':   'Harga Satuan Maks',
                    'status':             'Status'
                }),
                use_container_width=True, height=400
            )
            csv_harga = detail_harga_data.to_csv(index=False)
            st.download_button(
                label="Download as CSV",
                icon=":material/download:",
                data=csv_harga,
                file_name=f"evaluasi_harga_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("Tidak ada data evaluasi harga untuk filter yang dipilih.")


    # =====================================================
    # HALAMAN 4: KINERJA PURCHASING GROUP
    # =====================================================

    elif page == "Kinerja Purchasing Group":
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:50px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" fill="currentColor" class="bi bi-briefcase-fill" viewBox="0 0 16 16" style="margin-bottom: 8px; margin-right: 12px;">
                    <path d="M6.5 1A1.5 1.5 0 0 0 5 2.5V3H1.5A1.5 1.5 0 0 0 0 4.5v1.384l7.614 2.03a1.5 1.5 0 0 0 .772 0L16 5.884V4.5A1.5 1.5 0 0 0 14.5 3H11v-.5A1.5 1.5 0 0 0 9.5 1h-3zm0 1h3a.5.5 0 0 1 .5.5V3H6v-.5a.5.5 0 0 1 .5-.5z"/>
                    <path d="M0 12.5A1.5 1.5 0 0 0 1.5 14h13a1.5 1.5 0 0 0 1.5-1.5V6.85L8.129 8.947a.5.5 0 0 1-.258 0L0 6.85v5.65z"/>
                </svg>
                Kinerja per Purchasing Group
            </h1>
        """, unsafe_allow_html=True)
        st.markdown("Analisis komprehensif jumlah item, nilai pengadaan (OE vs Realisasi), efisiensi, dan kecepatan proses per Purchasing Group — termasuk breakdown per metode tender.")
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

        # Query lebih sederhana untuk KPI — langsung dari view
        pg_kpi_query = f"""
        SELECT
            COUNT(DISTINCT CASE WHEN no_pr != 'No PR' AND {bagian_pr_cond}
                THEN no_pr || '-' || line_item_pr::text END)                         AS total_item_pr,
            COUNT(DISTINCT CASE WHEN nomor_po IS NOT NULL AND {bagian_po_cond}
                THEN nomor_po || '-' || item_po::text END)                           AS total_item_po,
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
            t_oe         = float(pg_kpi['total_oe'][0] or 0)
            t_real       = float(pg_kpi['total_realisasi'][0] or 0)
            t_efis       = t_oe - t_real
            t_efis_pct   = (t_efis / t_oe * 100) if t_oe > 0 else 0
            avg_lt        = pg_kpi['avg_lead_time_overall'][0]
            konversi_pct = (t_item_po / t_item_pr * 100) if t_item_pr > 0 else 0

            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Total Item PR", f"{t_item_pr:,}",
                          delta=f"{konversi_pct:.1f}% sudah PO")
            with col2:
                st.metric("Total Item PO", f"{t_item_po:,}")
            with col3:
                st.metric("Total OE", format_idr(t_oe))
            with col4:
                delta_efis = "efisien" if t_efis >= 0 else "over budget"
                st.metric("Efisiensi", format_idr(t_efis), delta=f"{t_efis_pct:.1f}% {delta_efis}")
            with col5:
                lt_label = f"{avg_lt} Hari" if pd.notna(avg_lt) else "N/A"
                lt_delta = "✅ On Target" if (avg_lt and avg_lt <= 30) else "⚠️ Over Target"
                st.metric("Avg Lead Time", lt_label, delta=lt_delta)

        st.markdown("---")

        # ── TAB: OVERVIEW | TENDER TYPE ────────────────────────────────────────
        tab1, tab2 = st.tabs(["📊 Overview per Purchasing Group", "🏷️ Breakdown per Metode Tender"])

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
                st.markdown("##### 📋 Tabel Ringkasan per Purchasing Group")

                df_table = pg_data.copy()
                df_table['konversi_pct'] = (
                    df_table['jml_item_po'] / df_table['jml_item_pr'].replace(0, float('nan')) * 100
                ).round(1).fillna(0)
                df_table['efisiensi_pct'] = df_table['efisiensi_pct'].fillna(0)

                df_display = df_table.copy()
                df_display['nilai_oe']     = df_display['nilai_oe'].apply(format_idr)
                df_display['nilai_po']     = df_display['nilai_po'].apply(format_idr)
                df_display['efisiensi']    = df_display['efisiensi'].apply(format_idr)
                df_display['efisiensi_pct']= df_display['efisiensi_pct'].apply(lambda x: f"{x:+.1f}%")
                df_display['avg_lead_time']= df_display['avg_lead_time'].apply(
                    lambda x: f"{x} Hari" if pd.notna(x) else "N/A")
                df_display['min_lead_time']= df_display['min_lead_time'].apply(
                    lambda x: f"{int(x)} Hari" if pd.notna(x) else "N/A")
                df_display['max_lead_time']= df_display['max_lead_time'].apply(
                    lambda x: f"{int(x)} Hari" if pd.notna(x) else "N/A")
                df_display['konversi_pct'] = df_display['konversi_pct'].apply(lambda x: f"{x:.1f}%")

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
                    st.markdown("##### 💰 Perbandingan Nilai OE vs Realisasi PO")
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
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig_val, use_container_width=True)

                with col2:
                    st.markdown("##### 📈 % Efisiensi per Purchasing Group")
                    pg_efis = pg_data[pg_data['efisiensi_pct'].notna()].copy()
                    pg_efis['warna'] = pg_efis['efisiensi_pct'].apply(
                        lambda x: '#2ca02c' if x >= 0 else '#d62728')
                    pg_efis['label'] = pg_efis['efisiensi_pct'].apply(lambda x: f"{x:+.1f}%")
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
                    st.markdown("##### ⏱️ Rata-rata Lead Time per Purchasing Group")
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
                    st.markdown("##### 🔄 % Konversi PR → PO per Purchasing Group")
                    pg_data['konversi_pct'] = (
                        pg_data['jml_item_po'] /
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
        # TAB 2: BREAKDOWN PER METODE TENDER
        # ══════════════════════════════════════════════════════════════════════
        with tab2:
            st.markdown("Perbandingan kinerja pengadaan berdasarkan metode tender: Tender Normal vs Tender Kontrak.")

            tender_query = f"""
            SELECT
                COALESCE(purchasing_group, 'Unassigned')                             AS purchasing_group,
                COALESCE(po.metode_pelelangan, 'Tidak Diketahui')                   AS metode_tender,
                COUNT(DISTINCT CASE WHEN {bagian_po_cond}
                    THEN v.nomor_po || '-' || v.item_po::text END)                   AS jml_item_po,
                COALESCE(SUM(CASE WHEN {bagian_pr_cond} THEN v.oe ELSE 0 END), 0)   AS total_oe,
                COALESCE(SUM(CASE WHEN {bagian_po_cond}
                    THEN v.total_amount_local_curr ELSE 0 END), 0)                   AS total_realisasi,
                COALESCE(SUM(CASE WHEN {bagian_pr_cond} THEN v.oe ELSE 0 END), 0)
                    - COALESCE(SUM(CASE WHEN {bagian_po_cond}
                    THEN v.total_amount_local_curr ELSE 0 END), 0)                   AS efisiensi,
                ROUND(AVG(CASE WHEN {bagian_po_cond} AND v.lead_time_process_po IS NOT NULL
                    THEN v.lead_time_process_po END)::numeric, 1)                    AS avg_lead_time
            FROM vw_pr_po_complete v
            LEFT JOIN po_items po
                ON v.nomor_po = po.nomor_po AND v.item_po = po.item_po
            WHERE {filter_conditions}
              AND v.nomor_po IS NOT NULL
            GROUP BY COALESCE(purchasing_group, 'Unassigned'),
                     COALESCE(po.metode_pelelangan, 'Tidak Diketahui')
            ORDER BY purchasing_group, total_realisasi DESC
            """

            with st.spinner("Memuat data per metode tender..."):
                tender_data = load_data(tender_query)

            if not tender_data.empty:

                # ── KPI Tender Summary ────────────────────────────────────────
                st.markdown("##### 📊 Ringkasan per Metode Tender (Semua PG)")
                tender_summary = tender_data.groupby('metode_tender').agg(
                    jml_item_po   = ('jml_item_po',   'sum'),
                    total_oe      = ('total_oe',       'sum'),
                    total_realisasi=('total_realisasi','sum'),
                    efisiensi     = ('efisiensi',      'sum'),
                    avg_lead_time = ('avg_lead_time',  'mean')
                ).reset_index()
                tender_summary['efisiensi_pct'] = (
                    tender_summary['efisiensi'] /
                    tender_summary['total_oe'].replace(0, float('nan')) * 100
                ).round(1).fillna(0)
                tender_summary['avg_lead_time'] = tender_summary['avg_lead_time'].round(1)

                # Tampilkan sebagai metric cards per metode
                cols = st.columns(len(tender_summary))
                for i, (_, row) in enumerate(tender_summary.iterrows()):
                    with cols[i]:
                        pct_label = f"{row['efisiensi_pct']:+.1f}% efisiensi"
                        st.metric(
                            label=f"🏷️ {row['metode_tender']}",
                            value=format_idr(row['total_realisasi']),
                            delta=pct_label
                        )
                        st.caption(
                            f"OE: {format_idr(row['total_oe'])} | "
                            f"{int(row['jml_item_po']):,} item | "
                            f"Lead Time: {row['avg_lead_time']} Hari"
                        )

                st.markdown("<br>", unsafe_allow_html=True)

                # ── Chart: Realisasi per Metode Tender per PG ─────────────────
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("##### 💰 Nilai Realisasi PO per Metode Tender")
                    tender_data['label'] = tender_data['total_realisasi'].apply(format_idr_short)
                    fig_t1 = px.bar(
                        tender_data,
                        x='purchasing_group', y='total_realisasi',
                        color='metode_tender', barmode='stack',
                        text='label',
                        labels={
                            'purchasing_group': 'Purchasing Group',
                            'total_realisasi' : 'Total Realisasi (IDR)',
                            'metode_tender'   : 'Metode Tender'
                        }
                    )
                    fig_t1.update_traces(textposition='inside', textfont_size=10)
                    fig_t1.update_layout(
                        height=420,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02)
                    )
                    st.plotly_chart(fig_t1, use_container_width=True)

                with col2:
                    st.markdown("##### ⏱️ Lead Time per Metode Tender")
                    tender_lt = tender_data[tender_data['avg_lead_time'].notna()]
                    fig_t2 = px.bar(
                        tender_lt,
                        x='purchasing_group', y='avg_lead_time',
                        color='metode_tender', barmode='group',
                        text=tender_lt['avg_lead_time'].apply(lambda x: f"{x} Hr"),
                        labels={
                            'purchasing_group': 'Purchasing Group',
                            'avg_lead_time'   : 'Lead Time Rata-rata (Hari)',
                            'metode_tender'   : 'Metode Tender'
                        }
                    )
                    fig_t2.add_hline(y=55, line_dash="dash", line_color="red",
                                     annotation_text="Target 55 Hari",
                                     annotation_position="bottom right")
                    fig_t2.update_traces(textposition='outside', textfont_size=10)
                    fig_t2.update_layout(
                        height=420,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02)
                    )
                    st.plotly_chart(fig_t2, use_container_width=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # ── Tabel Detail ──────────────────────────────────────────────
                st.markdown("##### 📋 Detail per Purchasing Group × Metode Tender")
                df_t_display = tender_data.copy()
                df_t_display['efisiensi_pct'] = (
                    df_t_display['efisiensi'] /
                    df_t_display['total_oe'].replace(0, float('nan')) * 100
                ).round(1).fillna(0)
                df_t_display['total_oe']       = df_t_display['total_oe'].apply(format_idr)
                df_t_display['total_realisasi'] = df_t_display['total_realisasi'].apply(format_idr)
                df_t_display['efisiensi']       = df_t_display['efisiensi'].apply(format_idr)
                df_t_display['efisiensi_pct']   = df_t_display['efisiensi_pct'].apply(lambda x: f"{x:+.1f}%")
                df_t_display['avg_lead_time']   = df_t_display['avg_lead_time'].apply(
                    lambda x: f"{x} Hari" if pd.notna(x) else "N/A")
                st.dataframe(
                    df_t_display.rename(columns={
                        'purchasing_group': 'Purchasing Group',
                        'metode_tender'   : 'Metode Tender',
                        'jml_item_po'     : 'Jml Item PO',
                        'total_oe'        : 'Total OE',
                        'total_realisasi' : 'Realisasi PO',
                        'efisiensi'       : 'Efisiensi',
                        'efisiensi_pct'   : '% Efisiensi',
                        'avg_lead_time'   : 'Lead Time Avg',
                    }),
                    use_container_width=True, height=350
                )

                csv_tender = tender_data.to_csv(index=False)
                st.download_button(
                    label="Download as CSV",
                    icon=":material/download:",
                    data=csv_tender,
                    file_name=f"kinerja_pg_tender_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )

            else:
                st.info("Tidak ada data metode tender pada periode ini. Pastikan kolom metode_pelelangan sudah terisi di tabel po_items.")

    # =====================================================
    # HALAMAN 5: HALAMAN ALERT
    # =====================================================

    elif page == "Halaman Alert":

        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:60px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" fill="currentColor" class="bi bi-clipboard2-data-fill" viewBox="0 0 16 16" style="margin-bottom: 10px; margin-right: 8px;">
                    <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5m.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2"/>
                </svg>
                Warning & Action Required
            </h1>
        """, unsafe_allow_html=True)
        st.markdown("Halaman ini menampilkan anomali data dan dokumen yang membutuhkan tindakan segera!")
        st.markdown("---")

        # ALERT 1: PR > 30 hari belum ada PO
        st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:30px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 6px; margin-right: 8px;">
                        <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0M9.283 4.002H7.971L6.072 5.385v1.271l1.834-1.318h.065V12h1.312z"/>
                    </svg>
                    PR Pending Mendekati Kadaluarsa (> 30 Hari)
                </h1>
            """, unsafe_allow_html=True)
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
            st.dataframe(alert_pr_data, width="stretch")
        else:
            st.success("Aman! Tidak ada PR Pending yang umurnya lebih dari 30 hari.")

        st.markdown("<br>", unsafe_allow_html=True)

        col_alert1, col_alert2 = st.columns([2, 1])

        with col_alert1:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:30px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 6px; margin-right: 8px;">
                        <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0M6.646 6.24c0-.691.493-1.306 1.336-1.306.756 0 1.313.492 1.313 1.236 0 .697-.469 1.23-.902 1.705l-2.971 3.293V12h5.344v-1.107H7.268v-.077l1.974-2.22.096-.107c.688-.763 1.287-1.428 1.287-2.43 0-1.266-1.031-2.215-2.613-2.215-1.758 0-2.637 1.19-2.637 2.402v.065h1.271v-.07Z"/>
                    </svg>
                    PO Overdue (Melewati Delivery Date)
                </h1>
            """, unsafe_allow_html=True)
            st.info("Menampilkan PO yang tanggal kirimnya sudah lewat namun barang belum diterima.")

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
                st.dataframe(alert_po_data, width="stretch")
            else:
                st.success("Aman! Tidak ada PO yang terlambat dari jadwal.")

        with col_alert2:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:30px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 6px; margin-right: 8px;">
                        <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0m-8.082.414c.92 0 1.535.54 1.541 1.318.012.791-.615 1.36-1.588 1.354-.861-.006-1.482-.469-1.54-1.066H5.104c.047 1.177 1.05 2.144 2.754 2.144 1.653 0 2.954-.937 2.93-2.396-.023-1.278-1.031-1.846-1.734-1.916v-.07c.597-.1 1.505-.739 1.482-1.876-.03-1.177-1.043-2.074-2.637-2.062-1.675.006-2.59.984-2.625 2.12h1.248c.036-.556.557-1.054 1.348-1.054.785 0 1.348.486 1.348 1.195.006.715-.563 1.237-1.342 1.237h-.838v1.072h.879Z"/>
                    </svg>
                    Rekap Aging PO (Belum Dikirim)
                </h1>
            """, unsafe_allow_html=True)

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
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("Tidak ada data aging PO.")

# =====================================================
# FOOTER & NAVIGATION CHANGELOG
# =====================================================
st.markdown("---")

col_foot1, col_foot2 = st.columns([5, 1])

with col_foot1:
    st.markdown(
        f"<div style='color:#666; margin-top: 10px;'>"
        f"PR-PO Monitoring System - Pengadaan Barang v1.7 | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        f"</div>",
        unsafe_allow_html=True
    )

with col_foot2:
    if st.session_state.show_changelog:
        button_label = "Kembali ke App"
        button_icon = ":material/arrow_back:"
    else:
        button_label = "Log Perubahan"
        button_icon = ":material/history:"
    
    if st.button(button_label, icon=button_icon, use_container_width=True):
        st.session_state.show_changelog = not st.session_state.show_changelog
        st.rerun() # Refresh halaman agar perubahan langsung terlihat