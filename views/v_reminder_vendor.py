"""
v_reminder_vendor.py - Halaman "PO Outstanding - Reminder Email"

Alur halaman:
1. Pilih vendor (dropdown, cari berdasarkan kode/nama) -> email vendor
   otomatis muncul (read-only).
2. Pilih PO + Item milik vendor tersebut (multi-select).
3. Preview isi email (tabel PO/Item terpilih) -- WAJIB direview sebelum kirim.
4. Isi kredensial SMTP manual (Gmail; host & port sudah terisi default).
5. Submit -> kirim SATU email ke vendor tersebut.

Catatan:
- Mengacu ke tabel `po_outstanding` (lihat schema_po_outstanding.sql &
  etl_po_outstanding.py). Selama ETL belum dijalankan / tabel belum ada,
  halaman ini menampilkan pesan informatif alih-alih error mentah.
- Tidak ada upload dokumen lampiran (sudah diputuskan tidak diperlukan).
- Satu kali proses hanya untuk SATU vendor (submit ulang untuk vendor lain).
- Kredensial SMTP diinput manual setiap sesi, TIDAK disimpan ke database
  atau session state permanen -- sesuai kesepakatan awal.
"""

import streamlit as st
import pandas as pd
import smtplib
import os
import sys
import time
from datetime import datetime
from contextlib import redirect_stdout, redirect_stderr
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from sqlalchemy import text


def _get_engine():
    from config_db import get_db_engine
    return get_db_engine()


class _StreamlitCapture:
    """Menangkap output terminal ETL, mengikuti pola StreamlitCapture di
    v_manajemen_data.py (nama di-underscore agar tidak bentrok/duplikat)."""
    def __init__(self, placeholder):
        self.placeholder = placeholder
        self.lines = []
        self.buffer = ""
        self.last_update = time.time()

    def write(self, text_chunk):
        if '\r' in text_chunk:
            return
        self.buffer += text_chunk
        if '\n' in self.buffer:
            parts = self.buffer.split('\n')
            self.lines.extend(parts[:-1])
            self.buffer = parts[-1]
        if time.time() - self.last_update > 1.0:
            self.flush()

    def flush(self):
        if not self.lines and not self.buffer:
            return
        display_lines = self.lines[-25:]
        if self.buffer:
            display_lines.append(self.buffer)
        self.placeholder.code('\n'.join(display_lines), language='bash')
        self.last_update = time.time()


# =============================================================================
# HELPER: Query data vendor & PO dari database
# =============================================================================

def _get_vendor_list(load_data):
    """Ambil daftar vendor unik (kode, nama, email) yang punya PO outstanding."""
    query = """
        SELECT
            vendor_code,
            vendor_name,
            MAX(vendor_email) AS vendor_email,
            COUNT(*) AS jumlah_po_item
        FROM po_outstanding
        GROUP BY vendor_code, vendor_name
        ORDER BY vendor_name
    """
    return load_data(query)


def _get_po_by_vendor(load_data, vendor_code):
    """Ambil semua baris PO/Item outstanding milik satu vendor tertentu."""
    query = """
        SELECT
            purchasing_document,
            item,
            short_text,
            document_date,
            delivery_date,
            order_quantity,
            order_unit,
            still_to_be_delivered_qty,
            net_order_value,
            currency,
            pending_time,
            pending_time_classification
        FROM po_outstanding
        WHERE vendor_code = :vendor_code
        ORDER BY delivery_date ASC, purchasing_document, item
    """
    # load_data pada platform ini menerima raw SQL string (lihat pola view lain
    # seperti v_manajemen_data.py), sehingga parameter disisipkan langsung.
    # Aman karena vendor_code berasal dari pilihan dropdown (hasil query
    # sebelumnya), bukan input bebas dari pengguna.
    query_final = query.replace(":vendor_code", f"'{vendor_code}'")
    return load_data(query_final)


# =============================================================================
# HELPER: Bangun isi email (HTML)
# =============================================================================

def _build_email_html(vendor_name, df_selected, tanggal_surat_label):
    rows_html = ""
    for i, (_, row) in enumerate(df_selected.iterrows(), start=1):
        doc_date = pd.to_datetime(row['document_date']).strftime('%d-%m-%Y') if pd.notna(row['document_date']) else "-"
        del_date = pd.to_datetime(row['delivery_date']).strftime('%d-%m-%Y') if pd.notna(row['delivery_date']) else "-"
        rows_html += f"""
        <tr>
            <td style="padding:8px; border:1px solid #ddd; text-align:center;">{i}</td>
            <td style="padding:8px; border:1px solid #ddd;">{row['purchasing_document']}</td>
            <td style="padding:8px; border:1px solid #ddd;">{row['item']}</td>
            <td style="padding:8px; border:1px solid #ddd;">{row['short_text'] or '-'}</td>
            <td style="padding:8px; border:1px solid #ddd;">{doc_date}</td>
            <td style="padding:8px; border:1px solid #ddd;">{del_date}</td>
            <td style="padding:8px; border:1px solid #ddd; text-align:center;">{int(row['pending_time']) if pd.notna(row['pending_time']) else '-'} hari</td>
        </tr>
        """

    # Nama vendor ditampilkan tebal; awalan "PT" hanya ditambahkan otomatis
    # jika nama vendor pada data belum diawali "PT" (menghindari "PT PT ...").
    vendor_name_clean = (vendor_name or "").strip()
    if vendor_name_clean.upper().startswith("PT"):
        vendor_display = vendor_name_clean
    else:
        vendor_display = f"PT {vendor_name_clean}"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="margin:0; padding:0; font-family:Arial, sans-serif; background-color:#f9f9f9;">
    <table align="center" width="700" cellpadding="0" cellspacing="0" style="background-color:#ffffff; padding:32px;">
        <tr>
            <td style="color:#222222; font-size:15px; line-height:1.7; text-align:justify;">
                <p style="text-align:center; font-weight:bold; font-size:16px; margin:0 0 20px 0;">
                    SURAT PERMINTAAN KLARIFIKASI ATAS KETERLAMBATAN PEMENUHAN PO
                </p>

                <table cellpadding="0" cellspacing="0" style="font-size:15px; margin-bottom:16px;">
                    <tr>
                        <td style="padding:2px 12px 2px 0; vertical-align:top; white-space:nowrap;">Hari/Tanggal</td>
                        <td style="padding:2px 8px; vertical-align:top;">:</td>
                        <td style="padding:2px 0; vertical-align:top;">{tanggal_surat_label}</td>
                    </tr>
                    <tr>
                        <td style="padding:2px 12px 2px 0; vertical-align:top; white-space:nowrap;">Perihal</td>
                        <td style="padding:2px 8px; vertical-align:top;">:</td>
                        <td style="padding:2px 0; vertical-align:top;">Klarifikasi dan Tindak Lanjut PO Outstanding</td>
                    </tr>
                </table>

                <p style="margin:0 0 4px 0;">Kepada Yth.</p>
                <p style="margin:0 0 4px 0;"><strong>{vendor_display}</strong></p>
                <p style="margin:0 0 16px 0;">di Tempat</p>

                <p>Dengan hormat,</p>

                <p>
                    Berdasarkan hasil monitoring atas realisasi Purchase Order (PO) yang telah diterbitkan
                    kepada <strong>{vendor_display}</strong>, kami menemukan masih terdapat sejumlah PO yang
                    belum terealisasi dan/atau masih berstatus Outstanding, sebagaimana daftar berikut :
                </p>
            </td>
        </tr>
        <tr>
            <td style="padding:16px 0;">
                <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse; font-size:13px;">
                    <thead>
                        <tr style="background-color:#f0f0f0;">
                            <th style="padding:8px; border:1px solid #ddd; text-align:center;">No.</th>
                            <th style="padding:8px; border:1px solid #ddd; text-align:left;">No. PO</th>
                            <th style="padding:8px; border:1px solid #ddd; text-align:left;">Item</th>
                            <th style="padding:8px; border:1px solid #ddd; text-align:left;">Deskripsi</th>
                            <th style="padding:8px; border:1px solid #ddd; text-align:left;">Tgl PO</th>
                            <th style="padding:8px; border:1px solid #ddd; text-align:left;">Tgl Kirim (Delivery Date)</th>
                            <th style="padding:8px; border:1px solid #ddd; text-align:center;">Keterlambatan</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </td>
        </tr>
        <tr>
            <td style="color:#222222; font-size:15px; line-height:1.7; text-align:justify;">
                <p>
                    Sehubungan dengan hal tersebut, kami meminta untuk segera memberikan Surat klarifikasi
                    tertulis atas PO yang masih outstanding untuk masing-masing PO.
                </p>
                <p>
                    Surat Klarifikasi tersebut dapat dikirimkan melalui <strong>Email</strong>
                    <strong>expeditinglaporan2020@gmail.com</strong> dan kami terima <strong>paling lambat 3 (tiga) hari kerja</strong>
                    sejak pemberitahuan ini dikirimkan, dengan mencantumkan
                    <strong>alasan keterlambatan dan tanggal pasti penyelesaian/pengiriman</strong>.
                </p>
                <p>
                    Perlu kami sampaikan bahwa tingkat pemenuhan dan ketepatan waktu pengiriman akan menjadi
                    bagian dari evaluasi kinerja vendor dan pertimbangan dalam proses pengadaan berikutnya.
                    Adapun diperlukan penjelasan lebih lanjut dapat menghubungi <strong>Nomor WhatsApp Admin Pengadaan Barang: 
                    +62 811-3076-2493 (Chat Only).</strong>
                </p>
                <p>
                    Demikian disampaikan untuk menjadi perhatian dan segera ditindaklanjuti.
                </p>

                <p style="margin-top:24px; margin-bottom:0;">Hormat kami,</p>
                <p style="margin:0;">&nbsp;</p>
                <p style="margin:0;">PT PETROKIMIA GRESIK</p>
                <p style="margin:0 0 40px 0;">Pgs. VP Pengadaan Barang</p>

                <p style="margin:0; font-weight:bold;">Mochammad Fais</p>
                <p style="margin:0;">AVP Pengadaan Barang Alat Pabrik &amp; TA</p>
            </td>
        </tr>
    </table>
    </body>
    </html>
    """
    return html

def _send_email(smtp_host, smtp_port, sender_email, sender_password, to_email, subject, html_body,
                 sender_display_name="Pengadaan Barang Petro"):
    msg = MIMEMultipart('alternative')
    msg['From'] = formataddr((sender_display_name, sender_email))
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))

    server = smtplib.SMTP(smtp_host, int(smtp_port))
    try:
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
    finally:
        server.quit()


# =============================================================================
# TAB 1: KIRIM REMINDER (isi halaman yang sudah ada sebelumnya)
# =============================================================================

def _tab_kirim_reminder(load_data):
    if load_data is None:
        st.error("Koneksi data tidak tersedia (load_data tidak ditemukan).")
        return

    # -------------------------------------------------------------------
    # 1. Ambil daftar vendor
    # -------------------------------------------------------------------
    try:
        df_vendor = _get_vendor_list(load_data)
    except Exception as e:
        st.warning(
            ":material/warning: Tabel data PO Outstanding belum tersedia atau belum terisi "
            "(kemungkinan ETL belum dijalankan). Silakan jalankan ETL PO Outstanding "
            "terlebih dahulu di halaman Manajemen Data.\n\n"
            f"Detail teknis: {e}"
        )
        return

    if df_vendor.empty:
        st.info("Belum ada data PO Outstanding. Silakan jalankan ETL PO Outstanding terlebih dahulu.")
        return

    st.markdown("### :material/counter_1: Pilih Vendor")

    df_vendor['label'] = df_vendor['vendor_code'].astype(str) + " - " + df_vendor['vendor_name']
    vendor_options = df_vendor['label'].tolist()

    selected_label = st.selectbox(
        "Cari vendor berdasarkan kode atau nama",
        options=vendor_options,
        index=None,
        placeholder="Ketik kode atau nama vendor...",
        key="rv_vendor_select"
    )

    if not selected_label:
        st.info("Silakan pilih vendor untuk melanjutkan.")
        return

    vendor_row = df_vendor[df_vendor['label'] == selected_label].iloc[0]
    vendor_code = vendor_row['vendor_code']
    vendor_name = vendor_row['vendor_name']
    vendor_email = vendor_row['vendor_email']

    col_a, col_b = st.columns(2)
    with col_a:
        st.text_input("Nama Vendor", value=vendor_name, disabled=True, key="rv_vendor_name_display")
    with col_b:
        st.text_input(
            "Email Vendor",
            value=vendor_email if vendor_email else ":material/warning: Belum ada email terdaftar",
            disabled=True,
            key="rv_vendor_email_display"
        )

    if not vendor_email:
        st.warning(
            "Vendor ini belum memiliki alamat email pada data. "
            "Lengkapi data email vendor terlebih dahulu (proses rekap sedang berjalan) "
            "sebelum email dapat dikirim."
        )

    st.markdown("---")

    # -------------------------------------------------------------------
    # 2. Pilih PO + Item
    # -------------------------------------------------------------------
    st.markdown("### :material/counter_2: Pilih PO & Item yang Akan Diinformasikan")

    df_po = _get_po_by_vendor(load_data, vendor_code)

    if df_po.empty:
        st.info("Tidak ditemukan PO outstanding untuk vendor ini.")
        return

    df_po = df_po.copy()
    df_po['pilih'] = False
    df_po_display = df_po.rename(columns={
        'purchasing_document': 'No. PO',
        'item': 'Item',
        'short_text': 'Deskripsi',
        'document_date': 'Tgl PO',
        'delivery_date': 'Delivery Date',
        'order_quantity': 'Qty Order',
        'order_unit': 'Satuan',
        'still_to_be_delivered_qty': 'Sisa Qty',
        'net_order_value': 'Nilai PO',
        'currency': 'Mata Uang',
        'pending_time': 'Hari Telat',
        'pending_time_classification': 'Kategori Telat',
    })

    edited_df = st.data_editor(
        df_po_display[['pilih', 'No. PO', 'Item', 'Deskripsi', 'Tgl PO', 'Delivery Date',
                        'Qty Order', 'Satuan', 'Hari Telat', 'Kategori Telat']],
        hide_index=True,
        use_container_width=True,
        disabled=['No. PO', 'Item', 'Deskripsi', 'Tgl PO', 'Delivery Date',
                  'Qty Order', 'Satuan', 'Hari Telat', 'Kategori Telat'],
        column_config={
            "pilih": st.column_config.CheckboxColumn("Pilih", default=False)
        },
        key="rv_po_editor"
    )

    selected_idx = edited_df[edited_df['pilih'] == True].index
    df_selected = df_po.loc[selected_idx]

    if df_selected.empty:
        st.info("Pilih minimal satu baris PO/Item di atas untuk melanjutkan.")
        return

    st.success(f"{len(df_selected)} baris PO/Item dipilih untuk vendor **{vendor_name}**.")

    st.markdown("---")

    # -------------------------------------------------------------------
    # 3. Preview email
    # -------------------------------------------------------------------
    st.markdown("### :material/counter_3: Preview Email")

    subject = st.text_input(
        "Subjek Email",
        value=f"Reminder Status Pengiriman PO - {vendor_name}",
        key="rv_email_subject"
    )

    col_tgl, _ = st.columns([1, 2])
    with col_tgl:
        tanggal_surat = st.date_input(
            "Hari/Tanggal Surat",
            value=datetime.today().date(),
            key="rv_tanggal_surat",
            help="Tanggal ini akan ditampilkan pada bagian 'Hari/Tanggal' di isi surat."
        )

    HARI_ID = {
        "Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu",
        "Thursday": "Kamis", "Friday": "Jumat", "Saturday": "Sabtu", "Sunday": "Minggu"
    }
    BULAN_ID = {
        1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
        7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
    }
    nama_hari = HARI_ID[tanggal_surat.strftime("%A")]
    nama_bulan = BULAN_ID[tanggal_surat.month]
    tanggal_surat_label = f"{nama_hari} / {tanggal_surat.day} {nama_bulan} {tanggal_surat.year}"

    html_body = _build_email_html(vendor_name, df_selected, tanggal_surat_label)

    with st.expander(":material/visibility: Lihat Preview Isi Email", expanded=True):
        st.components.v1.html(html_body, height=450, scrolling=True)

    st.markdown("---")

    # -------------------------------------------------------------------
    # 4. Kredensial SMTP + Kirim
    # -------------------------------------------------------------------
    st.markdown("### :material/counter_4: Kirim Email")

    with st.form("rv_send_form"):
        col1, col2 = st.columns(2)
        with col1:
            smtp_host = st.text_input("SMTP Host", value="smtp.gmail.com", key="rv_smtp_host")
            sender_email = st.text_input("Email Pengirim (Gmail)", value="", placeholder="nama@gmail.com", key="rv_sender_email")
        with col2:
            smtp_port = st.text_input("SMTP Port", value="587", key="rv_smtp_port")
            sender_password = st.text_input(
                "App Password Gmail",
                value="",
                type="password",
                help="Gunakan App Password Gmail (bukan password akun biasa). "
                     "Buat di myaccount.google.com/apppasswords",
                key="rv_sender_password"
            )

        st.caption(
            ":material/lock: Kredensial ini hanya dipakai untuk sesi pengiriman saat ini dan tidak disimpan di manapun."
        )

        confirm = st.checkbox(
            f"Saya sudah memeriksa preview email dan yakin ingin mengirim ke **{vendor_email or '(email belum ada)'}**.",
            key="rv_confirm_send"
        )

        submitted = st.form_submit_button(
            ":material/send: Kirim Email ke Vendor",
            type="primary",
            use_container_width=True,
            disabled=not vendor_email
        )

    if submitted:
        if not confirm:
            st.error("Silakan centang konfirmasi terlebih dahulu sebelum mengirim.")
        elif not sender_email or not sender_password:
            st.error("Email pengirim dan App Password wajib diisi.")
        elif not vendor_email:
            st.error("Vendor ini belum memiliki alamat email. Email tidak dapat dikirim.")
        else:
            with st.spinner(f"Mengirim email ke {vendor_email}..."):
                try:
                    _send_email(
                        smtp_host=smtp_host,
                        smtp_port=smtp_port,
                        sender_email=sender_email,
                        sender_password=sender_password,
                        to_email=vendor_email,
                        subject=subject,
                        html_body=html_body,
                        sender_display_name="Pengadaan Barang Petrokimia Gresik",
                    )
                    st.success(f":material/check_circle: Email berhasil dikirim ke {vendor_name} ({vendor_email})!")
                    st.balloons()
                except smtplib.SMTPAuthenticationError:
                    st.error(
                        ":material/error: Autentikasi gagal. Pastikan menggunakan App Password Gmail yang benar "
                        "(bukan password akun biasa), dan akun mengizinkan akses SMTP."
                    )
                except Exception as e:
                    st.error(f":material/error: Gagal mengirim email: {e}")


# =============================================================================
# TAB 2: IMPORT DATA EXCEL (ETL PO Outstanding)
# =============================================================================
# Sengaja DIPISAH dari v_manajemen_data.py (tidak ditambahkan sebagai salah
# satu "Pilih Modul ETL" di sana), supaya ketika fitur reminder vendor ini
# sudah tidak dipakai lagi (setelah website pusat resmi launching), modul ini
# tinggal dihapus/dinonaktifkan tanpa perlu mengubah v_manajemen_data.py yang
# sudah stabil dan dipakai modul-modul lain.

def _tab_import_data():
    st.markdown(
        "<p style='font-size:14px; opacity:0.7; margin-top:4px; margin-bottom:20px;'>"
        "Upload file Excel PO Outstanding (Sheet1) untuk memperbarui data yang dipakai "
        "pada tab <b>Kirim Reminder</b>. Data lama akan <b>diganti total</b> dengan data "
        "dari file terbaru -- PO yang sudah tidak outstanding otomatis hilang dari sistem."
        "</p>",
        unsafe_allow_html=True
    )

    from config_db import get_setting, set_setting

    # -------------------------------------------------------------------
    # Info tanggal update terakhir (khusus modul ini)
    # -------------------------------------------------------------------
    po_date_str = get_setting("DATA_UPDATE_PO_OUTSTANDING", "-")
    try:
        DATA_UPDATE_PO = datetime.strptime(po_date_str, "%Y-%m-%d").date()
        po_date_label = DATA_UPDATE_PO.strftime('%d %B %Y')
    except Exception:
        po_date_label = "Belum pernah diperbarui"

    st.markdown(f"""
        <div style='background: var(--secondary-background-color); border: 1px solid rgba(255, 75, 75, 0.3);
                    border-radius: 10px; padding: 16px; border-left: 5px solid #ff4b4b; margin-bottom:20px;'>
            <p style='margin: 0; font-size: 13px; opacity: 0.7; font-weight: 600;'>Data PO Outstanding terakhir diperbarui</p>
            <h4 style='margin: 4px 0 0 0; font-size: 20px;'>{po_date_label}</h4>
        </div>
    """, unsafe_allow_html=True)

    st.info(
        ":material/info: Pastikan file Excel yang diupload memiliki sheet bernama **'Sheet1'** "
        "dengan kolom-kolom sesuai format PO Outstanding (Purchasing Document, Item, "
        "Vendor Code, Vendor Name, Vendor email, Document Date, Delivery Date, dsb)."
    )

    def _jalankan_etl_po_outstanding(file_path, sheet_name, update_tanggal):
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../ETL')))
        import etl_po_outstanding  # type: ignore

        etl_po_outstanding.Config.PO_OUTSTANDING_FILE = file_path
        etl_po_outstanding.Config.SHEET_NAME = sheet_name
        etl_po_outstanding.db_get_engine = _get_engine

        terminal = st.empty()
        capture_po = _StreamlitCapture(terminal)
        with redirect_stdout(capture_po), redirect_stderr(capture_po):
            try:
                sukses = etl_po_outstanding.run_etl()
                capture_po.flush()

                if sukses:
                    if update_tanggal:
                        set_setting("DATA_UPDATE_PO_OUTSTANDING", datetime.today().strftime("%Y-%m-%d"))
                    st.success(
                        ":material/check_circle: Proses sinkronisasi PO Outstanding selesai! Data lama telah diganti "
                        "dengan data terbaru. Silakan buka tab **Kirim Reminder** untuk memakainya."
                    )
                    st.cache_data.clear()
                else:
                    st.error(":material/error: Proses ETL PO Outstanding gagal, periksa log terminal di atas.")
            except Exception as e:
                st.error(f":material/error: Gagal memproses data PO Outstanding: {e}")
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

    file_po = st.file_uploader(
        "Upload File PO Outstanding (.xlsx) — data diambil dari sheet 'Sheet1'",
        type=["xlsx"],
        key="rv_uploader_po_outstanding"
    )
    update_tgl_po = st.checkbox(
        "Update Tanggal Data Menjadi Hari Ini", value=True, key="rv_chk_po_outstanding"
    )

    if file_po:
        try:
            xl = pd.ExcelFile(file_po)
            if "Sheet1" not in xl.sheet_names:
                st.error(f":material/error: Sheet 'Sheet1' tidak ditemukan. Sheet yang ada: {xl.sheet_names}")
            else:
                st.success(":material/check_circle: Sheet 'Sheet1' ditemukan.")
                if st.button("Jalankan ETL PO Outstanding", type="primary", icon=":material/cloud_upload:", key="rv_btn_etl"):
                    po_path = "temp_po_outstanding.xlsx"
                    with open(po_path, "wb") as f:
                        f.write(file_po.getbuffer())
                    _jalankan_etl_po_outstanding(po_path, "Sheet1", update_tgl_po)
        except Exception as e:
            st.error(f"Gagal membaca file: {e}")

    # -------------------------------------------------------------------
    # Zona berbahaya: kosongkan data PO Outstanding
    # -------------------------------------------------------------------
    st.markdown("<hr style='margin: 32px 0 20px 0; border-color: rgba(128,128,128,0.2);'>", unsafe_allow_html=True)
    with st.expander(":material/delete: Kosongkan Data PO Outstanding"):
        st.write(
            "Menghapus seluruh data PO Outstanding dari database secara permanen. "
            "Gunakan hanya jika perlu mengulang proses upload dari awal."
        )
        confirm_po = st.checkbox("Saya yakin", key="rv_confirm_delete_po")
        if st.button("Hapus Data PO Outstanding", type="primary", disabled=not confirm_po,
                     use_container_width=True, key="rv_btn_delete_po"):
            with st.spinner("Menghapus data PO Outstanding..."):
                try:
                    engine = _get_engine()
                    with engine.begin() as conn:
                        conn.execute(text("TRUNCATE TABLE po_outstanding RESTART IDENTITY;"))
                    st.success("Data PO Outstanding berhasil dikosongkan!")
                    st.cache_data.clear()
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal menghapus data: {e}")


# =============================================================================
# TAB 3: LIHAT SEMUA DATA (tampilan mirip Excel, seluruh kolom & baris)
# =============================================================================

def _tab_lihat_semua_data(load_data):
    st.markdown(
        "<p style='font-size:14px; opacity:0.7; margin-top:4px; margin-bottom:20px;'>"
        "Menampilkan seluruh data PO Outstanding apa adanya dari database, mirip tampilan file Excel sumber."
        "</p>",
        unsafe_allow_html=True
    )

    if load_data is None:
        st.error("Koneksi data tidak tersedia (load_data tidak ditemukan).")
        return

    query = """
        SELECT
            purchasing_document   AS "Purchasing Document",
            item                  AS "Item",
            purchase_requisition  AS "Purchase Requisition",
            short_text            AS "Short Text",
            document_date         AS "Document Date",
            delivery_date         AS "Delivery Date",
            vendor_code           AS "Vendor Code",
            vendor_name           AS "Vendor Name",
            vendor_email          AS "Vendor email",
            purchasing_group      AS "Purchasing Group",
            order_quantity        AS "Order Quantity",
            still_to_be_delivered_qty   AS "Still to be delivered (qty)",
            order_unit            AS "Order Unit",
            net_order_value       AS "Net Order Value",
            currency              AS "Currency",
            still_to_be_delivered_value AS "Still to be delivered (value)",
            outline_agreement     AS "Outline Agreement",
            deletion_indicator    AS "Deletion Indicator",
            requisitioner         AS "Requisitioner",
            pending_time          AS "PENDING TIME",
            pending_time_classification AS "PENDING TIME Classification"
        FROM po_outstanding
        ORDER BY purchasing_document, item
    """

    try:
        df_all = load_data(query)
    except Exception as e:
        st.warning(
            ":material/warning: Tabel data PO Outstanding belum tersedia atau belum terisi "
            "(kemungkinan ETL belum dijalankan). Silakan jalankan ETL di tab "
            "**Import Data Excel** terlebih dahulu.\n\n"
            f"Detail teknis: {e}"
        )
        return

    if df_all.empty:
        st.info("Belum ada data PO Outstanding. Silakan jalankan ETL di tab **Import Data Excel** terlebih dahulu.")
        return

    # Rapikan tampilan tanggal agar tidak muncul jam 00:00:00
    for col in ["Document Date", "Delivery Date"]:
        if col in df_all.columns:
            df_all[col] = pd.to_datetime(df_all[col], errors='coerce').dt.strftime('%d-%m-%Y')

    col_info, col_search = st.columns([2, 3])
    with col_info:
        st.metric("Total Baris (PO + Item)", f"{len(df_all):,}".replace(",", "."))
    with col_search:
        keyword = st.text_input(
            ":material/search: Cari (No. PO / Vendor / Deskripsi, dll)",
            placeholder="Ketik kata kunci untuk memfilter tabel...",
            key="rv_search_all_data"
        )

    if keyword:
        mask = df_all.apply(
            lambda row: row.astype(str).str.contains(keyword, case=False, na=False).any(),
            axis=1
        )
        df_display = df_all[mask]
        st.caption(f"Menampilkan {len(df_display)} dari {len(df_all)} baris yang cocok dengan '{keyword}'.")
    else:
        df_display = df_all

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        height=600
    )

    # Tombol unduh sebagai Excel, konsisten dengan pola backup di v_manajemen_data.py
    import io
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_display.to_excel(writer, index=False, sheet_name="PO Outstanding")

    st.download_button(
        label="Unduh Data yang Ditampilkan (.xlsx)",
        data=buffer.getvalue(),
        file_name=f"PO_Outstanding_{datetime.today().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        icon=":material/download:",
    )


# =============================================================================
# RENDER: tiga tab -> Kirim Reminder, Import Data Excel, Lihat Semua Data
# =============================================================================

def render(**kwargs):
    load_data = kwargs.get('load_data')

    st.markdown("""
        <h1 style='display:flex; align-items:center; font-size:38px; margin-bottom:0;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor"
                 viewBox="0 0 16 16" style="margin-right:12px; margin-bottom:4px;">
                <path d="M0 4a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2zm2-1a1 1 0 0 0-1 1v.217l7 4.2 7-4.2V4a1 1 0 0 0-1-1zm13 2.383-4.708 2.825L15 11.105zm-.034 6.876-5.64-3.383L8 9.583l-1.326-.795-5.64 3.383A1 1 0 0 0 2 13h12a1 1 0 0 0 .966-.741M1 11.105l4.708-2.897L1 5.383z"/>
            </svg>
            PO Outstanding - Reminder Email
        </h1>
    """, unsafe_allow_html=True)

    st.markdown(
        "<p style='font-size:15px; opacity:0.6; margin-top:4px; margin-bottom:24px;'>"
        "Kirim email pengingat ke vendor terkait PO yang belum selesai (PR-PO outstanding). "
        "Halaman ini bersifat sementara sampai website resmi dari pusat tersedia."
        "</p>",
        unsafe_allow_html=True
    )

    tab_kirim, tab_import, tab_semua = st.tabs([
        ":material/mail: Kirim Reminder", ":material/upload_file: Import Data Excel", ":material/table_view: Lihat Semua Data"
    ])

    with tab_kirim:
        _tab_kirim_reminder(load_data)

    with tab_import:
        _tab_import_data()

    with tab_semua:
        _tab_lihat_semua_data(load_data)