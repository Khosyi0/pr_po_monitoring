"""
utils.py - Fungsi pembantu: format uang, CSS, dan filter kondisi SQL
"""

import streamlit as st
import pandas as pd
from google import genai
from datetime import datetime
import base64
import os
import numpy as np

# =============================================================================
# FORMAT ANGKA & RUPIAH (STANDAR INDONESIA)
# =============================================================================

def format_number(x, decimals=0) -> str:
    """Format angka biasa ke standar Indonesia (titik untuk ribuan, koma untuk desimal)."""
    if x is None or pd.isna(x):
        return "0"
    
    if decimals > 0:
        raw_formatted = f"{float(x):,.{decimals}f}"
    else:
        raw_formatted = f"{int(x):,}"
        
    formatted = raw_formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
    return formatted

def format_currency(x) -> str:
    """Format ke Rp X.XXX (tanpa singkatan T/M/Jt)."""
    if x is None or pd.isna(x) or x == 0:
        return "Rp 0"
    return f"Rp {format_number(x)}"

def format_idr(x) -> str:
    """Format angka menjadi string Rupiah dengan suffix T/M/Jt."""
    if x is None or pd.isna(x) or x == 0:
        return "Rp 0"

    abs_x = abs(x)
    if abs_x >= 1e12:
        val, suffix = x / 1e12, "T"
    elif abs_x >= 1e9:
        val, suffix = x / 1e9, "M"
    elif abs_x >= 1e6:
        val, suffix = x / 1e6, "Jt"
    else:
        return format_currency(x)

    formatted = f"{val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    if formatted.endswith(',00'):
        formatted = formatted[:-3]

    return f"Rp {formatted} {suffix}"

def format_idr_short(x) -> str:
    """Format angka ringkas untuk label chart (1 desimal)."""
    if x is None or pd.isna(x) or x == 0:
        return "0"

    abs_x = abs(x)
    if abs_x >= 1e12:
        val, suffix = x / 1e12, "T"
    elif abs_x >= 1e9:
        val, suffix = x / 1e9, "M"
    elif abs_x >= 1e6:
        val, suffix = x / 1e6, "Jt"
    else:
        return format_number(x)

    formatted = f"{val:,.1f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    if formatted.endswith(',0'):
        formatted = formatted[:-2]

    return f"{formatted} {suffix}"

def idr_axis(max_val, n_ticks=6) -> dict:
    if max_val is None or max_val <= 0:
        return {}

    step = max_val / (n_ticks - 1)
    tickvals = [round(step * i) for i in range(n_ticks)]

    def _fmt(v):
        abs_v = abs(v)
        if abs_v >= 1e12:
            val = v / 1e12
            s = "T"
        elif abs_v >= 1e9:
            val = v / 1e9
            s = "M"
        elif abs_v >= 1e6:
            val = v / 1e6
            s = "Jt"
        elif abs_v >= 1e3:
            val = v / 1e3
            s = "Rb"
        else:
            return str(int(v))
        
        txt = f"{val:,.1f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        if txt.endswith(',0'):
            txt = txt[:-2]
        return f"{txt} {s}"

    ticktext = [_fmt(v) for v in tickvals]

    return dict(
        tickvals=tickvals,
        ticktext=ticktext,
        range=[0, max_val],
    )

# =============================================================================
# CUSTOM CSS
# =============================================================================

def inject_css():
    """Inject custom CSS adaptive light/dark mode ke halaman."""
    st.markdown("""
<style>
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] div {
        color: var(--text-color);
    }
    h1 {
        color: #1f77b4;
    }
    .stMultiSelect, .stDateInput {
        background-color: transparent;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# FILTER SQL BUILDER
# =============================================================================

def build_filter_conditions(
    date_from, date_to,
    selected_department, exclude_dept,
    selected_p_group, exclude_purchasing_group
) -> str:
    """Bangun string kondisi WHERE untuk query SQL dari nilai filter sidebar.
    
    Filter tanggal menggunakan kolom `first_full_release` (bukan `tgl_create_pr`).
    Total PR dihitung dari baris yang memiliki `first_full_release IS NOT NULL`
    dan tanggalnya masuk dalam rentang periode yang dipilih.
    """
    conditions = [
        f"first_full_release >= '{date_from}'",
        f"first_full_release <= '{date_to}'"
    ]

    if selected_department and 'All' not in selected_department:
        dept_list = "','".join(selected_department)
        if exclude_dept:
            conditions.append(f"(department_code NOT IN ('{dept_list}') OR department_code IS NULL)")
        else:
            conditions.append(f"department_code IN ('{dept_list}')")

    if selected_p_group and 'All' not in selected_p_group:
        pg_list = "','".join(selected_p_group)
        if exclude_purchasing_group:
            conditions.append(f"(purchasing_group NOT IN ('{pg_list}') OR purchasing_group IS NULL)")
        else:
            conditions.append(f"purchasing_group IN ('{pg_list}')")

    return " AND ".join(conditions)

def build_po_filter_conditions(date_from, date_to, bagian_po_cond='1=1') -> str:
    """Bangun WHERE clause untuk query PO langsung dari tabel po_items + purchase_orders.
    Filter tanggal berdasarkan date_ordered (bukan tgl_create_pr).
    Dipakai untuk metrik PO di semua halaman agar konsisten dengan v_dashboard.
    """
    return (
        f"poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}' "
        f"AND {bagian_po_cond.replace('bagian_po', 'poi.bagian_po')}"
    )

def build_bagian_conditions(selected_bagian, exclude_bagian) -> tuple[str, str]:
    """Kembalikan tuple (bagian_pr_cond, bagian_po_cond) untuk filter bagian."""
    if 'All' not in selected_bagian and selected_bagian:
        bagian_list = "','".join(selected_bagian)
        if exclude_bagian:
            pr = f"(bagian_pr NOT IN ('{bagian_list}') OR bagian_pr IS NULL)"
            po = f"(bagian_po NOT IN ('{bagian_list}') OR bagian_po IS NULL)"
        else:
            pr = f"bagian_pr IN ('{bagian_list}')"
            po = f"bagian_po IN ('{bagian_list}')"
        return pr, po
    return "1=1", "1=1"

def build_dept_cond(col: str, selected_department, exclude_dept) -> str:
    """Bangun kondisi SQL filter Department untuk kolom tertentu.

    Dipakai pada query yang tidak JOIN ke vw_pr_po_complete, misalnya query
    langsung ke po_items (kolom `poi.department_code`) atau purchase_requisitions.

    Parameters
    ----------
    col : str
        Nama kolom department beserta alias tabel, misal ``'poi.department_code'``
        atau ``'pr.department_code'``.
    selected_department : list
        Daftar department yang dipilih. ``['All']`` berarti tidak ada filter.
    exclude_dept : bool
        ``True`` → exclude department yang dipilih; ``False`` → include.

    Returns
    -------
    str
        Kondisi SQL siap pakai, misal ``"poi.department_code IN ('TA','TB')"``
        atau ``'1=1'`` jika tidak ada filter.
    """
    if selected_department and 'All' not in selected_department:
        dept_list = "','".join(selected_department)
        if exclude_dept:
            return f"({col} NOT IN ('{dept_list}') OR {col} IS NULL)"
        else:
            return f"{col} IN ('{dept_list}')"
    return "1=1"

def build_pg_cond(col: str, selected_p_group, exclude_purchasing_group) -> str:
    """Bangun kondisi SQL filter Purchasing Group untuk kolom tertentu.

    Dipakai pada query yang tidak JOIN ke vw_pr_po_complete, misalnya query
    langsung ke purchase_orders (kolom ``'poh.purchasing_group'``).

    Parameters
    ----------
    col : str
        Nama kolom purchasing_group beserta alias tabel, misal
        ``'poh.purchasing_group'`` atau ``'poi.purchasing_group'``.
    selected_p_group : list
        Daftar purchasing group yang dipilih. ``['All']`` berarti tidak ada filter.
    exclude_purchasing_group : bool
        ``True`` → exclude group yang dipilih; ``False`` → include.

    Returns
    -------
    str
        Kondisi SQL siap pakai atau ``'1=1'`` jika tidak ada filter.
    """
    if selected_p_group and 'All' not in selected_p_group:
        pg_list = "','".join(selected_p_group)
        if exclude_purchasing_group:
            return f"({col} NOT IN ('{pg_list}') OR {col} IS NULL)"
        else:
            return f"{col} IN ('{pg_list}')"
    return "1=1"

# =============================================================================
# SIPS WHERE CLAUSE BUILDER
# =============================================================================

def build_sips_bagian_cond(selected_bagian, date_to=None) -> str:
    """
    Bangun kondisi filter bagian untuk query vw_sips menggunakan logika
    "bagian karyawan ditentukan berdasarkan date_to filter, bukan tanggal transaksi".

    LOGIKA MUTASI:
    Ketika date_to >= berlaku_dari mutasi baru seorang karyawan, maka SELURUH
    transaksi karyawan tersebut dianggap milik bagian baru (tidak peduli kapan
    transaksi itu dibuat). Ini berarti filter bagian tidak menggunakan kolom
    `bagian` di vw_sips (yang berbasis tanggal transaksi), melainkan mengecek
    bagian aktif karyawan pada tanggal date_to via karyawan_bagian_history.

    Aturan penentuan bagian karyawan pada tanggal D (date_to):
      - Ambil baris di karyawan_bagian_history dengan berlaku_dari <= D
        DAN (berlaku_sampai IS NULL OR berlaku_sampai >= D)
      - Jika date_to tidak diberikan (None), pakai bagian saat ini
        (berlaku_sampai IS NULL = masih aktif)

    Parameters
    ----------
    selected_bagian : list
        Daftar bagian yang dipilih user. ['All'] = tanpa filter.
    date_to : date | str | None
        Batas akhir tanggal filter. Digunakan sebagai "tanggal acuan"
        untuk menentukan bagian aktif karyawan.

    Returns
    -------
    str
        Kondisi SQL siap pakai, atau '1=1' jika tidak ada filter bagian.
    """
    if not selected_bagian or "All" in selected_bagian:
        return "1=1"

    bg = ", ".join(f"'{b}'" for b in selected_bagian)

    if date_to:
        # Bagian karyawan = bagian yang berlaku pada date_to
        # (berlaku_dari <= date_to AND (berlaku_sampai IS NULL OR berlaku_sampai >= date_to))
        return f"""nik IN (
            SELECT nik FROM karyawan_bagian_history
            WHERE bagian IN ({bg})
              AND berlaku_dari <= '{date_to}'::date
              AND (berlaku_sampai IS NULL OR berlaku_sampai >= '{date_to}'::date)
        )"""
    else:
        # Tanpa date_to: gunakan bagian aktif saat ini (berlaku_sampai IS NULL)
        return f"""nik IN (
            SELECT nik FROM karyawan_bagian_history
            WHERE bagian IN ({bg})
              AND berlaku_sampai IS NULL
        )"""


def build_sips_where(date_from=None, date_to=None,
                     selected_nama=None, selected_bagian=None,
                     selected_pgroup=None,
                     extra: list = None) -> str:
    """
    Bangun WHERE clause untuk query vw_sips.
    - Filter tanggal menggunakan tgl_disposisi_buyer (konsisten dengan ETL &
      kolom BULAN DISPO di Excel), bukan requisition_date.
      Alasan: ETL menentukan bulan_import dari tgl_disposisi_buyer sebagai
      anchor utama, sehingga filter dashboard harus mengikuti kolom yang sama
      agar Total PR / Total PO sesuai dengan rekapan Excel atasan.
    - Filter bagian menggunakan build_sips_bagian_cond() dengan acuan date_to,
      sehingga karyawan yang mutasi bagian akan "membawa" seluruh transaksinya
      ke bagian baru begitu date_to melewati tanggal efektif mutasi.
    - Filter purchasing_group hanya aktif jika selected_pgroup bukan ['All']
    - Sertakan extra=['nilai_sla IS NOT NULL'] dsb. jika perlu kondisi tambahan
    """
    wp = ["1=1"]
    if extra:
        wp.extend(extra)
    if date_from:
        wp.append(f"tgl_disposisi_buyer >= '{date_from}'")
    if date_to:
        wp.append(f"tgl_disposisi_buyer <= '{date_to}'")

    # Filter bagian berbasis date_to (bukan kolom bagian statis di vw_sips)
    bagian_cond = build_sips_bagian_cond(selected_bagian, date_to=date_to)
    if bagian_cond != "1=1":
        wp.append(bagian_cond)

    if selected_pgroup and "All" not in selected_pgroup:
        pg = ", ".join(f"'{p}'" for p in selected_pgroup)
        wp.append(f"purchasing_group IN ({pg})")
    if selected_nama and "All" not in selected_nama:
        nms = ", ".join(f"'{n}'" for n in selected_nama)
        wp.append(f"nama IN ({nms})")
    return " AND ".join(wp)

# =============================================================================
# FILTER BAR: horizontal filter di atas konten halaman
# =============================================================================

def render_filter_bar(mode: str, load_data_fn) -> dict:
    """
    Render filter bar horizontal di atas konten halaman.

    mode : 'sap'  → filter SAP  (Bagian, Dept, P.Group, Date Range)
           'sips' → filter SIPS (Bagian, Nama, Date Range)

    Mengembalikan dict berisi nilai filter aktif.
    """
    current_year  = datetime.now().year
    default_start = datetime(current_year, 1, 1).date()

    # Tanggal terakhir data diambil, update sesuai ETL terbaru
    from datetime import date as _date
    DATA_UPDATE_SAP  = _date(2026, 2, 28)
    DATA_UPDATE_SIPS = _date(2026, 2, 28)

    def _init(k, v):
        if k not in st.session_state:
            st.session_state[k] = v

    def _all_logic(key):
        cur = st.session_state[key]
        if not cur:
            st.session_state[key] = ['All']
        elif 'All' in cur and len(cur) > 1:
            st.session_state[key] = [x for x in cur if x != 'All']

    def _label(text, tooltip=None):
        title_attr = f" title='{tooltip}'" if tooltip else ""
        cursor_style = " cursor:help;" if tooltip else ""
        icon = " <span style='font-size:10px; opacity:0.7;'>ⓘ</span>" if tooltip else ""
        
        st.markdown(
            f"<p{title_attr} style='font-size:12px;font-weight:600;margin:0 0 2px 0;opacity:0.8;{cursor_style}'>{text}{icon}</p>",
            unsafe_allow_html=True
        )

    def _spacer():
        st.markdown(
            "<p style='font-size:12px;margin:0 0 2px 0;opacity:0'>&nbsp;</p>",
            unsafe_allow_html=True
        )

    if mode == 'sap':
        # == Load options =======================================================
        try:
            dept_df = load_data_fn(
                "SELECT DISTINCT department_code FROM departments ORDER BY department_code"
            )
            bagian_df = load_data_fn("""
                SELECT DISTINCT bagian_pr AS bagian FROM vw_pr_po_complete
                 WHERE bagian_pr IS NOT NULL AND bagian_pr != 'UNKNOWN'
                UNION
                SELECT DISTINCT bagian_po AS bagian FROM vw_pr_po_complete
                 WHERE bagian_po IS NOT NULL AND bagian_po != 'UNKNOWN'
                ORDER BY 1
            """)
            pg_df = load_data_fn("""
                SELECT DISTINCT purchasing_group FROM purchase_requisitions
                 WHERE purchasing_group IS NOT NULL
                UNION
                SELECT DISTINCT purchasing_group FROM purchase_orders
                 WHERE purchasing_group IS NOT NULL
                ORDER BY 1
            """)
            opts_dept   = ['All'] + dept_df['department_code'].tolist()
            opts_bagian = ['All'] + bagian_df['bagian'].tolist()
            opts_pg     = ['All'] + pg_df['purchasing_group'].tolist()
        except Exception:
            opts_dept = opts_bagian = opts_pg = ['All']

        # Init session state TANPA value= di widget (cegah warning duplikat)
        _init('fb_bagian',    ['All'])
        _init('fb_dept',      ['All'])
        _init('fb_pgroup',    ['All'])
        _init('fb_date_from',  default_start)
        _init('fb_date_to',    DATA_UPDATE_SAP)

        c_bag, c_dept, c_pg, c_from, c_to, c_btn = st.columns([2, 2, 2, 1.5, 1.5, 0.8])

        with c_bag:
            _label("Bagian")
            st.multiselect("Bagian", options=opts_bagian, key="fb_bagian",
                           on_change=_all_logic, args=("fb_bagian",),
                           label_visibility="collapsed")
        with c_dept:
            _label("Department")
            st.multiselect("Department", options=opts_dept, key="fb_dept",
                           on_change=_all_logic, args=("fb_dept",),
                           label_visibility="collapsed")
        with c_pg:
            _label("Purchasing Group")
            st.multiselect("P.Group", options=opts_pg, key="fb_pgroup",
                           on_change=_all_logic, args=("fb_pgroup",),
                           label_visibility="collapsed")
        with c_from:
            _label("Dari", tooltip="PR SAP: 1st Full Release&#10;PO SAP: Date Ordered")
            st.date_input("Dari", key="fb_date_from", label_visibility="collapsed")
        with c_to:
            _label("Sampai", tooltip="PR SAP: 1st Full Release&#10;PO SAP: Date Ordered")
            st.date_input("Sampai", key="fb_date_to", label_visibility="collapsed")
        with c_btn:
            _spacer()
            if st.button("", icon=":material/refresh:", help="Refresh Data",
                         use_container_width=True, key="fb_refresh_sap"):
                st.cache_data.clear()
                st.rerun()

        # == Info data update + divider =========================================
        st.markdown(
            f"<p style='font-size:11px; opacity:0.5; margin:6px 0 0 2px;'>"
            f"Data SAP per <b>{DATA_UPDATE_SAP.strftime('%d %B %Y')}</b> &nbsp;·&nbsp; "
            f"Data SIPS per <b>{DATA_UPDATE_SIPS.strftime('%d %B %Y')}</b>"
            f"</p>",
            unsafe_allow_html=True
        )
        st.markdown("---")

        return dict(
            date_from           = st.session_state.fb_date_from,
            date_to             = st.session_state.fb_date_to,
            selected_bagian     = st.session_state.fb_bagian,
            selected_department = st.session_state.fb_dept,
            selected_p_group    = st.session_state.fb_pgroup,
            exclude_bagian      = False,
        )

    else:  # mode == 'sips'
        try:
            bagian_df = load_data_fn(
                "SELECT DISTINCT bagian FROM sips_employees WHERE bagian IS NOT NULL ORDER BY bagian"
            )
            opts_bagian_sips = ['All'] + bagian_df['bagian'].tolist()
        except Exception:
            opts_bagian_sips = ['All']

        # Init session state TANPA value= di widget (cegah warning duplikat)
        _init('fb_sips_bagian',    ['All'])
        _init('fb_sips_pgroup',    ['All'])
        _init('fb_sips_nama',      ['All'])
        _init('fb_sips_date_from',  default_start)
        _init('fb_sips_date_to',    DATA_UPDATE_SIPS)

        def _bagian_sips_changed():
            _all_logic("fb_sips_bagian")
            st.session_state.fb_sips_nama = ['All']

        # Load nama berdasarkan bagian dipilih
        try:
            sel_bag = st.session_state.fb_sips_bagian
            if 'All' not in sel_bag and sel_bag:
                bsql = "', '".join(sel_bag)
                nama_df = load_data_fn(
                    f"SELECT DISTINCT nama FROM sips_employees WHERE bagian IN ('{bsql}') ORDER BY nama"
                )
            else:
                nama_df = load_data_fn(
                    "SELECT DISTINCT nama FROM sips_employees ORDER BY nama"
                )
            opts_nama = ['All'] + nama_df['nama'].tolist()
        except Exception:
            opts_nama = ['All']

        # Load purchasing group SIPS
        try:
            pg_sips_df = load_data_fn(
                "SELECT DISTINCT purchasing_group FROM sips_data WHERE purchasing_group IS NOT NULL ORDER BY purchasing_group"
            )
            opts_pgroup_sips = ['All'] + pg_sips_df['purchasing_group'].tolist()
        except Exception:
            opts_pgroup_sips = ['All']

        c_pg, c_bag, c_nama, c_from, c_to, c_btn = st.columns([1.5, 1.5, 2, 1.3, 1.3, 0.8])

        with c_pg:
            _label("P. Group")
            st.multiselect("P. Group", options=opts_pgroup_sips, key="fb_sips_pgroup",
                           on_change=_all_logic, args=("fb_sips_pgroup",),
                           label_visibility="collapsed")
        with c_bag:
            _label("Bagian")
            st.multiselect("Bagian", options=opts_bagian_sips, key="fb_sips_bagian",
                           on_change=_bagian_sips_changed, label_visibility="collapsed")
        with c_nama:
            _label("Nama")
            st.multiselect("Nama", options=opts_nama, key="fb_sips_nama",
                           on_change=_all_logic, args=("fb_sips_nama",),
                           label_visibility="collapsed")
        with c_from:
            _label("Dari", tooltip="Data SIPS: Tanggal Disposisi Buyer")
            st.date_input("Dari", key="fb_sips_date_from", label_visibility="collapsed")
        with c_to:
            _label("Sampai", tooltip="Data SIPS: Tanggal Disposisi Buyer")
            st.date_input("Sampai", key="fb_sips_date_to", label_visibility="collapsed")
        with c_btn:
            _spacer()
            if st.button("", icon=":material/refresh:", help="Refresh Data",
                         use_container_width=True, key="fb_refresh_sips"):
                st.cache_data.clear()
                st.rerun()

        # == Info data update + divider =========================================
        st.markdown(
            f"<p style='font-size:11px; opacity:0.5; margin:6px 0 0 2px;'>"
            f"Data SAP per <b>{DATA_UPDATE_SAP.strftime('%d %B %Y')}</b> &nbsp;·&nbsp; "
            f"Data SIPS per <b>{DATA_UPDATE_SIPS.strftime('%d %B %Y')}</b>"
            f"</p>",
            unsafe_allow_html=True
        )
        st.markdown("---")

        return dict(
            date_from       = st.session_state.fb_sips_date_from,
            date_to         = st.session_state.fb_sips_date_to,
            selected_bagian = st.session_state.fb_sips_bagian,
            selected_pgroup = st.session_state.fb_sips_pgroup,
            selected_nama   = st.session_state.fb_sips_nama,
        )

# =============================================================================
# SCROLL TO TOP BUTTON
# =============================================================================

def inject_scroll_to_top():
    """
    Tombol scroll-to-top selalu visible di pojok kanan bawah.
    - st.markdown  : render tombol + CSS (tidak butuh iframe)
    - st.components: inject event listener via window.parent (butuh iframe
                     tapi hanya untuk JS, bukan untuk menampilkan elemen)
    """
    # Tombol + CSS via st.markdown (selalu render, tidak butuh iframe)
    st.markdown("""
<style>
#stt-btn {
    position: fixed;
    bottom: 56px;
    right: 18px;
    z-index: 99999;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: #ff4b4b;
    color: white;
    border: none;
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background .2s ease, transform .2s ease, box-shadow .2s ease;
}
#stt-btn:hover {
    background: #e03c3c;
    transform: translateY(-3px);
    box-shadow: 0 8px 20px rgba(0,0,0,0.35);
}
#stt-btn:active { transform: translateY(0); }
</style>
<button id="stt-btn" title="Scroll ke atas">
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18"
         fill="currentColor" viewBox="0 0 16 16">
        <path fill-rule="evenodd"
              d="M7.646 4.646a.5.5 0 0 1 .708 0l6 6a.5.5 0 0
                 1-.708.708L8 5.707l-5.646 5.647a.5.5 0 0
                 1-.708-.708z"/>
    </svg>
</button>
""", unsafe_allow_html=True)

    # Event listener via iframe, mengakses window.parent.document
    # untuk scroll section[data-testid="stMain"] yang terbukti dari debug
    st.components.v1.html("""
<script>
(function() {
    function attachListener() {
        var doc = window.parent.document;
        var btn = doc.getElementById('stt-btn');
        if (!btn) { setTimeout(attachListener, 200); return; }

        // Hindari duplikat listener
        if (btn.dataset.sttAttached) return;
        btn.dataset.sttAttached = '1';

        btn.addEventListener('click', function() {
            var el = doc.querySelector('section[data-testid="stMain"]');
            if (el) el.scrollTop = 0;
        });
    }
    setTimeout(attachListener, 300);
})();
</script>
""", height=0)

# =============================================================================
# PETA SISTEM: LAZY LOAD: hanya dimuat saat user bertanya soal struktur
# =============================================================================

# Kata kunci yang mengindikasikan pertanyaan tentang struktur/letak di dashboard
_TRIGGER_PETA = [
    # Navigasi & letak
    "halaman", "page", "menu", "navigasi", "dimana", "di mana", "letak",
    "ada di", "temukan di", "lihat di", "pergi ke", "buka halaman",
    # Elemen visual
    "chart", "grafik", "tabel", "table", "diagram", "visualisasi",
    "kpi", "kartu", "card", "metrik",
    # Pertanyaan struktur
    "ada apa", "apa saja", "fitur apa", "struktur", "isi halaman",
    "menampilkan apa", "berisi apa", "bagian mana", "section",
    # Kata tanya umum yang mungkin tentang navigasi
    "di sini ada", "bisa lihat", "cara lihat", "cara melihat",
]

def _butuh_peta_sistem(user_input: str) -> bool:
    """Cek apakah pertanyaan user memerlukan informasi Peta Sistem."""
    teks = user_input.lower()
    return any(k in teks for k in _TRIGGER_PETA)

def _fetch_peta_sistem(load_data_fn) -> str:
    """
    Ambil Peta Sistem dari database (lazy, hanya dipanggil saat dibutuhkan).
    Hasil di-cache di st.session_state selama sesi berlangsung.
    """
    # Cache di session_state agar tidak query DB berulang dalam satu sesi
    if "melati_peta_cache" in st.session_state:
        return st.session_state["melati_peta_cache"]

    try:
        df = load_data_fn("""
            SELECT urutan, nama_halaman, konten
            FROM melati_peta_sistem
            ORDER BY urutan
        """)

        if df.empty:
            return ""

        lines = [
            "INFORMASI STRUKTUR HALAMAN APLIKASI (PETA SISTEM):",
            "Kamu mengetahui seluruh daftar halaman dan chart di sistem ini beserta deskripsi singkatnya.",
            "",
        ]

        for _, row in df.iterrows():
            lines.append(f"{row['urutan']}. {row['nama_halaman']}")
            # Indent setiap baris konten
            for baris in str(row['konten']).strip().splitlines():
                lines.append(f"    {baris.strip()}")
            lines.append("")

        result = "\n".join(lines)
        st.session_state["melati_peta_cache"] = result
        return result

    except Exception as e:
        # Tabel belum ada atau error, kembalikan string kosong, tidak crash
        return ""

# =============================================================================
# KOMPONEN AI ANALYST (GEMINI)
# =============================================================================

def render_chat_analyst(konteks_data_teks: str, nama_halaman: str, load_data_fn=None):
    """Merender antarmuka chat LLM secara sebaris (inline) dengan kotak scrollable."""

    img_path = "assets/Melati_icon.png"
    img_b64 = ""

    if os.path.exists(img_path):
        with open(img_path, "rb") as img_file:
            img_b64 = base64.b64encode(img_file.read()).decode()

    if img_b64:
        # Jika gambar ditemukan, jadikan icon bulat (border-radius: 50%)
        icon_html = f'<img src="data:image/png;base64,{img_b64}" width="38" height="38" style="margin-right: 12px; border-radius: 50%; object-fit: cover; border: 2px solid #1f77b4;">'
    else:
        # Fallback (cadangan) jika gambar tidak ditemukan, gunakan emoji
        icon_html = '<span style="font-size: 32px; margin-right: 12px;">🕵️‍♀️</span>'
    
    # Header AI
    st.markdown(f"""
        <h1 style='display: flex; align-items: center; font-size:28px; color: #1f77b4; margin-bottom: 5px;'>
            {icon_html}
            Tanya ke Melati (Monitoring, Evaluasi, Laporan Terintegrasi)
        </h1>
    """, unsafe_allow_html=True)
    st.caption(f"Tanyakan *insight* atau kesimpulan dari data di sistem Monitoring & Reporting Pengadaan Barang.")

    # 1. Inisialisasi API
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        client = genai.Client(api_key=api_key)
    except Exception:
        st.error("API Key belum dikonfigurasi di file secrets.toml")
        return

    # 2. Setup Memori Sesi
    if "chat_memory" not in st.session_state:
        st.session_state.chat_memory = []

    # 3. KOTAK PERCAKAPAN SCROLLABLE (Tinggi Tetap 400px)
    chat_box = st.container(height=400)
    
    # Render histori yang sudah ada ke dalam kotak tersebut
    with chat_box:
        if not st.session_state.chat_memory:
            st.info("Ketik pertanyaan Anda di bawah untuk memulai analisis data.")
            
        for msg in st.session_state.chat_memory:
            if msg["role"] == "assistant":
                avatar_img = "assets/Melati_icon.png"
            else:
                avatar_img = None

            with st.chat_message(msg["role"], avatar=avatar_img):
                st.markdown(msg["content"])

    # 4. KOTAK INPUT (Inline, diam di tempat)
    # Menggunakan form agar teks otomatis terhapus (clear) setelah dikirim
    with st.form(key=f"chat_form_{nama_halaman}", clear_on_submit=True):
        col_input, col_btn = st.columns([9, 1]) # Proporsi 90% input, 10% tombol
        
        with col_input:
            user_input = st.text_input(
                "Prompt AI", 
                placeholder="Contoh: Vendor mana yang nilai PO-nya paling besar?", 
                label_visibility="collapsed" # Menyembunyikan label agar bersih
            )
        with col_btn:
            submit_btn = st.form_submit_button("Kirim", icon=":material/send:")

    # 5. LOGIKA EKSEKUSI API
    if submit_btn and user_input:
        
        # Simpan pertanyaan user ke memori
        st.session_state.chat_memory.append({"role": "user", "content": user_input})
        
        # Tampilkan langsung ke dalam kotak percakapan yang di-scroll tadi
        with chat_box:
            with st.chat_message("user"):
                st.markdown(user_input)
                
            # Render animasi loading & balasan AI
            with st.chat_message("assistant", avatar="assets/Melati_icon.png"):
                with st.spinner("Tunggu, Melati sedang menganalisis data..."):
                    try:
                        # -------------------------------------------------------------
                        # PETA SISTEM: lazy load, hanya jika pertanyaan menyinggung
                        # struktur / letak chart / navigasi dashboard
                        # -------------------------------------------------------------
                        if _butuh_peta_sistem(user_input) and load_data_fn is not None:
                            peta_context = _fetch_peta_sistem(load_data_fn)
                        else:
                            peta_context = ""

                        # Rakit Prompt Rahasia
                        system_prompt = f"""
                        Kamu adalah asisten AI bernama Melati, seorang analis data perempuan yang ceria, sangat teliti, dan bersikap layaknya "detektif" andal yang sedang menyelidiki data sistem perusahaan.
                        
                        Tugas dan Aturan Ketat Melati:
                        1. IDENTITAS & GAYA BAHASA: Namamu adalah Melati, detektif data pengadaan. HANYA perkenalkan dirimu secara penuh jika user SECARA EKSPLISIT bertanya "siapa kamu", "kamu siapa", "perkenalkan dirimu", atau sejenisnya. Jika user hanya menyapa ("halo", "hai", dll.) atau langsung mengajukan pertanyaan data, JANGAN memperkenalkan diri, langsung jawab pertanyaannya saja dengan gaya yang ceria dan to the point. Gunakan gaya bahasa yang ceria, ramah, sedikit playful (gunakan kata "aku" dan "kamu"), tapi tetap SANGAT OBJEKTIF dan tajam saat menganalisis angka.
                        2. FAKTUAL & OBJEKTIF: Jawab HANYA berdasarkan data di bawah. JIKA DATA TIDAK ADA, katakan dengan nada detektif: "Hmm, sepertinya jejak data itu tidak kutemukan di layar saat ini 🔍."
                        3. NO HALLUCINATION: Sebagai detektif, kamu pantang mengarang bukti! JANGAN PERNAH mengarang angka, nama vendor, atau metrik yang tidak ada di data.
                        4. ATURAN PENOLAKAN RUMUS/KALKULASI: Kamu HANYA tahu deskripsi singkat chart. JIKA user bertanya tentang RUMUS, FORMULA, CARA MENGHITUNG, atau KALKULASI spesifik dari suatu chart, kamu WAJIB menjawab dengan template kalimat ini (sesuaikan nama halaman dan chart-nya):
                           "Maaf, Melati masih belum bisa memperoleh informasi tersebut. Kamu bisa mengetahui informasinya dengan cara pergi ke Halaman [Judul Halaman], di chart/tabel [Nama Chart/Nama Tabel], lalu klik tombol 'Show Formula' berbentuk mata 😭."
                        5. BATASAN DOMAIN: Tolak dengan sopan hal di luar pengadaan, dashboard, atau data yang diberikan.
                        6. FORMAT: Berikan analisis terstruktur, tebalkan angka penting, gunakan bullet points, dan sedikit emoji.
                        7. ATURAN FILTER LINTAS SISTEM (PENTING!): Pada 'BUKTI DATA' di bawah, tertera informasi 'Halaman aktif' saat ini. JIKA user bertanya tentang data/angka dari sistem yang BERBEDA dengan halaman aktif saat ini (misalnya: kita sedang di halaman SIPS, tapi user menanyakan data SAP, atau sebaliknya), kamu WAJIB menyebutkan "Kondisi Filter" yang sedang berlaku pada data tersebut sebelum memberikan jawabannya. Ambil informasi filter ini dari teks di bawah tulisan [SAP] FILTER AKTIF atau [SIPS] FILTER AKTIF.
                        
                        {peta_context}

                        Berikut adalah BUKTI-BUKTI DATA yang sedang tayang di layar saat ini:
                        --- MULAI BUKTI DATA ---
                        {konteks_data_teks}
                        --- AKHIR BUKTI DATA ---
                        
                        Pertanyaan dari User: {user_input}
                        """
                        
                        # Eksekusi API Gemini
                        response = client.models.generate_content(
                            model="gemini-3-flash-preview",
                            contents=system_prompt
                        )
                        
                        # Tampilkan hasil
                        st.markdown(response.text)
                        
                        # Simpan ke memori agar tidak hilang saat filter diubah
                        st.session_state.chat_memory.append({"role": "assistant", "content": response.text})
                    
                    except Exception as e:
                        st.error(f"Terjadi kesalahan saat menghubungi API: {e}")