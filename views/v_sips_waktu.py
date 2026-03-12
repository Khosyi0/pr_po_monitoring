"""
v_sips_waktu.py - Analisis Waktu Proses SIPS

Timeline nyata dari data Excel:
  [Requisition Date (I)] --<Waktu Pra-Disposisi>--> [Tgl Disposisi Buyer (K)] --<PR-PO (N)>--> [Tanggal PO (L)]
                                                                                 <Realisasi SLA (T, hari kerja)>

Kolom waktu:
  PR-PO         = Disposisi Buyer -> Tgl PO, hari KERJA
  Standard SLA  = target: Agreement 12H / Urgent 24H / TA-Investasi 48H / Normal 57H
  Realisasi SLA = Disposisi -> PO hari KERJA (rata-rata 8H lebih pendek dari N)
  Nilai SLA     = 1 ontime - 0 miss - '-' belum PO (exclude dari analisis)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import format_number, render_chat_analyst, build_sips_where


def toggle_state(state_key):
    st.session_state[state_key] = not st.session_state[state_key]


LAYOUT = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
              font_color="gray", margin=dict(t=16, b=16, l=10, r=10), separators=",.")
GRID   = dict(gridcolor="rgba(128,128,128,0.15)")

KPI_CSS = """
<style>
.wt-card{display:flex;align-items:center;background:var(--secondary-background-color);
  border-radius:10px;padding:16px 14px;gap:14px;height:100%;}
.wt-icon{display:flex;align-items:center;justify-content:center;flex-shrink:0;}
.wt-body{flex:1;min-width:0;}
.wt-lbl{font-size:12.5px;opacity:.65;margin:0 0 4px 0;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.wt-val{font-size:2rem!important;font-weight:600!important;margin:0!important;
  padding:0!important;line-height:1.1!important;display:block!important;}
.dt-n{font-size:12px;opacity:.55;margin:0;}
.dt-g{font-size:12px;color:#09ab3b;margin:0;}
.dt-o{font-size:12px;color:#f0a500;margin:0;}
.dt-r{font-size:12px;color:#e03c3c;margin:0;}
</style>"""

ICONS = {
    "clock":  "M8 3.5a.5.5 0 0 0-1 0V9a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0 0 .496-.868L8 8.71zM8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16m7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0",
    "check":  "M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16M10.97 4.97a.235.235 0 0 0-.02.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-1.071-1.05",
    "warn":   "M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5m.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2",
    "target": "M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16M8 13A5 5 0 1 1 8 3a5 5 0 0 1 0 10m0 1A6 6 0 1 0 8 2a6 6 0 0 0 0 12m0-9a3 3 0 1 1 0 6 3 3 0 0 1 0-6m0 1a2 2 0 1 0 0 4 2 2 0 0 0 0-4",
    "split":  "M1 2.5A1.5 1.5 0 0 1 2.5 1h3A1.5 1.5 0 0 1 7 2.5v3A1.5 1.5 0 0 1 5.5 7h-3A1.5 1.5 0 0 1 1 5.5zm8 0A1.5 1.5 0 0 1 10.5 1h3A1.5 1.5 0 0 1 15 2.5v3A1.5 1.5 0 0 1 13.5 7h-3A1.5 1.5 0 0 1 9 5.5zm-8 8A1.5 1.5 0 0 1 2.5 9h3A1.5 1.5 0 0 1 7 10.5v3A1.5 1.5 0 0 1 5.5 15h-3A1.5 1.5 0 0 1 1 13.5zm8 0A1.5 1.5 0 0 1 10.5 9h3a1.5 1.5 0 0 1 1.5 1.5v3a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 9 13.5z",
    "route":  "M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0M4.5 7.5a.5.5 0 0 0 0 1h5.793l-2.147 2.146a.5.5 0 0 0 .708.708l3-3a.5.5 0 0 0 0-.708l-3-3a.5.5 0 0 0-.708.708L10.293 7.5z",
}

def svg(name, size=42):
    p = ICONS.get(name, ICONS["clock"])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'fill="currentColor" viewBox="0 0 16 16"><path d="{p}"/></svg>')

def kpi_card(icon, label, value, delta="", dc="n"):
    cls = {"n":"dt-n","g":"dt-g","o":"dt-o","r":"dt-r"}.get(dc,"dt-n")
    d = f'<p class="{cls}">{delta}</p>' if delta else ""
    return (f'<div class="wt-card"><div class="wt-icon">{svg(icon)}</div>'
            f'<div class="wt-body"><p class="wt-lbl">{label}</p>'
            f'<p class="wt-val">{value}</p>{d}</div></div>')


def render(load_data, date_from, date_to, selected_nama, selected_bagian=None, **kwargs):
    st.markdown(KPI_CSS, unsafe_allow_html=True)

    info_filter = kwargs.get('info_filter', 'Tidak ada filter spesifik')

    st.markdown("""
    <h1 style='display:flex;align-items:center;font-size:60px;'>
      <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" fill="currentColor"
           viewBox="0 0 16 16" style="margin-bottom:10px;margin-right:8px;">
        <path d="M3.5 0a.5.5 0 0 1 .5.5V1h8V.5a.5.5 0 0 1 1 0V1h1a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2h1V.5a.5.5 0 0 1 .5-.5M2 2a1 1 0 0 0-1 1v1h14V3a1 1 0 0 0-1-1zm13 3H1v9a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1z"/>
        <path d="M11 7.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm-3 0a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm-2 3a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm-3 0a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5z"/>
      </svg>
      Analisis Waktu Proses SIPS
    </h1>""", unsafe_allow_html=True)
    st.markdown("---")

    # ── WHERE clause ─────────────────────────────────────────────────────────
    where = build_sips_where(
        date_from=date_from, date_to=date_to,
        selected_nama=selected_nama, selected_bagian=selected_bagian,
        extra=["nilai_sla IS NOT NULL", "status IN ('Closed','Proses PO')"]
    )

    kpi_q = f"""
    SELECT
        ROUND(AVG(pr_po_days)::numeric,2)                               AS avg_pr_po,
        ROUND(AVG(realisasi_sla)::numeric,2)                           AS avg_real,
        ROUND(AVG(standar_sla)::numeric,2)                             AS avg_std,
        ROUND(AVG(tgl_disposisi_buyer - requisition_date)::numeric,2)  AS avg_pra,
        ROUND(AVG(tgl_po - requisition_date)::numeric,2)               AS avg_e2e,
        ROUND(AVG(standar_sla - realisasi_sla)::numeric,2)            AS avg_headroom,
        ROUND(SUM(CASE WHEN nilai_sla=1 THEN 1.0 END)/NULLIF(COUNT(*),0)*100,2) AS pct_ontime,
        COUNT(CASE WHEN nilai_sla=0 THEN 1 END)                        AS cnt_miss
    FROM vw_sips WHERE {where}
    """

    chart_q = f"""
    SELECT
        nama, standar_sla, pr_po_days, realisasi_sla, nilai_sla,
        kontrak_status, prioritas, purchasing_group,
        TO_CHAR(DATE_TRUNC('month',requisition_date),'YYYY-MM')         AS bulan,
        (tgl_disposisi_buyer - requisition_date)                        AS waktu_pra,
        (tgl_po - requisition_date)                                     AS e2e,
        (standar_sla - realisasi_sla)                                   AS headroom
    FROM vw_sips WHERE {where}
    """

    with st.spinner("Memuat data..."):
        try:
            dk = load_data(kpi_q)
            df = load_data(chart_q)
            if not df.empty:
                for col in ["pr_po_days", "realisasi_sla", "waktu_pra", "e2e", "headroom"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
        except Exception as e:
            st.error(f"Gagal memuat data: {e}")
            return

    no_data = dk.empty or df.empty

    avg_pr_po    = 0.0
    avg_real     = 0.0
    avg_std      = 0.0
    avg_pra      = 0.0
    avg_e2e      = 0.0
    avg_headroom = 0.0
    pct_ontime   = 0.0
    cnt_miss     = 0

    if not dk.empty and not dk.iloc[0].isnull().all():
        r = dk.iloc[0]
        avg_pr_po    = float(r['avg_pr_po'] or 0.0)
        avg_real     = float(r['avg_real'] or 0.0)
        avg_std      = float(r['avg_std'] or 0.0)
        avg_pra      = float(r['avg_pra'] or 0.0)
        avg_e2e      = float(r['avg_e2e'] or 0.0)
        avg_headroom = float(r['avg_headroom'] or 0.0)
        pct_ontime   = float(r['pct_ontime'] or 0.0)
        cnt_miss     = int(r['cnt_miss'] or 0)
    
    # BAGIAN 1: KPI Ringkasan
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:24px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0M8 3.5a.5.5 0 0 0-1 0V9a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0 0 .496-.868L8 8.71z"/>
            </svg>
            Ringkasan Waktu
        </h1>
    """, unsafe_allow_html=True)

    # ── Baris 1: Rata-rata PR-PO | Rata-rata Realisasi SLA | Waktu Pra-Disposisi ──
    col1, col2, col3 = st.columns(3)

    with col1:
        c_card, c_btn = st.columns([10, 2])
        with c_card:
            st.markdown(kpi_card("clock", "Rata-rata PR-PO",
                                 f"{format_number(avg_pr_po, decimals=2)} hari",
                                 "Proses Po dan Closed", "n"),
                        unsafe_allow_html=True)
        with c_btn:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            key_kpi_pr_po = "show_formula_kpi_pr_po"
            if key_kpi_pr_po not in st.session_state:
                st.session_state[key_kpi_pr_po] = False
            is_open = st.session_state[key_kpi_pr_po]
            icon    = ":material/visibility_off:" if is_open else ":material/visibility:"
            tooltip = "Hide Formula" if is_open else "Show Formula"
            st.button(icon, key=f"btn_{key_kpi_pr_po}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_kpi_pr_po})

    with col2:
        dc = "g" if avg_real <= avg_std else "r"
        c_card, c_btn = st.columns([10, 2])
        with c_card:
            st.markdown(kpi_card("check", "Rata-rata Realisasi SLA",
                                 f"{format_number(avg_real, decimals=2)} hari",
                                 f"Disposisi ke PO hari kerja | Standar rata-rata {format_number(avg_std)}H", dc),
                        unsafe_allow_html=True)
        with c_btn:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            key_kpi_real = "show_formula_kpi_real"
            if key_kpi_real not in st.session_state:
                st.session_state[key_kpi_real] = False
            is_open = st.session_state[key_kpi_real]
            icon    = ":material/visibility_off:" if is_open else ":material/visibility:"
            tooltip = "Hide Formula" if is_open else "Show Formula"
            st.button(icon, key=f"btn_{key_kpi_real}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_kpi_real})

    with col3:
        c_card, c_btn = st.columns([10, 2])
        with c_card:
            st.markdown(kpi_card("split", "Waktu Pra-Disposisi",
                                 f"{format_number(avg_pra, decimals=2)} hari",
                                 "Req Date ke Disposisi (routing / approval)", "n"),
                        unsafe_allow_html=True)
        with c_btn:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            key_kpi_pra = "show_formula_kpi_pra"
            if key_kpi_pra not in st.session_state:
                st.session_state[key_kpi_pra] = False
            is_open = st.session_state[key_kpi_pra]
            icon    = ":material/visibility_off:" if is_open else ":material/visibility:"
            tooltip = "Hide Formula" if is_open else "Show Formula"
            st.button(icon, key=f"btn_{key_kpi_pra}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_kpi_pra})

    # Formula info baris 1 - tampil di bawah baris, lebar penuh
    if st.session_state.get(key_kpi_pr_po, False):
        st.info(f"""\
    **Rata-rata Proses Po dan Closed dari PR-PO**: Rata-rata jumlah hari PR-PO dengan **Status** `Proses PO` dan `Closed` dari **Tanggal Disposisi Buyer** hingga **Tanggal PO** per karyawan.

    **Formula Excel:**
    - Filter nama karyawan yang ingin dicari
    - Filter **Status** menjadi `Proses PO` dan `Closed`
    - Hitung rata-rata **PR-PO**

    **Nilai saat ini:** {format_number(avg_pr_po, decimals=2)} hari

    **Target:** -
    """)

    if st.session_state.get(key_kpi_real, False):
        st.info(f"""\
    **Rata-rata Realisasi SLA**: Rata-rata waktu proses pengadaan dari Disposisi Buyer ke Tanggal PO dalam **hari kerja**.

    **Formula Excel:**
    - Filter nama karyawan yang ingin dicari
    - Filter **Nilai SLA** menjadi `1`
    - Hitung rata-rata **Realisasi SLA**

    **Interpretasi:**

    | Kondisi | Artinya |
    |---|---|
    | Realisasi ≤ Standard SLA | ✅ On-time, proses selesai sebelum target |
    | Realisasi > Standard SLA | ❌ Miss, proses melewati batas SLA |

    **Standard SLA rata-rata saat ini:** {format_number(avg_std)} hari &nbsp;|&nbsp; **Realisasi saat ini:** {format_number(avg_real, decimals=2)} hari
    """)

    if st.session_state.get(key_kpi_pra, False):
        st.info(f"""\
    **Waktu Pra-Disposisi**: Rata-rata waktu dari PR dibuat (Requisition Date) hingga PR diterima buyer (Tanggal Disposisi Buyer).

    Ini adalah waktu **di luar kendali tim pengadaan**.

    **Formula Excel:**
    - Filter nama karyawan yang ingin dicari
    - Filter **Nilai SLA** menjadi `1`
    - Hitung rata-rata dari `Tanggal Disposisi Buyer` dikurangi dengan `Requisition Date`

    **Nilai saat ini:** {format_number(avg_pra, decimals=2)} hari

    **Catatan:** Nilai ini tinggi bisa mengindikasikan bottleneck di proses approval atau routing sebelum PR masuk ke pengadaan.
    """)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Baris 2: Rata-rata End-to-End | SLA Headroom | % On Time SLA ──
    col4, col5, col6 = st.columns(3)

    with col4:
        c_card, c_btn = st.columns([10, 2])
        with c_card:
            st.markdown(kpi_card("route", "Rata-rata End-to-End",
                                 f"{format_number(avg_e2e, decimals=2)} hari",
                                 "Req Date ke Tgl PO (total keseluruhan)", "n"),
                        unsafe_allow_html=True)
        with c_btn:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            key_kpi_e2e = "show_formula_kpi_e2e"
            if key_kpi_e2e not in st.session_state:
                st.session_state[key_kpi_e2e] = False
            is_open = st.session_state[key_kpi_e2e]
            icon    = ":material/visibility_off:" if is_open else ":material/visibility:"
            tooltip = "Hide Formula" if is_open else "Show Formula"
            st.button(icon, key=f"btn_{key_kpi_e2e}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_kpi_e2e})

    with col5:
        dc = "g" if avg_headroom >= 0 else "r"
        c_card, c_btn = st.columns([10, 2])
        with c_card:
            st.markdown(kpi_card("target", "Rata-rata SLA Headroom",
                                 f"{format_number(avg_headroom, decimals=2)} hari",
                                 "Standard SLA minus Realisasi SLA (sisa waktu)", dc),
                        unsafe_allow_html=True)
        with c_btn:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            key_kpi_headroom = "show_formula_kpi_headroom"
            if key_kpi_headroom not in st.session_state:
                st.session_state[key_kpi_headroom] = False
            is_open = st.session_state[key_kpi_headroom]
            icon    = ":material/visibility_off:" if is_open else ":material/visibility:"
            tooltip = "Hide Formula" if is_open else "Show Formula"
            st.button(icon, key=f"btn_{key_kpi_headroom}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_kpi_headroom})

    with col6:
        dc = "g" if pct_ontime >= 90 else ("o" if pct_ontime >= 75 else "r")
        c_card, c_btn = st.columns([10, 2])
        with c_card:
            st.markdown(kpi_card("check", "% On Time SLA",
                                 f"{format_number(pct_ontime, decimals=2)}%",
                                 f"Realisasi SLA <= Standard SLA | Miss: {format_number(cnt_miss)}", dc),
                        unsafe_allow_html=True)
        with c_btn:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            key_kpi_ontime = "show_formula_kpi_ontime"
            if key_kpi_ontime not in st.session_state:
                st.session_state[key_kpi_ontime] = False
            is_open = st.session_state[key_kpi_ontime]
            icon    = ":material/visibility_off:" if is_open else ":material/visibility:"
            tooltip = "Hide Formula" if is_open else "Show Formula"
            st.button(icon, key=f"btn_{key_kpi_ontime}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_kpi_ontime})

    # Formula info baris 2 - tampil di bawah baris, lebar penuh
    if st.session_state.get(key_kpi_e2e, False):
        st.info(f"""\
    **Rata-rata End-to-End**: Total waktu dari PR pertama kali dibuat (Requisition Date) hingga PO terbit (Tanggal PO), mencakup semua tahapan proses.

    Ini adalah gabungan dari **Waktu Pra-Disposisi** + **PR-PO**:
    - Pra-Disposisi = waktu sebelum buyer menerima PR (routing, approval, antrian)
    - PR-PO = waktu pengadaan setelah buyer menerima PR

    **Formula Excel:**
    - Filter nama karyawan yang ingin dicari
    - Filter **Status** menjadi `Closed`
    - Hitung rata-rata dari `Tanggal PO` dikurangi dengan `Requisition Date`

    **Nilai saat ini:** {format_number(avg_e2e, decimals=2)} hari &nbsp;|&nbsp; **Pra-Disposisi:** {format_number(avg_pra, decimals=2)} hari &nbsp;|&nbsp; **PR-PO:** {format_number(avg_pr_po, decimals=2)} hari
    """)

    if st.session_state.get(key_kpi_headroom, False):
        st.info(f"""\
    **Rata-rata SLA Headroom**: Sisa waktu rata-rata antara target SLA dengan waktu realisasi aktual.

    **Formula:**
    ```
    SLA Headroom = Standard SLA − Realisasi SLA
    ```
                
    **Formula Excel:**
    - Filter nama karyawan yang ingin dicari
    - Filter **Nilai SLA** menjadi `1`
    - Hitung rata-rata dari `Standard SLA` dikurangi dengan `Realisasi SLA`

    **Interpretasi:**

    | Nilai | Artinya |
    |---|---|
    | **Positif** | Proses selesai lebih cepat dari target, masih ada sisa waktu ✅ |
    | **0** | Tepat di batas SLA |
    | **Negatif** | Proses melewati Standard SLA, SLA Miss ❌ |

    **Nilai saat ini:** {format_number(avg_headroom, decimals=2)} hari

    **Target:** ≥ 0 hari (semakin besar semakin baik)
    """)

    if st.session_state.get(key_kpi_ontime, False):
        st.info(f"""\
    **% On Time SLA**: Persentase PR yang berhasil diselesaikan dalam batas Standard SLA.

    **Formula Excel:**
    - Filter nama karyawan yang ingin dicari
    - Filter **Nilai SLA** menjadi `1` dan `0`
    - `= Nilai SLA 1 - Total PO`

    **Interpretasi:**

    | % On Time | Status |
    |---|---|
    | ≥ 90% | 🟢 Baik |
    | 75% – 89% | 🟡 Perlu perhatian |
    | < 75% | 🔴 Kritis |

    **Nilai saat ini:** {format_number(pct_ontime, decimals=2)}% &nbsp;|&nbsp; **Miss:** {format_number(cnt_miss)} PR

    **Target:** ≥ 90%
    """)

    # ══════════════════════════════════════════════════════════════════════════
    # BAGIAN 2: Dekomposisi Waktu per Nama
    # ══════════════════════════════════════════════════════════════════════════
    title_col, btn_col = st.columns([9, 1])
    with title_col:
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:24px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                    <path d="M1 2.5A1.5 1.5 0 0 1 2.5 1h3A1.5 1.5 0 0 1 7 2.5v3A1.5 1.5 0 0 1 5.5 7h-3A1.5 1.5 0 0 1 1 5.5zm8 0A1.5 1.5 0 0 1 10.5 1h3A1.5 1.5 0 0 1 15 2.5v3A1.5 1.5 0 0 1 13.5 7h-3A1.5 1.5 0 0 1 9 5.5zm-8 8A1.5 1.5 0 0 1 2.5 9h3A1.5 1.5 0 0 1 7 10.5v3A1.5 1.5 0 0 1 5.5 15h-3A1.5 1.5 0 0 1 1 13.5zm8 0A1.5 1.5 0 0 1 10.5 9h3a1.5 1.5 0 0 1 1.5 1.5v3a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 9 13.5z"/>
                </svg>
                Dekomposisi Waktu per Nama
            </h1>
            <p style='opacity:.55; font-size:14px; margin:-10px 0 10px 0;'>Proporsi Realisasi SLA vs Selisih Waktu PR-PO per karyawan</p>
        """, unsafe_allow_html=True)
    with btn_col:
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        key_wt_decomp = "show_formula_wt_decomp"
        if key_wt_decomp not in st.session_state:
            st.session_state[key_wt_decomp] = False
        is_open = st.session_state[key_wt_decomp]
        icon = ":material/visibility_off:" if is_open else ":material/visibility:"
        tooltip = "Hide Formula" if is_open else "Show Formula"
        st.button(icon, key=f"btn_{key_wt_decomp}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_wt_decomp})

    if st.session_state.get(key_wt_decomp, False):
        st.info("""\
**Dekomposisi Waktu per Nama:** Stacked bar chart Proporsi Realisasi SLA vs Selisih Waktu PR-PO per karyawan.

| Komponen | Artinya |
|---|---|
| Oranye - Rata-rata Realisasi SLA | Waktu proses pengadaan yang dihitung sebagai Realisasi SLA (hari kerja) |
| Biru - Rata-rata PR-PO minus Realisasi | Selisih waktu antara total PR-PO dengan Realisasi SLA |

Total panjang bar menunjukkan rata-rata keseluruhan hari kerja PR-PO. Bar biru yang panjang mengindikasikan banyaknya waktu yang "terpotong" (misal karena penahanan/pending atau faktor pengecualian lain) yang tidak masuk ke perhitungan Realisasi SLA.

""")

    if df.empty:
            st.info("Tidak ada data untuk filter yang dipilih.")
    else:
        # Grouping & Kalkulasi data
        decomp = df.groupby("nama").agg(
            realisasi=("realisasi_sla", "mean"),
            pr_po=("pr_po_days", "mean")
        ).round(1).reset_index()

        if not decomp.empty:
            # Menghitung selisih, menggunakan .clip(lower=0) untuk mencegah nilai negatif jika ada anomali data
            decomp["selisih"] = (decomp["pr_po"] - decomp["realisasi"]).clip(lower=0).round(1)
            decomp["total"] = decomp["realisasi"] + decomp["selisih"]
            decomp = decomp.sort_values("total", ascending=True)

            # Pembuatan Chart
            fig = go.Figure()
            fig.add_bar(y=decomp["nama"], x=decomp["realisasi"], name="Rata-rata Realisasi SLA",
                        orientation="h", marker_color="#f0a500")
            fig.add_bar(y=decomp["nama"], x=decomp["selisih"], name="Rata-rata PR-PO minus Realisasi",
                        orientation="h", marker_color="#6c8ebf")

            fig.update_layout(barmode="stack", height=max(280, len(decomp)*44),
                                legend=dict(orientation="h", yanchor="bottom", y=1.01),
                                xaxis=dict(title="Hari", **GRID), yaxis=dict(title=""), **LAYOUT)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Tidak ada data untuk filter yang dipilih.")

    # ══════════════════════════════════════════════════════════════════════════
    # BAGIAN 3: Pemenuhan SLA per Jenis Pengadaan
    # ══════════════════════════════════════════════════════════════════════════
    title_col, btn_col = st.columns([9, 1])
    with title_col:
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:24px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                    <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16M10.97 4.97a.235.235 0 0 0-.02.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-1.071-1.05"/>
                </svg>
                Pemenuhan SLA per Jenis Pengadaan
            </h1>
            <p style='opacity:.55; font-size:14px; margin:-10px 0 10px 0;'>% On Time dan rata-rata Realisasi SLA per Standard SLA dan jenis kontrak</p>
        """, unsafe_allow_html=True)
    with btn_col:
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        key_wt_sla_type = "show_formula_wt_sla_type"
        if key_wt_sla_type not in st.session_state:
            st.session_state[key_wt_sla_type] = False
        is_open = st.session_state[key_wt_sla_type]
        icon = ":material/visibility_off:" if is_open else ":material/visibility:"
        tooltip = "Hide Formula" if is_open else "Show Formula"
        st.button(icon, key=f"btn_{key_wt_sla_type}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_wt_sla_type})

    if st.session_state.get(key_wt_sla_type, False):
        st.info("""\
**Standard SLA per jenis pengadaan:** Bar Chart % On Time dan rata-rata Realisasi SLA per Standard SLA dan jenis kontrak.

**Formula Excel:**
- Filter nama karyawan yang ingin dicari
- Filter **Nilai SLA** menjadi `1` dan `0`
- Hitung jumlah **Standard SLA** dengan nilai `12 Hari`, `24 Hari`, `48 Hari`, dan `57 Hari`
                
| Standard SLA | Jenis | Prioritas |
|---|---|---|
| 12 Hari | Agreement | Semua |
| 24 Hari | Non Agreement | Urgent |
| 48 Hari | Non Agreement | TA / Investasi / Emergency |
| 57 Hari | Non Agreement | Normal |

`Nilai SLA = 1` = Realisasi <= Standard (on-time), `= 0` = miss, `= '-'` = belum PO (dikecualikan).

""")

    if df.empty:
            st.info("Tidak ada data untuk filter yang dipilih.")
    else:
        sla_g = df.groupby("standar_sla").agg(
            total =("nilai_sla","count"),
            ontime=("nilai_sla", lambda x: (pd.to_numeric(x,errors="coerce")==1).sum()),
            avg_r =("realisasi_sla","mean"),
        ).reset_index()

        if not sla_g.empty:
            sla_g["pct"]       = (sla_g["ontime"] / sla_g["total"] * 100)
            sla_g["std_num"]   = sla_g["standar_sla"].astype(float)
            sla_g["standar_sla"] = sla_g["std_num"].apply(lambda x: f"{int(x)} Hari" if pd.notna(x) else "N/A")

            col_l, col_r = st.columns(2)
            with col_l:
                st.caption("% On Time per Standard SLA")
                f1 = px.bar(sla_g, x="standar_sla", y="pct",
                            text=sla_g["pct"].apply(lambda x: f"{x:.1f}%"),
                            color="pct",
                            color_continuous_scale=[[0,"#e03c3c"],[0.75,"#f0a500"],[1,"#09ab3b"]],
                            range_color=[0,100])
                f1.add_hline(y=90, line_dash="dash", line_color="rgba(128,128,128,0.5)",
                                annotation_text="Target 90%")
                f1.update_coloraxes(showscale=False)
                f1.update_traces(textposition="outside")
                f1.update_layout(height=300,
                                    xaxis=dict(title="Standard SLA", **GRID),
                                    yaxis=dict(title="% On Time", range=[0,115], **GRID), **LAYOUT)
                st.plotly_chart(f1, use_container_width=True)
            with col_r:
                st.caption("Rata-rata Realisasi SLA vs Standard SLA (target)")
                f2 = go.Figure()
                f2.add_bar(x=sla_g["standar_sla"], y=sla_g["avg_r"],
                            name="Realisasi SLA rata-rata", marker_color="#6c8ebf",
                            text=sla_g["avg_r"].round(1), textposition="outside")
                f2.add_scatter(x=sla_g["standar_sla"], y=sla_g["std_num"],
                                name="Standard SLA (target)", mode="markers",
                                marker=dict(color="#e03c3c", size=12, symbol="line-ew-open",
                                            line=dict(width=3, color="#e03c3c")))
                f2.update_layout(height=300,
                                    xaxis=dict(title="Jenis SLA", **GRID),
                                    yaxis=dict(title="Hari", **GRID),
                                    legend=dict(orientation="h", yanchor="bottom", y=1.01), **LAYOUT)
                st.plotly_chart(f2, use_container_width=True)
        else:
            st.info("Tidak ada data untuk filter yang dipilih.")

    # ══════════════════════════════════════════════════════════════════════════
    # BAGIAN 4: SLA Headroom per Nama
    # ══════════════════════════════════════════════════════════════════════════
    title_col, btn_col = st.columns([9, 1])
    with title_col:
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:24px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                    <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16M8 13A5 5 0 1 1 8 3a5 5 0 0 1 0 10m0 1A6 6 0 1 0 8 2a6 6 0 0 0 0 12m0-9a3 3 0 1 1 0 6 3 3 0 0 1 0-6m0 1a2 2 0 1 0 0 4 2 2 0 0 0 0-4"/>
                </svg>
                SLA Headroom per Nama
            </h1>
            <p style='opacity:.55; font-size:14px; margin:-10px 0 10px 0;'>Sisa waktu rata-rata (Standard SLA minus Realisasi SLA) per karyawan</p>
        """, unsafe_allow_html=True)
    with btn_col:
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        key_wt_headroom = "show_formula_wt_headroom"
        if key_wt_headroom not in st.session_state:
            st.session_state[key_wt_headroom] = False
        is_open = st.session_state[key_wt_headroom]
        icon = ":material/visibility_off:" if is_open else ":material/visibility:"
        tooltip = "Hide Formula" if is_open else "Show Formula"
        st.button(icon, key=f"btn_{key_wt_headroom}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_wt_headroom})

    if st.session_state.get(key_wt_headroom, False):
        st.info("""\
**SLA Headroom per Nama**: Horizontal Bar Chart Sisa waktu rata-rata (Standard SLA minus Realisasi SLA) per karyawan.

| Nilai | Artinya |
|---|---|
| Positif | Selesai lebih cepat dari target, masih ada sisa waktu |
| 0 | Tepat di batas SLA |
| Negatif | Melewati Standard SLA, SLA Miss |

Hijau = rata-rata headroom positif. Merah = sering melewati target.
""")

    if df.empty:
            st.info("Tidak ada data untuk filter yang dipilih.")
    else:
        hdroom = df.groupby("nama")["headroom"].mean().round(1).reset_index()

        if not hdroom.empty:
            hdroom.columns = ["nama", "h"]
            hdroom = hdroom.sort_values("h", ascending=True)
            hdroom["color"] = hdroom["h"].apply(lambda x: "#09ab3b" if x >= 0 else "#e03c3c")
            fh = go.Figure()
            fh.add_bar(y=hdroom["nama"], x=hdroom["h"], orientation="h",
                        marker_color=hdroom["color"].tolist(),
                        text=hdroom["h"].apply(lambda x: f"{x:+.1f}H"), textposition="outside")
            fh.add_vline(x=0, line_color="rgba(128,128,128,0.4)", line_width=1)
            fh.update_layout(height=max(280, len(hdroom)*40),
                                xaxis=dict(title="Hari (+ = lebih cepat dari target, - = miss)", **GRID),
                                yaxis=dict(title=""), showlegend=False, **LAYOUT)
            st.plotly_chart(fh, use_container_width=True)
        else:
            st.info("Tidak ada data untuk filter yang dipilih.")

    # ══════════════════════════════════════════════════════════════════════════
    # BAGIAN 5: Tren Waktu per Bulan
    # ══════════════════════════════════════════════════════════════════════════
    title_col, btn_col = st.columns([9, 1])
    with title_col:
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:24px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                    <path d="M0 0h1v15h15v1H0zm14.817 3.113a.5.5 0 0 1 .07.704l-4.5 5.5a.5.5 0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5 0 0 1 .758-.06l2.609 2.61 4.15-5.073a.5.5 0 0 1 .704-.07"/>
                </svg>
                Tren Waktu per Bulan
            </h1>
            <p style='opacity:.55; font-size:14px; margin:-10px 0 10px 0;'>Perubahan kecepatan proses dari bulan ke bulan</p>
        """, unsafe_allow_html=True)
    with btn_col:
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        key_wt_trend = "show_formula_wt_trend"
        if key_wt_trend not in st.session_state:
            st.session_state[key_wt_trend] = False
        is_open = st.session_state[key_wt_trend]
        icon = ":material/visibility_off:" if is_open else ":material/visibility:"
        tooltip = "Hide Formula" if is_open else "Show Formula"
        st.button(icon, key=f"btn_{key_wt_trend}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_wt_trend})

    if st.session_state.get(key_wt_trend, False):
        st.info("""\
**Tren Waktu per Bulan**: Combo Chart Perubahan kecepatan proses dari bulan ke bulan.

| Elemen | Warna | Keterangan |
|---|---|---|
| Bar biru | End-to-End | Req Date ke Tgl PO |
| Garis oranye | PR-PO | Hari kerja Disposisi ke PO |
| Garis hijau | Realisasi SLA | Hari kerja Disposisi ke PO |
| Garis merah putus | % On Time | Sumbu kanan |

""")

    if df.empty or "bulan" not in df.columns or not df["bulan"].notna().any():
            st.info("Tidak ada data untuk filter yang dipilih.")
    else:
        trend = df.groupby("bulan").agg(
            avg_pr_po=("pr_po_days","mean"), avg_real=("realisasi_sla","mean"),
            avg_e2e  =("e2e","mean"), total=("nilai_sla","count"),
            ontime   =("nilai_sla", lambda x: (pd.to_numeric(x,errors="coerce")==1).sum()),
        ).reset_index().sort_values("bulan")

    if date_from:
        bulan_from = str(date_from)[:7]   # ambil "YYYY-MM"
        trend = trend[trend["bulan"] >= bulan_from]
    if date_to:
        bulan_to = str(date_to)[:7]
        trend = trend[trend["bulan"] <= bulan_to]

        if not trend.empty:
            trend["pct"] = (trend["ontime"]/trend["total"]*100).round(1)
            ft = go.Figure()
            ft.add_bar(x=trend["bulan"], y=trend["avg_e2e"],
                        name="End-to-End (Req ke PO)", marker_color="#6c8ebf", opacity=0.5)
            ft.add_scatter(x=trend["bulan"], y=trend["avg_pr_po"], name="PR-PO (kerja)",
                            mode="lines+markers", line=dict(color="#f0a500",width=2), marker=dict(size=6))
            ft.add_scatter(x=trend["bulan"], y=trend["avg_real"], name="Realisasi SLA (kerja)",
                            mode="lines+markers", line=dict(color="#09ab3b",width=2), marker=dict(size=6))
            ft.add_scatter(x=trend["bulan"], y=trend["pct"], name="% On Time",
                            mode="lines+markers", yaxis="y2",
                            line=dict(color="#e03c3c",width=2,dash="dash"), marker=dict(size=5))
            ft.update_layout(
                height=340,
                yaxis =dict(title="Hari", **GRID),
                yaxis2=dict(title="% On Time", overlaying="y", side="right",
                            range=[0,110], showgrid=False),
                legend=dict(orientation="h", yanchor="bottom", y=1.01),
                xaxis =dict(title="", **GRID), **LAYOUT)
            st.plotly_chart(ft, use_container_width=True)
        else:
            st.info("Tidak ada data untuk filter yang dipilih.")

    # ══════════════════════════════════════════════════════════════════════════
    # BAGIAN 6: Distribusi Waktu
    # ══════════════════════════════════════════════════════════════════════════
    title_col, btn_col = st.columns([9, 1])
    with title_col:
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:24px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                    <path d="M1 11a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1zm5-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1zm5-5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1z"/>
                </svg>
                Distribusi Waktu
            </h1>
            <p style='opacity:.55; font-size:14px; margin:-10px 0 10px 0;'>Sebaran PR-PO dan Realisasi SLA untuk mendeteksi outlier</p>
        """, unsafe_allow_html=True)
    with btn_col:
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        key_wt_dist = "show_formula_wt_dist"
        if key_wt_dist not in st.session_state:
            st.session_state[key_wt_dist] = False
        is_open = st.session_state[key_wt_dist]
        icon = ":material/visibility_off:" if is_open else ":material/visibility:"
        tooltip = "Hide Formula" if is_open else "Show Formula"
        st.button(icon, key=f"btn_{key_wt_dist}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_wt_dist})

    if st.session_state.get(key_wt_dist, False):
        st.info("""\
**Distribusi Waktu**: Bar Chart Sebaran PR-PO dan Realisasi SLA untuk mendeteksi outlier.

- **Kiri - PR-PO**: Disposisi ke Tgl PO. Ekor kanan panjang = ada PR yang sangat lama diproses setelah disposisi.
- **Kanan - Realisasi SLA**: Waktu bersih proses pengadaan dari Disposisi ke PO dengan mengecualikan hari libur. Ini adalah metrik utama penentu On-Time/Miss SLA. Outlier di sebelah kanan menunjukkan dokumen yang jauh melewati target SLA.

Garis putus = rata-rata masing-masing.
""")

    if df.empty:
            st.info("Tidak ada data untuk filter yang dipilih.")
    else:
        col_l, col_r = st.columns(2)
        with col_l:
            st.caption("Distribusi PR-PO (hari kerja)")
            if "pr_po_days" in df.columns:
                d1 = df[df["pr_po_days"].notna() & (df["pr_po_days"]>=0)]
                if d1.empty:
                    st.info("Tidak ada data untuk filter yang dipilih.")
                else:
                    avg1 = d1["pr_po_days"].mean()
                    f6 = px.histogram(d1, x="pr_po_days", nbins=30, color_discrete_sequence=["#f0a500"])
                    f6.add_vline(x=avg1, line_dash="dash", line_color="#6c8ebf",
                                    annotation_text=f"Rata-rata {avg1:.1f}H", annotation_position="top right")
                    f6.update_layout(height=280, xaxis=dict(title="Hari",**GRID),
                                        yaxis=dict(title="Jumlah PR",**GRID), showlegend=False, **LAYOUT)
                    st.plotly_chart(f6, use_container_width=True)
            else:
                st.info("Tidak ada data untuk filter yang dipilih.")

        with col_r:
            st.caption("Distribusi Realisasi SLA (hari kerja)")
            if "realisasi_sla" in df.columns:
                d2 = df[df["realisasi_sla"].notna() & (df["realisasi_sla"]>=0)]
                if d2.empty:
                    st.info("Tidak ada data untuk filter yang dipilih.")
                else:
                    avg2 = d2["realisasi_sla"].mean()
                    f7 = px.histogram(d2, x="realisasi_sla", nbins=30, color_discrete_sequence=["#6c8ebf"])
                    f7.add_vline(x=avg2, line_dash="dash", line_color="#f0a500",
                                    annotation_text=f"Rata-rata {avg2:.1f}H", annotation_position="top right")
                    f7.update_layout(height=280, xaxis=dict(title="Hari",**GRID),
                                        yaxis=dict(title="Jumlah PR",**GRID), showlegend=False, **LAYOUT)
                    st.plotly_chart(f7, use_container_width=True)
            else:
                st.info("Tidak ada data untuk filter yang dipilih.")

    # ══════════════════════════════════════════════════════════════════════════
    # BAGIAN 7: Waktu per Prioritas
    # ══════════════════════════════════════════════════════════════════════════
    title_col, btn_col = st.columns([9, 1])
    with title_col:
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:24px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                    <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5m.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2"/>
                </svg>
                Waktu per Prioritas
            </h1>
            <p style='opacity:.55; font-size:14px; margin:-10px 0 10px 0;'>Rata-rata PR-PO & Realisasi SLA per Prioritas dan % On Time per Prioritas</p>
        """, unsafe_allow_html=True)
    with btn_col:
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        key_wt_prio = "show_formula_wt_prio"
        if key_wt_prio not in st.session_state:
            st.session_state[key_wt_prio] = False
        is_open = st.session_state[key_wt_prio]
        icon = ":material/visibility_off:" if is_open else ":material/visibility:"
        tooltip = "Hide Formula" if is_open else "Show Formula"
        st.button(icon, key=f"btn_{key_wt_prio}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_wt_prio})

    if st.session_state.get(key_wt_prio, False):
        st.info("""\
**Waktu per Prioritas**: Bar Chart Rata-rata PR-PO & Realisasi SLA per Prioritas dan % On Time per Prioritas.

| Prioritas | Standard SLA |
|---|---|
| Emergency | 12H (Agreement) / 48H (Non-Agreement) |
| Urgent | 24H |
| TA | 48H |
| Investasi | 48H |
| Normal | 12H (Agreement) / 57H (Non-Agreement) |

**Formula Excel:**
- Filter nama karyawan yang ingin dicari
- Filter **Nilai SLA** menjadi `1` dan `0`
- Filter **Prioritas** menjadi `Urgent`, `TA`, `Investasi`, dan `Normal`
- **Chart Kiri**: Hitung rata-rata **PR-PO** dan **Realisasi SLA**
- **Chart Kanan**: Total nilai `1` pada **Nilai SLA** dibagi **Total PO**
                
Idealnya Emergency dan Urgent lebih rendah dari Normal.
""")

    if df.empty:
        st.info("Tidak ada data untuk filter yang dipilih.")
    else:
        ORDER = ["Emergency","Urgent","TA","Investasi","Normal"]
        prio = df.groupby("prioritas").agg(
            avg_pr_po=("pr_po_days","mean"), avg_real=("realisasi_sla","mean"),
            total=("nilai_sla","count"),
            ontime=("nilai_sla", lambda x: (pd.to_numeric(x,errors="coerce")==1).sum()),
        ).reset_index()

        if not prio.empty:
            prio["pct"] = (prio["ontime"]/prio["total"]*100).round(1)
            prio["_o"]  = prio["prioritas"].apply(lambda x: ORDER.index(x) if x in ORDER else 99)
            prio = prio.sort_values("_o")

            col_l, col_r = st.columns(2)
            with col_l:
                st.caption("Rata-rata PR-PO & Realisasi SLA per Prioritas")
                f8 = go.Figure()
                f8.add_bar(x=prio["prioritas"], y=prio["avg_pr_po"], name="PR-PO (kerja)",
                            marker_color="#f0a500", text=prio["avg_pr_po"].round(1), textposition="outside")
                f8.add_bar(x=prio["prioritas"], y=prio["avg_real"], name="Realisasi SLA (kerja)",
                            marker_color="#09ab3b", text=prio["avg_real"].round(1), textposition="outside")
                f8.update_layout(barmode="group", height=300,
                                    xaxis=dict(title="", categoryorder="array", categoryarray=ORDER, **GRID),
                                    yaxis=dict(title="Hari", **GRID),
                                    legend=dict(orientation="h", yanchor="bottom", y=1.01), **LAYOUT)
                st.plotly_chart(f8, use_container_width=True)
            with col_r:
                st.caption("% On Time per Prioritas")
                f9 = px.bar(prio, x="prioritas", y="pct",
                            text=prio["pct"].apply(lambda x: f"{x:.1f}%"), color="pct",
                            color_continuous_scale=[[0,"#e03c3c"],[0.75,"#f0a500"],[1,"#09ab3b"]],
                            range_color=[0,100], category_orders={"prioritas":ORDER})
                f9.add_hline(y=90, line_dash="dash", line_color="rgba(128,128,128,0.5)",
                                annotation_text="Target 90%")
                f9.update_coloraxes(showscale=False)
                f9.update_traces(textposition="outside")
                f9.update_layout(height=300, xaxis=dict(title="", **GRID),
                                    yaxis=dict(title="% On Time", range=[0,115], **GRID), **LAYOUT)
                st.plotly_chart(f9, use_container_width=True)
        else:
            st.info("Tidak ada data untuk filter yang dipilih.")

    # ══════════════════════════════════════════════════════════════════════════
    # BAGIAN 8: Waktu Realisasi SLA per Purchasing Group
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    title_col, btn_col = st.columns([9, 1])
    with title_col:
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:24px;'>
                <svg xmlns="[http://www.w3.org/2000/svg](http://www.w3.org/2000/svg)" width="20" height="20" fill="currentColor" class="bi bi-diagram-3-fill" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                    <path d="M6 .5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1H9v1.07a7.001 7.001 0 0 1 3.274 12.474l.601.602a.5.5 0 0 1-.707.708l-.746-.746A6.97 6.97 0 0 1 8 16a6.97 6.97 0 0 1-3.422-.892l-.746.746a.5.5 0 0 1-.707-.708l.602-.602A7.001 7.001 0 0 1 7 2.07V1h-.5A.5.5 0 0 1 6 .5m2.5 5a.5.5 0 0 0-1 0v3.362l-1.429 2.38a.5.5 0 1 0 .858.515l1.5-2.5A.5.5 0 0 0 8.5 9zM.86 5.387A2.5 2.5 0 1 1 4.387 1.86 8.04 8.04 0 0 0 .86 5.387M11.613 1.86a2.5 2.5 0 1 1 3.527 3.527 8.04 8.04 0 0 0-3.527-3.527"/>
                </svg>
                Waktu Realisasi SLA per Purchasing Group
            </h1>
            <p style='opacity:.55; font-size:14px; margin:-10px 0 10px 0;'>Perbandingan rata-rata waktu penyelesaian berdasarkan Purchasing Group</p>
        """, unsafe_allow_html=True)
    with btn_col:
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        key_wt_pg = "show_formula_wt_pg"
        if key_wt_pg not in st.session_state:
            st.session_state[key_wt_pg] = False
        is_open = st.session_state[key_wt_pg]
        icon = ":material/visibility_off:" if is_open else ":material/visibility:"
        tooltip = "Hide Formula" if is_open else "Show Formula"
        st.button(icon, key=f"btn_{key_wt_pg}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_wt_pg})

    if st.session_state.get(key_wt_pg, False):
        st.info("""\
**Waktu Realisasi SLA per Purchasing Group**: Bar Chart Perbandingan rata-rata waktu penyelesaian berdasarkan Purchasing Group.

Menampilkan rata-rata waktu Realisasi SLA (dalam hari kerja) yang dihabiskan oleh masing-masing Purchasing Group.
                
**Formula Excel:**
- Filter **Purchasing Group** yang ingin dicari
- Filter **Status** menjadi `Proses PO` dan `Closed`
- Hitung rata-rata **Realisasi SLA**
                
""")

    if df.empty or "purchasing_group" not in df.columns:
        st.info("Tidak ada data untuk filter yang dipilih.")
    else:
        pg_df = df.groupby("purchasing_group").agg(
            avg_realisasi=("realisasi_sla", "mean"),
            jumlah_pr=("realisasi_sla", "count")
        ).reset_index()

        # Buang jika ada purchasing group yang kosong
        pg_df = pg_df[pg_df["purchasing_group"].notna() & (pg_df["purchasing_group"].str.strip() != "")]

        if not pg_df.empty:
            pg_df = pg_df.sort_values("avg_realisasi", ascending=False)

            fig_pg = go.Figure()
            fig_pg.add_bar(
                x=pg_df["purchasing_group"], 
                y=pg_df["avg_realisasi"],
                marker_color="#09ab3b",
                text=pg_df["avg_realisasi"].round(1).apply(lambda x: f"{x} H"),
                textposition="outside"
            )

            fig_pg.update_layout(
                height=320,
                xaxis=dict(title="Purchasing Group", **GRID),
                yaxis=dict(title="Rata-rata Hari Kerja", **GRID),
                **LAYOUT
            )
            st.plotly_chart(fig_pg, use_container_width=True)
        else:
            st.info("Tidak ada data untuk filter yang dipilih.")

    # =====================================================================
    # INTEGRASI AI: KUMPULKAN KONTEKS & PANGGIL CHAT
    # =====================================================================
    
    konteks_lines = []
    
    # 0. Rangkuman Filter
    konteks_lines.append("## 0. FILTER YANG SEDANG DITERAPKAN USER")
    konteks_lines.append(info_filter)
    konteks_lines.append("\n")

    # 1. Ringkasan KPI Waktu Utama
    konteks_lines.append("## 1. RINGKASAN KPI WAKTU PROSES SIPS")
    konteks_lines.append(f"- Rata-rata End-to-End (Total): {avg_e2e:.2f} hari")
    konteks_lines.append(f"- Rata-rata Pra-Disposisi (Sebelum masuk pengadaan): {avg_pra:.2f} hari")
    konteks_lines.append(f"- Rata-rata PR-PO (Hari kerja di pengadaan): {avg_pr_po:.2f} hari")
    konteks_lines.append(f"- Rata-rata Realisasi SLA (Hari Kerja di pengadaan): {avg_real:.2f} hari")
    konteks_lines.append(f"- Rata-rata Standard SLA Target: {avg_std:.2f} hari")
    konteks_lines.append(f"- SLA Headroom (Sisa Waktu): {avg_headroom:.2f} hari")
    konteks_lines.append(f"- % On Time SLA: {pct_ontime:.2f}% (Jumlah terlambat: {cnt_miss} PO)\n")

    # 2. Dekomposisi Waktu per Nama (Karyawan)
    if 'decomp' in locals() and not decomp.empty:
        konteks_lines.append("## 2. DEKOMPOSISI WAKTU PER KARYAWAN")
        # Menggunakan df decomp yang sudah dihitung sebelumnya
        konteks_lines.append(decomp.to_csv(index=False))
        konteks_lines.append("\n")

    # 3. SLA Berdasarkan Jenis Standard SLA
    if 'sla_g' in locals() and not sla_g.empty:
        konteks_lines.append("## 3. PEMENUHAN SLA BERDASARKAN STANDARD SLA")
        # Pilih kolom penting
        df_sla_simple = sla_g[['standar_sla', 'total', 'ontime', 'avg_r', 'pct']]
        konteks_lines.append(df_sla_simple.to_csv(index=False))
        konteks_lines.append("\n")

    # 4. Waktu per Prioritas Dokumen
    if 'prio' in locals() and not prio.empty:
        konteks_lines.append("## 4. WAKTU PROSES BERDASARKAN PRIORITAS")
        df_prio_simple = prio[['prioritas', 'avg_pr_po', 'avg_real', 'pct']]
        konteks_lines.append(df_prio_simple.to_csv(index=False))
        konteks_lines.append("\n")

            
    # 5. Rata-rata Realisasi SLA per Purchasing Group
    if 'pg_df' in locals() and not pg_df.empty:
        konteks_lines.append("## 5. RATA-RATA REALISASI SLA PER PURCHASING GROUP")
        df_pg_simple = pg_df[['purchasing_group', 'avg_realisasi', 'jumlah_pr']].sort_values('avg_realisasi', ascending=False)
        df_pg_simple['avg_realisasi'] = df_pg_simple['avg_realisasi'].round(1)
        konteks_lines.append(df_pg_simple.to_csv(index=False))
        konteks_lines.append("\n")


    # Gabungkan konteks lokal halaman ini dengan konteks global lintas sistem
    suplemen = "\n# SUPLEMEN - DETAIL HALAMAN INI (Analisis Waktu Proses SIPS)\n" + "\n".join(konteks_lines)
    konteks_final = kwargs.get("global_context", "") + "\n---\n" + suplemen

    # Panggil komponen chat
    render_chat_analyst(
        konteks_data_teks=konteks_final,
        nama_halaman="Analisis Waktu Proses SIPS"
    )