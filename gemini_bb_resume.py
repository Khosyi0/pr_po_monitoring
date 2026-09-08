"""
gemini_bb_resume.py - Resume otomatis (naratif, tidak kaku) memakai Gemini API.

Menggantikan `hitung_resume_generik` yang berbasis template string statis,
dengan resume yang ditulis oleh LLM (Gemini) supaya bahasanya lebih natural
dan enak dibaca atasan, tapi tetap akurat terhadap data.

Prinsip desain:
1. KONTEKS DIBATASI 3 PERIODE PUBLIKASI TERAKHIR
   Model hanya diberi tahu data pada 3 tanggal publikasi TERAKHIR yang ada
   pada df_plot_komparasi (dihitung dari seluruh referensi, bukan per
   referensi), persis sama dengan data yang tampil di tabel "Detail Histori
   Data (3 Periode Terakhir)" pada dokumen -- supaya narasi resume selalu
   konsisten dengan tabel yang dilihat pembaca, bukan mengacu ke rentang
   waktu yang berbeda (mis. 3 bulan) yang bisa membuat resume menyebut
   angka/tanggal yang tidak ada di tabel.

2. REFERENSI YANG TIDAK PUNYA DATA DI 3 PERIODE TSB
   Kalau suatu referensi (Majalah - Incoterm) TIDAK punya rilis harga pada
   salah satu dari 3 tanggal publikasi acuan (mis. publikasinya jarang /
   sudah lama tidak update), titik data TERAKHIR yang tersedia (walau lebih
   lama dari 3 periode acuan) tetap disertakan ke konteks, supaya AI tidak
   menganggap referensi tsb tidak punya data sama sekali. Ini sama seperti
   perilaku lama di `hitung_resume_generik` yang menyebutkan "referensi X
   terakhir rilis pada tanggal Y".

3. TIDAK ADA PANGGILAN OTOMATIS SAAT HALAMAN DIMUAT
   Modul ini HANYA dipanggil ketika user menekan tombol "Generate Resume AI"
   atau saat proses Generate Docs berjalan dan resume belum pernah dibuat
   (lihat pemanggilannya di analisis_bahan_baku.py). Modul ini sendiri tidak
   tahu soal state Streamlit -- murni fungsi query data + panggil API.

Prasyarat: st.secrets["gemini"]["api_key"] berisi API key Gemini.
"""

import json
import re

import pandas as pd
import streamlit as st

BULAN_INDO = {
    1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 5: 'Mei', 6: 'Juni',
    7: 'Juli', 8: 'Agustus', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
}

# Jumlah tanggal publikasi terakhir yang dipakai sebagai konteks resume --
# HARUS sama dengan jumlah kolom periode pada tabel "Detail Histori Data"
# di dokumen (saat ini 3 periode terakhir), supaya narasi resume selalu
# konsisten dengan tabel yang tampil.
JUMLAH_PERIODE_KONTEKS = 3

# Model Gemini yang dipakai. gemini-2.5-flash dipilih karena cepat & murah,
# cukup untuk tugas menulis ringkasan naratif pendek berbasis data terstruktur.
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)


def _format_tanggal_indo(dt):
    dt = pd.Timestamp(dt)
    return f"{dt.day:02d} {BULAN_INDO[dt.month]} {dt.year}"


def _susun_konteks_periode_terakhir(df_plot, y_col):
    """
    Menyusun ringkasan data historis per referensi (label_komparasi), dibatasi
    HANYA pada JUMLAH_PERIODE_KONTEKS tanggal publikasi TERAKHIR yang ada di
    seluruh df_plot -- persis sama dengan tanggal-tanggal yang dipakai pada
    tabel "Detail Histori Data (3 Periode Terakhir)" di dokumen.

    Untuk tiap referensi:
      - Ambil titik data pada tanggal-tanggal publikasi acuan tsb (kalau ada).
      - Kalau referensi tsb TIDAK punya rilis pada satu pun dari tanggal
        publikasi acuan (mis. publikasinya jarang), tetap sertakan titik data
        TERAKHIR yang tersedia (di luar tanggal-tanggal acuan), dengan catatan
        eksplisit bahwa data tsb "terakhir tersedia" -- supaya AI tahu itu
        bukan data pada periode acuan tapi tetap relevan disebutkan.

    df_plot HARUS sudah tidak mengandung baris Harga Perolehan (kalau ada,
    filter dulu sebelum memanggil fungsi ini), karena resume ini murni bicara
    soal komparasi Majalah - Incoterm.

    Mengembalikan dict:
    {
        "tanggal_acuan": Timestamp,        # tanggal publikasi paling baru di seluruh df_plot
        "tanggal_periode_acuan": [Timestamp, ...],  # N tanggal publikasi terakhir (urut lama->baru)
        "referensi": [
            {
                "label": str,
                "dalam_periode_acuan": bool,   # True kalau ada data pada tanggal2 acuan
                "titik_data": [ {"tanggal": "dd Mon yyyy", "harga": float}, ... ],
                # kalau dalam_periode_acuan == False, titik_data cuma berisi 1 entry
                # (titik data terakhir yang tersedia, di luar tanggal2 acuan)
            },
            ...
        ]
    }
    """
    if df_plot.empty:
        return None

    df_plot = df_plot.copy()
    df_plot['tanggal_terbit'] = pd.to_datetime(df_plot['tanggal_terbit'])

    tanggal_acuan = df_plot['tanggal_terbit'].max()

    # N tanggal publikasi UNIK terakhir di seluruh dataset (bukan per
    # referensi), sama seperti kolom-kolom periode pada tabel "Detail Histori
    # Data (3 Periode Terakhir)" -- diurutkan lama -> baru untuk narasi yang
    # kronologis.
    semua_tanggal_unik = sorted(df_plot['tanggal_terbit'].unique())
    tanggal_periode_acuan = semua_tanggal_unik[-JUMLAH_PERIODE_KONTEKS:]
    set_tanggal_periode_acuan = set(tanggal_periode_acuan)

    daftar_referensi = []
    for label, df_label in df_plot.groupby('label_komparasi'):
        df_label = df_label.sort_values('tanggal_terbit')
        df_dalam_periode = df_label[df_label['tanggal_terbit'].isin(set_tanggal_periode_acuan)]

        if not df_dalam_periode.empty:
            titik_data = [
                {"tanggal": _format_tanggal_indo(row['tanggal_terbit']), "harga": round(float(row[y_col]), 2)}
                for _, row in df_dalam_periode.iterrows()
            ]
            daftar_referensi.append({
                "label": label,
                "dalam_periode_acuan": True,
                "titik_data": titik_data,
            })
        else:
            # Tidak ada rilis pada tanggal-tanggal periode acuan -> tetap
            # pertahankan titik data TERAKHIR yang tersedia (walau lebih
            # lama), supaya AI tidak kehilangan konteks referensi ini sama
            # sekali.
            baris_terakhir = df_label.iloc[-1]
            daftar_referensi.append({
                "label": label,
                "dalam_periode_acuan": False,
                "titik_data": [{
                    "tanggal": _format_tanggal_indo(baris_terakhir['tanggal_terbit']),
                    "harga": round(float(baris_terakhir[y_col]), 2),
                }],
            })

    return {
        "tanggal_acuan": tanggal_acuan,
        "tanggal_periode_acuan": tanggal_periode_acuan,
        "referensi": daftar_referensi,
    }


def _bangun_prompt(label_bb, jenis_harga, konteks, config):
    """Menyusun prompt teks untuk Gemini dari hasil _susun_konteks_periode_terakhir."""
    tanggal_acuan_str = _format_tanggal_indo(konteks["tanggal_acuan"])
    daftar_tanggal_periode_str = ", ".join(
        _format_tanggal_indo(t) for t in konteks["tanggal_periode_acuan"]
    )

    bagian_data = []
    for ref in konteks["referensi"]:
        if ref["dalam_periode_acuan"]:
            titik_str = "; ".join(f"{t['tanggal']}: USD {t['harga']}/MT" for t in ref["titik_data"])
            bagian_data.append(f"- {ref['label']} (data pada periode acuan): {titik_str}")
        else:
            t = ref["titik_data"][0]
            bagian_data.append(
                f"- {ref['label']} (TIDAK ADA rilis pada periode acuan; "
                f"data terakhir yang tersedia): {t['tanggal']}: USD {t['harga']}/MT"
            )

    teks_data = "\n".join(bagian_data)

    kalimat_dampak = config.get("kalimat_dampak")
    konteks_dampak = (
        f"Jika relevan, boleh disinggung singkat dampaknya terhadap biaya produksi {kalimat_dampak}."
        if kalimat_dampak else ""
    )

    prompt = f"""Kamu adalah analis harga komoditas bahan baku pupuk. Tulis resume tren harga pasar untuk bahan baku "{label_bb}" (jenis harga: {jenis_harga}) dalam Bahasa Indonesia, berdasarkan data berikut.

Tanggal acuan (data terbaru): {tanggal_acuan_str}
Periode acuan (persis sama dengan tabel "Detail Histori Data" pada dokumen): {daftar_tanggal_periode_str}

Data per referensi (Majalah - Incoterm), HANYA mencakup periode acuan di atas:
{teks_data}

Instruksi penulisan:
1. Tulis dalam bentuk poin-poin (bullet), MAKSIMAL 4 poin, masing-masing 1-3 kalimat.
2. Fokus membahas tren pergerakan harga PADA PERIODE ACUAN DI ATAS SAJA: naik/turun/stabil, seberapa signifikan, dan konteks singkat penyebab jika bisa disimpulkan dari data (tanpa mengarang angka, tanggal, atau berita eksternal yang tidak ada di data). JANGAN merujuk ke tren jangka panjang atau tanggal di luar periode acuan yang diberikan.
3. Gaya bahasa naratif, profesional, TIDAK kaku/template, enak dibaca oleh manajemen. Hindari mengulang struktur kalimat yang sama persis di tiap poin.
4. Kalau ada referensi yang tidak punya rilis pada periode acuan, sebutkan itu di salah satu poin secara singkat (mis. "referensi X terakhir merilis harga pada tanggal Y"), tapi jangan jadikan itu poin utama.
5. Jangan gunakan angka atau tanggal yang tidak ada di data di atas. Semua klaim harus bisa ditelusuri ke data yang diberikan.
6. {konteks_dampak}
7. JANGAN gunakan markdown heading, JANGAN beri judul "Resume:", langsung mulai dari poin pertama.

Format output WAJIB berupa JSON array of string, tanpa teks lain di luar JSON. Contoh format:
["Poin pertama...", "Poin kedua...", "Poin ketiga..."]
"""
    return prompt


def _parse_response_json(teks_response):
    """
    Mem-parsing output Gemini menjadi list string. Menangani kemungkinan
    model membungkus JSON dengan ```json ... ``` fences.
    """
    teks_bersih = teks_response.strip()
    teks_bersih = re.sub(r"^```(json)?", "", teks_bersih.strip())
    teks_bersih = re.sub(r"```$", "", teks_bersih.strip())
    teks_bersih = teks_bersih.strip()

    try:
        hasil = json.loads(teks_bersih)
        if isinstance(hasil, list) and all(isinstance(x, str) for x in hasil):
            return hasil
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: kalau parsing JSON gagal, pecah per baris yang diawali bullet/dash
    baris_list = [
        re.sub(r"^[-•\*\d\.\)]+\s*", "", baris).strip()
        for baris in teks_bersih.splitlines()
        if baris.strip()
    ]
    baris_list = [b for b in baris_list if b]
    if baris_list:
        return baris_list

    raise ValueError("Gagal mem-parsing response Gemini menjadi daftar poin resume.")


def generate_resume_ai(df_plot_komparasi, y_col, label_bb, jenis_harga, config):
    """
    Fungsi utama: menyusun konteks 3 periode publikasi terakhir dari
    df_plot_komparasi (selaras dengan tabel "Detail Histori Data (3 Periode
    Terakhir)" di dokumen), memanggil Gemini API, dan mengembalikan list
    string poin-poin resume.

    df_plot_komparasi : DataFrame hasil filter komparasi Majalah-Incoterm
                         (TANPA baris Harga Perolehan), kolom minimal:
                         ['tanggal_terbit', 'label_komparasi', y_col]
    y_col              : nama kolom harga yang aktif ('harga_min'/'harga_max'/'harga_avg')
    label_bb           : label bahan baku (mis. "Ammonia")
    jenis_harga        : "MIN" / "MAX" / "AVERAGE"
    config             : entry BAHAN_BAKU_CONFIG bahan baku terkait

    Melempar Exception kalau gagal (API key tidak ada, request gagal, parsing
    gagal, dsb) -- pemanggil bertanggung jawab menangkap & menampilkan error
    ke user, supaya proses generate Google Docs tidak diam-diam memakai
    resume kosong/salah.
    """
    if df_plot_komparasi.empty:
        return ["Data tidak tersedia untuk periode ini."]

    konteks = _susun_konteks_periode_terakhir(df_plot_komparasi, y_col)
    if konteks is None:
        return ["Data tidak tersedia untuk periode ini."]

    prompt = _bangun_prompt(label_bb, jenis_harga, konteks, config)

    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        raise RuntimeError(
            "API Key Gemini belum dikonfigurasi di secrets.toml. "
            "Tambahkan baris: GEMINI_API_KEY = \"xxxxx\""
        )

    import requests

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.6,
            "responseMimeType": "application/json",
        },
    }

    response = requests.post(
        GEMINI_API_URL,
        params={"key": api_key},
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()

    try:
        teks_response = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise ValueError(f"Response Gemini tidak sesuai format yang diharapkan: {data}") from e

    list_resume = _parse_response_json(teks_response)
    return list_resume