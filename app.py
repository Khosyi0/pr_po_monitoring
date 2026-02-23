"""
app.py — File utama PR-PO Monitoring Dashboard
Jalankan dengan: streamlit run app.py

Struktur:
    app.py          → Sidebar, Filter, Navigasi, Routing
    config_db.py    → Koneksi database & load_data()
    utils.py        → format_idr, CSS, build_filter_conditions
    views/          → Satu file per halaman
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
# SIDEBAR NAVIGATION
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    page = option_menu(
        menu_title="Main Menu",
        options=[
            "Dashboard Monitoring",
            "Detailed PR-PO Data",
            "Evaluasi Harga Barang",
            "Kinerja Purchasing Group",
            "Halaman Alert"
        ],
        icons=[
            "bar-chart-fill",
            "file-earmark-text-fill",
            "tag-fill",
            "briefcase-fill",
            "exclamation-triangle-fill"
        ],
        menu_icon="cast",
        default_index=0,
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

# Tutup changelog otomatis saat pindah halaman
if 'last_page' not in st.session_state:
    st.session_state.last_page = page
if page != st.session_state.last_page:
    st.session_state.show_changelog = False
    st.session_state.last_page = page

# ─────────────────────────────────────────────────────────────────────────────
# DEFAULT FILTER VALUES (fallback jika DB error)
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
# SIDEBAR FILTERS
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
    # Load dropdown options dari DB
    departments = load_data(
        "SELECT DISTINCT department_code FROM departments ORDER BY department_code"
    )
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

    # ── Logic eksklusif 'All' untuk filter Bagian ────────────────────────────
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

    # ── Filter: Department ───────────────────────────────────────────────────
    st.sidebar.markdown("""
        <h2 style='font-size:16px; color:var(--text-color);'>
            🏢 Department
        </h2>
    """, unsafe_allow_html=True)
    selected_department = st.sidebar.multiselect(
        "Department", options=['All'] + departments['department_code'].tolist(),
        default=['All'], label_visibility="collapsed"
    )
    exclude_dept = False
    if 'All' not in selected_department and selected_department:
        exclude_dept = st.sidebar.checkbox(":material/block: Exclude selected Department")

    # ── Filter: Purchasing Group ─────────────────────────────────────────────
    st.sidebar.markdown("""
        <h2 style='font-size:16px; color:var(--text-color);'>
            👥 Purchasing Group
        </h2>
    """, unsafe_allow_html=True)
    selected_p_group = st.sidebar.multiselect(
        "Purchasing Group", options=options_p_group,
        default=['All'], label_visibility="collapsed"
    )
    exclude_purchasing_group = False
    if 'All' not in selected_p_group and selected_p_group:
        exclude_purchasing_group = st.sidebar.checkbox(":material/block: Exclude selected Purchasing Group")

    # ── Filter: Bagian ───────────────────────────────────────────────────────
    st.sidebar.markdown("""
        <h2 style='font-size:16px; color:var(--text-color);'>
            👤 Bagian
        </h2>
    """, unsafe_allow_html=True)
    st.sidebar.pills(
        "Bagian", options=options_bagian, selection_mode="multi",
        key="filter_bagian", on_change=update_bagian_logic,
        label_visibility="collapsed"
    )
    selected_bagian = st.session_state.filter_bagian

    # ── Filter: Date Range ───────────────────────────────────────────────────
    st.sidebar.markdown("""
        <h2 style='font-size:16px; color:var(--text-color);'>
            📅 Date Range
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
# BUILD FILTER CONDITIONS
# ─────────────────────────────────────────────────────────────────────────────

filter_conditions = build_filter_conditions(
    date_from, date_to,
    selected_department, exclude_dept,
    selected_p_group, exclude_purchasing_group
)
bagian_pr_cond, bagian_po_cond = build_bagian_conditions(selected_bagian, exclude_bagian)

# Argumen yang akan dikirim ke setiap view
view_args = dict(
    filter_conditions=filter_conditions,
    bagian_pr_cond=bagian_pr_cond,
    bagian_po_cond=bagian_po_cond,
    load_data=load_data,
)

# ─────────────────────────────────────────────────────────────────────────────
# ROUTING
# ─────────────────────────────────────────────────────────────────────────────

if st.session_state.show_changelog:
    v_changelog.render()

else:
    if   page == "Dashboard Monitoring":
        v_dashboard.render(**view_args)
    elif page == "Detailed PR-PO Data":
        v_detail.render(**view_args)
    elif page == "Evaluasi Harga Barang":
        v_evaluasi.render(**view_args)
    elif page == "Kinerja Purchasing Group":
        v_kinerja_pg.render(**view_args)
    elif page == "Halaman Alert":
        v_alert.render(**view_args)

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
col_foot1, col_foot2 = st.columns([4, 1])

with col_foot1:
    st.markdown(
        f"<div style='color:#666; margin-top:10px;'>"
        f"PR-PO Monitoring System — v1.8 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        f"</div>",
        unsafe_allow_html=True
    )

with col_foot2:
    btn_label = "Kembali ke App" if st.session_state.show_changelog else "Log Perubahan"
    btn_icon  = ":material/arrow_back:" if st.session_state.show_changelog else ":material/history:"
    if st.button(btn_label, icon=btn_icon, use_container_width=True):
        st.session_state.show_changelog = not st.session_state.show_changelog
        st.rerun()
