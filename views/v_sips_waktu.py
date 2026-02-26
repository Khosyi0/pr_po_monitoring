"""
v_sips_waktu.py - Analisis Waktu Proses SIPS

Timeline nyata dari data Excel:
  [Requisition Date (I)] --<Waktu Pra-Disposisi>--> [Tgl Disposisi Buyer (K)] --<PR-PO (N)>--> [Tanggal PO (L)]
                                                                                 <Realisasi SLA (T, hari kerja)>

Kolom waktu:
  N  PR-PO         = Disposisi Buyer → Tgl PO, hari KALENDER
  S  Standard SLA  = target: Agreement 12H / Urgent 24H / TA-Investasi 48H / Normal 57H
  T  Realisasi SLA = Disposisi → PO hari KERJA (rata-rata 8H lebih pendek dari N)
  U  Nilai SLA     = 1 ontime · 0 miss · '-' belum PO (exclude dari analisis)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import format_number


def toggle_state(key):
    st.session_state[key] = not st.session_state[key]

def init_toggle(key):
    if key not in st.session_state:
        st.session_state[key] = False

def formula_btn(key):
    init_toggle(key)
    opened = st.session_state[key]
    st.button(
        ":material/visibility_off:" if opened else ":material/visibility:",
        key=f"btn_{key}",
        help="Hide Formula" if opened else "Show Formula",
        on_click=toggle_state, kwargs={"key": key},
    )

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

def sec_btn(title, sub, key, formula, icon_path):
    # Buat rasio kolom 9 banding 1 seperti di v_dashboard.py
    title_col, btn_col = st.columns([9, 1])
    
    with title_col:
        # Render HTML untuk header + SVG + Subtitle
        st.markdown(f"""
            <h1 style='display: flex; align-items: center; font-size:24px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                    <path d="{icon_path}"/>
                </svg>
                {title}
            </h1>
            <p style='opacity:.55; font-size:14px; margin:-10px 0 10px 0;'>{sub}</p>
        """, unsafe_allow_html=True)
        
    with btn_col:
        # Posisikan tombol mata agar sejajar
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        formula_btn(key)
        
    # Render info box di bawah (luar kolom) jika tombol ditekan
    if st.session_state[key]:
        st.info(formula)


def render(load_data, date_from, date_to, selected_nama, **kwargs):
    st.markdown(KPI_CSS, unsafe_allow_html=True)

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

    wp = ["1=1", "nilai_sla IS NOT NULL", "status IN ('Closed','Proses PO')"]
    if date_from:
        wp.append(f"requisition_date >= '{date_from}'")
    if date_to:
        wp.append(f"requisition_date <= '{date_to}'")
    if selected_nama and "All" not in selected_nama:
        nms = ", ".join(f"'{n}'" for n in selected_nama)
        wp.append(f"nama IN ({nms})")
    where = " AND ".join(wp)

    kpi_q = f"""
    SELECT
        ROUND(AVG(pr_po_days)::numeric,1)                               AS avg_pr_po,
        ROUND(AVG(realisasi_sla)::numeric,1)                           AS avg_real,
        ROUND(AVG(standar_sla)::numeric,1)                             AS avg_std,
        ROUND(AVG(tgl_disposisi_buyer - requisition_date)::numeric,1)  AS avg_pra,
        ROUND(AVG(tgl_po - requisition_date)::numeric,1)               AS avg_e2e,
        ROUND(AVG(standar_sla - realisasi_sla)::numeric,1)            AS avg_headroom,
        ROUND(SUM(CASE WHEN nilai_sla=1 THEN 1.0 END)/NULLIF(COUNT(*),0)*100,1) AS pct_ontime,
        COUNT(CASE WHEN nilai_sla=0 THEN 1 END)                        AS cnt_miss
    FROM vw_sips WHERE {where}
    """

    chart_q = f"""
    SELECT
        nama, standar_sla, pr_po_days, realisasi_sla, nilai_sla,
        kontrak_status, prioritas,
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

    if dk.empty or df.empty:
        st.info("Tidak ada data untuk filter yang dipilih.")
        return

    r            = dk.iloc[0]
    avg_pr_po    = float(r["avg_pr_po"]    or 0)
    avg_real     = float(r["avg_real"]     or 0)
    avg_std      = float(r["avg_std"]      or 0)
    avg_pra      = float(r["avg_pra"]      or 0)
    avg_e2e      = float(r["avg_e2e"]      or 0)
    avg_headroom = float(r["avg_headroom"] or 0)
    pct_ontime   = float(r["pct_ontime"]   or 0)
    cnt_miss     = int(r["cnt_miss"]       or 0)

    # ── 1. KPI Ringkasan ─────────────────────────────────────────────────────
    st.markdown("""
            <h1 style='display: flex; align-items: center;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor" class="bi bi-graph-up" viewBox="0 0 16 16" style="margin-bottom: 8px; margin-right: 8px;">
                    <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0M8 3.5a.5.5 0 0 0-1 0V9a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0 0 .496-.868L8 8.71z"/>
                </svg>
                Ringkasan Waktu
            </h1>
        """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(kpi_card("clock","Rata-rata PR-PO",f"{format_number(avg_pr_po, decimals=1)} hari",
                             "Disposisi Buyer ke Tgl PO (hari kalender)","n"),
                    unsafe_allow_html=True)
    with c2:
        dc = "g" if avg_real <= avg_std else "r"
        st.markdown(kpi_card("check","Rata-rata Realisasi SLA",f"{format_number(avg_real, decimals=1)} hari",
                             f"Disposisi ke PO hari kerja | Standar rata-rata {format_number(avg_std)}H",dc),
                    unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card("split","Waktu Pra-Disposisi",f"{format_number(avg_pra, decimals=1)} hari",
                             "Req Date ke Disposisi (routing / approval)","n"),
                    unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(kpi_card("route","Rata-rata End-to-End",f"{format_number(avg_e2e, decimals=1)} hari",
                             "Req Date ke Tgl PO (total keseluruhan)","n"),
                    unsafe_allow_html=True)
    with c2:
        dc = "g" if avg_headroom >= 0 else "r"
        st.markdown(kpi_card("target","Rata-rata SLA Headroom",f"{format_number(avg_headroom, decimals=1)} hari",
                             "Standard SLA minus Realisasi SLA (sisa waktu)",dc),
                    unsafe_allow_html=True)
    with c3:
        dc = "g" if pct_ontime >= 90 else ("o" if pct_ontime >= 75 else "r")
        st.markdown(kpi_card("check","% On Time SLA",f"{format_number(pct_ontime, decimals=1)}%",
                             f"Realisasi SLA <= Standard SLA | Miss: {format_number(cnt_miss)}",dc),
                    unsafe_allow_html=True)

    # ── 2. Dekomposisi per Nama ───────────────────────────────────────────────
    sec_btn(
        title="Dekomposisi Waktu per Nama",
        sub="Proporsi PR-PO (tim pengadaan) vs Waktu Pra-Disposisi per karyawan",
        key="wt_decomp",
        icon_path="M1 2.5A1.5 1.5 0 0 1 2.5 1h3A1.5 1.5 0 0 1 7 2.5v3A1.5 1.5 0 0 1 5.5 7h-3A1.5 1.5 0 0 1 1 5.5zm8 0A1.5 1.5 0 0 1 10.5 1h3A1.5 1.5 0 0 1 15 2.5v3A1.5 1.5 0 0 1 13.5 7h-3A1.5 1.5 0 0 1 9 5.5zm-8 8A1.5 1.5 0 0 1 2.5 9h3A1.5 1.5 0 0 1 7 10.5v3A1.5 1.5 0 0 1 5.5 15h-3A1.5 1.5 0 0 1 1 13.5zm8 0A1.5 1.5 0 0 1 10.5 9h3a1.5 1.5 0 0 1 1.5 1.5v3a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 9 13.5z",
        formula="""\
**Dekomposisi Waktu per Nama**

| Komponen | Kolom | Artinya |
|---|---|---|
| Oranye - PR-PO | N | Disposisi ke PO (hari kalender, waktu tim pengadaan) |
| Biru - Pra-Disposisi | K minus I | Req Date ke Disposisi (routing/approval sebelum buyer) |

Total bar = rata-rata end-to-end. Bar oranye panjang = buyer lambat setelah menerima PR. Bar biru panjang = PR lama sebelum sampai ke buyer.

**Kalkulasi SQL:**
```sql
AVG(pr_po_days)                             AS avg_pr_po
AVG(tgl_disposisi_buyer - requisition_date) AS avg_pra
GROUP BY nama
```
""")

    decomp = df.groupby("nama").agg(pr_po=("pr_po_days","mean"), pra=("waktu_pra","mean")).round(1).reset_index()
    decomp["total"] = decomp["pr_po"] + decomp["pra"]
    decomp = decomp.sort_values("total", ascending=True)
    fig = go.Figure()
    fig.add_bar(y=decomp["nama"], x=decomp["pr_po"], name="PR-PO (tim pengadaan)",
                orientation="h", marker_color="#f0a500")
    fig.add_bar(y=decomp["nama"], x=decomp["pra"], name="Pra-Disposisi (sebelum buyer)",
                orientation="h", marker_color="#6c8ebf")
    fig.update_layout(barmode="stack", height=max(280, len(decomp)*44),
                      legend=dict(orientation="h", yanchor="bottom", y=1.01),
                      xaxis=dict(title="Hari", **GRID), yaxis=dict(title=""), **LAYOUT)
    st.plotly_chart(fig, use_container_width=True)

    # ── 3. SLA per Jenis Pengadaan ────────────────────────────────────────────
    sec_btn(
        title="Pemenuhan SLA per Jenis Pengadaan",
        sub="% On Time dan rata-rata Realisasi SLA per Standard SLA dan jenis kontrak",
        key="wt_sla_type",
        icon_path="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16M10.97 4.97a.235.235 0 0 0-.02.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-1.071-1.05",
        formula="""\
**Standard SLA per jenis pengadaan:**

| Standard SLA | Jenis | Prioritas |
|---|---|---|
| 12 Hari | Agreement | Semua |
| 24 Hari | Non Agreement | Urgent |
| 48 Hari | Non Agreement | TA / Investasi / Emergency |
| 57 Hari | Non Agreement | Normal |

`Nilai SLA = 1` = Realisasi <= Standard (on-time), `= 0` = miss, `= '-'` = belum PO (dikecualikan).

**Kalkulasi SQL:**
```sql
SUM(CASE WHEN nilai_sla=1 THEN 1.0 END) / COUNT(*) * 100 AS pct_ontime
GROUP BY standar_sla
```
""")

    sla_g = df.groupby("standar_sla").agg(
        total =("nilai_sla","count"),
        ontime=("nilai_sla", lambda x: (pd.to_numeric(x,errors="coerce")==1).sum()),
        avg_r =("realisasi_sla","mean"),
    ).reset_index()
    sla_g["pct"] = (sla_g["ontime"] / sla_g["total"] * 100)
    sla_g["std_num"] = sla_g["standar_sla"].astype(float)
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

    # ── 4. SLA Headroom per Nama ──────────────────────────────────────────────
    sec_btn(
        title="SLA Headroom per Nama",
        sub="Sisa waktu rata-rata (Standard SLA minus Realisasi SLA) per karyawan",
        key="wt_headroom",
        icon_path="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16M8 13A5 5 0 1 1 8 3a5 5 0 0 1 0 10m0 1A6 6 0 1 0 8 2a6 6 0 0 0 0 12m0-9a3 3 0 1 1 0 6 3 3 0 0 1 0-6m0 1a2 2 0 1 0 0 4 2 2 0 0 0 0-4",
        formula="""\
**SLA Headroom** = Standard SLA minus Realisasi SLA

| Nilai | Artinya |
|---|---|
| Positif | Selesai lebih cepat dari target, masih ada sisa waktu |
| 0 | Tepat di batas SLA |
| Negatif | Melewati Standard SLA, SLA Miss |

**Kalkulasi SQL:**
```sql
AVG(standar_sla - realisasi_sla) AS avg_headroom
GROUP BY nama
```
Hijau = rata-rata headroom positif. Merah = sering melewati target.
""")

    hdroom = df.groupby("nama")["headroom"].mean().round(1).reset_index()
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

    # ── 5. Tren per Bulan ─────────────────────────────────────────────────────
    sec_btn(
        title="Tren Waktu per Bulan",
        sub="Perubahan kecepatan proses dari bulan ke bulan",
        key="wt_trend",
        icon_path="M0 0h1v15h15v1H0zm14.817 3.113a.5.5 0 0 1 .07.704l-4.5 5.5a.5.5 0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5 0 0 1 .758-.06l2.609 2.61 4.15-5.073a.5.5 0 0 1 .704-.07",
        formula="""\
**Tren Waktu per Bulan**

| Elemen | Warna | Keterangan |
|---|---|---|
| Bar biru | End-to-End | Req Date ke Tgl PO |
| Garis oranye | PR-PO | Hari kalender Disposisi ke PO |
| Garis hijau | Realisasi SLA | Hari kerja Disposisi ke PO |
| Garis merah putus | % On Time | Sumbu kanan |

**Kalkulasi SQL:**
```sql
TO_CHAR(DATE_TRUNC('month',requisition_date),'YYYY-MM') AS bulan,
AVG(pr_po_days)                AS avg_pr_po,
AVG(realisasi_sla)             AS avg_real,
AVG(tgl_po - requisition_date) AS avg_e2e,
SUM(CASE WHEN nilai_sla=1 THEN 1.0 END)/COUNT(*)*100 AS pct_ontime
GROUP BY bulan ORDER BY bulan
```
""")

    if "bulan" in df.columns and df["bulan"].notna().any():
        trend = df.groupby("bulan").agg(
            avg_pr_po=("pr_po_days","mean"), avg_real=("realisasi_sla","mean"),
            avg_e2e  =("e2e","mean"), total=("nilai_sla","count"),
            ontime   =("nilai_sla", lambda x: (pd.to_numeric(x,errors="coerce")==1).sum()),
        ).reset_index().sort_values("bulan")
        trend["pct"] = (trend["ontime"]/trend["total"]*100).round(1)
        ft = go.Figure()
        ft.add_bar(x=trend["bulan"], y=trend["avg_e2e"],
                   name="End-to-End (Req ke PO)", marker_color="#6c8ebf", opacity=0.5)
        ft.add_scatter(x=trend["bulan"], y=trend["avg_pr_po"], name="PR-PO (kalender)",
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

    # ── 6. Distribusi Waktu ───────────────────────────────────────────────────
    sec_btn(
        title="Distribusi Waktu",
        sub="Sebaran PR-PO dan End-to-End untuk mendeteksi outlier",
        key="wt_dist",
        icon_path="M1 11a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1zm5-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1zm5-5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1z",
        formula="""\
**Distribusi Waktu**

**Kiri - PR-PO (N, hari kalender):** Disposisi ke Tgl PO. Mayoritas diharapkan di bawah Standard SLA.
Ekor kanan panjang = ada PR yang sangat lama diproses setelah disposisi.

**Kanan - End-to-End (Req Date ke Tgl PO):** Termasuk waktu pra-disposisi.
Outlier = PR yang sangat lama menunggu sebelum sampai ke buyer.

Garis putus = rata-rata masing-masing.
""")

    col_l, col_r = st.columns(2)
    with col_l:
        st.caption("Distribusi PR-PO (kolom N, hari kalender)")
        d1 = df[df["pr_po_days"].notna() & (df["pr_po_days"]>0)]
        if not d1.empty:
            avg1 = d1["pr_po_days"].mean()
            f6 = px.histogram(d1, x="pr_po_days", nbins=30, color_discrete_sequence=["#f0a500"])
            f6.add_vline(x=avg1, line_dash="dash", line_color="#6c8ebf",
                         annotation_text=f"Rata-rata {avg1:.1f}H", annotation_position="top right")
            f6.update_layout(height=280, xaxis=dict(title="Hari",**GRID),
                             yaxis=dict(title="Jumlah PR",**GRID), showlegend=False, **LAYOUT)
            st.plotly_chart(f6, use_container_width=True)
    with col_r:
        st.caption("Distribusi End-to-End (Req Date ke Tgl PO)")
        d2 = df[df["e2e"].notna() & (df["e2e"]>0)]
        if not d2.empty:
            avg2 = d2["e2e"].mean()
            f7 = px.histogram(d2, x="e2e", nbins=30, color_discrete_sequence=["#6c8ebf"])
            f7.add_vline(x=avg2, line_dash="dash", line_color="#f0a500",
                         annotation_text=f"Rata-rata {avg2:.1f}H", annotation_position="top right")
            f7.update_layout(height=280, xaxis=dict(title="Hari",**GRID),
                             yaxis=dict(title="Jumlah PR",**GRID), showlegend=False, **LAYOUT)
            st.plotly_chart(f7, use_container_width=True)

    # ── 7. Waktu per Prioritas ────────────────────────────────────────────────
    sec_btn(
        title="Waktu per Prioritas",
        sub="Apakah PR prioritas tinggi benar-benar diproses lebih cepat?",
        key="wt_prio",
        icon_path="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5m.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2",
        formula="""\
**Waktu per Prioritas**

| Prioritas | Standard SLA |
|---|---|
| Emergency | 12H (Agreement) / 48H (Non-Agreement) |
| Urgent | 24H |
| TA | 48H |
| Investasi | 48H |
| Normal | 12H (Agreement) / 57H (Non-Agreement) |

**Kalkulasi SQL:**
```sql
AVG(pr_po_days)    AS avg_pr_po,
AVG(realisasi_sla) AS avg_real,
SUM(CASE WHEN nilai_sla=1 THEN 1.0 END)/COUNT(*)*100 AS pct_ontime
GROUP BY prioritas
```
Idealnya Emergency dan Urgent lebih rendah dari Normal.
""")

    ORDER = ["Emergency","Urgent","TA","Investasi","Normal"]
    prio = df.groupby("prioritas").agg(
        avg_pr_po=("pr_po_days","mean"), avg_real=("realisasi_sla","mean"),
        total=("nilai_sla","count"),
        ontime=("nilai_sla", lambda x: (pd.to_numeric(x,errors="coerce")==1).sum()),
    ).reset_index()
    prio["pct"] = (prio["ontime"]/prio["total"]*100).round(1)
    prio["_o"]  = prio["prioritas"].apply(lambda x: ORDER.index(x) if x in ORDER else 99)
    prio = prio.sort_values("_o")

    col_l, col_r = st.columns(2)
    with col_l:
        st.caption("Rata-rata PR-PO & Realisasi SLA per Prioritas")
        f8 = go.Figure()
        f8.add_bar(x=prio["prioritas"], y=prio["avg_pr_po"], name="PR-PO (kalender)",
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
