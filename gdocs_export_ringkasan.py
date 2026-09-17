"""
gdocs_export_ringkasan.py - Generate Google Docs dari isi tab Ringkasan
halaman "Kondisi Stock BB" (v_kondisi_stock_bb.py).

Berbeda dari gdocs_export.py (yang dipakai v_bb_bahan_baku.py, isinya HANYA
1 tabel histori harga + 1 chart komparasi per bahan baku), dokumen di sini
per produk berisi:
  1. Judul produk (mis. "1. Asam Sulfat")
  2. Kalimat pembuka "Kondisi Balansitas <Produk> mengacu balans update
     tanggal <tanggal generate>."
  3. Tabel Ringkasan -- PERSIS sama seperti yang tampil di web: baris
     kategori (Stok Awal, Produksi, dst) DISISIPI baris shipment
     ("- Suplier" / "Origin : X") pada posisi yang sama seperti di web
     (lihat PRODUK_KE_KOMODITAS_RBB di v_kondisi_stock_bb.py).
  4. 2 chart berdampingan (side-by-side) dalam 1 baris tabel 1x2 tanpa
     border: kiri = chart Stock harian (Safety Stock vs Stock PG, digambar
     ulang dgn Matplotlib), kanan = chart Komparasi Harga Pasar Bahan Baku
     (dipakai ulang dari gdocs_export.render_chart_matplotlib).

Modul ini MENGIMPOR ULANG (reuse) fungsi-fungsi generik dari gdocs_export.py
yang sudah ada -- autentikasi, retensi dokumen, styling tabel (lebar kolom,
margin halaman, font Arial 11pt), upload gambar sementara -- supaya tidak
menduplikasi logika yang sudah teruji, dan konsisten stylingnya dengan
dokumen v_bb_bahan_baku.py.

Dokumen disimpan ke folder Google Drive terpisah dari gdocs_export.py biasa
(folder_id dikonfigurasi lewat st.secrets["google_docs_export_ringkasan"]).
"""

import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker

import pandas as pd
import streamlit as st

import gdocs_export  # reuse: auth, retensi, styling tabel generik, render chart komparasi


DEFAULT_MAX_DOCS_RINGKASAN = 5


def _get_config_ringkasan():
    cfg = st.secrets["google_docs_export_ringkasan"]
    folder_id = cfg["folder_id"]
    max_docs = int(cfg.get("max_docs", DEFAULT_MAX_DOCS_RINGKASAN))
    return folder_id, max_docs


# =============================================================================
# RENDER CHART STOCK HARIAN -> PNG (Matplotlib)
# =============================================================================
def render_chart_stock_matplotlib(df_chart, nama_produk):
    """
    Menggambar ulang chart 'Stock <Produk>' (Safety Stock vs Stock PG, atau
    beberapa jenis spt KCL Merah/Putih) sbg PNG memakai Matplotlib, meniru
    tampilan chart Altair di web (line chart, legend di bawah).

    df_chart: DataFrame dgn kolom ['jenis', 'tanggal', 'safety_stock', 'stock_pg'],
    sama seperti hasil _get_data_chart_harian di v_kondisi_stock_bb.py.
    Mengembalikan bytes PNG, atau None kalau df_chart kosong.
    """
    if df_chart is None or df_chart.empty:
        return None

    fig, ax = plt.subplots(figsize=(9, 6.5), dpi=150)

    daftar_jenis = sorted(df_chart['jenis'].unique())

    if daftar_jenis == ['default']:
        df_sorted = df_chart.sort_values('tanggal')
        ax.plot(df_sorted['tanggal'], df_sorted['safety_stock'], label='Safety Stock', color='#4A90D9', linewidth=2)
        ax.plot(df_sorted['tanggal'], df_sorted['stock_pg'], label='Stock PG', color='#E24949', linewidth=2)
    else:
        palet = ['#4A90D9', '#E24949', '#5AAE61', '#F4A340', '#9970AB']
        idx_warna = 0
        for jenis in daftar_jenis:
            df_j = df_chart[df_chart['jenis'] == jenis].sort_values('tanggal')
            ax.plot(df_j['tanggal'], df_j['safety_stock'], label=f'Safety Stock {jenis}',
                    color=palet[idx_warna % len(palet)], linewidth=2)
            idx_warna += 1
            ax.plot(df_j['tanggal'], df_j['stock_pg'], label=f'Stock PG {jenis}',
                    color=palet[idx_warna % len(palet)], linewidth=2)
            idx_warna += 1

    ax.set_title(f"Stock {nama_produk}", fontsize=15, fontweight="bold", loc="left")
    ax.set_xlabel("Tanggal", fontsize=11)
    ax.set_ylabel("Jumlah Stock", fontsize=11)
    ax.grid(True, axis="y", color="#e5e5e5", linewidth=0.8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    plt.setp(ax.get_xticklabels(), rotation=0, ha="center", fontsize=9)
    ax.tick_params(axis="y", labelsize=9)

    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2, fontsize=10, frameon=False, title="Kategori")
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


# =============================================================================
# BANGUN TABEL RINGKASAN (kategori + shipment, persis seperti di web)
# =============================================================================
def _siapkan_baris_tabel_ringkasan(tabel_gabungan):
    """
    tabel_gabungan: DataFrame index=Keterangan (bisa berisi tag HTML <br>
    utk baris shipment 2-baris & isi multi-baris), kolom=label bulan.
    Dikembalikan sbg list of list of string, dgn <br> dikonversi jadi '\n'
    (baris baru literal di dalam sel Google Docs -- Docs API mendukung '\n'
    sbg line break di dalam 1 sel tabel, cukup insertText biasa).
    """
    header = ["Keterangan"] + list(tabel_gabungan.columns)
    baris_list = [header]
    for idx, row in tabel_gabungan.iterrows():
        baris = [str(idx).replace("<br>", "\n")]
        for col in tabel_gabungan.columns:
            val = row[col]
            val_str = "" if val is None or (isinstance(val, float) and pd.isna(val)) else str(val)
            baris.append(val_str.replace("<br>", "\n"))
        baris_list.append(baris)
    return baris_list


# =============================================================================
# LEBAR KOLOM KHUSUS TABEL RINGKASAN
# =============================================================================
# Tabel Ringkasan BERBEDA karakter dari tabel histori harga di gdocs_export.py:
# - Kolom "Keterangan" isinya CAMPURAN: label kategori pendek (mis. "Stok
#   Awal") dan label shipment yang bisa panjang (mis. "- Mltrausaha / Amman
#   Origin : Indonesia (1)"). Kalau lebar kolom ini dihitung dari label
#   TERPANJANG (spt gdocs_export._hitung_lebar_kolom_referensi, yang dirancang
#   utk kasus semua baris kurang lebih sepadan panjangnya), maka SEMUA baris
#   ikut melebar mengikuti 1 outlier -- menyisakan banyak ruang kosong di
#   baris2 lain yang labelnya pendek (persis masalah yang terlihat di
#   screenshot: kolom Keterangan lebar dgn banyak whitespace).
# - Kolom bulan isinya JUGA bisa multi-baris panjang (Depart/ETA/MV/USD),
#   bukan cuma format harga pendek "1000.00 - 1100.00" spt tabel histori.
#
# Solusi: kolom "Keterangan" diberi lebar TETAP yang wajar (bukan mengikuti
# label terpanjang) -- label yang lebih panjang dari itu di-wrap ke baris
# berikutnya di dalam sel (sudah didukung Google Docs table secara native).
# Kolom bulan diberi lebar lebih lega drpd default tabel histori, supaya
# baris shipment yang multi-baris (Depart/ETA/MV/USD) lebih nyaman dibaca.
LEBAR_KOLOM_KETERANGAN_RINGKASAN_PT = 140
LEBAR_KOLOM_BULAN_RINGKASAN_PT = 130


def _hitung_lebar_kolom_tabel_ringkasan(n_cols):
    """Lebar kolom [Keterangan, bulan1, bulan2, ...] utk tabel Ringkasan --
    lihat penjelasan lengkap di komentar atas konstanta terkait."""
    n_kolom_bulan = max(n_cols - 1, 1)
    lebar_kolom = [LEBAR_KOLOM_KETERANGAN_RINGKASAN_PT] + [LEBAR_KOLOM_BULAN_RINGKASAN_PT] * n_kolom_bulan
    return lebar_kolom, sum(lebar_kolom)


def _requests_atur_lebar_kolom_ringkasan(tabel_start_index, n_cols):
    lebar_kolom, total_lebar = _hitung_lebar_kolom_tabel_ringkasan(n_cols)
    requests = []
    for c_idx, lebar in enumerate(lebar_kolom):
        requests.append({
            "updateTableColumnProperties": {
                "tableStartLocation": {"index": tabel_start_index},
                "columnIndices": [c_idx],
                "tableColumnProperties": {
                    "widthType": "FIXED_WIDTH",
                    "width": {"magnitude": lebar, "unit": "PT"},
                },
                "fields": "widthType,width",
            }
        })
    return requests, total_lebar


def _insert_tabel_ringkasan(docs_service, document_id, tabel_gabungan):
    """
    Menyisipkan tabel Ringkasan (kategori + shipment) ke akhir dokumen,
    dengan styling: header row background biru muda + bold + center, lebar
    kolom TETAP yang wajar (lihat _hitung_lebar_kolom_tabel_ringkasan --
    BUKAN dinamis dari label terpanjang seperti tabel histori harga, karena
    isi kolom "Keterangan" di sini campuran pendek & panjang), font Arial
    11pt di seluruh sel (reuse gdocs_export._requests_font_tabel).

    Mengembalikan tabel_start_index (dipakai kalau perlu referensi lanjutan,
    walau di alur normal tidak diperlukan lagi setelah ini).
    """
    baris_list = _siapkan_baris_tabel_ringkasan(tabel_gabungan)
    n_rows = len(baris_list)
    n_cols = len(baris_list[0])

    doc_current = docs_service.documents().get(documentId=document_id).execute()
    end_index = doc_current["body"]["content"][-1]["endIndex"] - 1

    docs_service.documents().batchUpdate(
        documentId=document_id,
        body={"requests": [{
            "insertTable": {
                "location": {"index": end_index},
                "rows": n_rows,
                "columns": n_cols,
            }
        }]}
    ).execute()

    doc_dengan_tabel = docs_service.documents().get(documentId=document_id).execute()
    tabel_element = None
    tabel_start_index = None
    for elem in doc_dengan_tabel["body"]["content"]:
        if "table" in elem:
            tabel_element = elem["table"]
            tabel_start_index = elem["startIndex"]

    if tabel_element is None:
        return None

    # -- Lebar kolom TETAP (bukan dinamis dari label terpanjang) --
    requests_lebar_kolom, total_lebar = _requests_atur_lebar_kolom_ringkasan(
        tabel_start_index, n_cols
    )
    requests_margin = gdocs_export._requests_atur_margin_halaman(total_lebar)
    docs_service.documents().batchUpdate(
        documentId=document_id,
        body={"requests": requests_margin + requests_lebar_kolom}
    ).execute()

    # -- Isi tiap sel, dari baris & kolom TERAKHIR ke AWAL supaya index tidak bergeser --
    requests_isi = []
    table_rows = tabel_element["tableRows"]
    for r_idx in reversed(range(len(table_rows))):
        cells = table_rows[r_idx]["tableCells"]
        for c_idx in reversed(range(len(cells))):
            teks = baris_list[r_idx][c_idx] if c_idx < len(baris_list[r_idx]) else ""
            if not teks:
                continue
            cell_start_index = cells[c_idx]["content"][0]["startIndex"]
            requests_isi.append({
                "insertText": {"location": {"index": cell_start_index}, "text": teks}
            })
    if requests_isi:
        docs_service.documents().batchUpdate(
            documentId=document_id, body={"requests": requests_isi}
        ).execute()

    # -- Vertical align + padding kecil utk seluruh sel --
    docs_service.documents().batchUpdate(
        documentId=document_id,
        body={"requests": [{
            "updateTableCellStyle": {
                "tableCellStyle": {
                    "contentAlignment": "MIDDLE",
                    "paddingTop": {"magnitude": 2.835, "unit": "PT"},
                    "paddingBottom": {"magnitude": 2.835, "unit": "PT"},
                    "paddingLeft": {"magnitude": 2, "unit": "PT"},
                    "paddingRight": {"magnitude": 2, "unit": "PT"},
                },
                "tableRange": {
                    "tableCellLocation": {
                        "tableStartLocation": {"index": tabel_start_index},
                        "rowIndex": 0, "columnIndex": 0,
                    },
                    "rowSpan": n_rows, "columnSpan": n_cols,
                },
                "fields": "contentAlignment,paddingTop,paddingBottom,paddingLeft,paddingRight",
            }
        }]}
    ).execute()

    # -- Background biru muda + bold + center utk baris header --
    HEADER_BG_COLOR = {"red": 0.741, "green": 0.843, "blue": 0.933}
    docs_service.documents().batchUpdate(
        documentId=document_id,
        body={"requests": [{
            "updateTableCellStyle": {
                "tableCellStyle": {"backgroundColor": {"color": {"rgbColor": HEADER_BG_COLOR}}},
                "tableRange": {
                    "tableCellLocation": {
                        "tableStartLocation": {"index": tabel_start_index},
                        "rowIndex": 0, "columnIndex": 0,
                    },
                    "rowSpan": 1, "columnSpan": n_cols,
                },
                "fields": "backgroundColor",
            }
        }]}
    ).execute()

    doc_setelah_bg = docs_service.documents().get(documentId=document_id).execute()
    tabel_final = None
    for elem in doc_setelah_bg["body"]["content"]:
        if "table" in elem:
            tabel_final = elem["table"]

    requests_text_style = []
    if tabel_final is not None:
        header_row = tabel_final["tableRows"][0]
        for cell in header_row["tableCells"]:
            for content_elem in cell.get("content", []):
                paragraph = content_elem.get("paragraph")
                if not paragraph:
                    continue
                para_start = content_elem["startIndex"]
                para_end = content_elem["endIndex"]
                requests_text_style.append({
                    "updateParagraphStyle": {
                        "range": {"startIndex": para_start, "endIndex": para_end},
                        "paragraphStyle": {"alignment": "CENTER"},
                        "fields": "alignment",
                    }
                })
                if para_end - 1 > para_start:
                    requests_text_style.append({
                        "updateTextStyle": {
                            "range": {"startIndex": para_start, "endIndex": para_end - 1},
                            "textStyle": {"bold": True},
                            "fields": "bold",
                        }
                    })

        # Kolom bulan (selain kolom 0 "Keterangan") rata tengah utk semua baris data
        for row in tabel_final["tableRows"][1:]:
            for cell in row["tableCells"][1:]:
                for content_elem in cell.get("content", []):
                    paragraph = content_elem.get("paragraph")
                    if not paragraph:
                        continue
                    para_start = content_elem["startIndex"]
                    para_end = content_elem["endIndex"]
                    requests_text_style.append({
                        "updateParagraphStyle": {
                            "range": {"startIndex": para_start, "endIndex": para_end},
                            "paragraphStyle": {"alignment": "CENTER"},
                            "fields": "alignment",
                        }
                    })

        # Font Arial 11pt di seluruh sel (reuse fungsi generik)
        requests_text_style.extend(gdocs_export._requests_font_tabel(tabel_final))

    if requests_text_style:
        docs_service.documents().batchUpdate(
            documentId=document_id, body={"requests": requests_text_style}
        ).execute()

    return tabel_start_index


def _insert_dua_chart_berdampingan(docs_service, drive_service, document_id,
                                     image_bytes_kiri, image_bytes_kanan):
    """
    Menyisipkan 2 gambar chart berdampingan memakai tabel 1 baris x 2 kolom
    TANPA border (border width 0), supaya secara visual terlihat seperti
    2 chart bersebelahan seperti tampilan web (bukan 2 tabel bergaris).
    Kalau salah satu gambar None (mis. tidak ada data), sel itu dikosongkan.
    """
    doc_current = docs_service.documents().get(documentId=document_id).execute()
    end_index = doc_current["body"]["content"][-1]["endIndex"] - 1

    docs_service.documents().batchUpdate(
        documentId=document_id,
        body={"requests": [{
            "insertTable": {"location": {"index": end_index}, "rows": 1, "columns": 2}
        }]}
    ).execute()

    doc_dengan_tabel = docs_service.documents().get(documentId=document_id).execute()
    tabel_element = None
    tabel_start_index = None
    for elem in doc_dengan_tabel["body"]["content"]:
        if "table" in elem:
            tabel_element = elem["table"]
            tabel_start_index = elem["startIndex"]

    if tabel_element is None:
        return

    # Hilangkan border tabel (semua sisi, width 0, warna putih) supaya
    # terlihat seperti 2 chart bersebelahan, bukan tabel bergaris.
    no_border = {"color": {"color": {"rgbColor": {"red": 1, "green": 1, "blue": 1}}}, "width": {"magnitude": 0, "unit": "PT"}, "dashStyle": "SOLID"}
    docs_service.documents().batchUpdate(
        documentId=document_id,
        body={"requests": [{
            "updateTableCellStyle": {
                "tableCellStyle": {
                    "borderLeft": no_border, "borderRight": no_border,
                    "borderTop": no_border, "borderBottom": no_border,
                    "paddingLeft": {"magnitude": 4, "unit": "PT"},
                    "paddingRight": {"magnitude": 4, "unit": "PT"},
                },
                "tableRange": {
                    "tableCellLocation": {"tableStartLocation": {"index": tabel_start_index}, "rowIndex": 0, "columnIndex": 0},
                    "rowSpan": 1, "columnSpan": 2,
                },
                "fields": "borderLeft,borderRight,borderTop,borderBottom,paddingLeft,paddingRight",
            }
        }]}
    ).execute()

    cells = tabel_element["tableRows"][0]["tableCells"]
    # Isi dari kanan ke kiri supaya index sel kiri tidak bergeser
    for c_idx, image_bytes in [(1, image_bytes_kanan), (0, image_bytes_kiri)]:
        if not image_bytes:
            continue
        cell_start_index = cells[c_idx]["content"][0]["startIndex"]
        temp_image_id, image_uri = gdocs_export._upload_image_ke_drive_sementara(
            drive_service, image_bytes, f"_temp_ringkasan_{document_id}_{c_idx}.png"
        )
        docs_service.documents().batchUpdate(
            documentId=document_id,
            body={"requests": [{
                "insertInlineImage": {
                    "location": {"index": cell_start_index},
                    "uri": image_uri,
                    "objectSize": {
                        "height": {"magnitude": 170, "unit": "PT"},
                        "width": {"magnitude": 230, "unit": "PT"},
                    },
                }
            }]}
        ).execute()
        gdocs_export._hapus_file_drive(drive_service, temp_image_id)


# =============================================================================
# 1 PRODUK -> DIPANGGIL BAIK UTK DOKUMEN TUNGGAL MAUPUN BATCH
# =============================================================================
def _tulis_satu_produk(docs_service, drive_service, document_id, nomor_urut,
                        nama_produk, tabel_gabungan, tanggal_update_str,
                        df_chart_stock, image_bytes_komparasi):
    """
    Menulis 1 blok produk ke akhir dokumen yang SUDAH ADA (document_id):
    judul bernomor -> kalimat pembuka -> tabel Ringkasan -> 2 chart
    berdampingan. Dipakai baik oleh generate_google_doc_ringkasan (1 produk)
    maupun generate_google_doc_ringkasan_batch (banyak produk, dipanggil
    berulang dgn nomor_urut 1, 2, 3, ...).
    """
    doc_current = docs_service.documents().get(documentId=document_id).execute()
    end_index = doc_current["body"]["content"][-1]["endIndex"] - 1

    judul_produk = f"{nomor_urut}. {nama_produk}"
    kalimat_pembuka = f"Kondisi Balansitas {nama_produk} mengacu balans update tanggal {tanggal_update_str} :"
    teks_pembuka = f"{judul_produk}\n{kalimat_pembuka}\n"

    requests = [
        {"insertText": {"location": {"index": end_index}, "text": teks_pembuka}},
        {
            "updateTextStyle": {
                "range": {"startIndex": end_index, "endIndex": end_index + len(judul_produk)},
                "textStyle": {"bold": True, "fontSize": {"magnitude": 13, "unit": "PT"}},
                "fields": "bold,fontSize",
            }
        },
        {
            "updateTextStyle": {
                "range": {
                    "startIndex": end_index + len(judul_produk) + 1,
                    "endIndex": end_index + len(judul_produk) + 1 + len(kalimat_pembuka),
                },
                "textStyle": {"bold": True},
                "fields": "bold",
            }
        },
        {
            "updateParagraphStyle": {
                "range": {"startIndex": end_index, "endIndex": end_index + len(teks_pembuka)},
                "paragraphStyle": {"alignment": "START"},
                "fields": "alignment",
            }
        },
    ]
    docs_service.documents().batchUpdate(documentId=document_id, body={"requests": requests}).execute()

    # -- Tabel Ringkasan (kategori + shipment, persis seperti di web) --
    _insert_tabel_ringkasan(docs_service, document_id, tabel_gabungan)

    # -- 2 chart berdampingan --
    image_bytes_stock = render_chart_stock_matplotlib(df_chart_stock, nama_produk)
    doc_before_chart = docs_service.documents().get(documentId=document_id).execute()
    idx_before_chart = doc_before_chart["body"]["content"][-1]["endIndex"] - 1
    docs_service.documents().batchUpdate(
        documentId=document_id,
        body={"requests": [{"insertText": {"location": {"index": idx_before_chart}, "text": "\n"}}]}
    ).execute()
    _insert_dua_chart_berdampingan(
        docs_service, drive_service, document_id, image_bytes_stock, image_bytes_komparasi
    )

    # -- Spasi pemisah sebelum produk berikutnya --
    doc_after_chart = docs_service.documents().get(documentId=document_id).execute()
    idx_after_chart = doc_after_chart["body"]["content"][-1]["endIndex"] - 1
    docs_service.documents().batchUpdate(
        documentId=document_id,
        body={"requests": [{"insertText": {"location": {"index": idx_after_chart}, "text": "\n\n"}}]}
    ).execute()


# =============================================================================
# ENTRY POINT: 1 PRODUK
# =============================================================================
def generate_google_doc_ringkasan(nama_produk, tabel_gabungan, tanggal_update_str,
                                    df_chart_stock, image_bytes_komparasi):
    """
    Membuat 1 Google Doc baru berisi Ringkasan utk SATU produk terpilih.
    Mengembalikan URL dokumen.

    tabel_gabungan       : DataFrame (kategori+shipment) persis spt di web,
                            index=Keterangan (boleh ada tag <br>), kolom=label bulan.
    tanggal_update_str   : string tanggal generate, sudah diformat (mis. "16 September 2026")
    df_chart_stock       : DataFrame data harian (jenis/tanggal/safety_stock/stock_pg), boleh None/kosong
    image_bytes_komparasi: PNG bytes hasil gdocs_export.render_chart_matplotlib, boleh None
    """
    folder_id, max_docs = _get_config_ringkasan()
    docs_service = gdocs_export._get_docs_service()
    drive_service = gdocs_export._get_drive_service()

    gdocs_export._enforce_retensi(drive_service, folder_id, nama_produk, max_docs)

    judul_dokumen = f"[{nama_produk}] Ringkasan Kondisi Stock BB - {tanggal_update_str}"
    doc = docs_service.documents().create(body={"title": judul_dokumen}).execute()
    document_id = doc["documentId"]

    file_info = drive_service.files().get(fileId=document_id, fields="parents").execute()
    current_parents = ",".join(file_info.get("parents", []))
    drive_service.files().update(
        fileId=document_id, addParents=folder_id, removeParents=current_parents, fields="id, parents",
    ).execute()

    _tulis_satu_produk(
        docs_service, drive_service, document_id, 1, nama_produk,
        tabel_gabungan, tanggal_update_str, df_chart_stock, image_bytes_komparasi
    )

    drive_service.permissions().create(fileId=document_id, body={"role": "reader", "type": "anyone"}).execute()
    return f"https://docs.google.com/document/d/{document_id}/edit"


# =============================================================================
# ENTRY POINT: BATCH (SEMUA PRODUK)
# =============================================================================
def generate_google_doc_ringkasan_batch(list_data_produk, tanggal_update_str):
    """
    Membuat 1 Google Doc berisi Ringkasan utk BANYAK produk sekaligus,
    berurutan (1. Asam Sulfat, 2. Sulfur, dst -- urutan mengikuti urutan
    list_data_produk apa adanya, ditentukan pemanggil).

    list_data_produk: list of dict, tiap dict:
        {
            "nama_produk": str,
            "tabel_gabungan": DataFrame,
            "df_chart_stock": DataFrame atau None,
            "image_bytes_komparasi": bytes atau None,
        }
    Mengembalikan URL dokumen.
    """
    folder_id, max_docs = _get_config_ringkasan()
    docs_service = gdocs_export._get_docs_service()
    drive_service = gdocs_export._get_drive_service()

    gdocs_export._enforce_retensi(drive_service, folder_id, "BATCH", max_docs)

    judul_dokumen = f"[BATCH] Ringkasan Kondisi Stock BB - {tanggal_update_str}"
    doc = docs_service.documents().create(body={"title": judul_dokumen}).execute()
    document_id = doc["documentId"]

    file_info = drive_service.files().get(fileId=document_id, fields="parents").execute()
    current_parents = ",".join(file_info.get("parents", []))
    drive_service.files().update(
        fileId=document_id, addParents=folder_id, removeParents=current_parents, fields="id, parents",
    ).execute()

    for i, data in enumerate(list_data_produk, start=1):
        _tulis_satu_produk(
            docs_service, drive_service, document_id, i,
            data["nama_produk"], data["tabel_gabungan"], tanggal_update_str,
            data.get("df_chart_stock"), data.get("image_bytes_komparasi"),
        )

    drive_service.permissions().create(fileId=document_id, body={"role": "reader", "type": "anyone"}).execute()
    return f"https://docs.google.com/document/d/{document_id}/edit"