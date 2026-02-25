"""
app.py - File utama PR-PO Monitoring Dashboard
Jalankan dengan: streamlit run app.py

Navigasi: st.navigation() bawaan Streamlit (position="sidebar")
  → Tombol Back/Forward browser berfungsi sempurna
  → CSS di-override agar tampilan mendekati desain sebelumnya
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
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

if 'filter_dept' not in st.session_state:
    st.session_state.filter_dept = ['All']
if 'prev_filter_dept' not in st.session_state:
    st.session_state.prev_filter_dept = ['All']

if 'filter_pgroup' not in st.session_state:
    st.session_state.filter_pgroup = ['All']
if 'prev_filter_pgroup' not in st.session_state:
    st.session_state.prev_filter_pgroup = ['All']

# ─────────────────────────────────────────────────────────────────────────────
# CSS - Override tampilan nav bawaan Streamlit + inject CSS aplikasi
# ─────────────────────────────────────────────────────────────────────────────

inject_css()

st.markdown("""
<style>
/* ── Judul "Main Menu" di atas navigasi ─────────────────────────────── */
[data-testid="stSidebarNav"]::before {
    content: "☰  Main Menu";
    display: block;
    font-size: 18px;
    font-weight: bold;
    color: var(--text-color);
    padding: 12px 16px 8px 16px;
    border-bottom: 1px solid rgba(128,128,128,0.2);
    margin-bottom: 4px;
}

/* ── Sembunyikan label "default" bawaan Streamlit (nama file) ────────── */
[data-testid="stSidebarNav"] span[data-testid="stSidebarNavLinkText"] {
    font-size: 15px;
}

/* ── Style setiap nav link ───────────────────────────────────────────── */
[data-testid="stSidebarNav"] a {
    border-radius: 8px;
    margin: 2px 6px;
    padding: 8px 12px;
    display: flex;
    align-items: center;
    text-decoration: none;
    color: var(--text-color) !important;
    transition: background-color 0.15s ease;
}

/* ── Hover effect ────────────────────────────────────────────────────── */
[data-testid="stSidebarNav"] a:hover {
    background-color: var(--secondary-background-color);
}

/* ── Halaman yang sedang aktif: merah seperti option_menu sebelumnya ─── */
[data-testid="stSidebarNav"] a[aria-current="page"] {
    background-color: #ff4b4b !important;
    color: white !important;
}
[data-testid="stSidebarNav"] a[aria-current="page"] span {
    color: white !important;
}

/* ── Icon di sebelah label (SVG bawaan Streamlit) ────────────────────── */
[data-testid="stSidebarNav"] svg {
    width: 18px;
    height: 18px;
    margin-right: 8px;
    flex-shrink: 0;
}

/* ── Hilangkan garis pemisah antar section yang tidak dipakai ─────────── */
[data-testid="stSidebarNavSeparator"] {
    display: none;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# DEFAULT FILTER VALUES
# ─────────────────────────────────────────────────────────────────────────────

date_from                = datetime.now().date() - timedelta(days=90)
date_to                  = datetime.now().date()
selected_department      = ['All']
selected_p_group         = ['All']
selected_bagian          = ['All']
exclude_dept             = False
exclude_purchasing_group = False
exclude_bagian           = False

# ─────────────────────────────────────────────────────────────────────────────
# DEFINISI HALAMAN - Wrapper agar filter bisa diakses saat render
# ─────────────────────────────────────────────────────────────────────────────
# Pola: setiap _render_* membaca view_args dari session_state.
# view_args diisi SETELAH filter sidebar selesai (di bawah), lalu pg.run()
# memanggil fungsi yang tepat berdasarkan URL saat ini.
# ─────────────────────────────────────────────────────────────────────────────

def _render_dashboard():    v_dashboard.render(**st.session_state.get('_view_args', {}))
def _render_detail():       v_detail.render(**st.session_state.get('_view_args', {}))
def _render_evaluasi():     v_evaluasi.render(**st.session_state.get('_view_args', {}))
def _render_kinerja():      v_kinerja_pg.render(**st.session_state.get('_view_args', {}))
def _render_alert():        v_alert.render(**st.session_state.get('_view_args', {}))

# ─────────────────────────────────────────────────────────────────────────────
# st.navigation() - POSISI SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

pg = st.navigation(
    [
        st.Page(_render_dashboard, title="Dashboard Monitoring",     icon=":material/dashboard:"),
        st.Page(_render_detail,    title="Detailed PR-PO Data",      icon=":material/unknown_document:"),
        st.Page(_render_evaluasi,  title="Evaluasi Harga Barang",    icon=":material/sell:"),
        st.Page(_render_kinerja,   title="Kinerja Purchasing Group", icon=":material/checked_bag:"),
        st.Page(_render_alert,     title="Halaman Alert",            icon=":material/assignment_late:"),
    ],
    position="sidebar",   # ← bawaan Streamlit, Back button berfungsi
)

# Tutup changelog otomatis saat navigasi halaman (Back/Forward atau klik menu)
current_page = pg.title
if 'last_page' not in st.session_state:
    st.session_state.last_page = current_page
if current_page != st.session_state.last_page:
    st.session_state.show_changelog = False
    st.session_state.last_page = current_page

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR FILTERS - Tampil di bawah nav bawaan Streamlit
# ─────────────────────────────────────────────────────────────────────────────

st.sidebar.markdown("""
    <h2 style='display:flex; align-items:center; font-size:20px;
               color:var(--text-color); margin-top:4px; margin-bottom:4px;'>
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"
             fill="currentColor" viewBox="0 0 16 16" style="margin-right:8px;">
            <path d="M1.5 1.5A.5.5 0 0 1 2 1h12a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-.128.334
                     L10 8.692V13.5a.5.5 0 0 1-.342.474l-3 1A.5.5 0 0 1 6 14.5V8.692
                     L1.628 3.834A.5.5 0 0 1 1.5 3.5z"/>
        </svg>
        Filters
    </h2>
    <hr style='margin:4px 0 12px 0; border-color:rgba(128,128,128,0.3);'>
""", unsafe_allow_html=True)

try:
    departments  = load_data("SELECT DISTINCT department_code FROM departments ORDER BY department_code")
    bagian_data  = load_data("""
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

    def update_dept_logic():
        current = st.session_state.filter_dept
        prev    = st.session_state.prev_filter_dept
        if 'All' in current and 'All' not in prev:
            st.session_state.filter_dept = ['All']
        elif 'All' in current and len(current) > 1:
            st.session_state.filter_dept = [x for x in current if x != 'All']
        elif not current:
            st.session_state.filter_dept = ['All']
        st.session_state.prev_filter_dept = st.session_state.filter_dept

    def update_pgroup_logic():
        current = st.session_state.filter_pgroup
        prev    = st.session_state.prev_filter_pgroup
        if 'All' in current and 'All' not in prev:
            st.session_state.filter_pgroup = ['All']
        elif 'All' in current and len(current) > 1:
            st.session_state.filter_pgroup = [x for x in current if x != 'All']
        elif not current:
            st.session_state.filter_pgroup = ['All']
        st.session_state.prev_filter_pgroup = st.session_state.filter_pgroup

    # ── Department ────────────────────────────────────────────────────────────
    st.sidebar.markdown("""
    <p style='font-size:14px; font-weight:600; color:var(--text-color);
              margin:0 0 4px 0; display:flex; align-items:center; gap:6px;'>
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"
             fill="currentColor" viewBox="0 0 16 16">
            <path d="M3 0a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h3v-3.5a.5.5 0 0 1 .5-.5h3
                     a.5.5 0 0 1 .5.5V16h3a1 1 0 0 0 1-1V1a1 1 0 0 0-1-1zm1 2.5a.5.5
                     0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0
                     1-.5-.5zm3 0a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0
                     1-.5.5h-1a.5.5 0 0 1-.5-.5zm3.5-.5h1a.5.5 0 0 1 .5.5v1a.5.5
                     0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5"/>
        </svg>
        Department
    </p>
    """, unsafe_allow_html=True)
    st.sidebar.multiselect(
        "Department",
        options=['All'] + departments['department_code'].tolist(),
        key="filter_dept", # Hubungkan dengan session state
        on_change=update_dept_logic, # Panggil logika saat berubah
        label_visibility="collapsed"
    )
    selected_department = st.session_state.filter_dept
    
    exclude_dept = False
    if 'All' not in selected_department and selected_department:
        exclude_dept = st.sidebar.checkbox(":material/block: Exclude selected Department")

    # ── Purchasing Group ──────────────────────────────────────────────────────
    st.sidebar.markdown("""
    <p style='font-size:14px; font-weight:600; color:var(--text-color);
              margin:8px 0 4px 0; display:flex; align-items:center; gap:6px;'>
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"
             fill="currentColor" viewBox="0 0 16 16">
            <path d="M7 14s-1 0-1-1 1-4 5-4 5 3 5 4-1 1-1 1zm4-6a3 3 0 1 0 0-6 3 3
                     0 0 0 0 6m-5.784 6A2.24 2.24 0 0 1 5 13c0-1.355.68-2.75
                     1.936-3.72A6.3 6.3 0 0 0 5 9c-4 0-5 3-5 4s1 1 1 1zM4.5 8a2.5
                     2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5"/>
        </svg>
        Purchasing Group
    </p>
    """, unsafe_allow_html=True)
    st.sidebar.multiselect(
        "Purchasing Group",
        options=options_p_group,
        key="filter_pgroup", # Hubungkan dengan session state
        on_change=update_pgroup_logic, # Panggil logika saat berubah
        label_visibility="collapsed"
    )
    selected_p_group = st.session_state.filter_pgroup
    
    exclude_purchasing_group = False
    if 'All' not in selected_p_group and selected_p_group:
        exclude_purchasing_group = st.sidebar.checkbox(":material/block: Exclude selected Purchasing Group")

    # ── Bagian ────────────────────────────────────────────────────────────────
    st.sidebar.markdown("""
    <p style='font-size:14px; font-weight:600; color:var(--text-color);
              margin:8px 0 4px 0; display:flex; align-items:center; gap:6px;'>
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"
             fill="currentColor" viewBox="0 0 16 16">
            <path fill-rule="evenodd" d="M6 3.5A1.5 1.5 0 0 1 7.5 2h1A1.5 1.5 0 0 1
                 10 3.5v1A1.5 1.5 0 0 1 8.5 6v1H14a.5.5 0 0 1 .5.5v1a.5.5 0 0
                 1-1 0V8h-5v.5a.5.5 0 0 1-1 0V8h-5v.5a.5.5 0 0 1-1 0v-1A.5.5
                 0 0 1 2 7h5.5V6A1.5 1.5 0 0 1 6 4.5z"/>
            <path d="M2.5 9.5A1.5 1.5 0 0 1 4 8.5h1A1.5 1.5 0 0 1 6.5 10v1A1.5
                     1.5 0 0 1 5 12.5H4A1.5 1.5 0 0 1 2.5 11zm5 0A1.5 1.5 0 0 1
                     9 8.5h1a1.5 1.5 0 0 1 1.5 1.5v1A1.5 1.5 0 0 1 10 12.5H9A1.5
                     1.5 0 0 1 7.5 11zm5 0A1.5 1.5 0 0 1 14 8.5h1a1.5 1.5 0 0 1
                     1.5 1.5v1A1.5 1.5 0 0 1 15 12.5h-1A1.5 1.5 0 0 1 12.5 11z"/>
        </svg>
        Bagian
    </p>
    """, unsafe_allow_html=True)
    st.sidebar.pills(
        "Bagian",
        options=options_bagian,
        selection_mode="multi",
        key="filter_bagian",
        on_change=update_bagian_logic,
        label_visibility="collapsed"
    )
    selected_bagian = st.session_state.filter_bagian

    # ── Date Range ────────────────────────────────────────────────────────────
    st.sidebar.markdown("""
    <p style='font-size:14px; font-weight:600; color:var(--text-color);
              margin:8px 0 4px 0; display:flex; align-items:center; gap:6px;'>
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"
             fill="currentColor" viewBox="0 0 16 16">
            <path d="M9 7a1 1 0 0 1 1-1h5v2h-5a1 1 0 0 1-1-1M1 7a1 1 0 0 0 1
                     1h5V6H2a1 1 0 0 0-1 1"/>
            <path d="M3.5 0a.5.5 0 0 1 .5.5V1h8V.5a.5.5 0 0 1 1 0V1h1a2 2 0 0
                     1 2 2v11a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2h1
                     V.5a.5.5 0 0 1 .5-.5M1 4v10a1 1 0 0 0 1 1h12a1 1 0 0 0
                     1-1V4z"/>
        </svg>
        Date Range
    </p>
    """, unsafe_allow_html=True)
    date_from = st.sidebar.date_input("From", value=datetime.now().date() - timedelta(days=360))
    date_to   = st.sidebar.date_input("To",   value=datetime.now().date())

    if st.sidebar.button("Refresh Data", icon=":material/refresh:"):
        st.cache_data.clear()
        st.rerun()

except Exception as e:
    st.sidebar.error(f"Error loading filters: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# BUILD VIEW ARGS & SIMPAN KE SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────

filter_conditions = build_filter_conditions(
    date_from, date_to,
    selected_department, exclude_dept,
    selected_p_group, exclude_purchasing_group
)
bagian_pr_cond, bagian_po_cond = build_bagian_conditions(selected_bagian, exclude_bagian)

st.session_state['_view_args'] = dict(
    filter_conditions=filter_conditions,
    bagian_pr_cond=bagian_pr_cond,
    bagian_po_cond=bagian_po_cond,
    load_data=load_data,
)

# ─────────────────────────────────────────────────────────────────────────────
# ROUTING EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

if st.session_state.show_changelog:
    v_changelog.render()
else:
    pg.run()

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
col_foot1, col_foot2 = st.columns([4, 1])

with col_foot1:
    st.markdown(
        f"<div style='color:#666; margin-top:10px;'>"
        f"PR-PO Monitoring System - v1.5 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        f"</div>",
        unsafe_allow_html=True
    )

with col_foot2:
    btn_label = "Kembali ke App" if st.session_state.show_changelog else "Log Perubahan"
    btn_icon  = ":material/arrow_back:" if st.session_state.show_changelog else ":material/history:"
    if st.button(btn_label, icon=btn_icon, use_container_width=True):
        st.session_state.show_changelog = not st.session_state.show_changelog
        st.rerun()