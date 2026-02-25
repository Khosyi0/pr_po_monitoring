"""
app.py - File utama PR-PO Monitoring Dashboard
Jalankan dengan: streamlit run app.py

Navigasi: st.navigation() dengan grouped sections (dict)
  → Back/Forward browser berfungsi penuh
  → Section headers di-style menjadi toggle SAP / SIPS
  → Filter sidebar conditional sesuai halaman aktif
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from config_db import load_data
from utils import inject_css, build_filter_conditions, build_bagian_conditions

# Views - PR-PO SAP
from views import v_changelog, v_dashboard, v_detail, v_evaluasi, v_kinerja_pg, v_alert

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Monitoring Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_css()

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────

def init_state(key, value):
    if key not in st.session_state:
        st.session_state[key] = value

init_state('show_changelog',      False)
init_state('filter_bagian',       ['All'])
init_state('prev_filter_bagian',  ['All'])
init_state('filter_dept',         ['All'])
init_state('prev_filter_dept',    ['All'])
init_state('filter_pgroup',       ['All'])
init_state('prev_filter_pgroup',  ['All'])

# ─────────────────────────────────────────────────────────────────────────────
# RENDER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _render_dashboard():    v_dashboard.render(**st.session_state.get('_view_args', {}))
def _render_detail():       v_detail.render(**st.session_state.get('_view_args', {}))
def _render_evaluasi():     v_evaluasi.render(**st.session_state.get('_view_args', {}))
def _render_kinerja():      v_kinerja_pg.render(**st.session_state.get('_view_args', {}))
def _render_alert():        v_alert.render(**st.session_state.get('_view_args', {}))

def _render_sips_dashboard():
    st.markdown("""
        <h1 style='display:flex; align-items:center; font-size:48px; gap:12px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="44" height="44"
                 fill="currentColor" viewBox="0 0 16 16">
                <path d="M0 0h1v15h15v1H0zm14.817 3.113a.5.5 0 0 1 .07.704l-4.5 5.5a.5.5
                         0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5
                         0 0 1 .758-.06l2.609 2.61 4.15-5.073a.5.5 0 0 1 .704-.07"/>
            </svg>
            SIPS Monitoring Dashboard
        </h1>
    """, unsafe_allow_html=True)
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
            <div style='text-align:center; padding:60px 20px;'>
                <div style='font-size:72px; margin-bottom:16px;'>⏳</div>
                <h2 style='font-size:24px; margin-bottom:8px;'>Menunggu Data</h2>
                <p style='opacity:0.6; font-size:15px; line-height:1.6;'>
                    Halaman ini akan menampilkan monitoring data dari aplikasi <strong>SIPS</strong>.<br>
                    Data Excel SIPS sedang disiapkan — dashboard akan diaktifkan<br>
                    setelah file diterima dan ETL selesai dikonfigurasi.
                </p>
            </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# NAVIGATION — grouped dict agar muncul section header SAP / SIPS
# ─────────────────────────────────────────────────────────────────────────────

pg = st.navigation(
    {
        "PR-PO SAP": [
            st.Page(_render_dashboard, title="Dashboard Monitoring",     icon=":material/dashboard:"),
            st.Page(_render_detail,    title="Detailed PR-PO Data",      icon=":material/unknown_document:"),
            st.Page(_render_evaluasi,  title="Evaluasi Harga Barang",    icon=":material/sell:"),
            st.Page(_render_kinerja,   title="Kinerja Purchasing Group", icon=":material/checked_bag:"),
            st.Page(_render_alert,     title="Halaman Alert",            icon=":material/assignment_late:"),
        ],
        "SIPS": [
            st.Page(_render_sips_dashboard, title="Dashboard Monitoring SIPS", icon=":material/dashboard:"),
            # Tambah halaman SIPS lain di sini nanti
        ],
    },
    position="sidebar",
)

# Tutup changelog saat navigasi halaman
current_page = pg.title
if 'last_page' not in st.session_state:
    st.session_state.last_page = current_page
if current_page != st.session_state.last_page:
    st.session_state.show_changelog = False
    st.session_state.last_page = current_page

# ─────────────────────────────────────────────────────────────────────────────
# CSS — style section headers menjadi toggle pill SAP / SIPS
# ─────────────────────────────────────────────────────────────────────────────

# Deteksi sistem aktif dari judul halaman
SIPS_TITLES = {"Dashboard Monitoring SIPS"}
is_sips = current_page in SIPS_TITLES

st.markdown(f"""
<style>

/* ── Judul "Main Menu" di atas nav ──────────────────────────────────── */
[data-testid="stSidebarNav"]::before {{
    content: "☰  Main Menu";
    display: block;
    font-size: 18px;
    font-weight: bold;
    color: var(--text-color);
    padding: 12px 16px 8px 16px;
    border-bottom: 1px solid rgba(128,128,128,0.2);
    margin-bottom: 4px;
}}

/* ── Section headers (PR-PO SAP / SIPS) jadi toggle pill ────────────── */
[data-testid="stSidebarNavSeparator"] {{
    display: none;   /* sembunyikan garis pemisah bawaan */
}}

/* Wrapper section header Streamlit */
[data-testid="stSidebarNavItems"] > div:has(> p) {{
    display: inline-flex !important;
    width: auto !important;
    margin: 0 !important;
}}

/* Bungkus semua section header dalam satu baris pill */
[data-testid="stSidebarNavItems"] {{
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 0 !important;
    padding: 6px 10px 2px 10px !important;
    align-items: center !important;
}}

/* Tiap label section = satu pill */
[data-testid="stSidebarNavItems"] > div > p {{
    font-size: 13px !important;
    font-weight: 600 !important;
    padding: 5px 16px !important;
    margin: 0 !important;
    border-radius: 20px !important;
    cursor: pointer !important;
    border: 1px solid rgba(128,128,128,0.3) !important;
    transition: all 0.15s !important;
    white-space: nowrap !important;
    line-height: 1.4 !important;
}}

/* Pill tidak aktif */
[data-testid="stSidebarNavItems"] > div > p {{
    background: transparent !important;
    color: var(--text-color) !important;
    opacity: 0.6 !important;
}}

/* Pill aktif — deteksi via urutan:
   div:nth-of-type(1) = PR-PO SAP, div:nth-of-type(2) = SIPS */
[data-testid="stSidebarNavItems"] > div:nth-of-type({"2" if is_sips else "1"}) > p {{
    background: #ff4b4b !important;
    color: white !important;
    opacity: 1 !important;
    border-color: #ff4b4b !important;
}}

/* Div pembungkus halaman-halaman per section */
[data-testid="stSidebarNavItems"] > div:has(> a) {{
    width: 100% !important;
    display: block !important;
    padding: 0 !important;
    margin: 0 !important;
}}

/* ── Nav link style ──────────────────────────────────────────────────── */
[data-testid="stSidebarNav"] a {{
    border-radius: 8px;
    margin: 2px 6px;
    padding: 8px 12px;
    display: flex;
    align-items: center;
    text-decoration: none;
    color: var(--text-color) !important;
    transition: background-color 0.15s ease;
}}
[data-testid="stSidebarNav"] a:hover {{
    background-color: var(--secondary-background-color);
}}
[data-testid="stSidebarNav"] a[aria-current="page"] {{
    background-color: #ff4b4b !important;
    color: white !important;
}}
[data-testid="stSidebarNav"] a[aria-current="page"] span {{
    color: white !important;
}}
[data-testid="stSidebarNav"] svg {{
    width: 18px;
    height: 18px;
    margin-right: 8px;
    flex-shrink: 0;
}}
[data-testid="stSidebarNav"] span[data-testid="stSidebarNavLinkText"] {{
    font-size: 15px;
}}

</style>
""", unsafe_allow_html=True)

# JS: buat section header bisa diklik → pindah ke halaman pertama di section
st.components.v1.html("""
<script>
(function() {
    function makeHeadersClickable() {
        var doc = window.parent.document;
        var navItems = doc.querySelector('[data-testid="stSidebarNavItems"]');
        if (!navItems) { setTimeout(makeHeadersClickable, 200); return; }

        var divs = navItems.children;
        var sections = [];  // kumpulkan {headerP, firstLink}

        for (var i = 0; i < divs.length; i++) {
            var p = divs[i].querySelector('p');          // section label
            var a = divs[i].querySelector('a');          // nav link

            if (p && !a) {
                // Ini section header — cari link pertama di section berikutnya
                for (var j = i + 1; j < divs.length; j++) {
                    var firstA = divs[j].querySelector('a');
                    if (firstA) {
                        sections.push({ p: p, a: firstA });
                        break;
                    }
                }
            }
        }

        sections.forEach(function(s) {
            // Hanya tambah listener sekali
            if (s.p.dataset.clickable) return;
            s.p.dataset.clickable = '1';
            s.p.style.cursor = 'pointer';
            s.p.addEventListener('click', function() {
                s.a.click();
            });
        });
    }
    setTimeout(makeHeadersClickable, 300);
    window.addEventListener('load', function() { setTimeout(makeHeadersClickable, 300); });
})();
</script>
""", height=0)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR FILTERS — conditional berdasarkan sistem aktif
# ─────────────────────────────────────────────────────────────────────────────

# Default values
date_from                = datetime.now().date() - timedelta(days=360)
date_to                  = datetime.now().date()
selected_department      = ['All']
selected_p_group         = ['All']
selected_bagian          = ['All']
exclude_dept             = False
exclude_purchasing_group = False
exclude_bagian           = False

st.sidebar.markdown("""
    <h2 style='display:flex; align-items:center; font-size:20px;
               color:var(--text-color); margin-top:4px; margin-bottom:4px;'>
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"
             fill="currentColor" viewBox="0 0 16 16" style="margin-right:8px;">
            <path d="M1.5 1.5A.5.5 0 0 1 2 1h12a.5.5 0 0 1 .5.5v2a.5.5 0 0
                     1-.128.334L10 8.692V13.5a.5.5 0 0 1-.342.474l-3 1A.5.5 0
                     0 1 6 14.5V8.692L1.628 3.834A.5.5 0 0 1 1.5 3.5z"/>
        </svg>
        Filters
    </h2>
    <hr style='margin:4px 0 12px 0; border-color:rgba(128,128,128,0.3);'>
""", unsafe_allow_html=True)

# ── Filter PR-PO SAP ─────────────────────────────────────────────────────────
if not is_sips:
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

        # Department
        st.sidebar.markdown("""
        <p style='font-size:14px; font-weight:600; color:var(--text-color);
                  margin:0 0 4px 0; display:flex; align-items:center; gap:6px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"
                 fill="currentColor" viewBox="0 0 16 16">
                <path d="M3 0a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h3v-3.5a.5.5 0 0 1
                         .5-.5h3a.5.5 0 0 1 .5.5V16h3a1 1 0 0 0 1-1V1a1 1 0 0
                         0-1-1zm1 2.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5
                         0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm3 0a.5.5 0 0 1 .5-.5h1a.5.5
                         0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm3.5-.5h1a.5.5
                         0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5v-1a.5.5
                         0 0 1 .5-.5"/>
            </svg>
            Department
        </p>
        """, unsafe_allow_html=True)
        st.sidebar.multiselect(
            "Department",
            options=['All'] + departments['department_code'].tolist(),
            key="filter_dept",
            on_change=update_dept_logic,
            label_visibility="collapsed"
        )
        selected_department = st.session_state.filter_dept
        exclude_dept = False
        if 'All' not in selected_department and selected_department:
            exclude_dept = st.sidebar.checkbox(":material/block: Exclude selected Department")

        # Purchasing Group
        st.sidebar.markdown("""
        <p style='font-size:14px; font-weight:600; color:var(--text-color);
                  margin:8px 0 4px 0; display:flex; align-items:center; gap:6px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"
                 fill="currentColor" viewBox="0 0 16 16">
                <path d="M7 14s-1 0-1-1 1-4 5-4 5 3 5 4-1 1-1 1zm4-6a3 3 0 1 0
                         0-6 3 3 0 0 0 0 6m-5.784 6A2.24 2.24 0 0 1 5 13c0-1.355
                         .68-2.75 1.936-3.72A6.3 6.3 0 0 0 5 9c-4 0-5 3-5 4s1
                         1 1 1zM4.5 8a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5"/>
            </svg>
            Purchasing Group
        </p>
        """, unsafe_allow_html=True)
        st.sidebar.multiselect(
            "Purchasing Group",
            options=options_p_group,
            key="filter_pgroup",
            on_change=update_pgroup_logic,
            label_visibility="collapsed"
        )
        selected_p_group = st.session_state.filter_pgroup
        exclude_purchasing_group = False
        if 'All' not in selected_p_group and selected_p_group:
            exclude_purchasing_group = st.sidebar.checkbox(":material/block: Exclude selected Purchasing Group")

        # Bagian
        st.sidebar.markdown("""
        <p style='font-size:14px; font-weight:600; color:var(--text-color);
                  margin:8px 0 4px 0; display:flex; align-items:center; gap:6px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"
                 fill="currentColor" viewBox="0 0 16 16">
                <path fill-rule="evenodd" d="M6 3.5A1.5 1.5 0 0 1 7.5 2h1A1.5 1.5
                     0 0 1 10 3.5v1A1.5 1.5 0 0 1 8.5 6v1H14a.5.5 0 0 1 .5.5v1a.5.5
                     0 0 1-1 0V8h-5v.5a.5.5 0 0 1-1 0V8h-5v.5a.5.5 0 0 1-1 0v-1
                     A.5.5 0 0 1 2 7h5.5V6A1.5 1.5 0 0 1 6 4.5z"/>
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

        # Date Range
        st.sidebar.markdown("""
        <p style='font-size:14px; font-weight:600; color:var(--text-color);
                  margin:8px 0 4px 0; display:flex; align-items:center; gap:6px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"
                 fill="currentColor" viewBox="0 0 16 16">
                <path d="M9 7a1 1 0 0 1 1-1h5v2h-5a1 1 0 0 1-1-1M1 7a1 1 0 0 0
                         1 1h5V6H2a1 1 0 0 0-1 1"/>
                <path d="M3.5 0a.5.5 0 0 1 .5.5V1h8V.5a.5.5 0 0 1 1 0V1h1a2 2
                         0 0 1 2 2v11a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V3a2 2 0 0 1
                         2-2h1V.5a.5.5 0 0 1 .5-.5M1 4v10a1 1 0 0 0 1 1h12a1 1
                         0 0 0 1-1V4z"/>
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

# ── Filter SIPS ───────────────────────────────────────────────────────────────
else:
    st.sidebar.markdown("""
        <div style='background:var(--secondary-background-color); border-radius:8px;
                    padding:14px 16px; font-size:13px; color:var(--text-color);
                    opacity:0.7; text-align:center; line-height:1.7;'>
            ⏳ Filter SIPS akan tersedia<br>setelah data diterima
        </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# BUILD VIEW ARGS
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
# ROUTING
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
    system_label = "SIPS" if is_sips else "PR-PO SAP"
    st.markdown(
        f"<div style='color:#666; margin-top:10px;'>"
        f"Monitoring Dashboard — {system_label} | v1.6 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        f"</div>",
        unsafe_allow_html=True
    )

with col_foot2:
    if not is_sips:
        btn_label = "Kembali ke App" if st.session_state.show_changelog else "Log Perubahan"
        btn_icon  = ":material/arrow_back:" if st.session_state.show_changelog else ":material/history:"
        if st.button(btn_label, icon=btn_icon, use_container_width=True):
            st.session_state.show_changelog = not st.session_state.show_changelog
            st.rerun()