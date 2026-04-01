"""
v_isu.py - Halaman Isu (Placeholder)
Menampilkan isu per bahan baku yang dikategorikan (operasional, harga, kebijakan, dll.)
Sumber data: BB & semua bagian (akan ditentukan lebih lanjut)
"""

import streamlit as st
from datetime import datetime


def render(**kwargs):

    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:55px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="45" height="45" fill="currentColor"
                 viewBox="0 0 16 16" style="margin-bottom: 8px; margin-right: 12px;">
                <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98
                         1.767h13.713c.889 0 1.438-.99.98-1.767zM8 5c.535 0 .954.462.9.995l-.35
                         3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5m.002 6a1 1 0 1
                         1 0 2 1 1 0 0 1 0-2"/>
            </svg>
            Isu
        </h1>
    """, unsafe_allow_html=True)

    st.markdown(
        "<p style='font-size:16px; color:gray; margin-top:-8px;'>"
        "Pencatatan dan monitoring isu per bahan baku dari seluruh bagian.</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # ── Info Placeholder ──────────────────────────────────────────────────────
    st.info(
        "🚧 **Halaman ini sedang dalam tahap perencanaan.**\n\n"
        "Halaman ini akan menampilkan isu yang terkait dengan bahan baku dari semua bagian, "
        "lengkap dengan kategori isu (operasional, harga, kebijakan, dll.), periode, dan status penyelesaian.\n\n"
        "**Fitur yang direncanakan:**\n"
        "- Tabel daftar isu: Bahan Baku, Isu, Periode, Kategori Isu\n"
        "- Filter berdasarkan kategori isu, periode, dan bagian\n"
        "- Input / edit isu (CRUD) oleh user yang berwenang\n"
        "- Ringkasan jumlah isu per kategori (chart)\n\n"
        "**Sumber Data:** BB & semua bagian (input manual oleh user)\n\n"
        "_Halaman ini akan diimplementasikan setelah diskusi lebih lanjut dengan tim terkait._"
    )

    # ── Gambaran Kolom yang Direncanakan ─────────────────────────────────────
    st.markdown("### 📋 Rencana Struktur Data")
    st.markdown("""
    | Kolom | Keterangan |
    |---|---|
    | **Bahan Baku** | Nama / kode bahan baku yang terdampak |
    | **Isu** | Deskripsi isu yang terjadi |
    | **Periode** | Periode isu terjadi (bulan/tahun) |
    | **Kategori Isu** | Jenis isu: Operasional / Harga / Kebijakan / Lainnya |
    | **Bagian** | Bagian yang melaporkan isu (BB, ALPATA, BARUM, dll.) |
    | **Status** | Open / In Progress / Resolved |
    | **Tanggal Input** | Tanggal data dimasukkan |
    | **Catatan** | Keterangan tambahan / tindakan yang diambil |
    """)

    st.markdown("---")
    st.markdown(
        f"<p style='font-size:11px; opacity:0.35; text-align:right;'>"
        f"Halaman placeholder — dibuat {datetime.now().strftime('%d %B %Y')}</p>",
        unsafe_allow_html=True
    )