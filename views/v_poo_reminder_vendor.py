"""
v_poo_reminder_vendor.py - Halaman "PO Outstanding - Reminder Email"

PERUBAHAN dari versi sebelumnya:
- Tab "Import Data Excel" DIHAPUS dari halaman ini. Upload data mentah
  (sheet ALL bulanan) sekarang dilakukan di halaman "Manajemen Data"
  sebagai salah satu Modul ETL ("PO Outstanding (ALL)"), yang otomatis
  memanggil etl_po_all.py lalu etl_generate_perlu_email.py.
- Halaman ini sekarang murni 2 tab: Kirim Reminder & Lihat Semua Data,
  keduanya membaca dari tabel po_outstanding (hasil filter otomatis).

Alur halaman (tab Kirim Reminder):
1. Pilih vendor (dropdown, cari berdasarkan kode/nama) -> email vendor
   otomatis muncul (read-only).
2. Pilih PO + Item milik vendor tersebut (multi-select).
3. Preview isi email (tabel PO/Item terpilih) -- WAJIB direview sebelum kirim.
4. Isi kredensial SMTP manual (Gmail; host & port sudah terisi default).
5. Submit -> kirim SATU email ke vendor tersebut.

Catatan:
- Mengacu ke tabel `po_outstanding`, yang sekarang diisi oleh proses
  etl_po_all.py + etl_generate_perlu_email.py (lihat halaman Manajemen
  Data / Monitoring PO Outstanding). Selama proses itu belum pernah
  dijalankan, halaman ini menampilkan pesan informatif alih-alih error mentah.
- Tidak ada upload dokumen lampiran (sudah diputuskan tidak diperlukan).
- Satu kali proses hanya untuk SATU vendor (submit ulang untuk vendor lain).
- Kredensial SMTP diinput manual setiap sesi, TIDAK disimpan ke database
  atau session state permanen -- sesuai kesepakatan awal.
- Email dikirim sebagai multipart/alternative (plain-text + HTML) untuk
  membantu deliverability / mengurangi risiko masuk folder spam.
"""

import streamlit as st
import pandas as pd
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr


def _get_engine():
    from config_db import get_db_engine
    return get_db_engine()


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
# HELPER: Bangun isi email (HTML & plain-text)
# =============================================================================

def _resolve_vendor_display(vendor_name):
    """Nama vendor ditampilkan tebal; awalan 'PT' hanya ditambahkan otomatis
    jika nama vendor pada data belum diawali 'PT' (menghindari 'PT PT ...')."""
    vendor_name_clean = (vendor_name or "").strip()
    if vendor_name_clean.upper().startswith("PT"):
        return vendor_name_clean
    return f"PT {vendor_name_clean}"


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

    vendor_display = _resolve_vendor_display(vendor_name)

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


def _build_email_plaintext(vendor_name, df_selected, tanggal_surat_label):
    """Versi teks biasa (tanpa HTML) dari isi surat, dengan informasi yang
    sama persis seperti versi HTML. Dikirim sebagai bagian 'plain' pada
    email multipart/alternative -- membantu deliverability (mengurangi
    risiko masuk folder spam) dan menjadi fallback bagi klien email yang
    tidak menampilkan HTML."""
    vendor_display = _resolve_vendor_display(vendor_name)

    lines = []
    lines.append("SURAT PERMINTAAN KLARIFIKASI ATAS KETERLAMBATAN PEMENUHAN PO")
    lines.append("")
    lines.append(f"Hari/Tanggal : {tanggal_surat_label}")
    lines.append("Perihal      : Klarifikasi dan Tindak Lanjut PO Outstanding")
    lines.append("")
    lines.append("Kepada Yth.")
    lines.append(vendor_display)
    lines.append("di Tempat")
    lines.append("")
    lines.append("Dengan hormat,")
    lines.append("")
    lines.append(
        f"Berdasarkan hasil monitoring atas realisasi Purchase Order (PO) yang telah "
        f"diterbitkan kepada {vendor_display}, kami menemukan masih terdapat sejumlah PO "
        f"yang belum terealisasi dan/atau masih berstatus Outstanding, sebagaimana daftar berikut :"
    )
    lines.append("")

    # Tabel PO dalam bentuk teks rata (fixed-width) agar tetap terbaca rapi
    # di klien email yang hanya menampilkan plain-text.
    header = ["No.", "No. PO", "Item", "Deskripsi", "Tgl PO", "Delivery Date", "Telat"]
    table_rows = [header]
    for i, (_, row) in enumerate(df_selected.iterrows(), start=1):
        doc_date = pd.to_datetime(row['document_date']).strftime('%d-%m-%Y') if pd.notna(row['document_date']) else "-"
        del_date = pd.to_datetime(row['delivery_date']).strftime('%d-%m-%Y') if pd.notna(row['delivery_date']) else "-"
        telat = f"{int(row['pending_time'])} hari" if pd.notna(row['pending_time']) else "-"
        table_rows.append([
            str(i),
            str(row['purchasing_document']),
            str(row['item']),
            str(row['short_text'] or '-'),
            doc_date,
            del_date,
            telat,
        ])

    col_widths = [max(len(str(r[c])) for r in table_rows) for c in range(len(header))]
    for r in table_rows:
        line = "  ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(r))
        lines.append(line)
    lines.append("")

    lines.append(
        "Sehubungan dengan hal tersebut, kami meminta untuk segera memberikan Surat "
        "klarifikasi tertulis atas PO yang masih outstanding untuk masing-masing PO."
    )
    lines.append("")
    lines.append(
        "Surat Klarifikasi tersebut dapat dikirimkan melalui Email "
        "expeditinglaporan2020@gmail.com dan kami terima paling lambat 3 (tiga) hari kerja "
        "sejak pemberitahuan ini dikirimkan, dengan mencantumkan alasan keterlambatan dan "
        "tanggal pasti penyelesaian/pengiriman."
    )
    lines.append("")
    lines.append(
        "Perlu kami sampaikan bahwa tingkat pemenuhan dan ketepatan waktu pengiriman akan "
        "menjadi bagian dari evaluasi kinerja vendor dan pertimbangan dalam proses pengadaan "
        "berikutnya. Adapun diperlukan penjelasan lebih lanjut dapat menghubungi Nomor WhatsApp "
        "Admin Pengadaan Barang: +62 811-3076-2493 (Chat Only)."
    )
    lines.append("")
    lines.append("Demikian disampaikan untuk menjadi perhatian dan segera ditindaklanjuti.")
    lines.append("")
    lines.append("Hormat kami,")
    lines.append("")
    lines.append("PT PETROKIMIA GRESIK")
    lines.append("Pgs. VP Pengadaan Barang")
    lines.append("")
    lines.append("")
    lines.append("Mochammad Fais")
    lines.append("AVP Pengadaan Barang Alat Pabrik & TA")

    return "\n".join(lines)


def _send_email(smtp_host, smtp_port, sender_email, sender_password, to_email, subject,
                 html_body, plain_body, sender_display_name="Pengadaan Barang Petro", cc_email=None):
    # multipart/alternative: klien email akan memilih salah satu bagian untuk
    # ditampilkan (umumnya HTML jika didukung), tapi keberadaan versi plain-text
    # membantu deliverability / mengurangi risiko email dianggap spam.
    msg = MIMEMultipart('alternative')
    msg['From'] = formataddr((sender_display_name, sender_email))
    msg['To'] = to_email
    msg['Subject'] = subject

    # Header 'Cc' hanya untuk DITAMPILKAN di email penerima (agar mereka tahu
    # siapa saja yang di-cc). Ini tidak otomatis membuat SMTP mengirim ke
    # alamat tsb -- alamat cc tetap harus ditambahkan eksplisit ke daftar
    # penerima (`all_recipients`) di server.sendmail() di bawah.
    cc_list = [e.strip() for e in (cc_email or "").split(",") if e.strip()]
    if cc_list:
        msg['Cc'] = ", ".join(cc_list)

    # Bagian plain-text HARUS ditempel lebih dulu, baru HTML -- sesuai urutan
    # preferensi standar multipart/alternative (bagian terakhir = paling disukai).
    msg.attach(MIMEText(plain_body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))

    all_recipients = [to_email] + cc_list

    server = smtplib.SMTP(smtp_host, int(smtp_port))
    try:
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, all_recipients, msg.as_string())
    finally:
        server.quit()


# =============================================================================
# TAB 1: KIRIM REMINDER
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
            "(kemungkinan belum ada upload & filter). Silakan upload data melalui halaman "
            "**Manajemen Data** (Modul ETL: PO Outstanding (ALL)) terlebih dahulu.\n\n"
            f"Detail teknis: {e}"
        )
        return

    if df_vendor.empty:
        st.info(
            "Belum ada data PO Outstanding. Silakan upload data melalui halaman "
            "**Manajemen Data** (Modul ETL: PO Outstanding (ALL)) terlebih dahulu."
        )
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
        'pending_time': 'Hari Telat',
        'pending_time_classification': 'Kategori Telat',
    })

    edited_df = st.data_editor(
        df_po_display[['pilih', 'No. PO', 'Item', 'Deskripsi', 'Tgl PO', 'Delivery Date',
                        'Hari Telat', 'Kategori Telat']],
        hide_index=True,
        use_container_width=True,
        disabled=['No. PO', 'Item', 'Deskripsi', 'Tgl PO', 'Delivery Date',
                  'Hari Telat', 'Kategori Telat'],
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
    plain_body = _build_email_plaintext(vendor_name, df_selected, tanggal_surat_label)

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
            sender_email = st.text_input(
                "Email Pengirim (Gmail)",
                value="expeditinglaporan2020@gmail.com",
                placeholder="nama@gmail.com",
                key="rv_sender_email"
            )
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

        cc_email = st.text_input(
            "CC",
            value="alpata@petrokimia-gresik.com, daanbarum@petrokimia-gresik.com",
            help="Alamat yang akan menerima salinan (CC) email ini. Bisa diisi lebih dari satu, "
                 "dipisahkan koma. Kosongkan jika tidak perlu CC.",
            key="rv_cc_email"
        )

        st.caption(
            ":material/lock: Kredensial ini hanya dipakai untuk sesi pengiriman saat ini dan tidak disimpan di manapun."
        )

        confirm_text = f"Saya sudah memeriksa preview email dan yakin ingin mengirim ke **{vendor_email or '(email belum ada)'}**"
        if cc_email.strip():
            confirm_text += f" (CC: **{cc_email.strip()}**)"
        confirm_text += "."

        confirm = st.checkbox(confirm_text, key="rv_confirm_send")

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
                        plain_body=plain_body,
                        sender_display_name="Pengadaan Barang Petrokimia Gresik",
                        cc_email=cc_email,
                    )
                    cc_note = f" (CC: {cc_email.strip()})" if cc_email.strip() else ""
                    st.success(f":material/check_circle: Email berhasil dikirim ke {vendor_name} ({vendor_email}){cc_note}!")
                    st.balloons()
                except smtplib.SMTPAuthenticationError:
                    st.error(
                        ":material/error: Autentikasi gagal. Pastikan menggunakan App Password Gmail yang benar "
                        "(bukan password akun biasa), dan akun mengizinkan akses SMTP."
                    )
                except Exception as e:
                    st.error(f":material/error: Gagal mengirim email: {e}")


# =============================================================================
# RENDER: satu tab -> Kirim Reminder
# (Tab "Lihat Semua Data" dihapus -- sudah tersedia di halaman
#  "Monitoring PO Outstanding" pada tab "Data ALL" dan "Perlu Email")
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
        "Untuk upload data mentah bulanan (sheet ALL) dan melihat seluruh data, gunakan "
        "halaman <b>Manajemen Data</b> dan <b>Monitoring PO Outstanding</b>. "
        "Halaman ini bersifat sementara sampai website resmi dari pusat tersedia."
        "</p>",
        unsafe_allow_html=True
    )

    _tab_kirim_reminder(load_data)