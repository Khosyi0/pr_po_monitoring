"""
v_monitoring_sparepart_ln.py - Halaman Monitoring Kedatangan Sparepart LN (Placeholder)
Memantau perkiraan kedatangan barang dari Luar Negeri (LN).
Sumber data: Tanggal siap ambil, Siapa yang ambil, Incoterm, LC/TT, parsial/sekali kirim
"""

import streamlit as st
from datetime import datetime


def render(**kwargs):

    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:55px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="45" height="45" fill="currentColor"
                 viewBox="0 0 16 16" style="margin-bottom: 8px; margin-right: 12px;">
                <path d="M0 3.5A1.5 1.5 0 0 1 1.5 2h9A1.5 1.5 0 0 1 12 3.5V5h1.02a1.5 1.5 0
                         0 1 1.17.563l1.481 1.85a1.5 1.5 0 0 1 .329.938V10.5a1.5 1.5 0 0 1-1.5
                         1.5H14a2 2 0 1 1-4 0H5a2 2 0 1 1-3.998-.085A1.5 1.5 0 0 1 0 10.5zm1.294
                         7.456A2 2 0 0 1 4.732 11h5.536a2 2 0 0 1 .732-.732V3.5a.5.5 0 0
                         0-.5-.5h-9a.5.5 0 0 0-.5.5v7a.5.5 0 0 0 .294.456M12 10a2 2 0 0 1 1.732
                         1h.768a.5.5 0 0 0 .5-.5V8.35a.5.5 0 0 0-.11-.312l-1.48-1.85A.5.5 0 0
                         0 13.02 6H12zm-9 1a1 1 0 1 0 0 2 1 1 0 0 0 0-2m9 0a1 1 0 1 0 0 2 1 1
                         0 0 0 0-2"/>
            </svg>
            Monitoring Kedatangan Sparepart LN
        </h1>
    """, unsafe_allow_html=True)

    st.markdown(
        "<p style='font-size:16px; color:gray; margin-top:-8px;'>"
        "Monitoring perkiraan kedatangan barang / sparepart dari Luar Negeri.</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # ── Info Placeholder ──────────────────────────────────────────────────────
    st.info(
        "🚧 **Halaman ini sedang dalam tahap perencanaan.**\n\n"
        "Halaman ini akan memantau perkiraan kedatangan sparepart yang dipesan dari Luar Negeri (LN), "
        "termasuk informasi incoterm, metode pembayaran, dan jadwal pengiriman.\n\n"
        "**Fitur yang direncanakan:**\n"
        "- List PO LN beserta estimasi tanggal siap ambil\n"
        "- Informasi siapa yang mengambil barang\n"
        "- Detail incoterm (FOB, CIF, dll.) dan metode pembayaran (LC / TT)\n"
        "- Status pengiriman: parsial atau sekali kirim\n"
        "- Alert mendekati tanggal kedatangan\n\n"
        "**Sumber Data:** Tanggal siap ambil, Siapa yang ambil, Incoterm, LC/TT, parsial/sekali kirim\n\n"
        "**Tampilan:** Mirip dengan halaman Monitoring Jaminan Pelaksanaan "
        "(list dengan kolom status dan detail pengiriman)\n\n"
        "_Detail kolom dan format data akan dikonfirmasi lebih lanjut._"
    )

    # ── Gambaran Kolom yang Direncanakan ─────────────────────────────────────
    st.markdown("### 📋 Rencana Struktur Data")
    st.markdown("""
    | Kolom | Keterangan |
    |---|---|
    | **Nomor PO** | Nomor Purchase Order SAP |
    | **Vendor** | Nama vendor / supplier luar negeri |
    | **Deskripsi Barang** | Nama / kode sparepart |
    | **Tanggal Siap Ambil** | Estimasi tanggal barang siap diambil |
    | **Siapa yang Ambil** | Nama petugas / forwarder yang mengambil barang |
    | **Incoterm** | Syarat pengiriman (FOB, CIF, EXW, dll.) |
    | **Metode Pembayaran** | LC (Letter of Credit) atau TT (Telegraphic Transfer) |
    | **Jenis Pengiriman** | Parsial (bertahap) atau Sekali Kirim |
    | **Status** | Menunggu / Dalam Perjalanan / Sudah Tiba / Selesai |
    | **Catatan** | Keterangan tambahan |
    """)

    st.markdown("---")
    st.markdown(
        f"<p style='font-size:11px; opacity:0.35; text-align:right;'>"
        f"Halaman placeholder — dibuat {datetime.now().strftime('%d %B %Y')}</p>",
        unsafe_allow_html=True
    )