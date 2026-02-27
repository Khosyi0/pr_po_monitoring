"""
v_evaluasi.py - Halaman Evaluasi Harga Barang
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from utils import format_idr, format_idr_short, format_number, format_currency, render_chat_analyst


def render(filter_conditions, bagian_pr_cond, bagian_po_cond, load_data, **kwargs):
        
        info_filter = kwargs.get('info_filter', 'Tidak ada filter spesifik')

        # Fungsi helper untuk tombol toggle formula
        def toggle_state(state_key):
            st.session_state[state_key] = not st.session_state[state_key]

        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:60px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" fill="currentColor" class="bi bi-tag-fill" viewBox="0 0 16 16" style="margin-bottom: 10px; margin-right: 8px;">
                    <path d="M2 1a1 1 0 0 0-1 1v4.586a1 1 0 0 0 .293.707l7 7a1 1 0 0 0 1.414 0l4.586-4.586a1 1 0 0 0 0-1.414l-7-7A1 1 0 0 0 6.586 1zm4 3.5a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0"/>
                </svg>
                Evaluasi PO per Harga Barang
            </h1>
        """, unsafe_allow_html=True)
        st.markdown("Analisis harga barang pada PO: perbandingan terhadap OE, variasi harga antar vendor, dan tren harga historis.")
        st.markdown("""
            <style>
            [data-testid="stMetricValue"] > div {
                font-size: 1.8rem !important; /* Ukuran font standar yang nyaman dibaca, tidak terlalu besar/kecil */
                white-space: normal !important; /* KUNCI: Mencegah teks dipotong (...) dan memungkinkannya turun baris */
                word-wrap: break-word !important; /* Memastikan angka/kata panjang bisa patah dengan rapi */
                line-height: 1.2 !important; /* Mengatur jarak vertikal jika teks menjadi 2 baris */
            }
            </style>
        """, unsafe_allow_html=True)
        st.markdown("---")

        # ── KPI HARGA ─────────────────────────────────────
        # Kolom oe sudah tersedia di vw_pr_po_complete (= estimasi_pr × quantity_pr)
        harga_kpi_query = f"""
        SELECT
            COUNT(DISTINCT material_no)                                                  AS total_material,
            COUNT(DISTINCT nomor_po)                                                     AS total_po,
            COALESCE(SUM(oe), 0)                                                         AS total_oe,
            COALESCE(SUM(total_amount_local_curr), 0)                                    AS total_realisasi,
            COALESCE(SUM(oe) - SUM(total_amount_local_curr), 0)                          AS total_efisiensi,
            COUNT(CASE WHEN total_amount_local_curr > oe AND oe > 0 THEN 1 END)          AS po_melebihi_oe,
            COUNT(CASE WHEN total_amount_local_curr <= oe AND oe > 0 THEN 1 END)         AS po_dibawah_oe
        FROM vw_pr_po_complete
        WHERE {filter_conditions}
        AND nomor_po IS NOT NULL
        AND oe IS NOT NULL
        AND ({bagian_po_cond})
        """
        with st.spinner("Memuat KPI harga..."):
            harga_kpi = load_data(harga_kpi_query)

        col1, col2, col3, col4 = st.columns(4)
        total_oe_val   = float(harga_kpi['total_oe'][0] or 0)
        total_real_val = float(harga_kpi['total_realisasi'][0] or 0)
        total_efis_val = float(harga_kpi['total_efisiensi'][0] or 0)
        po_over        = int(harga_kpi['po_melebihi_oe'][0] or 0)
        po_under       = int(harga_kpi['po_dibawah_oe'][0] or 0)

        # ── Definisi KPI: urutan kiri→kanan ───────────────────────────────────
        delta_label = "efisien" if total_efis_val >= 0 else "melebihi OE"
        KPI_EVAL = [
            {
                "key": "kpi_eval_material",
                "metric_args": ("Total Material Unik", f"{format_number(int(harga_kpi['total_material'][0] or 0))}"),
                "metric_kwargs": {},
                "formula": """\
**Total Material Unik**: Jumlah kode material berbeda yang tercatat dalam PO di periode filter.

**Kalkulasi SQL:**
```sql
COUNT(DISTINCT material_no) AS total_material
```
Filter: `nomor_po IS NOT NULL AND oe IS NOT NULL` - hanya material yang sudah masuk PO dan memiliki data OE untuk perbandingan harga.\
""",
            },
            {
                "key": "kpi_eval_oe",
                "metric_args": ("Total OE", format_idr(total_oe_val)),
                "metric_kwargs": {},
                "formula": """\
**Total OE (Owner's Estimate)**: Total nilai anggaran estimasi untuk semua material yang sudah masuk PO.

**Kalkulasi SQL:**
```sql
COALESCE(SUM(oe), 0) AS total_oe
```

**Sumber kolom `oe`:** Dihitung di view sebagai `estimasi_pr × quantity_pr`.

Ini adalah **nilai yang dianggarkan** sebelum proses pengadaan dimulai. Digunakan sebagai baseline untuk mengukur apakah realisasi PO lebih mahal atau lebih murah.\
""",
            },
            {
                "key": "kpi_eval_realisasi",
                "metric_args": ("Total Realisasi PO", format_idr(total_real_val)),
                "metric_kwargs": {},
                "formula": """\
**Total Realisasi PO**: Total nilai aktual yang dibayarkan dalam Purchase Order.

**Kalkulasi SQL:**
```sql
COALESCE(SUM(total_amount_local_curr), 0) AS total_realisasi
```

**Sumber kolom `total_amount_local_curr`:** Nilai PO dalam mata uang lokal (IDR), diambil langsung dari tabel `po_items`. Sudah memperhitungkan kurs jika PO aslinya dalam mata uang asing.\
""",
            },
            {
                "key": "kpi_eval_selisih",
                "metric_args": ("Selisih OE vs Realisasi", format_idr(total_efis_val)),
                "metric_kwargs": {"delta": delta_label},
                "formula": """\
**Selisih OE vs Realisasi**: Perbedaan antara total OE (anggaran) dan total realisasi PO.

**Kalkulasi SQL:**
```sql
COALESCE(SUM(oe) - SUM(total_amount_local_curr), 0) AS total_efisiensi
```

| Kondisi | Interpretasi |
|---|---|
| **Positif** (efisien) | Realisasi PO lebih murah dari OE → ada penghematan ✅ |
| **Negatif** (melebihi OE) | Realisasi PO lebih mahal dari OE → perlu evaluasi ❌ |\
""",
            },
            {
                "key": "kpi_eval_over",
                "metric_args": ("⚠️ Item PO Melebihi OE", f"{format_number(po_over)} item"),
                "metric_kwargs": {},
                "formula": """\
**Item PO Melebihi OE**: Jumlah baris item PO yang nilai realisasinya melebihi OE.

**Kalkulasi SQL:**
```sql
COUNT(CASE WHEN total_amount_local_curr > oe AND oe > 0 THEN 1 END) AS po_melebihi_oe
```

Item ini perlu diinvestigasi: kemungkinan penyebabnya adalah perubahan spesifikasi, kondisi pasar yang lebih mahal dari estimasi, atau kesalahan input OE di awal.\
""",
            },
            {
                "key": "kpi_eval_under",
                "metric_args": ("✅ Item PO Di Bawah / Sesuai OE", f"{format_number(po_under)} item"),
                "metric_kwargs": {},
                "formula": """\
**Item PO Di Bawah / Sesuai OE**: Jumlah baris item PO yang nilai realisasinya sama atau lebih murah dari OE.

**Kalkulasi SQL:**
```sql
COUNT(CASE WHEN total_amount_local_curr <= oe AND oe > 0 THEN 1 END) AS po_dibawah_oe
```

Semakin banyak item di kategori ini dibandingkan total item PO, semakin baik performa pengadaan dalam hal kepatuhan anggaran.\
""",
            },
        ]

        # ── Inisialisasi session state ─────────────────────────────────────────
        for kpi in KPI_EVAL:
            if kpi["key"] not in st.session_state:
                st.session_state[kpi["key"]] = False

        # ── Baris 1: 4 metric utama ────────────────────────────────────────────
        row1_kpis = KPI_EVAL[:4]
        row1_cols = st.columns(4)
        for col, kpi in zip(row1_cols, row1_kpis):
            with col:
                m_col, btn_col = st.columns([5, 1])
                with m_col:
                    st.metric(*kpi["metric_args"], **kpi["metric_kwargs"])
                with btn_col:
                    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
                    is_open = st.session_state[kpi["key"]]
                    icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                    tooltip = "Hide Formula" if is_open else "Show Formula"
                    st.button(icon, key=f"btn_{kpi['key']}", help=tooltip,
                              on_click=toggle_state, kwargs={"state_key": kpi["key"]})

        # ── Baris 2: 2 metric tambahan (kiri saja) ────────────────────────────
        row2_kpis = KPI_EVAL[4:]
        row2_all_cols = st.columns([1, 1, 2])
        for col, kpi in zip(row2_all_cols[:2], row2_kpis):
            with col:
                m_col, btn_col = st.columns([5, 1])
                with m_col:
                    st.metric(*kpi["metric_args"], **kpi["metric_kwargs"])
                with btn_col:
                    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
                    is_open = st.session_state[kpi["key"]]
                    icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                    tooltip = "Hide Formula" if is_open else "Show Formula"
                    st.button(icon, key=f"btn_{kpi['key']}", help=tooltip,
                              on_click=toggle_state, kwargs={"state_key": kpi["key"]})

        # ── Info boxes full-width, berurutan kiri→kanan ───────────────────────
        for kpi in KPI_EVAL:
            if st.session_state[kpi["key"]]:
                st.info(kpi["formula"])

        st.markdown("---")

        # ── ROW 1: Scatter OE vs Realisasi & Bar Top Material Overspend ───────────
        col1, col2 = st.columns(2)

        with col1:
            title_col, btn_col = st.columns([9, 1])
            with title_col:
                st.markdown("""
                    <h1 style='display: flex; align-items: center; font-size:22px;'>
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                            <path d="M1 11a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1zm5-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1zm5-5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1z"/>
                        </svg>
                        OE vs Realisasi Harga PO (per Material)
                    </h1>
                """, unsafe_allow_html=True)
            with btn_col:
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                key_scatter = "show_formula_eval_scatter"
                if key_scatter not in st.session_state:
                    st.session_state[key_scatter] = False
                is_open = st.session_state[key_scatter]
                icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                tooltip = "Hide Formula" if is_open else "Show Formula"
                st.button(icon, key=f"btn_{key_scatter}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_scatter})

            if st.session_state.get(key_scatter, False):
                st.info("""\
**OE vs Realisasi Harga PO (per Material)**: Scatter chart perbandingan nilai estimasi vs realisasi PO per material.

**Kalkulasi SQL:**
| Kolom | Formula |
|---|---|
| OE (sumbu X) | `SUM(estimasi_pr × quantity_pr)` per material |
| Realisasi (sumbu Y) | `SUM(total_amount_local_curr)` per material |
| Warna titik | 🔴 Merah = `realisasi > OE` (overspend) · 🟢 Hijau = `realisasi ≤ OE` (efisien) |

**Formula Excel:**
- Kolom **OE**: `= Estimasi_PR × Qty_PR`
- Kolom **Efisiensi**: `= OE − Total_Amount_in_Local_Curr`
- Nilai **negatif** di kolom Efisiensi = overspend

Garis diagonal pada chart = garis paritas (realisasi = OE). Titik di atas garis = overspend.
                """)

            st.caption("Perbandingan nilai estimasi vs realisasi PO per material")

            scatter_query = f"""
            SELECT
                v.material_no,
                COALESCE(m.description, v.pr_description, 'Unknown') AS nama_material,
                ROUND(AVG(v.oe)::numeric, 2)                           AS avg_oe,
                ROUND(AVG(v.total_amount_local_curr)::numeric, 2)      AS avg_realisasi,
                COUNT(DISTINCT v.nomor_po)                             AS jumlah_po
            FROM vw_pr_po_complete v
            LEFT JOIN materials m USING (material_no)
            WHERE {filter_conditions}
            AND v.nomor_po IS NOT NULL
            AND v.oe IS NOT NULL AND v.oe > 0
            AND v.total_amount_local_curr > 0
            AND ({bagian_po_cond})
            GROUP BY v.material_no, m.description, v.pr_description
            ORDER BY jumlah_po DESC
            LIMIT 50
            """
            with st.spinner("Memuat scatter chart..."):
                scatter_data = load_data(scatter_query)

            if not scatter_data.empty:
                scatter_data['status'] = scatter_data.apply(
                    lambda r: 'Melebihi OE' if r['avg_realisasi'] > r['avg_oe'] else 'Di Bawah / Sesuai OE',
                    axis=1
                )
                max_val = max(scatter_data['avg_oe'].max(), scatter_data['avg_realisasi'].max()) * 1.1
                fig = px.scatter(
                    scatter_data,
                    x='avg_oe', y='avg_realisasi',
                    color='status',
                    size='jumlah_po',
                    hover_name='nama_material',
                    hover_data={'material_no': True, 'jumlah_po': True,
                                'avg_oe': ':,.0f', 'avg_realisasi': ':,.0f'},
                    color_discrete_map={'Melebihi OE': '#d62728', 'Di Bawah / Sesuai OE': '#2ca02c'},
                    labels={'avg_oe': 'Rata-rata OE (IDR)', 'avg_realisasi': 'Rata-rata Realisasi PO (IDR)'}
                )
                fig.add_shape(type='line', x0=0, y0=0, x1=max_val, y1=max_val,
                            line=dict(color='gray', dash='dash', width=1))
                fig.add_annotation(x=max_val * 0.85, y=max_val * 0.9,
                                    text="Batas OE", showarrow=False,
                                    font=dict(color='gray', size=11))
                fig.update_layout(height=420, legend=dict(orientation='h', yanchor='bottom', y=1.02), separators=",.")
                st.plotly_chart(fig, use_container_width=True)
                st.caption("Titik di atas garis diagonal = realisasi melebihi OE. Ukuran titik = jumlah PO.")
            else:
                st.info("Tidak ada data yang tersedia.")

        with col2:
            title_col, btn_col = st.columns([9, 1])
            with title_col:
                st.markdown("""
                    <h1 style='display: flex; align-items: center; font-size:22px;'>
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-exclamation-triangle-fill" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                            <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5m.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2"/>
                        </svg>
                        Top 10 Material: Overspend Terbesar
                    </h1>
                """, unsafe_allow_html=True)
            with btn_col:
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                key_overspend = "show_formula_eval_overspend"
                if key_overspend not in st.session_state:
                    st.session_state[key_overspend] = False
                is_open = st.session_state[key_overspend]
                icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                tooltip = "Hide Formula" if is_open else "Show Formula"
                st.button(icon, key=f"btn_{key_overspend}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_overspend})

            if st.session_state.get(key_overspend, False):
                st.info("""\
**Top 10 Material: Overspend Terbesar**: Bar chart 10 material dengan selisih (realisasi - OE) terbesar.

**Kalkulasi SQL:**
```sql
overspend = SUM(total_amount_local_curr) - SUM(estimasi_pr * quantity_pr)
```
Diurutkan descending, diambil 10 material teratas dengan nilai overspend positif.

**Formula Excel:**
- Kolom **OE**: `= Estimasi_PR × Qty_PR`
- Kolom **Efisiensi**: `= OE − Total_Amount_in_Local_Curr`
- Filter baris dengan nilai Efisiensi **negatif** (konvensi Excel: negatif = realisasi lebih mahal dari OE)
- Urutkan ascending, ambil 10 teratas (nilai paling negatif = paling overspend)
                """)

            st.caption("Top 10 material dengan selisih (realisasi - OE) terbesar.")

            overspend_query = f"""
            SELECT
                v.material_no,
                COALESCE(m.description, v.pr_description, 'Unknown')          AS nama_material,
                SUM(v.total_amount_local_curr - v.oe)                          AS total_overspend,
                ROUND(AVG(
                    CASE WHEN v.oe > 0
                    THEN ((v.total_amount_local_curr - v.oe) / v.oe * 100)
                    END
                )::numeric, 1)                                                  AS persen_overspend,
                COUNT(DISTINCT v.nomor_po)                                      AS jumlah_po
            FROM vw_pr_po_complete v
            LEFT JOIN materials m USING (material_no)
            WHERE {filter_conditions}
            AND v.nomor_po IS NOT NULL
            AND v.oe IS NOT NULL AND v.oe > 0
            AND v.total_amount_local_curr > v.oe
            AND ({bagian_po_cond})
            GROUP BY v.material_no, m.description, v.pr_description
            ORDER BY total_overspend DESC
            LIMIT 10
            """
            with st.spinner("Memuat top overspend..."):
                overspend_data = load_data(overspend_query)

            if not overspend_data.empty:
                overspend_data['label'] = overspend_data['nama_material'].str[:30]
                overspend_data['label_text'] = overspend_data['total_overspend'].apply(format_idr_short)
                fig = px.bar(
                    overspend_data,
                    x='total_overspend', y='label', orientation='h',
                    text='label_text',
                    color='persen_overspend',
                    color_continuous_scale='Reds',
                    labels={'total_overspend': 'Total Overspend (IDR)',
                            'label': 'Material', 'persen_overspend': '% di atas OE'}
                )
                fig.update_layout(height=420, yaxis={'categoryorder': 'total ascending'},
                                coloraxis_colorbar=dict(title='% Overspend'))
                fig.update_traces(textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("Tidak ada material dengan realisasi melebihi OE pada periode ini.")

        st.markdown("---")

        # ── ROW 2: Harga per Vendor & Tren Harga Historis ─────────────────────────
        col1, col2 = st.columns(2)

        with col1:
            title_col, btn_col = st.columns([9, 1])
            with title_col:
                st.markdown("""
                    <h1 style='display: flex; align-items: center; font-size:22px;'>
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-people-fill" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                            <path d="M7 14s-1 0-1-1 1-4 5-4 5 3 5 4-1 1-1 1zm4-6a3 3 0 1 0 0-6 3 3 0 0 0 0 6m-5.784 6A2.24 2.24 0 0 1 5 13c0-1.355.68-2.75 1.936-3.72A6.3 6.3 0 0 0 5 9c-4 0-5 3-5 4s1 1 1 1zM4.5 8a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5"/>
                        </svg>
                        Variasi Harga Antar Vendor (Top 10 Material)
                    </h1>
                """, unsafe_allow_html=True)
            with btn_col:
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                key_vendor_var = "show_formula_eval_vendor_var"
                if key_vendor_var not in st.session_state:
                    st.session_state[key_vendor_var] = False
                is_open = st.session_state[key_vendor_var]
                icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                tooltip = "Hide Formula" if is_open else "Show Formula"
                st.button(icon, key=f"btn_{key_vendor_var}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_vendor_var})

            if st.session_state.get(key_vendor_var, False):
                st.info("""\
**Variasi Harga Antar Vendor (Top 10 Material)**: Perbandingan harga satuan dari vendor berbeda untuk material yang sama.

**Kalkulasi harga satuan SQL:**
```sql
unit_price = total_amount_local_curr / NULLIF(qty_po, 0)
```

Chart menampilkan scatter harga satuan tiap transaksi PO per vendor, untuk 10 material dengan nilai total terbesar.

**Cara membaca:**
- Rentang harga **sempit** = harga pasar sudah terstabilisasi antar vendor
- Rentang harga **lebar** = ada potensi penghematan besar melalui seleksi vendor atau negosiasi
- Vendor dengan harga terendah konsisten = kandidat utama untuk dijadikan **vendor preferens**

Di Excel: `=Total_Amount/Qty_PO` per baris PO → buat pivot `Material × Vendor` untuk membandingkan.
                """)

            st.caption("Top 10 perbandingan harga satuan dari vendor berbeda untuk material yang sama.")

            vendor_price_query = f"""
            WITH ranked AS (
                SELECT
                    v.material_no,
                    COALESCE(m.description, v.pr_description, 'Unknown') AS nama_material,
                    COUNT(DISTINCT v.vendor_name) AS jumlah_vendor
                FROM vw_pr_po_complete v
                LEFT JOIN materials m USING (material_no)
                WHERE {filter_conditions}
                AND v.nomor_po IS NOT NULL
                AND v.qty_po > 0
                AND v.total_amount_local_curr > 0
                AND ({bagian_po_cond})
                GROUP BY v.material_no, m.description, v.pr_description
                ORDER BY jumlah_vendor DESC
                LIMIT 10
            )
            SELECT
                r.material_no,
                r.nama_material,
                v.vendor_name,
                ROUND((SUM(v.total_amount_local_curr) / NULLIF(SUM(v.qty_po), 0))::numeric, 2) AS harga_satuan_avg,
                COUNT(DISTINCT v.nomor_po) AS jumlah_po
            FROM ranked r
            JOIN vw_pr_po_complete v USING (material_no)
            WHERE {filter_conditions}
            AND v.nomor_po IS NOT NULL
            AND v.qty_po > 0
            AND v.total_amount_local_curr > 0
            AND ({bagian_po_cond})
            GROUP BY r.material_no, r.nama_material, v.vendor_name
            ORDER BY r.material_no, harga_satuan_avg
            """
            with st.spinner("Memuat variasi harga vendor..."):
                vendor_price_data = load_data(vendor_price_query)

            material_options = []
            material_labels  = {}

            if not vendor_price_data.empty:
                material_options = vendor_price_data['material_no'].unique().tolist()
                material_labels  = {
                    row['material_no']: f"{row['material_no']} – {row['nama_material'][:40]}"
                    for _, row in vendor_price_data.drop_duplicates('material_no').iterrows()
                }
                selected_mat = st.selectbox(
                    "Pilih Material:",
                    options=material_options,
                    format_func=lambda x: material_labels.get(x, x),
                    key="select_material_vendor"
                )
                df_mat = vendor_price_data[vendor_price_data['material_no'] == selected_mat]
                fig = px.bar(
                    df_mat,
                    x='vendor_name', y='harga_satuan_avg',
                    text=df_mat['harga_satuan_avg'].apply(format_idr_short),
                    color='harga_satuan_avg',
                    color_continuous_scale='Blues',
                    labels={'vendor_name': 'Vendor', 'harga_satuan_avg': 'Harga Satuan Rata-rata (IDR)'}
                )
                fig.update_layout(height=380, showlegend=False,
                                coloraxis_showscale=False, xaxis_tickangle=-30)
                fig.update_traces(textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Tidak ada data variasi harga yang tersedia.")

        with col2:
            title_col, btn_col = st.columns([9, 1])
            with title_col:
                st.markdown("""
                    <h1 style='display: flex; align-items: center; font-size:22px;'>
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-graph-up" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                            <path fill-rule="evenodd" d="M0 0h1v15h15v1H0zm14.817 3.113a.5.5 0 0 1 .07.704l-4.5 5.5a.5.5 0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5 0 0 1 .758-.06l2.609 2.61 4.15-5.073a.5.5 0 0 1 .704-.07"/>
                        </svg>
                        Tren Harga Historis per Material
                    </h1>
                """, unsafe_allow_html=True)
            with btn_col:
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                key_trend = "show_formula_eval_trend"
                if key_trend not in st.session_state:
                    st.session_state[key_trend] = False
                is_open = st.session_state[key_trend]
                icon = ":material/visibility_off:" if is_open else ":material/visibility:"
                tooltip = "Hide Formula" if is_open else "Show Formula"
                st.button(icon, key=f"btn_{key_trend}", help=tooltip, on_click=toggle_state, kwargs={"state_key": key_trend})

            if st.session_state.get(key_trend, False):
                st.info("""\
**Tren Harga Historis per Material**: Line chart pergerakan harga satuan PO dari waktu ke waktu. Berguna untuk mendeteksi kenaikan harga yang tidak wajar.

**Kalkulasi SQL:**
```sql
unit_price = AVG(total_amount_local_curr / NULLIF(qty_po, 0))
```
Di-group per `DATE_TRUNC('month', date_ordered)` untuk tampilan bulanan.

**Kegunaan analisis:**
- Tren **naik** = indikasi inflasi bahan baku atau leverage vendor meningkat → perlu renegosiasi
- Tren **turun** = negosiasi berhasil atau kondisi pasar lebih kompetitif ✅
- **Lonjakan tiba-tiba** = perlu investigasi (perubahan spesifikasi, vendor baru, atau potensi kesalahan input)

Di Excel: `=AVERAGEIFS(kolom_unit_price, kolom_material, kode_x, kolom_bulan, bulan_x)`
                """)

            st.caption("Pergerakan rata-rata harga satuan PO dari waktu ke waktu.")

            if material_options:
                selected_mat_trend = st.selectbox(
                    "Pilih Material:",
                    options=material_options,
                    format_func=lambda x: material_labels.get(x, x),
                    key="select_material_trend"
                )
                trend_harga_query = f"""
                SELECT
                    DATE_TRUNC('month', date_ordered)::DATE                               AS bulan,
                    ROUND((SUM(total_amount_local_curr) / NULLIF(SUM(qty_po), 0))::numeric, 2) AS harga_satuan_avg,
                    COUNT(DISTINCT nomor_po)                                            AS jumlah_po,
                    ROUND(AVG(oe)::numeric, 2)                                          AS avg_oe
                FROM vw_pr_po_complete
                WHERE material_no = '{selected_mat_trend}'
                AND date_ordered IS NOT NULL
                AND qty_po > 0
                AND total_amount_local_curr > 0
                AND nomor_po IS NOT NULL
                GROUP BY 1
                ORDER BY 1
                """
                with st.spinner("Memuat tren harga..."):
                    trend_harga_data = load_data(trend_harga_query)

                if not trend_harga_data.empty:
                    trend_harga_data['bulan'] = pd.to_datetime(trend_harga_data['bulan'])
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=trend_harga_data['bulan'],
                        y=trend_harga_data['harga_satuan_avg'],
                        mode='lines+markers',
                        name='Harga Satuan Realisasi',
                        line=dict(color='#1f77b4', width=2),
                        hovertemplate='%{x|%b %Y}<br>Harga: Rp %{y:,.0f}<extra></extra>'
                    ))
                    if trend_harga_data['avg_oe'].notna().any() and trend_harga_data['avg_oe'].sum() > 0:
                        fig.add_trace(go.Scatter(
                            x=trend_harga_data['bulan'],
                            y=trend_harga_data['avg_oe'],
                            mode='lines',
                            name='OE Rata-rata',
                            line=dict(color='#ff7f0e', dash='dash', width=1.5),
                            hovertemplate='%{x|%b %Y}<br>OE: Rp %{y:,.0f}<extra></extra>'
                        ))
                    fig.update_layout(
                        height=380,
                        xaxis_title='Bulan',
                        yaxis_title='Harga Satuan (IDR)',
                        legend=dict(orientation='h', yanchor='bottom', y=1.02),
                        separators=",.",
                        hovermode='x unified'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Tidak ada data historis untuk material ini.")
            else:
                st.info("Tidak ada material yang bisa dipilih untuk tren historis.")

        st.markdown("---")

        # ── ROW 3: Tabel Detail Evaluasi Harga ────────────────────────────────────
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:22px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-table" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                    <path d="M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2zm15 2h-4v3h4zm0 4h-4v3h4zm0 4h-4v3h3a1 1 0 0 0 1-1zm-5 3v-3H6v3zm-5 0v-3H1v2a1 1 0 0 0 1 1zm-4-4h4V8H1zm0-4h4V4H1zm5-3v3h4V4zm4 4H6v3h4z"/>
                </svg>
                Detail Evaluasi Harga per Material
            </h1>
        """, unsafe_allow_html=True)
        st.caption("Ringkasan perbandingan OE vs realisasi per material. Kolom 'Status' menandai item yang perlu perhatian.")

        detail_harga_query = f"""
        SELECT
            v.material_no,
            COALESCE(m.description, v.pr_description, 'Unknown')                AS nama_material,
            m.material_group                                                    AS grup_material,
            COUNT(DISTINCT v.nomor_po)                                            AS jumlah_po,
            COUNT(DISTINCT v.vendor_name)                                         AS jumlah_vendor,
            ROUND(AVG(v.oe)::numeric, 0)                                          AS rata_oe,
            ROUND(AVG(v.total_amount_local_curr)::numeric, 0)                     AS rata_realisasi,
            ROUND(AVG(CASE WHEN v.oe > 0
                THEN (v.total_amount_local_curr - v.oe) / v.oe * 100
                END)::numeric, 1)                                                AS persen_selisih_avg,
            ROUND((SUM(v.oe) - SUM(v.total_amount_local_curr))::numeric, 0)       AS total_selisih,
            ROUND(MIN(v.total_amount_local_curr / NULLIF(v.qty_po, 0))::numeric, 0)   AS harga_satuan_min,
            ROUND(MAX(v.total_amount_local_curr / NULLIF(v.qty_po, 0))::numeric, 0)   AS harga_satuan_max
        FROM vw_pr_po_complete v
        LEFT JOIN materials m USING (material_no)
        WHERE {filter_conditions}
        AND v.nomor_po IS NOT NULL
        AND v.oe IS NOT NULL AND v.oe > 0
        AND v.qty_po > 0
        AND ({bagian_po_cond})
        GROUP BY v.material_no, m.description, v.pr_description, m.material_group
        ORDER BY persen_selisih_avg DESC NULLS LAST
        LIMIT 100
        """
        with st.spinner("Memuat tabel detail harga..."):
            detail_harga_data = load_data(detail_harga_query)

        if not detail_harga_data.empty:
            def status_harga(persen):
                if pd.isna(persen):       return "-"
                elif persen > 10:         return "🔴 Jauh Melebihi OE"
                elif persen > 0:          return "🟡 Melebihi OE"
                elif persen >= -5:        return "🟢 Sesuai OE"
                else:                     return "✅ Efisien"

            detail_harga_data['status'] = detail_harga_data['persen_selisih_avg'].apply(status_harga)

            for col in ['rata_oe', 'rata_realisasi', 'total_selisih', 'harga_satuan_min', 'harga_satuan_max']:
                detail_harga_data[col] = detail_harga_data[col].apply(
                    lambda x: f"Rp {x:,.0f}" if pd.notna(x) else ""
                )
            detail_harga_data['persen_selisih_avg'] = detail_harga_data['persen_selisih_avg'].apply(
                lambda x: f"{x:+.1f}".replace('.', ',') + "%" if pd.notna(x) else ""
            )

            st.dataframe(
                detail_harga_data.rename(columns={
                    'material_no':        'Material No',
                    'nama_material':      'Nama Material',
                    'grup_material':      'Grup',
                    'jumlah_po':          'Jml PO',
                    'jumlah_vendor':      'Jml Vendor',
                    'rata_oe':            'Rata-rata OE',
                    'rata_realisasi':     'Rata-rata Realisasi',
                    'persen_selisih_avg': '% Selisih',
                    'total_selisih':      'Total Selisih',
                    'harga_satuan_min':   'Harga Satuan Min',
                    'harga_satuan_max':   'Harga Satuan Maks',
                    'status':             'Status'
                }),
                use_container_width=True, height=400
            )
            csv_harga = detail_harga_data.to_csv(index=False)
            st.download_button(
                label="Download as CSV",
                icon=":material/download:",
                data=csv_harga,
                file_name=f"evaluasi_harga_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("Tidak ada data evaluasi harga untuk filter yang dipilih.")

        # =====================================================================
        # INTEGRASI AI: KUMPULKAN KONTEKS & PANGGIL CHAT
        # =====================================================================
        
        konteks_lines = []
        
        # 0. Rangkuman Filter
        konteks_lines.append("## 0. FILTER YANG SEDANG DITERAPKAN USER")
        konteks_lines.append(info_filter)
        konteks_lines.append("\n")

        # 1. Ringkasan KPI Evaluasi Harga
        konteks_lines.append("## 1. RINGKASAN KPI EVALUASI HARGA")
        konteks_lines.append(f"- Total Material Unik: {int(harga_kpi['total_material'][0] or 0)}")
        konteks_lines.append(f"- Total OE (Estimasi): {format_idr(total_oe_val)}")
        konteks_lines.append(f"- Total Realisasi PO: {format_idr(total_real_val)}")
        konteks_lines.append(f"- Selisih OE vs Realisasi: {format_idr(total_efis_val)}")
        konteks_lines.append(f"- Item PO Melebihi OE (Overspend): {po_over} item")
        konteks_lines.append(f"- Item PO Sesuai/Di Bawah OE: {po_under} item\n")

        # 2. Data Top Overspend (Material yang paling rugi)
        if 'overspend_data' in locals() and not overspend_data.empty:
            konteks_lines.append("## 2. TOP 10 MATERIAL OVERSPEND TERBESAR")
            # Ambil kolom penting saja agar hemat token
            df_os_simple = overspend_data[['nama_material', 'total_overspend', 'persen_overspend']]
            konteks_lines.append(df_os_simple.to_markdown(index=False))
            konteks_lines.append("\n")

        # 3. Data Detail Harga (Ambil 15 teratas yang paling bermasalah)
        if 'detail_harga_data' in locals() and not detail_harga_data.empty:
            konteks_lines.append("## 3. DETAIL EVALUASI HARGA (15 ITEM DENGAN SELISIH TERBURUK)")
            df_detail_simple = detail_harga_data[['nama_material', 'rata_oe', 'rata_realisasi', 'persen_selisih_avg', 'status']].head(15)
            konteks_lines.append(df_detail_simple.to_markdown(index=False))
            konteks_lines.append("\n")

        # Gabungkan semua teks
        gabungan_konteks = "\n".join(konteks_lines)

        # Render kolom chat di paling bawah halaman
        render_chat_analyst(
            konteks_data_teks=gabungan_konteks, 
            nama_halaman="Evaluasi Harga Barang"
        )