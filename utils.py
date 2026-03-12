"""
utils.py - Fungsi pembantu: format uang, CSS, dan filter kondisi SQL
"""

import streamlit as st
import pandas as pd
from google import genai
import base64
import os

# ─────────────────────────────────────────────────────────────────────────────
# FORMAT ANGKA & RUPIAH (STANDAR INDONESIA)
# ─────────────────────────────────────────────────────────────────────────────

def format_number(x, decimals=0) -> str:
    """Format angka biasa ke standar Indonesia (titik untuk ribuan, koma untuk desimal)."""
    if x is None or pd.isna(x):
        return "0"
    
    # Gunakan format bawaan python dulu (koma untuk ribuan, titik untuk desimal)
    if decimals > 0:
        raw_formatted = f"{float(x):,.{decimals}f}"
    else:
        raw_formatted = f"{int(x):,}"
        
    # Tukar koma menjadi titik, dan titik menjadi koma
    formatted = raw_formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
    return formatted

def format_currency(x) -> str:
    """Format ke Rp X.XXX (tanpa singkatan T/M/Jt)."""
    if x is None or pd.isna(x) or x == 0:
        return "Rp 0"
    return f"Rp {format_number(x)}"


def format_idr(x) -> str:
    """Format angka menjadi string Rupiah dengan suffix T/M/Jt."""
    if x is None or pd.isna(x) or x == 0:
        return "Rp 0"

    abs_x = abs(x)
    if abs_x >= 1e12:
        val, suffix = x / 1e12, "T"
    elif abs_x >= 1e9:
        val, suffix = x / 1e9, "M"
    elif abs_x >= 1e6:
        val, suffix = x / 1e6, "Jt"
    else:
        return format_currency(x)

    # Format 2 desimal
    formatted = f"{val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    if formatted.endswith(',00'):
        formatted = formatted[:-3]

    return f"Rp {formatted} {suffix}"


def format_idr_short(x) -> str:
    """Format angka ringkas untuk label chart (1 desimal)."""
    if x is None or pd.isna(x) or x == 0:
        return "0"

    abs_x = abs(x)
    if abs_x >= 1e12:
        val, suffix = x / 1e12, "T"
    elif abs_x >= 1e9:
        val, suffix = x / 1e9, "M"
    elif abs_x >= 1e6:
        val, suffix = x / 1e6, "Jt"
    else:
        return format_number(x)

    # Format 1 desimal
    formatted = f"{val:,.1f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    if formatted.endswith(',0'):
        formatted = formatted[:-2]

    return f"{formatted} {suffix}"


def idr_axis(max_val, n_ticks=6) -> dict:
    """
    Hasilkan dict konfigurasi axis Plotly dengan tickvals & ticktext format IDR Indonesia.
    Gunakan sebagai: fig.update_layout(xaxis=idr_axis(max_val), yaxis=idr_axis(max_val))
    atau: fig.update_xaxes(**idr_axis(max_val))

    Contoh output ticktext: '0', '20 Jt', '40 Jt', '1,5 M', '2 M', dsb.
    """
    import numpy as np

    if max_val is None or max_val <= 0:
        return {}

    step = max_val / (n_ticks - 1)
    tickvals = [round(step * i) for i in range(n_ticks)]

    def _fmt(v):
        abs_v = abs(v)
        if abs_v >= 1e12:
            val = v / 1e12
            s = "T"
        elif abs_v >= 1e9:
            val = v / 1e9
            s = "M"
        elif abs_v >= 1e6:
            val = v / 1e6
            s = "Jt"
        elif abs_v >= 1e3:
            val = v / 1e3
            s = "Rb"
        else:
            return str(int(v))

        # Hilangkan desimal jika bulat
        txt = f"{val:,.1f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        if txt.endswith(',0'):
            txt = txt[:-2]
        return f"{txt} {s}"

    ticktext = [_fmt(v) for v in tickvals]

    return dict(
        tickvals=tickvals,
        ticktext=ticktext,
        range=[0, max_val],
    )


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────────────────────────────────────

def inject_css():
    """Inject custom CSS adaptive light/dark mode ke halaman."""
    st.markdown("""
<style>
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] div {
        color: var(--text-color);
    }
    h1 {
        color: #1f77b4;
    }
    .stMultiSelect, .stDateInput {
        background-color: transparent;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# FILTER SQL BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_filter_conditions(
    date_from, date_to,
    selected_department, exclude_dept,
    selected_p_group, exclude_purchasing_group
) -> str:
    """Bangun string kondisi WHERE untuk query SQL dari nilai filter sidebar.
    
    Filter tanggal menggunakan kolom `first_full_release` (bukan `tgl_create_pr`).
    Total PR dihitung dari baris yang memiliki `first_full_release IS NOT NULL`
    dan tanggalnya masuk dalam rentang periode yang dipilih.
    """
    conditions = [
        f"first_full_release >= '{date_from}'",
        f"first_full_release <= '{date_to}'"
    ]

    if selected_department and 'All' not in selected_department:
        dept_list = "','".join(selected_department)
        if exclude_dept:
            conditions.append(f"(department_code NOT IN ('{dept_list}') OR department_code IS NULL)")
        else:
            conditions.append(f"department_code IN ('{dept_list}')")

    if selected_p_group and 'All' not in selected_p_group:
        pg_list = "','".join(selected_p_group)
        if exclude_purchasing_group:
            conditions.append(f"(purchasing_group NOT IN ('{pg_list}') OR purchasing_group IS NULL)")
        else:
            conditions.append(f"purchasing_group IN ('{pg_list}')")

    return " AND ".join(conditions)


def build_po_filter_conditions(date_from, date_to, bagian_po_cond='1=1') -> str:
    """Bangun WHERE clause untuk query PO langsung dari tabel po_items + purchase_orders.
    Filter tanggal berdasarkan date_ordered (bukan tgl_create_pr).
    Dipakai untuk metrik PO di semua halaman agar konsisten dengan v_dashboard.
    """
    return (
        f"poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}' "
        f"AND {bagian_po_cond.replace('bagian_po', 'poi.bagian_po')}"
    )


def build_bagian_conditions(selected_bagian, exclude_bagian) -> tuple[str, str]:
    """Kembalikan tuple (bagian_pr_cond, bagian_po_cond) untuk filter bagian."""
    if 'All' not in selected_bagian and selected_bagian:
        bagian_list = "','".join(selected_bagian)
        if exclude_bagian:
            pr = f"(bagian_pr NOT IN ('{bagian_list}') OR bagian_pr IS NULL)"
            po = f"(bagian_po NOT IN ('{bagian_list}') OR bagian_po IS NULL)"
        else:
            pr = f"bagian_pr IN ('{bagian_list}')"
            po = f"bagian_po IN ('{bagian_list}')"
        return pr, po
    return "1=1", "1=1"


# ─────────────────────────────────────────────────────────────────────────────
# SIPS WHERE CLAUSE BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_sips_where(date_from=None, date_to=None,
                     selected_nama=None, selected_bagian=None,
                     extra: list = None) -> str:
    """
    Bangun WHERE clause untuk query vw_sips.
    - Filter tanggal menggunakan tgl_disposisi_buyer (konsisten dengan ETL &
      kolom BULAN DISPO di Excel) — bukan requisition_date.
      Alasan: ETL menentukan bulan_import dari tgl_disposisi_buyer sebagai
      anchor utama, sehingga filter dashboard harus mengikuti kolom yang sama
      agar Total PR / Total PO sesuai dengan rekapan Excel atasan.
    - Filter bagian hanya aktif jika selected_bagian bukan ['All']
    - Sertakan extra=['nilai_sla IS NOT NULL'] dsb. jika perlu kondisi tambahan
    """
    wp = ["1=1"]
    if extra:
        wp.extend(extra)
    if date_from:
        wp.append(f"tgl_disposisi_buyer >= '{date_from}'")
    if date_to:
        wp.append(f"tgl_disposisi_buyer <= '{date_to}'")
    if selected_bagian and "All" not in selected_bagian:
        bg = ", ".join(f"'{b}'" for b in selected_bagian)
        wp.append(f"bagian IN ({bg})")
    if selected_nama and "All" not in selected_nama:
        nms = ", ".join(f"'{n}'" for n in selected_nama)
        wp.append(f"nama IN ({nms})")
    return " AND ".join(wp)

# ─────────────────────────────────────────────────────────────────────────────
# KOMPONEN AI ANALYST (GEMINI)
# ─────────────────────────────────────────────────────────────────────────────

def render_chat_analyst(konteks_data_teks: str, nama_halaman: str):
    """Merender antarmuka chat LLM secara sebaris (inline) dengan kotak scrollable."""
    st.divider()

    img_path = "assets/Melati_icon.png"
    img_b64 = ""

    if os.path.exists(img_path):
        with open(img_path, "rb") as img_file:
            img_b64 = base64.b64encode(img_file.read()).decode()

    if img_b64:
        # Jika gambar ditemukan, jadikan icon bulat (border-radius: 50%)
        icon_html = f'<img src="data:image/png;base64,{img_b64}" width="38" height="38" style="margin-right: 12px; border-radius: 50%; object-fit: cover; border: 2px solid #1f77b4;">'
    else:
        # Fallback (cadangan) jika gambar tidak ditemukan, gunakan emoji
        icon_html = '<span style="font-size: 32px; margin-right: 12px;">🕵️‍♀️</span>'
    
    # Header AI
    st.markdown(f"""
        <h1 style='display: flex; align-items: center; font-size:28px; color: #1f77b4; margin-bottom: 5px;'>
            {icon_html}
            Tanya ke Melati (Monitoring, Evaluasi, Laporan Terintegrasi)
        </h1>
    """, unsafe_allow_html=True)
    st.caption(f"Tanyakan *insight* atau kesimpulan dari data di sistem Monitoring & Reporting Pengadaan Barang.")

    # 1. Inisialisasi API
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        client = genai.Client(api_key=api_key)
    except Exception:
        st.error("API Key belum dikonfigurasi di file secrets.toml")
        return

    # 2. Setup Memori Sesi
    if "chat_memory" not in st.session_state:
        st.session_state.chat_memory = []

    # =========================================================
    # 3. KOTAK PERCAKAPAN SCROLLABLE (Tinggi Tetap 400px)
    # =========================================================
    chat_box = st.container(height=400)
    
    # Render histori yang sudah ada ke dalam kotak tersebut
    with chat_box:
        if not st.session_state.chat_memory:
            st.info("Ketik pertanyaan Anda di bawah untuk memulai analisis data.")
            
        for msg in st.session_state.chat_memory:
            if msg["role"] == "assistant":
                avatar_img = "assets/Melati_icon.png"
            else:
                avatar_img = None

            with st.chat_message(msg["role"], avatar=avatar_img):
                st.markdown(msg["content"])

    # =========================================================
    # 4. KOTAK INPUT (Inline, diam di tempat)
    # =========================================================
    # Menggunakan form agar teks otomatis terhapus (clear) setelah dikirim
    with st.form(key=f"chat_form_{nama_halaman}", clear_on_submit=True):
        col_input, col_btn = st.columns([9, 1]) # Proporsi 90% input, 10% tombol
        
        with col_input:
            user_input = st.text_input(
                "Prompt AI", 
                placeholder="Contoh: Vendor mana yang nilai PO-nya paling besar?", 
                label_visibility="collapsed" # Menyembunyikan label agar bersih
            )
        with col_btn:
            submit_btn = st.form_submit_button("Kirim", icon=":material/send:")

    # =========================================================
    # 5. LOGIKA EKSEKUSI API
    # =========================================================
    if submit_btn and user_input:
        
        # Simpan pertanyaan user ke memori
        st.session_state.chat_memory.append({"role": "user", "content": user_input})
        
        # Tampilkan langsung ke dalam kotak percakapan yang di-scroll tadi
        with chat_box:
            with st.chat_message("user"):
                st.markdown(user_input)
                
            # Render animasi loading & balasan AI
            with st.chat_message("assistant", avatar="assets/Melati_icon.png"):
                with st.spinner("Tunggu, Melati sedang menganalisis data..."):
                    try:
                        # -------------------------------------------------------------
                        # PETA SISTEM (Nama Chart + Caption Singkat)
                        # -------------------------------------------------------------
                        peta_sistem = """
                        INFORMASI STRUKTUR HALAMAN APLIKASI (PETA SISTEM):
                        Kamu mengetahui seluruh daftar halaman dan chart di sistem ini beserta deskripsi singkatnya.
                        
                        KATEGORI 1: PR-PO SAP
                        1. Halaman Dashboard Monitoring SAP: 
                            - Menampilkan ringkasan KPI utama:
                                - "Total PR": Jumlah Purchase Requisition unik dalam periode filter.
                                - "Total PO": Jumlah baris Purchase Order dalam periode filter.
                                - "Produktivitas PR-PO": Persentase item PR yang berhasil dikonversi menjadi PO.
                                - "Total Savings": Selisih OE dengan realisasi PO.
                                - "Total Estimasi PR (OE)": Total nilai OE dari semua PR.
                                - "Pengelolaan Anggaran Operasional": Belum ada info lebih lanjut.
                                - "Sinergi PI Group": Belum ada info lebih lanjut.
                                - "Kecepatan Proses PO": Rata-rata hari dari 1St Full Release PR hingga PO diterbitkan (Date Ordered).
                                - "% Pengiriman Barang (GR/PO)": Persentase PO yang sudah diterima barangnya.
                                - "Ketepatan Pengiriman Barang": Persentase PO diterima tepat waktu dari total yang sudah dikirim.
                                - "Pemenuhan SLA OTOBOS": Belum ada info lebih lanjut.
                                - "Efisiensi Pengadaan (PO/OE)": Rata-rata persentase penghematan dari nilai OE per item PO.
                                - "Pemenuhan Izin Impor": Belum ada info lebih lanjut.
                                - "Pemenuhan SLA Pembebasan Barang": Belum ada info lebih lanjut.
                            - Menampilkan chart "PR Status by Department": Stacked bar chart jumlah PR per departemen, dibedakan antara PR yang sudah memiliki PO dan yang belum.
                            - Menampilkan chart "Top 10 Vendors by PO Value": Bar chart horizontal 10 vendor dengan total nilai PO terbesar.
                            - Menampilkan chart "PR-PO Creation Trend": Line chart jumlah PR dan PO yang dibuat per bulan.
                            - Menampilkan chart "Lead Time Distribution": Pie chart distribusi PO berdasarkan rentang waktu proses (dari 1St Full Release PR hingga Date Ordered PO terbit).
                            - Menampilkan tabel "Top 10 PR Without PO (Pending)": Tabel 10 PR tertua yang belum diproses menjadi PO. 
                            - Menampilkan chart "Delivery Performance": Pie chart status pengiriman PO (tepat waktu vs terlambat vs pending).
                            - Menampilkan chart "Material Category Value": Bar chart total nilai PO per kategori ABC material.
                        2. Detailed PR-PO SAP Data: Menampilkan tabel "Data mentah (raw data) SAP secara lengkap yang bisa di-filter".
                        3. Evaluasi Harga Barang:
                            - Menampilkan ringkasan KPI utama:
                                - "Total Material Unik": Jumlah kode material berbeda yang tercatat dalam PO di periode filter.
                                - "Total OE": Total nilai anggaran estimasi untuk semua material yang sudah masuk PO.
                                - "Total Realisasi PO": Total nilai aktual yang dibayarkan dalam Purchase Order.
                                - "Selisih OE vs Realisasi": Perbedaan antara total OE (anggaran) dan total realisasi PO.
                                - "Item PO Melebihi OE": Jumlah item PO yang nilai realisasinya melebihi OE.
                                - "Item PO Di Bawah / Sesuai OE": Jumlah item PO yang nilai realisasinya sama atau lebih murah dari OE.
                            - Menampilkan chart "OE vs Realisasi Harga PO (per Material)": Scatter chart perbandingan nilai estimasi vs realisasi PO per material.
                            - Menampilkan chart "Top 10 Material: Overspend Terbesar": Bar chart 10 material dengan selisih (realisasi - OE) terbesar.
                            - Menampilkan chart "Variasi Harga Antar Vendor (Top 10 Material)": Perbandingan harga satuan dari vendor berbeda untuk material yang sama.
                            - Menampilkan chart "Tren Harga Historis per Material": Line chart pergerakan harga satuan PO per bulan. Berguna untuk mendeteksi kenaikan harga yang tidak wajar dan melihat konsistensi vendor.
                            - Menampilkan chart "Perbandingan Vendor": Tabel ini menampilkan metrik kinerja vendor untuk material yang sedang dipilih, membantu Anda memilih vendor terbaik berdasarkan tiga pilar utama.
                            - Menampilkan tabel "Detail Evaluasi Harga per Material": Ringkasan perbandingan OE vs realisasi per material.
                        4. Kinerja Purchasing Group: 
                            - Menampilkan Tab Overview per Purchasing Group:
                                - Menampilkan Tabel "Ringkasan per Purchasing Group"
                                - Menampilkan chart "Perbandingan Nilai OE vs Realisasi PO": Grouped bar chart perbandingkan estimasi anggaran (OE) vs realisasi PO per Purchasing Group.
                                - Menampilkan chart "% Efisiensi per Purchasing Group": Bar chart horizontal persentase penghematan yang dicapai tiap Purchasing Group.
                                - Menampilkan chart "Rata-rata Lead Time per Purchasing Group": Bar chart horizontal rata-rata waktu proses PR→PO per Purchasing Group.
                                - Menampilkan chart "% Konversi PR → PO per Purchasing Group": Bar chart horizontal persentase PR yang berhasil dikonversi menjadi PO.
                            - Menampilkan Tab Breakdown Metode Tender & Kecepatan
                                - Menampilkan informasi "Avg Lead Time": Rata-rata waktu proses dari PR dibuat hingga PO diterbitkan, untuk semua Purchasing Group.
                                - Menampilkan informasi "Median Lead Time": Nilai tengah dari seluruh distribusi lead time PO dalam periode filter.
                                - Menampilkan informasi "Rentang Lead Time": Selisih antara lead time terpendek dan terpanjang dalam periode filter.
                                - Menampilkan informasi "On-Time (≤55 Hari)": Jumlah PO yang berhasil diproses dalam batas SLA 55 hari.
                                - Menampilkan informasi "Terlambat (>55 Hari)": Jumlah PO yang melebihi batas SLA 55 hari.
                                - Menampilkan chart "Kontrak vs Non-Kontrak per Purchasing Group": Stacked bar chart komposisi nilai realisasi berdasarkan jenis tender per Purchasing Group.
                                - Menampilkan chart "Distribusi Turn Around per Purchasing Group": Komposisi item PO berdasarkan kategori Turn Around (TA vs non-TA).
                                - Menampilkan tabel "Detail per Purchasing Group × Turn Around"
                                - Menampilkan chart "Lead Time: Kontrak vs Non-Kontrak per Purchasing Group": Grouped bar chart rata-rata lead time per jenis tender per Purchasing Group.
                                - Menampilkan chart "Tren Lead Time per Bulan": Line chart rata-rata kecepatan proses per bulan, dibedakan antara Tender Normal dan PR-PO Kontrak.
                                - Menampilkan tabel "Ringkasan Kecepatan per Purchasing Group × Jenis Tender"
                        5. Halaman Alert:
                            - Menampilkan tabel "PR Pending Mendekati Kadaluarsa (> 30 Hari)": Menampilkan PR yang belum diproses menjadi PO dan sudah menunggu lebih dari 30 hari sejak dibuat.
                            - Menampilkan tabel "PO Overdue (Melewati Delivery Date)": Menampilkan PO yang tanggal delivery-nya sudah lewat namun barang belum diterima semua (Delivery Completed belum X).
                            - Menampilkan chart "Rekap Aging PO (Belum Dikirim)": Bar chart jumlah PO yang belum dikirim dikelompokkan per rentang umur.
                        
                        KATEGORI 2: SIPS
                        6. Dashboard Monitoring SIPS:
                            - Menampilkan ringkasan KPI utama:
                                - "Total PR": Jumlah Purchase Requisition dalam periode filter (semua status).
                                - "Total PO": Jumlah PR yang sudah memiliki PO, yaitu yang berstatus Closed atau Proses PO.
                                - "PO/PR": Persentase PR yang sudah dikonversi menjadi PO.
                                - "Rata-rata PR-PO": Rata-rata jumlah hari semua PR-PO dari Tanggal Disposisi Buyer hingga Tanggal PO per karyawan.
                                - "SLA On Time": Jumlah PO yang diselesaikan dalam batas SLA standar.
                                - "% On Time": Persentase PO yang diselesaikan tepat waktu.
                                - "OE Proses PO": Total nilai Owner's Estimate (anggaran) untuk PR yang sudah berstatus Proses PO.
                                - "OE Closed": Total nilai Owner's Estimate untuk PR yang sudah berstatus Closed.
                                - "Total OE": Gabungan OE untuk status Proses PO dan Closed.
                                - "PO Proses PO": Total nilai realisasi PO untuk yang berstatus Proses PO.
                                - "PO Closed": Total nilai realisasi PO untuk yang berstatus Closed.
                                - "Total PO (Nilai)": Gabungan realisasi nilai PO untuk status Proses PO dan Closed.
                                - "Efisiensi %": Persentase penghematan dari selisih OE dengan realisasi nilai PO.
                                - "Efisiensi Rp": Nominal penghematan dalam Rupiah.
                                - "% On Budget": Persentase PO yang nilai realisasinya tidak melebihi nilai MR/SR (kolom Z ≤ 100%).
                            - Menampilkan chart "Pipeline & Trend PR-PO SIPS": Line chart jumlah PR dan PO yang dibuat per bulan.
                            - Menampilkan chart "Distribusi Status PR SIPS": Pie chart persentase jumlah dokumen berdasarkan status akhirnya.
                            - Menampilkan chart "Performa SLA per Karyawan": Bar chart persentase pencapaian SLA tepat waktu untuk setiap karyawan.
                            - Menampilkan chart "Distribusi Waktu PR → PO": Histogram persebaran jumlah PR berdasarkan lama proses pembuatannya (dalam satuan hari).
                            - Menampilkan chart "Beban Kerja per Karyawan": Bar chart ini menghitung frekuensi dokumen PR yang ditangani oleh masing-masing karyawan, serta seberapa banyak yang sudah berhasil dikonversi menjadi PO.
                            - Menampilkan chart "Proporsi PO Kontrak vs Non-Kontrak": Stacked bar chart ini menunjukkan berapa banyak item PO yang dibuat menggunakan kontrak payung (Outline Agreement) dibandingkan yang tidak.
                            - Menampilkan chart "Perbandingan Nilai OE vs PO per Karyawan": Grouped bar chart yang membandingkan total nilai anggaran (OE) dengan realisasi aktual (PO) untuk setiap karyawan.
                        7. Detailed SIPS Data: Menampilkan tabel "Data mentah dokumen SIPS".
                        8. Analisis Waktu Proses SIPS:
                            - Menampilkan Ringkasan Waktu:
                                - "Rata-rata PR-PO": Rata-rata jumlah hari PR-PO dengan Status Proses PO dan Closed dari Tanggal Disposisi Buyer hingga Tanggal PO per karyawan.
                                - "Rata-rata Realisasi SLA": Rata-rata waktu proses pengadaan dari Disposisi Buyer ke Tanggal PO dalam hari kerja.
                                - "Waktu Pra-Disposisi": Rata-rata waktu dari PR dibuat (Requisition Date) hingga PR diterima buyer (Tanggal Disposisi Buyer).
                                - "Rata-rata End-to-End": Total waktu dari PR pertama kali dibuat (Requisition Date) hingga PO terbit (Tanggal PO), mencakup semua tahapan proses.
                                - "Rata-rata SLA Headroom": Sisa waktu rata-rata antara target SLA dengan waktu realisasi aktual.
                                - "% On Time SLA": Persentase PR yang berhasil diselesaikan dalam batas Standard SLA.
                            - Menampilkan chart "Dekomposisi Waktu per Nama": Stacked bar chart Proporsi Realisasi SLA vs Selisih Waktu PR-PO per karyawan.
                            - Menampilkan chart "Standard SLA per jenis pengadaan": Bar Chart % On Time dan rata-rata Realisasi SLA per Standard SLA dan jenis kontrak.
                            - Menampilkan chart "SLA Headroom per Nama": Horizontal Bar Chart Sisa waktu rata-rata (Standard SLA minus Realisasi SLA) per karyawan.
                            - Menampilkan chart "Tren Waktu per Bulan": Combo Chart Perubahan kecepatan proses dari bulan ke bulan.
                            - Menampilkan chart "Distribusi Waktu": Bar Chart Sebaran PR-PO dan Realisasi SLA untuk mendeteksi outlier.
                            - Menampilkan chart "Waktu per Prioritas": Bar Chart Rata-rata PR-PO & Realisasi SLA per Prioritas dan % On Time per Prioritas.
                            - Menampilkan chart "Waktu Realisasi SLA per Purchasing Group": Bar Chart Perbandingan rata-rata waktu penyelesaian berdasarkan Purchasing Group.
                        """

                        # Rakit Prompt Rahasia
                        system_prompt = f"""
                        Kamu adalah asisten AI bernama Melati, seorang analis data perempuan yang ceria, sangat teliti, dan bersikap layaknya "detektif" andal yang sedang menyelidiki data sistem perusahaan.
                        
                        Tugas dan Aturan Ketat Melati:
                        1. IDENTITAS & GAYA BAHASA: Namamu adalah Melati, detektif data pengadaan. HANYA perkenalkan dirimu secara penuh jika user SECARA EKSPLISIT bertanya "siapa kamu", "kamu siapa", "perkenalkan dirimu", atau sejenisnya. Jika user hanya menyapa ("halo", "hai", dll.) atau langsung mengajukan pertanyaan data, JANGAN memperkenalkan diri, langsung jawab pertanyaannya saja dengan gaya yang ceria dan to the point. Gunakan gaya bahasa yang ceria, ramah, sedikit playful (gunakan kata "aku" dan "kamu"), tapi tetap SANGAT OBJEKTIF dan tajam saat menganalisis angka.
                        2. FAKTUAL & OBJEKTIF: Jawab HANYA berdasarkan data di bawah. JIKA DATA TIDAK ADA, katakan dengan nada detektif: "Hmm, sepertinya jejak data itu tidak kutemukan di layar saat ini 🔍."
                        3. NO HALLUCINATION: Sebagai detektif, kamu pantang mengarang bukti! JANGAN PERNAH mengarang angka, nama vendor, atau metrik yang tidak ada di data.
                        4. ATURAN PENOLAKAN RUMUS/KALKULASI: Kamu HANYA tahu deskripsi singkat chart. JIKA user bertanya tentang RUMUS, FORMULA, CARA MENGHITUNG, atau KALKULASI spesifik dari suatu chart, kamu WAJIB menjawab dengan template kalimat ini (sesuaikan nama halaman dan chart-nya):
                           "Maaf, Melati masih belum bisa memperoleh informasi tersebut. Kamu bisa mengetahui informasinya dengan cara pergi ke Halaman [Judul Halaman], di chart/tabel [Nama Chart/Nama Tabel], lalu klik tombol 'Show Formula' berbentuk mata 😭."
                        5. BATASAN DOMAIN: Tolak dengan sopan hal di luar pengadaan, dashboard, atau data yang diberikan.
                        6. FORMAT: Berikan analisis terstruktur, tebalkan angka penting, gunakan bullet points, dan sedikit emoji.
                        7. ATURAN FILTER LINTAS SISTEM (PENTING!): Pada 'BUKTI DATA' di bawah, tertera informasi 'Halaman aktif' saat ini. JIKA user bertanya tentang data/angka dari sistem yang BERBEDA dengan halaman aktif saat ini (misalnya: kita sedang di halaman SIPS, tapi user menanyakan data SAP, atau sebaliknya), kamu WAJIB menyebutkan "Kondisi Filter" yang sedang berlaku pada data tersebut sebelum memberikan jawabannya. Ambil informasi filter ini dari teks di bawah tulisan [SAP] FILTER AKTIF atau [SIPS] FILTER AKTIF.
                        
                        {peta_sistem}

                        Berikut adalah BUKTI-BUKTI DATA yang sedang tayang di layar saat ini:
                        --- MULAI BUKTI DATA ---
                        {konteks_data_teks}
                        --- AKHIR BUKTI DATA ---
                        
                        Pertanyaan dari User: {user_input}
                        """
                        
                        # Eksekusi API Gemini
                        response = client.models.generate_content(
                            model="gemini-3-flash-preview",
                            contents=system_prompt
                        )
                        
                        # Tampilkan hasil
                        st.markdown(response.text)
                        
                        # Simpan ke memori agar tidak hilang saat filter diubah
                        st.session_state.chat_memory.append({"role": "assistant", "content": response.text})
                    
                    except Exception as e:
                        st.error(f"Terjadi kesalahan saat menghubungi API: {e}")