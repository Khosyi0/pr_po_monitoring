"""
pdf_extractor_inklaring.py - Ekstraksi data Inklaring Barang Impor dari 7 jenis
dokumen PDF Bea Cukai: PIB Nopen, INWARD Manifest (BC 1.1), Laporan Penimbunan
MV, SPJM, SKEP, SPPB, dan SPTNP.

Strategi ekstraksi per dokumen:
  - PIB Nopen, SPJM, SKEP, SPPB, SPTNP: teks bisa langsung diambil lewat
    pdfplumber (PDF native / hasil generate sistem, bukan scan). Nilai
    diambil dengan regex pada teks tsb.
  - INWARD Manifest (BC 1.1): PDF berisi vector graphics tanpa layer teks
    sama sekali (bukan raster image, bukan teks) -- di-render ke gambar lalu
    di-OCR dengan Tesseract.
  - Laporan Penimbunan MV: PDF hasil scan/foto (raster image) -- di-render
    ke gambar lalu di-OCR dengan Tesseract.

OCR TIDAK 100% akurat, terutama untuk digit-digit tanggal berdempetan (mis.
"24-02-2025" bisa terbaca "12402-2025") dan simbol serupa (0/O, 1/l/I).
Karena itu, HASIL FUNGSI DI MODUL INI SELALU DIANGGAP SEBAGAI DRAFT AWAL yang
wajib direview manusia sebelum disimpan -- bukan kebenaran mutlak. Pemanggil
(v_inklaring_detail.py) menampilkan seluruh hasil ekstraksi di form yang bisa
diedit sebelum data benar-benar di-INSERT ke database.

Fungsi utama: extract_all(file_bytes_dict) -> dict hasil gabungan siap dipakai
mengisi form "Tambah Data Baru" di v_inklaring_detail.py, dengan key yang
sama seperti EDITABLE_DB_COLUMNS di sana.
"""

import io
import re
from datetime import datetime, date

import pdfplumber

try:
    import pytesseract
    from PIL import Image
    _OCR_AVAILABLE = True
except Exception:
    _OCR_AVAILABLE = False


# =============================================================================
# BULAN INDONESIA (untuk parsing tanggal format "11 Februari 2025", dipakai
# oleh SKEP)
# =============================================================================
BULAN_ID_KE_ANGKA = {
    'januari': 1, 'februari': 2, 'maret': 3, 'april': 4, 'mei': 5, 'juni': 6,
    'juli': 7, 'agustus': 8, 'september': 9, 'oktober': 10, 'november': 11,
    'desember': 12,
}


# =============================================================================
# MAPPING KOMODITI -> SINGKATAN
# Teks komoditi dari PIB tidak selalu identik kata demi kata: bisa ada variasi
# kadar/merek (mis. "PHOSPHATE ROCK 29% XYZ"), dan urutan kata inti bisa
# TERBALIK antar dokumen (mis. "PHOSPHATE ROCK" vs "ROCK PHOSPHATE" -- sumber
# datanya beda petugas input, tidak selalu konsisten). Karena itu pencocokan
# TIDAK memakai prefix match, melainkan: apakah SEMUA kata kunci inti (di
# bagian kiri, dipisah spasi) muncul di teks komoditi, dalam URUTAN BEBAS.
# Kalau tidak ada satupun kombinasi kata kunci yang lengkap cocok, komoditi
# dikosongkan (bukan dibiarkan sebagai teks asli).
KOMODITI_KE_SINGKATAN = {
    "AMMONIUM SULPHATE CAPROLACTAM GRADE IN BULK": "ZA",
    "PHOSPHORIC ACID IN BULK": "PA",
    "AMMONIUM CHLORIDE (NH4CL) IN BULK": "NH4Cl",
    "PHOSPHATE ROCK": "PR",
    "MURIATE OF POTASH (MOP)": "MOP",
    "DI-AMMONIUM PHOSPHATES (DAP) IN BULK": "DAP",
    "SULPHURIC ACID": "SA",
}


def _kata_kunci_inti(label_komoditi):
    """Ambil kata kunci inti dari label mapping, buang kata umum/generik
    ("IN", "BULK", "GRADE") dan tanda kurung supaya pencocokan berbasis
    kata-kunci tidak jadi terlalu longgar (mis. "IN BULK" sendirian jangan
    sampai dianggap cocok ke banyak komoditi berbeda). Tanda hubung (mis. di
    "DI-AMMONIUM") dipecah jadi kata terpisah, konsisten dengan cara token
    diekstrak dari teks komoditi PDF di _petakan_komoditi."""
    kata_umum_diabaikan = {"IN", "BULK", "GRADE", "OF", "NH4CL", "MOP", "DAP"}
    label_bersih = label_komoditi.replace("(", " ").replace(")", " ").replace("-", " ")
    kata_list = [
        k for k in label_bersih.upper().split()
        if k not in kata_umum_diabaikan
    ]
    return kata_list


# Precompute kata kunci inti per label, diurutkan dari YANG PALING BANYAK
# kata kuncinya ke yang paling sedikit -- supaya label yang lebih spesifik
# (lebih banyak kata kunci wajib cocok) dicek lebih dulu, mencegah salah
# cocok ke label lain yang kata kuncinya kebetulan subset.
_KOMODITI_KATA_KUNCI = sorted(
    ((label, _kata_kunci_inti(label), singkatan) for label, singkatan in KOMODITI_KE_SINGKATAN.items()),
    key=lambda item: len(item[1]), reverse=True
)


def _petakan_komoditi(teks_komoditi):
    """Mencocokkan teks komoditi hasil ekstraksi PDF ke singkatannya
    berdasarkan kemunculan SEMUA kata kunci inti suatu komoditi di dalam
    teks (urutan kata bebas, jadi tahan terhadap pembalikan seperti
    "ROCK PHOSPHATE" vs "PHOSPHATE ROCK"). Mengembalikan None kalau tidak
    ada yang cocok (field dikosongkan, bukan diisi teks asli)."""
    if not teks_komoditi:
        return None
    teks_upper = teks_komoditi.strip().upper()
    kata_di_teks = set(re.findall(r"[A-Z0-9]+", teks_upper))
    for _label, kata_kunci_list, singkatan in _KOMODITI_KATA_KUNCI:
        if all(kata in kata_di_teks for kata in kata_kunci_list):
            return singkatan
    return None


# =============================================================================
# HELPER UMUM
# =============================================================================
def _extract_text_all_pages(file_bytes):
    """Menggabungkan teks semua halaman PDF (native, bukan OCR).
    Memakai layout=True supaya posisi horizontal antar kolom (mis. tabel
    2 kolom di form PIB) tetap terjaga lewat spasi, bukan tercampur jadi
    satu baris tanpa jarak -- penting untuk PIB Nopen yang formatnya
    2 kolom (kiri: pengirim/penjual/importir, kanan: field G s.d. 26)."""
    teks_semua = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            teks = page.extract_text(layout=True) or page.extract_text()
            if teks:
                teks_semua.append(teks)
    return "\n".join(teks_semua)


def _ocr_all_pages(file_bytes, resolution=200):
    """Merender tiap halaman PDF ke gambar lalu menjalankan OCR (Tesseract),
    menggabungkan hasilnya. Dipakai untuk PDF yang tidak punya layer teks
    (vector graphics murni) atau hasil scan/foto (raster image)."""
    if not _OCR_AVAILABLE:
        raise RuntimeError(
            "Modul OCR (pytesseract/Pillow) tidak tersedia di lingkungan ini. "
            "Field dari dokumen ini harus diisi manual."
        )
    teks_semua = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            im = page.to_image(resolution=resolution)
            pil_img = im.original
            teks = pytesseract.image_to_string(pil_img, lang='eng')
            teks_semua.append(teks)
    return "\n".join(teks_semua)


def _cari(pattern, teks, group=1, flags=re.IGNORECASE):
    """Regex search yang aman -- None kalau tidak ketemu, hasil di-strip()."""
    m = re.search(pattern, teks, flags)
    if not m:
        return None
    try:
        hasil = m.group(group)
    except IndexError:
        return None
    return hasil.strip() if hasil else None


def _parse_tanggal_ddmmyyyy(teks_tanggal):
    """'13-02-2025' -> date(2025, 2, 13). None kalau gagal parse."""
    if not teks_tanggal:
        return None
    teks_tanggal = teks_tanggal.strip()
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(teks_tanggal, fmt).date()
        except ValueError:
            continue
    return None


def _parse_tanggal_bulan_indo(teks_tanggal):
    """'11 Februari 2025' -> date(2025, 2, 11). None kalau gagal parse.
    Dipakai untuk SKEP (tanggal pojok kanan atas format 'DD BULAN YYYY')."""
    if not teks_tanggal:
        return None
    m = re.match(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", teks_tanggal.strip())
    if not m:
        return None
    hari, nama_bulan, tahun = m.groups()
    bulan = BULAN_ID_KE_ANGKA.get(nama_bulan.lower())
    if not bulan:
        return None
    try:
        return date(int(tahun), bulan, int(hari))
    except ValueError:
        return None


def _parse_angka(teks_angka):
    """'22,000,000.0000' -> 22000000.0 ; '338,872' -> 338872.0 ;
    'Rp. 276,122' -> 276122.0. Menghapus 'Rp', koma ribuan, spasi.
    None kalau tidak ada digit sama sekali."""
    if not teks_angka:
        return None
    bersih = re.sub(r"[Rr][Pp]\.?", "", teks_angka)
    bersih = bersih.replace(",", "").strip()
    m = re.search(r"-?\d+(\.\d+)?", bersih)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def _quantity_hilangkan_7_nol(teks_angka):
    """
    QUANTITY (MT) dari SPPB, sesuai instruksi: "Berat, format hilang 7 angka
    0 (contoh '19,250,000.0000' menjadi '19250')". Ditafsirkan sebagai:
    ambil angka (buang koma & titik desimal dulu jadi string digit murni),
    lalu buang 7 digit nol paling kanan (karena format Bea Cukai selalu
    menulis berat dalam satuan gram, disimpan sbg XX.XXX.000,0000 -- 3 digit
    ribuan + 4 digit desimal = 7 digit yang perlu dibuang untuk dapat MT-nya).

    Contoh: '19,250,000.0000' -> hapus koma & titik -> '192500000000'
    -> buang 7 digit terakhir -> '19250' -> 19250.0
    """
    if not teks_angka:
        return None
    hanya_digit = re.sub(r"[^\d]", "", teks_angka)
    if len(hanya_digit) <= 7:
        return None
    dipotong = hanya_digit[:-7]
    try:
        return float(dipotong)
    except ValueError:
        return None


# =============================================================================
# 1. PIB NOPEN (paling banyak field diambil dari sini)
# =============================================================================
def _ekstrak_no_pen_pib_dari_koordinat(file_bytes):
    """Mengekstrak No Pen PIB (nomor di field G, yang menumpuk secara visual
    di baris yang sama dengan awal nama PENGIRIM/field '1. Nama, Alamat')
    berdasarkan POSISI KATA (x, y) di halaman PDF, bukan pola teks/spasi.

    Pendekatan berbasis pola spasi/koma terbukti TIDAK RELIABLE karena
    pemisah antara nama perusahaan dan nomor pendaftaran sangat bervariasi
    antar dokumen (kadang koma+1spasi, kadang tanpa koma+banyak spasi,
    kadang tanpa koma+1spasi -- kombinasi terakhir ini tidak bisa dibedakan
    dari spasi biasa di dalam nama lewat regex teks apapun). Posisi x/y kata
    di halaman PDF jauh lebih stabil: nomor pendaftaran SELALU berada di
    kolom kanan (x0 besar) pada baris (top) yang SAMA dengan label '1.'
    field PENGIRIM.
    """
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            page = pdf.pages[0]
            words = page.extract_words()

            # Cari label "1." yang jadi awal field PENGIRIM (bukan field A/B/C
            # di bagian atas dokumen yang juga memakai angka "1." sebagai
            # pilihan checkbox) -- dicirikan sebagai "1." dengan x0 KECIL
            # (kolom paling kiri halaman, bukan menumpuk di tengah/kanan
            # seperti checkbox A/B/C), dan merupakan kemunculan PERTAMA di
            # posisi tsb pada halaman (field PENGIRIM selalu di atas field
            # PENJUAL "1a.").
            baris_label_1 = None
            for w in words:
                if w['text'] == '1.' and w['x0'] < 30:
                    baris_label_1 = w
                    break
            if baris_label_1 is None:
                return None

            top_baris = baris_label_1['top']
            # Toleransi 3pt untuk variasi kecil posisi vertikal antar kata
            # dalam baris yang sama (baseline font kadang sedikit berbeda).
            kata_sebaris = [
                w for w in words
                if abs(w['top'] - top_baris) <= 3 and w['x0'] > 250
            ]
            # Nomor pendaftaran adalah kata PALING KANAN di baris ini yang
            # murni digit (>= 6 karakter) -- kolom kanan pada baris field
            # PENGIRIM tidak punya konten lain selain nomor ini.
            kandidat_angka = [w for w in kata_sebaris if re.fullmatch(r"\d{6,}", w['text'])]
            if not kandidat_angka:
                return None
            kandidat_terkanan = max(kandidat_angka, key=lambda w: w['x0'])
            return kandidat_terkanan['text']
    except Exception:
        return None


def extract_pib_nopen(file_bytes):
    teks = _extract_text_all_pages(file_bytes)
    hasil = {}

    # Tgl PIB & AJU PIB : "Nomor Pengajuan :00002001000020250207005447 Tanggal Pengajuan :10-02-2025"
    hasil['aju_pib'] = _cari(r"Nomor Pengajuan\s*:\s*(\d+)", teks)
    tgl_pib_raw = _cari(r"Tanggal Pengajuan\s*:\s*(\d{2}-\d{2}-\d{4})", teks)
    hasil['tgl_pib'] = _parse_tanggal_ddmmyyyy(tgl_pib_raw)

    # No Pen PIB: nomor yang menumpuk secara visual di baris yang sama
    # dengan field "1. Nama, Alamat" (PENGIRIM), di kolom kanan halaman
    # (field G "Nomor dan Tanggal Pendaftaran"). Diambil berdasarkan posisi
    # koordinat kata di halaman (lihat _ekstrak_no_pen_pib_dari_koordinat),
    # BUKAN regex pada teks yang sudah diratakan lewat layout=True -- pemisah
    # sebelum nomor (koma, jumlah spasi) terbukti tidak konsisten antar
    # dokumen dan tidak bisa diandalkan sebagai penanda posisi.
    hasil['no_pen_pib'] = _ekstrak_no_pen_pib_dari_koordinat(file_bytes)

    # Tgl No Pen PIB tetap diambil dari teks biasa (baris "G. Nomor dan
    # Tanggal Pendaftaran <tanggal>"), karena label & tanggalnya SELALU
    # berdekatan langsung tanpa ambiguitas spasi.
    hasil['tgl_no_pen_pib'] = _parse_tanggal_ddmmyyyy(
        _cari(r"Nomor dan Tanggal Pendaftaran\s+(\d{2}-\d{2}-\d{4})", teks)
    )

    # PENGIRIM = "1. Nama, Alamat" ; PEMASOK = "1a. Nama, Alamat" -- HANYA
    # baris pertama (nama perusahaan sampai koma penutup, mis. "BEST SIGN
    # ASIA CHEMICAL PTE . LTD .,"), TANPA baris alamat lanjutannya, sesuai
    # permintaan agar nilai field ini tidak terlalu panjang.
    def _ambil_nama_baris_pertama(label_pattern):
        m_label = re.search(rf"{label_pattern}\s*:\s*([^\n]*)\n", teks, flags=re.IGNORECASE)
        if not m_label:
            return None
        baris_pertama = m_label.group(1)
        # Buang nomor pendaftaran PIB yang menumpuk di ujung baris pertama (field "1")
        baris_pertama = re.sub(r",?\s*\d{6,}\s*$", "", baris_pertama).strip()
        # Rapikan koma/spasi trailing di ujung (mis. "... LTD . ,\u00a0\u00a0" -> "... LTD .,")
        baris_pertama = re.sub(r"\s*,\s*$", ",", baris_pertama).strip()
        return baris_pertama if baris_pertama else None

    hasil['pengirim'] = _ambil_nama_baris_pertama(r"1\.\s*Nama,\s*Alamat")
    hasil['pemasok'] = _ambil_nama_baris_pertama(r"1a\.\s*Nama,\s*Alamat")

    # KOMODITI = "Uraian :" pada bagian rincian barang (bukan "Uraian Jenis
    # Barang" di header tabel kolom 32). Baris pertama dipotong sebelum
    # kolom kanan (PPH.../PPN...) mulai menumpuk; baris kedua ("IN BULK")
    # juga dipotong sebelum kolom kanan (PPN...).
    baris_komoditi_1 = _cari(r"^\s*Uraian\s*:\s*(.+?)(?:\s+PPH\s|\s+PPN\s|$)", teks, flags=re.MULTILINE)
    m_uraian = re.search(r"^\s*Uraian\s*:.*\n", teks, flags=re.MULTILINE)
    baris_komoditi_2 = None
    if m_uraian:
        baris_setelah = teks[m_uraian.end():].split("\n")[0]
        m2 = re.match(r"\s*(.+?)(?:\s{2,}\S|\s+PPN\s|$)", baris_setelah)
        if m2:
            baris_komoditi_2 = m2.group(1).strip()
    if baris_komoditi_1:
        bagian = [baris_komoditi_1.strip()]
        if baris_komoditi_2 and not baris_komoditi_2.lower().startswith('merk'):
            bagian.append(baris_komoditi_2)
        teks_komoditi_asli = " ".join(bagian)
        # Petakan ke singkatan (ZA, PA, NH4Cl, PR, MOP, DAP, SA) berdasarkan
        # awalan teks; kosongkan kalau tidak ada yang cocok.
        hasil['komoditi'] = _petakan_komoditi(teks_komoditi_asli)

    # ASAL NEGARA = "Negara : CHINA (CN)" pada bagian rincian barang (bukan
    # field lain yang kebetulan memuat kata "Negara")
    hasil['asal_negara'] = _cari(r"Negara\s*:\s*([A-Za-z ]+?)\s*\([A-Z]{2}\)", teks)
    if not hasil.get('asal_negara'):
        hasil['asal_negara'] = _cari(r"Negara\s*:\s*([^\n]+)", teks)

    # Port of Load = "Pelabuhan Muat"
    hasil['port_of_load'] = _cari(r"Pelabuhan Muat\s*:\s*([A-Za-z ]+?)\s+[A-Z]{5}", teks)
    if not hasil.get('port_of_load'):
        hasil['port_of_load'] = _cari(r"Pelabuhan Muat\s*:\s*([^\n]+)", teks)

    # HS = "Pos Tarif" (nilai rincian barang, bukan header kolom 32)
    hasil['hs_code'] = _cari(r"Pos Tarif\s*:\s*(\d+)", teks)

    # Bea Masuk / PPN / PPh "Dibayar" -- baris "37. BM <dibayar> <ditanggung> ..."
    hasil['bea_masuk_rp'] = _parse_angka(_cari(r"37\.\s*BM\s+([\d,\.]+)", teks))
    hasil['ppn_rp'] = _parse_angka(_cari(r"41\.\s*PPN\s+([\d,\.]+)", teks))
    hasil['pph_rp'] = _parse_angka(_cari(r"43\.\s*PPh\s+([\d,\.]+)", teks))

    # BM % -- baris rincian barang "BM 0% 100% TID" (bukan header kolom)
    hasil['bm_persen'] = _parse_angka(_cari(r"\bBM\s+(\d+(?:\.\d+)?)\s*%\s+\d+%", teks))

    # INVOICE = field 26 "Nilai Pabean". Pada layout PIB ini, angka Nilai
    # Pabean (USD) muncul di baris field 23 "23. Nilai :CFR 3,467,200.00 26.
    # Nilai Pabean :" -- yaitu angka SEBELUM label "26. Nilai Pabean :",
    # bukan sesudahnya (nilai field 26 dalam Rupiah baru muncul 2 baris di
    # bawahnya sebagai "RP 56,466,819,200.00" pada baris field 25).
    hasil['invoice'] = _parse_angka(
        _cari(r"23\.\s*Nilai\s*:\s*[A-Z]+\s+([\d,\.]+)\s+26\.\s*Nilai Pabean", teks)
    )

    # Kurs = "NDPBM" -- angka muncul di baris BERIKUTNYA ("US DOLLAR   16286")
    hasil['kurs'] = _parse_angka(_cari(r"US DOLLAR\s+(\d[\d,\.]*)", teks))
    if hasil.get('kurs') is None:
        hasil['kurs'] = _parse_angka(_cari(r"NDPBM\s*:\s*([\d,\.]+)", teks))

    return hasil


# =============================================================================
# 2. SPJM (Surat Pemberitahuan Jalur Merah)
# =============================================================================
def extract_spjm(file_bytes):
    teks = _extract_text_all_pages(file_bytes)
    hasil = {}
    # SPJM field: "GRESIK, 06-05-2025" (tanggal penerbitan surat, di baris
    # sebelum tanda tangan) -- lebih diandalkan daripada "Nomor Pendaftaran
    # PIB : ... Tanggal :" karena field terakhir itu adalah tanggal PIB,
    # bukan tanggal SPJM.
    tgl_raw = _cari(r"GRESIK,\s*(\d{2}-\d{2}-\d{4})", teks)
    if not tgl_raw:
        # fallback ke tanggal setelah "Nomor Pendaftaran PIB"
        tgl_raw = _cari(r"Nomor Pendaftaran PIB\s*:\s*\d+\s*Tanggal\s*:\s*(\d{2}-\d{2}-\d{4})", teks)
    hasil['spjm'] = _parse_tanggal_ddmmyyyy(tgl_raw)
    return hasil


# =============================================================================
# 3. SKEP (Surat Persetujuan Penimbunan)
# =============================================================================
def extract_skep(file_bytes):
    teks = _extract_text_all_pages(file_bytes)
    hasil = {}
    # Tanggal pojok kanan atas, format "DD BULAN YYYY", pada baris yang sama
    # dengan "Nomor : S-xx/..."
    tgl_raw = _cari(
        r"Nomor\s*:\s*\S+.*?(\d{1,2}\s+[A-Za-z]+\s+\d{4})", teks
    )
    hasil['skep_bc'] = _parse_tanggal_bulan_indo(tgl_raw)
    return hasil


# =============================================================================
# 4. SPPB (Surat Persetujuan Pengeluaran Barang)
# =============================================================================
def extract_sppb(file_bytes):
    teks = _extract_text_all_pages(file_bytes)
    hasil = {}

    # No SPPB & Tgl SPPB dari baris "Nomor : 000088/KBC.1104/2025     Tanggal :
    # 13-02-2025" (baris SPPB, MUNCUL PERTAMA di dokumen -- beda dengan baris
    # berikutnya "Nomor Pendaftaran PIB : 000094  Tanggal : 13-02-2025" yang
    # harus DIABAIKAN).
    m_nomor_sppb = re.search(
        r"SURAT PERSETUJUAN PENGELUARAN BARANG.*?\n\s*Nomor\s*:\s*([^\s]+)\s+Tanggal\s*:\s*(\d{2}-\d{2}-\d{4})",
        teks, flags=re.IGNORECASE | re.DOTALL
    )
    if m_nomor_sppb:
        hasil['no_sppb'] = m_nomor_sppb.group(1).split('/')[0].strip()
        hasil['tgl_sppb'] = _parse_tanggal_ddmmyyyy(m_nomor_sppb.group(2))
    else:
        hasil['no_sppb'] = None
        hasil['tgl_sppb'] = None

    # Tgl ETA -- SPPB tidak eksplisit punya field ETA. Kolom paling dekat
    # maknanya adalah tanggal SPPB itu sendiri; diisi sama dengan tgl_sppb
    # sebagai pendekatan awal -- WAJIB dicek/dikoreksi manual oleh admin,
    # karena SPPB tidak selalu representatif untuk ETA aktual.
    hasil['tgl_eta'] = hasil['tgl_sppb']

    # QUANTITY (MT) = "Berat" -- dengan layout=True, label "Berat :" dan
    # angkanya bisa terpisah baris (kolom kanan lebih panjang dari kolom
    # kiri). Cari angka setelah label, boleh di baris yang sama atau baris
    # berikutnya.
    m_berat = re.search(r"Berat\s*:\s*\n?\s*([\d,\.]+)", teks, flags=re.IGNORECASE)
    if not m_berat:
        # fallback: angka format XX,XXX,XXX.XXXX (format berat Bea Cukai)
        # di baris manapun dalam dokumen
        m_berat = re.search(r"(\d{1,3}(?:,\d{3})+\.\d{4})", teks)
    hasil['quantity_mt'] = _quantity_hilangkan_7_nol(m_berat.group(1)) if m_berat else None

    return hasil


# =============================================================================
# 5. SPTNP (Surat Penetapan Tarif dan/atau Nilai Pabean)
# =============================================================================
def extract_sptnp(file_bytes):
    teks = _extract_text_all_pages(file_bytes)
    hasil = {}

    # No SPTNP = "Nomor" (baris "Nomor : 000078/KBC.1104/2025")
    hasil['no_sptnp'] = _cari(r"Nomor\s*:\s*([^\s]+)\s*\n\s*Tanggal", teks)

    # Tgl SPTNP = "Tanggal" (baris "Tanggal : 12-03-2025", tepat di bawah Nomor)
    tgl_raw = _cari(r"Nomor\s*:\s*[^\s]+\s*\n\s*Tanggal\s*:\s*(\d{2}-\d{2}-\d{4})", teks)
    hasil['tgl_sptnp'] = _parse_tanggal_ddmmyyyy(tgl_raw)

    # NILAI SPTNP = "JUMLAH KEKURANGAN/KELEBIHAN PEMBAYARAN" kolom KEKURANGAN
    # (angka PERTAMA setelah label tsb -- kolom kedua "Rp. 0" adalah KELEBIHAN)
    nilai_raw = _cari(
        r"JUMLAH KEKURANGAN/KELEBIHAN PEMBAYARAN\s+Rp\.\s*([\d,\.]+)",
        teks
    )
    hasil['nilai_sptnp'] = _parse_angka(nilai_raw)

    return hasil


# =============================================================================
# 6. INWARD MANIFEST (BC 1.1) -- perlu OCR (vector graphics, tanpa layer teks)
# =============================================================================
def extract_inward(file_bytes):
    hasil = {}

    # Beberapa dokumen INWARD (BC 1.1) ternyata punya layer teks NATIVE yang
    # bersih (bukan vector-graphics murni seperti contoh awal) -- dicoba
    # LEBIH DULU karena 100% akurat, tanpa risiko typo OCR (mis. "HAI" salah
    # baca jadi "HAl"). OCR hanya dipakai sebagai FALLBACK kalau dokumen
    # memang tidak punya teks sama sekali.
    teks_native = _extract_text_all_pages(file_bytes)
    if teks_native and len(teks_native.strip()) > 20:
        nama_kapal_raw = _cari(
            r"Nama Sarana Pengangkut\s*:\s*([A-Z][A-Za-z0-9 .,\-]+?)\s+Pelabuhan",
            teks_native
        )
        if nama_kapal_raw:
            hasil['nama_kapal'] = nama_kapal_raw.strip()
            return hasil

    # Fallback: OCR (dokumen tanpa layer teks sama sekali)
    try:
        teks_ocr = _ocr_all_pages(file_bytes)
    except Exception:
        hasil['nama_kapal'] = None
        return hasil

    # "Nama Sarana Pengangkul : MV, RUI AN" (OCR sering salah baca "Pengangkut"
    # jadi "Pengangkul" dan titik dua jadi koma -- regex dibuat toleran)
    nama_kapal_raw = _cari(
        r"Nama Sarana Pengangku[tl]\S*\s*[:;.,]?\s*([A-Z][A-Za-z0-9 .,\-]+?)(?:\s{2,}|\n|Pelabuhan)",
        teks_ocr
    )
    if nama_kapal_raw:
        # OCR kadang menyisipkan koma di antara "MV" dan nama kapal (mis.
        # "MV, RUI AN"); rapikan jadi "MV. RUI AN"
        nama_kapal_raw = re.sub(r"^MV[.,]\s*", "MV. ", nama_kapal_raw.strip())
    hasil['nama_kapal'] = nama_kapal_raw

    return hasil


# =============================================================================
# 7. LAPORAN PENIMBUNAN MV -- perlu OCR (hasil scan/foto)
# =============================================================================
def _ocr_baris_dengan_koordinat(file_bytes, resolution=200):
    """Menjalankan OCR dan mengembalikan list baris terekonstruksi lengkap
    dengan koordinat vertikalnya (top), bukan cuma teks polos. Setiap baris
    adalah dict {'top': int, 'text': str}, diurutkan berdasarkan top.

    Dipakai sebagai alternatif _ocr_all_pages() untuk dokumen yang label dan
    value-nya perlu dipasangkan berdasarkan KEDEKATAN POSISI VERTIKAL,
    karena urutan baris hasil OCR (top-to-bottom, left-to-right per blok)
    terbukti TIDAK SELALU merefleksikan urutan logis label->value pada
    dokumen dengan layout kolom (kadang label & value jadi satu baris utuh,
    kadang terpisah blok kolom kiri/kanan -- variasinya tidak konsisten
    antar dokumen meski templatenya sama)."""
    if not _OCR_AVAILABLE:
        raise RuntimeError(
            "Modul OCR (pytesseract/Pillow) tidak tersedia di lingkungan ini."
        )
    from collections import defaultdict

    semua_baris = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            im = page.to_image(resolution=resolution)
            pil_img = im.original
            data = pytesseract.image_to_data(pil_img, lang='eng', output_type=pytesseract.Output.DICT)
            n = len(data['text'])
            kelompok_baris = defaultdict(list)
            for i in range(n):
                t = data['text'][i].strip()
                if not t:
                    continue
                key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
                kelompok_baris[key].append((data['left'][i], t, data['top'][i]))
            for key in kelompok_baris:
                kata_terurut = sorted(kelompok_baris[key])
                top_baris = kata_terurut[0][2]
                teks_baris = " ".join(w[1] for w in kata_terurut)
                semua_baris.append({'top': top_baris, 'text': teks_baris})

    semua_baris.sort(key=lambda b: b['top'])
    return semua_baris


def _cari_value_terdekat(baris_list, label_key, toleransi_top=10):
    """Mencari baris label yang cocok (startswith, case-insensitive) dengan
    label_key, lalu mengembalikan VALUE-nya: bagian setelah ':' pada baris
    yang sama (kalau label & value menyatu 1 baris fisik), ATAU teks baris
    LAIN dengan 'top' paling dekat (dalam toleransi_top px) yang diawali
    ':'/'>'/';' (kalau value ada di baris/kolom terpisah). Mengembalikan
    None kalau label atau value tidak ditemukan."""
    baris_label = None
    for b in baris_list:
        if b['text'].lower().startswith(label_key.lower()):
            baris_label = b
            break
    if baris_label is None:
        return None

    # Kasus 1: value menyatu di baris yang sama, mis. "Kecamatan : Gresik"
    sisa_setelah_label = baris_label['text'][len(label_key):]
    m_sama_baris = re.search(r"[:>;]\s*(\S.*)$", sisa_setelah_label)
    if m_sama_baris:
        return m_sama_baris.group(1).strip()

    # Kasus 2: value ada di baris terpisah dengan top paling dekat, mis.
    # label di top=422 ("Nama Perusahaan Importir"), value di top=428
    # (": PT. Petrokimia Gresik") -- kolom kanan/baris terpisah.
    top_label = baris_label['top']
    kandidat_value = [
        b for b in baris_list
        if b is not baris_label
        and abs(b['top'] - top_label) <= toleransi_top
        and re.match(r"^[:>;]\s*\S", b['text'])
    ]
    if not kandidat_value:
        return None
    # Ambil yang top-nya PALING DEKAT ke label (untuk jaga-jaga kalau ada >1 kandidat)
    baris_value = min(kandidat_value, key=lambda b: abs(b['top'] - top_label))
    return re.sub(r"^[:>;]\s*", "", baris_value['text']).strip()


def extract_laporan_penimbunan(file_bytes):
    hasil = {}
    try:
        baris_list = _ocr_baris_dengan_koordinat(file_bytes)
    except Exception:
        for k in ('agent', 'gudang_timbun', 'start_bongkar', 'selesai_bongkar'):
            hasil[k] = None
        return hasil

    # AGENT = "Nama Pengangkut/kuasanya"
    hasil['agent'] = _cari_value_terdekat(baris_list, "Nama Pengangkut")

    # GUDANG TIMBUN = "Nama Tempat Penimbunan"
    hasil['gudang_timbun'] = _cari_value_terdekat(baris_list, "Nama Tempat Penimbunan")

    # START/SELESAI BONGKAR = "Tanggal dimulai s.d selesai pengawasan"
    tanggal_range = _cari_value_terdekat(baris_list, "Tanggal dimulai")
    if tanggal_range:
        tanggal_ditemukan = re.findall(r"(\d{2}-\d{2}-\d{4})", tanggal_range)
        if len(tanggal_ditemukan) >= 1:
            hasil['start_bongkar'] = _parse_tanggal_ddmmyyyy(tanggal_ditemukan[0])
        if len(tanggal_ditemukan) >= 2:
            hasil['selesai_bongkar'] = _parse_tanggal_ddmmyyyy(tanggal_ditemukan[1])

    return hasil


# =============================================================================
# GABUNGAN: PANGGIL SEMUA EKSTRAKSI SEKALIGUS
# =============================================================================
def extract_all(file_bytes_dict):
    """
    file_bytes_dict: dict dengan key salah satu dari
      'pib_nopen', 'spjm', 'skep', 'sppb', 'sptnp', 'inward', 'laporan_penimbunan'
    value = bytes isi file PDF (boleh sebagian key tidak ada / None, akan
    dilewati -- field terkait tidak diisi).

    Mengembalikan (hasil_dict, error_dict):
      hasil_dict berisi field yang berhasil diekstrak (key sama seperti
      EDITABLE_DB_COLUMNS di v_inklaring_detail.py).
      error_dict berisi {nama_dokumen: pesan_error} untuk dokumen yang gagal
      diproses sama sekali (mis. file korup / OCR tidak tersedia), supaya
      pemanggil bisa menampilkan peringatan tanpa menghentikan seluruh proses.
    """
    hasil = {}
    errors = {}

    ekstraktor_per_dokumen = {
        'pib_nopen': extract_pib_nopen,
        'spjm': extract_spjm,
        'skep': extract_skep,
        'sppb': extract_sppb,
        'sptnp': extract_sptnp,
        'inward': extract_inward,
        'laporan_penimbunan': extract_laporan_penimbunan,
    }

    for nama_dokumen, fn in ekstraktor_per_dokumen.items():
        file_bytes = file_bytes_dict.get(nama_dokumen)
        if not file_bytes:
            continue
        try:
            hasil_dokumen = fn(file_bytes)
            for k, v in hasil_dokumen.items():
                if v is not None:
                    hasil[k] = v
        except Exception as e:
            errors[nama_dokumen] = str(e)

    return hasil, errors