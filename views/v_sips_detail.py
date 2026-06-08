"""
v_sips_detail.py - Halaman Detailed SIPS Data
"""

import streamlit as st
import pandas as pd
import io
from datetime import datetime
from utils import build_sips_where, format_number, render_chat_analyst

def render(load_data, date_from, date_to, selected_nama, selected_bagian=None, **kwargs):

    selected_pgroup = kwargs.get('selected_pgroup', ['All'])

    # == Header ================================================================
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

    with st.expander("Pencarian & Tabel Data SIPS"):

        # == Search bar ============================================================
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

        # == WHERE clause ==========================================================
        # 1. Standard Where (menggunakan filter tanggal global)
        where_pr = build_sips_where(
            date_from=date_from, date_to=date_to,
            selected_nama=selected_nama, selected_bagian=selected_bagian,
            selected_pgroup=selected_pgroup
        )

        # 2. Where khusus PO (mengabaikan filter tanggal global)
        where_po = build_sips_where(
            date_from=None, date_to=None,
            selected_nama=selected_nama, selected_bagian=selected_bagian,
            selected_pgroup=selected_pgroup
        )

        # 3. Kondisi filter tanggal PO untuk meniru behavior "COUNTIFS" di Excel
        po_date_cond = f"""(
            (tgl_po >= '{date_from}'::date AND tgl_po <= '{date_to}'::date)
            OR tgl_po IS NULL 
            OR tgl_po::text IN ('', '-')
        )"""

        # == Query tabel ===========================================================
        table_query = f"""
            SELECT
                nama,
                no_pr,
                item_of                                            AS "Item",
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
            WHERE ({where_pr}) OR ({where_po} AND {po_date_cond})
            ORDER BY requisition_date DESC
        """

        with st.spinner("Memuat data..."):
            try:
                df_raw = load_data(table_query)
            except Exception as e:
                st.error(f"Gagal memuat data: {e}")
                return

        if not df_raw.empty:
            if search_term:
                term = search_term.lower()
                mask = (
                    df_raw['no_pr'].astype(str).str.lower().str.contains(term, na=False) |
                    df_raw['No PO'].astype(str).str.lower().str.contains(term, na=False) |
                    df_raw['Deskripsi'].astype(str).str.lower().str.contains(term, na=False) |
                    df_raw['nama'].astype(str).str.lower().str.contains(term, na=False) |
                    df_raw['No MR/SR'].astype(str).str.lower().str.contains(term, na=False)
                )
                df = df_raw[mask].copy()
            else:
                df = df_raw.copy()
                
            if not df.empty:
                
                df.index = df.index + 1

                # == Format kolom ==========================================================
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

                # == Info jumlah baris =====================================================
                count_label = f"Menampilkan **{len(df):,}** baris"
                if len(df) > 500:
                    count_label += " *(ditampilkan 500 teratas untuk performa, gunakan fitur Download untuk data lengkap)*"
                    df_display = df.head(500)
                else:
                    df_display = df
                    
                st.caption(count_label)

                styled_display = (df_display.style
                          .map(color_status, subset=["Status"])
                          .map(color_sla,    subset=["SLA Nilai"]))

                st.dataframe(styled_display, use_container_width=True, height=480)

                # == Download XLSX ==========================================================
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='SIPS_Data')
                excel_buffer.seek(0) # Kembali ke awal buffer

                st.download_button(
                    label="Download sebagai XLSX",
                    icon=":material/download:",
                    data=excel_buffer,
                    file_name=f"sips_data_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                )
            else:
                st.info("Tidak ada data yang cocok dengan pencarian.")
        else:
            st.info("Tidak ada data yang cocok dengan filter yang dipilih.")

    st.markdown("---")

    # =====================================================================
    # INTEGRASI AI: KUMPULKAN KONTEKS & PANGGIL CHAT
    # =====================================================================

    info_filter = kwargs.get('info_filter', 'Tidak ada filter spesifik')
    konteks_lines = []

    # 0. Filter aktif
    konteks_lines.append("## 0. FILTER YANG SEDANG DITERAPKAN USER")
    konteks_lines.append(info_filter)
    konteks_lines.append("")

    # 1. Ringkasan statistik tabel
    konteks_lines.append("## 1. RINGKASAN DATA TABEL SIPS YANG DITAMPILKAN")
    if 'df' in locals() and not df.empty:
        n_rows = len(df)
        konteks_lines.append(f"- Jumlah baris tampil: {n_rows} (limit 500 per query)")

        # Gunakan kolom asli dari df (sebelum rename/format) yang masih tersimpan
        if 'nama' in df.columns:
            konteks_lines.append(f"- Karyawan (nama) unik: {df['nama'].dropna().nunique()}")
        if 'Status' in df.columns:
            status_dist = df['Status'].value_counts().to_dict()
            status_str = ", ".join(f"{k}: {v}" for k, v in status_dist.items())
            konteks_lines.append(f"- Distribusi Status: {status_str}")
        if 'SLA Nilai' in df.columns:
            try:
                sla_ok   = (df['SLA Nilai'].astype(str) == '1').sum()
                sla_miss = (df['SLA Nilai'].astype(str) == '0').sum()
                sla_pct  = round(sla_ok / (sla_ok + sla_miss) * 100, 1) if (sla_ok + sla_miss) > 0 else 0
                konteks_lines.append(f"- SLA On Time: {sla_ok} | Terlambat: {sla_miss} | % On Time: {sla_pct}%")
            except Exception:
                pass
        if search_term:
            konteks_lines.append(f"- Kata kunci pencarian aktif: '{search_term}'")
        konteks_lines.append("")

        # 2. Sampel 20 baris teratas
        konteks_lines.append("## 2. SAMPEL DATA SIPS (20 BARIS TERATAS)")
        cols_for_ai = [c for c in ['nama', 'no_pr', 'Status', 'Deskripsi', 'Tgl Requisisi',
                                    'Tgl PO', 'PR-PO (hari)', 'SLA Standar', 'SLA Realisasi',
                                    'SLA Nilai', 'Prioritas', 'OE PR (Rp)', 'Nilai PO (Rp)']
                       if c in df.columns]
        konteks_lines.append(df[cols_for_ai].head(20).to_csv(index=False))
        konteks_lines.append("")
    else:
        konteks_lines.append("Tidak ada data yang cocok dengan filter yang dipilih.\n")

    # Gabungkan konteks lokal dengan konteks global lintas sistem
    suplemen = "\n# SUPLEMEN - DETAIL HALAMAN INI (Detailed SIPS Data)\n" + "\n".join(konteks_lines)
    konteks_final = kwargs.get("global_context", "") + "\n---\n" + suplemen

    with st.expander("Tanya ke Melati (Monitoring, Evaluasi, Laporan Terintegrasi)"):
        render_chat_analyst(
            konteks_data_teks=konteks_final,
            nama_halaman="Detailed SIPS Data",
            load_data_fn=load_data,
        )