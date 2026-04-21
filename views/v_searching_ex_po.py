"""
v_searching_ex_po.py - Halaman Searching Ex PO (Placeholder)
Untuk mengetahui siapa saja vendor yang pernah menang di suatu material.
Sumber data: Basis material number 3 tahun ke belakang (PO SAP)
"""

import streamlit as st
from datetime import datetime


def render(**kwargs):

    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:55px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="45" height="45" fill="currentColor"
                 viewBox="0 0 16 16" style="margin-bottom: 8px; margin-right: 12px;">
                <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001q.044.06.098.115l3.85
                         3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1 1 0 0 0-.115-.1zM12 6.5a5.5
                         5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0"/>
            </svg>
            Searching Ex PO
        </h1>
    """, unsafe_allow_html=True)

    st.markdown(
        "<p style='font-size:16px; color:gray; margin-top:-8px;'>"
        "Pencarian riwayat vendor yang pernah menang pengadaan untuk suatu material.</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # == Info Placeholder ======================================================
    st.info(
        "🚧 **Halaman ini sedang dalam tahap perencanaan.**\n\n"
        "Halaman ini akan memungkinkan tim pengadaan untuk mencari riwayat vendor "
        "yang pernah mendapatkan PO untuk suatu material tertentu dalam 3 tahun terakhir. "
        "Berguna saat proses sourcing atau negosiasi untuk mengetahui kompetitor dan "
        "harga historis yang pernah ditawarkan.\n\n"
        "**Fitur yang direncanakan:**\n"
        "- Pencarian berdasarkan Material Number atau deskripsi material\n"
        "- Tampilan list vendor yang pernah menang beserta harga dan tanggal PO\n"
        "- Perbandingan harga antar vendor untuk material yang sama\n"
        "- Download hasil pencarian (3 tahun ke belakang)\n\n"
        "**Sumber Data:** Data PO SAP — basis Material Number, 3 tahun ke belakang\n\n"
        "_Data ini sudah tersedia di database, tinggal dibuatkan antarmuka pencarian._"
    )

    # == Gambaran Kolom yang Direncanakan =====================================
    st.markdown("### 📋 Rencana Tampilan Hasil Pencarian")
    st.markdown("""
    | Kolom | Keterangan |
    |---|---|
    | **Material Number** | Kode material SAP |
    | **Deskripsi** | Nama barang |
    | **Nomor PO** | Nomor Purchase Order |
    | **Tanggal PO** | Tanggal PO diterbitkan |
    | **Vendor** | Nama vendor yang mendapat PO |
    | **Harga Satuan** | Harga per satuan saat PO |
    | **Qty** | Kuantitas yang dipesan |
    | **Total Nilai PO** | Total nilai PO (Rp) |
    | **Metode Pengadaan** | Tender / Kontrak / Penunjukan Langsung |
    | **Purchasing Group** | PG penerbit PO |
    """)

    st.markdown("---")
    st.markdown(
        f"<p style='font-size:11px; opacity:0.35; text-align:right;'>"
        f"Halaman placeholder — dibuat {datetime.now().strftime('%d %B %Y')}</p>",
        unsafe_allow_html=True
    )