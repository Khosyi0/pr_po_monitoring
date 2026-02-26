"""
v_sips_detail.py - Halaman Detailed SIPS Data
"""

import streamlit as st
import pandas as pd
from datetime import datetime


def render(load_data, date_from, date_to, selected_nama, **kwargs):

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:60px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" fill="currentColor"
                 viewBox="0 0 16 16" style="margin-bottom:10px; margin-right:8px;">
                <path d="M9.293 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0
                         2-2V4.707A1 1 0 0 0 13.707 4L10 .293A1 1 0 0 0 9.293 0M9.5
                         3.5v-2l3 3h-2a1 1 0 0 1-1-1M4.5 9a.5.5 0 0 1 0-1h7a.5.5 0
                         0 1 0 1zM4 10.5a.5.5 0 0 1 .5-.5h7a.5.5 0 0 1 0 1h-7a.5.5
                         0 0 1-.5-.5m.5 2.5a.5.5 0 0 1 0-1h4a.5.5 0 0 1 0 1z"/>
            </svg>
            Detailed SIPS Data
        </h1>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # ── Search bar ────────────────────────────────────────────────────────────
    st.markdown("""
        <h3 style='display:flex; align-items:center; font-size:18px; font-weight:600;
                   margin-bottom:8px; gap:6px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor"
                 viewBox="0 0 16 16">
                <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001q.044.06.098.115l3.85
                         3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1 1 0 0 0-.115-.1zM12 6.5a5.5
                         5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0"/>
            </svg>
            Search (No PR, No PO, Short Text, Nama)
        </h3>
    """, unsafe_allow_html=True)

    search_term = st.text_input("Search", value="", label_visibility="collapsed",
                                placeholder="Ketik No PR, No PO, nama barang, atau nama karyawan...")

    # ── WHERE clause ──────────────────────────────────────────────────────────
    where_parts = ["1=1"]
    if date_from:
        where_parts.append(f"requisition_date >= '{date_from}'")
    if date_to:
        where_parts.append(f"requisition_date <= '{date_to}'")
    if selected_nama and 'All' not in selected_nama:
        names_sql = ", ".join(f"'{n}'" for n in selected_nama)
        where_parts.append(f"nama IN ({names_sql})")
    if search_term:
        term = search_term.replace("'", "''")
        where_parts.append(f"""(
            no_pr       ILIKE '%{term}%' OR
            no_po       ILIKE '%{term}%' OR
            short_text  ILIKE '%{term}%' OR
            nama        ILIKE '%{term}%' OR
            nomor_mr_sr ILIKE '%{term}%'
        )""")
    where = " AND ".join(where_parts)

    # ── Query tabel ───────────────────────────────────────────────────────────
    table_query = f"""
        SELECT
            nama,
            no_pr,
            item_of                                             AS "Item",
            status                                             AS "Status",
            purchasing_group                                   AS "P. Group",
            short_text                                         AS "Deskripsi",
            requisition_date                                   AS "Tgl Requisisi",
            tgl_po                                             AS "Tgl PO",
            no_po                                              AS "No PO",
            pr_po_days                                         AS "PR-PO (hari)",
            standar_sla                                        AS "SLA Standar",
            realisasi_sla                                      AS "SLA Realisasi",
            nilai_sla                                          AS "SLA Nilai",
            kontrak_status                                     AS "Kontrak",
            prioritas                                          AS "Prioritas",
            oe_pr                                              AS "OE PR (Rp)",
            nilai_item_po                                      AS "Nilai PO (Rp)",
            ROUND((persen_po_sr_mr * 100)::numeric, 2)         AS "PO/MR (%)",
            nomor_mr_sr                                        AS "No MR/SR"
        FROM vw_sips
        WHERE {where}
        ORDER BY requisition_date DESC
        LIMIT 500
    """

    with st.spinner("Memuat data..."):
        try:
            df = load_data(table_query)
        except Exception as e:
            st.error(f"Gagal memuat data: {e}")
            return

    if df.empty:
        st.info("Tidak ada data yang sesuai dengan filter.")
        return

    # ── Format kolom ──────────────────────────────────────────────────────────
    for col in ["OE PR (Rp)", "Nilai PO (Rp)"]:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: f"Rp {x:,.0f}" if pd.notna(x) else ""
            )

    for col in ["Tgl Requisisi", "Tgl PO"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d')

    for col in ["PR-PO (hari)", "SLA Standar", "SLA Realisasi"]:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: f"{x:.0f}" if pd.notna(x) else ""
            )

    if "PO/MR (%)" in df.columns:
        df["PO/MR (%)"] = df["PO/MR (%)"].apply(
            lambda x: f"{x:.2f}%" if pd.notna(x) else ""
        )

    # Warnai kolom Status
    def color_status(val):
        colors = {
            "Closed":    "color: #09ab3b; font-weight:600",
            "Proses PO": "color: #f0a500; font-weight:600",
            "Open":      "color: #6c8ebf; font-weight:600",
        }
        return colors.get(val, "")

    def color_sla(val):
        try:
            v = float(str(val).replace(",", "."))
            if v == 1:   return "color: #09ab3b; font-weight:600"
            if v == 0:   return "color: #e03c3c; font-weight:600"
        except:
            pass
        return ""

    styled = (df.style
              .map(color_status, subset=["Status"])
              .map(color_sla,    subset=["SLA Nilai"]))

    # ── Info jumlah baris ─────────────────────────────────────────────────────
    count_label = f"Menampilkan **{len(df):,}** baris"
    if len(df) == 500:
        count_label += " *(limit 500, gunakan filter untuk mempersempit hasil)*"
    st.caption(count_label)

    st.dataframe(styled, use_container_width=True, height=480)

    # ── Download CSV ──────────────────────────────────────────────────────────
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download sebagai CSV",
        icon=":material/download:",
        data=csv,
        file_name=f"sips_data_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
    )
