"""
app.py - File utama PR-PO Monitoring Dashboard
Jalankan dengan: streamlit run app.py

Navigasi: st.navigation() dengan grouped dict
  → Back/Forward browser berfungsi penuh
  → Section headers PR-PO SAP / SIPS distyle menjadi toggle pill
  → Filter sidebar berbeda per sistem
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import warnings
import base64
import os
warnings.filterwarnings('ignore')

# ── Load Dashboard icon (untuk page_icon & halaman login) ────────────────────
def _load_icon_b64(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None

_ICON_PATH = "assets/Dashboard_icon.png"
_icon_b64  = _load_icon_b64(_ICON_PATH)

from config_db import load_data
from utils import inject_css, build_filter_conditions, build_bagian_conditions, render_filter_bar
from context_builder import build_global_context


# Views - PR-PO SAP
from views import v_changelog, v_dashboard, v_detail, v_evaluasi, v_kinerja_pg, v_alert

# Views - SIPS
from views import v_sips_dashboard, v_sips_detail, v_sips_waktu

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

from PIL import Image
_page_icon = Image.open(_ICON_PATH) if os.path.exists(_ICON_PATH) else "📊"

st.set_page_config(
    page_title="Monitoring Dashboard",
    page_icon=_page_icon,
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_css()

# ─────────────────────────────────────────────────────────────────────────────
# AUTH — cek sebelum apapun dirender
# ─────────────────────────────────────────────────────────────────────────────

def render_login():
    """Tampilkan halaman login. Panggil st.stop() setelah ini jika belum auth."""
    # Sembunyikan sidebar saat halaman login
    st.markdown("""
        <style>
            [data-testid="stSidebar"] { display: none; }
            [data-testid="stSidebarNav"] { display: none; }
            .login-container {
                max-width: 400px;
                margin: 80px auto 0 auto;
                padding: 40px;
                border-radius: 16px;
                border: 1px solid rgba(128,128,128,0.2);
                background: var(--background-color);
                box-shadow: 0 4px 24px rgba(0,0,0,0.08);
            }
        </style>
    """, unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.markdown("""
            <div style='text-align:center; margin-bottom: 24px;'>
        """, unsafe_allow_html=True)

        # Tampilkan ikon dashboard jika tersedia, fallback ke emoji
        if _icon_b64:
            st.markdown(
                f"<div style='text-align:center;'>"
                f"<img src='data:image/png;base64,{_icon_b64}' "
                f"width='90' height='90' style='border-radius:16px; margin-bottom:12px;'>"
                f"</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown("<div style='text-align:center; font-size:56px;'>📊</div>", unsafe_allow_html=True)

        st.markdown("""
                <h2 style='font-size:24px; text-align:center; margin-left:18px;'>Monitoring Dashboard</h2>
                <p style='color: #888; font-size:14px; margin-bottom:18px; text-align:center;'>Pengadaan Barang</p>
            </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            password_input = st.text_input(
                "Password",
                type="password",
                placeholder="Masukkan password...",
                label_visibility="collapsed"
            )
            submitted = st.form_submit_button("Masuk", use_container_width=True, type="primary")

        if submitted:
            try:
                correct_password = st.secrets["auth"]["password"]
            except (KeyError, FileNotFoundError):
                st.error("Konfigurasi auth tidak ditemukan di secrets.")
                st.stop()

            if password_input == correct_password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Password salah. Silakan coba lagi.")

        st.markdown("""
            <p style='text-align:center; color:#aaa; font-size:12px; margin-top:24px;'>
                Hubungi administrator jika lupa password.
            </p>
        """, unsafe_allow_html=True)


# Inisialisasi state auth
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Blok akses — stop di sini jika belum login
if not st.session_state.authenticated:
    render_login()
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────

def init_state(key, value):
    if key not in st.session_state:
        st.session_state[key] = value

init_state('show_changelog',      False)
init_state('filter_mode',          'sidebar')  # 'sidebar' atau 'topbar'
# SAP filters
init_state('filter_bagian',       ['All'])
init_state('prev_filter_bagian',  ['All'])
init_state('filter_dept',         ['All'])
init_state('prev_filter_dept',    ['All'])
init_state('filter_pgroup',       ['All'])
init_state('prev_filter_pgroup',  ['All'])
# SIPS filters
init_state('sips_filter_nama',    ['All'])
init_state('sips_prev_nama',      ['All'])
init_state('sips_filter_bagian',  ['All'])
init_state('sips_prev_bagian',    ['All'])


# ─────────────────────────────────────────────────────────────────────────────
# DIALOG KONFIRMASI LOGOUT
# ─────────────────────────────────────────────────────────────────────────────

@st.dialog("Konfirmasi Logout")
def dialog_logout():
    # Paksa dialog ke tengah layar
    st.markdown("""
<style>
div[data-testid="stDialog"] > div > div {
    position: fixed !important;
    top: 50% !important;
    left: 50% !important;
    transform: translate(-50%, -50%) !important;
    margin: 0 !important;
}
</style>
""", unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align:center; font-size:15px; margin:8px 0 20px 0;'>"
        "Yakin ingin keluar dari dashboard?</p>",
        unsafe_allow_html=True
    )
    col_ya, col_tidak = st.columns(2)
    with col_ya:
        if st.button("Ya, Logout", icon=":material/logout:",
                     use_container_width=True, type="primary",
                     key="dlg_logout_ya"):
            st.session_state.authenticated = False
            st.rerun()
    with col_tidak:
        if st.button("Batal", icon=":material/close:",
                     use_container_width=True, key="dlg_logout_tidak"):
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# HALAMAN: render functions
# ─────────────────────────────────────────────────────────────────────────────

def _render_dashboard():    v_dashboard.render(**st.session_state.get('_view_args', {}))
def _render_detail():       v_detail.render(**st.session_state.get('_view_args', {}))
def _render_evaluasi():     v_evaluasi.render(**st.session_state.get('_view_args', {}))
def _render_kinerja():      v_kinerja_pg.render(**st.session_state.get('_view_args', {}))
def _render_alert():        v_alert.render(**st.session_state.get('_view_args', {}))
def _render_sips_dashboard(): v_sips_dashboard.render(**st.session_state.get('_sips_view_args', {}))
def _render_sips_detail():    v_sips_detail.render(**st.session_state.get('_sips_view_args', {}))
def _render_sips_waktu():     v_sips_waktu.render(**st.session_state.get('_sips_view_args', {}))

# ─────────────────────────────────────────────────────────────────────────────
# NAVIGATION: grouped dict agar muncul section header sebagai toggle
# ─────────────────────────────────────────────────────────────────────────────

pg = st.navigation(
    {
        "PR-PO SAP": [
            st.Page(_render_dashboard, title="Dashboard Monitoring SAP",     icon=":material/dashboard:"),
            st.Page(_render_detail,    title="Detailed PR-PO SAP Data",      icon=":material/unknown_document:"),
            st.Page(_render_evaluasi,  title="Evaluasi Harga Barang",    icon=":material/sell:"),
            st.Page(_render_kinerja,   title="Kinerja Purchasing Group", icon=":material/checked_bag:"),
            st.Page(_render_alert,     title="Halaman Alert",            icon=":material/assignment_late:"),
        ],
        "SIPS": [
            st.Page(_render_sips_dashboard, title="Dashboard Monitoring SIPS", icon=":material/dashboard:"),
            st.Page(_render_sips_detail,    title="Detailed SIPS Data",         icon=":material/unknown_document:"),
            st.Page(_render_sips_waktu, title="Analisis Waktu Proses SIPS", icon=":material/schedule:"),
            # Tambah halaman SIPS lain di sini
        ],
    },
    position="sidebar",
)

# Deteksi sistem aktif dari judul halaman yang sedang dibuka
SIPS_TITLES = {"Dashboard Monitoring SIPS", "Detailed SIPS Data", "Analisis Waktu Proses SIPS"}
current_page = pg.title
is_sips      = current_page in SIPS_TITLES

# Tutup changelog otomatis saat navigasi
if 'last_page' not in st.session_state:
    st.session_state.last_page = current_page
if current_page != st.session_state.last_page:
    st.session_state.show_changelog = False
    st.session_state.last_page = current_page

# ─────────────────────────────────────────────────────────────────────────────
# CSS: section headers menjadi toggle pill SAP / SIPS
# ─────────────────────────────────────────────────────────────────────────────

# Pill aktif: div ke-1 = PR-PO SAP, div ke-2 = SIPS
active_div = "2" if is_sips else "1"

st.markdown(f"""
<style>

/* ── Judul "Main Menu" ───────────────────────────────────────────────── */
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

/* ── Section headers → satu baris pill toggle ────────────────────────── */
[data-testid="stSidebarNavSeparator"] {{ display: none; }}

[data-testid="stSidebarNavItems"] {{
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 0 !important;
    padding: 6px 10px 2px 10px !important;
    align-items: center !important;
}}

[data-testid="stSidebarNavItems"] > div:has(> p) {{
    display: inline-flex !important;
    width: auto !important;
    margin: 0 !important;
}}

/* Tiap label section = pill */
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
    background: transparent !important;
    color: var(--text-color) !important;
    opacity: 0.6 !important;
}}

/* Pill aktif */
[data-testid="stSidebarNavItems"] > div:nth-of-type({active_div}) > p {{
    background: #ff4b4b !important;
    color: white !important;
    opacity: 1 !important;
    border-color: #ff4b4b !important;
}}

/* Nav link div block */
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

# JS: section header bisa diklik → pindah ke halaman pertama section-nya
st.components.v1.html("""
<script>
(function() {
    function makeHeadersClickable() {
        var doc = window.parent.document;
        var navItems = doc.querySelector('[data-testid="stSidebarNavItems"]');
        if (!navItems) { setTimeout(makeHeadersClickable, 200); return; }

        var divs = navItems.children;
        var sections = [];

        for (var i = 0; i < divs.length; i++) {
            var p = divs[i].querySelector('p');
            var a = divs[i].querySelector('a');
            if (p && !a) {
                for (var j = i + 1; j < divs.length; j++) {
                    var firstA = divs[j].querySelector('a');
                    if (firstA) { sections.push({ p: p, a: firstA }); break; }
                }
            }
        }

        sections.forEach(function(s) {
            if (s.p.dataset.clickable) return;
            s.p.dataset.clickable = '1';
            s.p.addEventListener('click', function() { s.a.click(); });
        });
    }
    setTimeout(makeHeadersClickable, 300);
    window.addEventListener('load', function() { setTimeout(makeHeadersClickable, 300); });
})();
</script>
""", height=0)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR FILTERS
# ─────────────────────────────────────────────────────────────────────────────

# Default values (dipakai jika filter tidak ter-render / error)
current_year = datetime.now().year
default_start_date = datetime(current_year, 1, 1).date()
date_from                = default_start_date
date_to                  = datetime.now().date()
selected_department      = ['All']
selected_p_group         = ['All']
selected_bagian          = ['All']
exclude_dept             = False
exclude_purchasing_group = False
exclude_bagian           = False
default_sips_start_date  = datetime(current_year, 1, 1).date()
sips_date_from           = default_sips_start_date
sips_date_to             = datetime.now().date()
sips_selected_nama       = ['All']
sips_selected_bagian     = ['All']

# ── Info data terakhir diambil ────────────────────────────────────────────────
st.sidebar.markdown("""
    <div style='
        background: rgba(31, 119, 180, 0.08);
        border: 1px solid rgba(31, 119, 180, 0.25);
        border-radius: 8px;
        padding: 8px 12px;
        margin-bottom: 10px;
    '>
        <p style='font-size:11px; color:var(--text-color); opacity:0.7; margin:0 0 4px 0;
                  display:flex; align-items:center; gap:5px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11"
                 fill="currentColor" viewBox="0 0 16 16">
                <path d="M8 3.5a.5.5 0 0 0-1 0V9a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0
                         0 .496-.868L8 8.71z"/>
                <path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16m7-8A7 7 0 1 1 1 8a7 7 0
                         0 1 14 0"/>
            </svg>
            Data terakhir diperbarui
        </p>
        <p style='font-size:12px; font-weight:600; color:var(--text-color); margin:0;'>
            SAP &nbsp;→&nbsp; 28 Februari 2026
        </p>
        <p style='font-size:12px; font-weight:600; color:var(--text-color); margin:3px 0 0 0;'>
            SIPS &nbsp;→&nbsp; 28 Februari 2026
        </p>
    </div>
""", unsafe_allow_html=True)

# ── Toggle filter mode + header ──────────────────────────────────────────────
_mode_label = "⬆ Top Bar" if st.session_state.filter_mode == 'sidebar' else "⬅ Sidebar"
_mode_help  = "Pindahkan filter ke atas halaman" if st.session_state.filter_mode == 'sidebar' else "Pindahkan filter ke sidebar"

col_fh, col_toggle = st.sidebar.columns([3, 2])
with col_fh:
    st.markdown("""
        <h2 style='display:flex; align-items:center; font-size:20px;
                   color:var(--text-color); margin-top:4px; margin-bottom:4px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18"
                 fill="currentColor" viewBox="0 0 16 16" style="margin-right:8px;">
                <path d="M1.5 1.5A.5.5 0 0 1 2 1h12a.5.5 0 0 1 .5.5v2a.5.5 0 0
                         1-.128.334L10 8.692V13.5a.5.5 0 0 1-.342.474l-3 1A.5.5 0
                         0 1 6 14.5V8.692L1.628 3.834A.5.5 0 0 1 1.5 3.5z"/>
            </svg>
            Filters
        </h2>
    """, unsafe_allow_html=True)
with col_toggle:
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    if st.button(_mode_label, help=_mode_help, use_container_width=True,
                 key="btn_toggle_filter_mode"):
        st.session_state.filter_mode = (
            'topbar' if st.session_state.filter_mode == 'sidebar' else 'sidebar'
        )
        st.rerun()

st.sidebar.markdown("<hr style='margin:4px 0 12px 0; border-color:rgba(128,128,128,0.3);'>",
                    unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# FILTERS PR-PO SAP / SIPS — hanya tampil jika mode sidebar
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.filter_mode == 'sidebar' and not is_sips:
    try:
        departments  = load_data("SELECT DISTINCT department_code FROM departments ORDER BY department_code")
        bagian_data  = load_data("""
            SELECT DISTINCT bagian_pr AS bagian FROM vw_pr_po_complete WHERE bagian_pr IS NOT NULL AND bagian_pr != 'UNKNOWN'
            UNION
            SELECT DISTINCT bagian_po AS bagian FROM vw_pr_po_complete WHERE bagian_po IS NOT NULL AND bagian_po != 'UNKNOWN'
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
            cur, prv = st.session_state.filter_bagian, st.session_state.prev_filter_bagian
            if 'All' in cur and 'All' not in prv:   st.session_state.filter_bagian = ['All']
            elif 'All' in cur and len(cur) > 1:      st.session_state.filter_bagian = [x for x in cur if x != 'All']
            elif not cur:                             st.session_state.filter_bagian = ['All']
            st.session_state.prev_filter_bagian = st.session_state.filter_bagian

        def update_dept_logic():
            cur, prv = st.session_state.filter_dept, st.session_state.prev_filter_dept
            if 'All' in cur and 'All' not in prv:   st.session_state.filter_dept = ['All']
            elif 'All' in cur and len(cur) > 1:      st.session_state.filter_dept = [x for x in cur if x != 'All']
            elif not cur:                             st.session_state.filter_dept = ['All']
            st.session_state.prev_filter_dept = st.session_state.filter_dept

        def update_pgroup_logic():
            cur, prv = st.session_state.filter_pgroup, st.session_state.prev_filter_pgroup
            if 'All' in cur and 'All' not in prv:   st.session_state.filter_pgroup = ['All']
            elif 'All' in cur and len(cur) > 1:      st.session_state.filter_pgroup = [x for x in cur if x != 'All']
            elif not cur:                             st.session_state.filter_pgroup = ['All']
            st.session_state.prev_filter_pgroup = st.session_state.filter_pgroup

        # ── Department ────────────────────────────────────────────────────────
        st.sidebar.markdown("""
        <p style='font-size:14px; font-weight:600; color:var(--text-color);
                  margin:0 0 4px 0; display:flex; align-items:center; gap:6px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"
                 fill="currentColor" viewBox="0 0 16 16">
                <path d="M3 0a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h3v-3.5a.5.5 0 0 1
                         .5-.5h3a.5.5 0 0 1 .5.5V16h3a1 1 0 0 0 1-1V1a1 1 0 0
                         0-1-1zm1 2.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5
                         0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm3 0a.5.5 0 0 1 .5-.5h1
                         a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5z
                         m3.5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0
                         0 1-.5-.5v-1a.5.5 0 0 1 .5-.5"/>
            </svg>
            Department
        </p>
        """, unsafe_allow_html=True)
        st.sidebar.multiselect("Department",
            options=['All'] + departments['department_code'].tolist(),
            key="filter_dept", on_change=update_dept_logic, label_visibility="collapsed")
        selected_department = st.session_state.filter_dept
        exclude_dept = False
        if 'All' not in selected_department and selected_department:
            exclude_dept = st.sidebar.checkbox(":material/block: Exclude selected Department")

        # ── Purchasing Group ──────────────────────────────────────────────────
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
        st.sidebar.multiselect("Purchasing Group",
            options=options_p_group,
            key="filter_pgroup", on_change=update_pgroup_logic, label_visibility="collapsed")
        selected_p_group = st.session_state.filter_pgroup
        exclude_purchasing_group = False
        if 'All' not in selected_p_group and selected_p_group:
            exclude_purchasing_group = st.sidebar.checkbox(":material/block: Exclude selected Purchasing Group")

        # ── Bagian ────────────────────────────────────────────────────────────
        st.sidebar.markdown("""
        <p style='font-size:14px; font-weight:600; color:var(--text-color);
                  margin:8px 0 4px 0; display:flex; align-items:center; gap:6px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"
                 fill="currentColor" viewBox="0 0 16 16">
                <path fill-rule="evenodd" d="M6 3.5A1.5 1.5 0 0 1 7.5 2h1A1.5 1.5
                     0 0 1 10 3.5v1A1.5 1.5 0 0 1 8.5 6v1H14a.5.5 0 0 1 .5.5v1
                     a.5.5 0 0 1-1 0V8h-5v.5a.5.5 0 0 1-1 0V8h-5v.5a.5.5 0 0
                     1-1 0v-1A.5.5 0 0 1 2 7h5.5V6A1.5 1.5 0 0 1 6 4.5z"/>
                <path d="M2.5 9.5A1.5 1.5 0 0 1 4 8.5h1A1.5 1.5 0 0 1 6.5 10v1
                         A1.5 1.5 0 0 1 5 12.5H4A1.5 1.5 0 0 1 2.5 11zm5 0A1.5
                         1.5 0 0 1 9 8.5h1a1.5 1.5 0 0 1 1.5 1.5v1A1.5 1.5 0 0
                         1 10 12.5H9A1.5 1.5 0 0 1 7.5 11zm5 0A1.5 1.5 0 0 1 14
                         8.5h1a1.5 1.5 0 0 1 1.5 1.5v1A1.5 1.5 0 0 1 15 12.5h-1
                         A1.5 1.5 0 0 1 12.5 11z"/>
            </svg>
            Bagian
        </p>
        """, unsafe_allow_html=True)
        st.sidebar.pills("Bagian", options=options_bagian, selection_mode="multi",
            key="filter_bagian", on_change=update_bagian_logic, label_visibility="collapsed")
        selected_bagian = st.session_state.filter_bagian

        # ── Date Range ────────────────────────────────────────────────────────
        st.sidebar.markdown("""
        <p style='font-size:14px; font-weight:600; color:var(--text-color);
                  margin:8px 0 4px 0; display:flex; align-items:center; gap:6px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"
                 fill="currentColor" viewBox="0 0 16 16">
                <path d="M3.5 0a.5.5 0 0 1 .5.5V1h8V.5a.5.5 0 0 1 1 0V1h1a2 2
                         0 0 1 2 2v11a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V3a2 2 0 0
                         1 2-2h1V.5a.5.5 0 0 1 .5-.5M1 4v10a1 1 0 0 0 1 1h12a1
                         1 0 0 0 1-1V4z"/>
            </svg>
            Date Range
        </p>
        """, unsafe_allow_html=True)
        date_from = st.sidebar.date_input("SAP From", value=default_start_date)
        date_to   = st.sidebar.date_input("SAP To",   value=datetime.now().date())

        if st.sidebar.button("Refresh Data", icon=":material/refresh:"):
            st.cache_data.clear()
            st.rerun()

    except Exception as e:
        st.sidebar.error(f"Error loading filters: {e}")

elif st.session_state.filter_mode == 'sidebar' and is_sips:
    try:
        # Nama difilter berdasarkan Bagian yang dipilih
        if 'All' not in sips_selected_bagian and sips_selected_bagian:
            bagian_sql = "', '".join(sips_selected_bagian)
            nama_data = load_data(f"""
                SELECT DISTINCT nama FROM sips_employees
                WHERE bagian IN ('{bagian_sql}') ORDER BY nama
            """)
        else:
            nama_data = load_data("""
                SELECT DISTINCT nama FROM sips_employees
                WHERE bagian IS NOT NULL ORDER BY nama

            """)

        options_nama = ['All'] + nama_data['nama'].tolist()

        def update_nama_logic():
            cur, prv = st.session_state.sips_filter_nama, st.session_state.sips_prev_nama
            if 'All' in cur and 'All' not in prv:   st.session_state.sips_filter_nama = ['All']
            elif 'All' in cur and len(cur) > 1:      st.session_state.sips_filter_nama = [x for x in cur if x != 'All']
            elif not cur:                             st.session_state.sips_filter_nama = ['All']
            st.session_state.sips_prev_nama = st.session_state.sips_filter_nama

        # ── Filter Nama ───────────────────────────────────────────────────────
        st.sidebar.markdown("""
        <p style='font-size:14px; font-weight:600; color:var(--text-color);
                  margin:8px 0 4px 0; display:flex; align-items:center; gap:6px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"
                 fill="currentColor" viewBox="0 0 16 16">
                <path d="M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6m2-3a2 2 0 1 1-4 0 2
                         2 0 0 1 4 0m4 8c0 1-1 1-1 1H3s-1 0-1-1 1-4 6-4 6 3
                         6 4m-1-.004c-.001-.246-.154-.986-.832-1.664C11.516 10.68
                         10.289 10 8 10s-3.516.68-4.168 1.332c-.678.678-.83
                         1.418-.832 1.664z"/>
            </svg>
            Nama
        </p>
        """, unsafe_allow_html=True)
        st.sidebar.multiselect("Nama",
            options=options_nama,
            key="sips_filter_nama",
            on_change=update_nama_logic,
            label_visibility="collapsed"
        )
        sips_selected_nama = st.session_state.sips_filter_nama

        bagian_data = load_data("""
            SELECT DISTINCT bagian FROM sips_employees
            WHERE bagian IS NOT NULL ORDER BY bagian

        """)
        options_bagian_sips = ['All'] + bagian_data['bagian'].tolist()

        def update_bagian_sips_logic():
            cur, prv = st.session_state.sips_filter_bagian, st.session_state.sips_prev_bagian
            if 'All' in cur and 'All' not in prv:   st.session_state.sips_filter_bagian = ['All']
            elif 'All' in cur and len(cur) > 1:      st.session_state.sips_filter_bagian = [x for x in cur if x != 'All']
            elif not cur:                             st.session_state.sips_filter_bagian = ['All']
            # Reset filter nama saat bagian berubah
            st.session_state.sips_filter_nama = ['All']
            st.session_state.sips_prev_bagian = st.session_state.sips_filter_bagian

        # ── Filter Bagian ─────────────────────────────────────────────────────
        st.sidebar.markdown("""
        <p style='font-size:14px; font-weight:600; color:var(--text-color);
                  margin:0 0 4px 0; display:flex; align-items:center; gap:6px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"
                 fill="currentColor" viewBox="0 0 16 16">
                <path fill-rule="evenodd" d="M6 3.5A1.5 1.5 0 0 1 7.5 2h1A1.5 1.5
                     0 0 1 10 3.5v1A1.5 1.5 0 0 1 8.5 6v1H14a.5.5 0 0 1 .5.5v1
                     a.5.5 0 0 1-1 0V8h-5v.5a.5.5 0 0 1-1 0V8h-5v.5a.5.5 0 0
                     1-1 0v-1A.5.5 0 0 1 2 7h5.5V6A1.5 1.5 0 0 1 6 4.5z"/>
                <path d="M2.5 9.5A1.5 1.5 0 0 1 4 8.5h1A1.5 1.5 0 0 1 6.5 10v1
                         A1.5 1.5 0 0 1 5 12.5H4A1.5 1.5 0 0 1 2.5 11zm5 0A1.5
                         1.5 0 0 1 9 8.5h1a1.5 1.5 0 0 1 1.5 1.5v1A1.5 1.5 0 0
                         1 10 12.5H9A1.5 1.5 0 0 1 7.5 11zm5 0A1.5 1.5 0 0 1 14
                         8.5h1a1.5 1.5 0 0 1 1.5 1.5v1A1.5 1.5 0 0 1 15 12.5h-1
                         A1.5 1.5 0 0 1 12.5 11z"/>
            </svg>
            Bagian
        </p>
        """, unsafe_allow_html=True)
        st.sidebar.pills("Bagian SIPS", options=options_bagian_sips, selection_mode="multi",
            key="sips_filter_bagian", on_change=update_bagian_sips_logic, label_visibility="collapsed")
        sips_selected_bagian = st.session_state.sips_filter_bagian

        # ── Date Range SIPS ───────────────────────────────────────────────────
        st.sidebar.markdown("""
        <p style='font-size:14px; font-weight:600; color:var(--text-color);
                  margin:8px 0 4px 0; display:flex; align-items:center; gap:6px; margin-top:6px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"
                 fill="currentColor" viewBox="0 0 16 16">
                <path d="M3.5 0a.5.5 0 0 1 .5.5V1h8V.5a.5.5 0 0 1 1 0V1h1a2 2
                         0 0 1 2 2v11a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V3a2 2 0 0
                         1 2-2h1V.5a.5.5 0 0 1 .5-.5M1 4v10a1 1 0 0 0 1 1h12a1
                         1 0 0 0 1-1V4z"/>
            </svg>
            Date Range
        </p>
        """, unsafe_allow_html=True)
        sips_date_from = st.sidebar.date_input("SIPS From", value=default_start_date)
        sips_date_to   = st.sidebar.date_input("SIPS To", value=datetime.now().date())

        if st.sidebar.button("Refresh Data", icon=":material/refresh:", key="sips_refresh"):
            st.cache_data.clear()
            st.rerun()

    except Exception as e:
        st.sidebar.error(f"Error loading SIPS filters: {e}")

# ── Tombol Logout — selalu di paling bawah sidebar ───────────────────────────
st.sidebar.markdown("---")
if st.sidebar.button("🔒  Logout", use_container_width=True, key="btn_logout"):
    dialog_logout()

# ─────────────────────────────────────────────────────────────────────────────
# DEFAULT FILTER VALUES  (dipakai untuk sistem yang TIDAK aktif saat ini)
# ─────────────────────────────────────────────────────────────────────────────

_default_start_date = datetime(current_year, 1, 1).date()
_default_date_from = _default_start_date
_default_date_to   = datetime.now().date()

# Default SAP (dipakai saat halaman SIPS aktif)
_default_filter_sap = build_filter_conditions(
    _default_date_from, _default_date_to,
    ['All'], False, ['All'], False
)
_default_bagian_pr, _default_bagian_po = build_bagian_conditions(['All'], False)
_default_teks_sap = f"""
- Tanggal: {_default_date_from} s.d {_default_date_to}
- Department: All | Purchasing Group: All | Bagian: All
"""

# Default SIPS (dipakai saat halaman SAP aktif)
_default_sips_nama       = ['All']
_default_sips_bagian     = ['All']
_default_teks_sips = f"""
- Tanggal: {_default_date_from} s.d {_default_date_to}
- Bagian: All
- Nama: All
"""

# ─────────────────────────────────────────────────────────────────────────────
# BUILD VIEW ARGS
# ─────────────────────────────────────────────────────────────────────────────

# SAP view args
filter_conditions = build_filter_conditions(
    date_from, date_to,
    selected_department, exclude_dept,
    selected_p_group, exclude_purchasing_group
)
bagian_pr_cond, bagian_po_cond = build_bagian_conditions(selected_bagian, exclude_bagian)

teks_filter_sap = f"""
- Tanggal: {date_from} s.d {date_to}
- Department: {', '.join(selected_department)} (Exclude: {exclude_dept})
- Purchasing Group: {', '.join(selected_p_group)} (Exclude: {exclude_purchasing_group})
- Bagian: {', '.join(selected_bagian)} (Exclude: {exclude_bagian})
"""

teks_filter_sips = f"""
- Tanggal: {sips_date_from} s.d {sips_date_to}
- Bagian: {', '.join(sips_selected_bagian)}
- Nama: {', '.join(sips_selected_nama)}
"""

# ── Bangun / refresh konteks global untuk Melati ────────────────────────────────
global_context = build_global_context(
    load_data      = load_data,
    is_sips        = is_sips,
    # SAP aktif
    filter_conditions   = filter_conditions,
    bagian_pr_cond      = bagian_pr_cond,
    bagian_po_cond      = bagian_po_cond,
    teks_filter_sap     = teks_filter_sap,
    date_from           = date_from,
    date_to             = date_to,
    # SIPS aktif
    sips_date_from      = sips_date_from,
    sips_date_to        = sips_date_to,
    sips_selected_nama  = sips_selected_nama,
    sips_selected_bagian = sips_selected_bagian,
    teks_filter_sips    = teks_filter_sips,
    # Default SAP (dipakai saat halaman SIPS)
    default_filter_conditions = _default_filter_sap,
    default_bagian_pr_cond    = _default_bagian_pr,
    default_bagian_po_cond    = _default_bagian_po,
    default_teks_filter_sap   = _default_teks_sap,
    # Default SIPS (dipakai saat halaman SAP)
    default_sips_date_from    = _default_date_from,
    default_sips_date_to      = _default_date_to,
    default_sips_selected_nama = _default_sips_nama,
    default_sips_selected_bagian = _default_sips_bagian,
    default_teks_filter_sips  = _default_teks_sips,
)

st.session_state['_view_args'] = dict(
    filter_conditions = filter_conditions,
    bagian_pr_cond    = bagian_pr_cond,
    bagian_po_cond    = bagian_po_cond,
    load_data         = load_data,
    info_filter       = teks_filter_sap,
    global_context    = global_context,
    date_from         = date_from,
    date_to           = date_to,
)

# SIPS view args
st.session_state['_sips_view_args'] = dict(
    load_data         = load_data,
    date_from         = sips_date_from,
    date_to           = sips_date_to,
    selected_nama     = sips_selected_nama,
    selected_bagian   = sips_selected_bagian,
    info_filter       = teks_filter_sips,
    global_context    = global_context,
)

# ─────────────────────────────────────────────────────────────────────────────
# FILTER BAR — top bar mode, dirender sekali sebelum konten halaman
# ─────────────────────────────────────────────────────────────────────────────

if st.session_state.filter_mode == 'topbar' and not st.session_state.show_changelog:
    if is_sips:
        render_filter_bar('sips', load_data)
        sips_date_from       = st.session_state.get('fb_sips_date_from',  sips_date_from)
        sips_date_to         = st.session_state.get('fb_sips_date_to',    sips_date_to)
        sips_selected_bagian = st.session_state.get('fb_sips_bagian',     ['All'])
        sips_selected_nama   = st.session_state.get('fb_sips_nama',       ['All'])
    else:
        render_filter_bar('sap', load_data)
        date_from           = st.session_state.get('fb_date_from',   date_from)
        date_to             = st.session_state.get('fb_date_to',     date_to)
        selected_department = st.session_state.get('fb_dept',        ['All'])
        selected_p_group    = st.session_state.get('fb_pgroup',      ['All'])
        selected_bagian     = st.session_state.get('fb_bagian',      ['All'])
        filter_conditions   = build_filter_conditions(
            date_from, date_to, selected_department, False, selected_p_group, False
        )
        bagian_pr_cond, bagian_po_cond = build_bagian_conditions(selected_bagian, False)

    # Rebuild teks filter & view args dengan nilai terbaru
    teks_filter_sap = f"""
- Tanggal: {date_from} s.d {date_to}
- Department: {', '.join(selected_department)}
- Purchasing Group: {', '.join(selected_p_group)}
- Bagian: {', '.join(selected_bagian)}
"""
    teks_filter_sips = f"""
- Tanggal: {sips_date_from} s.d {sips_date_to}
- Bagian: {', '.join(sips_selected_bagian)}
- Nama: {', '.join(sips_selected_nama)}
"""
    st.session_state['_view_args'].update(dict(
        filter_conditions = filter_conditions,
        bagian_pr_cond    = bagian_pr_cond,
        bagian_po_cond    = bagian_po_cond,
        info_filter       = teks_filter_sap,
        date_from         = date_from,
        date_to           = date_to,
    ))
    st.session_state['_sips_view_args'].update(dict(
        date_from       = sips_date_from,
        date_to         = sips_date_to,
        selected_nama   = sips_selected_nama,
        selected_bagian = sips_selected_bagian,
        info_filter     = teks_filter_sips,
    ))

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
        f"Monitoring Dashboard - {system_label} | v1.8.1 | "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        f"</div>",
        unsafe_allow_html=True
    )

with col_foot2:
    btn_label = "Kembali ke App" if st.session_state.show_changelog else "Log Perubahan"
    btn_icon  = ":material/arrow_back:" if st.session_state.show_changelog else ":material/history:"
    if st.button(btn_label, icon=btn_icon, use_container_width=True):
        st.session_state.show_changelog = not st.session_state.show_changelog
        st.rerun()