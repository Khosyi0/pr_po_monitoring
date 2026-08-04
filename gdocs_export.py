"""
gdocs_export.py - Generate Google Docs dari data komparasi harga bahan baku.

Menggantikan alur export Excel (openpyxl) dengan Google Docs, memakai:
  - Autentikasi OAuth 2.0 dengan refresh token (kredensial dibaca dari st.secrets)
  - Google Docs API  -> membuat dokumen, menyisipkan gambar/tabel/teks
  - Google Drive API -> memindahkan dokumen ke folder tujuan, mengatur permission,
                         dan menegakkan retensi maksimal N dokumen per bahan baku

Chart digambar ulang memakai Matplotlib (BUKAN Kaleido / plotly.io.write_image),
karena Kaleido terbukti tidak stabil di lingkungan Streamlit Community Cloud.
Hasilnya tidak 100% identik secara visual dengan chart Plotly interaktif di
Streamlit, namun tetap menyampaikan informasi tren yang sama.

CATATAN PENTING soal pilihan OAuth (bukan Service Account):
Google menerapkan managed org-policy constraint
`iam.managed.disableServiceAccountApiKeyCreation` yang aktif secara DEFAULT
untuk semua project tanpa Organization (termasuk semua project pribadi biasa).
Constraint ini tidak bisa dinonaktifkan lewat Console maupun gcloud CLI biasa
untuk project semacam itu, dan menyebabkan SEMUA Service Account (credentials
JSON key) ditolak (403 PERMISSION_DENIED) saat memanggil Docs/Drive API --
sudah diverifikasi terjadi konsisten di banyak percobaan. Karena itu modul ini
memakai OAuth 2.0 dengan refresh token (identitas akun Google pribadi),
yang TIDAK terkena constraint tersebut.

Proses "Allow" OAuth HANYA dilakukan SEKALI, secara manual, oleh admin/developer
lewat skrip terpisah (lihat setup_oauth.py) -- TIDAK PERNAH muncul sebagai
halaman login di aplikasi Streamlit yang dipakai user lain. Setelah refresh
token didapat sekali dan disimpan di st.secrets, seluruh proses generate
dokumen di aplikasi berjalan otomatis tanpa interaksi login apapun.

Prasyarat (lihat panduan setup terpisah & setup_oauth.py):
  - Google Cloud Project dengan Docs API & Drive API aktif
  - OAuth Client ID (tipe "Desktop app") + akun sendiri terdaftar sebagai Test User
  - Refresh token yang dihasilkan sekali lewat setup_oauth.py
  - st.secrets["google_docs_export"] berisi: folder_id, max_docs_per_bahan_baku,
    dan sub-tabel oauth dengan client_id, client_secret, refresh_token.
"""

import io
import matplotlib
matplotlib.use("Agg")  # backend non-interaktif, aman dipakai di server tanpa display
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import pandas as pd
import streamlit as st
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]

TOKEN_URI = "https://oauth2.googleapis.com/token"

DEFAULT_MAX_DOCS_PER_BAHAN_BAKU = 3


# =============================================================================
# AUTENTIKASI & KLIEN API
# =============================================================================
def _get_credentials():
    """
    Membangun kredensial OAuth dari refresh token yang tersimpan di st.secrets.
    Access token baru akan otomatis di-generate ulang dari refresh token setiap
    kali dibutuhkan (refresh token itu sendiri tidak kadaluarsa dalam pemakaian
    normal), sehingga tidak perlu login interaktif sama sekali di aplikasi ini.
    """
    oauth_cfg = st.secrets["google_docs_export"]["oauth"]
    creds = Credentials(
        token=None,
        refresh_token=oauth_cfg["refresh_token"],
        token_uri=TOKEN_URI,
        client_id=oauth_cfg["client_id"],
        client_secret=oauth_cfg["client_secret"],
        scopes=SCOPES,
    )
    # Paksa refresh sekarang supaya access token siap dipakai segera;
    # google-api-python-client sebenarnya bisa auto-refresh sendiri saat
    # dibutuhkan, tapi refresh eksplisit di sini membuat error autentikasi
    # (mis. refresh token dicabut/invalid) langsung ketahuan lebih awal
    # dengan pesan yang jelas, bukan tersembunyi di tengah proses lain.
    creds.refresh(GoogleAuthRequest())
    return creds


def _get_docs_service():
    creds = _get_credentials()
    return build("docs", "v1", credentials=creds, cache_discovery=False)


def _get_drive_service():
    creds = _get_credentials()
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _get_config():
    cfg = st.secrets["google_docs_export"]
    folder_id = cfg["folder_id"]
    max_docs = int(cfg.get("max_docs_per_bahan_baku", DEFAULT_MAX_DOCS_PER_BAHAN_BAKU))
    return folder_id, max_docs


# =============================================================================
# RENDER CHART -> PNG (Matplotlib, tanpa Kaleido)
# =============================================================================
def render_chart_matplotlib(df_plot_chart, y_col, y_label, jenis_harga, label_bb, warna_map,
                             label_harga_perolehan=None):
    """
    Menggambar ulang chart komparasi harga sebagai PNG memakai Matplotlib.
    df_plot_chart: DataFrame dengan kolom ['tanggal_terbit', 'label_komparasi', y_col]
                   (boleh sudah termasuk baris Harga Perolehan).
    Mengembalikan bytes PNG.
    """
    # Seluruh tanggal unik pada data, dipakai sebagai tick sumbu X supaya SEMUA
    # tanggal publikasi tampil (bukan cuma sebagian yang dipilih otomatis oleh
    # Matplotlib), sama seperti perilaku chart Plotly di Streamlit.
    tanggal_unik = sorted(df_plot_chart['tanggal_terbit'].unique())

    # Lebar figure menyesuaikan jumlah tanggal, supaya label vertikal tetap
    # cukup renggang dan tidak saling menumpuk ketika datanya banyak.
    # Faktor dinaikkan lagi karena font tick label tanggal diperbesar signifikan.
    lebar_figure = max(24, len(tanggal_unik) * 0.45)
    fig, ax = plt.subplots(figsize=(lebar_figure, 14), dpi=150)

    for label, df_label in df_plot_chart.groupby('label_komparasi'):
        df_label = df_label.sort_values('tanggal_terbit')
        warna = warna_map.get(label, "#1f77b4")
        is_harga_perolehan = (label_harga_perolehan is not None and label == label_harga_perolehan)
        ax.plot(
            df_label['tanggal_terbit'], df_label[y_col],
            label=label, color=warna,
            linestyle="--" if is_harga_perolehan else "-",
            linewidth=2.2 if is_harga_perolehan else 2.0,
            marker="o", markersize=3,
        )

        # Label angka pada titik data terakhir garis ini, warna teks mengikuti
        # warna garisnya, supaya nilai terkini langsung terbaca di gambar statis.
        titik_terakhir = df_label.iloc[-1]
        ax.annotate(
            f"{titik_terakhir[y_col]:.2f}",
            xy=(titik_terakhir['tanggal_terbit'], titik_terakhir[y_col]),
            xytext=(6, 0), textcoords="offset points",
            va="center", ha="left",
            fontsize=24, fontweight="bold", color=warna,
        )

    # Beri sedikit ruang ekstra di kanan supaya label titik terakhir tidak terpotong
    ax.margins(x=0.02)

    ax.set_title(f"Komparasi Tren Harga {label_bb} ({jenis_harga})", fontsize=24, fontweight="bold")
    ax.set_xlabel("Tanggal Publikasi", fontsize=16)
    ax.set_ylabel(y_label, fontsize=18)
    ax.grid(True, axis="y", color="#e0e0e0", linewidth=0.8)
    ax.tick_params(axis="y", labelsize=11)

    # Paksa sumbu X menampilkan SEMUA tanggal unik sebagai tick, dengan label
    # tegak lurus (rotasi 90 derajat, bukan miring) -- konsisten dengan chart
    # Plotly di Streamlit yang juga menampilkan seluruh tanggal secara vertikal.
    # Fontsize dibuat signifikan lebih besar sesuai permintaan (fokus utama:
    # label tanggal dan legend, dibanding elemen chart lainnya).
    ax.set_xticks(tanggal_unik)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b %Y"))
    plt.setp(ax.get_xticklabels(), rotation=90, ha="center", va="top", fontsize=18)

    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.55), ncol=2, fontsize=20, frameon=False)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


# =============================================================================
# RETENSI: maksimal N dokumen per bahan baku dalam 1 folder Drive
# =============================================================================
def _judul_dengan_tag(label_bb, jenis_harga, start_date, end_date):
    """
    Judul dokumen diberi tag [label_bb] di depan supaya bisa dicari & dihitung
    oleh mekanisme retensi, tanpa perlu tabel pelacak terpisah di database.
    """
    return f"[{label_bb}] Komparasi Harga {label_bb} ({jenis_harga}) - {start_date} s.d. {end_date}"


def _enforce_retensi(drive_service, folder_id, label_bb, max_docs):
    """
    Mencari semua dokumen di folder tujuan yang judulnya diawali tag [label_bb],
    lalu jika jumlahnya sudah >= max_docs, hapus dokumen-dokumen tertua sampai
    tersisa (max_docs - 1) -- supaya setelah dokumen baru dibuat, totalnya
    kembali menjadi max_docs.
    """
    query = (
        f"'{folder_id}' in parents "
        f"and mimeType = 'application/vnd.google-apps.document' "
        f"and name contains '[{label_bb}]' "
        f"and trashed = false"
    )
    response = drive_service.files().list(
        q=query,
        fields="files(id, name, createdTime)",
        orderBy="createdTime asc",
        pageSize=100,
    ).execute()
    files = response.get("files", [])

    jumlah_saat_ini = len(files)
    if jumlah_saat_ini >= max_docs:
        jumlah_harus_dihapus = jumlah_saat_ini - max_docs + 1
        file_terlama = files[:jumlah_harus_dihapus]
        for f in file_terlama:
            try:
                drive_service.files().delete(fileId=f["id"]).execute()
            except Exception:
                # Kalau gagal hapus salah satu (mis. sudah terhapus manual), lanjut saja
                pass


# =============================================================================
# BANGUN GOOGLE DOC
# =============================================================================
def _upload_image_ke_drive_sementara(drive_service, image_bytes, nama_file):
    """
    Google Docs API membutuhkan gambar berupa URI publik untuk insertInlineImage,
    bukan bytes langsung. Jadi gambar diupload dulu sebagai file terpisah ke Drive,
    dibuat bisa diakses publik, dipakai untuk insertInlineImage, lalu dihapus
    setelah tidak diperlukan lagi (Docs API sudah meng-copy gambarnya ke dalam
    dokumen saat insert, jadi file sementara ini aman dihapus setelahnya).
    """
    media = MediaIoBaseUpload(io.BytesIO(image_bytes), mimetype="image/png", resumable=False)
    file_metadata = {"name": nama_file}
    uploaded = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    file_id = uploaded["id"]

    drive_service.permissions().create(
        fileId=file_id,
        body={"role": "reader", "type": "anyone"},
    ).execute()

    image_uri = f"https://drive.google.com/uc?id={file_id}"
    return file_id, image_uri


def _hapus_file_drive(drive_service, file_id):
    try:
        drive_service.files().delete(fileId=file_id).execute()
    except Exception:
        pass


def generate_google_doc(
    label_bb, jenis_harga, start_date, end_date,
    image_bytes, df_pivot, kolom_tanggal, list_resume,
):
    """
    Membuat 1 Google Doc baru berisi: judul, gambar chart, tabel histori data,
    dan resume otomatis. Mengembalikan URL dokumen yang bisa dibuka siapa saja
    (anyone with link can view).

    df_pivot     : sama seperti dipakai generate_excel_export (index=label_komparasi,
                   columns=tanggal_terbit, values=harga_range string "min - max")
    kolom_tanggal: list label tanggal yang sudah diformat, sejajar dengan df_pivot.columns
    list_resume  : list string poin-poin resume
    """
    folder_id, max_docs = _get_config()
    docs_service = _get_docs_service()
    drive_service = _get_drive_service()

    _enforce_retensi(drive_service, folder_id, label_bb, max_docs)

    judul = _judul_dengan_tag(label_bb, jenis_harga, start_date, end_date)

    # 1. Buat dokumen baru (otomatis masuk ke My Drive milik service account)
    doc = docs_service.documents().create(body={"title": judul}).execute()
    document_id = doc["documentId"]

    # 2. Pindahkan dokumen ke folder tujuan
    file_info = drive_service.files().get(fileId=document_id, fields="parents").execute()
    current_parents = ",".join(file_info.get("parents", []))
    drive_service.files().update(
        fileId=document_id,
        addParents=folder_id,
        removeParents=current_parents,
        fields="id, parents",
    ).execute()

    # 3. Upload gambar chart sebagai file sementara di Drive (dibutuhkan Docs API)
    temp_image_id, image_uri = _upload_image_ke_drive_sementara(
        drive_service, image_bytes, f"_temp_chart_{document_id}.png"
    )

    # 4. Susun request Docs API: judul, gambar, tabel, resume
    requests = []

    requests.append({
        "insertText": {
            "location": {"index": 1},
            "text": f"{judul}\n\n",
        }
    })

    # Tebalkan baris judul saja
    requests.append({
        "updateTextStyle": {
            "range": {"startIndex": 1, "endIndex": 1 + len(judul)},
            "textStyle": {"bold": True, "fontSize": {"magnitude": 16, "unit": "PT"}},
            "fields": "bold,fontSize",
        }
    })

    insert_index = 1 + len(judul) + 2  # setelah judul + 2 karakter newline

    requests.append({
        "insertInlineImage": {
            "location": {"index": insert_index},
            "uri": image_uri,
            "objectSize": {
                "height": {"magnitude": 300, "unit": "PT"},
                "width": {"magnitude": 480, "unit": "PT"},
            },
        }
    })

    docs_service.documents().batchUpdate(
        documentId=document_id, body={"requests": requests}
    ).execute()

    # 5. Sisipkan judul tabel + tabel histori data (request terpisah karena butuh
    #    index posisi terbaru setelah gambar disisipkan)
    doc_setelah_gambar = docs_service.documents().get(documentId=document_id).execute()
    end_index = doc_setelah_gambar["body"]["content"][-1]["endIndex"] - 1

    n_rows = len(df_pivot) + 2  # +2 untuk 2 baris header (Referensi/Harga USD/MT, lalu tanggal)
    n_cols = len(kolom_tanggal) + 1  # +1 untuk kolom "Referensi"

    requests_tabel = [
        {
            "insertText": {
                "location": {"index": end_index},
                "text": "\nDetail Histori Data (3 Periode Terakhir)\n",
            }
        },
        {
            "insertTable": {
                "location": {"index": end_index + 1 + len("Detail Histori Data (3 Periode Terakhir)\n")},
                "rows": n_rows,
                "columns": n_cols,
            }
        },
    ]
    docs_service.documents().batchUpdate(
        documentId=document_id, body={"requests": requests_tabel}
    ).execute()

    # 6. Isi tiap sel tabel. Struktur tabel di Docs API butuh index tiap sel
    #    yang dihitung ulang dari dokumen terbaru (paling aman: ambil ulang
    #    struktur tabel setelah insertTable, lalu isi dari sel PALING AKHIR
    #    ke awal supaya index sel sebelumnya tidak bergeser).
    doc_dengan_tabel = docs_service.documents().get(documentId=document_id).execute()
    tabel_element = None
    tabel_element_start_index = None
    for elem in doc_dengan_tabel["body"]["content"]:
        if "table" in elem:
            tabel_element = elem["table"]
            tabel_element_start_index = elem["startIndex"]

    if tabel_element is not None:
        header_row_1 = ["Referensi"] + ["Harga USD/MT"] + [""] * (n_cols - 2)
        header_row_2 = [""] + kolom_tanggal
        data_rows = []
        for label_idx, row in df_pivot.iterrows():
            baris = [str(label_idx)]
            for col in df_pivot.columns:
                val = row[col]
                baris.append("" if val is None or (isinstance(val, float) and val != val) else str(val))
            data_rows.append(baris)

        semua_baris_isi = [header_row_1, header_row_2] + data_rows

        requests_isi = []
        table_rows = tabel_element["tableRows"]
        # Isi dari baris & kolom TERAKHIR ke PALING AWAL supaya index tidak bergeser
        for r_idx in reversed(range(len(table_rows))):
            cells = table_rows[r_idx]["tableCells"]
            for c_idx in reversed(range(len(cells))):
                teks = semua_baris_isi[r_idx][c_idx] if c_idx < len(semua_baris_isi[r_idx]) else ""
                if not teks:
                    continue
                cell_start_index = cells[c_idx]["content"][0]["startIndex"]
                requests_isi.append({
                    "insertText": {
                        "location": {"index": cell_start_index},
                        "text": teks,
                    }
                })

        if requests_isi:
            docs_service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests_isi}
            ).execute()

        # 6a. Rata tengah SECARA VERTIKAL untuk seluruh sel tabel (header maupun
        # data), supaya teks tidak menempel ke bagian atas sel. Ini dilakukan
        # untuk SELURUH tabel sebelum merge, karena merge hanya mengubah
        # rowSpan/columnSpan dan tidak mempengaruhi contentAlignment yang sudah
        # di-set sebelumnya pada rentang sel yang tercakup.
        docs_service.documents().batchUpdate(
            documentId=document_id,
            body={"requests": [{
                "updateTableCellStyle": {
                    "tableCellStyle": {
                        "contentAlignment": "MIDDLE",
                        "paddingTop": {"magnitude": 2.835, "unit": "PT"},
                        "paddingBottom": {"magnitude": 2.835, "unit": "PT"},
                        "paddingLeft": {"magnitude": 2.835, "unit": "PT"},
                        "paddingRight": {"magnitude": 2.835, "unit": "PT"}
                    },
                    "tableRange": {
                        "tableCellLocation": {
                            "tableStartLocation": {"index": tabel_element_start_index},
                            "rowIndex": 0,
                            "columnIndex": 0,
                        },
                        "rowSpan": n_rows,
                        "columnSpan": n_cols,
                    },
                    "fields": "contentAlignment,paddingTop,paddingBottom,paddingLeft,paddingRight",
                }
            }]}
        ).execute()

        # 6b. Styling header tabel: merge sel "Referensi" (2 baris) & "Harga USD/MT"
        # (merentang semua kolom tanggal), lalu beri background biru muda, bold,
        # dan rata tengah pada seluruh baris header (2 baris pertama).
        HEADER_BG_COLOR = {"red": 0.741, "green": 0.843, "blue": 0.933}  # biru muda ala #BDD7EE

        requests_style = []

        # Merge kolom "Referensi" (kolom ke-0) pada baris header 1 & 2 menjadi satu sel
        requests_style.append({
            "mergeTableCells": {
                "tableRange": {
                    "tableCellLocation": {
                        "tableStartLocation": {"index": tabel_element_start_index},
                        "rowIndex": 0,
                        "columnIndex": 0,
                    },
                    "rowSpan": 2,
                    "columnSpan": 1,
                }
            }
        })

        # Merge baris header 1 pada kolom ke-1 sampai akhir menjadi satu sel "Harga USD/MT"
        if n_cols > 2:
            requests_style.append({
                "mergeTableCells": {
                    "tableRange": {
                        "tableCellLocation": {
                            "tableStartLocation": {"index": tabel_element_start_index},
                            "rowIndex": 0,
                            "columnIndex": 1,
                        },
                        "rowSpan": 1,
                        "columnSpan": n_cols - 1,
                    }
                }
            })

        # Background biru muda untuk seluruh baris header (baris index 0 dan 1)
        requests_style.append({
            "updateTableCellStyle": {
                "tableCellStyle": {
                    "backgroundColor": {"color": {"rgbColor": HEADER_BG_COLOR}},
                },
                "tableRange": {
                    "tableCellLocation": {
                        "tableStartLocation": {"index": tabel_element_start_index},
                        "rowIndex": 0,
                        "columnIndex": 0,
                    },
                    "rowSpan": 2,
                    "columnSpan": n_cols,
                },
                "fields": "backgroundColor",
            }
        })

        docs_service.documents().batchUpdate(
            documentId=document_id, body={"requests": requests_style}
        ).execute()

        # 6c. Bold + rata tengah untuk teks di baris header & rata tengah untuk kolom harga
        # (dilakukan SETELAH merge, karena index paragraph di dalam sel perlu 
        # diambil ulang dari struktur tabel terbaru pasca-merge).
        doc_setelah_merge = docs_service.documents().get(documentId=document_id).execute()
        tabel_setelah_merge = None
        for elem in doc_setelah_merge["body"]["content"]:
            if "table" in elem:
                tabel_setelah_merge = elem["table"]

        requests_text_style = []
        if tabel_setelah_merge is not None:
            # --- STYLING HEADER (2 Baris Pertama) ---
            header_rows = tabel_setelah_merge["tableRows"][:2]
            for row in header_rows:
                for cell in row["tableCells"]:
                    for content_elem in cell.get("content", []):
                        paragraph = content_elem.get("paragraph")
                        if not paragraph:
                            continue
                        para_start = content_elem["startIndex"]
                        para_end = content_elem["endIndex"]
                        
                        # Rata tengah paragraf untuk semua sel header
                        requests_text_style.append({
                            "updateParagraphStyle": {
                                "range": {"startIndex": para_start, "endIndex": para_end},
                                "paragraphStyle": {"alignment": "CENTER"},
                                "fields": "alignment",
                            }
                        })
                        
                        # Bold teks (kalau ada isinya, endIndex > startIndex+1 karena newline)
                        if para_end - 1 > para_start:
                            requests_text_style.append({
                                "updateTextStyle": {
                                    "range": {"startIndex": para_start, "endIndex": para_end - 1},
                                    "textStyle": {"bold": True},
                                    "fields": "bold",
                                }
                            })

            # --- STYLING ISI DATA (Baris ke-3 dan seterusnya) ---
            data_rows = tabel_setelah_merge["tableRows"][2:]
            for row in data_rows:
                # Mulai dari index ke-1, karena index 0 adalah "Referensi" (tetap dibiarkan rata kiri)
                for cell in row["tableCells"][1:]:
                    for content_elem in cell.get("content", []):
                        paragraph = content_elem.get("paragraph")
                        if not paragraph:
                            continue
                        para_start = content_elem["startIndex"]
                        para_end = content_elem["endIndex"]
                        
                        # Rata tengah paragraf untuk kolom berisi angka harga
                        requests_text_style.append({
                            "updateParagraphStyle": {
                                "range": {"startIndex": para_start, "endIndex": para_end},
                                "paragraphStyle": {"alignment": "CENTER"},
                                "fields": "alignment",
                            }
                        })

        if requests_text_style:
            docs_service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests_text_style}
            ).execute()

    # 7. Sisipkan resume di akhir dokumen
    doc_akhir = docs_service.documents().get(documentId=document_id).execute()
    end_index_final = doc_akhir["body"]["content"][-1]["endIndex"] - 1

    teks_resume = "\nResume:\n" + "\n".join([f"•  {poin}" for poin in list_resume]) + "\n"
    docs_service.documents().batchUpdate(
        documentId=document_id,
        body={"requests": [{
            "insertText": {"location": {"index": end_index_final}, "text": teks_resume}
        }]}
    ).execute()

    # 8. Bersihkan file gambar sementara (Docs sudah meng-copy gambarnya ke dalam dokumen)
    _hapus_file_drive(drive_service, temp_image_id)

    # 9. Set permission dokumen: siapa saja dengan link bisa melihat
    drive_service.permissions().create(
        fileId=document_id,
        body={"role": "reader", "type": "anyone"},
    ).execute()

    doc_url = f"https://docs.google.com/document/d/{document_id}/edit"
    return doc_url

def generate_google_doc_batch(
    start_date, end_date, jenis_harga, list_data_batch
):
    """
    Membuat 1 Google Doc yang berisi kompilasi beberapa bahan baku secara berurutan.
    list_data_batch adalah list of dictionary dengan format:
    {
        "label_bb": str,
        "image_bytes": bytes,
        "df_pivot": DataFrame,
        "kolom_tanggal": list,
        "list_resume": list
    }
    """
    folder_id, max_docs = _get_config()
    docs_service = _get_docs_service()
    drive_service = _get_drive_service()

    # Pakai tag [BATCH] untuk membedakan dengan dokumen satuan
    judul = f"[BATCH] Kompilasi Harga Bahan Baku ({jenis_harga}) - {start_date} s.d. {end_date}"
    
    # Enforce retensi khusus dokumen batch agar tidak menumpuk
    _enforce_retensi(drive_service, folder_id, "BATCH", max_docs)

    # 1. Buat dokumen & pindahkan ke folder
    doc = docs_service.documents().create(body={"title": judul}).execute()
    document_id = doc["documentId"]
    
    file_info = drive_service.files().get(fileId=document_id, fields="parents").execute()
    current_parents = ",".join(file_info.get("parents", []))
    drive_service.files().update(
        fileId=document_id,
        addParents=folder_id,
        removeParents=current_parents,
        fields="id, parents",
    ).execute()

    # 2. Tulis Judul Utama Dokumen
    docs_service.documents().batchUpdate(
        documentId=document_id, 
        body={"requests": [
            {
                "insertText": {"location": {"index": 1}, "text": f"{judul}\n\n"}
            },
            {
                "updateTextStyle": {
                    "range": {"startIndex": 1, "endIndex": 1 + len(judul)},
                    "textStyle": {"bold": True, "fontSize": {"magnitude": 18, "unit": "PT"}},
                    "fields": "bold,fontSize",
                }
            }
        ]}
    ).execute()

    # 3. Iterasi untuk setiap bahan baku dan sisipkan ke bagian bawah dokumen (append)
    for idx, data_bb in enumerate(list_data_batch):
        label_bb = data_bb["label_bb"]
        df_pivot = data_bb["df_pivot"]
        kolom_tanggal = data_bb["kolom_tanggal"]
        list_resume = data_bb["list_resume"]
        image_bytes = data_bb["image_bytes"]

        # Upload gambar ke Drive (sementara)
        temp_image_id, image_uri = _upload_image_ke_drive_sementara(
            drive_service, image_bytes, f"_temp_batch_{idx}_{document_id}.png"
        )

        # A. Sisipkan Judul Bahan Baku & Gambar
        doc_current = docs_service.documents().get(documentId=document_id).execute()
        end_idx = doc_current["body"]["content"][-1]["endIndex"] - 1

        req_header_img = [
            {"insertText": {"location": {"index": end_idx}, "text": f"\n{idx+1}. Komparasi Harga {label_bb}\n\n"}},
            {"updateTextStyle": {
                "range": {"startIndex": end_idx + 1, "endIndex": end_idx + 1 + len(f"{idx+1}. Komparasi Harga {label_bb}")},
                "textStyle": {"bold": True, "fontSize": {"magnitude": 14, "unit": "PT"}},
                "fields": "bold,fontSize"
            }},
            {"insertInlineImage": {
                "location": {"index": end_idx + 1 + len(f"{idx+1}. Komparasi Harga {label_bb}\n")},
                "uri": image_uri,
                "objectSize": {"height": {"magnitude": 300, "unit": "PT"}, "width": {"magnitude": 480, "unit": "PT"}}
            }}
        ]
        docs_service.documents().batchUpdate(documentId=document_id, body={"requests": req_header_img}).execute()

        # B. Sisipkan Tabel
        doc_current = docs_service.documents().get(documentId=document_id).execute()
        end_idx = doc_current["body"]["content"][-1]["endIndex"] - 1
        
        n_rows = len(df_pivot) + 2
        n_cols = len(kolom_tanggal) + 1
        req_tabel = [
            {"insertText": {"location": {"index": end_idx}, "text": "\nDetail Histori Data (3 Periode Terakhir)\n"}},
            {"insertTable": {"location": {"index": end_idx + len("\nDetail Histori Data (3 Periode Terakhir)\n")}, "rows": n_rows, "columns": n_cols}}
        ]
        docs_service.documents().batchUpdate(documentId=document_id, body={"requests": req_tabel}).execute()

        # C. Isi & Style Tabel
        doc_current = docs_service.documents().get(documentId=document_id).execute()
        
        # Cari tabel TERAKHIR yang baru saja disisipkan
        tabel_element = None
        tabel_start_index = None
        for elem in reversed(doc_current["body"]["content"]):
            if "table" in elem:
                tabel_element = elem["table"]
                tabel_start_index = elem["startIndex"]
                break

        if tabel_element:
            # Siapkan data baris
            header_1 = ["Referensi"] + ["Harga USD/MT"] + [""] * (n_cols - 2)
            header_2 = [""] + kolom_tanggal
            data_rows = []
            for label_idx, row in df_pivot.iterrows():
                baris = [str(label_idx)]
                for col in df_pivot.columns:
                    val = row[col]
                    baris.append("" if pd.isna(val) else str(val))
                data_rows.append(baris)
            semua_baris = [header_1, header_2] + data_rows

            req_isi = []
            table_rows = tabel_element["tableRows"]
            for r_idx in reversed(range(len(table_rows))):
                for c_idx in reversed(range(len(table_rows[r_idx]["tableCells"]))):
                    teks = semua_baris[r_idx][c_idx] if c_idx < len(semua_baris[r_idx]) else ""
                    if teks:
                        cell_start = table_rows[r_idx]["tableCells"][c_idx]["content"][0]["startIndex"]
                        req_isi.append({"insertText": {"location": {"index": cell_start}, "text": teks}})
            if req_isi:
                docs_service.documents().batchUpdate(documentId=document_id, body={"requests": req_isi}).execute()

            # Merge & Style Header Tabel
            HEADER_BG_COLOR = {"red": 0.741, "green": 0.843, "blue": 0.933}
            req_style = [
                # Vertical align middle & atur Padding 0.1cm untuk semua sel
                {
                    "updateTableCellStyle": {
                        "tableCellStyle": {
                            "contentAlignment": "MIDDLE",
                            "paddingTop": {"magnitude": 2.835, "unit": "PT"},
                            "paddingBottom": {"magnitude": 2.835, "unit": "PT"},
                            "paddingLeft": {"magnitude": 2.835, "unit": "PT"},
                            "paddingRight": {"magnitude": 2.835, "unit": "PT"}
                        },
                        "tableRange": {
                            "tableCellLocation": {
                                "tableStartLocation": {"index": tabel_start_index}, 
                                "rowIndex": 0, 
                                "columnIndex": 0
                            }, 
                            "rowSpan": n_rows, 
                            "columnSpan": n_cols
                        }, 
                        "fields": "contentAlignment,paddingTop,paddingBottom,paddingLeft,paddingRight"
                    }
                },
                # Merge 'Referensi'
                {"mergeTableCells": {"tableRange": {"tableCellLocation": {"tableStartLocation": {"index": tabel_start_index}, "rowIndex": 0, "columnIndex": 0}, "rowSpan": 2, "columnSpan": 1}}},
                # BG Color header
                {"updateTableCellStyle": {"tableCellStyle": {"backgroundColor": {"color": {"rgbColor": HEADER_BG_COLOR}}}, "tableRange": {"tableCellLocation": {"tableStartLocation": {"index": tabel_start_index}, "rowIndex": 0, "columnIndex": 0}, "rowSpan": 2, "columnSpan": n_cols}, "fields": "backgroundColor"}},
            ]
            if n_cols > 2:
                # Merge 'Harga USD/MT'
                req_style.append({"mergeTableCells": {"tableRange": {"tableCellLocation": {"tableStartLocation": {"index": tabel_start_index}, "rowIndex": 0, "columnIndex": 1}, "rowSpan": 1, "columnSpan": n_cols - 1}}})
            docs_service.documents().batchUpdate(documentId=document_id, body={"requests": req_style}).execute()

            # Center text di header & data
            doc_current = docs_service.documents().get(documentId=document_id).execute()
            tabel_element = next(elem["table"] for elem in reversed(doc_current["body"]["content"]) if "table" in elem)
            
            req_text_center = []
            # Header text (bold & center)
            for row in tabel_element["tableRows"][:2]:
                for cell in row["tableCells"]:
                    for content in cell.get("content", []):
                        if "paragraph" in content:
                            start, end = content["startIndex"], content["endIndex"]
                            req_text_center.append({"updateParagraphStyle": {"range": {"startIndex": start, "endIndex": end}, "paragraphStyle": {"alignment": "CENTER"}, "fields": "alignment"}})
                            if end - 1 > start:
                                req_text_center.append({"updateTextStyle": {"range": {"startIndex": start, "endIndex": end - 1}, "textStyle": {"bold": True}, "fields": "bold"}})
            # Data text (center hanya angka harga, index [1:])
            for row in tabel_element["tableRows"][2:]:
                for cell in row["tableCells"][1:]:
                    for content in cell.get("content", []):
                        if "paragraph" in content:
                            start, end = content["startIndex"], content["endIndex"]
                            req_text_center.append({"updateParagraphStyle": {"range": {"startIndex": start, "endIndex": end}, "paragraphStyle": {"alignment": "CENTER"}, "fields": "alignment"}})
            if req_text_center:
                docs_service.documents().batchUpdate(documentId=document_id, body={"requests": req_text_center}).execute()

        # D. Sisipkan Resume
        doc_current = docs_service.documents().get(documentId=document_id).execute()
        end_idx = doc_current["body"]["content"][-1]["endIndex"] - 1
        teks_resume = "\nResume:\n" + "\n".join([f"•  {poin}" for poin in list_resume]) + "\n\n"
        docs_service.documents().batchUpdate(documentId=document_id, body={"requests": [{"insertText": {"location": {"index": end_idx}, "text": teks_resume}}]}).execute()

        # Hapus gambar sementara
        _hapus_file_drive(drive_service, temp_image_id)

    # 4. Buka akses publik
    drive_service.permissions().create(fileId=document_id, body={"role": "reader", "type": "anyone"}).execute()
    
    return f"https://docs.google.com/document/d/{document_id}/edit"