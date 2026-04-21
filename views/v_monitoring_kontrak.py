"""
v_monitoring_kontrak.py - Halaman Monitoring Kontrak (Placeholder)
Memantau jumlah kontrak, validity date, nilai kontrak, dan realisasi kontrak.
Sumber data: SAP ME 3N (Download List Kontrak)
"""

import streamlit as st
from datetime import datetime


def render(**kwargs):

    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:55px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="45" height="45" fill="currentColor"
                 viewBox="0 0 16 16" style="margin-bottom: 8px; margin-right: 12px;">
                <path d="M9.293 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4.707A1 1
                         0 0 0 13.707 4L10 .293A1 1 0 0 0 9.293 0M9.5 3.5v-2l3 3h-2a1 1 0 0
                         1-1-1M4.5 9a.5.5 0 0 1 0-1h7a.5.5 0 0 1 0 1zM4 10.5a.5.5 0 0 1
                         .5-.5h7a.5.5 0 0 1 0 1h-7a.5.5 0 0 1-.5-.5m.5 2.5a.5.5 0 0 1 0-1h4
                         a.5.5 0 0 1 0 1z"/>
            </svg>
            Monitoring Kontrak
        </h1>
    """, unsafe_allow_html=True)

    st.markdown(
        "<p style='font-size:16px; color:gray; margin-top:-8px;'>"
        "Monitoring jumlah kontrak, validity date, nilai kontrak, dan realisasi kontrak.</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # == Info Placeholder ======================================================
    st.info(
        "🚧 **Halaman ini sedang dalam tahap perencanaan.**\n\n"
        "Halaman ini akan memantau seluruh kontrak pengadaan yang aktif maupun yang akan "
        "segera berakhir, termasuk nilai kontrak dan realisasi pembelian terhadap kontrak tersebut.\n\n"
        "**Fitur yang direncanakan:**\n"
        "- List semua kontrak aktif beserta validity date\n"
        "- Alert kontrak yang akan berakhir dalam 30/60/90 hari ke depan\n"
        "- Nilai kontrak vs realisasi pembelian (seberapa banyak kontrak sudah terpakai)\n"
        "- Filter berdasarkan vendor, Purchasing Group, dan status kontrak\n"
        "- Ringkasan KPI: total kontrak aktif, kontrak hampir expired, % utilisasi kontrak\n\n"
        "**Sumber Data:** SAP ME 3N — Download List Kontrak\n\n"
        "_ETL untuk data kontrak perlu ditambahkan setelah format export SAP ME 3N dikonfirmasi._"
    )

    # == Gambaran Kolom yang Direncanakan =====================================
    st.markdown("### 📋 Rencana Struktur Data")
    st.markdown("""
    | Kolom | Keterangan |
    |---|---|
    | **Nomor Kontrak** | Nomor kontrak SAP (Outline Agreement) |
    | **Vendor** | Nama vendor / supplier |
    | **Tanggal Mulai** | Tanggal kontrak berlaku |
    | **Tanggal Berakhir** | Tanggal kontrak habis masa berlakunya |
    | **Sisa Hari** | Berapa hari lagi sampai kontrak berakhir |
    | **Nilai Kontrak** | Nilai total yang disepakati dalam kontrak (Rp) |
    | **Realisasi PO** | Total nilai PO yang sudah dibuat menggunakan kontrak ini |
    | **Sisa Kontrak** | Nilai kontrak yang belum terpakai |
    | **% Utilisasi** | Persentase nilai kontrak yang sudah digunakan |
    | **Purchasing Group** | PG penanggung jawab kontrak |
    | **Status** | Aktif / Hampir Berakhir / Expired |
    """)

    st.markdown("---")
    st.markdown(
        f"<p style='font-size:11px; opacity:0.35; text-align:right;'>"
        f"Halaman placeholder — dibuat {datetime.now().strftime('%d %B %Y')}</p>",
        unsafe_allow_html=True
    )