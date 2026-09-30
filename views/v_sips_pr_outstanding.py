"""
v_sips_pr_outstanding.py - Halaman PR Outstanding SIPS
Menampilkan PR SIPS yang pending (belum jadi PO) beserta aging-nya.
"""
 
import streamlit as st
import pandas as pd
import io
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from utils import format_idr, format_idr_short, format_number, render_chat_analyst, build_sips_where, build_sips_bagian_cond
 
SIPS_PR_OUTSTANDING_CSS = """
<style>
/* Styling untuk Chart Plotly agar dibungkus kotak seperti di halaman lain */
div[data-testid="stPlotlyChart"] {
    border-radius: 12px !important;
    background-color: var(--secondary-background-color) !important;
    background-image: linear-gradient(rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.08)) !important;
    border: 1px solid rgba(128, 128, 128, 0.25) !important;
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08) !important;
    page-break-inside: avoid;
    break-inside: avoid;
    overflow: hidden !important;
}

/* Posisi tombol popover (Lihat Formula) di sebelah judul */
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

def render(load_data, date_from, date_to, selected_nama, selected_bagian=None, **kwargs):

    st.markdown(SIPS_PR_OUTSTANDING_CSS, unsafe_allow_html=True)
 
    info_filter     = kwargs.get('info_filter', 'Tidak ada filter spesifik')
    selected_pgroup = kwargs.get('selected_pgroup', ['All'])
 
    # == Header ================================================================
    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:55px; margin-bottom: 0px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="45" height="45" fill="currentColor"
                 viewBox="0 0 16 16" style="margin-bottom: 8px; margin-right: 12px;">
                <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98
                         1.767h13.713c.889 0 1.438-.99.98-1.767zM8 5c.535 0 .954.462.9.995l-.35
                         3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5m.002 6a1 1 0 1
                         1 0 2 1 1 0 0 1 0-2"/>
            </svg>
            PR Outstanding - SIPS
        </h1>
    """, unsafe_allow_html=True)
    st.markdown(
        "<p style='font-size:18px; color:gray;'>Halaman ini menampilkan PR SIPS yang masih pending (belum menjadi PO) beserta aging-nya, sehingga memudahkan untuk memantau"
        " dan menangani PR yang membutuhkan tindakan segera!</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")
    st.markdown("<br>", unsafe_allow_html=True)
 
    # == WHERE clause ====================================================
    where_pr = build_sips_where(
        date_from=date_from, date_to=date_to,
        selected_nama=selected_nama, selected_bagian=selected_bagian,
        selected_pgroup=selected_pgroup
    )

    # Where khusus PO: tanpa filter tanggal tgl_disposisi_buyer,
    # tapi tetap pakai date_to sebagai acuan mutasi bagian
    where_po = build_sips_where(
        date_from=None, date_to=None,
        selected_nama=selected_nama, selected_bagian=selected_bagian,
        selected_pgroup=selected_pgroup,
        extra=[build_sips_bagian_cond(selected_bagian, date_to=date_to)]
        if (selected_bagian and 'All' not in selected_bagian) else None
    )

    # ══════════════════════════════════════════════════════════════════════════
    # PR_OUTSTANDING 1: PR Pending > 30 Hari (Selain Closed & Proses PO)
    # ══════════════════════════════════════════════════════════════════════════
    title_col, btn_col = st.columns([10, 1])
    with title_col:
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:30px; margin-bottom: 0px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="currentColor"
                     viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 10px;">
                    <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0M9.283 4.002H7.971L6.072 5.385v1.271
                             l1.834-1.318h.065V12h1.312z"/>
                </svg>
                PR Pending Mendekati Kadaluarsa (> 30 Hari)
            </h1>
        """, unsafe_allow_html=True)
    with btn_col:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Lihat Formula"):
            st.info("""\
**PR Pending Mendekati Kadaluarsa (> 30 Hari)**: Menampilkan PR SIPS berstatus *selain Closed dan Proses PO* yang belum
diproses menjadi PO dan sudah menunggu lebih dari 30 hari sejak **Tanggal Disposisi Buyer**.

**Kolom yang ditampilkan:**
| Kolom | Keterangan |
|---|---|
| `Nama` | Nama buyer yang menangani PR |
| `No PR` | Nomor Purchase Requisition |
| `Item` | Item ke-berapa dari nomor PR tersebut |
| `Deskripsi` | Nama barang / short text |
| `P. Group` | Purchasing Group |
| `Prioritas` | Prioritas PR (Normal / Urgent / TA / dst.) |
| `Tgl Disposisi` | Tanggal PR diterima buyer |
| `OE PR (Rp)` | Nilai estimasi anggaran PR |
| `Umur (Hari)` | Selisih hari dari Tanggal Disposisi hingga hari ini |

**Formula Excel:** (SIPS)
- Filter **Status** selain `Closed` dan `Proses PO`
- Tambah kolom `= TODAY() - Tanggal Disposisi Buyer`
- Filter nilai > 30
        """)

    st.caption("Menampilkan PR SIPS berstatus selain 'Closed' dan 'Proses PO' yang belum diproses menjadi PO lebih dari 30 hari sejak tanggal disposisi buyer.")

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    PR_OUTSTANDING_pr_query = f"""
    SELECT
        nama,
        no_pr,
        item_of                                         AS item,
        short_text                                      AS deskripsi,
        purchasing_group,
        prioritas,
        tgl_disposisi_buyer,
        oe_pr,
        (CURRENT_DATE - tgl_disposisi_buyer)::INT       AS umur_hari,
        status
    FROM vw_sips
    WHERE {where_pr}
      AND UPPER(TRIM(status)) NOT IN ('CLOSED', 'PROSES PO')
      AND tgl_disposisi_buyer IS NOT NULL
      AND (CURRENT_DATE - tgl_disposisi_buyer) > 30
    ORDER BY umur_hari DESC, nama, no_pr
    """

    with st.spinner("Memuat PR_OUTSTANDING PR pending..."):
        PR_OUTSTANDING_pr_data = load_data(PR_OUTSTANDING_pr_query)

    if not PR_OUTSTANDING_pr_data.empty:
        PR_OUTSTANDING_pr_data['tgl_disposisi_buyer'] = pd.to_datetime(
            PR_OUTSTANDING_pr_data['tgl_disposisi_buyer'], errors='coerce'
        ).dt.strftime('%Y-%m-%d')
        PR_OUTSTANDING_pr_data['oe_pr'] = PR_OUTSTANDING_pr_data['oe_pr'].apply(
            lambda x: f"Rp {x:,.0f}" if pd.notna(x) else ""
        )
        
        PR_OUTSTANDING_pr_data.index = PR_OUTSTANDING_pr_data.index + 1

        st.caption(f"Ditemukan **{len(PR_OUTSTANDING_pr_data):,}** PR pending > 30 hari.")
        st.dataframe(
            PR_OUTSTANDING_pr_data.rename(columns={
                'nama':               'Nama',
                'no_pr':              'No PR',
                'item':               'Item',
                'deskripsi':          'Deskripsi',
                'purchasing_group':   'P. Group',
                'prioritas':          'Prioritas',
                'tgl_disposisi_buyer':'Tgl Disposisi',
                'oe_pr':              'OE PR (Rp)',
                'umur_hari':          'Umur (Hari)',
                'status':             'Status',
            }),
            use_container_width=True,
            height=280,
        )

        # Download XLSX
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            PR_OUTSTANDING_pr_data.to_excel(writer, index=False, sheet_name='PR_Pending')
        excel_buffer.seek(0)

        st.download_button(
            label="Download sebagai XLSX",
            icon=":material/download:",
            data=excel_buffer,
            file_name=f"sips_pr_pending_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.success("Kerja bagus! Tidak ada PR SIPS yang pending lebih dari 30 hari.")

    st.markdown("<br><br>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # PR_OUTSTANDING 2: Rekap Aging PR (per rentang umur) + Breakdown per Nama
    # ══════════════════════════════════════════════════════════════════════════
    col_aging, col_nama = st.columns([1, 1], gap="large")

    with col_aging:
        title_col2, btn_col2 = st.columns([8, 1])
        with title_col2:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:30px; margin-bottom: 0px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="currentColor"
                         viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 10px;">
                        <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0M6.646 6.24c0-.691.493-1.306 1.336-1.306.756 0 1.313.492 1.313 1.236 0 .697-.469 1.23-.902 1.705l-2.971 3.293V12h5.344v-1.107H7.268v-.077l1.974-2.22.096-.107c.688-.763 1.287-1.428 1.287-2.43 0-1.266-1.031-2.215-2.613-2.215-1.758 0-2.637 1.19-2.637 2.402v.065h1.271v-.07Z"/>
                    </svg>
                    Rekap Aging PR Pending (Open)
                </h1>
            """, unsafe_allow_html=True)
        with btn_col2:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Lihat Formula"):
                st.info("""\
**Rekap Aging PR Pending (Open)**: Bar chart jumlah PR yang belum diproses (status selain Closed dan Proses PO),
dikelompokkan per rentang umur sejak Tanggal Disposisi Buyer.

**Kategori Aging:**
- `0–7 Hari`: Masih baru masuk
- `8–14 Hari`: Proses awal
- `15–30 Hari`: Pantau berkala
- `31–50 Hari`: Follow-up aktif ke buyer
- `51–90 Hari`: Mendekati batas kritis
- `> 90 Hari`: 🔴 Sangat kritis, eskalasi segera

**Formula Excel:** (SIPS)
- Filter **Status** selain `Closed` dan `Proses PO`
- Tambah kolom `= TODAY() - Tanggal Disposisi Buyer`
- Filter sesuai range yang diinginkan
            """)

        st.caption("Jumlah PR Pending (selain Closed & Proses PO) berdasarkan lama menunggu sejak disposisi.")

        aging_query = f"""
        SELECT
            CASE
                WHEN (CURRENT_DATE - tgl_disposisi_buyer) <= 7  THEN '0–7 Hari'
                WHEN (CURRENT_DATE - tgl_disposisi_buyer) <= 14 THEN '8–14 Hari'
                WHEN (CURRENT_DATE - tgl_disposisi_buyer) <= 30 THEN '15–30 Hari'
                WHEN (CURRENT_DATE - tgl_disposisi_buyer) <= 50 THEN '31–50 Hari'
                WHEN (CURRENT_DATE - tgl_disposisi_buyer) <= 90 THEN '51–90 Hari'
                ELSE '> 90 Hari'
            END AS umur_pr,
            COUNT(*) AS total_pr
        FROM vw_sips
        WHERE {where_pr}
            AND UPPER(TRIM(status)) NOT IN ('CLOSED', 'PROSES PO')
            AND tgl_disposisi_buyer IS NOT NULL
        GROUP BY 1
        ORDER BY MIN(CURRENT_DATE - tgl_disposisi_buyer)
        """

        with st.spinner("Memuat aging..."):
            aging_data = load_data(aging_query)

        if not aging_data.empty:
            category_aging = ['0–7 Hari', '8–14 Hari', '15–30 Hari', '31–50 Hari', '51–90 Hari', '> 90 Hari']
            
            # Map rentang ke urutan agar dataframe terurut rapi
            aging_data['sort_key'] = aging_data['umur_pr'].apply(lambda x: category_aging.index(x) if x in category_aging else 99)
            aging_data = aging_data.sort_values('sort_key').reset_index(drop=True)

            # Mapping warna tetap: semakin lama hari -> semakin merah
            aging_color_map = {
                '0–7 Hari':   '#09ab3b',  # Hijau
                '8–14 Hari':  '#2ecc71',  # Hijau muda
                '15–30 Hari': '#f1c40f',  # Kuning
                '31–50 Hari': '#f39c12',  # Oranye muda
                '51–90 Hari': '#e67e22',  # Oranye tua
                '> 90 Hari':  '#e03c3c'   # Merah
            }

            fig_aging = px.bar(
                aging_data, 
                x='umur_pr', 
                y='total_pr',
                labels={'umur_pr': 'Aging', 'total_pr': 'Jumlah PR'},
                text='total_pr',
                category_orders={'umur_pr': category_aging},
                color='umur_pr',  # Warna diikat ke kategori umur (Aging), bukan total_pr
                color_discrete_map=aging_color_map
            )
            fig_aging.update_traces(textposition='outside')
            fig_aging.update_layout(
                showlegend=False,  # Sembunyikan legenda agar tampilan tetap bersih
                height=360,
                margin=dict(t=25, b=0, l=0, r=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='gray',
                xaxis=dict(tickangle=0, title='Aging'),
                yaxis=dict(gridcolor='rgba(128,128,128,0.15)', title='Jumlah PR')
            )
            st.plotly_chart(fig_aging, use_container_width=True)
        else:
            st.info("Tidak ada PR Open pada filter ini.")

    with col_nama:
        title_col3, btn_col3 = st.columns([8, 1])
        with title_col3:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:30px; margin-bottom: 0px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="currentColor"
                         viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 10px;">
                        <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0m-8.082.414c.92 0 1.535.54 1.541 1.318.012.791-.615 1.36-1.588 1.354-.861-.006-1.482-.469-1.54-1.066H5.104c.047 1.177 1.05 2.144 2.754 2.144 1.653 0 2.954-.937 2.93-2.396-.023-1.278-1.031-1.846-1.734-1.916v-.07c.597-.1 1.505-.739 1.482-1.876-.03-1.177-1.043-2.074-2.637-2.062-1.675.006-2.59.984-2.625 2.12h1.248c.036-.556.557-1.054 1.348-1.054.785 0 1.348.486 1.348 1.195.006.715-.563 1.237-1.342 1.237h-.838v1.072h.879Z"/>
                    </svg>
                    Realisasi PR-PO per Buyer
                </h1>
            """, unsafe_allow_html=True)
        with btn_col3:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Lihat Formula"):
                st.info("""\
**Realisasi PR-PO per Buyer**: Perbandingan jumlah Total PR yang didisposisikan ke masing-masing buyer terhadap PR yang sudah berhasil diproses (Status Closed atau Proses PO).

Selisih antara bar Biru dan bar Oranye menunjukkan **PR Outstanding** yang masih dalam proses pengerjaan oleh buyer tersebut.

**Formula Excel:** (SIPS)
- Filter nama buyer di kolom **Buyer**
- **Total PR**: Hitung seluruh baris PR buyer tersebut
- **PR Status Closed**: Hitung baris berstatus `Closed` dan `Proses PO`
""")

        st.caption("Perbandingan Total PR dan PR Status Closed/Proses PO untuk masing-masing buyer.")

        beban_query = f"""
        SELECT
            nama,
            COUNT(*) AS total_pr,
            COUNT(CASE WHEN UPPER(TRIM(status)) IN ('CLOSED', 'PROSES PO') THEN 1 END) AS pr_closed
        FROM vw_sips
        WHERE {where_pr}
          AND tgl_disposisi_buyer IS NOT NULL
        GROUP BY nama
        ORDER BY total_pr DESC
        """

        with st.spinner("Memuat realisasi per buyer..."):
            beban_data = load_data(beban_query)

        if not beban_data.empty:
            # Singkatkan nama jika terlalu panjang untuk tampilan sumbu X
            beban_data['nama_display'] = beban_data['nama'].astype(str).str.split(',').str[0].str.strip()

            fig_beban = go.Figure()

            # Bar 1: Total PR (Biru)
            fig_beban.add_trace(go.Bar(
                x=beban_data['nama_display'],
                y=beban_data['total_pr'],
                name='Total PR',
                marker_color='#2b7fff',
                text=beban_data['total_pr'],
                textposition='outside',
                textfont=dict(size=11, color='#2b7fff', weight='bold'),
                customdata=beban_data[['nama', 'total_pr']],
                hovertemplate='<b>%{customdata[0]}</b><br>Total PR: %{customdata[1]:,}<extra></extra>'
            ))

            # Bar 2: PR Status Closed (Oranye)
            fig_beban.add_trace(go.Bar(
                x=beban_data['nama_display'],
                y=beban_data['pr_closed'],
                name='PR Status Closed',
                marker_color='#f39c38',
                text=beban_data['pr_closed'],
                textposition='outside',
                textfont=dict(size=11, color='#f39c38', weight='bold'),
                customdata=beban_data[['nama', 'pr_closed']],
                hovertemplate='<b>%{customdata[0]}</b><br>PR Status Closed: %{customdata[1]:,}<extra></extra>'
            ))

            max_val_beban = max(beban_data['total_pr'].max(), beban_data['pr_closed'].max()) * 1.18

            fig_beban.update_layout(
                barmode='group',
                height=360,
                margin=dict(t=35, b=10, l=10, r=10),
                legend=dict(
                    orientation='h',
                    yanchor='bottom',
                    y=1.02,
                    xanchor='left',
                    x=0.01
                ),
                xaxis=dict(
                    title='',
                    tickangle=-25,
                    showgrid=False
                ),
                yaxis=dict(
                    title='Jumlah PR',
                    range=[0, max_val_beban],
                    gridcolor='rgba(128,128,128,0.15)'
                ),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='gray'
            )
            st.plotly_chart(fig_beban, use_container_width=True)
        else:
            st.info("Tidak ada data realisasi PR-PO per buyer.")

    st.markdown("<br><br>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # PR_OUTSTANDING 4: Tren Realisasi Item PR-PO (Berdasarkan Bulan Disposisi)
    # ══════════════════════════════════════════════════════════════════════════
    title_col4, btn_col4 = st.columns([10, 1])
    with title_col4:
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:30px; margin-bottom: 0px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="currentColor"
                     viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 10px;">
                    <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0M7.519 5.057c-.886 1.418-1.772 2.838-2.542 4.265v1.12H8.85V12h1.26v-1.559h1.007V9.334H10.11V4.002H8.176zM6.225 9.281v.053H8.85V5.063h-.065c-.867 1.33-1.787 2.806-2.56 4.218"/>
                </svg>
                Tren Realisasi Item PR-PO
            </h1>
        """, unsafe_allow_html=True)
    with btn_col4:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Lihat Formula"):
            st.info("""\
**Tren Realisasi Item PR-PO**: Grafik perbandingan jumlah Total PR yang masuk per bulan disposisi terhadap PR yang sudah berhasil diproses (Status Closed atau Proses PO).

Selisih antara bar Biru (Total PR) dan bar Oranye (PR Status Closed) menggambarkan volume **PR Outstanding / Pending** yang belum selesai dikerjakan pada bulan tersebut.

**Formula Excel:** (SIPS)
- **Total PR**: Hitung baris PR berdasarkan bulan di `Tanggal Disposisi Buyer`
- **PR Status Closed**: Hitung baris berstatus `Closed` dan `Proses PO` berdasarkan bulan di `Tanggal Disposisi Buyer`
""")

    st.caption("Perbandingan Total PR dan PR yang sudah berstatus Closed/Proses PO berdasarkan bulan disposisi buyer.")

    trend_pr_query = f"""
    SELECT 
        DATE_TRUNC('month', tgl_disposisi_buyer)::date AS month,
        COUNT(*) AS total_pr,
        COUNT(CASE WHEN UPPER(TRIM(status)) IN ('CLOSED', 'PROSES PO') THEN 1 END) AS pr_closed
    FROM vw_sips
    WHERE {where_pr}
      AND tgl_disposisi_buyer IS NOT NULL
    GROUP BY 1
    ORDER BY 1
    """

    with st.spinner("Memuat tren realisasi PR-PO..."):
        trend_pr_data = load_data(trend_pr_query)

    if not trend_pr_data.empty:
        trend_pr_data['month'] = pd.to_datetime(trend_pr_data['month']).dt.tz_localize(None)
        trend_pr_data = trend_pr_data.sort_values('month').reset_index(drop=True)
        
        # Filter batas tanggal awal bulan
        dt_from_pd = pd.to_datetime(date_from).replace(day=1)
        dt_to_pd = pd.to_datetime(date_to).replace(day=1)
        trend_pr_data = trend_pr_data[(trend_pr_data['month'] >= dt_from_pd) & (trend_pr_data['month'] <= dt_to_pd)]

        month_names_id = {
            1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
            7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
        }
        trend_pr_data['month_name'] = trend_pr_data['month'].dt.month.map(month_names_id)

        fig_trend = go.Figure()

        # Bar 1: Total PR (Biru)
        fig_trend.add_trace(go.Bar(
            x=trend_pr_data['month_name'],
            y=trend_pr_data['total_pr'],
            name='Total PR',
            marker_color='#2b7fff',
            text=trend_pr_data['total_pr'],
            textposition='outside',
            textfont=dict(size=12, color='#2b7fff', weight='bold'),
            hovertemplate='<b>%{x}</b><br>Total PR: %{y:,}<extra></extra>'
        ))

        # Bar 2: PR Status Closed (Oranye)
        fig_trend.add_trace(go.Bar(
            x=trend_pr_data['month_name'],
            y=trend_pr_data['pr_closed'],
            name='PR Status Closed',
            marker_color='#f39c38',
            text=trend_pr_data['pr_closed'],
            textposition='outside',
            textfont=dict(size=12, color='#f39c38', weight='bold'),
            hovertemplate='<b>%{x}</b><br>PR Status Closed: %{y:,}<extra></extra>'
        ))

        max_val_y = max(trend_pr_data['total_pr'].max(), trend_pr_data['pr_closed'].max()) * 1.18

        fig_trend.update_layout(
            barmode='group',
            height=380,
            xaxis_title='',
            yaxis_title='Total PR',
            yaxis=dict(
                range=[0, max_val_y],
                showgrid=True,
                gridcolor='rgba(128,128,128,0.15)'
            ),
            xaxis=dict(
                tickmode='array',
                tickvals=trend_pr_data['month_name'].tolist(),
                tickangle=0,
                showgrid=False
            ),
            margin=dict(t=50, b=10, l=10, r=20),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.05,
                xanchor="left",
                x=0.01
            ),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Tidak ada data tren realisasi PR-PO untuk filter ini.")

    st.markdown("<br><br>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # PR_OUTSTANDING 5: Monitoring Status PR SIPS
    # ══════════════════════════════════════════════════════════════════════════
    title_col5, btn_col5 = st.columns([10, 1])
    with title_col5:
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:30px; margin-bottom: 0px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="currentColor"
                     viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 10px;">
                    <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0m-8.006 4.158c1.74 0 2.924-1.119 2.924-2.806 0-1.641-1.178-2.584-2.56-2.584-.897 0-1.442.421-1.612.68h-.064l.193-2.344h3.621V4.002H5.791L5.445 8.63h1.149c.193-.358.668-.809 1.435-.809.85 0 1.582.604 1.582 1.57 0 1.085-.779 1.682-1.57 1.682-.697 0-1.389-.31-1.53-1.031H5.276c.065 1.213 1.149 2.115 2.72 2.115Z"/>
                </svg>
                Monitoring Status PR SIPS
            </h1>
        """, unsafe_allow_html=True)
    with btn_col5:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Lihat Formula"):
            st.info("""\
**Monitoring Status PR SIPS**: Menampilkan jumlah PR berdasarkan statusnya beserta total nilai OE.

**Keterangan Status:**
| Status | Keterangan |
|---|---|
| `Open` | PR sudah didisposisi ke buyer, belum ada PO |
| `Proses PO` | PO sedang dalam proses pengerjaan |
| `Closed` | PO sudah selesai dan ditutup |

**Formula Excel:** (SIPS)
- Filter **Status** sesuai yang diinginkan
- Hitung jumlah baris dan jumlahkan kolom **OE PR**
        """)

    st.caption("Distribusi jumlah PR dan total OE berdasarkan status dokumen SIPS.")

    status_dist_query = f"""
    SELECT
        status,
        COUNT(*)                                        AS jumlah_pr,
        COALESCE(SUM(oe_pr), 0)                         AS total_oe,
        ROUND(AVG(
            CASE WHEN tgl_disposisi_buyer IS NOT NULL
            THEN (CURRENT_DATE - tgl_disposisi_buyer)
            END
        )::numeric, 1)                                  AS avg_umur_hari
    FROM vw_sips
    WHERE {where_pr}
    GROUP BY status
    ORDER BY
        CASE UPPER(TRIM(status))
            WHEN 'OPEN'      THEN 1
            WHEN 'PROSES PO' THEN 2
            WHEN 'CLOSED'    THEN 3
            ELSE 4
        END
    """

    with st.spinner("Memuat monitoring status..."):
        status_dist_data = load_data(status_dist_query)

    if not status_dist_data.empty:
        if True:  # chart full-width atas
            color_status = {
                'Open':      '#6c8ebf',
                'Proses PO': '#f0a500',
                'Closed':    '#09ab3b',
            }
            colors_bar = [color_status.get(s, '#aaaaaa') for s in status_dist_data['status']]

            fig_sd = go.Figure()
            fig_sd.add_trace(go.Bar(
                name='Jumlah PR',
                x=status_dist_data['status'],
                y=status_dist_data['jumlah_pr'],
                text=status_dist_data['jumlah_pr'],
                textposition='outside',
                marker_color=colors_bar,
                hovertemplate="<b>%{x}</b><br>Jumlah PR: %{y}<extra></extra>",
            ))
            fig_sd.update_layout(
                height=360,
                xaxis_title='Status',
                yaxis_title='Jumlah PR',
                margin=dict(t=30, b=10, l=0, r=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='gray',
                showlegend=False,
                yaxis=dict(gridcolor='rgba(128,128,128,0.15)'),
            )
            st.plotly_chart(fig_sd, use_container_width=True)

        # Tabel ringkasan di bawah chart (full-width)
        if True:
            total_pr_all = status_dist_data['jumlah_pr'].sum()

            TH = 'padding:8px 12px;font-size:14px;font-weight:600;'
            P  = 'padding:8px 12px;border-bottom:1px solid rgba(128,128,128,0.2);font-size:14px;'
            thead_sd = (
                '<thead><tr style="border-bottom:2px solid rgba(128,128,128,0.4)">'
                + f'<th style="{TH}text-align:left">Status</th>'
                + f'<th style="{TH}text-align:center">Jml PR</th>'
                + f'<th style="{TH}text-align:right">Total OE</th>'
                + f'<th style="{TH}text-align:center">% Total</th>'
                + f'<th style="{TH}text-align:center">Avg Umur</th>'
                + '</tr></thead>'
            )

            badge_color_sd = {
                'Open':      '#6c8ebf',
                'Proses PO': '#f0a500',
                'Closed':    '#09ab3b',
            }
            rows_sd = []
            for _, row in status_dist_data.iterrows():
                status  = str(row['status'])
                pct     = round(row['jumlah_pr'] / total_pr_all * 100, 1) if total_pr_all > 0 else 0
                bc      = badge_color_sd.get(status, '#888888')
                badge   = (f'<span style="background:{bc};color:#fff;padding:2px 10px;'
                           f'border-radius:12px;font-size:12px;font-weight:600">{status}</span>')
                oe_fmt  = format_idr_short(float(row['total_oe']))
                avg_u   = f"{row['avg_umur_hari']:.0f} hr" if pd.notna(row['avg_umur_hari']) else '-'
                rows_sd.append(
                    '<tr>'
                    + f'<td style="{P}">{badge}</td>'
                    + f'<td style="{P}text-align:center;font-weight:600">{int(row["jumlah_pr"])}</td>'
                    + f'<td style="{P}text-align:right">{oe_fmt}</td>'
                    + f'<td style="{P}text-align:center">{pct}%</td>'
                    + f'<td style="{P}text-align:center">{avg_u}</td>'
                    + '</tr>'
                )

            rows_sd.append(
                '<tr style="border-top:2px solid rgba(128,128,128,0.4);font-weight:700">'
                + f'<td style="padding:8px 12px;font-size:14px">Total</td>'
                + f'<td style="padding:8px 12px;font-size:14px;text-align:center">{int(total_pr_all)}</td>'
                + f'<td style="padding:8px 12px;font-size:14px;text-align:right">'
                + f'{format_idr_short(float(status_dist_data["total_oe"].sum()))}</td>'
                + f'<td style="padding:8px 12px;font-size:14px;text-align:center">100%</td>'
                + f'<td style="padding:8px 12px;font-size:14px;text-align:center">-</td>'
                + '</tr>'
            )

            tabel_sd_html = (
                '<table style="width:100%;border-collapse:collapse">'
                + thead_sd
                + '<tbody>' + ''.join(rows_sd) + '</tbody>'
                + '</table>'
            )
            st.markdown(tabel_sd_html, unsafe_allow_html=True)
    else:
        st.info("Tidak ada data status PR SIPS untuk filter yang dipilih.")

    st.markdown("---")

    # =====================================================================
    # INTEGRASI AI: KUMPULKAN KONTEKS & PANGGIL CHAT
    # =====================================================================

    konteks_lines = []

    konteks_lines.append("## 0. FILTER YANG SEDANG DITERAPKAN USER")
    konteks_lines.append(info_filter)
    konteks_lines.append("")

    if 'PR_OUTSTANDING_pr_data' in locals() and not PR_OUTSTANDING_pr_data.empty:
        konteks_lines.append(f"## 1. PR_OUTSTANDING: PR SIPS PENDING > 30 HARI (Total: {len(PR_OUTSTANDING_pr_data)} PR)")
        df_simple = PR_OUTSTANDING_pr_data[['nama', 'no_pr', 'purchasing_group',
                                            'prioritas', 'tgl_disposisi_buyer', 'umur_hari', 'status']].head(20)
        konteks_lines.append(df_simple.to_csv(index=False))
        konteks_lines.append("")
    else:
        konteks_lines.append("## 1. PR_OUTSTANDING: PR SIPS PENDING > 30 HARI\nAman. Tidak ada PR pending > 30 hari.\n")

    if 'aging_data' in locals() and not aging_data.empty:
        konteks_lines.append("## 2. REKAP AGING PR PENDING SIPS")
        konteks_lines.append(aging_data.to_csv(index=False))
        konteks_lines.append("")
    else:
        konteks_lines.append("## 2. REKAP AGING PR PENDING SIPS\nTidak ada data aging.\n")

    if 'beban_data' in locals() and not beban_data.empty:
        konteks_lines.append("## 3. REALISASI PR-PO PER BUYER")
        konteks_lines.append(beban_data[['nama', 'total_pr', 'pr_closed']].to_csv(index=False))
        konteks_lines.append("")
    else:
        konteks_lines.append("## 3. REALISASI PR-PO PER BUYER\nTidak ada data.\n")

    if 'trend_pr_data' in locals() and not trend_pr_data.empty:
        konteks_lines.append("## 4. TREN REALISASI ITEM PR-PO")
        konteks_lines.append(trend_pr_data[['month_name', 'total_pr', 'pr_closed']].to_csv(index=False))
        konteks_lines.append("")

    if 'status_dist_data' in locals() and not status_dist_data.empty:
        konteks_lines.append("## 5. DISTRIBUSI STATUS PR SIPS")
        konteks_lines.append(status_dist_data.to_csv(index=False))
        konteks_lines.append("")
    else:
        konteks_lines.append("## 5. DISTRIBUSI STATUS PR SIPS\nTidak ada data.\n")

    suplemen = "\n# SUPLEMEN - DETAIL HALAMAN INI (PR_OUTSTANDING SIPS)\n" + "\n".join(konteks_lines)
    konteks_final = kwargs.get("global_context", "") + "\n---\n" + suplemen

    with st.expander("Tanya ke Melati (Monitoring, Evaluasi, Laporan Terintegrasi)"):
        render_chat_analyst(
            konteks_data_teks=konteks_final,
            nama_halaman="Halaman PR_OUTSTANDING SIPS (Warning & Action Required)",
            load_data_fn=load_data,
        )