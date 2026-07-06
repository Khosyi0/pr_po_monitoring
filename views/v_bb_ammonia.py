import streamlit as st
import pandas as pd
import plotly.express as px
import io

def render(load_data, global_context):
    st.markdown("### :material/science: Analisis Tren Komparasi Harga Pasar: Ammonia")
    
    # 1. Ambil data Ammonia dari database
    query = """
        SELECT tanggal_terbit, nama_majalah, incoterm, harga_min, harga_max 
        FROM master_harga_bahan_baku 
        WHERE bahan_baku = 'Ammonia'
        ORDER BY tanggal_terbit ASC
    """
    df = load_data(query)
    
    if df.empty:
        st.warning("Data harga Ammonia belum tersedia di database.")
        return

    list_majalah = df['nama_majalah'].unique()
    min_date = df['tanggal_terbit'].min()
    max_date = df['tanggal_terbit'].max()

    # Pengaturan default tanggal mulai (Januari 2025)
    default_start_date = pd.Timestamp('2025-01-01').date()
    calendar_min_date = min(min_date, default_start_date)
    
    if default_start_date > max_date or default_start_date < min_date:
        default_start_date = min_date

    # 2. Expander untuk Filter Komparasi dengan Ikon Material Settings
    with st.expander(":material/settings: Filter Komparasi Harga Pasar", expanded=True):
        col_mulai, col_sampai, col_metode, col_jml = st.columns(4)
        with col_mulai:
            start_date = st.date_input(
                "Mulai dari tanggal", 
                value=default_start_date,
                min_value=calendar_min_date,
                max_value=max_date
            )
        with col_sampai:
            end_date = st.date_input(
                "Sampai tanggal", 
                value=max_date,
                min_value=calendar_min_date,
                max_value=max_date
            )
        with col_metode:
            jenis_harga = st.selectbox(
                "Jenis Harga", 
                ["AVERAGE", "MIN", "MAX"],
                help="Pilih nilai harga yang ingin diplot pada grafik"
            )
        with col_jml:
            jml_komparasi = st.number_input("Jumlah Komparasi", min_value=1, max_value=5, value=2)
            
        st.markdown("<hr style='margin: 10px 0; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
        
        komparasi_data = {}
        warna_map = {}

        default_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

        for i in range(int(jml_komparasi)):
            c1, c2, c3 = st.columns([3, 3, 1])
            with c1:
                majalah_pilihan = st.selectbox(f"Majalah ke-{i+1}", list_majalah, index=i if i < len(list_majalah) else 0, key=f"majalah_{i}")
            with c2:
                list_incoterm = df[df['nama_majalah'] == majalah_pilihan]['incoterm'].unique()
                incoterm_pilihan = st.multiselect(f"Metode Incoterm ke-{i+1}", list_incoterm, default=list_incoterm[:1] if len(list_incoterm) > 0 else [], key=f"incoterm_{i}")
            with c3:
                warna_pilihan = st.color_picker("Warna", default_colors[i % len(default_colors)], key=f"color_{i}")
            
            if incoterm_pilihan:
                komparasi_data[majalah_pilihan] = incoterm_pilihan
                for incoterm in incoterm_pilihan:
                    label = f"{majalah_pilihan} - {incoterm}"
                    warna_map[label] = warna_pilihan

    if start_date <= end_date and komparasi_data:
        df_plot = pd.DataFrame()
        
        for majalah, incoterms in komparasi_data.items():
            temp_df = df[(df['nama_majalah'] == majalah) & (df['incoterm'].isin(incoterms)) & (df['tanggal_terbit'] >= start_date) & (df['tanggal_terbit'] <= end_date)].copy()
            if not temp_df.empty:
                temp_df['label_komparasi'] = temp_df['nama_majalah'] + ' - ' + temp_df['incoterm']
                df_plot = pd.concat([df_plot, temp_df], ignore_index=True)
        
        if not df_plot.empty:
            df_plot['harga_avg'] = (df_plot['harga_min'] + df_plot['harga_max']) / 2
            
            # Konversi data tanggal murni
            df_plot['tanggal_terbit'] = pd.to_datetime(df_plot['tanggal_terbit'])
            df_plot = df_plot.sort_values('tanggal_terbit')
            tanggal_unik = df_plot['tanggal_terbit'].unique()
            
            if jenis_harga == "MIN": y_col, y_label = 'harga_min', 'Harga Minimum (USD/MT)'
            elif jenis_harga == "MAX": y_col, y_label = 'harga_max', 'Harga Maksimum (USD/MT)'
            else: y_col, y_label = 'harga_avg', 'Harga Rata-rata (USD/MT)'
            
            fig = px.line(
                df_plot, x='tanggal_terbit', y=y_col, color='label_komparasi',
                color_discrete_map=warna_map, markers=True, 
                title=f"Komparasi Tren Harga Ammonia ({jenis_harga})",
                labels={y_col: y_label, 'tanggal_terbit': 'Tanggal Publikasi', 'label_komparasi': 'Majalah & Incoterm'}
            )
            
            fig.update_layout(
                hovermode="x unified",
                legend=dict(orientation="v", yanchor="top", y=-0.6, xanchor="left", x=0),
                margin=dict(b=300, t=80, l=60, r=40),
                height=600
            )
            
            fig.update_xaxes(
                tickangle=-90,
                type='date', 
                tickmode='array',
                tickvals=tanggal_unik,
                tickformat="%d %b %Y",
                title=dict(
                    text="Tanggal Publikasi",
                    standoff=40
                )
            )
            
            fig.update_yaxes(dtick=50)
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("#### :material/table_chart: Detail Histori Data (3 Periode Terakhir)")
            
            # Proses Pivot Data
            df_display = df_plot.copy()
            df_display['harga_range'] = df_display['harga_min'].apply(lambda x: f"{x:g}") + ' - ' + df_display['harga_max'].apply(lambda x: f"{x:g}")
            
            df_pivot = df_display.pivot_table(
                index='label_komparasi', 
                columns='tanggal_terbit', 
                values='harga_range',
                aggfunc=lambda x: ' '.join(x)
            )
            
            df_pivot = df_pivot.sort_index(axis=1, ascending=False)
            df_pivot = df_pivot.iloc[:, :3]
            
            bulan_indo = {
                1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 5: 'Mei', 6: 'Juni',
                7: 'Juli', 8: 'Agustus', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
            }
            kolom_tanggal = [f"{d.day:02d} {bulan_indo[d.month]} {d.year}" for d in df_pivot.columns]
            
            jml_kolom = len(kolom_tanggal)
            
            thead = f'''
<thead>
    <tr>
        <th rowspan="2" style="vertical-align: middle; text-align: left !important;">Referensi</th>
        <th colspan="{jml_kolom}">Harga USD/MT</th>
    </tr>
    <tr>
'''
            for tgl in kolom_tanggal:
                thead += f"<th>{tgl}</th>"
            thead += "</tr>\n</thead>"
            
            tbody = "<tbody>\n"
            for index, row in df_pivot.iterrows():
                tbody += f"<tr>\n<td style='text-align: left !important;'>{index}</td>\n"
                for col in df_pivot.columns:
                    val = row[col]
                    val_str = "" if pd.isna(val) else str(val)
                    tbody += f"<td>{val_str}</td>\n"
                tbody += "</tr>\n"
            tbody += "</tbody>"
            
            html_table = f"<table>\n{thead}\n{tbody}\n</table>"
            
            styled_html = f"""
<style>
.custom-table-container {{
    width: 100%;
    overflow-x: auto;
    margin-bottom: 2rem;
}}
.custom-table-container table {{
    width: 100%;
    border-collapse: collapse;
    font-family: "Source Sans Pro", sans-serif;
    font-size: 14px;
    color: var(--text-color);
}}
.custom-table-container th, .custom-table-container td {{
    text-align: center !important;
    padding: 10px !important;
    border: 1px solid rgba(128, 128, 128, 0.2);
}}
.custom-table-container th {{
    background-color: rgba(128, 128, 128, 0.1);
    font-weight: 600;
}}
</style>
<div class="custom-table-container">
    {html_table}
</div>
"""
            st.markdown(styled_html, unsafe_allow_html=True)
                
        else:
            st.info("Tidak ada data yang tersedia untuk kombinasi filter yang dipilih pada rentang waktu tersebut.")
    else:
        if start_date > end_date:
            st.error("❌ 'Mulai dari tanggal' tidak boleh lebih besar dari 'Sampai tanggal'.")
        else:
            st.info("Silakan tentukan minimal 1 metode Incoterm.")