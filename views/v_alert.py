"""
v_alert.py - Halaman Alert
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from utils import format_idr, format_idr_short


def render(filter_conditions, bagian_pr_cond, bagian_po_cond, load_data, **kwargs):
        
        # Fungsi helper untuk tombol toggle formula
        def toggle_state(state_key):
            st.session_state[state_key] = not st.session_state[state_key]

        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:55px; margin-bottom: 0px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="45" height="45" fill="currentColor" class="bi bi-clipboard2-data-fill" viewBox="0 0 16 16" style="margin-bottom: 8px; margin-right: 12px;">
                    <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5m.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2"/>
                </svg>
                Warning & Action Required
            </h1>
        """, unsafe_allow_html=True)
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
            key_alert_pr = "show_formula_alert_pr"
            if key_alert_pr not in st.session_state:
                st.session_state[key_alert_pr] = False
            is_open = st.session_state[key_alert_pr]
            icon = ":material/visibility_off:" if is_open else ":material/visibility:"
            tooltip = "Hide Formula" if is_open else "Show Formula"
            st.button(icon, key=f"btn_{key_alert_pr}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_alert_pr})

        st.caption("Menampilkan PR yang belum diproses menjadi PO selama lebih dari 30 hari sejak dibuat.")
        
        if st.session_state.get(key_alert_pr, False):
            st.info("""\
**PR Pending Mendekati Kadaluarsa (> 30 Hari)**: Menampilkan PR yang belum diproses menjadi PO dan sudah menunggu lebih dari 30 hari sejak dibuat.

**Kalkulasi SQL:**
```sql
umur_hari = CURRENT_DATE - tgl_create_pr::DATE
Filter : nomor_po IS NULL           -- belum ada PO
     AND no_pr != 'No PR'           -- bukan baris fiktif
     AND umur_hari > 30             -- lebih dari 30 hari
ORDER BY umur_hari DESC             -- yang paling lama di atas
```

**Kolom yang ditampilkan:**
| Kolom | Keterangan |
|---|---|
| `no_pr` | Nomor Purchase Requisition di SAP |
| `tgl_create_pr` | Tanggal PR dibuat |
| `department` | Kode departemen pemohon |
| `bagian` | Bagian/seksi pemohon |
| `estimasi_pr` | Nilai estimasi per baris PR (kolom `estimasi_pr`) |
| `umur_hari` | Selisih hari dari tanggal buat hingga hari ini |

Di Excel: filter kolom *No PO* kosong → tambah kolom `=TODAY()-tgl_create_pr` → filter nilai > 30.
            """)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True) # Spasi sebelum tabel

        alert_pr_query = f"""
        SELECT
            no_pr, tgl_create_pr,
            department_code AS department,
            bagian_pr AS bagian,
            estimasi_pr,
            CURRENT_DATE - tgl_create_pr::DATE AS umur_hari
        FROM vw_pr_po_complete
        WHERE {filter_conditions} AND nomor_po IS NULL AND no_pr != 'No PR'
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
            st.dataframe(alert_pr_data, use_container_width=True, height=250)
        else:
            st.success("Aman! Tidak ada PR Pending yang umurnya lebih dari 30 hari.")

        st.markdown("<br><br>", unsafe_allow_html=True) # Jarak yang jelas antar section besar

        # ══════════════════════════════════════════════════════════════════════
        # ALERT 2 & 3: PO Overdue & Aging PO
        # ══════════════════════════════════════════════════════════════════════
        # Menggunakan gap="large" agar antar kolom ada jarak bernapas
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
                key_alert_po = "show_formula_alert_po"
                if key_alert_po not in st.session_state:
                    st.session_state[key_alert_po] = False
                is_open = st.session_state[key_alert_po]
                icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                tooltip = "Hide Formula" if is_open else "Show Formula"
                st.button(icon, key=f"btn_{key_alert_po}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_alert_po})

            st.caption("Menampilkan PO yang tanggal kirimnya sudah lewat namun barang belum diterima.")

            if st.session_state.get(key_alert_po, False):
                st.info("""\
**PO Overdue (Melewati Delivery Date)**: Menampilkan PO yang tanggal delivery-nya sudah lewat namun barang belum masuk Good Receipt (GR).

**Kalkulasi SQL:**
```sql
hari_terlambat = CURRENT_DATE - del_date_po::DATE
Filter : del_date_po::DATE < CURRENT_DATE
     AND on_time_delivery IN ('TERLAMBAT', 'IN PROGRESS')
ORDER BY hari_terlambat DESC
```

**Kolom yang ditampilkan:**
| Kolom | Keterangan |
|---|---|
| `nomor_po` | Nomor Purchase Order |
| `date_ordered` | Tanggal PO diterbitkan |
| `target_delivery` | Tanggal delivery yang disepakati (`del_date_po`) |
| `vendor_name` | Nama vendor pemasok |
| `on_time_delivery` | Status pengiriman saat ini |
| `hari_terlambat` | Jumlah hari keterlambatan dari tanggal target |

Di Excel: tambah kolom `=TODAY()-del_date_po` → filter nilai positif dan status belum selesai.
                """)

            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

            alert_po_query = f"""
            SELECT
                v.nomor_po,
                v.date_ordered,
                p.del_date_po AS target_delivery,
                v.vendor_name,
                v.on_time_delivery,
                CURRENT_DATE - p.del_date_po::DATE AS hari_terlambat
            FROM vw_pr_po_complete v
            LEFT JOIN purchase_orders p ON v.nomor_po = p.nomor_po
            WHERE {filter_conditions}
            AND v.nomor_po IS NOT NULL
            AND p.del_date_po::DATE < CURRENT_DATE
            AND v.on_time_delivery IN ('TERLAMBAT', 'IN PROGRESS')
            GROUP BY 1, 2, 3, 4, 5, 6
            ORDER BY hari_terlambat DESC
            """
            with st.spinner("Memuat PO overdue..."):
                alert_po_data = load_data(alert_po_query)

            if not alert_po_data.empty:
                alert_po_data['date_ordered']    = pd.to_datetime(alert_po_data['date_ordered']).dt.strftime('%Y-%m-%d')
                alert_po_data['target_delivery'] = pd.to_datetime(alert_po_data['target_delivery']).dt.strftime('%Y-%m-%d')
                st.dataframe(alert_po_data, use_container_width=True, height=400)
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
                key_alert_aging = "show_formula_alert_aging"
                if key_alert_aging not in st.session_state:
                    st.session_state[key_alert_aging] = False
                is_open = st.session_state[key_alert_aging]
                icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                tooltip = "Hide Formula" if is_open else "Show Formula"
                st.button(icon, key=f"btn_{key_alert_aging}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_alert_aging})

            if st.session_state.get(key_alert_aging, False):
                st.info("""\
**Rekap Aging PO (Belum Dikirim)**: Bar chart jumlah PO yang belum dikirim dikelompokkan per rentang umur.

**Kalkulasi SQL:**
```sql
aging_days = CURRENT_DATE − date_ordered::DATE

CASE
  WHEN aging_days <= 15 THEN '0-15 Hari'
  WHEN aging_days <= 30 THEN '16-30 Hari'
  WHEN aging_days <= 60 THEN '31-60 Hari'
  ELSE                       '> 60 Hari'
END AS umur_po
```

**Filter data:** Hanya PO dengan `on_time_delivery IN ('TERLAMBAT', 'IN PROGRESS')`, barang belum diterima.

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
                    WHEN CURRENT_DATE - date_ordered::DATE <= 15 THEN '0-15 Hari'
                    WHEN CURRENT_DATE - date_ordered::DATE <= 30 THEN '16-30 Hari'
                    WHEN CURRENT_DATE - date_ordered::DATE <= 60 THEN '31-60 Hari'
                    ELSE '> 60 Hari'
                END AS umur_po,
                COUNT(DISTINCT nomor_po) AS total_po
            FROM vw_pr_po_complete
            WHERE {filter_conditions} AND nomor_po IS NOT NULL
            AND on_time_delivery IN ('TERLAMBAT', 'IN PROGRESS')
            GROUP BY 1
            ORDER BY 1
            """
            with st.spinner("Memuat aging PO..."):
                aging_data = load_data(aging_query)

            if not aging_data.empty:
                category_aging = ['0-15 Hari', '16-30 Hari', '31-60 Hari', '> 60 Hari']
                
                fig = px.bar(
                    aging_data, x='umur_po', y='total_po',
                    labels={'umur_po': 'Aging (Hari)', 'total_po': 'Jumlah PO'},
                    text_auto=True,
                    category_orders={'umur_po': category_aging}
                )
                
                fig.update_layout(
                    height=400,
                    margin=dict(t=20, b=0, l=0, r=0)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Tidak ada data aging PO.")