"""
v_inklaring_dashboard.py - Halaman Dashboard Inklaring Barang Impor
"""
import streamlit as st
import pandas as pd
import numpy as np
import io
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from utils import render_chat_analyst, format_number, format_idr, format_idr_short, idr_axis

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

    # == HEADER ===============================================================
    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:60px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" fill="currentColor" class="bi bi-box-seam-fill" viewBox="0 0 16 16" style="margin-bottom: 10px; margin-right: 8px;">
                <path d="M10 .5a.5.5 0 0 0-.5-.5h-3a.5.5 0 0 0-.5.5.5.5 0 0 1-.5.5.5.5 0 0 0-.5.5V2a.5.5 0 0 0 .5.5h5A.5.5 0 0 0 11 2v-.5a.5.5 0 0 0-.5-.5.5.5 0 0 1-.5-.5"/>
                <path d="M4.085 1H3.5A1.5 1.5 0 0 0 2 2.5v12A1.5 1.5 0 0 0 3.5 16h9a1.5 1.5 0 0 0 1.5-1.5v-12A1.5 1.5 0 0 0 12.5 1h-.585q.084.236.085.5V2a1.5 1.5 0 0 1-1.5 1.5h-5A1.5 1.5 0 0 1 4 2v-.5q.001-.264.085-.5M10 7a1 1 0 1 1 2 0v5a1 1 0 1 1-2 0zm-6 4a1 1 0 1 1 2 0v1a1 1 0 1 1-2 0zm4-3a1 1 0 0 1 1 1v3a1 1 0 1 1-2 0V9a1 1 0 0 1 1-1"/>
            </svg>
            Dashboard Inklaring Impor
        </h1>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # == FILTER TANGGAL =======================================================
    date_filter = ""
    if date_from and date_to:
        start_str = date_from.strftime('%Y-%m-%d')
        end_str = date_to.strftime('%Y-%m-%d')
        date_filter = f"WHERE tgl_eta >= '{start_str}' AND tgl_eta <= '{end_str}'"

    # == LOAD DATA ============================================================
    query = f"""
        SELECT 
            id as no, tgl_pib, aju_pib, no_aju, sap, nama_kapal, tgl_eta, 
            quantity_mt, komoditi, pemasok, asal_negara, 
            bea_masuk_rp, ppn_rp, pph_rp, 
            start_bongkar, selesai_bongkar, spjm, status, tgl_sppb
        FROM inklaring_impor
        {date_filter}
    """
    
    with st.spinner("Menghitung KPI dan merender dashboard..."):
        df = load_data(query)

    if df.empty:
        st.warning("Tidak ada data Inklaring pada rentang waktu ini.")
        return

    # == PANDAS DATA TRANSFORMATIONS (RUMUS EXCEL) =============================
    
    date_cols = ['tgl_pib', 'tgl_eta', 'start_bongkar', 'selesai_bongkar', 'tgl_sppb']
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')
        
    num_cols = ['bea_masuk_rp', 'ppn_rp', 'pph_rp', 'quantity_mt']
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df['TOTAL_BIAYA'] = df['bea_masuk_rp'] + df['ppn_rp'] + df['pph_rp']
    df['Lama_Bongkar_Hari'] = (df['selesai_bongkar'] - df['start_bongkar']).dt.total_seconds() / (24 * 3600)
    df['Bebas_Hari'] = (df['tgl_sppb'] - df['selesai_bongkar'].dt.normalize()).dt.days

    is_hijau_mask = df['spjm'].fillna('').astype(str).str.strip().isin(['', '0', '0.0'])
    df['Keterangan_Jalur'] = np.where(is_hijau_mask, 'HIJAU', 'MERAH')

    df['Check_List'] = df['status'].astype(str).str.lower().isin(['done', 'selesai', 'pib selesai', 'pib_selesai'])

    df['SLA_Target'] = np.where(df['komoditi'] == 'SA', 15, 
                                np.where(df['Keterangan_Jalur'] == 'MERAH', 8, 0))

    df['Score_SLA'] = np.where(
        df['Bebas_Hari'].isna() | (df['Bebas_Hari'] == 0), 
        0, 
        np.where(df['SLA_Target'] >= df['Bebas_Hari'], 1, 0)
    )

    df['Waiting_Time'] = (df['start_bongkar'].dt.normalize() - df['tgl_pib']).dt.days

    total_data = len(df)
    total_score_1 = (df['Score_SLA'] == 1).sum()
    persen_sla_epp = (total_score_1 / total_data) * 100 if total_data > 0 else 0

    pib_selesai = df['tgl_sppb'].notna().sum()
    pib_on_progress = total_data - pib_selesai

    # == METRICS CARDS (ROW 1) =================================================
    st.markdown("""
        <h1 style='display: flex; align-items: center;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor" class="bi bi-graph-up" viewBox="0 0 16 16" style="margin-bottom: 8px; margin-right: 8px;">
                <path fill-rule="evenodd" d="M0 0h1v15h15v1H0zm14.817 3.113a.5.5 0 0 1 .07.704l-4.5 5.5a.5.5 0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5 0 0 1 .758-.06l2.609 2.61 4.15-5.073a.5.5 0 0 1 .704-.07"/>
            </svg>
            Key Performance Indicators
        </h1>
    """, unsafe_allow_html=True)

    total_biaya_sum = df['TOTAL_BIAYA'].sum()
    avg_waiting = df['Waiting_Time'].mean()
    avg_bongkar = df['Lama_Bongkar_Hari'].mean()
    avg_bebas_hari = df['Bebas_Hari'].mean()

    KPI_DASH = [
        {
            "key": "kpi_total_pib",
            "icon": "file",
            "label": "Total PIB",
            "value": f"{format_number(total_data)}",
            "delta": "Kapal",
            "dtype": "neutral",
            "formula": "Jumlah total PIB pada periode filter."
        },
        {
            "key": "kpi_pib_selesai",
            "icon": "check",
            "label": "PIB Selesai",
            "value": f"{format_number(pib_selesai)}",
            "delta": f"{format_number(pib_on_progress)} On Progress",
            "dtype": "neutral",
            "formula": "Jumlah dokumen PIB yang Tanggal SPPB-nya sudah terisi. Dokumen On Progress adalah selisih Total PIB dengan PIB Selesai."
        },
        {
            "key": "kpi_kinerja_sla",
            "icon": "target",
            "label": "Kinerja SLA EPP",
            "value": f"{format_number(persen_sla_epp, decimals=2)}%",
            "delta": "Target: > 80%",
            "dtype": "green" if persen_sla_epp >= 80 else "red",
            "formula": "Persentase dokumen dengan Score SLA = 1 dibagi total dokumen."
        },
        {
            "key": "kpi_avg_bebas",
            "icon": "clock",
            "label": "Rata-rata Bebas (Hari)",
            "value": f"{format_number(avg_bebas_hari, decimals=2)} Hari" if pd.notna(avg_bebas_hari) else "-",
            "delta": "Tgl SPPB - Selesai Bongkar",
            "dtype": "neutral",
            "formula": "Rata-rata selisih hari dari Selesai Bongkar hingga Tgl SPPB diterbitkan."
        },
        {
            "key": "kpi_avg_waiting",
            "icon": "clock",
            "label": "Rata-rata Waiting Time",
            "value": f"{format_number(avg_waiting, decimals=2)} Hari" if pd.notna(avg_waiting) else "-",
            "delta": "Start Bongkar - Tgl PIB",
            "dtype": "neutral",
            "formula": "Rata-rata selisih hari dari Tgl PIB hingga Start Bongkar."
        },
        {
            "key": "kpi_avg_bongkar",
            "icon": "clock",
            "label": "Rata-rata Waktu Proses Bongkar",
            "value": f"{format_number(avg_bongkar, decimals=2)} Hari" if pd.notna(avg_bongkar) else "-",
            "delta": "Selesai Bongkar - Start Bongkar",
            "dtype": "neutral",
            "formula": "Rata-rata selisih hari dari Start Bongkar hingga Selesai Bongkar."
        },
        {
            "key": "kpi_total_biaya",
            "icon": "currency",
            "label": "Total Biaya",
            "value": f"{format_idr(total_biaya_sum)}",
            "delta": "Bea Masuk + PPN + PPH",
            "dtype": "neutral",
            "formula": "Total nilai Bea Masuk + PPN + PPH dari seluruh dokumen pada periode filter."
        }
    ]

    def render_kpi_row(items):
        cols = st.columns(3)
        for i, col in enumerate(cols):
            with col:
                if i >= len(items):
                    continue
                kpi = items[i]
                delta_arrow = ""
                delta_text = f"{delta_arrow}{kpi['delta']}" if kpi['delta'] else ""
                
                st.markdown(_card(ICONS[kpi["icon"]], kpi["label"], kpi["value"], delta_text, kpi["dtype"]), unsafe_allow_html=True)
                with st.popover(":material/visibility:", help="Lihat Formula"):
                    st.info(kpi["formula"])

    for row_start in range(0, len(KPI_DASH), 3):
        row_items = KPI_DASH[row_start:row_start + 3]
        render_kpi_row(row_items)
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    st.markdown("---")

    # == CHARTS (ROW 2) ========================================================
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        title_col, btn_col = st.columns([9, 1])
        with title_col:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:30px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-pie-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 6px; margin-right: 8px;">
                        <path d="M15.985 8.5H8.207l-5.5 5.5a8 8 0 0 0 13.277-5.5zM2 13.292A8 8 0 0 1 7.5.015v7.778l-5.5 5.5zM8.5.015V7.5h7.485A8.001 8.001 0 0 0 8.5.015z"/>
                    </svg>
                    Proporsi Keterangan Jalur
                </h1>
            """, unsafe_allow_html=True)
        with btn_col:
            st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Lihat Formula"):
                st.info("""\
**Proporsi Keterangan Jalur**: Pie chart distribusi jumlah dokumen impor berdasarkan jalur merah dan jalur hijau.

**Formula Excel:**
- `Jalur Merah` = Jika kolom SPJM berisi teks (seperti tanggal) atau angka selain 0.
- `Jalur Hijau` = Jika kolom SPJM kosong, berisi 0, atau teks '0'.
                """)
        st.caption("Distribusi dokumen impor berdasarkan jalur.")

        jalur_count = df['Keterangan_Jalur'].value_counts().reset_index()
        jalur_count.columns = ['Jalur', 'Jumlah']
        
        color_map = {'MERAH': '#d62728', 'HIJAU': '#2ca02c'}
        
        fig_jalur = px.pie(
            jalur_count, names='Jalur', values='Jumlah', hole=0.4,
            color='Jalur', color_discrete_map=color_map
        )
        fig_jalur.update_layout(margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig_jalur, use_container_width=True)

    with col_chart2:
        title_col, btn_col = st.columns([9, 1])
        with title_col:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:30px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 6px; margin-right: 8px;">
                        <path d="M11 2a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v12h.5a.5.5 0 0 1 0 1H.5a.5.5 0 0 1 0-1H1v-3a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3h1V7a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v7h1z"/>
                    </svg>
                    Total Volume Impor per Komoditi
                </h1>
            """, unsafe_allow_html=True)
        with btn_col:
            st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Lihat Formula"):
                st.info("""\
**Total Volume Impor per Komoditi**: Bar chart horizontal total volume (dalam Metric Ton) dari setiap komoditi yang diimpor.
                """)
        st.caption("Total volume dari setiap komoditi.")

        vol_komoditi = df.groupby('komoditi')['quantity_mt'].sum().reset_index()
        vol_komoditi = vol_komoditi.sort_values('quantity_mt', ascending=True)
        
        fig_vol = px.bar(
            vol_komoditi, x='quantity_mt', y='komoditi', orientation='h',
            text_auto='.2s', color_discrete_sequence=['#1f77b4']
        )
        fig_vol.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
            xaxis_title="Quantity (Metric Ton)", yaxis_title=""
        )
        st.plotly_chart(fig_vol, use_container_width=True)

    st.markdown("---")

    # --- ROW 3: PETA DUNIA ASAL NEGARA ---
    title_col_map, btn_col_map = st.columns([19, 1])
    with title_col_map:
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:30px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-globe-americas" viewBox="0 0 16 16" style="margin-bottom: 6px; margin-right: 8px;">
                    <path d="M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0M2.04 4.326c.325 1.329 2.532 2.54 3.717 3.19.48.263.793.434.743.484-.08.08-.162.158-.242.234-.416.416-.682.906-.682 1.484 0 .578.266 1.068.682 1.484.416.416.906.682 1.484.682.578 0 1.068-.266 1.484-.682.416-.416.682-.906.682-1.484 0-.578-.266-1.068-.682-1.484a6.7 6.7 0 0 0-.242-.234c-.05-.05-.263-.22-.743-.484.325-1.329 2.532-2.54 3.717-3.19.48-.263.793-.434.743-.484-.08-.08-.162-.158-.242-.234a1.5 1.5 0 0 0-.682-1.484 6.7 6.7 0 0 0-1.484-.682c-.578 0-1.068.266-1.484.682-.416.416-.682.906-.682 1.484 0 .578.266 1.068.682 1.484.416.416.906.682 1.484.682.578 0 1.068-.266 1.484-.682.416-.416.682-.906.682-1.484 0-.578-.266-1.068-.682-1.484a6.7 6.7 0 0 0-1.484-.682c-.578 0-1.068.266-1.484.682z"/>
                </svg>
                Peta Asal Negara Impor
            </h1>
        """, unsafe_allow_html=True)
    with btn_col_map:
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Lihat Formula"):
            st.info("""\
**Peta Asal Negara Impor**: Peta dunia yang menunjukkan negara asal barang impor.

**Logika Visual:**
- Setiap negara asal direpresentasikan oleh sebuah lingkaran.
- Ukuran lingkaran proporsional dengan jumlah dokumen impor (PIB) dari negara tersebut. Semakin besar lingkaran, semakin banyak impor dari negara itu.
""")
    st.caption("Distribusi geografis asal barang impor. Ukuran lingkaran menunjukkan frekuensi impor.")

    # 1. Standardisasi Data (Semuanya dipaksa ke UPPERCASE untuk pencarian)
    # Ini memastikan 'Singapore', 'SINGAPORE', dan 'singapura' diperlakukan sama.
    df_map = df.copy()
    df_map['asal_negara_clean'] = df_map['asal_negara'].fillna('UNKNOWN').str.strip().str.upper()

    # 2. Definisikan Mapping Nama Tampilan dan Koordinat
    # Key harus UPPERCASE agar cocok dengan asal_negara_clean
    geo_master = {
        'VIETNAM': {'name': 'Vietnam', 'lat': 14.0583, 'lon': 108.2772},
        'CHINA': {'name': 'China', 'lat': 35.8617, 'lon': 104.1954},
        'RRC': {'name': 'China', 'lat': 35.8617, 'lon': 104.1954},
        'SINGAPORE': {'name': 'Singapore', 'lat': 1.3521, 'lon': 103.8198},
        'SINGAPURA': {'name': 'Singapore', 'lat': 1.3521, 'lon': 103.8198},
        'TAIWAN': {'name': 'Taiwan', 'lat': 23.6978, 'lon': 120.9605},
        'TAIWAN, PROVINCE OF CHINA': {'name': 'Taiwan', 'lat': 23.6978, 'lon': 120.9605},
        'UNITED ARAB EMIRATES': {'name': 'UAE', 'lat': 23.4241, 'lon': 53.8478},
        'UAE': {'name': 'UAE', 'lat': 23.4241, 'lon': 53.8478},
        'RUSIA': {'name': 'Russia', 'lat': 61.5240, 'lon': 105.3188},
        'RUSSIAN FEDERATION': {'name': 'Russia', 'lat': 61.5240, 'lon': 105.3188},
        'KOREA': {'name': 'South Korea', 'lat': 35.9078, 'lon': 127.7669},
        'SOUTH KOREA': {'name': 'South Korea', 'lat': 35.9078, 'lon': 127.7669},
        'MESIR': {'name': 'Egypt', 'lat': 26.8206, 'lon': 30.8025},
        'EGYPT': {'name': 'Egypt', 'lat': 26.8206, 'lon': 30.8025},
        'UNITED STATES': {'name': 'USA', 'lat': 37.0902, 'lon': -95.7129},
        'USA': {'name': 'USA', 'lat': 37.0902, 'lon': -95.7129},
        'UNITED STATES OF AMERICA': {'name': 'USA', 'lat': 37.0902, 'lon': -95.7129},
        'JORDAN': {'name': 'Jordan', 'lat': 31.2407, 'lon': 36.5115},
        'QATAR': {'name': 'Qatar', 'lat': 25.3548, 'lon': 51.1839},
        'CANADA': {'name': 'Canada', 'lat': 56.1304, 'lon': -106.3468},
        'KANADA': {'name': 'Canada', 'lat': 56.1304, 'lon': -106.3468},
        'MOROCCO': {'name': 'Morocco', 'lat': 31.7917, 'lon': -7.0926},
        'MAROKO': {'name': 'Morocco', 'lat': 31.7917, 'lon': -7.0926},
        'KUWAIT': {'name': 'Kuwait', 'lat': 29.3117, 'lon': 47.4818},
    }

    # 3. Terapkan Master Data ke Dataframe
    df_map['display_name'] = df_map['asal_negara_clean'].map(lambda x: geo_master.get(x, {}).get('name', x))
    df_map['lat'] = df_map['asal_negara_clean'].map(lambda x: geo_master.get(x, {}).get('lat'))
    df_map['lon'] = df_map['asal_negara_clean'].map(lambda x: geo_master.get(x, {}).get('lon'))

    # Agregasi data berdasarkan display_name dan koordinat
    country_counts = df_map.groupby(['display_name', 'lat', 'lon']).size().reset_index(name='count')

    # DEBUG: Cek jika ada negara yang tidak punya koordinat
    unknown_countries = df_map[df_map['lat'].isna()]['asal_negara_clean'].unique()
    if len(unknown_countries) > 0:
        st.warning(f"Negara berikut tidak memiliki koordinat di geo_master: {', '.join(unknown_countries)}")

    # 4. Buat Peta
    fig_map = px.scatter_geo(
        country_counts, 
        lat="lat", 
        lon="lon",
        size="count", 
        hover_name="display_name", 
        hover_data={"count": True, "lat": False, "lon": False},
        projection="natural earth", 
        color="display_name",
        size_max=40
    )

    fig_map.update_layout(
        height=450, margin={"r":0,"t":10,"l":0,"b":0},
        geo=dict(
            showcoastlines=True, coastlinecolor="rgba(128,128,128,0.3)",
            showcountries=True, countrycolor="rgba(128,128,128,0.3)",
            showland=True, landcolor="rgba(128,128,128,0.08)",
            showocean=True, oceancolor="rgba(31,119,180,0.1)",
            bgcolor='rgba(0,0,0,0)'
        ), paper_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )

    fig_map.update_traces(marker=dict(sizemin=12, line=dict(width=0)))
    st.plotly_chart(fig_map, use_container_width=True)

    # == CHARTS (ROW 3) ========================================================
    st.markdown("---")
    title_col2, btn_col2 = st.columns([19, 1])
    with title_col2:
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:30px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-bar-chart-steps" viewBox="0 0 16 16" style="margin-bottom: 6px; margin-right: 8px;">
                    <path d="M.5 0a.5.5 0 0 1 .5.5v15a.5.5 0 0 1-1 0V.5A.5.5 0 0 1 .5 0zM2 1.5a.5.5 0 0 1 .5-.5h4a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-4a.5.5 0 0 1-.5-.5v-1zm2 4a.5.5 0 0 1 .5-.5h7a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-7a.5.5 0 0 1-.5-.5v-1zm2 4a.5.5 0 0 1 .5-.5h6a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-6a.5.5 0 0 1-.5-.5v-1zm2 4a.5.5 0 0 1 .5-.5h7a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-7a.5.5 0 0 1-.5-.5v-1z"/>
                </svg>
                Top 10 PIB dengan Total Biaya Terbesar
            </h1>
        """, unsafe_allow_html=True)
    with btn_col2:
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Lihat Formula"):
            st.info("""\
**Top 10 PIB dengan Total Biaya Terbesar**: Stacked bar chart menampilkan 10 dokumen dengan pengeluaran pajak tertinggi.

**Formula Excel:**
- `Total Biaya` = Bea Masuk (Rp) + PPN + PPH.
""")
    st.caption("10 dokumen impor dengan nilai pengeluaran pajak terbesar, dirincikan berdasarkan komposisi jenis pajaknya.")

    df_top10 = df.nlargest(10, 'TOTAL_BIAYA').copy()

    df_top10['Label'] = df_top10['nama_kapal'].fillna('-').astype(str) + ' - AJU ' + df_top10['no_aju'].fillna('-').astype(str)
    
    df_top10_chart = df_top10.rename(columns={
        'bea_masuk_rp': 'Bea Masuk (Rp)',
        'ppn_rp': 'PPN',
        'pph_rp': 'PPH'
    })

    fig_top10 = px.bar(
        df_top10_chart, 
        x='Label', 
        y=['Bea Masuk (Rp)', 'PPN', 'PPH'],
        labels={'value': 'Total Biaya (Rupiah)', 'variable': 'Jenis Pajak', 'Label': 'Dokumen Impor'},
        color_discrete_sequence=['#1f77b4', '#ff7f0e', '#2ca02c'],
        category_orders={"variable": ["Bea Masuk (Rp)", "PPN", "PPH"]}
    )
    
    max_top10_val = df_top10['TOTAL_BIAYA'].max()
    fig_top10.update_layout(
        barmode='group',
        margin=dict(t=20, b=20, l=20, r=20),
        legend_title_text="Jenis Pajak",
        hovermode="x unified",
        xaxis_tickangle=-45,
        xaxis_type='category', 
        yaxis=idr_axis(max_top10_val)
    )
    
    fig_top10.update_traces(
        hovertemplate="<b>%{x}</b><br>Nilai: Rp %{y:,.0f}<extra></extra>"
    )

    st.plotly_chart(fig_top10, use_container_width=True)

    # == TABEL RINCIAN SLA =====================================================
    st.markdown("---")
    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:30px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-table" viewBox="0 0 16 16" style="margin-bottom: 6px; margin-right: 8px;">
                <path d="M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2zm15 2h-4v3h4zm0 4h-4v3h4zm0 4h-4v3h3a1 1 0 0 0 1-1zm-5 3v-3H6v3zm-5 0v-3H1v2a1 1 0 0 0 1 1zm-4-4h4V8H1zm0-4h4V4H1zm5-3v3h4V4zm4 4H6v3h4z"/>
            </svg>
            Tabel Rincian SLA per Kapal
        </h1>
    """, unsafe_allow_html=True)

    df_sla = df[['no_aju', 'nama_kapal', 'komoditi', 'Keterangan_Jalur', 
                 'SLA_Target', 'Bebas_Hari', 'Score_SLA', 'Check_List']].copy()
    
    df_sla['Check_List'] = df_sla['Check_List'].apply(lambda x: "✅ Selesai" if x else "⏳ Proses")
    df_sla['Score_SLA'] = df_sla['Score_SLA'].apply(lambda x: "⭐ Memenuhi (1)" if x == 1 else "❌ Melampaui (0)")
    
    df_sla.index = df_sla.index + 1
    df_sla.columns = ['No AJU', 'Nama Kapal', 'Komoditi', 'Jalur', 'SLA (Target Hari)', 'Bebas (Realisasi Hari)', 'Score SLA', 'Status']
    st.dataframe(df_sla, use_container_width=True)

    # Tombol Download untuk Tabel Rincian SLA per Kapal (XLSX)
    if not df_sla.empty:
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df_sla.to_excel(writer, index=False, sheet_name='Rincian_SLA_Kapal')
        excel_buffer.seek(0) # Kembali ke awal buffer
        st.download_button(
            label="Download Rincian SLA per Kapal (XLSX)",
            data=excel_buffer,
            file_name=f"inklaring_sla_kapal_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    st.markdown("---")

    # =====================================================================
    # INTEGRASI AI CHAT ANALYST
    # =====================================================================
    info_filter = kwargs.get('info_filter', 'Filter tanggal default aktif')
    konteks_lines = []
    
    konteks_lines.append("## RINGKASAN DASHBOARD INKLARING")
    konteks_lines.append(f"- Total Dokumen PIB: {total_data}")
    konteks_lines.append(f"- PIB Selesai: {pib_selesai} | PIB On Progress: {pib_on_progress}")
    konteks_lines.append(f"- Pencapaian SLA EPP: {persen_sla_epp:.1f}%")
    konteks_lines.append(f"- Total Pajak Impor Dibayarkan: Rp {total_biaya_sum:,.0f}")
    konteks_lines.append(f"- Rata-rata Waiting Time: {avg_waiting:.1f} Hari")
    konteks_lines.append(f"- Rata-rata Waktu Proses Bongkar: {avg_bongkar:.1f} Hari")
    val_bebas = f"{avg_bebas_hari:.1f} Hari" if pd.notna(avg_bebas_hari) else "-"
    konteks_lines.append(f"- Rata-rata Bebas: {val_bebas}")
    konteks_lines.append(f"- Filter Aktif: {info_filter}")
    konteks_lines.append("")
    
    merah = (df['Keterangan_Jalur'] == 'MERAH').sum()
    hijau = (df['Keterangan_Jalur'] == 'HIJAU').sum()
    konteks_lines.append(f"- Distribusi Jalur Kepabeanan: {merah} Jalur Merah, {hijau} Jalur Hijau.")

    if 'country_counts' in locals() and not country_counts.empty:
        konteks_lines.append(f"- Top 5 Negara Asal Impor: {', '.join(country_counts.head(5)['country'].tolist())}")
        konteks_lines.append("")

    suplemen = "\n".join(konteks_lines)
    konteks_final = kwargs.get("global_context", "") + "\n---\n" + suplemen

    with st.expander("Tanya ke Melati (Monitoring, Evaluasi, Laporan Terintegrasi)"):
        render_chat_analyst(
            konteks_data_teks=konteks_final,
            nama_halaman="Dashboard Inklaring Impor",
            load_data_fn=load_data,
        )