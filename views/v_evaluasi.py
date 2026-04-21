"""
v_evaluasi.py - Halaman Evaluasi Harga Barang
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from utils import format_idr, format_idr_short, format_number, format_currency, render_chat_analyst, idr_axis

EVALUASI_CSS = """
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
    "kpi_eval_material": "M2 1a1 1 0 0 0-1 1v4.586a1 1 0 0 0 .293.707l7 7a1 1 0 0 0 1.414 0l4.586-4.586a1 1 0 0 0 0-1.414l-7-7A1 1 0 0 0 6.586 1zm4 3.5a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0",
    "kpi_eval_oe": "M4 10.781c.148 1.667 1.513 2.85 3.591 3.003V15h1.043v-1.216c2.27-.179 3.678-1.438 3.678-3.3 0-1.59-.947-2.51-2.956-3.028l-.722-.187V3.467c1.122.11 1.879.714 2.07 1.616h1.47c-.166-1.6-1.54-2.748-3.54-2.875V1H7.591v1.233c-1.939.23-3.27 1.472-3.27 3.156 0 1.454.966 2.483 2.661 2.917l.61.162v4.031c-1.149-.17-1.94-.8-2.131-1.718zm3.391-3.836c-1.043-.263-1.6-.825-1.6-1.616 0-.944.704-1.641 1.8-1.828v3.495l-.2-.05zm1.591 1.872c1.287.323 1.852.859 1.852 1.769 0 1.097-.826 1.828-2.2 1.939V8.73z",
    "kpi_eval_realisasi": "M1 3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1zm7 8a2 2 0 1 0 0-4 2 2 0 0 0 0 4 M0 5a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H1a1 1 0 0 1-1-1zm3 0a2 2 0 0 1-2 2v4a2 2 0 0 1 2 2h10a2 2 0 0 1 2-2V7a2 2 0 0 1-2-2z",
    "kpi_eval_selisih": "M11.534 7h3.932a.25.25 0 0 1 .192.41l-1.966 2.36a.25.25 0 0 1-.384 0l-1.966-2.36a.25.25 0 0 1 .192-.41m-11 2h3.932a.25.25 0 0 0 .192-.41L2.692 6.23a.25.25 0 0 0-.384 0L.342 8.59A.25.25 0 0 0 .534 9 M8 3c-1.552 0-2.94.707-3.857 1.818a.5.5 0 1 1-.771-.636A6.002 6.002 0 0 1 13.917 7H12.9A5 5 0 0 0 8 3M3.1 9a5.002 5.002 0 0 0 8.757 2.182.5.5 0 1 1 .771.636A6.002 6.002 0 0 1 2.083 9z",
    "kpi_eval_over": "M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5m.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2",
    "kpi_eval_under": "M10.97 4.97a.75.75 0 0 1 1.07 1.05l-3.99 4.99a.75.75 0 0 1-1.08.02L4.324 8.384a.75.75 0 1 1 1.06-1.06l2.094 2.093 3.473-4.425z M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0z",
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

        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:60px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" fill="currentColor" class="bi bi-tag-fill" viewBox="0 0 16 16" style="margin-bottom: 10px; margin-right: 8px;">
                    <path d="M2 1a1 1 0 0 0-1 1v4.586a1 1 0 0 0 .293.707l7 7a1 1 0 0 0 1.414 0l4.586-4.586a1 1 0 0 0 0-1.414l-7-7A1 1 0 0 0 6.586 1zm4 3.5a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0"/>
                </svg>
                Evaluasi PO per Harga Barang
            </h1>
        """, unsafe_allow_html=True)
        st.markdown("Analisis harga barang pada PO: perbandingan terhadap OE, variasi harga antar vendor, dan tren harga historis.")
        st.markdown(EVALUASI_CSS, unsafe_allow_html=True)
        st.markdown("---")

# == KPI HARGA =====================================
        date_from = kwargs.get('date_from')
        date_to   = kwargs.get('date_to')
        bagian_po_poi = bagian_po_cond.replace('bagian_po', 'poi.bagian_po')

        # OE metrics
        harga_pr_query = f"""
        SELECT
            COALESCE(SUM(poi.estimasi_pr * poi.quantity_pr), 0) AS total_oe
        FROM po_items poi
        JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
        WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
        AND poi.estimasi_pr IS NOT NULL
        AND poi.quantity_pr IS NOT NULL
        AND poi.total_amount_local_curr IS NOT NULL
        AND {bagian_po_poi}
        AND {dept_cond}
        AND {pg_cond}
        """
        # PO metrics
        harga_kpi_query = f"""
        SELECT
            COUNT(DISTINCT poi.material_no)                                              AS total_material,
            COUNT(DISTINCT poi.nomor_po)                                                 AS total_po,
            COALESCE(SUM(poi.total_amount_local_curr), 0)                                AS total_realisasi,
            COUNT(CASE WHEN poi.total_amount_local_curr > (poi.estimasi_pr * poi.quantity_pr)
                AND (poi.estimasi_pr * poi.quantity_pr) > 0 THEN 1 END)                  AS po_melebihi_oe,
            COUNT(CASE WHEN poi.total_amount_local_curr <= (poi.estimasi_pr * poi.quantity_pr)
                AND (poi.estimasi_pr * poi.quantity_pr) > 0 THEN 1 END)                  AS po_dibawah_oe
        FROM po_items poi
        JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
        LEFT JOIN vw_pr_po_complete v ON poi.nomor_po = v.nomor_po AND poi.item_po = v.item_po
        WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
          AND {bagian_po_poi}
          AND {dept_cond}
          AND {pg_cond}
          AND poi.total_amount_local_curr IS NOT NULL
        """
        with st.spinner("Memuat KPI harga..."):
            harga_pr  = load_data(harga_pr_query)
            harga_kpi = load_data(harga_kpi_query)

        total_oe_val   = float(harga_pr['total_oe'][0] or 0)
        total_real_val = float(harga_kpi['total_realisasi'][0] or 0)
        total_efis_val = total_oe_val - total_real_val
        po_over        = int(harga_kpi['po_melebihi_oe'][0] or 0)
        po_under       = int(harga_kpi['po_dibawah_oe'][0] or 0)
        total_mat      = int(harga_kpi['total_material'][0] or 0)
        delta_label    = "efisien" if total_efis_val >= 0 else "melebihi OE"

        # == DEFINISI KPI DENGAN DOKUMENTASI LENGKAP ==
        KPI_EVAL_CARDS = [
            {
                "key": "kpi_eval_material",
                "label": "Total Material Unik",
                "value": f"{format_number(total_mat)}",
                "delta": "Item dalam PO",
                "formula": """**Total Material Unik:** Jumlah kode material berbeda yang tercatat dalam PO di periode filter.

**Formula Excel:** (PO SAP)
- Filter **Material No** selain `1000076` dan `blanks`
- Filter **PO Deletion Flag** selain `L`
- Buat kolom baru `=COUNTIFS` menghitung kemunculan **Material No** yang sama dari baris pertama sampai baris saat ini. Kalau hasilnya = 1, berarti ini kemunculan pertama → nilai 1 (tidak duplikat). Kalau sudah pernah muncul sebelumnya → nilai 2 (duplikat).
- Hitung jumlah angka **1** di kolom tersebut
"""
            },
            {
                "key": "kpi_eval_oe",
                "label": "Total OE",
                "value": format_idr(total_oe_val),
                "delta": "Anggaran Estimasi",
                "formula": f"""**Total OE:** Total nilai anggaran estimasi material yang sudah masuk PO.

**Total OE saat ini:** Rp {total_oe_val:,.2f}

**Formula Excel:** (PO SAP)
- Filter **Material No** selain `1000076
- Filter **PO Deletion Flag** selain `L`
- Buat kolom **OE**: `= Quantity PR × Estimasi PR`
- Jumlahkan nilai pada kolom **OE**

Ini adalah **nilai yang dianggarkan** sebelum proses pengadaan dimulai. Digunakan sebagai baseline untuk mengukur apakah realisasi PO lebih mahal atau lebih murah.
"""
            },
            {
                "key": "kpi_eval_realisasi",
                "label": "Total Realisasi PO",
                "value": format_idr(total_real_val),
                "delta": "Nilai Aktual PO",
                "formula": f"""**Total Realisasi PO**: Total nilai aktual yang dibayarkan dalam Purchase Order.

**Total Realisasi PO saat ini:** Rp {total_real_val:,.2f}

**Formula Excel:** (PO SAP)
- Filter **Material No** selain `1000076
- Filter **PO Deletion Flag** selain `L`
- Jumlahkan nilai pada kolom **Total Amount in Local Curr**
"""
            },
            {
                "key": "kpi_eval_selisih",
                "label": "Selisih OE vs Realisasi",
                "value": format_idr(total_efis_val),
                "delta": delta_label,
                "formula": f"""**Selisih OE vs Realisasi**: Perbedaan antara total OE (anggaran) dan total realisasi PO.

**Total Selisih saat ini:** Rp {total_efis_val:,.2f}

**Formula**
```
= Total OE - Total Realisasi PO
```

| Kondisi | Interpretasi |
|---|---|
| **Positif** (efisien) | Realisasi PO lebih murah dari OE → ada penghematan ✅ |
| **Negatif** (melebihi OE) | Realisasi PO lebih mahal dari OE → perlu evaluasi ❌ |"""
            },
            {
                "key": "kpi_eval_over",
                "label": "Item PO Melebihi OE",
                "value": f"{format_number(po_over)} item",
                "delta": "Perlu Investigasi",
                "formula": """**Item PO Melebihi OE**: Jumlah item PO yang nilai realisasinya melebihi OE.

**Formula Excel:** (PO SAP)
- Filter **Material No** selain `1000076
- Filter **PO Deletion Flag** selain `L`
- Buat kolom **OE**: `= Quantity PR × Estimasi PR`
- Buat kolom **Efisiensi**: `=OE - Total Amount in Local Curr`
- Filter kolom **Efisiensi** yang hasilnya kurang dari **0**

Item ini perlu diinvestigasi: kemungkinan penyebabnya adalah perubahan spesifikasi, kondisi pasar yang lebih mahal dari estimasi, atau kesalahan input OE di awal.
"""
            },
            {
                "key": "kpi_eval_under",
                "label": "Item Sesuai/Di Bawah OE",
                "value": f"{format_number(po_under)} item",
                "delta": "Aman/Hemat",
                "formula": """**Item PO Di Bawah / Sesuai OE**: Jumlah item PO yang nilai realisasinya sama atau lebih murah dari OE.

**Formula Excel:** (PO SAP)
- Filter **Material No** selain `1000076
- Filter **PO Deletion Flag** selain `L`
- Buat kolom **OE**: `= Quantity PR × Estimasi PR`
- Buat kolom **Efisiensi**: `=OE - Total Amount in Local Curr`
- Filter kolom **Efisiensi** yang hasilnya lebih besar sama dengan **0**

Semakin banyak item di kategori ini dibandingkan total item PO, semakin baik performa pengadaan dalam hal kepatuhan anggaran.         
"""
            },
        ]

        # == RENDERING 3 COLUMNS PER ROW ==
        for row_start in range(0, len(KPI_EVAL_CARDS), 3):
            cols = st.columns(3, gap="medium")
            row_items = KPI_EVAL_CARDS[row_start : row_start + 3]
            for i, kpi in enumerate(row_items):
                with cols[i]:
                    delta_type = "neutral"
                    if kpi['key'] == 'kpi_eval_selisih':
                        delta_type = "green" if total_efis_val >= 0 else "red"
                    elif kpi['key'] == 'kpi_eval_over':
                        delta_type = "red"
                    elif kpi['key'] == 'kpi_eval_under':
                        delta_type = "green"
                    
                    card_html = _card(ICONS[kpi['key']], kpi['label'], kpi['value'], kpi['delta'], delta_type)
                    
                    st.markdown(card_html, unsafe_allow_html=True)
                    with st.popover(":material/visibility:", help="Lihat Formula"):
                        st.info(kpi["formula"])
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

        st.markdown("---")

        # == ROW 1: Scatter OE vs Realisasi (full width) ============================

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
            with st.popover(":material/visibility:", help="Lihat Formula"):
                st.info("""\
**OE vs Realisasi Harga PO (per Material)**: Scatter chart perbandingan nilai estimasi vs realisasi PO per material.

**Kalkulasi SQL:**
| Kolom | Formula |
|---|---|
| OE (sumbu X) | `AVG(estimasi_pr × quantity_pr)` dari tabel `po_items` (sumber: **PO SAP**) |
| Realisasi (sumbu Y) | `AVG(total_amount_local_curr)` dari tabel `po_items` |
| Warna titik | 🔴 Merah = `realisasi > OE` (overspend) · 🟢 Hijau = `realisasi ≤ OE` (efisien) |

**Formula Excel:** (PO SAP)
- Filter **PO Deletion Flag** selain `L`
- Filter **Material No** sesuai yang dicari, pastikan **Description** sesuai
- Buat kolom **OE**: `= Estimasi_PR × Qty_PR` dan jumlahkan
- Buat kolom **Efisiensi**: `= OE − Total_Amount_in_Local_Curr` dan jumlahkan
- Nilai **negatif** di kolom Efisiensi = overspend

Garis diagonal pada chart = garis paritas (realisasi = OE). Titik di atas garis = overspend.
            """)

        st.caption("Perbandingan nilai estimasi vs realisasi PO per material")

        scatter_query = f"""
        SELECT
            poi.material_no,
            COALESCE(m.description, poi.description, 'Unknown')              AS nama_material,
            ROUND(AVG(poi.estimasi_pr * poi.quantity_pr)::numeric, 2)        AS avg_oe,
            ROUND(AVG(poi.total_amount_local_curr)::numeric, 2)              AS avg_realisasi,
            COUNT(DISTINCT poi.nomor_po)                                     AS jumlah_po
        FROM po_items poi
        JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
        LEFT JOIN materials m ON poi.material_no = m.material_no
        WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
        AND poi.nomor_po IS NOT NULL
        AND poi.estimasi_pr IS NOT NULL AND poi.estimasi_pr > 0
        AND poi.quantity_pr IS NOT NULL AND poi.quantity_pr > 0
        AND poi.total_amount_local_curr > 0
        AND ({bagian_po_cond.replace('bagian_po', 'poi.bagian_po')})
        AND {dept_cond}
        AND {pg_cond}
        GROUP BY poi.material_no, m.description, poi.description
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
            scatter_data['selisih'] = scatter_data['avg_oe'] - scatter_data['avg_realisasi']
            max_val = max(scatter_data['avg_oe'].max(), scatter_data['avg_realisasi'].max()) * 1.1
            fig = px.scatter(
                scatter_data,
                x='avg_oe', y='avg_realisasi',
                color='status',
                size='jumlah_po',
                hover_name='nama_material',
                hover_data={'material_no': True, 'jumlah_po': True,
                            'avg_oe': ':,.0f', 'avg_realisasi': ':,.0f', 'selisih': ':,.0f'},
                color_discrete_map={'Melebihi OE': '#d62728', 'Di Bawah / Sesuai OE': '#2ca02c'},
                labels={'avg_oe': 'Rata-rata OE (IDR)', 'avg_realisasi': 'Rata-rata Realisasi PO (IDR)', 'selisih': 'Selisih (IDR)'}
            )
            fig.add_shape(type='line', x0=0, y0=0, x1=max_val, y1=max_val,
                        line=dict(color='gray', dash='dash', width=1))
            fig.add_annotation(x=max_val * 0.85, y=max_val * 0.9,
                                text="Batas OE", showarrow=False,
                                font=dict(color='gray', size=11))
            axis_cfg = idr_axis(max_val)
            fig.update_layout(
                height=420,
                legend=dict(orientation='h', yanchor='bottom', y=1.02),
                separators=",.",
                xaxis=axis_cfg,
                yaxis=axis_cfg, margin=dict(t=40, b=40, l=40, r=20)
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Titik di atas garis diagonal = realisasi melebihi OE. Ukuran titik = jumlah PO.")
        else:
            st.info("Tidak ada data yang tersedia.")

        st.markdown("---")

        # == ROW 1b: Top 10 Overspend & Top 10 Efisiensi =============================
        col_over, col_ef = st.columns(2)

        with col_over:
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
                with st.popover(":material/visibility:", help="Lihat Formula"):
                    st.info("""\
**Top 10 Material: Overspend Terbesar**: Bar chart 10 material dengan selisih (OE - realisasi) terbesar.

**Formula Excel:** (PO SAP)
- Filter **PO Deletion Flag** selain `L`
- Filter **Material No** sesuai yang dicari, pastikan **Description** sesuai
- Buat kolom **OE**: `= Estimasi_PR × Qty_PR`
- Buat kolom **Efisiensi**: `= OE − Total_Amount_in_Local_Curr`
- Jumlahkan kolom **Efisiensi** yang kurang dari **0**
                """)

            st.caption("Top 10 material dengan selisih (OE - realisasi) terbesar.")

            overspend_query = f"""
            SELECT
                poi.material_no,
                COALESCE(m.description, MIN(poi.description), 'Unknown')         AS nama_material,
                SUM(poi.total_amount_local_curr - (poi.estimasi_pr * poi.quantity_pr)) AS total_overspend,
                ROUND(AVG(
                    CASE WHEN (poi.estimasi_pr * poi.quantity_pr) > 0
                    THEN ((poi.total_amount_local_curr - (poi.estimasi_pr * poi.quantity_pr))
                          / (poi.estimasi_pr * poi.quantity_pr) * 100)
                    END
                )::numeric, 1)                                                    AS persen_overspend,
                COUNT(DISTINCT poi.nomor_po)                                      AS jumlah_po
            FROM po_items poi
            JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
            LEFT JOIN materials m ON poi.material_no = m.material_no
            WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
            AND poi.nomor_po IS NOT NULL
            AND poi.estimasi_pr IS NOT NULL AND poi.estimasi_pr > 0
            AND poi.quantity_pr IS NOT NULL AND poi.quantity_pr > 0
            AND poi.total_amount_local_curr > (poi.estimasi_pr * poi.quantity_pr)
            AND ({bagian_po_cond.replace('bagian_po', 'poi.bagian_po')})
            AND {dept_cond}
            AND {pg_cond}
            GROUP BY poi.material_no, m.description
            ORDER BY total_overspend DESC
            LIMIT 10
            """
            with st.spinner("Memuat top overspend..."):
                overspend_data = load_data(overspend_query)

            if not overspend_data.empty:
                overspend_data['label'] = overspend_data['nama_material'].str[:30]
                overspend_data['label_text'] = overspend_data['total_overspend'].apply(format_idr_short)
                overspend_data['hover_overspend'] = overspend_data['total_overspend'].apply(
                    lambda x: f"Rp {x:,.0f}"
                )
                fig = px.bar(
                    overspend_data,
                    x='total_overspend', y='label', orientation='h',
                    text='label_text',
                    color='persen_overspend',
                    color_continuous_scale='Reds',
                    labels={'total_overspend': 'Total Overspend (IDR)',
                            'label': 'Material', 'persen_overspend': '% di atas OE'},
                    custom_data=['hover_overspend', 'persen_overspend', 'jumlah_po', 'material_no'],
                )
                fig.update_traces(
                    textposition='outside',
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        "Total Overspend: %{customdata[0]}<br>"
                        "% di atas OE: %{customdata[1]:.1f}%<br>"
                        "Jumlah PO: %{customdata[2]}<br>"
                        "Material No: %{customdata[3]}"
                        "<extra></extra>"
                    )
                )
                fig.update_layout(
                    height=420,
                    yaxis={'categoryorder': 'total ascending'},
                    coloraxis_colorbar=dict(title='% Overspend'),
                    xaxis=idr_axis(overspend_data['total_overspend'].max() * 1.15), margin=dict(t=20, b=40, l=20, r=40)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("Tidak ada material dengan realisasi melebihi OE pada periode ini.")

        with col_ef:
            title_col, btn_col = st.columns([9, 1])
            with title_col:
                st.markdown("""
                    <h1 style='display: flex; align-items: center; font-size:22px;'>
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-patch-check-fill" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                            <path d="M10.067.87a2.89 2.89 0 0 0-4.134 0l-.622.638-.89-.011a2.89 2.89 0 0 0-2.924 2.924l.01.89-.636.622a2.89 2.89 0 0 0 0 4.134l.637.622-.011.89a2.89 2.89 0 0 0 2.924 2.924l.89-.01.622.636a2.89 2.89 0 0 0 4.134 0l.622-.637.89.011a2.89 2.89 0 0 0 2.924-2.924l-.01-.89.636-.622a2.89 2.89 0 0 0 0-4.134l-.637-.622.011-.89a2.89 2.89 0 0 0-2.924-2.924l-.89.01zm.287 5.984-3 3a.5.5 0 0 1-.708 0l-1.5-1.5a.5.5 0 1 1 .708-.708L7 8.793l2.646-2.647a.5.5 0 0 1 .708.708"/>
                        </svg>
                        Top 10 Material: Efisiensi Terbesar
                    </h1>
                """, unsafe_allow_html=True)
            with btn_col:
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                with st.popover(":material/visibility:", help="Lihat Formula"):
                    st.info("""\
**Top 10 Material: Efisiensi Terbesar**: Bar chart 10 material dengan total penghematan (OE - realisasi) terbesar.

**Formula Excel:** (PO SAP)
- Filter **PO Deletion Flag** selain `L`
- Filter **Material No** sesuai yang dicari, pastikan **Description** sesuai
- Buat kolom **OE**: `= Estimasi_PR × Qty_PR`
- Buat kolom **Efisiensi**: `= OE − Total_Amount_in_Local_Curr`
- Jumlahkan kolom **Efisiensi** yang lebih dari **0**

**Catatan:** Efisiensi besar belum tentu selalu positif, bisa jadi OE-nya terlalu tinggi sejak awal, atau spesifikasi barang diturunkan. Perlu dikonfirmasi ke bagian terkait.
                """)

            st.caption("Top 10 material dengan penghematan terbesar terhadap OE.")

            efisien_query = f"""
            SELECT
                poi.material_no,
                COALESCE(m.description, MIN(poi.description), 'Unknown')           AS nama_material,
                SUM((poi.estimasi_pr * poi.quantity_pr) - poi.total_amount_local_curr) AS total_efisiensi,
                ROUND(AVG(
                    CASE WHEN (poi.estimasi_pr * poi.quantity_pr) > 0
                    THEN (((poi.estimasi_pr * poi.quantity_pr) - poi.total_amount_local_curr)
                          / (poi.estimasi_pr * poi.quantity_pr) * 100)
                    END
                )::numeric, 1)                                                     AS persen_efisiensi,
                COUNT(DISTINCT poi.nomor_po)                                       AS jumlah_po
            FROM po_items poi
            JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
            LEFT JOIN materials m ON poi.material_no = m.material_no
            WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
            AND poi.nomor_po IS NOT NULL
            AND poi.estimasi_pr IS NOT NULL AND poi.estimasi_pr > 0
            AND poi.quantity_pr IS NOT NULL AND poi.quantity_pr > 0
            AND poi.total_amount_local_curr < (poi.estimasi_pr * poi.quantity_pr)
            AND ({bagian_po_cond.replace('bagian_po', 'poi.bagian_po')})
            AND {dept_cond}
            AND {pg_cond}
            GROUP BY poi.material_no, m.description
            ORDER BY total_efisiensi DESC
            LIMIT 10
            """
            with st.spinner("Memuat top efisiensi..."):
                efisien_data = load_data(efisien_query)

            if not efisien_data.empty:
                efisien_data['label']           = efisien_data['nama_material'].str[:30]
                efisien_data['label_text']      = efisien_data['total_efisiensi'].apply(format_idr_short)
                efisien_data['hover_efisiensi'] = efisien_data['total_efisiensi'].apply(
                    lambda x: f"Rp {x:,.0f}"
                )
                fig_ef = px.bar(
                    efisien_data,
                    x='total_efisiensi', y='label', orientation='h',
                    text='label_text',
                    color='persen_efisiensi',
                    color_continuous_scale='Greens',
                    labels={
                        'total_efisiensi':  'Total Efisiensi (IDR)',
                        'label':            'Material',
                        'persen_efisiensi': '% Efisiensi',
                    },
                    custom_data=['hover_efisiensi', 'persen_efisiensi', 'jumlah_po', 'material_no'],
                )
                fig_ef.update_traces(
                    textposition='outside',
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        "Total Efisiensi: %{customdata[0]}<br>"
                        "% Efisiensi: %{customdata[1]:.1f}%<br>"
                        "Jumlah PO: %{customdata[2]}<br>"
                        "Material No: %{customdata[3]}"
                        "<extra></extra>"
                    )
                )
                fig_ef.update_layout(
                    height=450,
                    yaxis={'categoryorder': 'total ascending'},
                    coloraxis_colorbar=dict(title='% Efisiensi'),
                    xaxis=idr_axis(efisien_data['total_efisiensi'].max() * 1.15), margin=dict(t=20, b=40, l=20, r=40)
                )
                st.plotly_chart(fig_ef, use_container_width=True)
            else:
                st.info("Tidak ada material dengan realisasi di bawah OE pada periode ini.")

        st.markdown("---")

        # == ROW 2: Harga per Vendor & Tren Harga Historis =========================

        # 1. Load data variasi vendor terlebih dahulu untuk mendapatkan daftar material
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
            COUNT(DISTINCT v.nomor_po)                                          AS jumlah_po,
            ROUND(AVG(
                CASE
                    WHEN v.date_ordered IS NOT NULL AND v.first_full_release IS NOT NULL
                    THEN EXTRACT(DAY FROM (v.date_ordered - v.first_full_release))
                END
            )::numeric, 1)                                                       AS avg_lead_time,
            COUNT(CASE WHEN v.on_time_delivery = 'TEPAT WAKTU' THEN 1 END)          AS jml_ontime,
            COUNT(CASE WHEN v.on_time_delivery IS NOT NULL THEN 1 END)          AS jml_delivery_ada
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
            
            # 2. Filter Global untuk Material (Satu Filter untuk Kedua Komponen)
            selected_mat = st.selectbox(
                "Pilih Material:",
                options=material_options,
                format_func=lambda x: material_labels.get(x, x),
                key="select_material_shared"
            )

        else:
            selected_mat = None
            st.selectbox("Pilih Material:", options=["Tidak ada data"], disabled=True, key="select_material_shared_disabled")
            
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        # == KOLOM 1: Variasi Harga Antar Vendor (Chart Saja) =====================
        with col1:
            title_col, btn_col = st.columns([9, 1])
            with title_col:
                st.markdown("""
                    <h1 style='display: flex; align-items: center; font-size:22px;'>
                        <svg xmlns="[http://www.w3.org/2000/svg](http://www.w3.org/2000/svg)" width="20" height="20" fill="currentColor" class="bi bi-people-fill" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                            <path d="M7 14s-1 0-1-1 1-4 5-4 5 3 5 4-1 1-1 1zm4-6a3 3 0 1 0 0-6 3 3 0 0 0 0 6m-5.784 6A2.24 2.24 0 0 1 5 13c0-1.355.68-2.75 1.936-3.72A6.3 6.3 0 0 0 5 9c-4 0-5 3-5 4s1 1 1 1zM4.5 8a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5"/>
                        </svg>
                        Variasi Harga Antar Vendor (Top 10 Material)
                    </h1>
                """, unsafe_allow_html=True)
            with btn_col:
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                with st.popover(":material/visibility:", help="Lihat Formula"):
                    st.info("""\
    **Variasi Harga Antar Vendor (Top 10 Material)**: Perbandingan harga satuan dari vendor berbeda untuk material yang sama.

    **Formula Excel:** (PO SAP)
    - Filter **PO Deletion Flag** selain `L`
    - Filter **Material No** sesuai yang dicari, pastikan **Description** sesuai
    - Pastikan filter **1St Full Release** sesuai dengan filter di dashboard
    - Buat kolom baru `=Total Amount in Local Curr / Qty PO`
    - Jika dua item pada **Vendor Name** yang sama, maka kolom baru tersebut dirata-rata
                """)

            st.caption("Top 10 perbandingan harga satuan dari vendor berbeda untuk material yang sama.")

            if vendor_price_data.empty or selected_mat is None:
                st.info("Tidak ada data variasi harga yang tersedia.")
            else:
                df_mat = vendor_price_data[vendor_price_data['material_no'] == selected_mat]
                if df_mat.empty:
                    st.info("Tidak ada data variasi harga untuk material ini.")
                else:
                    fig = px.bar(
                        df_mat,
                        x='vendor_name', y='harga_satuan_avg',
                        text=df_mat['harga_satuan_avg'].apply(format_idr_short),
                        color='harga_satuan_avg',
                        color_continuous_scale='Blues',
                        labels={'vendor_name': 'Vendor', 'harga_satuan_avg': 'Harga Satuan Rata-rata (IDR)'}
                    )
                    fig.update_layout(
                        height=380, showlegend=False,
                        coloraxis_showscale=False, xaxis_tickangle=-30,
                        yaxis=idr_axis(df_mat['harga_satuan_avg'].max() * 1.15), margin=dict(t=20, b=40, l=20, r=20)
                    )
                    fig.update_traces(textposition='outside')
                    st.plotly_chart(fig, use_container_width=True)

            # == KOLOM 2: Tren Harga Historis per Material ============================
            with col2:
                title_col, btn_col = st.columns([9, 1])
                with title_col:
                    st.markdown("""
                        <h1 style='display: flex; align-items: center; font-size:22px;'>
                            <svg xmlns="[http://www.w3.org/2000/svg](http://www.w3.org/2000/svg)" width="20" height="20" fill="currentColor" class="bi bi-graph-up" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                                <path fill-rule="evenodd" d="M0 0h1v15h15v1H0zm14.817 3.113a.5.5 0 0 1 .07.704l-4.5 5.5a.5.5 0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5 0 0 1 .758-.06l2.609 2.61 4.15-5.073a.5.5 0 0 1 .704-.07"/>
                            </svg>
                            Tren Harga Historis per Material
                        </h1>
                    """, unsafe_allow_html=True)
                with btn_col:
                    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                    with st.popover(":material/visibility:", help="Lihat Formula"):
                        st.info("""\
        **Tren Harga Historis per Material**: Line chart pergerakan harga satuan PO per bulan. Berguna untuk mendeteksi kenaikan harga yang tidak wajar dan melihat konsistensi vendor.

        **Formula Excel:** (PO SAP)
        - Filter **PO Deletion Flag** selain `L`
        - Filter **Material No** sesuai yang dicari, pastikan **Description** sesuai
        - Pastikan filter **1St Full Release** sesuai dengan bulan yang dicari
        - Buat kolom baru `=Total Amount in Local Curr / Qty PO`
        - Rata-rata kolom tersebut

        **Kegunaan analisis:**
        - Tren **naik** = indikasi inflasi bahan baku atau leverage vendor → perlu renegosiasi ⚠️
        - Tren **turun** = negosiasi berhasil atau pasar lebih kompetitif ✅
        - **Lonjakan tiba-tiba** = perlu investigasi (vendor baru, perubahan spesifikasi, atau input keliru)
                    """)

                st.caption("Pergerakan rata-rata harga satuan PO dari waktu ke waktu.")

                if selected_mat is None:
                    st.info("Tidak ada data historis yang tersedia.")
                else:
                    # Filter bagian/dept/pg tetap diterapkan agar tren konsisten
                    # dengan filter aktif. Filter tanggal sengaja tidak dibatasi
                    # agar seluruh histori harga terbaca dengan baik.
                    _trend_bagian = bagian_po_cond.replace('bagian_po', 'bagian_po')
                    trend_harga_query = f"""
                    SELECT
                        DATE_TRUNC('month', date_ordered)::DATE                                  AS bulan,
                        ROUND((SUM(total_amount_local_curr) / NULLIF(SUM(qty_po), 0))::numeric, 0) AS harga_satuan_avg,
                        COUNT(DISTINCT nomor_po)                                                 AS jumlah_po,
                        COUNT(DISTINCT vendor_name)                                              AS jumlah_vendor
                    FROM vw_pr_po_complete
                    WHERE material_no = '{selected_mat}'
                    AND date_ordered IS NOT NULL
                    AND qty_po > 0
                    AND total_amount_local_curr > 0
                    AND nomor_po IS NOT NULL
                    AND ({_trend_bagian})
                    AND ({dept_cond.replace('poi.department_code', 'department_code')})
                    AND ({pg_cond.replace('poh.purchasing_group', 'purchasing_group')})
                    GROUP BY 1
                    ORDER BY 1
                    """
                    with st.spinner("Memuat tren harga..."):
                        trend_harga_data = load_data(trend_harga_query)

                    if not trend_harga_data.empty:
                        trend_harga_data['bulan'] = pd.to_datetime(trend_harga_data['bulan'])

                        fig_trend = go.Figure()
                        fig_trend.add_trace(go.Scatter(
                            x=trend_harga_data['bulan'],
                            y=trend_harga_data['harga_satuan_avg'],
                            mode='lines+markers',
                            name='Harga Realisasi (PO)',
                            line=dict(color='#1f77b4', width=2.5),
                            marker=dict(size=7),
                            customdata=trend_harga_data[['jumlah_po', 'jumlah_vendor']],
                            hovertemplate=(
                                '<b>%{x|%b %Y}</b><br>'
                                'Harga Realisasi: Rp %{y:,.0f}/unit<br>'
                                'Jumlah PO: %{customdata[0]}<br>'
                                'Vendor aktif: %{customdata[1]}'
                                '<extra></extra>'
                            )
                        ))
                        y_max_trend = trend_harga_data['harga_satuan_avg'].max() * 1.15
                        fig_trend.update_layout(
                            height=400,
                            xaxis_title='Bulan',
                            yaxis_title='Harga Satuan (IDR/unit)',
                            legend=dict(orientation='h', yanchor='bottom', y=1.02),
                            hovermode='x unified', margin=dict(t=40, b=40, l=20, r=20),
                            yaxis=idr_axis(y_max_trend),
                        )
                        st.plotly_chart(fig_trend, use_container_width=True)
                        st.caption('Chart ini menampilkan seluruh histori material tanpa dibatasi filter tanggal, agar tren harga dapat terbaca dengan baik.')
                    else:
                        st.info("Tidak ada data historis untuk material ini.")


        # == TABEL FULL WIDTH: Perbandingan Vendor ================================
        st.markdown("<br>", unsafe_allow_html=True)
        
        title_col_tbl, btn_col_tbl = st.columns([9, 1])
        with title_col_tbl:
            st.markdown("""
                <h1 style='display: flex; align-items: center; font-size:22px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-graph-up" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                        <path fill-rule="evenodd" d="M2.5 12a.5.5 0 0 1 .5-.5h10a.5.5 0 0 1 0 1H3a.5.5 0 0 1-.5-.5m0-4a.5.5 0 0 1 .5-.5h10a.5.5 0 0 1 0 1H3a.5.5 0 0 1-.5-.5m0-4a.5.5 0 0 1 .5-.5h10a.5.5 0 0 1 0 1H3a.5.5 0 0 1-.5-.5"/>
                    </svg>
                    Perbandingan Vendor: Harga · Kecepatan · Reliabilitas
                </h1>
            """, unsafe_allow_html=True)
        
        with btn_col_tbl:
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Lihat Formula"):
                st.info("""\
**Perbandingan Vendor**: Tabel ini menampilkan metrik kinerja vendor untuk material yang sedang dipilih, membantu Anda memilih vendor terbaik berdasarkan tiga pilar utama.

**Kalkulasi Metrik:**
- **Harga Satuan**: Seperti pada chart **Variasi Harga Antar Vendor (Top 10 Material)**
- **Lead Time Proses**: Rata-rata waktu dari **1St Full Release** ke **Date Ordered**
- **On-Time Delivery**: `(Jumlah pengiriman 'TEPAT WAKTU' / Total pengiriman yang memiliki status) × 100%`
- **Frekuensi**: Berapa kali transaksi PO dengan vendor ini

**Indikator Warna:**
- 🟢 **Terbaik (Hijau)**: Harga terendah (selisih ≤ 2% dari minimum), Lead Time sangat cepat, On-Time ≥ 90%
- 🟡 **Menengah (Kuning/Oranye)**: Harga bersaing (selisih ≤ 10%), Lead Time wajar, On-Time ≥ 70%
- 🔴 **Perlu Perhatian (Merah)**: Harga jauh lebih mahal (> 10%), Lead Time lama, On-Time < 70%
                """)

        st.caption('Tiga dimensi pembeda antar vendor untuk material yang sama.')

        if vendor_price_data.empty or selected_mat is None:
            st.info("Tidak ada data perbandingan vendor yang tersedia.")
        else:
            df_tbl = df_mat.copy()
            if df_tbl.empty:
                st.info("Tidak ada data perbandingan vendor untuk material ini.")
            else:
                df_tbl['pct_ontime'] = df_tbl.apply(
                    lambda r: round(r['jml_ontime'] / r['jml_delivery_ada'] * 100, 1)
                    if r['jml_delivery_ada'] > 0 else None,
                    axis=1
                )
                df_tbl = df_tbl.sort_values('harga_satuan_avg')

                harga_min = df_tbl['harga_satuan_avg'].min()
                lt_vals   = df_tbl['avg_lead_time'].dropna()
                lt_min    = lt_vals.min() if len(lt_vals) > 0 else 1
                max_po    = df_tbl['jumlah_po'].max()

                # Helper: kembalikan HTML cell, pakai single-quote di dalam, tidak ada backslash
                def _cell_harga(val):
                    if pd.isna(val):
                        return '<span style="color:gray">-</span>'
                    pct   = (val - harga_min) / harga_min * 100 if harga_min > 0 else 0
                    color = '#09ab3b' if pct <= 2 else ('#f0a500' if pct <= 10 else '#e03c3c')
                    arrow = '&#9660;' if pct <= 2 else ('&#9650;' if pct > 10 else '~')
                    return '<span style="color:' + color + ';font-weight:600">' + arrow + ' ' + format_idr_short(val) + '</span>'

                def _cell_lt(val):
                    if pd.isna(val):
                        return '<span style="color:gray">-</span>'
                    color = '#09ab3b' if val <= lt_min * 1.3 else ('#f0a500' if val <= lt_min * 2 else '#e03c3c')
                    return '<span style="color:' + color + ';font-weight:600">' + str(int(val)) + ' hari</span>'

                def _cell_ontime(val, jml):
                    if pd.isna(val) or jml == 0:
                        return '<span style="color:gray">-</span>'
                    color = '#09ab3b' if val >= 90 else ('#f0a500' if val >= 70 else '#e03c3c')
                    return '<span style="color:' + color + ';font-weight:600">' + str(int(val)) + '%</span>'

                def _cell_freq(val):
                    pct   = val / max_po if max_po > 0 else 0
                    bar_w = max(4, int(pct * 56))
                    bar   = '<div style="width:' + str(bar_w) + 'px;height:8px;background:#1f77b4;border-radius:4px;display:inline-block;vertical-align:middle"></div>'
                    txt   = '<span style="font-weight:600;margin-left:6px">' + str(int(val)) + 'x</span>'
                    return bar + txt

                # Build baris tabel
                BD = 'border-bottom:1px solid rgba(128,128,128,0.2)'
                P  = 'padding:8px 10px;' + BD
                rows_parts = []
                for _, row in df_tbl.iterrows():
                    vname = str(row['vendor_name'])
                    vname = (vname[:38] + '…') if len(vname) > 38 else vname
                    tr = (
                        '<tr>'
                        + '<td style="' + P + 'font-size:13px">' + vname + '</td>'
                        + '<td style="' + P + 'text-align:center">' + _cell_harga(row['harga_satuan_avg']) + '</td>'
                        + '<td style="' + P + 'text-align:center">' + _cell_lt(row['avg_lead_time']) + '</td>'
                        + '<td style="' + P + 'text-align:center">' + _cell_ontime(row['pct_ontime'], row['jml_delivery_ada']) + '</td>'
                        + '<td style="' + P + '">' + _cell_freq(row['jumlah_po']) + '</td>'
                        + '</tr>'
                    )
                    rows_parts.append(tr)

                TH = 'padding:8px 10px;font-size:18px;font-weight:600;'
                thead = (
                    '<thead><tr style="border-bottom:2px solid rgba(128,128,128,0.4)">'
                    + '<th style="' + TH + 'text-align:left">Vendor</th>'
                    + '<th style="' + TH + 'text-align:center">Harga Satuan<br><small style="font-weight:400">(IDR/unit, rata-rata)</small></th>'
                    + '<th style="' + TH + 'text-align:center">Lead Time Proses<br><small style="font-weight:400">(PR &#8594; PO, rata-rata)</small></th>'
                    + '<th style="' + TH + 'text-align:center">On-Time Delivery<br><small style="font-weight:400">(% tepat waktu)</small></th>'
                    + '<th style="' + TH + 'text-align:center">Frekuensi<br><small style="font-weight:400">(jumlah PO)</small></th>'
                    + '</tr></thead>'
                )
                tabel_html = (
                    '<table style="width:100%;border-collapse:collapse;font-size:14px">'
                    + thead
                    + '<tbody>' + ''.join(rows_parts) + '</tbody>'
                    + '</table>'
                    + '<p style="font-size:12px;margin-top:8px">'
                    + '&#128994; Terbaik &nbsp;|&nbsp; &#128993; Menengah &nbsp;|&nbsp; &#128308; Perlu perhatian'
                    + ' &nbsp;|&nbsp; - = data tidak tersedia &nbsp;|&nbsp; Harga diurutkan dari terendah ke tertinggi'
                    + '</p>'
                )
                st.markdown(tabel_html, unsafe_allow_html=True)

        st.markdown("---")

        # == ROW 3: Ranking Vendor Keseluruhan =====================================
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:22px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-trophy-fill" viewBox="0 0 16 16" style="margin-bottom: 4px; margin-right: 8px;">
                    <path d="M2.5.5A.5.5 0 0 1 3 0h10a.5.5 0 0 1 .5.5q0 .807-.034 1.536a3 3 0 1 1-1.133 5.89c-.79 1.865-1.878 2.777-2.833 3.011v2.173l1.425.356c.194.048.377.135.537.255L13.3 15.1a.5.5 0 0 1-.3.9H3a.5.5 0 0 1-.3-.9l1.838-1.379c.16-.12.343-.207.537-.255L6.5 13.11v-2.173c-.955-.234-2.043-1.146-2.833-3.012a3 3 0 1 1-1.132-5.89A33 33 0 0 1 2.5.5m.099 2.54a2 2 0 0 0 .72 3.935c-.333-1.05-.588-2.346-.72-3.935m10.083 3.935a2 2 0 0 0 .72-3.935c-.133 1.59-.388 2.885-.72 3.935"/>
                </svg>
                Ranking Vendor Keseluruhan
            </h1>
        """, unsafe_allow_html=True)
 
        st.caption("Performa keseluruhan vendor lintas material dalam periode filter. Diurutkan berdasarkan total nilai PO terbesar.")
 
        ranking_vendor_query = f"""
        SELECT
            v.vendor_name,
            COUNT(DISTINCT poi.nomor_po)                                             AS jumlah_po,
            COUNT(DISTINCT poi.material_no)                                          AS jumlah_material,
            COALESCE(SUM(poi.total_amount_local_curr), 0)                            AS total_nilai_po,
            ROUND(AVG(
                CASE WHEN (poi.estimasi_pr * poi.quantity_pr) > 0
                THEN ((poi.total_amount_local_curr - (poi.estimasi_pr * poi.quantity_pr))
                      / (poi.estimasi_pr * poi.quantity_pr) * 100)
                END
            )::numeric, 1)                                                           AS pct_vs_oe,
            ROUND(AVG(
                CASE WHEN poh.date_ordered IS NOT NULL AND poi.first_full_release IS NOT NULL
                THEN (poh.date_ordered::date - poi.first_full_release::date)
                END
            )::numeric, 1)                                                           AS avg_lead_time,
            COUNT(CASE WHEN poi.on_time_delivery = 'TEPAT WAKTU' THEN 1 END)        AS jml_ontime,
            COUNT(CASE WHEN poi.on_time_delivery IN ('TEPAT WAKTU','TERLAMBAT')
                  THEN 1 END)                                                        AS jml_delivery_ada
        FROM po_items poi
        JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
        LEFT JOIN vendors v ON poh.vendor_code = v.vendor_code
        WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
          AND v.vendor_name IS NOT NULL
          AND poi.total_amount_local_curr IS NOT NULL
          AND {bagian_po_poi}
          AND {dept_cond}
          AND {pg_cond}
        GROUP BY v.vendor_name
        ORDER BY total_nilai_po DESC
        LIMIT 50
        """
        with st.spinner("Memuat ranking vendor..."):
            ranking_vendor_data = load_data(ranking_vendor_query)
 
        if not ranking_vendor_data.empty:
            # Hitung % on-time
            ranking_vendor_data['pct_ontime'] = ranking_vendor_data.apply(
                lambda r: round(r['jml_ontime'] / r['jml_delivery_ada'] * 100, 1)
                if r['jml_delivery_ada'] > 0 else None,
                axis=1
            )
 
            # == Tab chart vs tabel =============================================
            tab_chart, tab_tabel = st.tabs([
                ":material/bar_chart: Visualisasi",
                ":material/table_chart: Tabel Lengkap",
            ])
 
            with tab_chart:
                # Dua chart berdampingan: Total Nilai PO & % vs OE
                ch1, ch2 = st.columns(2)
 
                with ch1:
                    _title_ch1, _btn_ch1 = st.columns([9, 1])
                    with _title_ch1:
                        st.markdown("**Peta Risiko Vendor: Nilai PO vs % Selisih terhadap OE**")
                    with _btn_ch1:
                        with st.popover(":material/visibility:", help="Lihat Formula"):
                            st.info("""\
**Peta Risiko Vendor (Scatter)**: Bubble chart posisi vendor berdasarkan dua dimensi risiko sekaligus, seberapa besar nilai transaksinya dan seberapa mahal harganya terhadap OE.
 
**Sumbu X: Total Nilai PO:** `SUM(total_amount_local_curr)` per vendor dalam periode filter.
 
**Sumbu Y: % Selisih vs OE:** Rata-rata selisih realisasi terhadap OE per item:
```
AVG((total_amount_local_curr − estimasi_pr × quantity_pr) / (estimasi_pr × quantity_pr) × 100)
```
Nilai positif = realisasi lebih mahal dari OE. Nilai negatif = realisasi lebih hemat.
 
**Ukuran titik** = jumlah PO vendor tersebut.
 
**Garis referensi:**
- Horizontal (Y=0): batas antara mahal vs hemat terhadap OE
- Vertikal (X=median): batas antara vendor bernilai besar vs kecil
 
**Kuadran:**
- 🔴 Kanan-atas: Nilai besar & mahal → **prioritas evaluasi/renegosiasi**
- 🔵 Kanan-bawah: Nilai besar & efisien → **pertahankan**
- 🟡 Kiri-atas: Nilai kecil & mahal
- 🟢 Kiri-bawah: Nilai kecil & efisien
                        """)
                    scatter_rv = ranking_vendor_data.dropna(subset=['pct_vs_oe']).copy()
                    scatter_rv['label'] = scatter_rv['vendor_name'].str[:30]
                    scatter_rv['hover_nilai'] = scatter_rv['total_nilai_po'].apply(
                        lambda x: f"Rp {x:,.0f}"
                    )
                    scatter_rv['kuadran'] = scatter_rv.apply(
                        lambda r: '🔴 Nilai Besar & Mahal'   if r['total_nilai_po'] >= scatter_rv['total_nilai_po'].median() and r['pct_vs_oe'] > 0
                        else ('🟡 Nilai Kecil & Mahal'        if r['pct_vs_oe'] > 0
                        else ('🔵 Nilai Besar & Efisien'      if r['total_nilai_po'] >= scatter_rv['total_nilai_po'].median()
                        else '🟢 Nilai Kecil & Efisien')),
                        axis=1
                    )
                    color_map_rv = {
                        '🔴 Nilai Besar & Mahal':   '#d62728',
                        '🟡 Nilai Kecil & Mahal':   '#f0a500',
                        '🔵 Nilai Besar & Efisien': '#1f77b4',
                        '🟢 Nilai Kecil & Efisien': '#2ca02c',
                    }
                    fig_rv1 = px.scatter(
                        scatter_rv,
                        x='total_nilai_po',
                        y='pct_vs_oe',
                        color='kuadran',
                        color_discrete_map=color_map_rv,
                        size='jumlah_po',
                        size_max=30,
                        hover_name='label',
                        custom_data=['hover_nilai', 'jumlah_po', 'jumlah_material', 'avg_lead_time'],
                        labels={
                            'total_nilai_po': 'Total Nilai PO (IDR)',
                            'pct_vs_oe':      '% Selisih vs OE',
                            'kuadran':        'Kuadran',
                        },
                    )
                    fig_rv1.update_traces(
                        hovertemplate=(
                            "<b>%{hovertext}</b><br>"
                            "Total Nilai PO: %{customdata[0]}<br>"
                            "% vs OE: %{y:+.1f}%<br>"
                            "Jumlah PO: %{customdata[1]}<br>"
                            "Jumlah Material: %{customdata[2]}<br>"
                            "Avg Lead Time: %{customdata[3]:.0f} hari"
                            "<extra></extra>"
                        )
                    )
                    # Garis referensi: vertikal (median nilai) & horizontal (0% OE)
                    median_nilai = scatter_rv['total_nilai_po'].median()
                    fig_rv1.add_hline(y=0,           line_dash='dash', line_color='gray',   line_width=1)
                    fig_rv1.add_vline(x=median_nilai, line_dash='dot',  line_color='gray',   line_width=1)
                    # Anotasi kuadran
                    x_max = scatter_rv['total_nilai_po'].max()
                    y_max = scatter_rv['pct_vs_oe'].abs().max()
                    fig_rv1.add_annotation(
                        x=x_max * 0.98, y=y_max * 0.92, xanchor='right',
                        text="⚠️ Prioritas Evaluasi", showarrow=False,
                        font=dict(color='#d62728', size=11)
                    )
                    fig_rv1.add_annotation(
                        x=x_max * 0.98, y=-y_max * 0.92, xanchor='right',
                        text="✅ Pertahankan", showarrow=False,
                        font=dict(color='#1f77b4', size=11)
                    )
                    fig_rv1.update_layout(
                        height=520,
                        xaxis=idr_axis(x_max * 1.05),
                        yaxis_title='% Selisih vs OE (+ = lebih mahal, - = lebih hemat)',
                        legend=dict(orientation='h', yanchor='bottom', y=1.02, font=dict(size=10)),
                        hovermode='closest',
                        margin=dict(t=40, b=40, l=40, r=20)
                    )
                    st.plotly_chart(fig_rv1, use_container_width=True)
                    st.caption(
                        "Titik di atas garis horizontal (0%) = realisasi melebihi OE. "
                        "Garis vertikal = nilai PO median. Ukuran titik = jumlah PO."
                    )
 
                with ch2:
                    _title_ch2, _btn_ch2 = st.columns([9, 1])
                    with _title_ch2:
                        st.markdown("**% Realisasi vs OE per Vendor (Top 20, diurutkan terburuk)**")
                    with _btn_ch2:
                        with st.popover(":material/visibility:", help="Lihat Formula"):
                            st.info("""\
**% Realisasi vs OE per Vendor (Top 20)**: Bar chart horizontal yang menampilkan posisi setiap vendor terhadap OE, diurutkan dari yang paling mahal ke yang paling hemat.
 
**Data yang ditampilkan:** 20 vendor dengan total nilai PO terbesar (Top 20 dari query utama), kemudian diurutkan ulang berdasarkan % selisih vs OE dari terburuk ke terbaik.
 
**% Selisih vs OE:**
```
AVG((total_amount_local_curr − estimasi_pr × quantity_pr) / (estimasi_pr × quantity_pr) × 100)
```
 
**Warna bar:**
- 🔴 Merah: realisasi jauh di atas OE (> 10%) → perlu investigasi
- 🟡 Kuning: realisasi sedikit di atas OE (0% – 10%) → perlu perhatian
- 🟢 Hijau: realisasi di bawah atau sesuai OE (≤ 0%) → efisien
 
**Catatan:** Chart ini membantu melihat distribusi performa vendor secara cepat, vendor di sebelah kanan bar (nilai positif besar) adalah prioritas renegosiasi harga.
                        """)
                    top20_oe = ranking_vendor_data.head(20).dropna(subset=['pct_vs_oe']).copy()
                    if not top20_oe.empty:
                        top20_oe = top20_oe.sort_values('pct_vs_oe', ascending=False)
                        top20_oe['warna'] = top20_oe['pct_vs_oe'].apply(
                            lambda x: '🔴 Melebihi OE (>10%)' if x > 10
                            else ('🟡 Sedikit di atas OE (0-10%)' if x > 0
                            else '🟢 Di Bawah / Sesuai OE')
                        )
                        color_map = {
                            '🔴 Melebihi OE (>10%)':        '#d62728',
                            '🟡 Sedikit di atas OE (0-10%)': '#f0a500',
                            '🟢 Di Bawah / Sesuai OE':       '#2ca02c',
                        }
                        top20_oe['label'] = top20_oe['vendor_name'].str[:28]
                        fig_rv2 = px.bar(
                            top20_oe,
                            x='pct_vs_oe', y='label', orientation='h',
                            color='warna',
                            color_discrete_map=color_map,
                            text=top20_oe['pct_vs_oe'].apply(lambda x: f"{x:+.1f}%"),
                            labels={'pct_vs_oe': '% Selisih vs OE', 'label': 'Vendor', 'warna': 'Status'},
                            custom_data=['jumlah_po'],
                        )
                        fig_rv2.update_traces(
                            textposition='outside',
                            hovertemplate=(
                                "<b>%{y}</b><br>"
                                "% vs OE: %{x:+.1f}%<br>"
                                "Jumlah PO: %{customdata[0]}"
                                "<extra></extra>"
                            )
                        )
                        x_abs = top20_oe['pct_vs_oe'].abs().max() * 1.3
                        fig_rv2.update_layout(
                            height=520,
                            yaxis={'categoryorder': 'total ascending'},
                            xaxis=dict(range=[-x_abs, x_abs]),
                            margin=dict(t=40, b=40, l=20, r=40),
                            legend=dict(orientation='h', yanchor='bottom', y=1.02, font=dict(size=11)),
                        )
                        fig_rv2.add_vline(x=0, line_dash='dash', line_color='gray', line_width=1)
                        st.plotly_chart(fig_rv2, use_container_width=True)
                    else:
                        st.info("Data % vs OE tidak tersedia untuk vendor ini.")
 
            with tab_tabel:
                max_po_rv  = ranking_vendor_data['jumlah_po'].max()
                max_val_rv = ranking_vendor_data['total_nilai_po'].max()
 
                def _rv_nilai(val):
                    if pd.isna(val): return '<span style="color:gray">-</span>'
                    pct   = val / max_val_rv if max_val_rv > 0 else 0
                    bar_w = max(4, int(pct * 80))
                    bar   = '<div style="width:' + str(bar_w) + 'px;height:8px;background:#1f77b4;border-radius:4px;display:inline-block;vertical-align:middle;margin-right:6px"></div>'
                    return bar + '<span style="font-weight:600">' + format_idr_short(val) + '</span>'
 
                def _rv_pct_oe(val):
                    if pd.isna(val): return '<span style="color:gray">-</span>'
                    color = '#2ca02c' if val <= 0 else ('#f0a500' if val <= 10 else '#d62728')
                    sign  = '+' if val > 0 else ''
                    return '<span style="color:' + color + ';font-weight:600">' + sign + f'{val:.1f}%</span>'
 
                def _rv_lt(val):
                    if pd.isna(val): return '<span style="color:gray">-</span>'
                    lt_vals_rv = ranking_vendor_data['avg_lead_time'].dropna()
                    lt_min_rv  = lt_vals_rv.min() if len(lt_vals_rv) > 0 else 1
                    color = '#2ca02c' if val <= lt_min_rv * 1.3 else ('#f0a500' if val <= lt_min_rv * 2 else '#d62728')
                    return '<span style="color:' + color + ';font-weight:600">' + str(int(val)) + ' hari</span>'
 
                def _rv_ontime(val, jml):
                    if pd.isna(val) or jml == 0: return '<span style="color:gray">-</span>'
                    color = '#2ca02c' if val >= 90 else ('#f0a500' if val >= 70 else '#d62728')
                    return '<span style="color:' + color + ';font-weight:600">' + str(int(val)) + '%</span>'
 
                def _rv_freq(val):
                    pct   = val / max_po_rv if max_po_rv > 0 else 0
                    bar_w = max(4, int(pct * 56))
                    bar   = '<div style="width:' + str(bar_w) + 'px;height:8px;background:#1f77b4;border-radius:4px;display:inline-block;vertical-align:middle"></div>'
                    return bar + '<span style="font-weight:600;margin-left:6px">' + str(int(val)) + 'x</span>'
 
                BD  = 'border-bottom:1px solid rgba(128,128,128,0.2)'
                P   = 'padding:8px 10px;' + BD
                TH  = 'padding:8px 10px;font-size:13px;font-weight:600;'
 
                rows_rv = []
                for idx_r, row in ranking_vendor_data.iterrows():
                    rank   = idx_r + 1
                    vname  = str(row['vendor_name'])
                    vname  = (vname[:40] + '…') if len(vname) > 40 else vname
                    medal  = '🥇' if rank == 1 else ('🥈' if rank == 2 else ('🥉' if rank == 3 else str(rank)))
                    tr = (
                        '<tr>'
                        + '<td style="' + P + 'text-align:center;font-weight:700">' + medal + '</td>'
                        + '<td style="' + P + 'font-size:13px">' + vname + '</td>'
                        + '<td style="' + P + 'text-align:center;font-weight:600">' + str(int(row['jumlah_material'])) + '</td>'
                        + '<td style="' + P + '">' + _rv_nilai(row['total_nilai_po']) + '</td>'
                        + '<td style="' + P + 'text-align:center">' + _rv_pct_oe(row['pct_vs_oe']) + '</td>'
                        + '<td style="' + P + 'text-align:center">' + _rv_lt(row['avg_lead_time']) + '</td>'
                        + '<td style="' + P + 'text-align:center">' + _rv_ontime(row['pct_ontime'], row['jml_delivery_ada']) + '</td>'
                        + '<td style="' + P + '">' + _rv_freq(row['jumlah_po']) + '</td>'
                        + '</tr>'
                    )
                    rows_rv.append(tr)
 
                thead_rv = (
                    '<thead><tr style="border-bottom:2px solid rgba(128,128,128,0.4)">'
                    + '<th style="' + TH + 'text-align:center">#</th>'
                    + '<th style="' + TH + 'text-align:left">Vendor</th>'
                    + '<th style="' + TH + 'text-align:center">Jml<br><small style="font-weight:400">Material</small></th>'
                    + '<th style="' + TH + 'text-align:left">Total Nilai PO<br><small style="font-weight:400">(IDR)</small></th>'
                    + '<th style="' + TH + 'text-align:center">% vs OE<br><small style="font-weight:400">(rata-rata)</small></th>'
                    + '<th style="' + TH + 'text-align:center">Avg Lead Time<br><small style="font-weight:400">(PR→PO)</small></th>'
                    + '<th style="' + TH + 'text-align:center">% On-Time<br><small style="font-weight:400">Delivery</small></th>'
                    + '<th style="' + TH + 'text-align:center">Frekuensi<br><small style="font-weight:400">(jml PO)</small></th>'
                    + '</tr></thead>'
                )
                tabel_rv_html = (
                    '<table style="width:100%;border-collapse:collapse;font-size:14px">'
                    + thead_rv
                    + '<tbody>' + ''.join(rows_rv) + '</tbody>'
                    + '</table>'
                    + '<p style="font-size:12px;margin-top:8px">'
                    + '🟢 Baik &nbsp;|&nbsp; 🟡 Perhatikan &nbsp;|&nbsp; 🔴 Perlu Evaluasi'
                    + ' &nbsp;|&nbsp; - = data tidak tersedia &nbsp;|&nbsp; Diurutkan: Total Nilai PO terbesar'
                    + '</p>'
                )
                st.markdown(tabel_rv_html, unsafe_allow_html=True)
 
                # Download tabel sebagai CSV
                csv_rv = ranking_vendor_data.drop(columns=['jml_ontime','jml_delivery_ada']).rename(columns={
                    'vendor_name':    'Vendor',
                    'jumlah_po':      'Jml PO',
                    'jumlah_material':'Jml Material',
                    'total_nilai_po': 'Total Nilai PO (IDR)',
                    'pct_vs_oe':      '% vs OE',
                    'avg_lead_time':  'Avg Lead Time (hari)',
                    'pct_ontime':     '% On-Time Delivery',
                }).to_csv(index=False)
                st.download_button(
                    label="Download sebagai CSV",
                    icon=":material/download:",
                    data=csv_rv,
                    file_name=f"ranking_vendor_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                )
        else:
            st.info("Tidak ada data vendor untuk filter yang dipilih.")
 
        st.markdown("---")

        # == ROW 4: Tabel Detail Evaluasi Harga ====================================
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
        LEFT JOIN purchase_orders poh ON v.nomor_po = poh.nomor_po
        WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
        AND v.nomor_po IS NOT NULL
        AND v.oe IS NOT NULL AND v.oe > 0
        AND v.qty_po > 0
        AND ({bagian_po_cond.replace('bagian_po', 'v.bagian_po')})
        AND ({dept_cond.replace('poi.department_code', 'v.department_code')})
        AND ({pg_cond.replace('poh.purchasing_group', 'v.purchasing_group')})
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

        st.markdown("---")

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

        # 2. Data Top Overspend
        if 'overspend_data' in locals() and not overspend_data.empty:
            konteks_lines.append("## 2. TOP 10 MATERIAL OVERSPEND TERBESAR")
            df_os_simple = overspend_data[['nama_material', 'total_overspend', 'persen_overspend']]
            konteks_lines.append(df_os_simple.to_csv(index=False))
            konteks_lines.append("\n")

        # 2b. Data Top Efisiensi
        if 'efisien_data' in locals() and not efisien_data.empty:
            konteks_lines.append("## 2b. TOP 10 MATERIAL EFISIENSI TERBESAR")
            df_ef_simple = efisien_data[['nama_material', 'total_efisiensi', 'persen_efisiensi']]
            konteks_lines.append(df_ef_simple.to_csv(index=False))
            konteks_lines.append("\n")

        # 2c. Ranking Vendor Keseluruhan (top 15)
        if 'ranking_vendor_data' in locals() and not ranking_vendor_data.empty:
            konteks_lines.append("## 2c. RANKING VENDOR KESELURUHAN (TOP 15)")
            df_rv_simple = ranking_vendor_data[['vendor_name','jumlah_po','jumlah_material',
                                                'total_nilai_po','pct_vs_oe',
                                                'avg_lead_time','pct_ontime']].head(15)
            konteks_lines.append(df_rv_simple.to_csv(index=False))
            konteks_lines.append("\n")

        # 3. Data Detail Harga (Ambil 15 teratas yang paling bermasalah)
        if 'detail_harga_data' in locals() and not detail_harga_data.empty:
            konteks_lines.append("## 3. DETAIL EVALUASI HARGA (15 ITEM DENGAN SELISIH TERBURUK)")
            df_detail_simple = detail_harga_data[['nama_material', 'rata_oe', 'rata_realisasi', 'persen_selisih_avg', 'status']].head(15)
            konteks_lines.append(df_detail_simple.to_csv(index=False))
            konteks_lines.append("\n")

        # Gabungkan konteks lokal halaman ini dengan konteks global lintas sistem
        suplemen = "\n# SUPLEMEN - DETAIL HALAMAN INI (Evaluasi Harga)\n" + "\n".join(konteks_lines)
        konteks_final = kwargs.get("global_context", "") + "\n---\n" + suplemen

        # Render kolom chat di paling bawah halaman
        with st.expander("Tanya ke Melati (Monitoring, Evaluasi, Laporan Terintegrasi)"):
            render_chat_analyst(
                konteks_data_teks=konteks_final, 
                nama_halaman="Evaluasi Harga Barang",
                load_data_fn=load_data,
            )