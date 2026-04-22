"""
v_alert.py - Halaman Alert SAP
"""
import streamlit as st
import pandas as pd
import io
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from utils import format_idr, format_idr_short, format_number, render_chat_analyst

ALERT_CSS = """
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
    align-items: flex-start;
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
    line-height: 1.1 !important;
    color: var(--text-color) !important;
    white-space: normal !important;
    word-wrap: break-word !important;
    display: block !important;
}

.dash-delta { font-size: 12px; margin: 0; color: var(--text-color) !important; opacity: 0.6; }
.dash-delta-green { font-size: 12px; color: #09ab3b !important; margin: 0; font-weight: 600; }
.dash-delta-red   { font-size: 12px; color: #e03c3c !important; margin: 0; font-weight: 600; }
.dash-delta-orange{ font-size: 12px; color: #f0a500 !important; margin: 0; font-weight: 600; }
</style>
"""

ICONS = {
    "kpi_outstanding_total": "M8 1a2.5 2.5 0 0 1 2.5 2.5V4h-5v-.5A2.5 2.5 0 0 1 8 1m3.5 3v-.5a3.5 3.5 0 1 0-7 0V4H1v10a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V4zM2 5h12v9a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1z",
    "kpi_outstanding_kritis": "M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5m.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2",
    "kpi_outstanding_pantau": "M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001q.044.06.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1 1 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0",
    "kpi_outstanding_nilai": "M4 10.781c.148 1.667 1.513 2.85 3.591 3.003V15h1.043v-1.216c2.27-.179 3.678-1.438 3.678-3.3 0-1.59-.947-2.51-2.956-3.028l-.722-.187V3.467c1.122.11 1.879.714 2.07 1.616h1.47c-.166-1.6-1.54-2.748-3.54-2.875V1H7.591v1.233c-1.939.23-3.27 1.472-3.27 3.156 0 1.454.966 2.483 2.661 2.917l.61.162v4.031c-1.149-.17-1.94-.8-2.131-1.718zm3.391-3.836c-1.043-.263-1.6-.825-1.6-1.616 0-.944.704-1.641 1.8-1.828v3.495l-.2-.05zm1.591 1.872c1.287.323 1.852.859 1.852 1.769 0 1.097-.826 1.828-2.2 1.939V8.73z",
}

def _svg(path_d: str, size: int = 40) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'fill="currentColor" viewBox="0 0 16 16"><path d="{path_d}"/></svg>'
    )

def _card(icon_d: str, label: str, value: str,
          delta: str = "", delta_type: str = "neutral") -> str:
    delta_cls = {
        "green":  "dash-delta-green",
        "red":    "dash-delta-red",
        "orange": "dash-delta-orange",
    }.get(delta_type, "dash-delta")
    delta_html = f'<p class="{delta_cls}">{delta}</p>' if delta else ""
    return f"""<div class="dash-card">
    <div class="dash-icon">{_svg(icon_d, 36)}</div>
    <div class="dash-body">
        <p class="dash-label">{label}</p>
        <p class="dash-value">{value}</p>{delta_html}
    </div>
</div>"""

def render(filter_conditions, bagian_pr_cond, bagian_po_cond, load_data, **kwargs):

        info_filter = kwargs.get('info_filter', 'Tidak ada filter spesifik')
        dept_cond   = kwargs.get('dept_cond', '1=1')
        pg_cond     = kwargs.get('pg_cond',   '1=1')
        
        info_filter = kwargs.get('info_filter', 'Tidak ada filter spesifik')
        date_from   = kwargs.get('date_from')
        date_to     = kwargs.get('date_to')
        
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:55px; margin-bottom: 0px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="45" height="45" fill="currentColor" class="bi bi-clipboard2-data-fill" viewBox="0 0 16 16" style="margin-bottom: 8px; margin-right: 12px;">
                    <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5m.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2"/>
                </svg>
                Warning & Action Required - SAP
            </h1>
        """, unsafe_allow_html=True)
        st.markdown(ALERT_CSS, unsafe_allow_html=True)
        st.markdown("<p style='font-size: 18px; color: gray;'>Halaman ini menampilkan anomali data dan dokumen yang membutuhkan tindakan segera!</p>", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("<br>", unsafe_allow_html=True) # Tambahan spasi

        # ══════════════════════════════════════════════════════════════════════
        # ALERT 1: PR > 30 hari belum ada PO
        # ══════════════════════════════════════════════════════════════════════
        title_col, btn_col = st.columns([10, 1]) # Mengubah rasio agar tidak dempet
        with title_col:
            st.markdown("""
                    <h1 style='display: flex; align-items: center; font-size:30px; margin-bottom: 0px;'>
                        <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 10px;">
                            <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0M9.283 4.002H7.971L6.072 5.385v1.271l1.834-1.318h.065V12h1.312z"/>
                        </svg>
                        PR Pending Mendekati Kadaluarsa (> 30 Hari)
                    </h1>
                """, unsafe_allow_html=True)
        with btn_col:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True) # Menyesuaikan tinggi tombol
            with st.popover(":material/visibility:", help="Lihat Formula"):
                st.info("""\
**PR Pending Mendekati Kadaluarsa (> 30 Hari)**: Menampilkan PR yang belum diproses menjadi PO dan sudah menunggu lebih dari 30 hari sejak dibuat.

**Kolom yang ditampilkan:**
| Kolom | Keterangan |
|---|---|
| `no_pr` | Nomor Purchase Requisition di SAP |
| `tgl_create_pr` | Tanggal PR dibuat |
| `department` | Kode departemen pemohon |
| `bagian` | Bagian/seksi pemohon |
| `estimasi_pr` | Nilai estimasi per baris PR (kolom `estimasi_pr`) |
| `umur_hari` | Selisih hari dari tanggal buat hingga hari ini |

**Formula Excel:** (PR SAP)
- Filter kolom **No PO** kosong
- Tambah kolom `=TODAY()-tgl_create_pr`
- Filter nilai > 30.
            """)

        st.caption("Menampilkan PR yang belum diproses menjadi PO selama lebih dari 30 hari sejak dibuat.")

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True) # Spasi sebelum tabel

        alert_pr_query = f"""
        SELECT
            no_pr, tgl_create_pr,
            department_code AS department,
            bagian_pr AS bagian,
            estimasi_pr,
            CURRENT_DATE - tgl_create_pr::DATE AS umur_hari
        FROM vw_pr_po_complete
        WHERE {filter_conditions} AND {bagian_pr_cond} AND nomor_po IS NULL AND no_pr != 'No PR'
        AND (CURRENT_DATE - tgl_create_pr::DATE) > 30
        ORDER BY umur_hari DESC
        """
        with st.spinner("Memuat alert PR..."):
            alert_pr_data = load_data(alert_pr_query)

        if not alert_pr_data.empty:
            alert_pr_data['tgl_create_pr'] = pd.to_datetime(alert_pr_data['tgl_create_pr']).dt.strftime('%Y-%m-%d')
            alert_pr_data['estimasi_pr'] = alert_pr_data['estimasi_pr'].apply(
                lambda x: f"Rp {x:,.0f}" if pd.notna(x) else ""
            )
            alert_pr_data.index = alert_pr_data.index + 1
            st.dataframe(
                alert_pr_data.rename(columns={
                    'no_pr':        'No PR',
                    'tgl_create_pr':'Tgl Dibuat',
                    'department':   'Department',
                    'bagian':       'Bagian',
                    'estimasi_pr':  'Estimasi (Rp)',
                    'umur_hari':    'Umur (Hari)',
                }),
                use_container_width=True, height=250
            )
        else:
            st.success("Aman! Tidak ada PR Pending yang umurnya lebih dari 30 hari.")

        st.markdown("<br><br>", unsafe_allow_html=True) # Jarak yang jelas antar section besar

        # ══════════════════════════════════════════════════════════════════════
        # ALERT 2 & 3: PO Overdue & Aging PO
        # ══════════════════════════════════════════════════════════════════════
        col_alert1, col_alert2 = st.columns([1.5, 1], gap="large")

        with col_alert1:
            title_col, btn_col = st.columns([8, 1]) # Rasio diubah
            with title_col:
                st.markdown("""
                    <h1 style='display: flex; align-items: center; font-size:30px; margin-bottom: 0px;'>
                        <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 10px;">
                            <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0M6.646 6.24c0-.691.493-1.306 1.336-1.306.756 0 1.313.492 1.313 1.236 0 .697-.469 1.23-.902 1.705l-2.971 3.293V12h5.344v-1.107H7.268v-.077l1.974-2.22.096-.107c.688-.763 1.287-1.428 1.287-2.43 0-1.266-1.031-2.215-2.613-2.215-1.758 0-2.637 1.19-2.637 2.402v.065h1.271v-.07Z"/>
                        </svg>
                        PO Overdue (Melewati Delivery Date)
                    </h1>
                """, unsafe_allow_html=True)
            with btn_col:
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                with st.popover(":material/visibility:", help="Lihat Formula"):
                    st.info("""\
**PO Overdue (Melewati Delivery Date)**: Menampilkan PO yang tanggal delivery-nya sudah lewat namun barang belum diterima semua (`Delivery Completed` belum `X`).

**Status `on_time_delivery`:**
| Status | Kondisi |
|---|---|
| `IN PROGRESS` | `Delivery Completed` belum `X` (belum diterima semua, bisa sebagian atau belum sama sekali) |
| `TEPAT WAKTU` | `Delivery Completed = X` dan `Tgl Terima Barang ≤ Del Date PO` |
| `TERLAMBAT` | `Delivery Completed = X` dan `Tgl Terima Barang > Del Date PO` |

**Kolom yang ditampilkan:**
| Kolom | Keterangan |
|---|---|
| `nomor_po` | Nomor Purchase Order |
| `item_po` | Item PO dari Nomor PO |
| `date_ordered` | Tanggal PO diterbitkan |
| `target_delivery` | Tanggal delivery yang disepakati (`del_date_po`) |
| `vendor_name` | Nama vendor pemasok |
| `on_time_delivery` | Status pengiriman saat ini |
| `hari_terlambat` | Jumlah hari melewati target delivery |

**Formula Excel:** (PO SAP)
- Filter kolom **Delivery Completed** kosong
- Tambah kolom `=TODAY()-del_date_po`
- Filter nilai positif.
                """)

            st.caption("Menampilkan PO yang tanggal kirimnya sudah lewat namun barang belum diterima.")

            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

            alert_po_query = f"""
            SELECT
                poh.nomor_po,
                poi.item_po,
                poh.date_ordered,
                poi.del_date_po AS target_delivery,
                v.vendor_name,
                poi.on_time_delivery,
                CURRENT_DATE - poi.del_date_po::DATE AS hari_terlambat
            FROM purchase_orders poh
            JOIN po_items poi ON poh.nomor_po = poi.nomor_po
            LEFT JOIN vendors v ON poh.vendor_code = v.vendor_code
            WHERE poi.del_date_po::DATE < CURRENT_DATE
            AND poi.on_time_delivery = 'IN PROGRESS'
            AND {bagian_po_cond.replace('bagian_po', 'poi.bagian_po')}
            AND poh.date_ordered::DATE >= '{date_from}'
            AND poh.date_ordered::DATE <= '{date_to}'
            AND {dept_cond}
            AND {pg_cond}
            ORDER BY hari_terlambat DESC, poh.nomor_po, poi.item_po
            """
            with st.spinner("Memuat PO overdue..."):
                alert_po_data = load_data(alert_po_query)

            if not alert_po_data.empty:
                alert_po_data['date_ordered']    = pd.to_datetime(alert_po_data['date_ordered']).dt.strftime('%Y-%m-%d')
                alert_po_data['target_delivery'] = pd.to_datetime(alert_po_data['target_delivery']).dt.strftime('%Y-%m-%d')
                alert_po_data.index = alert_po_data.index + 1
                st.dataframe(
                    alert_po_data.rename(columns={
                        'nomor_po':       'No PO',
                        'item_po':        'Item',
                        'date_ordered':   'Tgl PO',
                        'target_delivery':'Target Delivery',
                        'vendor_name':    'Vendor',
                        'on_time_delivery':'Status',
                        'hari_terlambat': 'Terlambat (Hari)',
                    }),
                    use_container_width=True, height=400
                )
            else:
                st.success("Aman! Tidak ada PO yang terlambat dari jadwal.")

        with col_alert2:
            title_col, btn_col = st.columns([7, 1]) # Rasio diubah
            with title_col:
                st.markdown("""
                    <h1 style='display: flex; align-items: center; font-size:30px; margin-bottom: 0px;'>
                        <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 10px;">
                            <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0m-8.082.414c.92 0 1.535.54 1.541 1.318.012.791-.615 1.36-1.588 1.354-.861-.006-1.482-.469-1.54-1.066H5.104c.047 1.177 1.05 2.144 2.754 2.144 1.653 0 2.954-.937 2.93-2.396-.023-1.278-1.031-1.846-1.734-1.916v-.07c.597-.1 1.505-.739 1.482-1.876-.03-1.177-1.043-2.074-2.637-2.062-1.675.006-2.59.984-2.625 2.12h1.248c.036-.556.557-1.054 1.348-1.054.785 0 1.348.486 1.348 1.195.006.715-.563 1.237-1.342 1.237h-.838v1.072h.879Z"/>
                        </svg>
                        Rekap Aging PO (Belum Dikirim)
                    </h1>
                """, unsafe_allow_html=True)
            with btn_col:
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                with st.popover(":material/visibility:", help="Lihat Formula"):
                    st.info("""\
**Rekap Aging PO (Belum Dikirim)**: Bar chart jumlah PO yang belum diterima semua, dikelompokkan per rentang umur sejak PO diterbitkan.

**Formula Excel:** (PO SAP)
- Filter kolom **Delivery Completed** kosong
- Tambah kolom `=TODAY()-date ordered`
- Filter nilai sesuai dengan rangenya.
                        
**Cara membaca chart:**
| Bucket | Status |
|---|---|
| 0–15 Hari | Masih sangat baru, belum perlu tindakan |
| 16–30 Hari | Pantau berkala |
| 31–60 Hari | Follow-up aktif ke vendor |
| > 60 Hari | 🔴 Kritis, eskalasi segera ke atasan/tim vendor |

                """)

            st.caption("Jumlah PO yang belum dikirim")

            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

            aging_query = f"""
            SELECT
                CASE
                    WHEN CURRENT_DATE - poh.date_ordered::DATE <= 15 THEN '0-15 Hari'
                    WHEN CURRENT_DATE - poh.date_ordered::DATE <= 30 THEN '16-30 Hari'
                    WHEN CURRENT_DATE - poh.date_ordered::DATE <= 60 THEN '31-60 Hari'
                    ELSE '> 60 Hari'
                END AS umur_po,
                COUNT(*) AS total_item
            FROM purchase_orders poh
            JOIN po_items poi ON poh.nomor_po = poi.nomor_po
            WHERE poi.on_time_delivery = 'IN PROGRESS'
            AND {bagian_po_cond.replace('bagian_po', 'poi.bagian_po')}
            AND poh.date_ordered::DATE >= '{date_from}'
            AND poh.date_ordered::DATE <= '{date_to}'
            AND {dept_cond}
            AND {pg_cond}
            GROUP BY 1
            ORDER BY 1
            """
            with st.spinner("Memuat aging PO..."):
                aging_data = load_data(aging_query)

            if not aging_data.empty:
                category_aging = ['0-15 Hari', '16-30 Hari', '31-60 Hari', '> 60 Hari']
                
                fig = px.bar(
                    aging_data, x='umur_po', y='total_item',
                    labels={'umur_po': 'Aging (Hari)', 'total_item': 'Jumlah Item PO'},
                    text_auto=True,
                    category_orders={'umur_po': category_aging}
                )
                
                fig.update_layout(
                    height=400,
                    margin=dict(t=20, b=20, l=20, r=20)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Tidak ada data aging PO.")

        st.markdown("<br><br>", unsafe_allow_html=True)

        # ══════════════════════════════════════════════════════════════════════
        # MONITORING PO STATUS
        # ══════════════════════════════════════════════════════════════════════
        title_col, btn_col = st.columns([10, 1])
        with title_col:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:30px; margin-bottom: 0px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="currentColor" class="bi bi-diagram-3-fill" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 10px;">
                        <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0M7.519 5.057c-.886 1.418-1.772 2.838-2.542 4.265v1.12H8.85V12h1.26v-1.559h1.007V9.334H10.11V4.002H8.176zM6.225 9.281v.053H8.85V5.063h-.065c-.867 1.33-1.787 2.806-2.56 4.218"/>
                    </svg>
                    Monitoring PO Status
                </h1>
            """, unsafe_allow_html=True)
        with btn_col:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Lihat Formula"):
                st.info("""\
**Monitoring PO Status**: Menampilkan jumlah PO berdasarkan statusnya.

**Keterangan Nilai PO Status:**
| Nilai | Keterangan |
|---|---|
| `A` | PO aktif / dalam proses |
| `B` | PO selesai / closed |
| *(kosong)* | Status tidak diisi / belum ditentukan |

**Formula Excel:** (PO SAP)
- Filter **Material No** selain `1000076`
- Filter **PO Deletion Flag** selain `L`
- Filter **PO Status** sesuai yang diinginkan
            """)

        st.caption("Distribusi PO berdasarkan kolom PO Status dari Excel PO SAP.")

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        po_status_query = f"""
        SELECT
            COALESCE(NULLIF(TRIM(poh.po_status), ''), '(kosong)') AS po_status,
            COUNT(DISTINCT poh.nomor_po)                           AS jumlah_po,
            COUNT(poi.item_po)                                     AS jumlah_item
        FROM purchase_orders poh
        JOIN po_items poi ON poh.nomor_po = poi.nomor_po
        WHERE poh.date_ordered::DATE >= '{date_from}'
          AND poh.date_ordered::DATE <= '{date_to}'
          AND {bagian_po_cond.replace('bagian_po', 'poi.bagian_po')}
          AND {dept_cond}
          AND {pg_cond}
        GROUP BY 1
        ORDER BY
            CASE COALESCE(NULLIF(TRIM(poh.po_status), ''), '(kosong)')
                WHEN 'A' THEN 1
                WHEN 'B' THEN 2
                ELSE 3
            END
        """
        with st.spinner("Memuat Monitoring PO Status..."):
            po_status_data = load_data(po_status_query)

        if not po_status_data.empty:
            col_chart, col_tbl = st.columns([1.4, 1], gap="large")

            with col_chart:
                color_po   = {'A': '#1f77b4', 'B': '#09ab3b', '(kosong)': '#aaaaaa'}
                color_item = {'A': '#aec7e8', 'B': '#98e6b0', '(kosong)': '#dddddd'}
                colors_po   = [color_po.get(s, '#cccccc')   for s in po_status_data['po_status']]
                colors_item = [color_item.get(s, '#eeeeee') for s in po_status_data['po_status']]

                fig_status = go.Figure()
                fig_status.add_trace(go.Bar(
                    name='Jumlah PO',
                    x=po_status_data['po_status'],
                    y=po_status_data['jumlah_po'],
                    text=po_status_data['jumlah_po'],
                    textposition='outside',
                    marker_color=colors_po,
                    hovertemplate="<b>PO Status: %{x}</b><br>Jumlah PO: %{y}<extra></extra>",
                ))
                fig_status.add_trace(go.Bar(
                    name='Jumlah Item',
                    x=po_status_data['po_status'],
                    y=po_status_data['jumlah_item'],
                    text=po_status_data['jumlah_item'],
                    textposition='outside',
                    marker_color=colors_item,
                    marker_line_color=colors_po,
                    marker_line_width=1.5,
                    hovertemplate="<b>PO Status: %{x}</b><br>Jumlah Item: %{y}<extra></extra>",
                ))
                fig_status.update_layout(
                    barmode='group',
                    height=380,
                    xaxis_title="PO Status",
                    yaxis_title="Jumlah",
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                    margin=dict(t=40, b=20, l=20, r=20),
                )
                st.plotly_chart(fig_status, use_container_width=True)

            with col_tbl:
                st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
                total_po   = po_status_data['jumlah_po'].sum()
                total_item = po_status_data['jumlah_item'].sum()

                TH = 'padding:8px 12px;font-size:14px;font-weight:600;'
                P  = 'padding:8px 12px;border-bottom:1px solid rgba(128,128,128,0.2);font-size:14px;'
                thead = (
                    '<thead><tr style="border-bottom:2px solid rgba(128,128,128,0.4)">'
                    + f'<th style="{TH}text-align:left">PO Status</th>'
                    + f'<th style="{TH}text-align:center">Jumlah PO</th>'
                    + f'<th style="{TH}text-align:center">Jumlah Item</th>'
                    + f'<th style="{TH}text-align:center">% dari Total</th>'
                    + '</tr></thead>'
                )

                badge_color = {'A': '#1f77b4', 'B': '#09ab3b', '(kosong)': '#888888'}
                rows_parts = []
                for _, row in po_status_data.iterrows():
                    status = str(row['po_status'])
                    pct    = round(row['jumlah_po'] / total_po * 100, 1) if total_po > 0 else 0
                    bc     = badge_color.get(status, '#cccccc')
                    badge  = f'<span style="background:{bc};color:#fff;padding:2px 10px;border-radius:12px;font-size:13px;font-weight:600">{status}</span>'
                    rows_parts.append(
                        '<tr>'
                        + f'<td style="{P}">{badge}</td>'
                        + f'<td style="{P}text-align:center;font-weight:600">{int(row["jumlah_po"])}</td>'
                        + f'<td style="{P}text-align:center">{int(row["jumlah_item"])}</td>'
                        + f'<td style="{P}text-align:center">{pct}%</td>'
                        + '</tr>'
                    )

                rows_parts.append(
                    '<tr style="border-top:2px solid rgba(128,128,128,0.4);font-weight:700">'
                    + f'<td style="padding:8px 12px;font-size:14px">Total</td>'
                    + f'<td style="padding:8px 12px;font-size:14px;text-align:center">{int(total_po)}</td>'
                    + f'<td style="padding:8px 12px;font-size:14px;text-align:center">{int(total_item)}</td>'
                    + f'<td style="padding:8px 12px;font-size:14px;text-align:center">100%</td>'
                    + '</tr>'
                )

                tabel_html = (
                    '<table style="width:100%;border-collapse:collapse">'
                    + thead
                    + '<tbody>' + ''.join(rows_parts) + '</tbody>'
                    + '</table>'
                )
                st.markdown(tabel_html, unsafe_allow_html=True)
        else:
            st.info("Tidak ada data PO Status untuk filter yang dipilih.")

        # == Tabel List PO per Status ==========================================
        if not po_status_data.empty:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

            # Pilihan status untuk filter tabel
            available_statuses = po_status_data['po_status'].tolist()
            status_labels = {
                'A':        '🔵 A - Aktif / Dalam Proses',
                'B':        '🟢 B - Selesai / Closed',
                '(kosong)': '⚪ (kosong) - Belum Ditentukan',
            }

            title_col2, btn_col2 = st.columns([10, 1])
            with title_col2:
                st.markdown("""
                    <h1 style='display: flex; align-items: center; font-size:22px; margin-bottom: 0px;'>
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor"
                             viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                            <path d="M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0
                                     1-2-2zm15 2h-4v3h4zm0 4h-4v3h4zm0 4h-4v3h3a1 1 0 0 0 1-1zm-5 3v-3H6v3zm-5
                                     0v-3H1v2a1 1 0 0 0 1 1zm-4-4h4V8H1zm0-4h4V4H1zm5-3v3h4V4zm4 4H6v3h4z"/>
                        </svg>
                        List PO per Status
                    </h1>
                """, unsafe_allow_html=True)
            with btn_col2:
                with st.popover(":material/visibility:", help="Lihat Formula"):
                    st.info("""\
**List PO per Status**: Tabel detail semua PO untuk status yang dipilih.

**Kolom yang ditampilkan:**
| Kolom | Keterangan |
|---|---|
| `Nomor PO` | Nomor Purchase Order |
| `Tgl PO` | Tanggal PO diterbitkan (`Date Ordered`) |
| `PO Status` | Status PO: A (aktif), B (closed), atau kosong |
| `Vendor` | Nama vendor pemasok |
| `Purchasing Group` | Purchasing Group penerbit PO |
| `Jumlah Item` | Jumlah item/baris dalam PO tersebut |
| `Total Nilai (Rp)` | Total nilai realisasi PO dalam Rupiah |
| `Delivery Completed` | Apakah semua barang sudah diterima (X = ya) |

**Formula Excel:** (PO SAP)
- Filter **Material No** selain `1000076`
- Filter **PO Deletion Flag** selain `L`
- Filter **PO Status** sesuai yang dipilih
                """)

            st.caption("Pilih status untuk menampilkan daftar PO yang termasuk dalam kategori tersebut.")

            # Pills pemilih status - default pilih semua yang tersedia
            pill_opts = [s for s in ['A', 'B', '(kosong)'] if s in available_statuses]
            pill_labels = [status_labels.get(s, s) for s in pill_opts]

            selected_status_pill = st.pills(
                "Filter Status PO",
                options=pill_opts,
                format_func=lambda s: status_labels.get(s, s),
                selection_mode="multi",
                default=pill_opts,
                key="pill_po_status_filter",
                label_visibility="collapsed",
            )

            # Fallback jika tidak ada yang dipilih
            active_statuses = selected_status_pill if selected_status_pill else pill_opts

            # Query list PO
            status_in_sql = ", ".join(
                f"''" if s == '(kosong)' else f"'{s}'"
                for s in active_statuses
            )
            # Bangun kondisi WHERE untuk status kosong vs berisi
            status_where_parts = []
            for s in active_statuses:
                if s == '(kosong)':
                    status_where_parts.append("COALESCE(NULLIF(TRIM(poh.po_status), ''), '(kosong)') = '(kosong)'")
                else:
                    status_where_parts.append(f"TRIM(poh.po_status) = '{s}'")
            status_where = "(" + " OR ".join(status_where_parts) + ")" if status_where_parts else "1=0"

            list_po_query = f"""
            SELECT
                poh.nomor_po,
                poi.item_po,
                poh.date_ordered::DATE                                          AS tgl_po,
                poi.del_date_po                                                 AS due_date,
                COALESCE(NULLIF(TRIM(poh.po_status), ''), '(kosong)')           AS po_status,
                v.vendor_name,
                poh.purchasing_group,
                poi.description,
                poi.total_amount_local_curr                                     AS nilai_item,
                poi.on_time_delivery                                            AS delivery_completed
            FROM purchase_orders poh
            JOIN po_items poi ON poh.nomor_po = poi.nomor_po
            LEFT JOIN vendors v ON poh.vendor_code = v.vendor_code
            WHERE poh.date_ordered::DATE >= '{date_from}'
            AND poh.date_ordered::DATE <= '{date_to}'
            AND {bagian_po_cond.replace('bagian_po', 'poi.bagian_po')}
            AND {dept_cond}
            AND {pg_cond}
            AND {status_where}
            ORDER BY poh.date_ordered DESC, poh.nomor_po, poi.item_po
            LIMIT 1000
            """

            with st.spinner("Memuat list PO..."):
                list_po_data = load_data(list_po_query)

            if not list_po_data.empty:
                df_display_po = list_po_data.copy()
                df_display_po.index = df_display_po.index + 1
                df_display_po['tgl_po'] = pd.to_datetime(
                    df_display_po['tgl_po'], errors='coerce'
                ).dt.strftime('%Y-%m-%d')
                df_display_po['due_date'] = pd.to_datetime(
                    df_display_po['due_date'], errors='coerce'
                ).dt.strftime('%Y-%m-%d')
                df_display_po['nilai_item'] = df_display_po['nilai_item'].apply(
                    lambda x: f"Rp {x:,.0f}" if pd.notna(x) else ""
                )
                df_display_po['description'] = df_display_po['description'].str[:50] if 'description' in df_display_po.columns else ""

                count_label = f"Menampilkan **{len(df_display_po):,}** item PO"
                if len(df_display_po) == 1000:
                    count_label += " *(limit 1000, gunakan filter untuk mempersempit hasil)*"
                st.caption(count_label)

                st.dataframe(
                    df_display_po.rename(columns={
                        'nomor_po':           'Nomor PO',
                        'item_po':            'Item',
                        'tgl_po':             'Tgl PO',
                        'due_date':           'Due Date',
                        'po_status':          'PO Status',
                        'vendor_name':        'Vendor',
                        'purchasing_group':   'Purchasing Group',
                        'description':        'Deskripsi',
                        'nilai_item':         'Nilai Item (Rp)',
                        'delivery_completed': 'Status Pengiriman',
                    }),
                    use_container_width=True,
                    height=380,
                )

                # Download XLSX
                xlsx_list_po = list_po_data.copy()
                xlsx_list_po['tgl_po'] = pd.to_datetime(
                    xlsx_list_po['tgl_po'], errors='coerce'
                ).dt.strftime('%Y-%m-%d')
                xlsx_list_po['nilai_item'] = xlsx_list_po['nilai_item'].apply(
                    lambda x: f"Rp {x:,.0f}" if pd.notna(x) else ""
                )
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    xlsx_list_po.to_excel(writer, index=False, sheet_name='List_PO')
                excel_buffer.seek(0)
                
                st.download_button(
                    label="Download sebagai XLSX",
                    icon=":material/download:",
                    data=excel_buffer,
                    file_name=f"list_po_status_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                st.info("Tidak ada PO untuk status yang dipilih.")

        st.markdown("<br><br>", unsafe_allow_html=True)

        # ══════════════════════════════════════════════════════════════════════
        # GRAFIK PO TERLAMBAT
        # ══════════════════════════════════════════════════════════════════════
        title_col, btn_col = st.columns([10, 1])
        with title_col:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:30px; margin-bottom: 0px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="currentColor" class="bi bi-graph-down-arrow" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 10px;">
                        <path fill-rule="evenodd" d="M0 0h1v15h15v1H0zm10 11.5a.5.5 0 0 0 .5.5h4a.5.5 0 0 0 .5-.5v-4a.5.5 0 0 0-1 0v2.6l-3.613-4.417a.5.5 0 0 0-.74-.037L7.06 8.233 3.404 3.206a.5.5 0 0 0-.808.588l4 5.5a.5.5 0 0 0 .758.06l2.609-2.61L13.445 11H10.5a.5.5 0 0 0-.5.5"/>
                    </svg>
                    Grafik PO Terlambat
                </h1>
            """, unsafe_allow_html=True)
        with btn_col:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Lihat Formula"):
                st.info("""\
**Grafik PO Terlambat**: Menampilkan visualisasi PO yang sudah melewati delivery date namun barang belum diterima semua (`on_time_delivery = 'IN PROGRESS'` dan `del_date_po < hari ini`).

**Tiga chart yang ditampilkan:**
| Chart | Keterangan |
|---|---|
| Distribusi Keterlambatan (Bucket) | Jumlah item PO berdasarkan rentang hari terlambat: 1-7, 8-30, 31-60, >60 hari |
| Top 10 Purchasing Group Terlambat | PG dengan jumlah item PO terlambat terbanyak |
| Top 10 Vendor Terlambat | Vendor dengan jumlah item PO terlambat terbanyak, membantu evaluasi performa vendor |

**Formula Excel:** (PO SAP)
- Filter **Delivery Completed** kosong / bukan `X`
- Filter **Del Date PO** sebelum hari ini
- Tambah kolom `=TODAY()-Del Date PO`
- Kelompokkan per rentang hari
            """)

        st.caption("Visualisasi PO yang sudah melewati delivery date berdasarkan keterlambatan, purchasing group, dan vendor.")

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        grafik_terlambat_query = f"""
        SELECT
            poi.nomor_po,
            poi.item_po,
            poh.purchasing_group,
            v.vendor_name,
            poi.del_date_po,
            (CURRENT_DATE - poi.del_date_po::DATE)  AS hari_terlambat,
            poi.total_amount_local_curr
        FROM po_items poi
        JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
        LEFT JOIN vendors v ON poh.vendor_code = v.vendor_code
        WHERE poi.del_date_po::DATE < CURRENT_DATE
          AND poi.on_time_delivery = 'IN PROGRESS'
          AND {bagian_po_cond.replace('bagian_po', 'poi.bagian_po')}
          AND poh.date_ordered::DATE >= '{date_from}'
          AND poh.date_ordered::DATE <= '{date_to}'
          AND {dept_cond}
          AND {pg_cond}
        """

        with st.spinner("Memuat grafik PO terlambat..."):
            grafik_terlambat_data = load_data(grafik_terlambat_query)

        if not grafik_terlambat_data.empty:
            col_dist, col_pg, col_vendor = st.columns(3)

            # == Chart 1: Distribusi bucket keterlambatan ==
            with col_dist:
                st.markdown("**Distribusi Keterlambatan**")
                grafik_terlambat_data['bucket'] = pd.cut(
                    grafik_terlambat_data['hari_terlambat'],
                    bins=[0, 7, 30, 60, float('inf')],
                    labels=['1–7 Hari', '8–30 Hari', '31–60 Hari', '> 60 Hari'],
                    right=True
                )
                bucket_counts = (grafik_terlambat_data['bucket']
                                 .value_counts()
                                 .reindex(['1–7 Hari', '8–30 Hari', '31–60 Hari', '> 60 Hari'])
                                 .reset_index())
                bucket_counts.columns = ['bucket', 'jumlah']
                fig_dist = px.bar(
                    bucket_counts, x='bucket', y='jumlah',
                    text_auto=True,
                    color='jumlah',
                    color_continuous_scale=[[0, '#09ab3b'], [0.33, '#f0a500'], [1, '#e03c3c']],
                    labels={'bucket': 'Rentang Keterlambatan', 'jumlah': 'Jumlah Item PO'},
                )
                fig_dist.update_coloraxes(showscale=False)
                fig_dist.update_traces(textposition='outside')
                fig_dist.update_layout(
                    height=320, margin=dict(t=20, b=20, l=20, r=20),
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font_color='gray',
                    xaxis=dict(gridcolor='rgba(128,128,128,0.15)'),
                    yaxis=dict(gridcolor='rgba(128,128,128,0.15)'),
                )
                st.plotly_chart(fig_dist, use_container_width=True)

            # == Chart 2: Top 10 Purchasing Group terlambat ==
            with col_pg:
                st.markdown("**Top 10 Purchasing Group**")
                pg_late = (grafik_terlambat_data
                           .groupby('purchasing_group')
                           .agg(jumlah=('item_po', 'count'),
                                avg_hari=('hari_terlambat', 'mean'))
                           .reset_index()
                           .sort_values('jumlah', ascending=False)
                           .head(10))
                pg_late['avg_hari'] = pg_late['avg_hari'].round(1)
                pg_late = pg_late.sort_values('jumlah', ascending=True)
                fig_pg_late = px.bar(
                    pg_late, x='jumlah', y='purchasing_group', orientation='h',
                    text='jumlah',
                    color='avg_hari',
                    color_continuous_scale=[[0, '#f0a500'], [1, '#e03c3c']],
                    labels={'jumlah': 'Jml Item PO', 'purchasing_group': 'P. Group',
                            'avg_hari': 'Avg Hari Terlambat'},
                    custom_data=['avg_hari'],
                )
                fig_pg_late.update_traces(
                    textposition='outside',
                    hovertemplate='<b>%{y}</b><br>Jumlah: %{x}<br>Avg Terlambat: %{customdata[0]:.1f} hari<extra></extra>'
                )
                fig_pg_late.update_coloraxes(colorbar=dict(title='Avg Hari'))
                fig_pg_late.update_layout(
                    height=320, margin=dict(t=20, b=20, l=20, r=20),
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font_color='gray',
                    xaxis=dict(gridcolor='rgba(128,128,128,0.15)'),
                    yaxis=dict(title=''),
                )
                st.plotly_chart(fig_pg_late, use_container_width=True)

            # == Chart 3: Top 10 Vendor terlambat ==
            with col_vendor:
                st.markdown("**Top 10 Vendor Terlambat**")
                vendor_late = (grafik_terlambat_data
                               .dropna(subset=['vendor_name'])
                               .groupby('vendor_name')
                               .agg(jumlah=('item_po', 'count'),
                                    avg_hari=('hari_terlambat', 'mean'))
                               .reset_index()
                               .sort_values('jumlah', ascending=False)
                               .head(10))
                vendor_late['avg_hari'] = vendor_late['avg_hari'].round(1)
                vendor_late['label']    = vendor_late['vendor_name'].str[:22]
                vendor_late = vendor_late.sort_values('jumlah', ascending=True)
                fig_vnd_late = px.bar(
                    vendor_late, x='jumlah', y='label', orientation='h',
                    text='jumlah',
                    color='avg_hari',
                    color_continuous_scale=[[0, '#f0a500'], [1, '#e03c3c']],
                    labels={'jumlah': 'Jml Item PO', 'label': 'Vendor',
                            'avg_hari': 'Avg Hari Terlambat'},
                    custom_data=['avg_hari', 'vendor_name'],
                )
                fig_vnd_late.update_traces(
                    textposition='outside',
                    hovertemplate='<b>%{customdata[1]}</b><br>Jumlah: %{x}<br>Avg Terlambat: %{customdata[0]:.1f} hari<extra></extra>'
                )
                fig_vnd_late.update_coloraxes(colorbar=dict(title='Avg Hari'))
                fig_vnd_late.update_layout(
                    height=320, margin=dict(t=20, b=20, l=20, r=20),
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font_color='gray',
                    xaxis=dict(gridcolor='rgba(128,128,128,0.15)'),
                    yaxis=dict(title=''),
                )
                st.plotly_chart(fig_vnd_late, use_container_width=True)

            # Ringkasan metrik di bawah chart
            total_item_late  = len(grafik_terlambat_data)
            avg_hari_late    = grafik_terlambat_data['hari_terlambat'].mean()
            max_hari_late    = grafik_terlambat_data['hari_terlambat'].max()
            total_val_late   = grafik_terlambat_data['total_amount_local_curr'].sum()
            
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            
            # Menggunakan struktur _card yang baru
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(_card(
                    ICONS.get("kpi_outstanding_total", ""),
                    "Total Item PO Terlambat",
                    f"{total_item_late:,}",
                    "",
                    "neutral"
                ), unsafe_allow_html=True)
            with c2:
                st.markdown(_card(
                    ICONS.get("kpi_outstanding_kritis", ""),
                    "Rata-rata Keterlambatan",
                    f"{avg_hari_late:.1f} Hari",
                    "",
                    "red"
                ), unsafe_allow_html=True)
            with c3:
                st.markdown(_card(
                    ICONS.get("kpi_outstanding_pantau", ""),
                    "Keterlambatan Terpanjang",
                    f"{int(max_hari_late)} Hari",
                    "",
                    "orange"
                ), unsafe_allow_html=True)
            with c4:
                st.markdown(_card(
                    ICONS.get("kpi_outstanding_nilai", ""),
                    "Total Nilai PO Terlambat",
                    format_idr(total_val_late),
                    "",
                    "neutral"
                ), unsafe_allow_html=True)

        else:
            st.success("Bagus! Tidak ada PO yang melewati delivery date saat ini.")

        st.markdown("<br><br>", unsafe_allow_html=True)

        # ══════════════════════════════════════════════════════════════════════
        # TABEL PO OUTSTANDING (belum GR, belum melewati due date)
        # ══════════════════════════════════════════════════════════════════════
        title_col, btn_col = st.columns([10, 1])
        with title_col:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:30px; margin-bottom: 0px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="currentColor" class="bi bi-hourglass-split" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 10px;">
                        <path d="M2.5 15a.5.5 0 1 1 0-1h1v-1a4.5 4.5 0 0 1 2.557-4.06c.29-.139.443-.377.443-.59v-.7c0-.213-.154-.451-.443-.59A4.5 4.5 0 0 1 3.5 3V2h-1a.5.5 0 0 1 0-1h11a.5.5 0 0 1 0 1h-1v1a4.5 4.5 0 0 1-2.557 4.06c-.29.139-.443.377-.443.59v.7c0 .213.154.451.443.59A4.5 4.5 0 0 1 12.5 13v1h1a.5.5 0 0 1 0 1zm2-13v1a3.5 3.5 0 0 0 1.989 3.158c.533.256 1.011.791 1.011 1.342v.7c0 .55-.478 1.086-1.011 1.342A3.5 3.5 0 0 0 4.5 13v1h7v-1a3.5 3.5 0 0 0-1.989-3.158C8.978 9.586 8.5 9.051 8.5 8.5v-.7c0-.55.478-1.086 1.011-1.342A3.5 3.5 0 0 0 11.5 3V2z"/>
                    </svg>
                    PO Outstanding (Belum GR, Belum Jatuh Tempo)
                </h1>
            """, unsafe_allow_html=True)
        with btn_col:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Lihat Formula"):
                st.info("""\
**PO Outstanding (Belum GR, Belum Jatuh Tempo)**: Menampilkan PO yang kondisinya:
- `on_time_delivery = 'IN PROGRESS'` → barang belum diterima semua
- `del_date_po >= hari ini` → delivery date belum terlewati

Ini adalah daftar PO yang **masih aman** tapi perlu dimonitor agar tidak berubah menjadi overdue.

**Kolom yang ditampilkan:**
| Kolom | Keterangan |
|---|---|
| `Nomor PO` | Nomor Purchase Order |
| `Item` | Item/baris PO |
| `Tgl PO` | Tanggal PO diterbitkan |
| `Target Delivery` | Tanggal delivery yang disepakati |
| `Sisa Hari` | Berapa hari lagi sebelum jatuh tempo (makin kecil = makin mendesak) |
| `Vendor` | Nama vendor |
| `P. Group` | Purchasing Group |
| `Nilai PO (Rp)` | Nilai realisasi item PO |
| `Status Pengiriman` | Status pengiriman saat ini |

**Formula Excel:** (PO SAP)
- Filter **Delivery Completed** kosong / bukan `X`
- Filter **Del Date PO** lebih besar sama dengan hari ini
- Tambah kolom `=Del Date PO - TODAY()` untuk menghitung sisa hari

**Catatan:** Urutkan berdasarkan sisa hari terkecil untuk mengetahui PO mana yang paling mendesak di-follow up.
            """)

        st.caption("PO yang barangnya belum diterima (IN PROGRESS) namun masih dalam batas delivery date - perlu dipantau agar tidak berubah menjadi overdue.")

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        # Filter sisa hari - pills untuk memilih rentang
        sisa_hari_opts = ["Semua", "≤ 7 Hari", "8–14 Hari", "15–30 Hari", "> 30 Hari"]
        selected_sisa = st.pills(
            "Filter Sisa Hari",
            options=sisa_hari_opts,
            default="Semua",
            key="pill_po_outstanding_sisa",
            label_visibility="collapsed",
        )
        if not selected_sisa:
            selected_sisa = "Semua"

        # Bangun kondisi sisa hari
        if selected_sisa == "≤ 7 Hari":
            sisa_cond = "AND (poi.del_date_po::DATE - CURRENT_DATE) <= 7"
        elif selected_sisa == "8–14 Hari":
            sisa_cond = "AND (poi.del_date_po::DATE - CURRENT_DATE) BETWEEN 8 AND 14"
        elif selected_sisa == "15–30 Hari":
            sisa_cond = "AND (poi.del_date_po::DATE - CURRENT_DATE) BETWEEN 15 AND 30"
        elif selected_sisa == "> 30 Hari":
            sisa_cond = "AND (poi.del_date_po::DATE - CURRENT_DATE) > 30"
        else:
            sisa_cond = ""

        outstanding_query = f"""
        SELECT
            poh.nomor_po,
            poi.item_po,
            poh.date_ordered::DATE                                  AS tgl_po,
            poi.del_date_po                                         AS target_delivery,
            (poi.del_date_po::DATE - CURRENT_DATE)::INT             AS sisa_hari,
            v.vendor_name,
            poh.purchasing_group,
            poi.description                                         AS deskripsi,
            poi.total_amount_local_curr                             AS nilai_po,
            poi.on_time_delivery                                    AS status_pengiriman
        FROM po_items poi
        JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
        LEFT JOIN vendors v ON poh.vendor_code = v.vendor_code
        WHERE poi.del_date_po::DATE >= CURRENT_DATE
          AND poi.on_time_delivery = 'IN PROGRESS'
          AND {bagian_po_cond.replace('bagian_po', 'poi.bagian_po')}
          AND poh.date_ordered::DATE >= '{date_from}'
          AND poh.date_ordered::DATE <= '{date_to}'
          AND {dept_cond}
          AND {pg_cond}
          {sisa_cond}
        ORDER BY sisa_hari ASC, poh.nomor_po, poi.item_po
        LIMIT 1000
        """

        with st.spinner("Memuat PO Outstanding..."):
            outstanding_data = load_data(outstanding_query)

        if not outstanding_data.empty:
            # KPI ringkasan outstanding
            total_outstanding  = len(outstanding_data)
            kritis_7           = int((outstanding_data['sisa_hari'] <= 7).sum())
            perlu_pantau       = int(((outstanding_data['sisa_hari'] > 7) & (outstanding_data['sisa_hari'] <= 30)).sum())
            total_val_outs     = outstanding_data['nilai_po'].sum()

            # Menggunakan struktur _card yang baru
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(_card(
                    ICONS.get("kpi_outstanding_total", ""),
                    "Total Item PO Outstanding",
                    f"{total_outstanding:,}",
                    "",
                    "neutral"
                ), unsafe_allow_html=True)
            with c2:
                st.markdown(_card(
                    ICONS.get("kpi_outstanding_kritis", ""),
                    "Kritis (≤ 7 Hari)",
                    f"{kritis_7:,}",
                    "Perlu follow-up segera" if kritis_7 > 0 else "Aman",
                    "red" if kritis_7 > 0 else "green"
                ), unsafe_allow_html=True)
            with c3:
                st.markdown(_card(
                    ICONS.get("kpi_outstanding_pantau", ""),
                    "Perlu Pantau (8–30 Hari)",
                    f"{perlu_pantau:,}",
                    "",
                    "orange"
                ), unsafe_allow_html=True)
            with c4:
                st.markdown(_card(
                    ICONS.get("kpi_outstanding_nilai", ""),
                    "Total Nilai Outstanding",
                    format_idr(total_val_outs),
                    "",
                    "neutral"
                ), unsafe_allow_html=True)

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            # Format kolom untuk tampilan
            df_outs_display = outstanding_data.copy()
            df_outs_display.index = df_outs_display.index + 1
            df_outs_display['tgl_po']          = pd.to_datetime(df_outs_display['tgl_po'], errors='coerce').dt.strftime('%Y-%m-%d')
            df_outs_display['target_delivery'] = pd.to_datetime(df_outs_display['target_delivery'], errors='coerce').dt.strftime('%Y-%m-%d')
            df_outs_display['nilai_po']        = df_outs_display['nilai_po'].apply(
                lambda x: f"Rp {x:,.0f}" if pd.notna(x) else ""
            )
            df_outs_display['deskripsi']       = df_outs_display['deskripsi'].str[:50]

            # 1. RENAME DATAFRAME TERLEBIH DAHULU
            df_outs_renamed = df_outs_display.rename(columns={
                'nomor_po':         'Nomor PO',
                'item_po':          'Item',
                'tgl_po':           'Tgl PO',
                'target_delivery':  'Target Delivery',
                'sisa_hari':        'Sisa Hari',  # Nama baru
                'vendor_name':      'Vendor',
                'purchasing_group': 'P. Group',
                'deskripsi':        'Deskripsi',
                'nilai_po':         'Nilai PO (Rp)',
                'status_pengiriman':'Status Pengiriman',
            })

            # Warnai sisa hari berdasarkan urgensi
            def _color_sisa(val):
                try:
                    v = int(val)
                    if v <= 7:   return "color: #e03c3c; font-weight:700"
                    if v <= 14:  return "color: #f0a500; font-weight:600"
                    if v <= 30:  return "color: #1f77b4"
                    return ""
                except:
                    return ""

            # 2. TERAPKAN STYLE PADA DATAFRAME YANG SUDAH DI-RENAME (Gunakan subset 'Sisa Hari')
            styled_outs = df_outs_renamed.style.map(_color_sisa, subset=['Sisa Hari'])

            count_label_outs = f"Menampilkan **{total_outstanding:,}** item PO outstanding"
            if total_outstanding == 1000:
                count_label_outs += " *(limit 1000, gunakan filter untuk mempersempit)*"
            st.caption(count_label_outs)

            # 3. RENDER DATAFRAME
            st.dataframe(
                styled_outs,
                use_container_width=True,
                height=380,
            )

            # Download XLSX
            xlsx_outs = outstanding_data.copy()
            xlsx_outs['tgl_po']          = pd.to_datetime(xlsx_outs['tgl_po'], errors='coerce').dt.strftime('%Y-%m-%d')
            xlsx_outs['target_delivery'] = pd.to_datetime(xlsx_outs['target_delivery'], errors='coerce').dt.strftime('%Y-%m-%d')
            xlsx_outs['nilai_po']        = xlsx_outs['nilai_po'].apply(
                lambda x: f"Rp {x:,.0f}" if pd.notna(x) else ""
            )
            
            excel_buffer_outs = io.BytesIO()
            with pd.ExcelWriter(excel_buffer_outs, engine='openpyxl') as writer:
                xlsx_outs.to_excel(writer, index=False, sheet_name='PO_Outstanding')
            excel_buffer_outs.seek(0)

            st.download_button(
                label="Download PO Outstanding sebagai XLSX",
                icon=":material/download:",
                data=excel_buffer_outs,
                file_name=f"po_outstanding_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.success("Tidak ada PO outstanding dalam filter yang dipilih.")

        st.markdown("---")

        # =====================================================================
        # INTEGRASI AI: KUMPULKAN KONTEKS & PANGGIL CHAT
        # =====================================================================
        
        konteks_lines = []
        
        # 0. Rangkuman Filter
        konteks_lines.append("## 0. FILTER YANG SEDANG DITERAPKAN USER")
        konteks_lines.append(info_filter)
        konteks_lines.append("\n")

        # 1. Alert PR Kadaluarsa
        if 'alert_pr_data' in locals() and not alert_pr_data.empty:
            konteks_lines.append(f"## 1. ALERT: PR PENDING > 30 HARI (Total: {len(alert_pr_data)} PR)")
            # Ambil maksimal 15 baris untuk menghemat token
            df_pr_simple = alert_pr_data[['no_pr', 'department', 'umur_hari', 'estimasi_pr']].head(15)
            konteks_lines.append(df_pr_simple.to_csv(index=False))
            konteks_lines.append("\n")
        else:
            konteks_lines.append("## 1. ALERT: PR PENDING > 30 HARI\nAman. Tidak ada PR pending > 30 hari.\n")

        # 2. Alert PO Overdue
        if 'alert_po_data' in locals() and not alert_po_data.empty:
            konteks_lines.append(f"## 2. ALERT: PO OVERDUE / TERLAMBAT (Total: {len(alert_po_data)} PO)")
            # Ambil kolom esensial maksimal 20 baris
            df_po_simple = alert_po_data[['nomor_po', 'vendor_name', 'target_delivery', 'hari_terlambat']].head(20)
            konteks_lines.append(df_po_simple.to_csv(index=False))
            konteks_lines.append("\n")
        else:
            konteks_lines.append("## 2. ALERT: PO OVERDUE\nAman. Tidak ada PO overdue/terlambat pengiriman.\n")

        # 3. Alert Aging PO
        if 'aging_data' in locals() and not aging_data.empty:
            konteks_lines.append("## 3. RINGKASAN AGING PO (BELUM DIKIRIM)")
            konteks_lines.append(aging_data.to_csv(index=False))
            konteks_lines.append("\n")
        else:
            konteks_lines.append("## 3. RINGKASAN AGING PO\nTidak ada data aging PO.\n")

        # 4. Monitoring PO Status
        if 'po_status_data' in locals() and not po_status_data.empty:
            konteks_lines.append("## 4. MONITORING PO STATUS")
            konteks_lines.append(po_status_data.to_csv(index=False))
            konteks_lines.append("\n")
        else:
            konteks_lines.append("## 4. MONITORING PO STATUS\nTidak ada data PO Status.\n")

        # 5. List PO per Status
        if 'list_po_data' in locals() and not list_po_data.empty:
            konteks_lines.append(f"## 5. LIST PO PER STATUS (Top 20 terbaru)")
            df_list_simple = list_po_data[['nomor_po', 'item_po', 'tgl_po', 'po_status', 'vendor_name',
                                           'purchasing_group', 'nilai_item']].head(20)
            konteks_lines.append(df_list_simple.to_csv(index=False))
            konteks_lines.append("\n")
        else:
            konteks_lines.append("## 5. LIST PO PER STATUS\nTidak ada data list PO.\n")

        # 6. Grafik PO Terlambat
        if 'grafik_terlambat_data' in locals() and not grafik_terlambat_data.empty:
            konteks_lines.append(f"## 6. GRAFIK PO TERLAMBAT (Total: {len(grafik_terlambat_data)} item)")
            summary_late = grafik_terlambat_data.groupby('purchasing_group').agg(
                jumlah=('item_po', 'count'),
                avg_hari=('hari_terlambat', 'mean')
            ).reset_index().sort_values('jumlah', ascending=False).head(10)
            summary_late['avg_hari'] = summary_late['avg_hari'].round(1)
            konteks_lines.append(summary_late.to_csv(index=False))
            konteks_lines.append("")
        else:
            konteks_lines.append("## 6. GRAFIK PO TERLAMBAT\nTidak ada PO yang melewati delivery date.\n")

        # 7. PO Outstanding
        if 'outstanding_data' in locals() and not outstanding_data.empty:
            konteks_lines.append(f"## 7. PO OUTSTANDING (Belum GR, Belum Jatuh Tempo) (Total: {len(outstanding_data)} item)")
            df_outs_ai = outstanding_data[['nomor_po', 'item_po', 'target_delivery', 'sisa_hari',
                                           'vendor_name', 'purchasing_group', 'nilai_po']].head(20)
            konteks_lines.append(df_outs_ai.to_csv(index=False))
            konteks_lines.append("")
        else:
            konteks_lines.append("## 7. PO OUTSTANDING\nTidak ada PO outstanding dalam filter ini.\n")

        # Gabungkan konteks lokal halaman ini dengan konteks global lintas sistem
        suplemen = "\n# SUPLEMEN - DETAIL HALAMAN INI (Alert)\n" + "\n".join(konteks_lines)
        konteks_final = kwargs.get("global_context", "") + "\n---\n" + suplemen


        # Render chat di bawah halaman Alert SAP
        with st.expander("Tanya ke Melati (Monitoring, Evaluasi, Laporan Terintegrasi)"):
            render_chat_analyst(
                konteks_data_teks=konteks_final,
                nama_halaman="Halaman Alert (Warning & Action Required - SAP)",
                load_data_fn=load_data,
            )