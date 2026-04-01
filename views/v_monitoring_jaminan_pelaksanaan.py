"""
v_monitoring_jaminan_pelaksanaan.py - Halaman Monitoring Jaminan Pelaksanaan (Placeholder)
Memantau apakah vendor sudah mengirim jaminan pelaksanaan
Sumber data: List PO - EPP, List Realisasinya - Masing-masing buyer
"""

import streamlit as st
from datetime import datetime


def render(**kwargs):

    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:55px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="45" height="45" fill="currentColor"
                 viewBox="0 0 16 16" style="margin-bottom: 8px; margin-right: 12px;">
                <path d="M9.5 0a.5.5 0 0 1 .5.5.5.5 0 0 0 .5.5.5.5 0 0 1 .5.5V2a.5.5 0 0 1-.5.5h-5A.5.5 0 0 1 5 2v-.5a.5.5 0 0 1 .5-.5.5.5 0 0 0 .5-.5.5.5 0 0 1 .5-.5z"/>
                <path d="M3 2.5a.5.5 0 0 1 .5-.5H4a.5.5 0 0 0 0-1h-.5A1.5 1.5 0 0 0 2 2.5v12A1.5 1.5 0 0 0 3.5 16h9a1.5 1.5 0 0 0 1.5-1.5v-12A1.5 1.5 0 0 0 12.5 1H12a.5.5 0 0 0 0 1h.5a.5.5 0 0 1 .5.5v12a.5.5 0 0 1-.5.5h-9a.5.5 0 0 1-.5-.5z"/>
                <path d="M9.979 5.356a.5.5 0 0 0-.968.04L7.92 10.49l-.94-3.135a.5.5 0 0 0-.926-.08L4.69 10H4.5a.5.5 0 0 0 0 1H5a.5.5 0 0 0 .447-.276l.936-1.873 1.138 3.793a.5.5 0 0 0 .968-.04L9.58 7.51l.94 3.135A.5.5 0 0 0 11 11h.5a.5.5 0 0 0 0-1h-.128z"/>
            </svg>
            Monitoring Jaminan Pelaksanaan
        </h1>
    """, unsafe_allow_html=True)

    st.markdown(
        "<p style='font-size:16px; color:gray; margin-top:-8px;'>"
        "Monitoring perkiraan apakah vendor sudah mengirim jaminan pelaksanaan</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # ── Info Placeholder ──────────────────────────────────────────────────────
    st.info(
        "🚧 **Halaman ini sedang dalam tahap perencanaan.**\n\n"
        "Halaman ini akan menampilkan grafik perkiraan apakah vendor sudah mengirim jaminan pelaksanaan.\n\n"
        "**Fitur yang direncanakan:**\n"
        "- Tes\n\n"
        "**Sumber Data:** \n - List PO : EPP\n - List Realisasi : Masing-masing Buyer"
    )

    # ── Gambaran Kolom yang Direncanakan ─────────────────────────────────────
    st.markdown("### 📋 Rencana Struktur Data")
    st.markdown("""
    | Kolom | Keterangan |
    |---|---|
    | **Tes** | Tes |
    """)

    st.markdown("---")
    st.markdown(
        f"<p style='font-size:11px; opacity:0.35; text-align:right;'>"
        f"Halaman placeholder — dibuat {datetime.now().strftime('%d %B %Y')}</p>",
        unsafe_allow_html=True
    )