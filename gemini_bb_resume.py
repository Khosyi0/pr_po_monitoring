"""
gemini_bb_resume.py - Resume otomatis (naratif, tidak kaku) memakai Gemini API.

Menggantikan `hitung_resume_generik` yang berbasis template string statis,
dengan resume yang ditulis oleh LLM (Gemini) supaya bahasanya lebih natural
dan enak dibaca atasan, tapi tetap akurat terhadap data.

Prinsip desain:
1. KONTEKS DIBATASI 3 BULAN TERAKHIR
   Model hanya diberi tahu data 3 bulan terakhir (dihitung dari tanggal
   terbit paling baru yang ada pada rentang filter user), supaya narasinya
   fokus membicarakan tren jangka pendek/menengah -- bukan seluruh histori
   yang bisa membingungkan konteks.

2. DATA TERAKHIR TETAP DIPERTAHANKAN WALAU DI LUAR 3 BULAN
   Kalau suatu referensi (Majalah - Incoterm) TIDAK punya rilis harga sama
   sekali dalam 3 bulan terakhir (mis. publikasinya jarang / sudah lama tidak
   update), titik data TERAKHIR yang tersedia (walau lebih lama dari 3 bulan)
   tetap disertakan ke konteks, supaya AI tidak menganggap referensi tsb
   tidak punya data sama sekali. Ini sama seperti perilaku lama di
   `hitung_resume_generik` yang menyebutkan "referensi X terakhir rilis pada
   tanggal Y" ketika Y sudah lebih dari 14 hari dari T0.

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

JUMLAH_BULAN_KONTEKS = 3

# Model Gemini yang dipakai. gemini-2.5-flash dipilih karena cepat & murah,
# cukup untuk tugas menulis ringkasan naratif pendek berbasis data terstruktur.
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)


def _format_tanggal_indo(dt):
    dt = pd.Timestamp(dt)
    return f"{dt.day:02d} {BULAN_INDO[dt.month]} {dt.year}"


def _susun_konteks_3_bulan(df_plot, y_col):
    """
    Menyusun ringkasan data historis per referensi (label_komparasi), dibatasi
    3 bulan terakhir dari tanggal terbit paling baru di df_plot.

    Untuk tiap referensi:
      - Ambil semua titik data dalam jendela 3 bulan terakhir (urut tanggal).
      - Kalau TIDAK ADA titik data sama sekali dalam jendela tsb, tetap
        sertakan titik data TERAKHIR yang tersedia (di luar jendela), dengan
        catatan eksplisit bahwa data tsb "terakhir tersedia" -- supaya AI
        tahu itu bukan data terkini tapi tetap relevan disebutkan.

    df_plot HARUS sudah tidak mengandung baris Harga Perolehan (kalau ada,
    filter dulu sebelum memanggil fungsi ini), karena resume ini murni bicara
    soal komparasi Majalah - Incoterm.

    Mengembalikan dict:
    {
        "tanggal_acuan": Timestamp,   # T0, tanggal terbit paling baru di seluruh df_plot
        "batas_3_bulan": Timestamp,
        "referensi": [
            {
                "label": str,
                "dalam_jendela": bool,   # True kalau ada data dlm 3 bulan terakhir
                "titik_data": [ {"tanggal": "dd Mon yyyy", "harga": float}, ... ],
                # kalau dalam_jendela == False, titik_data cuma berisi 1 entry
                # (titik data terakhir yang tersedia, di luar jendela)
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
    batas_3_bulan = tanggal_acuan - pd.DateOffset(months=JUMLAH_BULAN_KONTEKS)

    daftar_referensi = []
    for label, df_label in df_plot.groupby('label_komparasi'):
        df_label = df_label.sort_values('tanggal_terbit')
        df_dalam_jendela = df_label[df_label['tanggal_terbit'] >= batas_3_bulan]

        if not df_dalam_jendela.empty:
            titik_data = [
                {"tanggal": _format_tanggal_indo(row['tanggal_terbit']), "harga": round(float(row[y_col]), 2)}
                for _, row in df_dalam_jendela.iterrows()
            ]
            daftar_referensi.append({
                "label": label,
                "dalam_jendela": True,
                "titik_data": titik_data,
            })
        else:
            # Tidak ada rilis dalam 3 bulan terakhir -> tetap pertahankan
            # titik data TERAKHIR yang tersedia (walau lebih lama), supaya
            # AI tidak kehilangan konteks referensi ini sama sekali.
            baris_terakhir = df_label.iloc[-1]
            daftar_referensi.append({
                "label": label,
                "dalam_jendela": False,
                "titik_data": [{
                    "tanggal": _format_tanggal_indo(baris_terakhir['tanggal_terbit']),
                    "harga": round(float(baris_terakhir[y_col]), 2),
                }],
            })

    return {
        "tanggal_acuan": tanggal_acuan,
        "batas_3_bulan": batas_3_bulan,
        "referensi": daftar_referensi,
    }


def _bangun_prompt(label_bb, jenis_harga, konteks, config):
    """Menyusun prompt teks untuk Gemini dari hasil _susun_konteks_3_bulan."""
    tanggal_acuan_str = _format_tanggal_indo(konteks["tanggal_acuan"])
    batas_str = _format_tanggal_indo(konteks["batas_3_bulan"])

    bagian_data = []
    for ref in konteks["referensi"]:
        if ref["dalam_jendela"]:
            titik_str = "; ".join(f"{t['tanggal']}: USD {t['harga']}/MT" for t in ref["titik_data"])
            bagian_data.append(f"- {ref['label']} (data dalam 3 bulan terakhir): {titik_str}")
        else:
            t = ref["titik_data"][0]
            bagian_data.append(
                f"- {ref['label']} (TIDAK ADA rilis baru dalam 3 bulan terakhir; "
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
Jendela data utama: 3 bulan terakhir (sejak {batas_str} sampai {tanggal_acuan_str})

Data per referensi (Majalah - Incoterm):
{teks_data}

Instruksi penulisan:
1. Tulis dalam bentuk poin-poin (bullet), MAKSIMAL 4 poin, masing-masing 1-3 kalimat.
2. Fokus membahas tren pergerakan harga dalam 3 bulan terakhir: naik/turun/stabil, seberapa signifikan, dan konteks singkat penyebab jika bisa disimpulkan dari data (tanpa mengarang angka atau berita eksternal yang tidak ada di data).
3. Gaya bahasa naratif, profesional, TIDAK kaku/template, enak dibaca oleh manajemen. Hindari mengulang struktur kalimat yang sama persis di tiap poin.
4. Kalau ada referensi yang tidak punya rilis baru dalam 3 bulan terakhir, sebutkan itu di salah satu poin secara singkat (mis. "referensi X terakhir merilis harga pada tanggal Y"), tapi jangan jadikan itu poin utama.
5. Jangan gunakan angka yang tidak ada di data di atas. Semua klaim harus bisa ditelusuri ke data yang diberikan.
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
    Fungsi utama: menyusun konteks 3 bulan terakhir dari df_plot_komparasi,
    memanggil Gemini API, dan mengembalikan list string poin-poin resume.

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

    konteks = _susun_konteks_3_bulan(df_plot_komparasi, y_col)
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