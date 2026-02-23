"""
app.py - File utama PR-PO Monitoring Dashboard
Jalankan dengan: streamlit run app.py
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_option_menu import option_menu
import warnings
warnings.filterwarnings('ignore')

from config_db import load_data
from utils import inject_css, build_filter_conditions, build_bagian_conditions

# Views
from views import v_changelog, v_dashboard, v_detail, v_evaluasi, v_kinerja_pg, v_alert

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="PR-PO Monitoring Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────

if 'show_changelog' not in st.session_state:
    st.session_state.show_changelog = False

if 'filter_bagian' not in st.session_state:
    st.session_state.filter_bagian = ['All']
if 'prev_filter_bagian' not in st.session_state:
    st.session_state.prev_filter_bagian = ['All']

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────

inject_css()

# ─────────────────────────────────────────────────────────────────────────────
# DEFAULT FILTER VALUES
# ─────────────────────────────────────────────────────────────────────────────

date_from            = datetime.now().date() - timedelta(days=90)
date_to              = datetime.now().date()
selected_department  = ['All']
selected_p_group     = ['All']
selected_bagian      = ['All']
exclude_dept         = False
exclude_purchasing_group = False
exclude_bagian       = False

# ─────────────────────────────────────────────────────────────────────────────
# BUILD VIEW ARGS (Harus di atas agar siap dipakai oleh Pages)
# ─────────────────────────────────────────────────────────────────────────────

# Kita buat dummy function dulu, nilainya akan di-update setelah sidebar filter
view_args = dict()

def show_dashboard(): v_dashboard.render(**view_args)
def show_detail():    v_detail.render(**view_args)
def show_evaluasi():  v_evaluasi.render(**view_args)
def show_kinerja():   v_kinerja_pg.render(**view_args)
def show_alert():     v_alert.render(**view_args)

# ─────────────────────────────────────────────────────────────────────────────
# SETUP NATIVE NAVIGATION (HIDDEN)
# ─────────────────────────────────────────────────────────────────────────────

# Definisi halaman menggunakan engine bawaan Streamlit
pg_dashboard = st.Page(show_dashboard, title="Dashboard Monitoring")
pg_detail    = st.Page(show_detail, title="Detailed PR-PO Data")
pg_evaluasi  = st.Page(show_evaluasi, title="Evaluasi Harga Barang")
pg_kinerja   = st.Page(show_kinerja, title="Kinerja Purchasing Group")
pg_alert     = st.Page(show_alert, title="Halaman Alert")

pages_dict = {
    "Dashboard Monitoring": pg_dashboard,
    "Detailed PR-PO Data": pg_detail,
    "Evaluasi Harga Barang": pg_evaluasi,
    "Kinerja Purchasing Group": pg_kinerja,
    "Halaman Alert": pg_alert
}

# Inisialisasi navigasi dengan position="hidden" agar menu jelek bawaannya tidak muncul!
pg = st.navigation(list(pages_dict.values()), position="hidden")

# pg.title sekarang memegang status kebenaran mutlak dari URL browser saat ini
current_active_title = pg.title

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR NAVIGATION (CUSTOM UI)
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    selected_page = option_menu(
        menu_title="Main Menu",
        options=list(pages_dict.keys()),
        icons=[
            "bar-chart-fill",
            "file-earmark-text-fill",
            "tag-fill",
            "briefcase-fill",
            "exclamation-triangle-fill"
        ],
        menu_icon="cast",
        # Sinkronkan tampilan menu dengan halaman yang sedang aktif dari URL
        default_index=list(pages_dict.keys()).index(current_active_title),
        key=f"menu_{current_active_title}", # Reset UI jika tombol Back ditekan
        styles={
            "container"       : {"padding": "0!important", "background-color": "transparent"},
            "icon"            : {"color": "var(--text-color)", "font-size": "18px"},
            "nav-link"        : {
                "font-size": "16px", "text-align": "left", "margin": "5px",
                "color": "var(--text-color)",
                "--hover-color": "var(--secondary-background-color)"
            },
            "nav-link-selected": {"background-color": "#ff4b4b", "color": "white"},
            "menu-title"      : {"color": "var(--text-color)", "font-size": "18px", "font-weight": "bold"}
        }
    )
    st.markdown("---")

# Jika user mengklik menu (yang berbeda dari URL saat ini), suruh Streamlit pindah halaman!
if selected_page != current_active_title:
    st.switch_page(pages_dict[selected_page])

# Tutup changelog otomatis saat pindah halaman
if 'last_page' not in st.session_state:
    st.session_state.last_page = current_active_title
if current_active_title != st.session_state.last_page:
    st.session_state.show_changelog = False
    st.session_state.last_page = current_active_title

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR FILTERS (Dijalankan setelah Navigasi)
# ─────────────────────────────────────────────────────────────────────────────

st.sidebar.markdown("""
    <h2 style='display: flex; align-items: center; font-size: 20px; color: var(--text-color); margin-top: -20px;'>
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-funnel-fill" viewBox="0 0 16 16" style="margin-right: 10px;">
            <path d="M1.5 1.5A.5.5 0 0 1 2 1h12a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-.128.334L10 8.692V13.5a.5.5 0 0 1-.342.474l-3 1A.5.5 0 0 1 6 14.5V8.692L1.628 3.834A.5.5 0 0 1 1.5 3.5z"/>
        </svg>
        Filters
    </h2>
""", unsafe_allow_html=True)

try:
    departments = load_data("SELECT DISTINCT department_code FROM departments ORDER BY department_code")
    bagian_data = load_data("""
        SELECT DISTINCT bagian_pr AS bagian FROM vw_pr_po_complete WHERE bagian_pr IS NOT NULL
        UNION
        SELECT DISTINCT bagian_po AS bagian FROM vw_pr_po_complete WHERE bagian_po IS NOT NULL
        ORDER BY 1
    """)
    p_group_data = load_data("""
        SELECT DISTINCT purchasing_group FROM purchase_requisitions WHERE purchasing_group IS NOT NULL
        UNION
        SELECT DISTINCT purchasing_group FROM purchase_orders WHERE purchasing_group IS NOT NULL
        ORDER BY 1
    """)

    options_bagian  = ['All'] + bagian_data['bagian'].tolist()
    options_p_group = ['All'] + p_group_data['purchasing_group'].tolist()

    def update_bagian_logic():
        current = st.session_state.filter_bagian
        prev    = st.session_state.prev_filter_bagian
        if 'All' in current and 'All' not in prev:
            st.session_state.filter_bagian = ['All']
        elif 'All' in current and len(current) > 1:
            st.session_state.filter_bagian = [x for x in current if x != 'All']
        elif not current:
            st.session_state.filter_bagian = ['All']
        st.session_state.prev_filter_bagian = st.session_state.filter_bagian

    st.sidebar.markdown(f"""
    <h2 style='display: flex; align-items: center; font-size: 16px; color: var(--text-color);'>
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-calendar-event" viewBox="0 0 16 16" style="margin-right: 8px; margin-bottom: 3px;">
            <path d="M3 0a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h3v-3.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 .5.5V16h3a1 1 0 0 0 1-1V1a1 1 0 0 0-1-1zm1 2.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm3 0a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm3.5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5M4 5.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zM7.5 5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5m2.5.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zM4.5 8h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5m2.5.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm3.5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5"/>
        </svg>
        Department
    </h2>
    """, unsafe_allow_html=True)
    selected_department = st.sidebar.multiselect("Department", options=['All'] + departments['department_code'].tolist(), default=['All'], label_visibility="collapsed")
    exclude_dept = False
    if 'All' not in selected_department and selected_department:
        exclude_dept = st.sidebar.checkbox(":material/block: Exclude selected Department")

    st.sidebar.markdown(f"""
    <h2 style='display: flex; align-items: center; font-size: 16px; color: var(--text-color); margin-bottom: -10px;'>
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-people-fill" viewBox="0 0 16 16" style="margin-right: 8px; margin-bottom: 3px;">
            <path d="M7 14s-1 0-1-1 1-4 5-4 5 3 5 4-1 1-1 1zm4-6a3 3 0 1 0 0-6 3 3 0 0 0 0 6m-5.784 6A2.24 2.24 0 0 1 5 13c0-1.355.68-2.75 1.936-3.72A6.3 6.3 0 0 0 5 9c-4 0-5 3-5 4s1 1 1 1zM4.5 8a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5"/>
        </svg>
        Purchasing Group
    </h2>
    """, unsafe_allow_html=True)
    selected_p_group = st.sidebar.multiselect("Purchasing Group", options=options_p_group, default=['All'], label_visibility="collapsed")
    exclude_purchasing_group = False
    if 'All' not in selected_p_group and selected_p_group:
        exclude_purchasing_group = st.sidebar.checkbox(":material/block: Exclude selected Purchasing Group")

    st.sidebar.markdown(f"""
    <h2 style='display: flex; align-items: center; font-size: 16px; color: var(--text-color);'>
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-calendar-event" viewBox="0 0 16 16" style="margin-right: 8px; margin-bottom: 3px;">
            <path d="M7 14s-1 0-1-1 1-4 5-4 5 3 5 4-1 1-1 1zm4-6a3 3 0 1 0 0-6 3 3 0 0 0 0 6m-5.784 6A2.24 2.24 0 0 1 5 13c0-1.355.68-2.75 1.936-3.72A6.3 6.3 0 0 0 5 9c-4 0-5 3-5 4s1 1 1 1zM4.5 8a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5"/>
        </svg>
        Bagian
    </h2>
    """, unsafe_allow_html=True)
    st.sidebar.pills("Bagian", options=options_bagian, selection_mode="multi", key="filter_bagian", on_change=update_bagian_logic, label_visibility="collapsed")
    selected_bagian = st.session_state.filter_bagian

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
    date_to   = st.sidebar.date_input("To",   value=datetime.now().date())

    if st.sidebar.button("Refresh Data", icon=":material/refresh:"):
        st.cache_data.clear()
        st.rerun()

except Exception as e:
    st.sidebar.error(f"Error loading filters: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# UPDATE VIEW ARGS DENGAN FILTER TERBARU
# ─────────────────────────────────────────────────────────────────────────────

filter_conditions = build_filter_conditions(date_from, date_to, selected_department, exclude_dept, selected_p_group, exclude_purchasing_group)
bagian_pr_cond, bagian_po_cond = build_bagian_conditions(selected_bagian, exclude_bagian)

view_args.update(dict(
    filter_conditions=filter_conditions,
    bagian_pr_cond=bagian_pr_cond,
    bagian_po_cond=bagian_po_cond,
    load_data=load_data,
))

# ─────────────────────────────────────────────────────────────────────────────
# ROUTING EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

if st.session_state.show_changelog:
    v_changelog.render()
else:
    # Membiarkan mesin Streamlit yang mengeksekusi halaman yang tepat
    pg.run()

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
col_foot1, col_foot2 = st.columns([4, 1])

with col_foot1:
    st.markdown(
        f"<div style='color:#666; margin-top:10px;'>"
        f"PR-PO Monitoring System - v1.8 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        f"</div>",
        unsafe_allow_html=True
    )

with col_foot2:
    btn_label = "Kembali ke App" if st.session_state.show_changelog else "Log Perubahan"
    btn_icon  = ":material/arrow_back:" if st.session_state.show_changelog else ":material/history:"
    if st.button(btn_label, icon=btn_icon, use_container_width=True):
        st.session_state.show_changelog = not st.session_state.show_changelog
        st.rerun()