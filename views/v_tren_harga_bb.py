"""
v_tren_harga_bb.py - Halaman Tren Harga Bahan Baku (Placeholder)
Menampilkan pergerakan harga bahan baku 5 tahunan.
Sumber data: BB
"""

import streamlit as st
from datetime import datetime


def render(**kwargs):

    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:55px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="45" height="45" fill="currentColor"
                 viewBox="0 0 16 16" style="margin-bottom: 8px; margin-right: 12px;">
                <path d="M0 0h1v15h15v1H0zm14.817 3.113a.5.5 0 0 1 .07.704l-4.5 5.5a.5.5
                         0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5
                         0 0 1 .758-.06l2.609 2.61 4.15-5.073a.5.5 0 0 1 .704-.07"/>
            </svg>
            Tren Harga Bahan Baku
        </h1>
    """, unsafe_allow_html=True)

    st.markdown(
        "<p style='font-size:16px; color:gray; margin-top:-8px;'>"
        "Monitoring pergerakan harga bahan baku dalam 5 tahun terakhir.</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # ── Info Placeholder ──────────────────────────────────────────────────────
    st.info(
        "🚧 **Halaman ini sedang dalam tahap perencanaan.**\n\n"
        "Halaman ini akan menampilkan grafik tren harga bahan baku secara historis "
        "selama 5 tahun ke belakang, sehingga tim dapat mengidentifikasi pola harga, "
        "lonjakan tidak wajar, dan tren jangka panjang.\n\n"
        "**Fitur yang direncanakan:**\n"
        "- Grafik harga historis per bahan baku (line chart 5 tahunan)\n"
        "- Filter berdasarkan nama/kode bahan baku\n"
        "- Perbandingan harga antar periode (YoY)\n"
        "- Anotasi event penting (misal: kenaikan harga global, perubahan vendor)\n\n"
        "**Sumber Data:** BB\n\n"
        "_Sumber data dan format file akan dikonfirmasi lebih lanjut bersama tim BB._"
    )

    # ── Gambaran Kolom yang Direncanakan ─────────────────────────────────────
    st.markdown("### 📋 Rencana Struktur Data")
    st.markdown("""
    | Kolom | Keterangan |
    |---|---|
    | **Kode / Nama Bahan Baku** | Identifikasi bahan baku |
    | **Periode** | Bulan & tahun harga tercatat |
    | **Harga Satuan** | Harga per satuan bahan baku (Rp atau USD) |
    | **Satuan** | Satuan pengukuran (ton, kg, liter, dll.) |
    | **Vendor / Sumber** | Vendor atau sumber harga referensi |
    | **Catatan** | Keterangan tambahan (misal: harga pasar, kontrak) |
    """)

    st.markdown("---")
    st.markdown(
        f"<p style='font-size:11px; opacity:0.35; text-align:right;'>"
        f"Halaman placeholder — dibuat {datetime.now().strftime('%d %B %Y')}</p>",
        unsafe_allow_html=True
    )