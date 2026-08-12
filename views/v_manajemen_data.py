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
    """Menangkap output terminal dengan efisien, mengabaikan spam dari tqdm."""
    def __init__(self, placeholder):
        self.placeholder = placeholder
        self.lines = []
        self.buffer = ""
        self.last_update = time.time()
        
    def write(self, text):
        # Abaikan output dari tqdm yang menggunakan \r (carriage return)
        if '\r' in text:
            return  
            
        self.buffer += text
        
        # Jika ada baris baru, pisahkan dan masukkan ke daftar baris
        if '\n' in self.buffer:
            parts = self.buffer.split('\n')
            self.lines.extend(parts[:-1])  
            self.buffer = parts[-1]        
            
        # Refresh UI max 1 detik sekali
        if time.time() - self.last_update > 1.0:
            self.flush()
            
    def flush(self):
        if not self.lines and not self.buffer:
            return
            
        # Tampilkan maksimal 25 baris terakhir agar UI tidak berat
        display_lines = self.lines[-25:] 
        if self.buffer:
            display_lines.append(self.buffer)
            
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
        "Pusat kendali sinkronisasi data SAP, SIPS, Inklaring, Harga Bahan Baku, dan manajemen backup sistem."
        "</p>", 
        unsafe_allow_html=True
    )

    from config_db import get_setting, set_setting

    sap_date_str = get_setting("DATA_UPDATE_SAP", "2026-03-31")
    sips_date_str = get_setting("DATA_UPDATE_SIPS", "2026-03-31")
    inklaring_date_str = get_setting("DATA_UPDATE_INKLARING", "2026-03-31")
    bahan_baku_date_str = get_setting("DATA_UPDATE_BAHAN_BAKU", "2026-03-31")

    try: DATA_UPDATE_SAP = datetime.strptime(sap_date_str, "%Y-%m-%d").date()
    except: DATA_UPDATE_SAP = datetime(2026, 3, 31).date()
        
    try: DATA_UPDATE_SIPS = datetime.strptime(sips_date_str, "%Y-%m-%d").date()
    except: DATA_UPDATE_SIPS = datetime(2026, 3, 31).date()

    try: DATA_UPDATE_INKLARING = datetime.strptime(inklaring_date_str, "%Y-%m-%d").date()
    except: DATA_UPDATE_INKLARING = datetime(2026, 3, 31).date()
    
    try: DATA_UPDATE_BAHAN_BAKU = datetime.strptime(bahan_baku_date_str, "%Y-%m-%d").date()
    except: DATA_UPDATE_BAHAN_BAKU = datetime(2026, 3, 31).date()

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
    
    col_sap, col_sips, col_inklaring, col_bb = st.columns(4)
    
    with col_sap:
        st.markdown(f"""
            <div style='background: var(--secondary-background-color); border: 1px solid rgba(31, 119, 180, 0.3); border-radius: 10px; padding: 16px; border-left: 5px solid #1f77b4;'>
                <p style='margin: 0; font-size: 13px; opacity: 0.7; font-weight: 600;'>Database PR-PO SAP</p>
                <h4 style='margin: 4px 0 0 0; font-size: 20px;'>{DATA_UPDATE_SAP.strftime('%d %b %Y')}</h4>
            </div>
        """, unsafe_allow_html=True)

    with col_sips:
        st.markdown(f"""
            <div style='background: var(--secondary-background-color); border: 1px solid rgba(255, 75, 75, 0.3); border-radius: 10px; padding: 16px; border-left: 5px solid #ff4b4b;'>
                <p style='margin: 0; font-size: 13px; opacity: 0.7; font-weight: 600;'>Database SIPS</p>
                <h4 style='margin: 4px 0 0 0; font-size: 20px;'>{DATA_UPDATE_SIPS.strftime('%d %b %Y')}</h4>
            </div>
        """, unsafe_allow_html=True)

    with col_inklaring:
        st.markdown(f"""
            <div style='background: var(--secondary-background-color); border: 1px solid rgba(44, 160, 44, 0.3); border-radius: 10px; padding: 16px; border-left: 5px solid #2ca02c;'>
                <p style='margin: 0; font-size: 13px; opacity: 0.7; font-weight: 600;'>Database Inklaring</p>
                <h4 style='margin: 4px 0 0 0; font-size: 20px;'>{DATA_UPDATE_INKLARING.strftime('%d %b %Y')}</h4>
            </div>
        """, unsafe_allow_html=True)
        
    with col_bb:
        st.markdown(f"""
            <div style='background: var(--secondary-background-color); border: 1px solid rgba(148, 103, 189, 0.3); border-radius: 10px; padding: 16px; border-left: 5px solid #9467bd;'>
                <p style='margin: 0; font-size: 13px; opacity: 0.7; font-weight: 600;'>Harga Bahan Baku</p>
                <h4 style='margin: 4px 0 0 0; font-size: 20px;'>{DATA_UPDATE_BAHAN_BAKU.strftime('%d %b %Y')}</h4>
            </div>
        """, unsafe_allow_html=True)

    with st.expander("Edit Manual Tanggal Pembaruan", icon=":material/edit:"):
        with st.form("form_edit_tanggal"):
            c1, c2, c3, c4 = st.columns(4)
            with c1: new_sap_date = st.date_input("Update SAP", DATA_UPDATE_SAP)
            with c2: new_sips_date = st.date_input("Update SIPS", DATA_UPDATE_SIPS)
            with c3: new_inklaring_date = st.date_input("Update Inklaring", DATA_UPDATE_INKLARING)
            with c4: new_bb_date = st.date_input("Update Harga BB", DATA_UPDATE_BAHAN_BAKU)
            
            if st.form_submit_button("Simpan Perubahan"):
                set_setting("DATA_UPDATE_SAP", new_sap_date.strftime("%Y-%m-%d"))
                set_setting("DATA_UPDATE_SIPS", new_sips_date.strftime("%Y-%m-%d"))
                set_setting("DATA_UPDATE_INKLARING", new_inklaring_date.strftime("%Y-%m-%d"))
                set_setting("DATA_UPDATE_BAHAN_BAKU", new_bb_date.strftime("%Y-%m-%d"))
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
            jenis_data = st.selectbox("Jenis Data", ["PR SAP", "PO SAP", "SIPS", "Inklaring Barang Impor", "Harga Bahan Baku"])
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
            elif jenis_data == "Harga Bahan Baku":
                query = f"""
                SELECT * FROM master_harga_bahan_baku 
                WHERE tanggal_terbit >= '{start_str}' AND tanggal_terbit <= '{end_str}'
                ORDER BY tanggal_terbit DESC, bahan_baku ASC, nama_majalah ASC
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
                            type="primary",
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
        
        tipe_etl = st.selectbox(
            "Pilih Modul ETL", 
            ["SAP (PR & PO)", "SIPS", "SAP + SIPS (1 File)", "Inklaring Barang Impor", "EPROC (Utilisasi)", "Harga Bahan Baku", "Kondisi Stock BB"]
        )

        if tipe_etl == "SAP (PR & PO)":
            file_sap = st.file_uploader("Upload File SAP (.xlsx) — harus ada sheet 'PR SAP' dan 'PO SAP'", type=["xlsx"])
            update_tgl_sap = st.checkbox("Update Tanggal Data Menjadi Hari Ini", value=False, key="chk_sap")
            if file_sap:
                if st.button("Jalankan ETL SAP", type="primary", icon=":material/cloud_upload:"):
                    sap_path = "temp_sap.xlsx"
                    with open(sap_path, "wb") as f: f.write(file_sap.getbuffer())

                    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../ETL')))
                    import etl_sap as etl_sap  # type: ignore

                    etl_sap.Config.SAP_FILE  = sap_path
                    etl_sap.Config.PR_SHEET  = 'PR SAP'
                    etl_sap.Config.PO_SHEET  = 'PO SAP'
                    etl_sap.get_db_engine    = _get_engine

                    terminal = st.empty()
                    capture_sap = StreamlitCapture(terminal)
                    with redirect_stdout(capture_sap), redirect_stderr(capture_sap):
                        etl_sap.run_etl()
                        capture_sap.flush()

                    os.remove(sap_path)
                    if update_tgl_sap:
                        set_setting("DATA_UPDATE_SAP", datetime.today().strftime("%Y-%m-%d"))
                    st.success("Proses sinkronisasi SAP selesai!")

        elif tipe_etl == "SAP + SIPS (1 File)":
            file_gabung = st.file_uploader(
                "Upload File Excel Gabungan (.xlsx) — harus ada sheet: 'PR SAP', 'PO SAP', 'SIPS'",
                type=["xlsx"]
            )
            update_tgl_sap  = st.checkbox("Update Tanggal SAP Menjadi Hari Ini",  value=False, key="chk_sap2")
            update_tgl_sips = st.checkbox("Update Tanggal SIPS Menjadi Hari Ini", value=False, key="chk_sips2")

            if file_gabung:
                try:
                    xl = pd.ExcelFile(file_gabung)
                    sheets_ada = xl.sheet_names
                    sheets_wajib = ['PR SAP', 'PO SAP', 'SIPS']
                    sheets_kurang = [s for s in sheets_wajib if s not in sheets_ada]
                    if sheets_kurang:
                        st.error(f"❌ Sheet tidak ditemukan di file: {', '.join(sheets_kurang)}")
                    else:
                        st.success(f"✅ Sheet ditemukan: {', '.join(sheets_wajib)}")
                except Exception as e:
                    st.error(f"Gagal membaca file: {e}")
                    sheets_kurang = ['error']

                if not sheets_kurang and st.button("Jalankan ETL SAP + SIPS", type="primary", icon=":material/cloud_upload:"):
                    gabung_path = "temp_gabung.xlsx"
                    with open(gabung_path, "wb") as f: f.write(file_gabung.getbuffer())

                    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../ETL')))
                    import etl_sap as etl_sap    # type: ignore
                    import etl_sips              # type: ignore

                    # --- ETL SAP ---
                    etl_sap.Config.SAP_FILE  = gabung_path
                    etl_sap.Config.PR_SHEET  = 'PR SAP'
                    etl_sap.Config.PO_SHEET  = 'PO SAP'
                    etl_sap.get_db_engine    = _get_engine

                    terminal = st.empty()
                    capture = StreamlitCapture(terminal)
                    with redirect_stdout(capture), redirect_stderr(capture):
                        etl_sap.run_etl()
                        capture.flush()

                    # --- ETL SIPS ---
                    etl_sips.Config.SIPS_FILE      = gabung_path
                    etl_sips.Config.SIPS_SHEET     = 'SIPS'
                    etl_sips.Config.PERIODE_IMPORT = []
                    etl_sips.db_get_engine         = _get_engine

                    with redirect_stdout(capture), redirect_stderr(capture):
                        etl_sips.run_etl()
                        capture.flush()

                    os.remove(gabung_path)
                    if update_tgl_sap:
                        set_setting("DATA_UPDATE_SAP",  datetime.today().strftime("%Y-%m-%d"))
                    if update_tgl_sips:
                        set_setting("DATA_UPDATE_SIPS", datetime.today().strftime("%Y-%m-%d"))
                    st.success("Proses sinkronisasi SAP + SIPS selesai!")

        elif tipe_etl == "SIPS":

            # 1. FUNGSI HELPER (mengikuti pola Inklaring / Harga Bahan Baku)
            def _jalankan_etl_sips(file_path, update_tanggal):
                sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../ETL')))
                import etl_sips  # type: ignore

                etl_sips.Config.SIPS_FILE      = file_path
                etl_sips.Config.SIPS_SHEET     = 'SIPS'
                etl_sips.Config.PERIODE_IMPORT = []
                etl_sips.db_get_engine         = _get_engine

                terminal = st.empty()
                capture_sips = StreamlitCapture(terminal)
                with redirect_stdout(capture_sips), redirect_stderr(capture_sips):
                    try:
                        etl_sips.run_etl()
                        capture_sips.flush()

                        if update_tanggal:
                            set_setting("DATA_UPDATE_SIPS", datetime.today().strftime("%Y-%m-%d"))

                        st.success("Proses sinkronisasi SIPS selesai! Tekan tombol Refresh Data agar data terbaru muncul di dashboard.")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Gagal memproses data SIPS: {e}")
                    finally:
                        if os.path.exists(file_path):
                            os.remove(file_path)

            # 2. LOGIKA ANTARMUKA / UI MODUL SIPS
            metode_input = st.radio("Metode Input Data SIPS", ["Upload File Manual", "Tarik Langsung dari Google Sheets"], horizontal=True, key="rad_sips")
            update_tgl_sips = st.checkbox("Update Tanggal Data Menjadi Hari Ini", value=False, key="chk_sips")

            if metode_input == "Upload File Manual":
                file_sips = st.file_uploader("Upload File SIPS (.xlsx)", type=["xlsx"])
                if file_sips:
                    if st.button("Jalankan ETL SIPS", type="primary", icon=":material/cloud_upload:"):
                        sips_path = "temp_sips.xlsx"
                        with open(sips_path, "wb") as f:
                            f.write(file_sips.getbuffer())

                        _jalankan_etl_sips(sips_path, update_tgl_sips)

            else:
                # Opsi Tarik dari Google Sheets
                st.info("Pastikan Google Sheet memiliki akses 'Anyone with the link can view' agar sistem bisa mengunduhnya.")

                sheet_id_sips = st.text_input(
                    "ID Google Sheet (SIPS)",
                    value="15v05LiVAp2kbus90Lf_uyfVc0EkwTHQMRs8JvP6vT9Q",
                    placeholder="Contoh: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                    key="txt_sheet_sips"
                )

                if st.button("Tarik Data & Jalankan ETL SIPS", type="primary", icon=":material/cloud_download:"):
                    if not sheet_id_sips:
                        st.error("Masukkan ID Google Sheet terlebih dahulu!")
                    else:
                        with st.spinner("Mengunduh data SIPS dari Google Sheets..."):
                            import requests
                            try:
                                export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id_sips}/export?format=xlsx"
                                response = requests.get(export_url)

                                if response.status_code == 200:
                                    sips_path = "temp_sips_gsheet.xlsx"
                                    with open(sips_path, "wb") as f:
                                        f.write(response.content)

                                    st.success("File SIPS berhasil diunduh. Memulai proses ETL...")
                                    _jalankan_etl_sips(sips_path, update_tgl_sips)
                                else:
                                    st.error(f"Gagal mengunduh file. Status code: {response.status_code}. Pastikan ID benar dan akses terbuka.")
                            except Exception as e:
                                st.error(f"Terjadi kesalahan saat mengunduh: {e}")

        elif tipe_etl == "Inklaring Barang Impor":
            # 1. PINDAHKAN FUNGSI HELPER KE SINI (KE ATAS) agar terhindar dari scope error
            def _jalankan_etl_inklaring(file_path, update_tanggal):
                sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../ETL')))
                import etl_inklaring # type: ignore
                
                etl_inklaring.Config.INKLARING_FILE = file_path
                etl_inklaring.db_get_engine = _get_engine
                
                terminal = st.empty()
                capture_inklaring = StreamlitCapture(terminal)
                with redirect_stdout(capture_inklaring), redirect_stderr(capture_inklaring):
                    try:
                        sukses = etl_inklaring.run_etl()
                        capture_inklaring.flush()
                        
                        if sukses:
                            if update_tanggal:
                                set_setting("DATA_UPDATE_INKLARING", datetime.today().strftime("%Y-%m-%d"))
                            st.success("Proses sinkronisasi Inklaring selesai! Tekan tombol Refresh Data agar data terbaru muncul di dashboard.")
                            st.cache_data.clear()
                        else:
                            st.error("Proses ETL Inklaring gagal, periksa terminal di atas.")
                    except Exception as e:
                        st.error(f"Gagal memproses data Inklaring: {e}")
                    finally:
                        if os.path.exists(file_path):
                            os.remove(file_path)

            # 2. LOGIKA ANTARMUKA / UI MODUL INKLARING
            metode_input = st.radio("Metode Input Data Inklaring", ["Upload File Manual", "Tarik Langsung dari Google Sheets"], horizontal=True, key="rad_inklaring")
            update_tgl_inklaring = st.checkbox("Update Tanggal Data Menjadi Hari Ini", value=False, key="chk_inklaring")
            
            if metode_input == "Upload File Manual":
                file_inklaring = st.file_uploader("Upload File Inklaring (.csv / .xlsx)", type=["csv", "xlsx"])
                if file_inklaring:
                    if st.button("Jalankan ETL Inklaring", type="primary", icon=":material/cloud_upload:"):
                        ext = ".csv" if file_inklaring.name.endswith(".csv") else ".xlsx"
                        inklaring_path = f"temp_inklaring_upload{ext}"
                        with open(inklaring_path, "wb") as f:
                            f.write(file_inklaring.getbuffer())
                            
                        _jalankan_etl_inklaring(inklaring_path, update_tgl_inklaring)
            
            else:
                # Opsi Tarik dari Google Sheets
                st.info("Pastikan Google Sheet memiliki akses 'Anyone with the link can view' agar sistem bisa mengunduhnya.")
                
                # Masukkan ID default Google Sheet untuk Inklaring jika ada, atau biarkan kosong seperti di bawah
                sheet_id_inklaring = st.text_input(
                    "ID Google Sheet (Inklaring)", 
                    value="1MD8RCYEeY_VC_NHjNfxiNKOTWyTNdgJscJL_thOZVtQ",  # Ganti dengan ID Google Sheet Inklaring jika berbeda
                    placeholder="Contoh: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                    key="txt_sheet_inklaring"
                )
                
                if st.button("Tarik Data & Jalankan ETL Inklaring", type="primary", icon=":material/cloud_download:"):
                    if not sheet_id_inklaring:
                        st.error("Masukkan ID Google Sheet terlebih dahulu!")
                    else:
                        with st.spinner("Mengunduh data Inklaring dari Google Sheets..."):
                            import requests
                            try:
                                # Mengunduh langsung dalam format Excel .xlsx agar parsing column header lebih konsisten
                                export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id_inklaring}/export?format=xlsx"
                                response = requests.get(export_url)
                                
                                if response.status_code == 200:
                                    # Simpan dengan ekstensi .xlsx agar dibaca oleh pd.read_excel di etl_inklaring.py
                                    inklaring_path = "temp_inklaring_gsheet.xlsx"
                                    with open(inklaring_path, "wb") as f:
                                        f.write(response.content)
                                    
                                    st.success("File Inklaring berhasil diunduh. Memulai proses ETL...")
                                    _jalankan_etl_inklaring(inklaring_path, update_tgl_inklaring)
                                else:
                                    st.error(f"Gagal mengunduh file. Status code: {response.status_code}. Pastikan ID benar dan akses terbuka.")
                            except Exception as e:
                                st.error(f"Terjadi kesalahan saat mengunduh: {e}")

        elif tipe_etl == "EPROC (Utilisasi)":

            # 1. FUNGSI HELPER
            def _jalankan_etl_eproc(file_path):
                sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../ETL')))
                import etl_eproc  # type: ignore

                etl_eproc.Config.EPROC_FILE = file_path
                etl_eproc.db_get_engine = _get_engine

                terminal = st.empty()
                capture_eproc = StreamlitCapture(terminal)
                with redirect_stdout(capture_eproc), redirect_stderr(capture_eproc):
                    try:
                        sukses = etl_eproc.run_etl()
                        capture_eproc.flush()

                        if sukses:
                            st.success("✅ Proses unggah data EPROC selesai! Cek Dashboard Summary untuk melihat perubahannya.")
                            st.cache_data.clear()
                        else:
                            st.error("❌ Proses gagal, silakan periksa log terminal di atas.")
                    except Exception as e:
                        st.error(f"Gagal memproses data EPROC: {e}")
                    finally:
                        if os.path.exists(file_path):
                            os.remove(file_path)

            # 2. LOGIKA ANTARMUKA / UI MODUL EPROC
            metode_input = st.radio("Metode Input Data EPROC", ["Upload File Manual", "Tarik Langsung dari Google Sheets"], horizontal=True, key="rad_eproc")

            if metode_input == "Upload File Manual":
                file_eproc = st.file_uploader("Upload File EPROC (.xlsx) — harus ada sheet 'EPROC'", type=["xlsx"])
                if file_eproc:
                    if st.button("Jalankan ETL EPROC", type="primary", icon=":material/cloud_upload:"):
                        eproc_path = "temp_eproc.xlsx"
                        with open(eproc_path, "wb") as f:
                            f.write(file_eproc.getbuffer())

                        _jalankan_etl_eproc(eproc_path)

            else:
                # Opsi Tarik dari Google Sheets
                st.info("Pastikan Google Sheet memiliki akses 'Anyone with the link can view' agar sistem bisa mengunduhnya.")

                sheet_id_eproc = st.text_input(
                    "ID Google Sheet (EPROC)",
                    value="15v05LiVAp2kbus90Lf_uyfVc0EkwTHQMRs8JvP6vT9Q",
                    placeholder="Contoh: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                    key="txt_sheet_eproc"
                )

                if st.button("Tarik Data & Jalankan ETL EPROC", type="primary", icon=":material/cloud_download:"):
                    if not sheet_id_eproc:
                        st.error("Masukkan ID Google Sheet terlebih dahulu!")
                    else:
                        with st.spinner("Mengunduh data EPROC dari Google Sheets..."):
                            import requests
                            try:
                                export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id_eproc}/export?format=xlsx"
                                response = requests.get(export_url)

                                if response.status_code == 200:
                                    eproc_path = "temp_eproc_gsheet.xlsx"
                                    with open(eproc_path, "wb") as f:
                                        f.write(response.content)

                                    st.success("File EPROC berhasil diunduh. Memulai proses ETL...")
                                    _jalankan_etl_eproc(eproc_path)
                                else:
                                    st.error(f"Gagal mengunduh file. Status code: {response.status_code}. Pastikan ID benar dan akses terbuka.")
                            except Exception as e:
                                st.error(f"Terjadi kesalahan saat mengunduh: {e}")

        elif tipe_etl == "Harga Bahan Baku":
            
            # 1. PINDAHKAN FUNGSI HELPER KE SINI (KE ATAS)
            def _jalankan_etl_bahan_baku(file_path, update_tanggal):
                sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../ETL')))
                import etl_harga_bahan_baku as etl_bb # type: ignore

                etl_bb.Config.EXCEL_FILE = file_path
                etl_bb.db_get_engine = _get_engine

                terminal = st.empty()
                capture_bb = StreamlitCapture(terminal)
                with redirect_stdout(capture_bb), redirect_stderr(capture_bb):
                    try:
                        etl_bb.run_etl()
                        capture_bb.flush()
                        
                        if update_tanggal:
                            set_setting("DATA_UPDATE_BAHAN_BAKU", datetime.today().strftime("%Y-%m-%d"))
                        
                        st.success("Proses sinkronisasi Harga Bahan Baku selesai! Tekan tombol Refresh Data agar data terbaru muncul.")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Gagal memproses data Harga Bahan Baku: {e}")
                    finally:
                        if os.path.exists(file_path):
                            os.remove(file_path)

            # 2. BARU SETELAH ITU LOGIKA UI-NYA
            metode_input = st.radio("Metode Input Data", ["Upload File Manual", "Tarik Langsung dari Google Sheets"], horizontal=True, key="rad_bb")
            update_tgl_bahan_baku = st.checkbox("Update Tanggal Data Menjadi Hari Ini", value=False, key="chk_bahan_baku")
            
            if metode_input == "Upload File Manual":
                file_bahan_baku = st.file_uploader("Upload File Rekapan Majalah (.xlsx)", type=["xlsx"])
                if file_bahan_baku:
                    if st.button("Jalankan ETL Harga Bahan Baku", type="primary", icon=":material/cloud_upload:"):
                        bb_path = "temp_bahan_baku.xlsx"
                        with open(bb_path, "wb") as f: 
                            f.write(file_bahan_baku.getbuffer())
                            
                        _jalankan_etl_bahan_baku(bb_path, update_tgl_bahan_baku)
                        
            else:
                st.info("Pastikan Google Sheet memiliki akses 'Anyone with the link can view' agar sistem bisa mengunduhnya.")
                
                sheet_id = st.text_input(
                    "ID Google Sheet", 
                    value="11QKLfNWhV7mFpwgJJ-6Zg8HWWs3yEmHCGszNuwDXl5o",
                    placeholder="Contoh: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                    key="txt_sheet_bb"
                )
                
                if st.button("Tarik Data & Jalankan ETL", type="primary", icon=":material/cloud_download:"):
                    if not sheet_id:
                        st.error("Masukkan ID Google Sheet terlebih dahulu!")
                    else:
                        with st.spinner("Mengunduh data dari Google Sheets..."):
                            import requests
                            try:
                                export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
                                response = requests.get(export_url)
                                
                                if response.status_code == 200:
                                    bb_path = "temp_bahan_baku_gsheet.xlsx"
                                    with open(bb_path, "wb") as f:
                                        f.write(response.content)
                                    
                                    st.success("File berhasil diunduh. Memulai proses ETL...")
                                    
                                    _jalankan_etl_bahan_baku(bb_path, update_tgl_bahan_baku)
                                else:
                                    st.error(f"Gagal mengunduh file. Status code: {response.status_code}. Pastikan ID benar dan akses terbuka.")
                            except Exception as e:
                                st.error(f"Terjadi kesalahan saat mengunduh: {e}")

        elif tipe_etl == "Kondisi Stock BB":

            # 1. FUNGSI HELPER
            def _jalankan_etl_kondisi_stock_bb(file_path, tahun_data):
                sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../ETL')))
                import etl_kondisi_stock_bb as etl_ksb  # type: ignore

                etl_ksb.Config.EXCEL_FILE  = file_path
                etl_ksb.Config.SHEET_PUPUK = 'Pupuk'
                etl_ksb.Config.SHEET_BB    = 'Bahan Baku'
                etl_ksb.Config.TAHUN_DATA  = tahun_data
                etl_ksb.db_get_engine      = _get_engine

                terminal = st.empty()
                capture_ksb = StreamlitCapture(terminal)
                with redirect_stdout(capture_ksb), redirect_stderr(capture_ksb):
                    try:
                        sukses = etl_ksb.run_etl()
                        capture_ksb.flush()

                        if sukses:
                            st.success("Proses sinkronisasi Kondisi Stock BB selesai! Tekan tombol Refresh Data agar data terbaru muncul di dashboard.")
                            st.cache_data.clear()
                        else:
                            st.error("Proses ETL Kondisi Stock BB gagal, periksa terminal di atas.")
                    except Exception as e:
                        st.error(f"Gagal memproses data Kondisi Stock BB: {e}")
                    finally:
                        if os.path.exists(file_path):
                            os.remove(file_path)

            # 2. LOGIKA ANTARMUKA / UI MODUL KONDISI STOCK BB
            st.info(
                "ℹ️ ETL modul ini hanya menghapus & mengganti data untuk **tahun yang dipilih** "
                "di bawah ini. Data tahun-tahun lain di database tetap aman dan tidak tersentuh."
            )

            tahun_sekarang = datetime.today().year
            tahun_data_ksb = st.selectbox(
                "Tahun Data",
                options=list(range(tahun_sekarang - 2, tahun_sekarang + 2)),
                index=2,  # default ke tahun berjalan
                key="sel_tahun_ksb",
                help="Tahun data yang direkap di dalam file (bukan tahun hari ini). Dicek manual karena rekapan bisa dimulai dari bulan berapa saja tiap tahunnya."
            )

            metode_input = st.radio("Metode Input Data", ["Upload File Manual", "Tarik Langsung dari Google Sheets"], horizontal=True, key="rad_ksb")

            if metode_input == "Upload File Manual":
                file_ksb = st.file_uploader(
                    "Upload File Excel — harus ada sheet 'Pupuk' dan 'Bahan Baku'",
                    type=["xlsx"],
                    key="uploader_ksb"
                )
                if file_ksb:
                    if st.button("Jalankan ETL Kondisi Stock BB", type="primary", icon=":material/cloud_upload:"):
                        ksb_path = "temp_kondisi_stock_bb.xlsx"
                        with open(ksb_path, "wb") as f:
                            f.write(file_ksb.getbuffer())
                        _jalankan_etl_kondisi_stock_bb(ksb_path, tahun_data_ksb)

            else:
                st.info("Pastikan Google Sheet memiliki akses 'Anyone with the link can view' agar sistem bisa mengunduhnya. Sheet 'Pupuk' dan 'Bahan Baku' harus ada di dalamnya.")

                sheet_id_ksb = st.text_input(
                    "ID Google Sheet (Kondisi Stock BB)",
                    value="1vlBMT1FzSYEhtU3iabkpG1rMZpIGoyE_5EF3ZVYqk3g",
                    placeholder="Contoh: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                    key="txt_sheet_ksb"
                )

                if st.button("Tarik Data & Jalankan ETL Kondisi Stock BB", type="primary", icon=":material/cloud_download:"):
                    if not sheet_id_ksb:
                        st.error("Masukkan ID Google Sheet terlebih dahulu!")
                    else:
                        with st.spinner("Mengunduh data dari Google Sheets..."):
                            import requests
                            try:
                                export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id_ksb}/export?format=xlsx"
                                response = requests.get(export_url)

                                if response.status_code == 200:
                                    ksb_path = "temp_kondisi_stock_bb_gsheet.xlsx"
                                    with open(ksb_path, "wb") as f:
                                        f.write(response.content)

                                    st.success("File berhasil diunduh. Memulai proses ETL...")
                                    _jalankan_etl_kondisi_stock_bb(ksb_path, tahun_data_ksb)
                                else:
                                    st.error(f"Gagal mengunduh file. Status code: {response.status_code}. Pastikan ID benar dan akses terbuka.")
                            except Exception as e:
                                st.error(f"Terjadi kesalahan saat mengunduh: {e}")

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
    
    col_del1, col_del2, col_del3, col_del4, col_del5 = st.columns(5)
    
    with col_del1:
        with st.expander("🗑️ Hapus Data SAP"):
            st.write("Menghapus semua data Purchase Requisition, Purchase Order, Goods Receipt, dan riwayat status rilis. (Data Master tetap aman).")
            confirm_sap = st.checkbox("Saya yakin (SAP)", key="confirm_sap")
            if st.button("Hapus Data SAP", type="primary", disabled=not confirm_sap, use_container_width=True):
                with st.spinner("Menghapus data SAP..."):
                    try:
                        engine = _get_engine()
                        with engine.begin() as conn:
                            conn.execute(text("TRUNCATE TABLE purchase_requisitions, purchase_orders CASCADE;"))
                        st.success("Data SAP berhasil dikosongkan!")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menghapus data: {e}")

    with col_del2:
        with st.expander("🗑️ Hapus Data SIPS"):
            st.write("Menghapus semua riwayat transaksi SIPS dan data karyawan SIPS dari database.")
            confirm_sips = st.checkbox("Saya yakin (SIPS)", key="confirm_sips")
            if st.button("Hapus Data SIPS", type="primary", disabled=not confirm_sips, use_container_width=True):
                with st.spinner("Menghapus data SIPS..."):
                    try:
                        engine = _get_engine()
                        with engine.begin() as conn:
                            conn.execute(text("TRUNCATE TABLE sips_data, sips_employees CASCADE;"))
                        st.success("Data SIPS berhasil dikosongkan!")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menghapus data: {e}")

    with col_del3:
        with st.expander("🗑️ Hapus Inklaring"):
            st.write("Mengosongkan seluruh tabel Inklaring Barang Impor dari database secara permanen.")
            confirm_inklaring = st.checkbox("Saya yakin", key="confirm_inklaring")
            if st.button("Hapus Inklaring", type="primary", disabled=not confirm_inklaring, use_container_width=True):
                with st.spinner("Menghapus data Inklaring..."):
                    try:
                        engine = _get_engine()
                        with engine.begin() as conn:
                            conn.execute(text("TRUNCATE TABLE inklaring_impor RESTART IDENTITY CASCADE;"))
                        st.success("Data Inklaring berhasil dikosongkan!")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menghapus data: {e}")
                        
    with col_del4:
        with st.expander("🗑️ Hapus Harga BB"):
            st.write("Mengosongkan seluruh riwayat rekapan majalah Harga Bahan Baku dari database.")
            confirm_bb = st.checkbox("Saya yakin", key="confirm_bb")
            if st.button("Hapus Harga BB", type="primary", disabled=not confirm_bb, use_container_width=True):
                with st.spinner("Menghapus data Harga Bahan Baku..."):
                    try:
                        engine = _get_engine()
                        with engine.begin() as conn:
                            conn.execute(text("TRUNCATE TABLE master_harga_bahan_baku RESTART IDENTITY CASCADE;"))
                        st.success("Data Harga Bahan Baku berhasil dikosongkan!")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menghapus data: {e}")

    with col_del5:
        with st.expander("🗑️ Hapus Kondisi Stock BB"):
            st.write("Menghapus data Kondisi Stock BB per tahun tertentu (data tahun lain tidak terpengaruh), atau kosongkan seluruhnya.")
            tahun_sekarang_del = datetime.today().year
            pilihan_hapus_ksb = st.radio(
                "Cakupan hapus",
                ["Hapus tahun tertentu", "Hapus SEMUA tahun"],
                key="radio_hapus_ksb",
                horizontal=False
            )
            if pilihan_hapus_ksb == "Hapus tahun tertentu":
                tahun_hapus_ksb = st.selectbox(
                    "Pilih tahun yang akan dihapus",
                    options=list(range(tahun_sekarang_del - 3, tahun_sekarang_del + 2)),
                    index=3,
                    key="sel_tahun_hapus_ksb"
                )
            confirm_ksb = st.checkbox("Saya yakin", key="confirm_ksb")
            if st.button("Hapus Kondisi Stock BB", type="primary", disabled=not confirm_ksb, use_container_width=True):
                with st.spinner("Menghapus data Kondisi Stock BB..."):
                    try:
                        engine = _get_engine()
                        if pilihan_hapus_ksb == "Hapus tahun tertentu":
                            with engine.begin() as conn:
                                deleted = conn.execute(
                                    text("DELETE FROM kondisi_stock_bb_raw WHERE tahun_data = :tahun"),
                                    {'tahun': tahun_hapus_ksb}
                                ).rowcount
                            st.success(f"Data Kondisi Stock BB tahun {tahun_hapus_ksb} berhasil dihapus ({deleted} baris)!")
                        else:
                            with engine.begin() as conn:
                                conn.execute(text("TRUNCATE TABLE kondisi_stock_bb_raw RESTART IDENTITY CASCADE;"))
                            st.success("SELURUH data Kondisi Stock BB (semua tahun) berhasil dikosongkan!")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menghapus data: {e}")