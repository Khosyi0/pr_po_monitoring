"""
v_detail.py - Halaman Detailed PR-PO SAP Data
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from utils import format_idr, format_idr_short, format_number, render_chat_analyst


def render(filter_conditions, bagian_pr_cond, bagian_po_cond, load_data, **kwargs):
        # ── DATA TABLE ───────────────────────────────────
        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:60px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" fill="currentColor" class="bi bi-clipboard2-data-fill" viewBox="0 0 16 16" style="margin-bottom: 10px; margin-right: 8px;">
                    <path d="M9.293 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4.707A1 1 0 0 0 13.707 4L10 .293A1 1 0 0 0 9.293 0M9.5 3.5v-2l3 3h-2a1 1 0 0 1-1-1M4.5 9a.5.5 0 0 1 0-1h7a.5.5 0 0 1 0 1zM4 10.5a.5.5 0 0 1 .5-.5h7a.5.5 0 0 1 0 1h-7a.5.5 0 0 1-.5-.5m.5 2.5a.5.5 0 0 1 0-1h4a.5.5 0 0 1 0 1z"/>
                </svg>
                Detailed PR-PO SAP Data
            </h1>
        """, unsafe_allow_html=True)
        st.markdown("---")

        st.markdown("""
            <h1 style='display: flex; align-items: center; font-size:20px; font-weight: normal;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-graph-up" viewBox="0 0 16 16" style="margin-bottom: 2px; margin-right: 4px;">
                    <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001q.044.06.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1 1 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0"/>
                </svg>
                Search (PR No, PO No, Material, Vendor)
            </h1>
        """, unsafe_allow_html=True)
        search_term = st.text_input("Search", value="", label_visibility="collapsed")
        search_condition = ""
        if search_term:
            search_condition = f"""
            AND (
                no_pr ILIKE '%{search_term}%' OR
                nomor_po ILIKE '%{search_term}%' OR
                pr_description ILIKE '%{search_term}%' OR
                vendor_name ILIKE '%{search_term}%'
            )
            """

        table_query = f"""
        SELECT
            no_pr, line_item_pr, tgl_create_pr, department_code,
            material_no, pr_description, quantity_pr, satuan_pr, estimasi_pr,
            nomor_po, date_ordered, vendor_name, qty_po,
            total_amount_local_curr, efisiensi, lead_time_process_po,
            status_pengiriman, on_time_delivery
        FROM vw_pr_po_complete
        WHERE {filter_conditions} {search_condition}
        AND ({bagian_pr_cond} OR {bagian_po_cond})
        ORDER BY tgl_create_pr DESC
        LIMIT 100
        """

        with st.spinner("Memuat data tabel..."):
            table_data = load_data(table_query)

        if not table_data.empty:

            table_data['no_pr'] = table_data['no_pr'].replace('No PR', '-')
            table_data['department_code'] = table_data['department_code'].replace('Unknown', '-')

            for col in ['estimasi_pr', 'total_amount_local_curr', 'efisiensi']:
                if col in table_data.columns:
                    table_data[col] = table_data[col].apply(
                        lambda x: f"Rp {x:,.0f}" if pd.notna(x) else ""
                    )
            for col in ['tgl_create_pr', 'date_ordered']:
                if col in table_data.columns:
                    table_data[col] = pd.to_datetime(table_data[col]).dt.strftime('%Y-%m-%d')

            st.dataframe(table_data, use_container_width=True, height=400)
            csv = table_data.to_csv(index=False)
            st.download_button(
                label="Download as CSV",
                icon=":material/download:",
                data=csv,
                file_name=f"pr_po_data_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("Tidak ada data yang cocok dengan filter yang dipilih.")

        # =====================================================================
        # INTEGRASI AI: KUMPULKAN KONTEKS & PANGGIL CHAT
        # =====================================================================

        info_filter = kwargs.get('info_filter', 'Tidak ada filter spesifik')
        konteks_lines = []

        # 0. Filter aktif
        konteks_lines.append("## 0. FILTER YANG SEDANG DITERAPKAN USER")
        konteks_lines.append(info_filter)
        konteks_lines.append("")

        # 1. Ringkasan statistik tabel yang sedang ditampilkan
        konteks_lines.append("## 1. RINGKASAN DATA TABEL YANG DITAMPILKAN")
        if 'table_data' in locals() and not table_data.empty:
            n_rows = len(table_data)
            konteks_lines.append(f"- Jumlah baris tampil: {n_rows} (limit 100 per query)")
            # Hitung ringkasan dari data yang ada
            n_pr  = table_data['no_pr'].replace('-', pd.NA).dropna().nunique()
            n_po  = table_data['nomor_po'].dropna().nunique()
            n_vnd = table_data['vendor_name'].dropna().nunique() if 'vendor_name' in table_data.columns else 0
            konteks_lines.append(f"- PR unik dalam data ini: {n_pr}")
            konteks_lines.append(f"- PO unik dalam data ini: {n_po}")
            konteks_lines.append(f"- Vendor unik: {n_vnd}")
            if search_term:
                konteks_lines.append(f"- Kata kunci pencarian aktif: '{search_term}'")
            konteks_lines.append("")

            # 2. Sampel 20 baris teratas untuk referensi LLM
            konteks_lines.append("## 2. SAMPEL DATA (20 BARIS TERATAS)")
            cols_for_ai = [c for c in ['no_pr', 'department_code', 'material_no', 'pr_description',
                                        'nomor_po', 'vendor_name', 'total_amount_local_curr',
                                        'lead_time_process_po', 'status_pengiriman', 'on_time_delivery']
                           if c in table_data.columns]
            konteks_lines.append(table_data[cols_for_ai].head(20).to_csv(index=False))
            konteks_lines.append("")
        else:
            konteks_lines.append("Tidak ada data yang cocok dengan filter yang dipilih.\n")

        # Gabungkan konteks lokal dengan konteks global lintas sistem
        suplemen = "\n# SUPLEMEN - DETAIL HALAMAN INI (Detailed PR-PO Data)\n" + "\n".join(konteks_lines)
        konteks_final = kwargs.get("global_context", "") + "\n---\n" + suplemen

        render_chat_analyst(
            konteks_data_teks=konteks_final,
            nama_halaman="Detailed PR-PO Data",
            load_data_fn=load_data,
        )