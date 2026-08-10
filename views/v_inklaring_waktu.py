"""
v_inklaring_waktu.py - Halaman Analisis Waktu Proses Inklaring
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from utils import render_chat_analyst, format_number

KPI_CSS = """
<style>
/* Copied from v_dashboard.py for consistency */
.dash-card, div[data-testid="stPlotlyChart"] {
    border-radius: 12px !important;
    background-color: var(--secondary-background-color) !important;
    background-image: linear-gradient(rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.08)) !important;
    border: 1px solid rgba(128, 128, 128, 0.25) !important;
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08) !important;
    page-break-inside: avoid;
    break-inside: avoid;
}

.dash-card {
    border-left-width: 6px !important;
    border-left-style: solid !important;
    border-left-color: var(--text-color) !important;
    display: flex;
    align-items: center;
    gap: 14px;
    min-height: 120px !important;
    height: 100%;
    padding: 20px 18px 16px 18px;
}

div[data-testid="stPlotlyChart"] {
    overflow: hidden !important;
}

.dash-icon {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    border-radius: 10px;
    background: rgba(128, 128, 128, 0.1) !important;
    color: var(--text-color) !important;
}

.dash-body { flex: 1; min-width: 0; }

.dash-label {
    font-size: 12.5px;
    margin: 0 0 6px 0 !important;
    line-height: 1.3;
    font-weight: 500;
    color: var(--text-color) !important;
    opacity: 0.75;
}

.dash-value {
    font-size: 2rem !important;
    font-weight: 600 !important;
    margin: 0 0 4px 0 !important;
    padding: 0 !important;
    line-height: 1.1 !important;
    display: block !important;
}

.dash-delta { font-size: 12px; margin: 0; color: var(--text-color) !important; opacity: 0.6; }
.dash-delta-green { font-size: 12px; color: #09ab3b !important; margin: 0; font-weight: 600; }
.dash-delta-red   { font-size: 12px; color: #e03c3c !important; margin: 0; font-weight: 600; }
.dash-delta-orange{ font-size: 12px; color: #f0a500 !important; margin: 0; font-weight: 600; }

/* Posisi tombol popover di dalam kartu KPI */
div[data-testid="stHorizontalBlock"] > div {
    position: relative; /* Membuat setiap kolom menjadi container relatif */
}
div[data-testid="stPopover"] {
    position: absolute;
    top: 10px;
    right: 10px;
    width: 40px;
    z-index: 10;
}
</style>
"""

ICONS = {
    "file": "M4 0h5.293A1 1 0 0 1 10 .293L13.707 4a1 1 0 0 1 .293.707V14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2zm5.5 1.5v2a1 1 0 0 0 1 1h2l-3-3z",
    "check": "M10.97 4.97a.75.75 0 0 1 1.07 1.05l-3.99 4.99a.75.75 0 0 1-1.08.02L4.324 8.384a.75.75 0 1 1 1.06-1.06l2.094 2.093 3.473-4.425z M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0z",
    "target": "M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16M10.97 4.97a.235.235 0 0 0-.02.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-1.071-1.05",
    "currency": "M4 10.781c.148 1.667 1.513 2.85 3.591 3.003V15h1.043v-1.216c2.27-.179 3.678-1.438 3.678-3.3 0-1.59-.947-2.51-2.956-3.028l-.722-.187V3.467c1.122.11 1.879.714 2.07 1.616h1.47c-.166-1.6-1.54-2.748-3.54-2.875V1H7.591v1.233c-1.939.23-3.27 1.472-3.27 3.156 0 1.454.966 2.483 2.661 2.917l.61.162v4.031c-1.149-.17-1.94-.8-2.131-1.718zm3.391-3.836c-1.043-.263-1.6-.825-1.6-1.616 0-.944.704-1.641 1.8-1.828v3.495l-.2-.05zm1.591 1.872c1.287.323 1.852.859 1.852 1.769 0 1.097-.826 1.828-2.2 1.939V8.73z",
    "clock": "M8 3.5a.5.5 0 0 0-1 0V9a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0 0 .496-.868L8 8.71V3.5zM8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0z"
}

def _svg(path_d: str, size: int = 40) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'fill="currentColor" viewBox="0 0 16 16"><path d="{path_d}"/></svg>')

def _card(icon_d: str, label: str, value: str, delta: str = "", delta_type: str = "neutral") -> str:
    delta_class = {
        "green":  "dash-delta-green",
        "red":    "dash-delta-red",
        "orange": "dash-delta-orange",
    }.get(delta_type, "dash-delta")
    delta_html = f'<p class="{delta_class}">{delta}</p>' if delta else ""
    return f"""<div class="dash-card">
    <div class="dash-icon">{_svg(icon_d, 36)}</div>
    <div class="dash-body">
        <p class="dash-label">{label}</p>
        <p class="dash-value">{value}</p>{delta_html}
    </div>
</div>"""

def render(load_data, date_from=None, date_to=None, **kwargs):
    st.markdown(KPI_CSS, unsafe_allow_html=True)

    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:55px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="45" height="45" fill="currentColor" class="bi bi-clock-history" viewBox="0 0 16 16" style="margin-bottom: 8px; margin-right: 12px;">
                <path d="M8.515 1.019A7 7 0 0 0 8 1V0a8 8 0 0 1 .589.022zm2.004.45a7 7 0 0 0-.985-.299l.219-.976q.576.129 1.126.342zm1.37.71a7 7 0 0 0-.439-.27l.493-.87a8 8 0 0 1 .979.654l-.615.789a7 7 0 0 0-.418-.302zm1.834 1.79a7 7 0 0 0-.653-.796l.724-.69q.406.429.747.91zm.744 1.352a7 7 0 0 0-.214-.468l.893-.45a8 8 0 0 1 .45 1.088l-.95.313a7 7 0 0 0-.179-.483m.53 2.507a7 7 0 0 0-.1-1.025l.985-.17q.1.58.116 1.17zm-.131 1.538q.05-.254.081-.51l.993.123a8 8 0 0 1-.23 1.155l-.964-.267q.069-.247.12-.501m-.952 2.379q.276-.436.486-.908l.914.405q-.24.54-.555 1.038zm-.964 1.205q.183-.183.35-.378l.758.653a8 8 0 0 1-.401.432z"/>
                <path d="M8 1a7 7 0 1 0 4.95 11.95l.707.707A8.001 8.001 0 1 1 8 0z"/>
                <path d="M7.5 3a.5.5 0 0 1 .5.5v5.21l3.248 1.856a.5.5 0 0 1-.496.868l-3.5-2A.5.5 0 0 1 7 9V3.5a.5.5 0 0 1 .5-.5"/>
            </svg>
            Analisis Waktu Proses Inklaring
        </h1>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # Load data
    date_filter = ""
    if date_from and date_to:
        start_str = date_from.strftime('%Y-%m-%d')
        end_str = date_to.strftime('%Y-%m-%d')
        date_filter = f"WHERE tgl_eta >= '{start_str}' AND tgl_eta <= '{end_str}'"

    query = f"""
        SELECT 
            tgl_pib, aju_pib, no_aju, nama_kapal, 
            start_bongkar, selesai_bongkar, tgl_sppb
        FROM inklaring_impor
        {date_filter}
    """

    with st.spinner("Memuat data waktu..."):
        df = load_data(query)

    if df.empty:
        st.warning("Tidak ada data Inklaring pada rentang waktu ini.")
        return

    date_cols = ['tgl_pib', 'start_bongkar', 'selesai_bongkar', 'tgl_sppb']
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    # == PANDAS DATA TRANSFORMATIONS ==========================
    df['Lama_Bongkar_Hari'] = (df['selesai_bongkar'] - df['start_bongkar']).dt.total_seconds() / (24 * 3600)
    df['Bebas_Hari'] = (df['tgl_sppb'] - df['selesai_bongkar'].dt.normalize()).dt.days
    df['Waiting_Time'] = (df['start_bongkar'].dt.normalize() - df['tgl_pib']).dt.days

    avg_bebas = df['Bebas_Hari'].mean()
    avg_waiting = df['Waiting_Time'].mean()
    avg_bongkar = df['Lama_Bongkar_Hari'].mean()

    # Rincian angka nominal (total selisih hari / jumlah dokumen = rata-rata)
    # untuk ditampilkan di popover formula, contoh: "-160 / 68 = -2,35 Hari".
    # (Selaras dengan v_inklaring_dashboard.py)
    def _sum_count_avg(value_col):
        valid = df[value_col].dropna()
        total = valid.sum()
        count = valid.count()
        avg = total / count if count > 0 else float('nan')
        fmt_num = lambda v: format_number(v, decimals=2) if pd.notna(v) else "-"
        total_str = f"{total:,.0f}".replace(",", ".")
        return f"{total_str} / {count} = {fmt_num(avg)} Hari"

    detail_bebas_hari = _sum_count_avg('Bebas_Hari')
    detail_waiting = _sum_count_avg('Waiting_Time')
    detail_bongkar = _sum_count_avg('Lama_Bongkar_Hari')
    
    # == KPI CARDS ============================================
    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:24px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-graph-up" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                <path fill-rule="evenodd" d="M0 0h1v15h15v1H0zm14.817 3.113a.5.5 0 0 1 .07.704l-4.5 5.5a.5.5 0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5 0 0 1 .758-.06l2.609 2.61 4.15-5.073a.5.5 0 0 1 .704-.07"/>
            </svg>
            Key Performance Indicators Waktu Inklaring
        </h1>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        val1 = f"{format_number(avg_bebas, decimals=1)} Hari" if pd.notna(avg_bebas) else "-"
        st.markdown(_card(ICONS["clock"], "Rata-rata Bebas (Hari)", val1, "Tgl SPPB - Selesai Bongkar", "neutral"), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Lihat Formula"):
            st.info(
                "**Rata-rata Bebas (Hari)**: Rata-rata selisih hari dari Selesai Bongkar hingga Tgl SPPB diterbitkan.\n\n"
                f"Total Selisih Hari / Jumlah Dokumen = Rata-rata:\n"
                f"**{detail_bebas_hari}**"
            )
    with col2:
        val2 = f"{format_number(avg_waiting, decimals=1)} Hari" if pd.notna(avg_waiting) else "-"
        st.markdown(_card(ICONS["clock"], "Rata-rata Waiting Time", val2, "Start Bongkar - Tgl PIB", "neutral"), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Lihat Formula"):
            st.info(
                "**Rata-rata Waiting Time**: Rata-rata selisih hari dari Tgl PIB hingga Start Bongkar.\n\n"
                f"Total Selisih Hari / Jumlah Dokumen = Rata-rata:\n"
                f"**{detail_waiting}**"
            )
    with col3:
        val3 = f"{format_number(avg_bongkar, decimals=1)} Hari" if pd.notna(avg_bongkar) else "-"
        st.markdown(_card(ICONS["clock"], "Rata-rata Waktu Proses Bongkar", val3, "Selesai Bongkar - Start Bongkar", "neutral"), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Lihat Formula"):
            st.info(
                "**Rata-rata Waktu Proses Bongkar**: Rata-rata selisih hari dari Start Bongkar hingga Selesai Bongkar.\n\n"
                f"Total Selisih Hari / Jumlah Dokumen = Rata-rata:\n"
                f"**{detail_bongkar}**"
            )

    st.markdown("---")

    # == 3 NEW BAR CHARTS (BEBAS, WAITING, BONGKAR) ============
    df['Kapal_Label'] = df['nama_kapal'].fillna('-').astype(str) + ' - AJU ' + df['no_aju'].fillna('-').astype(str)
    
    col_c1, col_c2 = st.columns(2)
    
    with col_c1:
        title_col, btn_col = st.columns([19, 1])
        with title_col:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:24px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                        <path d="M1 11a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1zm5-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1zm5-5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1z"/>
                    </svg>
                    Bebas Hari per Kapal (Terlama)
                </h1>
            """, unsafe_allow_html=True)
        with btn_col:
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Lihat Formula"):
                st.info("**Bebas Hari**: Tgl SPPB - Selesai Bongkar (Hari).\nMenampilkan maksimal 15 kapal dengan durasi bebas hari terlama.")
        st.caption("15 kapal dengan waktu bebas terlama.")
        
        df_bebas = df.dropna(subset=['Bebas_Hari']).nlargest(15, 'Bebas_Hari').sort_values('Bebas_Hari', ascending=True)
        if not df_bebas.empty:
            fig_bebas = px.bar(df_bebas, x='Bebas_Hari', y='Kapal_Label', orientation='h', text_auto='.1f', color_discrete_sequence=['#1f77b4'])
            fig_bebas.update_layout(margin=dict(t=20, b=20, l=20, r=20), xaxis_title="Hari", yaxis_title="")
            st.plotly_chart(fig_bebas, use_container_width=True)
        else:
            st.info("Tidak ada data Bebas Hari yang tersedia.")

    with col_c2:
        title_col, btn_col = st.columns([19, 1])
        with title_col:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:24px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                        <path d="M1 11a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1zm5-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1zm5-5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1z"/>
                    </svg>
                    Waiting Time per Kapal (Terlama)
                </h1>
            """, unsafe_allow_html=True)
        with btn_col:
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Lihat Formula"):
                st.info("**Waiting Time**: Start Bongkar - Tgl PIB (Hari).\nMenampilkan maksimal 15 kapal dengan durasi waktu tunggu terlama.")
        st.caption("15 kapal dengan waktu tunggu (waiting time) terlama.")
        
        df_wait = df.dropna(subset=['Waiting_Time']).nlargest(15, 'Waiting_Time').sort_values('Waiting_Time', ascending=True)
        if not df_wait.empty:
            fig_wait = px.bar(df_wait, x='Waiting_Time', y='Kapal_Label', orientation='h', text_auto='.1f', color_discrete_sequence=['#d62728'])
            fig_wait.update_layout(margin=dict(t=20, b=20, l=20, r=20), xaxis_title="Hari", yaxis_title="")
            st.plotly_chart(fig_wait, use_container_width=True)
        else:
            st.info("Tidak ada data Waiting Time yang tersedia.")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    title_col, btn_col = st.columns([19, 1])
    with title_col:
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:24px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                    <path d="M1 11a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1zm5-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1zm5-5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1z"/>
                </svg>
                Waktu Proses Bongkar per Kapal (Terlama)
            </h1>
        """, unsafe_allow_html=True)
    with btn_col:
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Lihat Formula"):
            st.info("**Waktu Proses Bongkar**: Selesai Bongkar - Start Bongkar (Hari).\nMenampilkan maksimal 15 kapal dengan durasi waktu bongkar terlama.")
    st.caption("15 kapal dengan proses bongkar muat terlama.")
    
    df_bongkar = df.dropna(subset=['Lama_Bongkar_Hari']).nlargest(15, 'Lama_Bongkar_Hari').sort_values('Lama_Bongkar_Hari', ascending=True)
    if not df_bongkar.empty:
        fig_bongkar = px.bar(df_bongkar, x='Lama_Bongkar_Hari', y='Kapal_Label', orientation='h', text_auto='.1f', color_discrete_sequence=['#2ca02c'])
        fig_bongkar.update_layout(margin=dict(t=20, b=20, l=20, r=20), xaxis_title="Hari", yaxis_title="", height=350)
        st.plotly_chart(fig_bongkar, use_container_width=True)
    else:
        st.info("Tidak ada data Waktu Proses Bongkar yang tersedia.")

    st.markdown("---")

    # == GANTT CHART TIMELINE =================================
    title_col, btn_col = st.columns([19, 1])
    with title_col:
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:30px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-view-list" viewBox="0 0 16 16" style="margin-bottom: 6px; margin-right: 8px;">
                    <path d="M3 4.5h10a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2zm0 1a1 1 0 0 0-1 1v3a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-3a1 1 0 0 0-1-1H3zM1 2a.5.5 0 0 1 .5-.5h13a.5.5 0 0 1 0 1h-13A.5.5 0 0 1 1 2zm0 12a.5.5 0 0 1 .5-.5h13a.5.5 0 0 1 0 1h-13A.5.5 0 0 1 1 14z"/>
                </svg>
                Timeline Operasional (Waiting Time & Bongkar)
            </h1>
        """, unsafe_allow_html=True)
    with btn_col:
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Lihat Formula"):
            st.info("""\
**Timeline Operasional (Waiting Time & Bongkar)**: Gantt Chart yang memvisualisasikan perjalanan waktu setiap kapal.

**Logika Visual:**
- Garis **Merah (Waiting Time)**: Dihitung dari tanggal `Tgl PIB` hingga waktu `Start Bongkar`. Menunjukkan durasi kapal menunggu izin atau antrian sandar.
- Garis **Biru (Proses Bongkar)**: Dihitung dari waktu `Start Bongkar` hingga `Selesai Bongkar`. Menunjukkan durasi nyata operasional bongkar muat.
""")
    st.caption("Timeline durasi waktu tunggu (dari PIB diterbitkan) hingga selesai bongkar muat per dokumen.")
    
    # Siapkan data untuk Timeline (Gantt)
    df_timeline = df.dropna(subset=['tgl_pib', 'start_bongkar', 'selesai_bongkar']).copy()
    
    if not df_timeline.empty:
        # Kita hanya ambil 15 data terbaru agar chart tidak terlalu sesak (opsional)
        df_timeline = df_timeline.sort_values('tgl_pib', ascending=False).head(15)
        
        # Label Nama Kapal + AJU
        df_timeline['Kapal_Label'] = df_timeline['nama_kapal'].fillna('-').astype(str) + ' - AJU ' + df_timeline['no_aju'].fillna('-').astype(str)
        
        timeline_data = []
        for _, row in df_timeline.iterrows():
            # 1. Fase Waiting Time
            if pd.notna(row['tgl_pib']) and pd.notna(row['start_bongkar']):
                timeline_data.append({
                    'No AJU': row['Kapal_Label'],
                    'Tahap': 'Waiting Time',
                    'Start': row['tgl_pib'],
                    'Finish': row['start_bongkar']
                })
            
            # 2. Fase Proses Bongkar
            if pd.notna(row['start_bongkar']) and pd.notna(row['selesai_bongkar']):
                timeline_data.append({
                    'No AJU': row['Kapal_Label'],
                    'Tahap': 'Proses Bongkar',
                    'Start': row['start_bongkar'],
                    'Finish': row['selesai_bongkar']
                })
        
        df_gantt = pd.DataFrame(timeline_data)
        
        # Mapping warna
        color_discrete_map = {'Waiting Time': '#d62728', 'Proses Bongkar': '#1f77b4'}
        
        fig_gantt = px.timeline(
            df_gantt, 
            x_start="Start", 
            x_end="Finish", 
            y="No AJU", 
            color="Tahap",
            color_discrete_map=color_discrete_map,
            hover_data={"No AJU": True, "Tahap": True, "Start": "|%d %b %Y %H:%M", "Finish": "|%d %b %Y %H:%M"}
        )
        
        fig_gantt.update_yaxes(autorange="reversed")
        fig_gantt.update_layout(
            barmode='group',
            margin=dict(t=20, b=20, l=20, r=20),
            legend_title_text="",
            xaxis_title="Tanggal Operasional",
            height=400 + (len(df_timeline) * 15)
        )
        st.plotly_chart(fig_gantt, use_container_width=True)
    else:
        st.info("Data Tanggal PIB, Start Bongkar, atau Selesai Bongkar tidak lengkap untuk merender timeline.")

    st.markdown("---")

    # Konteks AI
    info_filter = kwargs.get('info_filter', 'Filter tanggal default aktif')
    konteks_lines = ["## RINGKASAN WAKTU INKLARING", f"- Filter Aktif: {info_filter}"]
    konteks_lines.append(f"- Rata-rata Bebas: {avg_bebas:.1f} Hari" if pd.notna(avg_bebas) else "- Rata-rata Bebas: -")
    konteks_lines.append(f"- Rata-rata Waiting Time: {avg_waiting:.1f} Hari" if pd.notna(avg_waiting) else "- Rata-rata Waiting Time: -")
    konteks_lines.append(f"- Rata-rata Waktu Proses Bongkar: {avg_bongkar:.1f} Hari" if pd.notna(avg_bongkar) else "- Rata-rata Waktu Proses Bongkar: -")
    
    if not df_timeline.empty:
        konteks_lines.append("- Menampilkan timeline 15 kapal terbaru berdasarkan Tanggal PIB.")
        konteks_lines.append(df_timeline[['Kapal_Label', 'tgl_pib', 'start_bongkar', 'selesai_bongkar', 'tgl_sppb']].to_csv(index=False))

    suplemen = "\n".join(konteks_lines)
    konteks_final = kwargs.get("global_context", "") + "\n---\n" + suplemen

    with st.expander("Tanya ke Melati (Monitoring, Evaluasi, Laporan Terintegrasi)"):
        render_chat_analyst(
            konteks_data_teks=konteks_final,
            nama_halaman="Analisis Waktu Proses Inklaring",
            load_data_fn=load_data,
        )