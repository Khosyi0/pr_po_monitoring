"""
v_changelog.py - Halaman Log Perubahan
"""
import streamlit as st
import pandas as pd

def render(**kwargs):
    """Render halaman changelog. Tidak butuh filter_conditions."""
    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:40px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="35" height="35" fill="currentColor" class="bi bi-journal-code" viewBox="0 0 16 16" style="margin-bottom: 8px; margin-right: 12px;">
                <path fill-rule="evenodd" d="M8.646 5.646a.5.5 0 0 1 .708 0l2 2a.5.5 0 0 1 0 .708l-2 2a.5.5 0 0 1-.708-.708L10.293 8 8.646 6.354a.5.5 0 1 1 .708-.708zm-1.292 0a.5.5 0 0 0-.708 0l-2 2a.5.5 0 0 0 0 .708l2 2a.5.5 0 0 0 .708-.708L5.707 8l1.647-1.646a.5.5 0 0 0 0-.708z"/>
                <path d="M3 0h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2v-1h1v1a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1H3a1 1 0 0 0-1 1v1H1V2a2 2 0 0 1 2-2z"/>
                <path d="M1 5v-.5a.5.5 0 0 1 1 0V5h.5a.5.5 0 0 1 0 1h-2a.5.5 0 0 1 0-1H1zm0 3v-.5a.5.5 0 0 1 1 0V8h.5a.5.5 0 0 1 0 1h-2a.5.5 0 0 1 0-1H1zm0 3v-.5a.5.5 0 0 1 1 0v.5h.5a.5.5 0 0 1 0 1h-2a.5.5 0 0 1 0-1H1z"/>
            </svg>
            System Changelog
        </h1>
    """, unsafe_allow_html=True)
    st.markdown("Catatan pembaruan, perbaikan bug, dan penambahan fitur pada dashboard PR-PO Monitoring.")
    st.markdown("---")

    changelog_data = [
         {"Tanggal": "26 Mar 2026", "Versi": "v1.8.2", "Perubahan": """
    - Menambahkan chart Ringkasan Kecpeatan per Purchasing Group x Jenis Tender di halaman Analisis Waktu Proses SIPS
    - Menambahkan Halaman Alert SIPS:
        - PR Pending Mendekati Kadaluarsa (> 30 Hari)
        - Rekap Aging PR Pending (Open)
        - Beban Pending per Karyawan
        - Monitoring Status PR SIPS
    - Menambahkan template halaman Executive Summary
    - Mengubah tanggal filter jadi maksimal sesuai dengan data diupdate
    - Menambahkan beberapa chart di Halaman Alert SAP
        - List PO per Status
        - Grafik PO Terlambat
        - PO Outstanding (Belum GR, Belum Jatuh Tempo)"""},
        {"Tanggal": "13 Mar 2026", "Versi": "v1.8.1", "Perubahan": """
    - Menambahkan chart Top 10 Material: Efisiensi Terbesar di halaman Evaluasi Harga Barang
    - Menambahkan chart Ranking Vendor Keseluruhan di halaman Evaluasi Harga Barang
    - Menambahkan fitur tombol ke halaman atas ketika scroll terlalu bawah
    - Menambahkan fitur sidebar bisa menjadi header
    - Menambahkan firut konfirmasi ketika akan logout"""},
        {"Tanggal": "13 Mar 2026", "Versi": "v1.8", "Perubahan": """
    - Memperbarui perhitungan Produktivitas PR-PO pada halaman Dashboard Monitoring SAP
    - Menambahkan halaman Login demi keamanan data
    - Menambahkan icon/logo untuk sistem
    - Memperbarui logika Peta Sistem untuk Melati"""},
        {"Tanggal": "12 Mar 2026", "Versi": "v1.7.6", "Perubahan": """
    - Validasi isi data halaman Analisis Waktu Proses SIPS
        - Fix beberapa query agar sesuai dengan data asli dari excel SAP
    - Mengubah beberapa elemen di halaman Dashboard Monitoring SAP
    - Menambahkan chart Monitoring PO Status pada Halaman Alert
        - Fix query
            - Total PR
            - Kecepatan Proses PO
            - % Pengiriman Barang
            - Ketepatan Pengiriman Barang
        - Penambahan filter khusus pada chart Top 10 Vendors by PO Value
        - Mengubah tanggal yang muncul pada chart PR-PO Creation Trend"""},
        {"Tanggal": "11 Mar 2026", "Versi": "v1.7.5", "Perubahan": """
    - Validasi isi data halaman Alert
        - Fix beberapa query agar sesuai dengan data asli dari excel SAP
    - Validasi isi data halaman Dashboard Monitoring SIPS
        - Fix beberapa query agar sesuai dengan data asli dari excel SIPS
        - Fix format angka rupiah"""},
        {"Tanggal": "10 Mar 2026", "Versi": "v1.7.4", "Perubahan": """
    - Validasi isi data halaman Kinerja Purchasing Group
        - Fix beberapa query agar sesuai dengan data asli dari excel SAP
        - Merge tab \"Breakdown Metode per Tender\" dan \"Kecepatan Proses\"
        - Menghapus beberapa chart yang sudah ada di halaman lain
        - Fix beberapa query agar sesuai dengan data aslid dari excel SAP"""},
        {"Tanggal": "9 Mar 2026", "Versi": "v1.7.3", "Perubahan": """
    - Validasi isi data halaman Evaluasi Harga Barang
        - Fix beberapa query agar sesuai dengan data asli dari excel SAP
        - Memperbarui UI untuk KPI"""},
        {"Tanggal": "5 Mar 2026", "Versi": "v1.7.2", "Perubahan": """
    - Validasi isi data halaman Dashboard Monitoring SAP
        - Fix beberapa query agar sesuai dengan data asli dari excel SAP
        - Mengubah beberapa chart agar informasi lebih mudah dipahami"""},
        {"Tanggal": "3 Mar 2026", "Versi": "v1.7.1", "Perubahan": """
    - Update UI halaman Evaluasi Harga Barang, Dashboard Monitoring SIPS, dan Analisis Waktu Proses SIPS ketika tidak ada data untuk filter yang dipilih
    - Memperbaiki bug infomasi "0" dan informasi detail per chart di halaman Analisis Waktu Proses SIPS
    - Menambahkan kamus tentang struktur sistem ke Melati"""},
        {"Tanggal": "2 Mar 2026", "Versi": "v1.7", "Perubahan": """
    - Optimisasi Melati agar dapat membaca keseluruhan data, tidak hanya data yang tampil di halaman tersebut
    - Menambahkan Melati ke halaman Detailed PR-PO Data dan Detailed SIPS Data
    - Menambahkan filter "Bagian" (ALPATA, BARUM, BB/BD/BP) pada bagian SIPS
    - Merubah query pada "Nama" menjadi "NIK" untuk bagian SIPS agar lebih akurat dan konsisten dengan data yang ada
    - Update filter default untuk tanggal menjadi berawal dari tanggal 1 Januari tahun saat ini
    - Update halaman Evaluasi Harga Barang
        - Menambahkan chart Perbandingan Vendor: Harga · Kecepatan · Reliabilitas
        - Perubahan chart Tren Harga Historis per Material
        - Filter material menjadi satu diantara tiga chart (Variasi Harga Antar Vendor (Top 10 Material), Tren Harga Historis per Material, dan Perbandingan Vendor: Harga · Kecepatan · Reliabilitas)
    - Update halaman Analisis Waktu Proses SIPS
        - Perubahan isi chart Dekomposisi Waktu per Nama menjadi Proporsi Realisasi SLA vs Selisih Waktu PR-PO per karyawan
        - Menambahkan chart Waktu Realisasi SLA per Purchasing Group
        - Mengubah chart Distribusi End-to-End (Req Date ke Tgl PO) menjadi Distribusi Realisasi SLA (hari kerja)
    - Update halaman Dashboard Monitoring SIPS
        - Menambahkan chart Proporsi PO Kontrak vs Non-Kontrak per Karyawan
        - Menambahkan chart Beban Kerja (Volume Dokumen) per Karyawan"""},
        {"Tanggal": "27 Feb 2026", "Versi": "v1.6", "Perubahan": """
    - Menambahkan info detail pada masing-masing bagian pada Ringkasan Waktu di halaman Analisis Waktu Proses SIPS
    - Menambahkan model LLM bernama untuk memberikan insight otomatis berdasarkan data yang tampil di halaman Dashboard Monitoring SIPS
        - Model LLM menggunakan model gemini-3-flash-preview dari Google GenAI dengan prompt rahasia yang dirancang khusus untuk memberikan insight yang tajam, faktual, dan objektif berdasarkan data
        - Data perusahaan tidak akan menjadi dataset pelatihan model Gemini karena API KEY yang digunakan jenisnya paid (estimasi Rp 20.000 per bulan)
        - Model LLM memiliki kepribadian bernama Melati (Monitoring, Evaluasi, Laporan Terintegrasi) yang bersikap ceria, ramah, sedikit playful, tapi tetap sangat objektif dan tajam saat menganalisis data
        - Penggunaan model LLM ini masih dalam tahap awal (proof of concept) dan akan terus disempurnakan"""},
        {"Tanggal": "26 Feb 2026", "Versi": "v1.5.1", "Perubahan": """
    - Menambahkan info penting di halaman Dashboard Monitoring SIPS
        - Total PR
        - Total PO
        - PO/PR
        - Rata-rata PR-PO
        - SLA On Time
        - % On Time
        - OE Proses PO
        - OE Closed
        - Total OE
        - PO Proses PO
        - PO Closed
        - Total PO
        - Efisiensi %
        - Efisiensi Rp
        - % On Budget
    - Menambahkan beberapa chart di halaman Dashboard Monitoring SIPS
        - Pipeline & Trend PR-PO SIPS
        - Distribusi Status PR SIPS
        - Performa SLA per Karyawan
        - Distribusi Waktu PR → PO
        - Perbandingan Nilai OE vs PO per Karyawan
    - Menambahkan filter pada halaman Dashboard Monitoring SIPS
        - Karyawan
        - Date Range
    - Menambahkan halaman Detailed SIPS Data
    - Menambahkan halaman Analisis Waktu Proses SIPS
        - Menambahkan Ringkasan Waktu
            - Rata-rata PR-PO
            - Rata-rata Realisasi SLA
            - Waktu Pra-Disposisi
            - Rata-rata End-to-End
            - Rata-rata SLA Headroom
            - % On Time SLA
        - Menambahkan Dekomposisi Waktu per Nama
        - Menambahkan Pemenuhan SLA per Jenis Pengadaan
        - Menambahkan SLA Headroom per Nama
        - Menambahkan Tren Waktu per Bulan
        - Menambahkan Distribusi Waktu
        - Menambahkan Waktu per Prioritas
    - Fix format angka Indonesia di semua halaman"""},
        {"Tanggal": "25 Feb 2026", "Versi": "v1.5", "Perubahan": """
    - Menambahkan info KPI penting di halaman Dashboard Monitoring
        - Produktivitas PR-PO
        - Pengelolaan Anggaran Operasional
        - Sinergi PI Group
        - Kecepatan Proses PO
        - % Pengiriman Barang
        - Ketepatan Pengiriman Barang
        - Pemenuhan SLA OTOBOS
        - Efisiensi Pengadaan
        - Pemenuhan Izin Impor
        - Pemenuhan SLA Pembebasan Barang
    - Perbaikan filter Department dan Purchasing Group
    - Menambahkan kerangka halaman dashboard untuk data dari SIPS"""},
        {"Tanggal": "24 Feb 2026", "Versi": "v1.4.1", "Perubahan": """
    - Fix bug navigasi halaman
        - Menggunakan navigasi bawaan dengan custom CSS untuk menggantikan 'streamlit-option-menu' yang menyebabkan bug navigasi
    - Menambahkan 'Show Formula' di setiap info penting di atas pada semua halaman
    - Update halaman Kinerja Purchasing Group
        - Fix bug 'Show Formula' dengan navigasi antar tab di halaman Kinerja Purchasing Group
        - Menghapus "Rata-rata Lead Time" di tab 'Kecepatan Proses'karena duplicate dengan info di atas
        - Mengecilkan font info agar value "Total OE" dan "Efisiensi" dapat terbaca
        - Mengubah chart Distribusi Lead Time Overall dari Bar Chart menjadi Pie Chart
    - Menambahkan caption singkat untuk setiap chart di semua halaman"""},
        {"Tanggal": "23 Feb 2026", "Versi": "v1.4", "Perubahan": """
    - Refactor: dashboard dipecah menjadi multi-file (app.py, config_db.py, utils.py, views/)
    - Menambahkan info detail dari masing-masing chart di semua halaman"""},
        {"Tanggal": "20 Feb 2026", "Versi": "v1.3", "Perubahan": """- Menambahkan beberapa info di halaman Kinerja Purchasing Group
    - Total Item PR
    - Total Item PO
    - Total OE
    - Efisiensi
    - Avg Lead Time
    - Tab Overview per Purchasing Group
        - Tabel Ringkasan per Purchasing Group
        - Perbandingan Nilai OE vs Realisasi PO
        - % Efisiensi per Purchasing Group
        - Rata-rata Lead Time per Purchasing Group
        - % Konversi PR → PO per Purchasing Group
    - Tab Breakdown per Metode Tender
        - Kontrak vs Non-Kontrak per Purchasing Group
        - Distribusi Turn Around per Purchasing Group
            - Distribusi Jumlah Item per Turn Around
            - Lead Time Rata-rata per Kategori Turn Around
        - Lead Time: Kontrak vs Non-Kontrak
        - Detail per PG × Turn Around
    - Tab Kecepatan Proses
        - Rata-rata Lead Time
        - Median Lead Time
        - Rentang Lead Time
        - On-Time (<=55 Hari)
        - Terlambat (>55 Hari)
        - Distribusi Lead Time Overall
        - Lead Time: Tender Normal vs PR-PO Kontrak
        - Tren Lead Time per Bulan
        - Ringkasan Kecepatan per PG x Jenis Tender"""},
        {"Tanggal": "19 Feb 2026", "Versi": "v1.2.1", "Perubahan": """
    - Memperbarui UI dengan ikon dan warna yang cocok untuk tema gelap dan terang
    - Menambahkan halaman Kinerja Purchasing Group
    - Menambahkan Changelog"""},
        {"Tanggal": "18 Feb 2026", "Versi": "v1.2", "Perubahan": """
    - Optimisasi Query
    - Deployment Dashboard Website
    - Menambahkan halaman Evaluasi Harga Barang
        - Total Material Unik
        - Total OE
        - Total Realisasi PO
        - Selisih OE vs Realisasi
        - Item PO Melebihi OE
        - Item PO Di Bawah / Sesuai OE
        - OE vs Realisasi Harga PO (per Material)
        - Top 10 Material: Overspend Terbesar
        - Variasi Harga Antar Vendor (Top 10 Material)
        - Tren Harga Historis per Material
        - Detail Evaluasi Harga per Material"""},
        {"Tanggal": "17 Feb 2026", "Versi": "v1.13", "Perubahan": """
    - Update Struktur Database
    - Persiapan Deployment Website
        - Konfigurasi neon.tech untuk hosting database
        - Konfigurasi streamlit cloud untuk hosting aplikasi
        - Konfigurasi koneksi database PostgreSQL dengan neon.tech dan Secrets di streamlit cloud"""},
        {"Tanggal": "13 Feb 2026", "Versi": "v1.1.2", "Perubahan": """- Menambahkan halaman alert
    - PR Pending Mendekati Kadaluarsa (> 30 Hari)
    - PO Overdue (Melewati Delivery Date)
    - Rekap Aging PO (Belum Dikirim)"""},
        {"Tanggal": "12 Feb 2026", "Versi": "v1.1.1", "Perubahan": """
    - Perbaikan logika select Total PR dan Total PO
    - Menambahkan halaman Detailed PR-PO Data"""},
        {"Tanggal": "11 Feb 2026", "Versi": "v1.1", "Perubahan": """- Menambahkan garis besar dari dashboard
    - Menambahkan Key Performance Indicators
        - Total PR
        - Total PO
        - Total Estimasi PR
        - Total Savings
    - Menambahkan PR Status by Department
    - Menambahkan Top 10 Vendors by PO Value
    - Menambahkan PR-PO Creation Trend
    - Menambahkan Lead Time Distribution
    - Menambahkan Additional Insights
        - Top 10 PR Without PO (Pending)
        - Delivery Performance
        - Material Category Value"""},
        {"Tanggal": "10 Feb 2026", "Versi": "v1.0", "Perubahan": """
    - Rilis awal dashboard monitoring (lokal)
    - Penggunaan streamlit untuk visualisasi data PR-PO
    - Koneksi ke database PostgreSQL untuk mengambil data PR-PO"""},
    ]

    for item in changelog_data:
        with st.expander(f"**{item['Versi']}** - {item['Tanggal']}", expanded=(item['Versi'] in ["v1.8.2"])):
            st.markdown(item["Perubahan"])