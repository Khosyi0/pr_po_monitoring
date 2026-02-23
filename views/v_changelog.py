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
        {"Tanggal": "23 Feb 2026", "Versi": "v1.8", "Perubahan": """
    - Refactor: dashboard dipecah menjadi multi-file (app.py, config_db.py, utils.py, views/)
    - Menambahkan info detail dari masing-masing chart
    - Menambahkan detail dari masing-masing chart"""},
        {"Tanggal": "20 Feb 2026", "Versi": "v1.7", "Perubahan": """- Menambahkan beberapa info di halaman Kinerja Purchasing Group
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
        {"Tanggal": "19 Feb 2026", "Versi": "v1.6", "Perubahan": """
    - Update UI
    - Menambahkan halaman Kinerja Purchasing Group
    - Menambahkan Changelog"""},
        {"Tanggal": "18 Feb 2026", "Versi": "v1.5", "Perubahan": """
    - Optimisasi Query
    - Deployment Website
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
        {"Tanggal": "17 Feb 2026", "Versi": "v1.4", "Perubahan": "Update Struktur Database dan Persiapan Deployment Website"},
        {"Tanggal": "13 Feb 2026", "Versi": "v1.3", "Perubahan": """- Menambahkan halaman alert
    - PR Pending Mendekati Kadaluarsa (> 30 Hari)
    - PO Overdue (Melewati Delivery Date)
    - Rekap Aging PO (Belum Dikirim)"""},
        {"Tanggal": "12 Feb 2026", "Versi": "v1.2", "Perubahan": """
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
        
        {"Tanggal": "10 Feb 2026", "Versi": "v1.0", "Perubahan": "Rilis awal dashboard monitoring"},
    ]

    for item in changelog_data:
        with st.expander(f"**{item['Versi']}** - {item['Tanggal']}", expanded=(item['Versi'] in ["v1.8"])):
            st.markdown(item["Perubahan"])