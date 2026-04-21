import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy import text
import io
import os
import sys
import time
from contextlib import redirect_stdout, redirect_stderr

def _get_engine():
    from config_db import get_db_engine
    return get_db_engine()

class StreamlitCapture:
    """Menangkap output terminal (seperti fungsi print & tqdm) dan menampilkannya di Streamlit."""
    def __init__(self, placeholder):
        self.placeholder = placeholder
        self.lines = []
        self.current_line = ""
        self.last_update = time.time()
        
    def write(self, text):
        for char in text:
            if char == '\r':
                self.current_line = ""  # tqdm menimpa baris yang sama menggunakan carriage return
            elif char == '\n':
                self.lines.append(self.current_line)
                self.current_line = ""
            else:
                self.current_line += char
                
        # Refresh UI max 2 kali per detik agar browser tidak freeze
        if time.time() - self.last_update > 0.5:
            self.flush()
            
    def flush(self):
        display_lines = self.lines[-22:] + [self.current_line]
        self.placeholder.code('\n'.join(display_lines), language='bash')
        self.last_update = time.time()

def render(**kwargs):
    # == Header Halaman ========================================================
    st.markdown("""
        <h1 style='display:flex; align-items:center; font-size:42px; margin-bottom:0;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" fill="currentColor" 
                 viewBox="0 0 16 16" style="margin-right:12px; margin-bottom:4px;">
                <path d="M15.502 1.94a.5.5 0 0 1 0 .706L14.459 3.69l-2-2L13.502.646a.5.5 0 0 1 .707 0l1.293 1.293zm-1.75 2.456-2-2L4.939 9.21a.5.5 0 0 0-.121.196l-.805 2.414a.25.25 0 0 0 .316.316l2.414-.805a.5.5 0 0 0 .196-.12l6.813-6.814z"/>
                <path fill-rule="evenodd" d="M1 13.5A1.5 1.5 0 0 0 2.5 15h11a1.5 1.5 0 0 0 1.5-1.5v-6a.5.5 0 0 0-1 0v6a.5.5 0 0 1-.5.5h-11a.5.5 0 0 1-.5-.5v-11a.5.5 0 0 1 .5-.5H9a.5.5 0 0 0 0-1H2.5A1.5 1.5 0 0 0 1 2.5z"/>
            </svg>
            Manajemen Data
        </h1>
    """, unsafe_allow_html=True)
    
    st.markdown(
        "<p style='font-size:15px; opacity:0.6; margin-top:4px; margin-bottom:24px;'>"
        "Pusat kendali sinkronisasi data SAP, SIPS, Inklaring, dan manajemen backup sistem."
        "</p>", 
        unsafe_allow_html=True
    )

    from config_db import get_setting, set_setting

    sap_date_str = get_setting("DATA_UPDATE_SAP", "2026-03-31")
    sips_date_str = get_setting("DATA_UPDATE_SIPS", "2026-03-31")
    inklaring_date_str = get_setting("DATA_UPDATE_INKLARING", "2026-03-31")

    try: DATA_UPDATE_SAP = datetime.strptime(sap_date_str, "%Y-%m-%d").date()
    except: DATA_UPDATE_SAP = datetime(2026, 3, 31).date()
        
    try: DATA_UPDATE_SIPS = datetime.strptime(sips_date_str, "%Y-%m-%d").date()
    except: DATA_UPDATE_SIPS = datetime(2026, 3, 31).date()

    try: DATA_UPDATE_INKLARING = datetime.strptime(inklaring_date_str, "%Y-%m-%d").date()
    except: DATA_UPDATE_INKLARING = datetime(2026, 3, 31).date()

    # == Bagian 1: Informasi Status Data =======================================
    st.markdown("""
        <h3 style='display: flex; align-items: center; font-size:20px; margin-bottom:12px; color:var(--text-color);'>
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-arrow-repeat" viewBox="0 0 16 16" style="margin-bottom: 2px; margin-right: 8px;">
                <path d="M11.534 7h3.932a.25.25 0 0 1 .192.41l-1.966 2.36a.25.25 0 0 1-.384 0l-1.966-2.36a.25.25 0 0 1 .192-.41m-11 2h3.932a.25.25 0 0 0 .192-.41L2.692 6.23a.25.25 0 0 0-.384 0L.342 8.59A.25.25 0 0 0 .534 9z"/>
                <path fill-rule="evenodd" d="M8 3c-1.552 0-2.94.707-3.857 1.818a.5.5 0 1 1-.771-.636A6.002 6.002 0 0 1 13.917 7H12.9A5 5 0 0 0 8 3M3.1 9a5.002 5.002 0 0 0 8.757 2.182.5.5 0 1 1 .771.636A6.002 6.002 0 0 1 2.083 9z"/>
            </svg>
            Status Pembaruan Data
        </h3>
    """, unsafe_allow_html=True)
    
    col_sap, col_sips, col_inklaring = st.columns(3)
    
    with col_sap:
        st.markdown(f"""
            <div style='background: var(--secondary-background-color); border: 1px solid rgba(31, 119, 180, 0.3); border-radius: 10px; padding: 16px; border-left: 5px solid #1f77b4;'>
                <p style='margin: 0; font-size: 14px; opacity: 0.7; font-weight: 600;'>Database PR-PO SAP</p>
                <h4 style='margin: 4px 0 0 0; font-size: 24px;'>{DATA_UPDATE_SAP.strftime('%d %B %Y')}</h4>
            </div>
        """, unsafe_allow_html=True)

    with col_sips:
        st.markdown(f"""
            <div style='background: var(--secondary-background-color); border: 1px solid rgba(255, 75, 75, 0.3); border-radius: 10px; padding: 16px; border-left: 5px solid #ff4b4b;'>
                <p style='margin: 0; font-size: 14px; opacity: 0.7; font-weight: 600;'>Database SIPS</p>
                <h4 style='margin: 4px 0 0 0; font-size: 24px;'>{DATA_UPDATE_SIPS.strftime('%d %B %Y')}</h4>
            </div>
        """, unsafe_allow_html=True)

    with col_inklaring:
        st.markdown(f"""
            <div style='background: var(--secondary-background-color); border: 1px solid rgba(44, 160, 44, 0.3); border-radius: 10px; padding: 16px; border-left: 5px solid #2ca02c;'>
                <p style='margin: 0; font-size: 14px; opacity: 0.7; font-weight: 600;'>Database Inklaring Impor</p>
                <h4 style='margin: 4px 0 0 0; font-size: 24px;'>{DATA_UPDATE_INKLARING.strftime('%d %B %Y')}</h4>
            </div>
        """, unsafe_allow_html=True)

    with st.expander("✏️ Edit Manual Tanggal Pembaruan"):
        with st.form("form_edit_tanggal"):
            c1, c2, c3 = st.columns(3)
            with c1:
                new_sap_date = st.date_input("Tanggal Update SAP", DATA_UPDATE_SAP)
            with c2:
                new_sips_date = st.date_input("Tanggal Update SIPS", DATA_UPDATE_SIPS)
            with c3:
                new_inklaring_date = st.date_input("Tanggal Update Inklaring", DATA_UPDATE_INKLARING)
            
            if st.form_submit_button("Simpan Perubahan"):
                set_setting("DATA_UPDATE_SAP", new_sap_date.strftime("%Y-%m-%d"))
                set_setting("DATA_UPDATE_SIPS", new_sips_date.strftime("%Y-%m-%d"))
                set_setting("DATA_UPDATE_INKLARING", new_inklaring_date.strftime("%Y-%m-%d"))
                st.success("Berhasil mengubah tanggal!")
                time.sleep(1)
                st.rerun()

    st.markdown("<hr style='margin: 32px 0 24px 0; border-color: rgba(128,128,128,0.2);'>", unsafe_allow_html=True)

    # == Bagian 2: Placeholder Backup & Upload =================================
    col_kiri, col_kanan = st.columns(2, gap="large")
    
    with col_kiri:
        st.markdown("""
            <h3 style='display: flex; align-items: center; font-size:18px; margin-bottom:12px; color:var(--text-color);'>
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" class="bi bi-box-arrow-in-down" viewBox="0 0 16 16" style="margin-bottom: 2px; margin-right: 8px;">
                    <path fill-rule="evenodd" d="M3.5 6a.5.5 0 0 0-.5.5v8a.5.5 0 0 0 .5.5h9a.5.5 0 0 0 .5-.5v-8a.5.5 0 0 0-.5-.5h-2a.5.5 0 0 1 0-1h2A1.5 1.5 0 0 1 14 6.5v8a1.5 1.5 0 0 1-1.5 1.5h-9A1.5 1.5 0 0 1 2 14.5v-8A1.5 1.5 0 0 1 3.5 5h2a.5.5 0 0 1 0 1z"/>
                    <path fill-rule="evenodd" d="M7.646 11.854a.5.5 0 0 0 .708 0l3-3a.5.5 0 0 0-.708-.708L8.5 10.293V1.5a.5.5 0 0 0-1 0v8.793L5.354 8.146a.5.5 0 1 0-.708.708z"/>
                </svg>
                Download / Backup Data
            </h3>
        """, unsafe_allow_html=True)
        
        with st.form("form_backup"):
            jenis_data = st.selectbox("Jenis Data", ["PR SAP", "PO SAP", "SIPS", "Inklaring Barang Impor"])
            c_from, c_to = st.columns(2)
            with c_from:
                start_date = st.date_input("Dari Tanggal", datetime(2026, 1, 1))
            with c_to:
                end_date = st.date_input("Sampai Tanggal", datetime(2026, 3, 31))
            
            submit_backup = st.form_submit_button("Siapkan File Backup")

        if submit_backup:
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            if jenis_data == "PR SAP":
                query = f"""
                SELECT 
                    pr.no_pr AS "No PR",
                    pr.tgl_create_pr AS "Tgl Create PR",
                    pr.department_code AS "Departement(Requisitioner)",
                    pr.plant_code AS "Plant",
                    pr.mrp_controller AS "MRP Controller",
                    pr.purchasing_group AS "Purchasing Group",
                    pr.bulan_pr AS "BULAN PR",
                    pr.pr_deletion_flag AS "PR Deletion Flag",
                    pr.pr_closed AS "PR Closed",
                    pr.bagian_pr AS "Bagian",
                    pri.line_item_pr AS "Line/Item PR",
                    pri.material_no AS "Material No",
                    pri.description AS "Description",
                    pri.quantity_pr AS "Quantity PR",
                    pri.satuan_pr AS "Satuan PR",
                    pri.estimasi_pr AS "Estimasi PR",
                    pri.currency_pr AS "Currency PR",
                    pri.pr_release_status AS "PR Release Status",
                    pri.tracking_no AS "Tracking No",
                    pri.cost_center AS "Cost Center",
                    pri.gl_account AS "GL Account",
                    pri.account_assignment AS "Account Assignment",
                    pri.contract_no AS "No Contract",
                    pri.contract_item AS "No Item Contract",
                    pri.e_proc AS "E-Proc",
                    pri.metode_pelelangan AS "Metode Pelelangan",
                    pri.inv_normal AS "INV/NORMAL",
                    pri.turn_around AS "turn around",
                    pri.pr_u AS "PR U",
                    pri.kontrak AS "KONTRAK",
                    pri.pupuk_organik AS "Pupuk Organik",
                    pri.batal AS "BATAL",
                    pri.source_determination_via AS "Source Determination Via",
                    pri.status_source_determination AS "Status Source Determination",
                    pri.first_full_release AS "1St Full Release",
                    poi.nomor_po AS "Nomor PO",
                    poi.item_po AS "Item PO",
                    poi.total_amount_local_curr AS "Total Amount in Local Curr",
                    poi.currency_po AS "Currency PO",
                    poi.qty_po AS "Qty PO",
                    poh.date_ordered AS "Date Ordered",
                    gr.tgl_terima_barang AS "Tgl Terima Barang",
                    gr.lead_time_process_po AS "Lead Time Process PO",
                    poh.po_status AS "PO Status",
                    v.vendor_name AS "Vendor Name",
                    poh.vendor_code AS "Vendor Code",
                    gr.tgl_qc_103 AS "Tgl QC(103)",
                    gr.tanggal_gr_103 AS "Tanggal GR103",
                    poi.nomor_dur AS "Nomor DUR",
                    poi.satuan_po AS "Satuan PO",
                    m.abc_indicator AS "ABC Indicator",
                    (SELECT MAX(release_date) FROM pr_release_history WHERE pr_item_id = pri.pr_item_id) AS "Tanggal Status Release Terakhir",
                    m.material_group AS "Material Group",
                    poi.total_amount AS "Total Amount",
                    poh.del_date_po AS "Del Date PO",
                    poi.total_item_po_net_price AS "Total Item PO/Net Price",
                    v.city AS "City",
                    v.vendor_account_group AS "Vendor Account Group",
                    poh.incoterm AS "Incoterm",
                    gr.service_acceptance AS "Service Acceptance",
                    gr.lead_time_delivery AS "Lead Time Delivery",
                    gr.status_supply AS "Status Supply",
                    (SELECT release_level FROM pr_release_history WHERE pr_item_id = pri.pr_item_id ORDER BY release_date DESC NULLS LAST LIMIT 1) AS "Status Release Terakhir",
                    poi.item_category AS "Item Category",
                    poi.tgl_penutupan_penawaran AS "Tgl Penutupan Penawaran",
                    poi.auction_date AS "Auction Date",
                    poi.tgl_pembukaan_penawaran AS "Tgl Pembukaan Penawaran",
                    poh.delivery_completed AS "Delivery Completed"
                FROM purchase_requisitions pr
                JOIN pr_items pri ON pr.pr_id = pri.pr_id
                LEFT JOIN po_items poi ON pri.pr_item_id = poi.pr_item_id
                LEFT JOIN purchase_orders poh ON poi.po_id = poh.po_id
                LEFT JOIN vendors v ON poh.vendor_code = v.vendor_code
                LEFT JOIN goods_receipt gr ON poi.po_item_id = gr.po_item_id
                LEFT JOIN materials m ON pri.material_no = m.material_no
                WHERE pr.tgl_create_pr >= '{start_str} 00:00:00' AND pr.tgl_create_pr <= '{end_str} 23:59:59'
                ORDER BY pr.tgl_create_pr DESC, pr.no_pr, pri.line_item_pr
                """
            elif jenis_data == "PO SAP":
                query = f"""
                SELECT 
                    po.nomor_po AS "Nomor PO",
                    po.date_ordered AS "Date Ordered",
                    po.vendor_code AS "Vendor Code",
                    v.vendor_name AS "Vendor Name",
                    v.vendor_account_group AS "Vendor Account Group",
                    v.city AS "City",
                    v.salesperson AS "Salesperson",
                    po.incoterm AS "Incoterm",
                    po.del_date_po AS "Del Date PO",
                    po.po_status AS "PO Status",
                    po.po_deletion_flag AS "PO Deletion Flag",
                    po.delivery_completed AS "Delivery Completed",
                    po.purchasing_group AS "Purchasing Group",
                    po.plant_code AS "Plant",
                    po.bulan_po AS "BULAN PO",
                    po.created_by AS "Created By",
                    po.buyer AS "BUYER",
                    po.our_reference AS "Our Reference",
                    po.your_reference AS "Your Reference",
                    po.bagian_po AS "Bagian",
                    poi.item_po AS "Item PO",
                    poi.no_pr AS "No PR",
                    poi.line_item_pr AS "Line/Item PR",
                    poi.department_code AS "Departement(Requisitioner)",
                    poi.material_no AS "Material No",
                    poi.description AS "Description",
                    m.material_group AS "Material Group",
                    m.abc_indicator AS "ABC Indicator",
                    poi.qty_po AS "Qty PO",
                    poi.satuan_po AS "Satuan PO",
                    poi.estimasi_pr AS "Estimasi PR",
                    poi.quantity_pr AS "Quantity PR",
                    poi.total_item_po_net_price AS "Total Item PO/Net Price",
                    poi.total_amount AS "Total Amount",
                    poi.total_amount_local_curr AS "Total Amount in Local Curr",
                    poi.currency_po AS "Currency PO",
                    poi.cost_center AS "Cost Center",
                    poi.gl_account AS "GL Account",
                    poi.account_assignment AS "Account Assignment",
                    poi.item_category AS "Item Category",
                    poi.contract_no AS "No Contract",
                    poi.contract_item AS "No Item Contract",
                    poi.no_rfq AS "No RFQ",
                    poi.rfq_item AS "RFQ Item",
                    poi.nomor_dur AS "Nomor DUR",
                    poi.metode_pelelangan AS "Metode Pelelangan",
                    poi.auction_date AS "Auction Date",
                    poi.tgl_penutupan_penawaran AS "Tgl Penutupan Penawaran",
                    poi.tgl_pembukaan_penawaran AS "Tgl Pembukaan Penawaran",
                    poi.oe AS "OE",
                    poi.efisiensi AS "EFISIENSI",
                    poi.efisiensi_persen AS "EFISIENSI%",
                    poi.status_pengiriman AS "Status Pengiriman",
                    poi.on_time_delivery AS "On Time Delivery",
                    poi.turn_around AS "Turn Around",
                    poi.invest AS "invest?",
                    poi.pupuk_organik AS "PUPUK PGNK",
                    poi.batal AS "L (batal)",
                    poi.kontrak AS "KONTRAK?",
                    poi.first_full_release AS "1St Full Release",
                    pri.satuan_pr AS "Satuan PR",
                    pri.currency_pr AS "Currency PR",
                    pr.tgl_create_pr AS "Tgl Create PR",
                    pri.tracking_no AS "Tracking No",
                    pri.pr_release_status AS "PR Release Status",
                    pr.mrp_controller AS "MRP Controller",
                    pri.e_proc AS "E-Proc",
                    gr.tgl_qc_103 AS "Tgl QC(103)",
                    gr.tanggal_gr_103 AS "Tanggal GR103",
                    gr.tgl_terima_barang AS "Tgl Terima Barang",
                    gr.service_acceptance AS "Service Acceptance",
                    gr.lead_time_process_po AS "Lead Time Process PO",
                    gr.lead_time_delivery AS "Lead Time Delivery",
                    gr.status_supply AS "Status Supply"
                FROM purchase_orders po
                JOIN po_items poi ON po.po_id = poi.po_id
                LEFT JOIN goods_receipt gr ON poi.po_item_id = gr.po_item_id
                LEFT JOIN vendors v ON po.vendor_code = v.vendor_code
                LEFT JOIN pr_items pri ON poi.pr_item_id = pri.pr_item_id
                LEFT JOIN purchase_requisitions pr ON pri.pr_id = pr.pr_id
                LEFT JOIN materials m ON poi.material_no = m.material_no
                WHERE po.date_ordered >= '{start_str} 00:00:00' AND po.date_ordered <= '{end_str} 23:59:59'
                ORDER BY po.date_ordered DESC, po.nomor_po, poi.item_po
                """
            elif jenis_data == "SIPS":
                query = f"""
                SELECT 
                    sd.nik AS "NIK",
                    sd.nama AS "Nama",
                    se.bagian AS "Bagian",
                    sd.no_pr AS "No PR",
                    sd.item_of AS "Item Of",
                    sd.status AS "Status",
                    sd.material_number AS "Material Number",
                    sd.short_text AS "Short Text",
                    sd.purchasing_group AS "Purchasing Group",
                    sd.requisition_date AS "Requisition Date",
                    sd.release_date AS "Release Date",
                    sd.tgl_disposisi_buyer AS "Tgl Disposisi Buyer",
                    sd.tgl_po AS "Tgl PO",
                    sd.requisitioner AS "Requisitioner",
                    sd.pr_po_days AS "PR-PO Days",
                    sd.no_po AS "No PO",
                    sd.prioritas AS "Prioritas",
                    sd.outline_agreement AS "Outline Agreement",
                    sd.kontrak_status AS "Kontrak Status",
                    sd.standar_sla AS "Standar SLA",
                    sd.realisasi_sla AS "Realisasi SLA",
                    sd.nilai_sla AS "Nilai SLA",
                    sd.nomor_mr_sr AS "Nomor MR/SR",
                    sd.nilai_mr_sr AS "Nilai MR/SR",
                    sd.oe_pr AS "OE PR",
                    sd.nilai_item_po AS "Nilai Item PO",
                    sd.persen_po_sr_mr AS "Persen PO/SR/MR",
                    sd.nilai_persen_po_sr_mr AS "Nilai Persen PO/SR/MR",
                    sd.bulan_dispo AS "Bulan Dispo"
                FROM sips_data sd
                LEFT JOIN sips_employees se ON sd.nik = se.nik
                WHERE sd.tgl_disposisi_buyer >= '{start_str}' AND sd.tgl_disposisi_buyer <= '{end_str}'
                ORDER BY sd.tgl_disposisi_buyer DESC
                """
            elif jenis_data == "Inklaring Barang Impor":
                query = f"""
                SELECT * FROM inklaring_impor 
                WHERE tgl_eta >= '{start_str}' AND tgl_eta <= '{end_str}'
                ORDER BY tgl_eta DESC
                """
            
            with st.spinner(f"Mengambil dan menyusun data {jenis_data}..."):
                try:
                    engine = _get_engine()
                    with engine.connect() as conn:
                        df_backup = pd.read_sql(text(query), conn)
                    
                    if df_backup.empty:
                        st.warning(f"Tidak ada data {jenis_data} pada periode yang dipilih.")
                    else:
                        buffer = io.BytesIO()
                        # Konversi datetime yang timezone-aware ke naive agar kompatibel dengan Excel (.xlsx)
                        for col in df_backup.select_dtypes(include=['datetime', 'datetimetz']).columns:
                            if getattr(df_backup[col].dt, 'tz', None) is not None:
                                df_backup[col] = df_backup[col].dt.tz_localize(None)

                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            df_backup.to_excel(writer, index=False, sheet_name=jenis_data[:30]) # max 31 char
                        
                        st.success(f"Berhasil menyiapkan {len(df_backup)} baris data!")
                        st.download_button(
                            label=f"Unduh File {jenis_data}.xlsx",
                            data=buffer.getvalue(),
                            file_name=f"Backup_{jenis_data.replace(' ', '_')}_{start_str}_{end_str}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            icon=":material/download:",
                            type="primary"
                        )
                except Exception as e:
                    st.error(f"Terjadi kesalahan saat menyiapkan backup: {e}")

    with col_kanan:
        st.markdown("""
            <h3 style='display: flex; align-items: center; font-size:18px; margin-bottom:12px; color:var(--text-color);'>
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" class="bi bi-box-arrow-up" viewBox="0 0 16 16" style="margin-bottom: 2px; margin-right: 8px;">
                    <path fill-rule="evenodd" d="M3.5 6a.5.5 0 0 0-.5.5v8a.5.5 0 0 0 .5.5h9a.5.5 0 0 0 .5-.5v-8a.5.5 0 0 0-.5-.5h-2a.5.5 0 0 1 0-1h2A1.5 1.5 0 0 1 14 6.5v8a1.5 1.5 0 0 1-1.5 1.5h-9A1.5 1.5 0 0 1 2 14.5v-8A1.5 1.5 0 0 1 3.5 5h2a.5.5 0 0 1 0 1z"/>
                    <path fill-rule="evenodd" d="M7.646.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1-.708.708L8.5 1.707V10.5a.5.5 0 0 1-1 0V1.707L5.354 3.854a.5.5 0 1 1-.708-.708z"/>
                </svg>
                Upload / Update Data Baru
            </h3>
        """, unsafe_allow_html=True)
        
        tipe_etl = st.selectbox("Pilih Modul ETL", ["SAP (PR & PO)", "SIPS", "Inklaring Barang Impor"])
        
        if tipe_etl == "SAP (PR & PO)":
            file_pr = st.file_uploader("Upload File PR SAP (.xlsx)", type=["xlsx"])
            file_po = st.file_uploader("Upload File PO SAP (.xlsx)", type=["xlsx"])
            update_tgl_sap = st.checkbox("Update Tanggal Data Menjadi Hari Ini", value=False, key="chk_sap")
            if file_pr and file_po:
                if st.button("Jalankan ETL SAP", type="primary", icon=":material/cloud_upload:"):
                    # Simpan sementara ke sistem lokal agar dapat dibaca library openpyxl
                    pr_path, po_path = "temp_pr_sap.xlsx", "temp_po_sap.xlsx"
                    with open(pr_path, "wb") as f: f.write(file_pr.getbuffer())
                    with open(po_path, "wb") as f: f.write(file_po.getbuffer())
                    
                    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../ETL')))
                    import etl_sap_to_postgres as etl_sap  # type: ignore
                    
                    etl_sap.Config.PR_FILE = pr_path
                    etl_sap.Config.PO_FILE = po_path
                    etl_sap.get_db_engine  = _get_engine  # Override koneksi db menggunakan versi dashboard yang rahasia
                    
                    terminal = st.empty()
                    capture_sap = StreamlitCapture(terminal)
                    with redirect_stdout(capture_sap), redirect_stderr(capture_sap):
                        etl_sap.run_etl()
                        capture_sap.flush()
                    
                    os.remove(pr_path)
                    os.remove(po_path)

                    if update_tgl_sap:
                        set_setting("DATA_UPDATE_SAP", datetime.today().strftime("%Y-%m-%d"))
                    st.success("Proses sinkronisasi SAP selesai!, tekan tombol Refresh Data agar data terbaru muncul di dashboard.")
                    
        elif tipe_etl == "SIPS":
            file_sips = st.file_uploader("Upload File SIPS (.xlsx)", type=["xlsx"])
            update_tgl_sips = st.checkbox("Update Tanggal Data Menjadi Hari Ini", value=False, key="chk_sips")
            if file_sips:
                if st.button("Jalankan ETL SIPS", type="primary", icon=":material/cloud_upload:"):
                    sips_path = "temp_sips.xlsx"
                    with open(sips_path, "wb") as f: f.write(file_sips.getbuffer())
                    
                    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../ETL')))
                    import etl_sips  # type: ignore
                    
                    etl_sips.Config.SIPS_FILE = sips_path
                    etl_sips.Config.PERIODE_IMPORT = []  # Bypass filter bulan di config asli agar semua data di file masuk
                    etl_sips.db_get_engine = _get_engine
                    
                    terminal = st.empty()
                    capture_sips = StreamlitCapture(terminal)
                    with redirect_stdout(capture_sips), redirect_stderr(capture_sips):
                        etl_sips.run_etl()
                        capture_sips.flush()
                        
                    os.remove(sips_path)
                    
                    if update_tgl_sips:
                        set_setting("DATA_UPDATE_SIPS", datetime.today().strftime("%Y-%m-%d"))
                    st.success("Proses sinkronisasi SIPS selesai!, tekan tombol Refresh Data agar data terbaru muncul di dashboard.")
        
        elif tipe_etl == "Inklaring Barang Impor":
            file_inklaring = st.file_uploader("Upload File Inklaring (.csv / .xlsx)", type=["csv", "xlsx"])
            update_tgl_inklaring = st.checkbox("Update Tanggal Data Menjadi Hari Ini", value=False, key="chk_inklaring")
            if file_inklaring:
                if st.button("Jalankan ETL Inklaring", type="primary", icon=":material/cloud_upload:"):
                    with st.spinner("Sedang memproses dan menyimpan data ke database..."):
                        try:
                            file_inklaring.seek(0)
                            if file_inklaring.name.endswith('.csv'):
                                df = pd.read_csv(file_inklaring)
                            else:
                                df = pd.read_excel(file_inklaring)
                            
                            column_mapping = {
                                "Tgl PIB": "tgl_pib", "AJU PIB": "aju_pib", "NO AJU": "no_aju",
                                "SAP": "sap", "LN": "ln", "NAMA KAPAL": "nama_kapal",
                                "Tgl ETA": "tgl_eta", "QUANTITY (MT)": "quantity_mt", "PEMASOK": "pemasok",
                                "PENGIRIM": "pengirim", "AGENT": "agent", "KOMODITI": "komoditi",
                                "ASAL NEGARA": "asal_negara", "Port of Load": "port_of_load", "HS": "hs_code",
                                "Bea Masuk (Rp)": "bea_masuk_rp", "PPN": "ppn_rp", "PPH": "pph_rp",
                                "BM % ": "bm_persen", "GUDANG TIMBUN": "gudang_timbun", "INVOICE": "invoice",
                                "Kurs": "kurs", "SKEP BC": "skep_bc", "START BONGKAR": "start_bongkar",
                                "SELESAI BONGKAR": "selesai_bongkar", "PPJK": "ppjk", "SPJM": "spjm",
                                "AMBIL SAMPEL": "ambil_sampel", "No Pen PIB": "no_pen_pib", 
                                "Tgl No Pen PIB": "tgl_no_pen_pib", "No S P P B": "no_sppb", 
                                "Tgl SPPB": "tgl_sppb", "STATUS": "status", "NO SPTNP": "no_sptnp",
                                "Tgl SPTNP": "tgl_sptnp", "NILAI SPTNP": "nilai_sptnp"
                            }
                            
                            df_clean = df[list(column_mapping.keys())].rename(columns=column_mapping)
                            kolom_teks = ['sap', 'no_aju', 'ln']
                            for col in kolom_teks:
                                df_clean[col] = df_clean[col].astype(str).str.replace(r'\.0$', '', regex=True)
                                df_clean[col] = df_clean[col].replace({'nan': None, 'NaN': None, 'None': None})
                            
                            df_clean['aju_pib'] = df_clean['aju_pib'].fillna(
                                'TEMP-' + df_clean['sap'].astype(str) + '-' + df_clean['no_aju'].astype(str)
                            )

                            date_columns = ['tgl_pib', 'tgl_eta', 'tgl_no_pen_pib', 'tgl_sppb', 'tgl_sptnp', 'start_bongkar', 'selesai_bongkar']
                            numeric_columns = ['quantity_mt', 'bea_masuk_rp', 'ppn_rp', 'pph_rp', 'bm_persen', 'kurs', 'nilai_sptnp']

                            for col in date_columns:
                                df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce')

                            for col in numeric_columns:
                                if df_clean[col].dtype == 'object':
                                    df_clean[col] = df_clean[col].astype(str).str.replace(r'[\.,]00$', '', regex=True)
                                    df_clean[col] = df_clean[col].str.replace(r'[,\.]', '', regex=True)
                                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

                            df_clean = df_clean.replace({np.nan: None, 'NaT': None})
                            df_clean = df_clean.drop_duplicates(subset=['aju_pib'], keep='last')
                            
                            engine = _get_engine()
                            with engine.begin() as conn:
                                df_clean.to_sql('temp_inklaring', conn, if_exists='replace', index=False)
                                
                                columns = list(df_clean.columns)
                                set_clause = ", ".join([f"{col} = EXCLUDED.{col}" for col in columns if col != 'aju_pib'])
                                
                                select_clause_items = []
                                for col in columns:
                                    if col in numeric_columns:
                                        select_clause_items.append(f"CAST({col} AS NUMERIC)")
                                    elif col in date_columns:
                                        select_clause_items.append(f"CAST({col} AS TIMESTAMP)")
                                    else:
                                        select_clause_items.append(col)
                                        
                                select_clause = ", ".join(select_clause_items)
                                
                                upsert_query = f"""
                                    INSERT INTO inklaring_impor ({', '.join(columns)})
                                    SELECT {select_clause} FROM temp_inklaring
                                    ON CONFLICT (aju_pib) DO UPDATE SET {set_clause};
                                """
                                conn.execute(text(upsert_query))
                                conn.execute(text("DROP TABLE temp_inklaring;"))
                                
                            if update_tgl_inklaring:
                                set_setting("DATA_UPDATE_INKLARING", datetime.today().strftime("%Y-%m-%d"))
                            st.success(f"🎉 Berhasil menyimpan {len(df_clean)} data Inklaring ke database!")
                            st.cache_data.clear()
                            
                        except Exception as e:
                            st.error(f"Gagal memproses data Inklaring: {e}")

    # == Bagian 3: Zona Berbahaya (Reset Data) =================================
    st.markdown("<hr style='margin: 32px 0 24px 0; border-color: rgba(128,128,128,0.2);'>", unsafe_allow_html=True)
    
    st.markdown("""
        <h3 style='display: flex; align-items: center; font-size:18px; margin-bottom:12px; color:#ff4b4b;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" class="bi bi-exclamation-triangle" viewBox="0 0 16 16" style="margin-bottom: 2px; margin-right: 8px;">
                <path d="M7.938 2.016A.13.13 0 0 1 8.002 2a.13.13 0 0 1 .063.016.15.15 0 0 1 .054.057l6.857 11.667c.036.06.035.124.002.183a.2.2 0 0 1-.054.06.1.1 0 0 1-.066.017H1.146a.1.1 0 0 1-.066-.017.2.2 0 0 1-.054-.06.18.18 0 0 1 .002-.183L7.884 2.073a.15.15 0 0 1 .054-.057zm1.044-.45a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767z"/>
                <path d="M7.002 12a1 1 0 1 1 2 0 1 1 0 0 1-2 0zM7.1 5.995a.905.905 0 1 1 1.8 0l-.35 3.507a.552.552 0 0 1-1.1 0z"/>
            </svg>
            Zona Berbahaya (Reset Data)
        </h3>
    """, unsafe_allow_html=True)
    
    st.warning("Fitur ini akan menghapus seluruh data transaksi dari database secara permanen. Gunakan hanya jika Anda perlu mengulang proses upload (ETL) dari awal atau membersihkan data yang salah.")
    
    col_del1, col_del2, col_del3 = st.columns(3)
    
    with col_del1:
        with st.expander("🗑️ Hapus Data SAP"):
            st.write("Tindakan ini akan menghapus semua data Purchase Requisition, Purchase Order, Goods Receipt, dan riwayat status rilis. (Data Master seperti Vendor dan Material akan tetap aman).")
            confirm_sap = st.checkbox("Saya yakin (SAP)", key="confirm_sap")
            if st.button("Hapus Data SAP", type="primary", disabled=not confirm_sap, use_container_width=True):
                with st.spinner("Menghapus data SAP..."):
                    try:
                        engine = _get_engine()
                        with engine.begin() as conn:
                            conn.execute(text("TRUNCATE TABLE purchase_requisitions, purchase_orders CASCADE;"))
                        st.success("Data SAP berhasil dikosongkan! Halaman akan dimuat ulang...")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menghapus data: {e}")

    with col_del2:
        with st.expander("🗑️ Hapus Data SIPS"):
            st.write("Tindakan ini akan menghapus semua riwayat transaksi SIPS dan data karyawan SIPS dari database.")
            confirm_sips = st.checkbox("Saya yakin (SIPS)", key="confirm_sips")
            if st.button("Hapus Data SIPS", type="primary", disabled=not confirm_sips, use_container_width=True):
                with st.spinner("Menghapus data SIPS..."):
                    try:
                        engine = _get_engine()
                        with engine.begin() as conn:
                            conn.execute(text("TRUNCATE TABLE sips_data, sips_employees CASCADE;"))
                        st.success("Data SIPS berhasil dikosongkan! Halaman akan dimuat ulang...")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menghapus data: {e}")

    with col_del3:
        with st.expander("🗑️ Hapus Data Inklaring"):
            st.write("Tindakan ini akan mengosongkan seluruh tabel Inklaring Barang Impor.")
            confirm_inklaring = st.checkbox("Saya yakin (Inklaring)", key="confirm_inklaring")
            if st.button("Hapus Inklaring", type="primary", disabled=not confirm_inklaring, use_container_width=True):
                with st.spinner("Menghapus data Inklaring..."):
                    try:
                        engine = _get_engine()
                        with engine.begin() as conn:
                            conn.execute(text("TRUNCATE TABLE inklaring_impor RESTART IDENTITY CASCADE;"))
                        st.success("Data Inklaring berhasil dikosongkan! Halaman akan dimuat ulang...")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menghapus data: {e}")