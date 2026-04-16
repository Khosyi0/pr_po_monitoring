"""
v_inklaring_dashboard.py - Halaman Dashboard Inklaring Barang Impor
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from utils import render_chat_analyst, format_number, format_idr, format_idr_short, idr_axis

def render(load_data, date_from=None, date_to=None, **kwargs):
    # ── HEADER ───────────────────────────────────────────────────────────────
    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:60px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" fill="currentColor" class="bi bi-box-seam-fill" viewBox="0 0 16 16" style="margin-bottom: 10px; margin-right: 8px;">
                <path d="M10 .5a.5.5 0 0 0-.5-.5h-3a.5.5 0 0 0-.5.5.5.5 0 0 1-.5.5.5.5 0 0 0-.5.5V2a.5.5 0 0 0 .5.5h5A.5.5 0 0 0 11 2v-.5a.5.5 0 0 0-.5-.5.5.5 0 0 1-.5-.5"/>
                <path d="M4.085 1H3.5A1.5 1.5 0 0 0 2 2.5v12A1.5 1.5 0 0 0 3.5 16h9a1.5 1.5 0 0 0 1.5-1.5v-12A1.5 1.5 0 0 0 12.5 1h-.585q.084.236.085.5V2a1.5 1.5 0 0 1-1.5 1.5h-5A1.5 1.5 0 0 1 4 2v-.5q.001-.264.085-.5M10 7a1 1 0 1 1 2 0v5a1 1 0 1 1-2 0zm-6 4a1 1 0 1 1 2 0v1a1 1 0 1 1-2 0zm4-3a1 1 0 0 1 1 1v3a1 1 0 1 1-2 0V9a1 1 0 0 1 1-1"/>
            </svg>
            Dashboard Inklaring Impor
        </h1>
    """, unsafe_allow_html=True)
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] > div {
            font-size: 2rem !important;
            white-space: normal !important;
            word-wrap: break-word !important;
            line-height: 1.2 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # ── FILTER TANGGAL ───────────────────────────────────────────────────────
    date_filter = ""
    if date_from and date_to:
        start_str = date_from.strftime('%Y-%m-%d')
        end_str = date_to.strftime('%Y-%m-%d')
        date_filter = f"WHERE tgl_eta >= '{start_str}' AND tgl_eta <= '{end_str}'"

    # ── LOAD DATA ────────────────────────────────────────────────────────────
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

    # ── PANDAS DATA TRANSFORMATIONS (RUMUS EXCEL) ─────────────────────────────
    
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

    # ── METRICS CARDS (ROW 1) ─────────────────────────────────────────────────
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

    KPI_DASH = [
        {
            "key": "kpi_total_pib",
            "icon_path": "M4 0h5.293A1 1 0 0 1 10 .293L13.707 4a1 1 0 0 1 .293.707V14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2zm5.5 1.5v2a1 1 0 0 0 1 1h2l-3-3z",
            "label": "Total PIB",
            "value": f"{format_number(total_data)}",
            "delta": "PIB",
            "formula": "Jumlah total PIB pada periode filter."
        },
        {
            "key": "kpi_pib_on_progress",
            "icon_path": "M8 3.5a.5.5 0 0 0-1 0V9a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0 0 .496-.868L8 8.71V3.5zM8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0z",
            "label": "PIB On Progress",
            "value": f"{format_number(pib_on_progress)}",
            "delta": "Dokumen",
            "formula": "Seleisih Total PIB dengan PIB Selesai."
        },
        {
            "key": "kpi_pib_selesai",
            "icon_path": "M10.97 4.97a.75.75 0 0 1 1.07 1.05l-3.99 4.99a.75.75 0 0 1-1.08.02L4.324 8.384a.75.75 0 1 1 1.06-1.06l2.094 2.093 3.473-4.425z M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0z",
            "label": "PIB Selesai",
            "value": f"{format_number(pib_selesai)}",
            "delta": "SPPB Terbit",
            "formula": "Jumlah dokumen PIB yang Tanggal SPPB-nya sudah terisi."
        },
        {
            "key": "kpi_kinerja_sla",
            "icon_path": "M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16M10.97 4.97a.235.235 0 0 0-.02.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-1.071-1.05",
            "label": "Kinerja SLA EPP",
            "value": f"{format_number(persen_sla_epp, decimals=2)}%",
            "delta": "Target: > 80%",
            "formula": "Persentase dokumen dengan Score SLA = 1 dibagi total dokumen."
        },
        {
            "key": "kpi_total_biaya",
            "icon_path": "M4 10.781c.148 1.667 1.513 2.85 3.591 3.003V15h1.043v-1.216c2.27-.179 3.678-1.438 3.678-3.3 0-1.59-.947-2.51-2.956-3.028l-.722-.187V3.467c1.122.11 1.879.714 2.07 1.616h1.47c-.166-1.6-1.54-2.748-3.54-2.875V1H7.591v1.233c-1.939.23-3.27 1.472-3.27 3.156 0 1.454.966 2.483 2.661 2.917l.61.162v4.031c-1.149-.17-1.94-.8-2.131-1.718zm3.391-3.836c-1.043-.263-1.6-.825-1.6-1.616 0-.944.704-1.641 1.8-1.828v3.495l-.2-.05zm1.591 1.872c1.287.323 1.852.859 1.852 1.769 0 1.097-.826 1.828-2.2 1.939V8.73z",
            "label": "Total Biaya",
            "value": f"{format_idr(total_biaya_sum)}",
            "delta": "Bea Masuk + PPN + PPH",
            "formula": "Total nilai Bea Masuk + PPN + PPH dari seluruh dokumen pada periode filter."
        },
        {
            "key": "kpi_avg_waiting",
            "icon_path": "M8 3.5a.5.5 0 0 0-1 0V9a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0 0 .496-.868L8 8.71V3.5zM8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0z",
            "label": "Rata-rata Waiting Time",
            "value": f"{format_number(avg_waiting, decimals=1)} Hari" if pd.notna(avg_waiting) else "-",
            "delta": "Start Bongkar - Tgl PIB",
            "formula": "Rata-rata selisih hari dari Tgl PIB hingga Start Bongkar."
        }
    ]

    st.markdown("""
    <style>
    .kpi-card {
        display: flex;
        align-items: center;
        background: var(--secondary-background-color);
        border-radius: 10px;
        padding: 16px 14px;
        gap: 12px;
        height: 100%;
    }
    .kpi-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        opacity: 1;
    }
    .kpi-body {
        flex: 1;
        min-width: 0;
    }
    .kpi-label {
        font-size: 13px;
        opacity: 0.9;
        margin: 0 0 2px 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .kpi-value {
        font-size: 2rem !important;
        font-weight: 600 !important;
        margin: 0 !important;
        padding: 0 !important;
        line-height: 1.1 !important;
        display: block !important;
    }
    .kpi-delta {
        font-size: 12px;
        color: #09ab3b;
        margin: 0;
    }
    .kpi-delta-neutral {
        font-size: 12px;
        opacity: 0.55;
        margin: 0;
    }
    [data-testid="column"]:nth-child(2) {
        display: flex;
        align-items: center;
        justify-content: flex-start;
    }
    </style>
    """, unsafe_allow_html=True)

    def render_kpi_row(items):
        n = len(items)
        cols = st.columns(3)
        for i, col in enumerate(cols):
            with col:
                if i >= n:
                    continue
                kpi = items[i]
                
                no_arrow = kpi["value"] == "-" or kpi["delta"].startswith("Target:") or kpi["delta"].startswith("PIB") or kpi["delta"].startswith("Dokumen") or kpi["delta"].startswith("SPPB") or kpi["delta"].startswith("Bea Masuk") or kpi["delta"].startswith("Start Bongkar")
                delta_arrow = "" if no_arrow else "↑ "
                delta_cls = "kpi-delta"

                card_html = f"""
                <div class="kpi-card">
                    <div class="kpi-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"
                             fill="currentColor" viewBox="0 0 16 16">
                            <path d="{kpi['icon_path']}"/>
                        </svg>
                    </div>
                    <div class="kpi-body">
                        <p class="kpi-label">{kpi['label']}</p>
                        <p class="kpi-value">{kpi['value']}</p>
                        <p class="{delta_cls}">{delta_arrow}{kpi['delta']}</p>
                    </div>
                </div>"""

                c_card, c_btn = st.columns([10, 2])
                with c_card:
                    st.markdown(card_html, unsafe_allow_html=True)
                with c_btn:
                    st.markdown("<div style='height:25px'></div>", unsafe_allow_html=True)
                    with st.popover(":material/visibility:", help="Lihat Formula"):
                        st.info(kpi["formula"])

    for row_start in range(0, len(KPI_DASH), 3):
        row_items = KPI_DASH[row_start:row_start + 3]
        render_kpi_row(row_items)
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    st.markdown("---")

    # ── CHARTS (ROW 2) ────────────────────────────────────────────────────────
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        title_col, btn_col = st.columns([9, 1])
        with title_col:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:30px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-pie-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 6px; margin-right: 8px;">
                        <path d="M15.985 8.5H8.207l-5.5 5.5a8 8 0 0 0 13.277-5.5zM2 13.292A8 8 0 0 1 7.5.015v7.778l-5.5 5.5zM8.5.015V7.5h7.485A8.001 8.001 0 0 0 8.5.015z"/>
                    </svg>
                    Proporsi Jalur Kepabeanan
                </h1>
            """, unsafe_allow_html=True)
        with btn_col:
            st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Lihat Formula"):
                st.info("""\
**Proporsi Jalur Kepabeanan**: Pie chart distribusi jumlah dokumen impor berdasarkan jalur merah dan jalur hijau.

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

    # ── CHARTS (ROW 3) - GANTT CHART TIMELINE ─────────────────────────────────
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
        
        # FIX LABEL: Mengubah label Kapal menjadi hanya Nomor AJU
        df_timeline['Kapal_Label'] = 'AJU ' + df_timeline['no_aju'].fillna('-').astype(str)
        
        timeline_data = []
        for _, row in df_timeline.iterrows():
            # 1. Fase Waiting Time (Tgl PIB sampai Start Bongkar)
            if pd.notna(row['tgl_pib']) and pd.notna(row['start_bongkar']):
                timeline_data.append({
                    'No AJU': row['Kapal_Label'],
                    'Tahap': 'Waiting Time',
                    'Start': row['tgl_pib'],
                    'Finish': row['start_bongkar']
                })
            
            # 2. Fase Proses Bongkar (Start Bongkar sampai Selesai Bongkar)
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
        
        fig_gantt.update_yaxes(autorange="reversed") # Agar data terbaru di atas
        fig_gantt.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
            legend_title_text="",
            xaxis_title="Tanggal Operasional",
            height=400 + (len(df_timeline) * 15) # Dinamis mengatur tinggi chart sesuai jumlah dokumen
        )
        st.plotly_chart(fig_gantt, use_container_width=True)
    else:
        st.info("Data Tanggal PIB, Start Bongkar, atau Selesai Bongkar tidak lengkap untuk merender timeline.")

    # ── CHARTS (ROW 4) ────────────────────────────────────────────────────────
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

    # Mengambil 10 data dengan Total Pajak terbesar
    df_top10 = df.nlargest(10, 'TOTAL_BIAYA').copy()
    
    # Tambahkan Ranking agar setiap baris memiliki Label X yang 100% dijamin unik
    df_top10 = df_top10.reset_index(drop=True)
    df_top10['Rank'] = df_top10.index + 1
    
    df_top10['Label'] = 'AJU ' + df_top10['no_aju'].fillna('-').astype(str)
    
    df_top10_chart = df_top10.rename(columns={
        'bea_masuk_rp': 'Bea Masuk (Rp)',
        'ppn_rp': 'PPN',
        'pph_rp': 'PPH'
    })

    # --- FIX GRAFIK NUMPUK (MELT DATA) ---
    # Mengubah format kolom menjadi baris agar Plotly bisa menumpuknya dengan benar
    df_melted = df_top10_chart.melt(
        id_vars=['Label', 'TOTAL_BIAYA', 'Rank'], 
        value_vars=['Bea Masuk (Rp)', 'PPN', 'PPH'],
        var_name='Jenis Pajak', 
        value_name='Nilai Pajak'
    )
    
    # Urutkan berdasarkan Rank agar tampilannya berurutan dari yang terbesar ke terkecil
    df_melted = df_melted.sort_values(['Rank', 'Jenis Pajak'])

    fig_top10 = px.bar(
        df_melted, 
        x='Label', 
        y='Nilai Pajak',
        color='Jenis Pajak',
        labels={'Nilai Pajak': 'Total Biaya (Rupiah)', 'Label': 'Dokumen Impor'},
        color_discrete_map={
            'Bea Masuk (Rp)': '#1f77b4', 
            'PPN': '#ff7f0e', 
            'PPH': '#2ca02c'
        }
    )
    # ---------------------------------------
    
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
    konteks_lines.append(f"- Filter Aktif: {info_filter}")
    konteks_lines.append("")
    
    merah = (df['Keterangan_Jalur'] == 'MERAH').sum()
    hijau = (df['Keterangan_Jalur'] == 'HIJAU').sum()
    konteks_lines.append(f"- Distribusi Jalur Kepabeanan: {merah} Jalur Merah, {hijau} Jalur Hijau.")

    suplemen = "\n".join(konteks_lines)
    konteks_final = kwargs.get("global_context", "") + "\n---\n" + suplemen

    render_chat_analyst(
        konteks_data_teks=konteks_final,
        nama_halaman="Dashboard Inklaring Impor",
        load_data_fn=load_data,
    )
