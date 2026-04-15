"""
v_inklaring_detail.py - Halaman Detailed Inklaring Barang Impor Data
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from utils import render_chat_analyst

def render(load_data, date_from=None, date_to=None, **kwargs):
    # ── DATA TABLE ───────────────────────────────────
    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:60px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" fill="currentColor" class="bi bi-box-seam-fill" viewBox="0 0 16 16" style="margin-bottom: 10px; margin-right: 8px;">
                <path fill-rule="evenodd" d="M15.528 2.973a.75.75 0 0 1 .472.696v8.662a.75.75 0 0 1-.472.696l-7.25 2.9a.75.75 0 0 1-.556 0l-7.25-2.9A.75.75 0 0 1 0 12.331V3.669a.75.75 0 0 1 .471-.696L7.443.184l.01-.003.268-.108a.75.75 0 0 1 .558 0l.269.108.01.003 6.97 2.789ZM10.404 2 4.25 4.461 1.846 3.5 8 1.039zM8 7.993c1.664-1.711 5.825-1.283 0 5.132-5.825-6.415-1.664-6.843 0-5.132"/>
            </svg>
            Detailed Inklaring Data
        </h1>
    """, unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:20px; font-weight: normal;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-search" viewBox="0 0 16 16" style="margin-bottom: 2px; margin-right: 4px;">
                <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001q.044.06.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1 1 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0"/>
            </svg>
            Search (No AJU, SAP, Nama Kapal, Komoditi, Pemasok)
        </h1>
    """, unsafe_allow_html=True)
    
    search_term = st.text_input("Search", value="", placeholder="Ketik AJU PIB, Nomor SAP, nama kapal, atau komoditi...", label_visibility="collapsed")

    # Filter rentang waktu menggunakan Tgl ETA
    date_filter = ""
    if date_from and date_to:
        start_str = date_from.strftime('%Y-%m-%d')
        end_str = date_to.strftime('%Y-%m-%d')
        date_filter = f"WHERE tgl_eta >= '{start_str}' AND tgl_eta <= '{end_str}'"
    
    # Query Data Inklaring
    table_query = f"""
    SELECT
        tgl_pib, aju_pib, no_aju, sap, nama_kapal, tgl_eta,
        quantity_mt, komoditi, pemasok, asal_negara,
        bea_masuk_rp, ppn_rp, pph_rp, kurs,
        start_bongkar, selesai_bongkar, ppjk,
        status, tgl_sppb
    FROM inklaring_impor
    {date_filter}
    ORDER BY tgl_eta DESC NULLS LAST
    """

    with st.spinner("Memuat data tabel inklaring..."):
        table_data_raw = load_data(table_query)

    if not table_data_raw.empty:
        # Proses Filter Search Bar
        if search_term:
            term = search_term.lower()
            mask = (
                table_data_raw['aju_pib'].astype(str).str.lower().str.contains(term, na=False) |
                table_data_raw['sap'].astype(str).str.lower().str.contains(term, na=False) |
                table_data_raw['nama_kapal'].astype(str).str.lower().str.contains(term, na=False) |
                table_data_raw['komoditi'].astype(str).str.lower().str.contains(term, na=False) |
                table_data_raw['pemasok'].astype(str).str.lower().str.contains(term, na=False)
            )
            table_data = table_data_raw[mask].copy()
        else:
            table_data = table_data_raw.copy()

        if not table_data.empty:
            # Handle Null values untuk display UI
            table_data['sap'] = table_data['sap'].fillna('-')
            table_data['no_aju'] = table_data['no_aju'].fillna('-')

            # Formatting Angka / Uang (Bea Masuk, PPN, PPH, Kurs)
            for col in ['bea_masuk_rp', 'ppn_rp', 'pph_rp', 'kurs']:
                if col in table_data.columns:
                    table_data[col] = table_data[col].apply(
                        lambda x: f"Rp {x:,.0f}" if pd.notna(x) else ""
                    )
            
            # Formatting Tanggal
            date_cols = ['tgl_pib', 'tgl_eta', 'start_bongkar', 'selesai_bongkar', 'tgl_sppb']
            for col in date_cols:
                if col in table_data.columns:
                    table_data[col] = pd.to_datetime(table_data[col]).dt.strftime('%Y-%m-%d')

            count_label = f"Menampilkan **{len(table_data):,}** baris dokumen impor"
            if len(table_data) > 500:
                count_label += " *(ditampilkan 500 teratas untuk performa, gunakan fitur Download untuk data lengkap)*"
                table_data_display = table_data.head(500)
            else:
                table_data_display = table_data

            st.caption(count_label)
            st.dataframe(table_data_display, use_container_width=True, height=400)
            
            # Tombol Download CSV
            csv = table_data.to_csv(index=False)
            st.download_button(
                label="Download as CSV",
                icon=":material/download:",
                data=csv,
                file_name=f"inklaring_data_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("Tidak ada data yang cocok dengan pencarian.")
    else:
        st.info("Tidak ada data inklaring yang ditemukan pada rentang tanggal ini.")

    # =====================================================================
    # INTEGRASI AI: KUMPULKAN KONTEKS & PANGGIL CHAT
    # =====================================================================

    info_filter = kwargs.get('info_filter', 'Filter tanggal default aktif')
    konteks_lines = []

    # 0. Filter aktif
    konteks_lines.append("## 0. FILTER YANG SEDANG DITERAPKAN USER")
    konteks_lines.append(info_filter)
    konteks_lines.append("")

    # 1. Ringkasan statistik tabel yang sedang ditampilkan
    konteks_lines.append("## 1. RINGKASAN DATA TABEL INKLARING")
    if 'table_data' in locals() and not table_data.empty:
        n_rows = len(table_data)
        konteks_lines.append(f"- Jumlah total dokumen PIB: {n_rows}")
        
        n_kapal = table_data['nama_kapal'].dropna().nunique()
        n_komoditi = table_data['komoditi'].dropna().nunique()
        
        konteks_lines.append(f"- Jumlah Kapal unik: {n_kapal}")
        konteks_lines.append(f"- Jenis Komoditi unik: {n_komoditi}")
        
        if search_term:
            konteks_lines.append(f"- Kata kunci pencarian aktif: '{search_term}'")
        konteks_lines.append("")

        # 2. Sampel 20 baris teratas untuk referensi LLM
        konteks_lines.append("## 2. SAMPEL DATA (20 BARIS TERATAS)")
        cols_for_ai = ['tgl_eta', 'tgl_pib', 'aju_pib', 'sap', 'nama_kapal', 'komoditi', 
                       'quantity_mt', 'bea_masuk_rp', 'status']
        cols_exist = [c for c in cols_for_ai if c in table_data.columns]
        konteks_lines.append(table_data[cols_exist].head(20).to_csv(index=False))
        konteks_lines.append("")
    else:
        konteks_lines.append("Tidak ada data yang tersedia.\n")

    # Gabungkan konteks lokal dengan konteks global
    suplemen = "\n# SUPLEMEN - DETAIL HALAMAN INI (Detailed Inklaring Impor)\n" + "\n".join(konteks_lines)
    konteks_final = kwargs.get("global_context", "") + "\n---\n" + suplemen

    render_chat_analyst(
        konteks_data_teks=konteks_final,
        nama_halaman="Detailed Inklaring Impor",
        load_data_fn=load_data,
    )