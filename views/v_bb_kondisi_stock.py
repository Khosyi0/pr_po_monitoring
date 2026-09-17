import streamlit as st
import pandas as pd
import json
import altair as alt
from datetime import datetime
from sqlalchemy import text
import plotly.express as px

from utils import MAPPING_SINGKATAN
import gdocs_export


# =============================================================================
# KONSTANTA
# =============================================================================

URUTAN_BULAN_LABEL = [
    ("realisasi", "Realisasi"),
    ("jan", "Januari"), ("feb", "Februari"), ("mar", "Maret"), ("apr", "April"),
    ("mei", "Mei"), ("jun", "Juni"), ("jul", "Juli"), ("agust", "Agustus"),
    ("sep", "September"), ("okt", "Oktober"), ("nop", "Nopember"), ("des", "Desember"),
]
BULAN_KEY_TO_LABEL = dict(URUTAN_BULAN_LABEL)
BULAN_KEY_ORDER = [k for k, _ in URUTAN_BULAN_LABEL]

# Urutan bulan khusus utk tab "Rencana Kebutuhan BB" (tidak ada 'realisasi',
# dan label ditampilkan singkat karena dipakai sbg nama kolom tabel lebar).
URUTAN_BULAN_LABEL_RBB = [
    ("jan", "Jan"), ("feb", "Feb"), ("mar", "Mar"), ("apr", "Apr"),
    ("mei", "Mei"), ("jun", "Jun"), ("jul", "Jul"), ("agust", "Agust"),
    ("sep", "Sep"), ("okt", "Okt"), ("nop", "Nop"), ("des", "Des"),
]
BULAN_KEY_ORDER_RBB = [k for k, _ in URUTAN_BULAN_LABEL_RBB]
BULAN_KEY_TO_LABEL_RBB = dict(URUTAN_BULAN_LABEL_RBB)

# Mapping nama produk di tab Ringkasan -> komoditas & posisi sisip di
# rencana_bb_raw (sheet 'Data BB <tahun>'). Ejaan/istilah kedua sisi ini
# memang berbeda (mis. 'Asam Sulfat' di Ringkasan vs 'Sulphuric Acid' di
# Data BB), jadi dipetakan manual di sini -- bukan fuzzy match -- supaya
# akurat dan mudah disesuaikan kalau ada produk baru.
#
# 'setelah_kategori': baris2 shipment disisipkan TEPAT SETELAH baris
# kategori ini di tabel Ringkasan (bukan selalu di paling bawah/atas).
# Kalau kategori ini tidak ditemukan di tabel produk yg sedang dirender
# (mis. user belum menandai kategori tsb), baris shipment akan ditaruh di
# paling bawah sbg fallback -- lihat _render_ringkasan.
PRODUK_KE_KOMODITAS_RBB = {
    "ZA": {"komoditas": "ZA", "setelah_kategori": "Impor"},
    "Phospate Rock": {"komoditas": "Phosphate Rock", "setelah_kategori": "Impor"},
    "Asam Sulfat": {"komoditas": "Sulphuric Acid", "setelah_kategori": "Amman"},
    "Sulphur": {"komoditas": "Sulphur", "setelah_kategori": "Impor"},
    "KCL": {"komoditas": "MOP/KCl", "setelah_kategori": "Impor KCl Putih"},
    "DAP": {"komoditas": "DAP", "setelah_kategori": "Impor"},
    "NH4Cl": {"komoditas": "NH4Cl", "setelah_kategori": "Impor"},
    "Ammonia": {"komoditas": "Ammonia", "setelah_kategori": "Pengadaan"},
    "PA": {"komoditas": "PA Impor", "setelah_kategori": "Pengadaan (Impor)"},
}

# Suplier dgn nilai ini menandakan "belum ada kontrak" -- baris ini tidak
# ditampilkan sbg baris shipment di tab Ringkasan (bukan rencana konkret).
RBB_SUPLIER_BELUM_KONTRAK = "kebutuhan belum ada kontrak"

# Mapping nama produk di tab Ringkasan -> key di BAHAN_BAKU_KOMPARASI_CONFIG
# (section 'Komparasi Harga Pasar Bahan Baku'). Dipakai supaya section
# tersebut mengikuti produk yang sedang dipilih di dropdown "Pilih Produk"
# paling atas -- TIDAK ada dropdown "Pilih Bahan Baku" terpisah lagi di
# section komparasi, karena kalau berbeda dari produk tabel Ringkasan
# terasa tidak relevan (mis. tabel ZA tapi tren yang tampil DAP).
# Produk yang tidak ada di mapping ini (mis. TSP, Urea -- tidak ada di
# VIRTUAL_PRODUCTS/kategori manual) akan menyembunyikan section komparasi.
PRODUK_KE_BAHAN_BAKU_KOMPARASI = {
    "ZA": "ZA",
    "Phospate Rock": "Phosphate Rock",
    "Asam Sulfat": "Sulfuric Acid",
    "Sulphur": "Sulfur",
    "KCL": "MOP-KCl",
    "DAP": "DAP",
    "NH4Cl": "NH4Cl",
    "Ammonia": "Ammonia",
    "PA": "Phosphoric Acid",
}

OPERATOR_OPTIONS = ["+", "-", "×", "÷"]
OPERATOR_TO_FUNC = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "×": lambda a, b: a * b,
    "÷": lambda a, b: (a / b) if (b not in (0, None) and pd.notna(b)) else None,
}

# =============================================================================
# KOMPARASI HARGA PASAR BAHAN BAKU (section paling bawah tab Ringkasan)
# =============================================================================
# Konfigurasi berikut diadaptasi dari v_bb_bahan_baku.py, disederhanakan
# karena di sini hanya dipakai utk filter + line chart (bukan resume/Excel/
# Google Docs export spt di halaman aslinya) -- field yg cuma dipakai resume
# (threshold_signifikan, kata_naik/turun, kalimat_dampak) sengaja tidak
# disertakan.
BULAN_INDO_KOMPARASI = {
    1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 5: 'Mei', 6: 'Juni',
    7: 'Juli', 8: 'Agustus', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
}

LABEL_HARGA_PEROLEHAN = "Harga Perolehan"
WARNA_HARGA_PEROLEHAN_DEFAULT = "#FFC300"

BAHAN_BAKU_KOMPARASI_CONFIG = {
    "Ammonia": {
        "label": "Ammonia", "db_value": "Ammonia",
        "default_komparasi": [
            {"majalah": "Fertecon Ammonia", "incoterm": "South East Asia FOB"},
            {"majalah": "Argus FMB Price Guide", "incoterm": "East Asia CFR (excl Taiwan)"},
        ],
    },
    "DAP": {
        "label": "DAP", "db_value": "DAP",
        "default_komparasi": [
            {"majalah": "Argus FMB Price Guide", "incoterm": "China FOB"},
            {"majalah": "Fertecon Phosphate", "incoterm": "FOB China Cash"},
        ],
    },
    "MOP-KCl": {
        "label": "MOP-KCl", "db_value": "MOP-KCl",
        "default_komparasi": [
            {"majalah": "MOP Ref. Argus FMB Price Guide (spot)", "incoterm": "SE Asia CFR Spot Std", "tampil_chart": True},
            {"majalah": "CRU", "incoterm": "CFR SEA", "tampil_chart": False},
        ],
    },
    "NH4Cl": {
        "label": "NH4Cl", "db_value": "NH4Cl",
        "default_komparasi": [
            {"majalah": "Argus Nitrogen", "incoterm": "CFR Southeast Asia"},
        ],
    },
    "NPK": {
        "label": "NPK", "db_value": "NPK",
        "default_komparasi": [],
    },
    "Phosphoric Acid": {
        "label": "Phosphoric Acid", "db_value": "Phosphoric Acid",
        "default_komparasi": [
            {"majalah": "Argus FMB Price Guide", "incoterm": "India CFR"},
            {"majalah": "Fertecon Phosphate", "incoterm": "India CFR"},
        ],
    },
    "Phosphate Rock": {
        "label": "Phosphate Rock", "db_value": ["phosphate rock", "phos rock", "phosrock"],
        "default_komparasi": [
            {"majalah": "Profercy Phosphate", "incoterm": "Jordan FOB 28-31%"},
            {"majalah": "Profercy Phosphate", "incoterm": "Egypt FOB 30-31%"},
            {"majalah": "Profercy Phosphate", "incoterm": "Jordan FOB 32-34%"},
            {"majalah": "Argus FMB Price Guide", "incoterm": "Jordan FOB 68-70% BPL"},
        ],
    },
    "Sulfur": {
        "label": "Sulfur", "db_value": "Sulfur",
        "default_komparasi": [
            {"majalah": "Argus FMB Price Guide Sulphur", "incoterm": "CFR Indonesia Spot"},
            {"majalah": "Argus FMB Price Guide Sulphur", "incoterm": "CFR India Spot"},
            {"majalah": "Fertecon Sulphur", "incoterm": "India CFR"},
        ],
    },
    "Sulfuric Acid": {
        "label": "Sulfuric Acid", "db_value": "Sulfuric Acid",
        "default_komparasi": [
            {"majalah": "Majalah ICIS SA pricing", "incoterm": "CFR Indonesia"},
            {"majalah": "Majalah ICIS SA pricing", "incoterm": "CFR S.E. Asia Spot"},
            {"majalah": "Argus FMB Sulphuric Acid", "incoterm": "Spot Price - cfr SEA"},
        ],
    },
    "TSP": {
        "label": "TSP", "db_value": "TSP",
        "default_komparasi": [],
    },
    "Urea": {
        "label": "Urea", "db_value": "Urea",
        "default_komparasi": [],
    },
    "ZA": {
        "label": "ZA", "db_value": "ZA",
        "default_komparasi": [
            {"majalah": "Fertecon Nitrates", "incoterm": "SE Asia CFR Caprolactam"},
            {"majalah": "Argus FMB Price Guide Nitrogen", "incoterm": "(NH4)2SO4 SE Asia CFR"},
        ],
    },
}


# =============================================================================
# VIRTUAL PRODUCTS (ON-THE-FLY DASHBOARD)
# =============================================================================

VIRTUAL_PRODUCTS = {
    "ZA": {
        "sumber_sheet": "Pupuk",
        "produk_asal": ["ZA BAHAN BAKU"],
        "mapping": {
            ("ZA BAHAN BAKU", "Stock awal"): "Stok Awal",
            ("ZA BAHAN BAKU", "► u/ bahan baku (curah)"): "Produksi Untuk Bahan Baku",
            ("ZA BAHAN BAKU", "- Impor untuk Bahan Baku"): "Impor",
            ("ZA BAHAN BAKU", "Jumlah Pemakaian"): "Pemakaian",
            ("ZA BAHAN BAKU", "Pengadaan Mitra ZA Plus"): "Pemakaian",
        },
        "formula": [
            {
                "kategori_hasil": "Stok Akhir",
                "komponen": [
                    {"kategori": "Stok Awal", "operator": "+"},
                    {"kategori": "Produksi Untuk Bahan Baku", "operator": "+"},
                    {"kategori": "Impor", "operator": "+"},
                    {"kategori": "Pemakaian", "operator": "-"},
                ]
            }
        ],
        "urutan_tampil": ["Stok Awal", "Produksi Untuk Bahan Baku", "Impor", "Pemakaian", "Stok Akhir"]
    },
    "Phospate Rock": {
        "sumber_sheet": "Bahan Baku",
        "produk_asal": ["BATUAN FOSFAT CURAH"],
        "mapping": {
            ("BATUAN FOSFAT CURAH", "Saldo Awal : Pabrik - II"): "Stok Awal",
            ("BATUAN FOSFAT CURAH", "Saldo Awal : Pabrik - III A"): "Stok Awal",
            ("BATUAN FOSFAT CURAH", "Saldo Awal : Pabrik - III B"): "Stok Awal",
            ("BATUAN FOSFAT CURAH", "Tersedia"): "Impor",
            ("BATUAN FOSFAT CURAH", "► Asam Fosfat I"): "Impor",
            ("BATUAN FOSFAT CURAH", "► Asam Fosfat II"): "Impor",
            ("BATUAN FOSFAT CURAH", "Jumlah Pemakaian"): "Pemakaian",
            ("BATUAN FOSFAT CURAH", "Saldo Akhir Total"): "Stok Akhir",
        },
        "formula": [],
        "urutan_tampil": ["Stok Awal", "Impor", "Pemakaian", "Stok Akhir"]
    },
    "Asam Sulfat": {
        "sumber_sheet": "Bahan Baku",
        "produk_asal": ["ASAM SULFAT"],
        "mapping": {
            ("ASAM SULFAT", "Stock awal"): "Stok Awal",
            ("ASAM SULFAT", "Jumlah Produksi Actual"): "Jumlah Produksi",
            ("ASAM SULFAT", "- Pengadaan Smelting/Freeport"): "PTFI / Smelting",
            ("ASAM SULFAT", "- Pengadaan Freeport Manyar"): "Freeport Manyar",
            ("ASAM SULFAT", "- Pengadaan (Amman)"): "Amman",
            ("ASAM SULFAT", "- Pengadaan Out Source"): "Impor",
            ("ASAM SULFAT", "Pemakaian & Penjualan"): "Pemakaian & Penjualan",
            ("ASAM SULFAT", "Stock akhir"): "Stok Akhir",
        },
        "formula": [],
        "urutan_tampil": ["Stok Awal", "Jumlah Produksi", "PTFI / Smelting", "Freeport Manyar", "Amman", "Impor", "Pemakaian & Penjualan", "Stok Akhir"]
    },
    "Sulphur": {
        "sumber_sheet": "Bahan Baku",
        "produk_asal": ["BELERANG"],
        "mapping": {
            ("BELERANG", "- Stock awal"): "Stok Awal",
            ("BELERANG", "- Pengadaan"): "Impor",
            ("BELERANG", "Asam Sulfat I dan II"): "Pemakaian",
            ("BELERANG", "Stock akhir"): "Stok Akhir",
        },
        "formula": [],
        "urutan_tampil": ["Stok Awal", "Impor", "Pemakaian", "Stok Akhir"]
    },
    "KCL": {
        "sumber_sheet": "Bahan Baku",
        "produk_asal": ["KCl - CURAH"],
        "mapping": {
            ("KCl - CURAH", "- Stock awal : KCL Merah"): "Stok Awal : KCl Merah",
            ("KCl - CURAH", "- Stock awal : KCL Putih"): "Stok Awal : KCl Putih",
            ("KCl - CURAH", "- Subtitusi KCl Putih ke Merah"): "Subs KCL Putih ke Merah",
            ("KCl - CURAH", "- Pengadaan : KCL Merah"): "Impor KCl Merah",
            ("KCl - CURAH", "- Pengadaan : KCL Putih"): "Impor KCl Putih",
            ("KCl - CURAH", "Jumlah Pemakaian : KCL Merah"): "Pemakaian KCl Merah",
            ("KCl - CURAH", "Jumlah Pemakaian : KCL Putih"): "Pemakaian KCl Putih",
            ("KCl - CURAH", "- Stock akhir : KCL Merah"): "Stok Akhir : KCl Merah",
            ("KCl - CURAH", "- Stock akhir : KCL Putih"): "Stok Akhir : KCl Putih",
        },
        "formula": [],
        "urutan_tampil": ["Stok Awal : KCl Merah", "Stok Awal : KCl Putih", "Subs KCL Putih ke Merah", "Impor KCl Merah", "Impor KCl Putih", "Pemakaian KCl Merah", "Pemakaian KCl Putih", "Stok Akhir : KCl Merah", "Stok Akhir : KCl Putih"]
    },
    "DAP": {
        "sumber_sheet": "Pupuk",
        "produk_asal": ["D A P"],
        "mapping": {
            ("D A P", "Stock awal"): "Stok Awal",
            ("D A P", "Produksi : DAP"): "Produksi",
            ("D A P", "- Impor DAP"): "Impor",
            ("D A P", "Jumlah Pemakaian"): "Pemakaian",
            ("D A P", "Stock akhir Curah"): "Stok Akhir",
        },
        "formula": [],
        "urutan_tampil": ["Stok Awal", "Produksi", "Impor", "Pemakaian", "Stok Akhir"]
    },
    "NH4Cl": {
        "sumber_sheet": "Bahan Baku",
        "produk_asal": ["NH4Cl"],
        "mapping": {
            ("NH4Cl", "Stock awal"): "Stok Awal",
            ("NH4Cl", "- Impor NH4Cl"): "Impor",
            ("NH4Cl", "Jumlah Pemakaian"): "Pemakaian",
            ("NH4Cl", "Stock akhir Curah"): "Stok Akhir",
        },
        "formula": [],
        "urutan_tampil": ["Stok Awal", "Impor", "Pemakaian", "Stok Akhir"]
    },
    "Ammonia": {
        "sumber_sheet": "Bahan Baku",
        "produk_asal": ["AMONIAK"],
        "mapping": {
            ("AMONIAK", "Stock awal"): "Stok Awal",
            ("AMONIAK", "- Produksi : Amoniak I"): "Total Produksi",
            ("AMONIAK", "- Produksi : Amoniak II"): "Total Produksi",
            ("AMONIAK", "- Pengadaan :"): "Pengadaan",
            ("AMONIAK", "Jumlah Pemakaian"): "Pemakaian",
            ("AMONIAK", "Penjualan"): "Penjualan",
            ("AMONIAK", "Stock akhir"): "Stok Akhir",
        },
        "formula": [],
        "urutan_tampil": ["Stok Awal", "Total Produksi", "Pengadaan", "Pemakaian", "Penjualan", "Stok Akhir"]
    },
    "PA": {
        "sumber_sheet": "Bahan Baku",
        "produk_asal": ["ASAM FOSFAT ( 54% )"],
        "mapping": {
            ("ASAM FOSFAT ( 54% )", "- Stock awal : Liquid & Sludge"): "Stok Awal",
            ("ASAM FOSFAT ( 54% )", "Jumlah Produksi 54%"): "Total Produksi",
            ("ASAM FOSFAT ( 54% )", "- Pengadaan PJA (54%)"): "Pengadaan (PJA)",
            ("ASAM FOSFAT ( 54% )", "- Pengadaan Out Source (54%)"): "Pengadaan (Impor)",
            ("ASAM FOSFAT ( 54% )", "Pemakaian & Penjualan"): "Pemakaian & Penjualan",
            ("ASAM FOSFAT ( 54% )", "- Stock akhir : Liquid & Sludge"): "Stok Akhir",
        },
        "formula": [],
        "urutan_tampil": ["Stok Awal", "Total Produksi", "Pengadaan (PJA)", "Pengadaan (Impor)", "Pemakaian & Penjualan", "Stok Akhir"]
    }
}


# =============================================================================
# HELPERS: QUERY - DATA MENTAH
# =============================================================================

@st.cache_data(ttl=300, show_spinner=False)
def _get_tahun_tersedia(_load_data):
    df = _load_data("SELECT DISTINCT tahun_data FROM kondisi_stock_bb_raw ORDER BY tahun_data DESC")
    return df['tahun_data'].tolist() if not df.empty else []


@st.cache_data(ttl=300, show_spinner=False)
def _get_daftar_produk(_load_data, sumber_sheet, tahun_data):
    df = _load_data(f"""
        SELECT DISTINCT produk, MIN(urutan_produk) AS urutan_produk
        FROM kondisi_stock_bb_raw
        WHERE sumber_sheet = '{sumber_sheet}' AND tahun_data = {tahun_data}
        GROUP BY produk
        ORDER BY urutan_produk, produk
    """)
    return df['produk'].tolist() if not df.empty else []


@st.cache_data(ttl=300, show_spinner=False)
def _get_data_produk(_load_data, sumber_sheet, produk, tahun_data):
    """Ambil semua baris (long format) untuk 1 produk, 1 tahun."""
    produk_escaped = produk.replace("'", "''")
    df = _load_data(f"""
        SELECT id, urutan_baris, label_baris, bulan, urutan_bulan, nilai,
               nilai_total_jan_des, nilai_rkap, kategori
        FROM kondisi_stock_bb_raw
        WHERE sumber_sheet = '{sumber_sheet}' AND produk = '{produk_escaped}' AND tahun_data = {tahun_data}
        ORDER BY urutan_baris, urutan_bulan
    """)
    return df


def _get_data_virtual(load_data, tahun_data, config):
    """Menarik data mentah dan langsung memetakan kategorinya berdasarkan config VIRTUAL_PRODUCTS."""
    sumber = config["sumber_sheet"]
    produk_in = ", ".join([f"'{p}'" for p in config["produk_asal"]])

    df = load_data(f"""
        SELECT id, produk, urutan_baris, label_baris, bulan, urutan_bulan, nilai,
               nilai_total_jan_des, nilai_rkap
        FROM kondisi_stock_bb_raw
        WHERE sumber_sheet = '{sumber}' AND produk IN ({produk_in}) AND tahun_data = {tahun_data}
    """)

    if df.empty:
        return df

    def map_kat(row):
        key = (row["produk"], row["label_baris"])
        return config["mapping"].get(key, None)

    df["kategori"] = df.apply(map_kat, axis=1)
    return df


def _pivot_wide(df_long):
    """Pivot data long (1 baris per bulan) -> wide (1 baris per label, kolom = bulan)."""
    if df_long.empty:
        return pd.DataFrame()

    df_label = (
        df_long[['urutan_baris', 'label_baris', 'nilai_total_jan_des', 'nilai_rkap', 'kategori']]
        .drop_duplicates(subset=['urutan_baris'])
        .set_index('urutan_baris')
    )

    pivot = df_long.pivot_table(
        index='urutan_baris', columns='bulan', values='nilai', aggfunc='first'
    )

    wide = df_label.join(pivot)

    kolom_urut = ['label_baris'] + [k for k in BULAN_KEY_ORDER if k in wide.columns] + \
                 ['nilai_total_jan_des', 'nilai_rkap', 'kategori']
    kolom_urut = [c for c in kolom_urut if c in wide.columns]
    wide = wide[kolom_urut].reset_index()

    rename_map = dict(URUTAN_BULAN_LABEL)
    rename_map.update({
        'label_baris': 'Label',
        'nilai_total_jan_des': 'Total Jan-Des',
        'nilai_rkap': 'RKAP',
        'kategori': 'Kategori',
    })
    wide = wide.rename(columns=rename_map)
    return wide

@st.cache_data(ttl=300, show_spinner=False)
def _get_daftar_produk_berkategori(_load_data, sumber_sheet, tahun_data):
    """Ambil daftar produk yang minimal punya 1 baris yang sudah dikategorikan."""
    df = _load_data(f"""
        SELECT DISTINCT produk, MIN(urutan_produk) AS urutan_produk
        FROM kondisi_stock_bb_raw
        WHERE sumber_sheet = '{sumber_sheet}' AND tahun_data = {tahun_data}
          AND kategori IS NOT NULL AND TRIM(kategori) != ''
        GROUP BY produk
        ORDER BY urutan_produk, produk
    """)
    return df['produk'].tolist() if not df.empty else []


# =============================================================================
# HELPERS: QUERY - FORMULA KATEGORI
# =============================================================================

@st.cache_data(ttl=300, show_spinner=False)
def _get_formula_list(_load_data, sumber_sheet, produk):
    produk_escaped = produk.replace("'", "''")
    df = _load_data(f"""
        SELECT id, kategori_hasil, komponen
        FROM kondisi_stock_bb_formula
        WHERE sumber_sheet = '{sumber_sheet}' AND produk = '{produk_escaped}'
        ORDER BY id
    """)
    return df


def _simpan_formula(engine, sumber_sheet, produk, kategori_hasil, komponen_list):
    """komponen_list: list of dict {'kategori': str, 'operator': str}"""
    komponen_json = json.dumps(komponen_list, ensure_ascii=False)
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO kondisi_stock_bb_formula (sumber_sheet, produk, kategori_hasil, komponen)
            VALUES (:sumber, :produk, :kategori_hasil, :komponen)
            ON CONFLICT (sumber_sheet, produk, kategori_hasil)
            DO UPDATE SET komponen = EXCLUDED.komponen
        """), {
            'sumber': sumber_sheet, 'produk': produk,
            'kategori_hasil': kategori_hasil, 'komponen': komponen_json,
        })


def _hapus_formula(engine, formula_id):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM kondisi_stock_bb_formula WHERE id = :id"), {'id': formula_id})


# =============================================================================
# HELPERS: QUERY - CHART HARIAN (sheet 'Stock Chart')
# =============================================================================

@st.cache_data(ttl=300, show_spinner=False)
def _get_daftar_virtual_produk_chart(_load_data, tahun_data):
    """Daftar virtual_produk yang punya data chart harian utk tahun tsb."""
    df = _load_data(f"""
        SELECT DISTINCT virtual_produk
        FROM kondisi_stock_bb_chart_harian
        WHERE tahun_data = {tahun_data}
        ORDER BY virtual_produk
    """)
    return df['virtual_produk'].tolist() if not df.empty else []


@st.cache_data(ttl=300, show_spinner=False)
def _get_data_chart_harian(_load_data, virtual_produk, tahun_data):
    """Ambil data harian (Safety Stock & Stock PG) utk 1 virtual produk, 1 tahun.
    Bisa berisi >1 'jenis' (mis. KCL: Merah & Putih)."""
    vp_escaped = virtual_produk.replace("'", "''")
    df = _load_data(f"""
        SELECT jenis, tanggal, safety_stock, stock_pg
        FROM kondisi_stock_bb_chart_harian
        WHERE virtual_produk = '{vp_escaped}' AND tahun_data = {tahun_data}
        ORDER BY jenis, tanggal
    """)
    if not df.empty:
        df['tanggal'] = pd.to_datetime(df['tanggal'])
    return df


# =============================================================================
# HELPERS: QUERY - RENCANA KEBUTUHAN BB (sheet 'Data BB <tahun>')
# =============================================================================

@st.cache_data(ttl=300, show_spinner=False)
def _get_tahun_tersedia_rbb(_load_data):
    df = _load_data("SELECT DISTINCT tahun_data FROM rencana_bb_raw ORDER BY tahun_data DESC")
    return df['tahun_data'].tolist() if not df.empty else []


@st.cache_data(ttl=300, show_spinner=False)
def _get_daftar_komoditas_rbb(_load_data, tahun_data):
    df = _load_data(f"""
        SELECT DISTINCT komoditas, MIN(urutan_komoditas) AS urutan_komoditas
        FROM rencana_bb_raw
        WHERE tahun_data = {tahun_data}
        GROUP BY komoditas
        ORDER BY urutan_komoditas
    """)
    return df['komoditas'].tolist() if not df.empty else []


@st.cache_data(ttl=300, show_spinner=False)
def _get_data_komoditas_rbb(_load_data, komoditas, tahun_data):
    """Ambil semua baris (long format) untuk 1 komoditas, 1 tahun dari rencana_bb_raw."""
    komoditas_escaped = komoditas.replace("'", "''")
    df = _load_data(f"""
        SELECT urutan_baris, origin, suplier, harga, bulan, urutan_bulan, isi_shipment,
               estimasi_qty_shipment, harga_perolehan_terakhir, posisi_stok,
               safety_stock, keterangan, rute_kapal_terdampak, mitigasi_risiko
        FROM rencana_bb_raw
        WHERE komoditas = '{komoditas_escaped}' AND tahun_data = {tahun_data}
        ORDER BY urutan_baris, urutan_bulan
    """)
    return df


def _pivot_shipment_wide(df_long):
    """Pivot data long rencana_bb_raw (1 baris per origin/suplier per bulan)
    -> wide (1 baris per origin/suplier, kolom = bulan berisi teks shipment)."""
    if df_long.empty:
        return pd.DataFrame()

    df_id = (
        df_long[['urutan_baris', 'origin', 'suplier', 'harga']]
        .drop_duplicates(subset=['urutan_baris'])
        .set_index('urutan_baris')
    )

    pivot = df_long.pivot_table(
        index='urutan_baris', columns='bulan', values='isi_shipment', aggfunc='first'
    )

    wide = df_id.join(pivot)

    kolom_urut = ['origin', 'suplier', 'harga'] + [k for k in BULAN_KEY_ORDER_RBB if k in wide.columns]
    kolom_urut = [c for c in kolom_urut if c in wide.columns]
    wide = wide[kolom_urut].reset_index(drop=True)

    rename_map = dict(URUTAN_BULAN_LABEL_RBB)
    rename_map.update({'origin': 'Origin', 'suplier': 'Suplier', 'harga': 'Harga (USD/MT)'})
    wide = wide.rename(columns=rename_map)
    return wide


# =============================================================================
# HELPERS: AGREGASI KATEGORI (termasuk formula)
# =============================================================================

def _hitung_agregat_kategori(df_long):
    """Return DataFrame index=kategori (termasuk hasil formula), kolom=bulan (kunci internal), value=nilai."""
    df_kategori = df_long[df_long['kategori'].notna() & (df_long['kategori'] != '')].copy()
    if df_kategori.empty:
        return pd.DataFrame()

    agg = (
        df_kategori
        .groupby(['kategori', 'bulan'], as_index=False)['nilai']
        .sum(min_count=1)
    )
    pivot = agg.pivot(index='kategori', columns='bulan', values='nilai')
    return pivot


def _terapkan_formula(pivot_dasar, df_formula):
    """Tambahkan baris hasil formula ke pivot_dasar (kategori x bulan)."""
    if df_formula is None or df_formula.empty:
        return pivot_dasar

    hasil = pivot_dasar.copy()
    for _, row in df_formula.iterrows():
        kategori_hasil = row['kategori_hasil']
        try:
            komponen = json.loads(row['komponen']) if isinstance(row['komponen'], str) else row['komponen']
        except Exception:
            continue

        if not komponen:
            continue

        nilai_formula = None
        for i, komp in enumerate(komponen):
            kat = komp.get('kategori')
            op = komp.get('operator', '+')
            if kat not in hasil.index:
                nilai_formula = None
                break
            baris_kat = hasil.loc[kat]
            if i == 0:
                nilai_formula = baris_kat.copy()
            else:
                func = OPERATOR_TO_FUNC.get(op, OPERATOR_TO_FUNC['+'])
                nilai_formula = pd.Series(
                    {col: func(nilai_formula.get(col), baris_kat.get(col)) for col in hasil.columns},
                    index=hasil.columns
                )
        if nilai_formula is not None:
            hasil.loc[kategori_hasil] = nilai_formula

    return hasil


# =============================================================================
# RENDER UTAMA
# =============================================================================

def render(**kwargs):
    load_data = kwargs.get('load_data')
    if load_data is None:
        from config_db import load_data as _ld
        load_data = _ld

    def _get_engine():
        from config_db import get_db_engine
        return get_db_engine()

    st.markdown("""
        <h1 style='display:flex; align-items:center; font-size:42px; margin-bottom:0;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" fill="currentColor"
                 viewBox="0 0 16 16" style="margin-right:12px; margin-bottom:4px;">
                <path d="M0 1.5A.5.5 0 0 1 .5 1H1.5a.5.5 0 0 1 .5.415l.1.585h11.914a.5.5 0 0 1 .491.592l-1.5 8A.5.5 0 0 1 12.5 11H4a.5.5 0 0 1-.491-.408L2.01 3.607 1.61 2.01 1.5 1.5H.5a.5.5 0 0 1-.5-.5m3.15 3-1.5 8H12.5l1.5-8z"/>
                <path d="M4 15a1 1 0 1 0 2 0 1 1 0 0 0-2 0m6 0a1 1 0 1 0 2 0 1 1 0 0 0-2 0"/>
            </svg>
            Kondisi Stock BB
        </h1>
    """, unsafe_allow_html=True)

    st.markdown(
        "<p style='font-size:15px; opacity:0.6; margin-top:4px; margin-bottom:24px;'>"
        "Data balans produksi, pengadaan, dan pemakaian untuk produk Pupuk & Bahan Baku."
        "</p>",
        unsafe_allow_html=True
    )

    tahun_list = _get_tahun_tersedia(load_data)
    if not tahun_list:
        st.warning(
            "Belum ada data Kondisi Stock BB di database. Silakan upload data terlebih dahulu "
            "lewat menu **Manajemen Data → Kondisi Stock BB**."
        )
        return

    col_tahun, _ = st.columns([1, 3])
    with col_tahun:
        tahun_pilih = st.selectbox("Tahun Data", options=tahun_list, index=0, key="ksb_tahun")

    st.markdown("<br>", unsafe_allow_html=True)

    tab_pupuk, tab_bb, tab_rencana, tab_ringkasan = st.tabs([
        ":material/agriculture: Pupuk",
        ":material/science: Bahan Baku",
        ":material/directions_boat: Rencana Kebutuhan BB",
        ":material/analytics: Ringkasan"
    ])

    with tab_pupuk:
        _render_sumber(load_data, _get_engine, "Pupuk", tahun_pilih)

    with tab_bb:
        _render_sumber(load_data, _get_engine, "Bahan Baku", tahun_pilih)

    with tab_rencana:
        _render_tab_rencana_bb(load_data)

    with tab_ringkasan:
        _render_tab_ringkasan(load_data, tahun_pilih)


def _render_sumber(load_data, get_engine_fn, sumber_sheet, tahun_data):

    daftar_produk = _get_daftar_produk(load_data, sumber_sheet, tahun_data)

    if not daftar_produk:
        st.info(f"Tidak ada data '{sumber_sheet}' untuk tahun {tahun_data}.")
        return

    produk_pilih = st.selectbox(
        f"Pilih Produk ({sumber_sheet})",
        options=daftar_produk,
        key=f"ksb_produk_{sumber_sheet}"
    )

    df_long = _get_data_produk(load_data, sumber_sheet, produk_pilih, tahun_data)

    if df_long.empty:
        st.info("Tidak ada data untuk produk ini.")
        return

    sub_mentah, sub_kategori = st.tabs([
        ":material/table_view: Data Mentah",
        ":material/label: Kategorisasi"
    ])

    with sub_mentah:
        _render_data_mentah(df_long)

    with sub_kategori:
        _render_kategorisasi(load_data, df_long, get_engine_fn, sumber_sheet, produk_pilih, tahun_data)


# =============================================================================
# HELPERS: KOMPARASI HARGA PASAR BAHAN BAKU
# =============================================================================

def _kb_get_config(bahan_baku_key):
    return BAHAN_BAKU_KOMPARASI_CONFIG[bahan_baku_key]


def _kb_variasikan_warna(hex_color, index, total):
    if total <= 1:
        return hex_color
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    factor = 0.6 + (0.7 * index / max(total - 1, 1))
    r = min(255, int(r * factor))
    g = min(255, int(g * factor))
    b = min(255, int(b * factor))
    return f"#{r:02x}{g:02x}{b:02x}"


def _kb_load_harga_perolehan(load_data, db_value, start_date, end_date):
    """Ambil data Harga Perolehan (tabel harga_perolehan_bahan_baku) utk
    bahan_baku terpilih, pada rentang tanggal yg sama dgn filter chart.
    Return DataFrame kosong kalau tidak ada data (mis. tabel belum ada, atau
    bahan baku ybs memang tidak punya kolom Harga Perolehan di sumbernya)."""
    if isinstance(db_value, (list, tuple)):
        alias_list = "', '".join([a.lower().strip() for a in db_value])
        where_clause = f"lower(trim(bahan_baku)) IN ('{alias_list}')"
    else:
        where_clause = f"bahan_baku = '{db_value}'"

    query = f"""
        SELECT tanggal_terbit, harga_perolehan
        FROM harga_perolehan_bahan_baku
        WHERE {where_clause}
          AND tanggal_terbit >= '{start_date}' AND tanggal_terbit <= '{end_date}'
        ORDER BY tanggal_terbit ASC
    """
    try:
        df_hp = load_data(query)
    except Exception:
        return pd.DataFrame(columns=['tanggal_terbit', 'harga_perolehan'])
    return df_hp


def _render_filter_komparasi_harga_pasar(load_data, bahan_baku_pilihan):
    """Bagian FILTER dari 'Komparasi Harga Pasar Bahan Baku' -- expander
    filter (tanggal, jenis harga, jumlah komparasi, warna, dst). Dipisah
    dari fungsi penggambar chart supaya filter bisa ditaruh di atas,
    sementara chart-nya sendiri dirender belakangan di dalam kolom (lihat
    _render_tab_ringkasan).

    bahan_baku_pilihan: key di BAHAN_BAKU_KOMPARASI_CONFIG, ditentukan dari
    produk yang sedang dipilih di dropdown "Pilih Produk" paling atas (lihat
    PRODUK_KE_BAHAN_BAKU_KOMPARASI) -- BUKAN dropdown terpisah di section
    ini, supaya section komparasi selalu relevan dgn produk tabel Ringkasan
    yang sedang aktif.

    Return dict berisi semua yang dibutuhkan utk menggambar chart, atau
    None kalau tidak ada data/filter belum valid (chart tidak digambar)."""

    st.markdown("### :material/monitoring: Komparasi Harga Pasar Bahan Baku")

    config = _kb_get_config(bahan_baku_pilihan)
    label_bb = config["label"]
    db_value = config["db_value"]

    suffix = bahan_baku_pilihan.lower().replace(" ", "_").replace("-", "_")

    if isinstance(db_value, (list, tuple)):
        alias_list = "', '".join([a.lower().strip() for a in db_value])
        where_clause = f"lower(trim(bahan_baku)) IN ('{alias_list}')"
    else:
        where_clause = f"bahan_baku = '{db_value}'"

    query = f"""
        SELECT tanggal_terbit, nama_majalah, incoterm, harga_min, harga_max
        FROM master_harga_bahan_baku
        WHERE {where_clause}
        ORDER BY tanggal_terbit ASC
    """
    df = load_data(query)

    if df.empty:
        st.warning(f"Data harga {label_bb} belum tersedia di database.")
        return None

    list_majalah = df['nama_majalah'].unique()
    min_date = df['tanggal_terbit'].min()
    max_date = df['tanggal_terbit'].max()

    # Default "Mulai dari tanggal" = tepat 1 tahun sebelum tanggal data
    # terakhir (max_date), bukan awal bulan -- mis. kalau data terakhir
    # 2026-09-03, default mulai jadi 2025-09-03.
    default_start_date = (pd.Timestamp(max_date) - pd.DateOffset(years=1)).date()
    calendar_min_date = min(min_date, default_start_date)

    if default_start_date > max_date or default_start_date < min_date:
        default_start_date = min_date

    def _save_to_permanent(widget_key, permanent_key):
        st.session_state[permanent_key] = st.session_state[widget_key]

    with st.expander(":material/settings: Filter Komparasi Harga Pasar", expanded=True):
        col_mulai, col_sampai, col_metode, col_jml = st.columns(4)
        with col_mulai:
            start_date = st.date_input(
                "Mulai dari tanggal",
                value=st.session_state.get(f"_perm_kb_start_date_{suffix}", default_start_date),
                min_value=calendar_min_date, max_value=max_date,
                key=f"kb_start_date_{suffix}",
                on_change=_save_to_permanent,
                args=(f"kb_start_date_{suffix}", f"_perm_kb_start_date_{suffix}")
            )
        with col_sampai:
            end_date = st.date_input(
                "Sampai tanggal",
                value=st.session_state.get(f"_perm_kb_end_date_{suffix}", max_date),
                min_value=calendar_min_date, max_value=max_date,
                key=f"kb_end_date_{suffix}",
                on_change=_save_to_permanent,
                args=(f"kb_end_date_{suffix}", f"_perm_kb_end_date_{suffix}")
            )
        with col_metode:
            jenis_harga_options = ["AVERAGE", "MIN", "MAX"]
            jenis_harga_default = st.session_state.get(f"_perm_kb_jenis_harga_{suffix}", "AVERAGE")
            jenis_harga = st.selectbox(
                "Jenis Harga", jenis_harga_options,
                index=jenis_harga_options.index(jenis_harga_default) if jenis_harga_default in jenis_harga_options else 0,
                help="Pilih nilai harga yang ingin diplot pada grafik",
                key=f"kb_jenis_harga_{suffix}",
                on_change=_save_to_permanent,
                args=(f"kb_jenis_harga_{suffix}", f"_perm_kb_jenis_harga_{suffix}")
            )
        with col_jml:
            default_komparasi_list = config.get("default_komparasi", [])
            default_jml_komparasi = len(default_komparasi_list) if default_komparasi_list else 2
            jml_komparasi = st.number_input(
                "Jumlah Komparasi", min_value=1, max_value=5,
                value=st.session_state.get(f"_perm_kb_jml_komparasi_{suffix}", default_jml_komparasi),
                key=f"kb_jml_komparasi_{suffix}",
                on_change=_save_to_permanent,
                args=(f"kb_jml_komparasi_{suffix}", f"_perm_kb_jml_komparasi_{suffix}")
            )

        st.markdown("<hr style='margin: 10px 0; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)

        # Garis Harga Perolehan SELALU ditampilkan di halaman ini (tidak ada
        # toggle on/off) -- kalau datanya memang tidak ada, garis ini
        # otomatis tidak muncul karena tidak ada apapun utk diplot.
        col_hp_warna, _ = st.columns([1, 3])
        with col_hp_warna:
            warna_harga_perolehan = st.color_picker(
                "Warna Garis Harga Perolehan",
                value=st.session_state.get(f"_perm_kb_warna_hp_{suffix}", WARNA_HARGA_PEROLEHAN_DEFAULT),
                key=f"kb_warna_hp_{suffix}",
                on_change=_save_to_permanent,
                args=(f"kb_warna_hp_{suffix}", f"_perm_kb_warna_hp_{suffix}")
            )

        st.markdown("<hr style='margin: 10px 0; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)

        komparasi_data = []
        warna_map = {}
        default_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

        for i in range(int(jml_komparasi)):
            default_dari_config = default_komparasi_list[i] if i < len(default_komparasi_list) else None

            c1, c2, c3, c4 = st.columns([3, 3, 1, 1])
            with c1:
                perm_key_majalah = f"_perm_kb_majalah_{suffix}_{i}"
                if perm_key_majalah in st.session_state:
                    default_majalah = st.session_state[perm_key_majalah]
                elif default_dari_config and default_dari_config.get("majalah") in list_majalah:
                    default_majalah = default_dari_config["majalah"]
                else:
                    default_majalah = list_majalah[i] if i < len(list_majalah) else list_majalah[0]
                majalah_index = list(list_majalah).index(default_majalah) if default_majalah in list_majalah else 0
                majalah_pilihan = st.selectbox(
                    f"Majalah ke-{i+1}", list_majalah,
                    index=majalah_index,
                    key=f"kb_majalah_{suffix}_{i}",
                    on_change=_save_to_permanent,
                    args=(f"kb_majalah_{suffix}_{i}", perm_key_majalah)
                )
            with c2:
                list_incoterm = df[df['nama_majalah'] == majalah_pilihan]['incoterm'].unique()
                perm_key_incoterm = f"_perm_kb_incoterm_{suffix}_{i}"
                if perm_key_incoterm in st.session_state:
                    default_incoterm = st.session_state[perm_key_incoterm]
                elif (default_dari_config and majalah_pilihan == default_dari_config.get("majalah")
                      and default_dari_config.get("incoterm") in list_incoterm):
                    default_incoterm = default_dari_config["incoterm"]
                else:
                    default_incoterm = list_incoterm[0] if len(list_incoterm) > 0 else None
                incoterm_index = list(list_incoterm).index(default_incoterm) if default_incoterm in list_incoterm else 0
                incoterm_pilihan = st.selectbox(
                    f"Metode Incoterm ke-{i+1}", list_incoterm,
                    index=incoterm_index if len(list_incoterm) > 0 else None,
                    key=f"kb_incoterm_{suffix}_{i}",
                    on_change=_save_to_permanent,
                    args=(f"kb_incoterm_{suffix}_{i}", perm_key_incoterm)
                )
            with c3:
                perm_key_warna = f"_perm_kb_warna_{suffix}_{i}"
                default_warna = st.session_state.get(perm_key_warna, default_colors[i % len(default_colors)])
                warna_pilihan = st.color_picker(
                    "Warna", default_warna,
                    key=f"kb_color_{suffix}_{i}",
                    on_change=_save_to_permanent,
                    args=(f"kb_color_{suffix}_{i}", perm_key_warna)
                )
            with c4:
                perm_key_tampil = f"_perm_kb_tampil_{suffix}_{i}"
                if perm_key_tampil in st.session_state:
                    default_tampil = st.session_state[perm_key_tampil]
                else:
                    default_tampil = default_dari_config.get("tampil_chart", True) if default_dari_config else True

                st.write("")
                st.write("")
                tampil_pilihan = st.checkbox(
                    "Plot di Chart", value=default_tampil,
                    key=f"kb_tampil_{suffix}_{i}",
                    on_change=_save_to_permanent,
                    args=(f"kb_tampil_{suffix}_{i}", perm_key_tampil)
                )

            if incoterm_pilihan:
                komparasi_data.append({
                    "majalah": majalah_pilihan,
                    "incoterms": [incoterm_pilihan],
                    "warna_dasar": warna_pilihan,
                    "tampil_chart": tampil_pilihan
                })

        for item in komparasi_data:
            for idx, incoterm in enumerate(item["incoterms"]):
                label_asli = f"{item['majalah']} - {incoterm}"
                label_singkat = MAPPING_SINGKATAN.get(label_asli, label_asli)
                warna_final = _kb_variasikan_warna(item["warna_dasar"], idx, len(item["incoterms"]))
                warna_map[label_singkat] = warna_final

    col_btn, _ = st.columns([1, 4])
    with col_btn:
        if st.button(":material/refresh: Refresh Data", use_container_width=True, key=f"kb_refresh_{suffix}"):
            st.cache_data.clear()
            st.rerun()

    if start_date > end_date:
        st.error("❌ 'Mulai dari tanggal' tidak boleh lebih besar dari 'Sampai tanggal'.")
        return None
    if not komparasi_data:
        st.info("Silakan tentukan minimal 1 metode Incoterm.")
        return None

    return {
        "df": df,
        "label_bb": label_bb,
        "db_value": db_value,
        "start_date": start_date,
        "end_date": end_date,
        "jenis_harga": jenis_harga,
        "komparasi_data": komparasi_data,
        "warna_map": warna_map,
        "warna_harga_perolehan": warna_harga_perolehan,
    }


def _render_chart_komparasi_harga_pasar(load_data, filter_hasil):
    """Bagian CHART dari 'Komparasi Harga Pasar Bahan Baku' -- menerima hasil
    dari _render_filter_komparasi_harga_pasar dan menggambar line chart-nya
    saja (st.plotly_chart). Dipisah dari filter supaya bisa ditaruh di kolom
    tersendiri (lihat _render_tab_ringkasan)."""
    if filter_hasil is None:
        return

    df = filter_hasil["df"]
    label_bb = filter_hasil["label_bb"]
    db_value = filter_hasil["db_value"]
    start_date = filter_hasil["start_date"]
    end_date = filter_hasil["end_date"]
    jenis_harga = filter_hasil["jenis_harga"]
    komparasi_data = filter_hasil["komparasi_data"]
    warna_map = filter_hasil["warna_map"]
    warna_harga_perolehan = filter_hasil["warna_harga_perolehan"]

    df_plot = pd.DataFrame()
    for item in komparasi_data:
        majalah = item["majalah"]
        incoterms = item["incoterms"]
        temp_df = df[(df['nama_majalah'] == majalah) & (df['incoterm'].isin(incoterms)) &
                     (df['tanggal_terbit'] >= start_date) & (df['tanggal_terbit'] <= end_date)].copy()
        if not temp_df.empty:
            temp_df['label_komparasi'] = temp_df['nama_majalah'] + ' - ' + temp_df['incoterm']
            temp_df['label_komparasi'] = temp_df['label_komparasi'].apply(
                lambda x: MAPPING_SINGKATAN.get(x, x)
            )
            df_plot = pd.concat([df_plot, temp_df], ignore_index=True)

    if df_plot.empty:
        st.info("Tidak ada data yang tersedia untuk kombinasi filter yang dipilih pada rentang waktu tersebut.")
        return

    df_plot['harga_avg'] = (df_plot['harga_min'] + df_plot['harga_max']) / 2
    df_plot['tanggal_terbit'] = pd.to_datetime(df_plot['tanggal_terbit'])
    df_plot = df_plot.sort_values('tanggal_terbit')

    if jenis_harga == "MIN":
        y_col, y_label = 'harga_min', 'Harga Minimum (USD/MT)'
    elif jenis_harga == "MAX":
        y_col, y_label = 'harga_max', 'Harga Maksimum (USD/MT)'
    else:
        y_col, y_label = 'harga_avg', 'Harga Rata-rata (USD/MT)'

    # Filter khusus utk Chart berdasarkan checkbox "Plot di Chart"
    label_yang_tampil = []
    for item in komparasi_data:
        if item.get("tampil_chart", True):
            for incoterm in item["incoterms"]:
                label_asli = f"{item['majalah']} - {incoterm}"
                label_singkat = MAPPING_SINGKATAN.get(label_asli, label_asli)
                label_yang_tampil.append(label_singkat)

    df_plot_chart = df_plot[df_plot['label_komparasi'].isin(label_yang_tampil)].copy()

    # -- Garis Harga Perolehan (selalu ditambahkan kalau datanya ada) --
    df_hp = _kb_load_harga_perolehan(load_data, db_value, start_date, end_date)
    if not df_hp.empty:
        df_hp = df_hp.copy()
        df_hp['tanggal_terbit'] = pd.to_datetime(df_hp['tanggal_terbit'])
        df_hp['label_komparasi'] = LABEL_HARGA_PEROLEHAN
        df_hp[y_col] = df_hp['harga_perolehan']
        df_hp_for_plot = df_hp[['tanggal_terbit', 'label_komparasi', y_col]]
        df_plot_chart = pd.concat([df_plot_chart, df_hp_for_plot], ignore_index=True)
        warna_map[LABEL_HARGA_PEROLEHAN] = warna_harga_perolehan

    tanggal_unik = df_plot_chart['tanggal_terbit'].unique()

    fig = px.line(
        df_plot_chart, x='tanggal_terbit', y=y_col, color='label_komparasi',
        color_discrete_map=warna_map,
        title=f"Komparasi Tren Harga {label_bb} ({jenis_harga})",
        labels={y_col: y_label, 'tanggal_terbit': 'Tanggal Publikasi', 'label_komparasi': 'Majalah & Incoterm'}
    )

    if not df_hp.empty:
        fig.for_each_trace(
            lambda tr: tr.update(line=dict(dash="dash", width=3)) if tr.name == LABEL_HARGA_PEROLEHAN else ()
        )

    for label, df_label in df_plot_chart.groupby('label_komparasi'):
        df_label_sorted = df_label.sort_values('tanggal_terbit')
        titik_terakhir = df_label_sorted.iloc[-1]
        warna_label = warna_map.get(label, "#1f77b4")
        fig.add_annotation(
            x=titik_terakhir['tanggal_terbit'],
            y=titik_terakhir[y_col],
            text=f"<b>{titik_terakhir[y_col]:.2f}</b>",
            showarrow=False,
            xanchor="left",
            yanchor="middle",
            xshift=8,
            font=dict(color=warna_label, size=12),
            bgcolor="rgba(255,255,255,0.75)",
        )

    fig.update_layout(
        hovermode="x unified",
        legend=dict(orientation="v", yanchor="top", y=-0.6, xanchor="left", x=0),
        # Margin kanan dikecilkan dari r=90 (nilai asli utk layout lebar
        # penuh di v_bb_bahan_baku.py) karena chart ini sekarang dirender
        # di kolom yang lebih sempit -- margin sebesar itu membuat area
        # kosong yang mencolok di sisi kanan. Tetap disisakan sedikit ruang
        # (r=50) supaya label anotasi angka di ujung garis tidak terpotong.
        margin=dict(b=300, t=80, l=60, r=50),
        height=600
    )

    fig.update_xaxes(
        tickangle=-90, type='date', tickmode='array', tickvals=tanggal_unik,
        tickformat="%d %b %Y", title=dict(text="Tanggal Publikasi", standoff=40)
    )

    fig.update_yaxes(dtick=50)

    st.plotly_chart(fig, use_container_width=True)


def _render_tab_ringkasan(load_data, tahun_data):
    produk_pupuk = [(p, "Pupuk") for p in _get_daftar_produk_berkategori(load_data, "Pupuk", tahun_data)]
    produk_bb    = [(p, "Bahan Baku") for p in _get_daftar_produk_berkategori(load_data, "Bahan Baku", tahun_data)]
    semua_produk = produk_pupuk + produk_bb

    label_map = {}

    for v_name, v_cfg in VIRTUAL_PRODUCTS.items():
        label_map[v_name] = {"type": "virtual", "config": v_cfg, "nama": v_name}

    hidden_db_products = []
    for v_cfg in VIRTUAL_PRODUCTS.values():
        hidden_db_products.extend(v_cfg["produk_asal"])

    for p, s in semua_produk:
        if p not in hidden_db_products:
            label_map[f"{p}  ·  {s}"] = {"type": "db", "produk": p, "sumber": s}

    if not label_map:
        st.info(f"Belum ada data ringkasan untuk tahun {tahun_data}.")
        return

    pilihan_label = st.selectbox(
        "Pilih Produk",
        options=list(label_map.keys()),
        key="ksb_produk_ringkasan"
    )
    pilihan = label_map[pilihan_label]

    bulan_terpilih = []
    tabel_gabungan_aktif = None

    if pilihan["type"] == "db":
        df_long = _get_data_produk(load_data, pilihan["sumber"], pilihan["produk"], tahun_data)
        df_formula = _get_formula_list(load_data, pilihan["sumber"], pilihan["produk"])
        nama_untuk_chart = pilihan["produk"]
        bulan_terpilih, tabel_gabungan_aktif = _render_ringkasan(load_data, tahun_data, df_long, df_formula, pilihan["produk"], pilihan["sumber"])
    else:
        cfg = pilihan["config"]
        df_long = _get_data_virtual(load_data, tahun_data, cfg)
        nama_untuk_chart = pilihan["nama"]

        if df_long.empty:
            st.info("Data mentah untuk produk ini belum tersedia.")
            return

        df_formula = pd.DataFrame(cfg["formula"])
        bulan_terpilih, tabel_gabungan_aktif = _render_ringkasan(load_data, tahun_data, df_long, df_formula, pilihan["nama"], cfg["sumber_sheet"], urutan_preset=cfg["urutan_tampil"])

    # == Filter Komparasi Harga Pasar Bahan Baku -- ditaruh SETELAH tabel
    # ringkasan, SEBELUM kedua chart (chart stock harian & chart komparasi
    # harga pasar digambar berdampingan dalam 2 kolom setelah filter ini).
    # Bahan baku utk komparasi ditentukan dari produk yang sedang dipilih
    # di atas (nama_untuk_chart), BUKAN dropdown terpisah -- supaya selalu
    # relevan dgn tabel Ringkasan yang sedang ditampilkan. Kalau produk ini
    # tidak ada pemetaannya (mis. produk yang bukan dari VIRTUAL_PRODUCTS
    # dan tidak match manual, seperti TSP/Urea), section ini disembunyikan.
    bahan_baku_komparasi = PRODUK_KE_BAHAN_BAKU_KOMPARASI.get(nama_untuk_chart)

    filter_hasil_kb = None
    if bahan_baku_komparasi:
        st.markdown("<hr style='margin: 32px 0 24px 0; border-color: rgba(128,128,128,0.2);'>", unsafe_allow_html=True)
        filter_hasil_kb = _render_filter_komparasi_harga_pasar(load_data, bahan_baku_komparasi)

    # == 2 kolom chart: kiri = Stock harian (Safety Stock vs Stock PG),
    # kanan = Komparasi Harga Pasar Bahan Baku (kalau produk ini punya
    # pemetaan; kalau tidak, kolom kanan dikosongkan).
    col_kiri, col_kanan = st.columns([2, 3])
    with col_kiri:
        if bulan_terpilih:
            _render_chart_harian(load_data, nama_untuk_chart, tahun_data, bulan_terpilih)
    with col_kanan:
        if bahan_baku_komparasi:
            _render_chart_komparasi_harga_pasar(load_data, filter_hasil_kb)

    # == Export Google Docs -- 2 tombol: produk yang sedang dipilih saja,
    # atau seluruh 9 produk sekaligus dalam 1 dokumen (bernomor 1, 2, 3, ...).
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<hr style='margin: 24px 0; border-color: rgba(128,128,128,0.2);'>", unsafe_allow_html=True)
    _render_tombol_export_ringkasan(
        load_data, tahun_data, nama_untuk_chart, tabel_gabungan_aktif,
        bulan_terpilih, filter_hasil_kb
    )


# -----------------------------------------------------------------------
# EXPORT GOOGLE DOCS (tab Ringkasan)
# -----------------------------------------------------------------------

# Urutan & daftar produk utk tombol "Generate Docs (Semua Produk)", sesuai
# urutan yang diminta: Asam Sulfat, Sulfur, PA (Asam Fosfat), Phospate Rock,
# ZA, KCL, DAP, NH4Cl, Ammonia. Key di sini HARUS persis sama dgn key
# VIRTUAL_PRODUCTS supaya bisa dipakai memanggil _get_data_virtual dkk.
URUTAN_BATCH_EXPORT_RINGKASAN = [
    "Asam Sulfat", "Sulphur", "PA", "Phospate Rock",
    "ZA", "KCL", "DAP", "NH4Cl", "Ammonia",
]


def _ambil_data_lengkap_produk_untuk_export(load_data, tahun_data, nama_produk):
    """
    Mengambil semua data yang dibutuhkan utk export 1 produk ke Google Docs:
    tabel_gabungan (kategori+shipment, dgn bulan filter DEFAULT produk itu
    sendiri -- lihat catatan di bawah), df_chart_stock, dan image_bytes
    chart komparasi (memakai default_komparasi dari config, BUKAN filter yg
    sedang aktif di layar -- supaya batch export tidak bergantung pada
    interaksi UI utk produk lain yang sedang tidak aktif/terlihat).

    Dipakai baik oleh tombol single export (utk produk SELAIN yang sedang
    aktif di layar -- kalau produk yang aktif, dipakai tabel_gabungan yang
    sudah dihitung dari filter yang sedang dipilih user) maupun batch export
    (semua produk, tidak ada satupun yang "sedang aktif" di layar).

    Return dict {"nama_produk", "tabel_gabungan", "df_chart_stock",
    "image_bytes_komparasi"}, atau None kalau data produk ini kosong.
    """
    if nama_produk not in VIRTUAL_PRODUCTS:
        return None
    cfg = VIRTUAL_PRODUCTS[nama_produk]
    df_long = _get_data_virtual(load_data, tahun_data, cfg)
    if df_long.empty:
        return None
    df_formula = pd.DataFrame(cfg["formula"])

    pivot_dasar = _hitung_agregat_kategori(df_long)
    if pivot_dasar.empty:
        return None
    pivot_lengkap = _terapkan_formula(pivot_dasar, df_formula)

    urutan_preset = cfg.get("urutan_tampil", [])
    kategori_ada = list(pivot_lengkap.index)
    urutan_final = [k for k in urutan_preset if k in kategori_ada] + \
                   sorted([k for k in kategori_ada if k not in urutan_preset])
    pivot_lengkap = pivot_lengkap.loc[urutan_final]

    bulan_tersedia = [b for b in BULAN_KEY_ORDER if b != 'realisasi' and b in pivot_lengkap.columns]
    if not bulan_tersedia:
        return None

    # Default bulan: 3 bulan mulai bulan berjalan (sama dgn logika default
    # tampilan web), supaya export batch tidak bergantung pilihan UI.
    current_month_idx = datetime.now().month - 1
    cal_keys = ['jan', 'feb', 'mar', 'apr', 'mei', 'jun', 'jul', 'agust', 'sep', 'okt', 'nop', 'des']
    target_keys = cal_keys[current_month_idx: current_month_idx + 3]
    bulan_key_terpilih = [b for b in target_keys if b in bulan_tersedia]
    if not bulan_key_terpilih:
        bulan_key_terpilih = bulan_tersedia[-3:] if len(bulan_tersedia) >= 3 else bulan_tersedia

    tabel = pivot_lengkap[bulan_key_terpilih].copy()
    tabel.columns = [BULAN_KEY_TO_LABEL[b] for b in bulan_key_terpilih]
    fmt_func = lambda v: f"{v:,.0f}" if pd.notna(v) else "-"
    tabel_display = tabel.map(fmt_func) if hasattr(tabel, "map") else tabel.applymap(fmt_func)
    tabel_display.index.name = "Keterangan"

    df_shipment = _bentuk_baris_shipment_rbb(load_data, nama_produk, tahun_data, bulan_key_terpilih)
    tabel_gabungan = tabel_display
    if not df_shipment.empty:
        df_shipment_display = df_shipment.copy()
        for c in df_shipment_display.columns:
            df_shipment_display[c] = df_shipment_display[c].apply(
                lambda v: v if (v is not None and not pd.isna(v)) else "-"
            )
        df_shipment_display.index.name = "Keterangan"
        mapping = PRODUK_KE_KOMODITAS_RBB.get(nama_produk, {})
        setelah_kategori = mapping.get("setelah_kategori")
        if setelah_kategori and setelah_kategori in tabel_display.index:
            posisi = list(tabel_display.index).index(setelah_kategori) + 1
            tabel_gabungan = pd.concat([
                tabel_display.iloc[:posisi], df_shipment_display, tabel_display.iloc[posisi:],
            ])
        else:
            tabel_gabungan = pd.concat([tabel_display, df_shipment_display])

    # -- Chart Stock harian --
    df_chart_stock = None
    virtual_tersedia = _get_daftar_virtual_produk_chart(load_data, tahun_data)
    if nama_produk in virtual_tersedia:
        df_chart_stock = _get_data_chart_harian(load_data, nama_produk, tahun_data)
        if not df_chart_stock.empty:
            bulan_num_map = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "mei": 5, "jun": 6,
                              "jul": 7, "agust": 8, "sep": 9, "okt": 10, "nop": 11, "des": 12}
            angka_bulan = [bulan_num_map[b] for b in bulan_key_terpilih if b in bulan_num_map]
            df_chart_stock = df_chart_stock[df_chart_stock['tanggal'].dt.month.isin(angka_bulan)]

    # -- Chart Komparasi Harga Pasar (pakai default_komparasi dari config,
    # BUKAN filter yang sedang aktif di layar -- lihat docstring) --
    image_bytes_komparasi = None
    bahan_baku_komparasi = PRODUK_KE_BAHAN_BAKU_KOMPARASI.get(nama_produk)
    if bahan_baku_komparasi:
        image_bytes_komparasi = _render_image_komparasi_dari_default(load_data, bahan_baku_komparasi)

    return {
        "nama_produk": nama_produk,
        "tabel_gabungan": tabel_gabungan,
        "df_chart_stock": df_chart_stock,
        "image_bytes_komparasi": image_bytes_komparasi,
    }


def _render_image_komparasi_dari_default(load_data, bahan_baku_key):
    """
    Menghasilkan PNG bytes chart Komparasi Harga Pasar utk 1 bahan baku,
    memakai default_komparasi dari config (BAHAN_BAKU_KOMPARASI_CONFIG),
    BUKAN filter yang sedang aktif di UI -- dipakai khusus utk proses
    export (baik single produk lain yg tidak sedang aktif, maupun batch
    semua produk), supaya hasilnya konsisten & tidak bergantung state UI.
    Meniru pola _proses_batch_bahan_baku di v_bb_bahan_baku.py, tapi
    disederhanakan (tanpa resume/tabel histori, cuma gambar chart-nya saja).
    Return None kalau data tidak tersedia.
    """
    config = _kb_get_config(bahan_baku_key)
    label_bb = config["label"]
    db_value = config["db_value"]
    default_komparasi_list = config.get("default_komparasi", [])
    if not default_komparasi_list:
        return None

    if isinstance(db_value, (list, tuple)):
        alias_list = "', '".join([a.lower().strip() for a in db_value])
        where_clause = f"lower(trim(bahan_baku)) IN ('{alias_list}')"
    else:
        where_clause = f"bahan_baku = '{db_value}'"

    query = f"""
        SELECT tanggal_terbit, nama_majalah, incoterm, harga_min, harga_max
        FROM master_harga_bahan_baku
        WHERE {where_clause}
        ORDER BY tanggal_terbit ASC
    """
    df = load_data(query)
    if df.empty:
        return None

    # Batasi rentang tanggal ke 1 tahun terakhir dari data terbaru (sama
    # dgn default rentang tanggal di mode interaktif -- lihat
    # _render_filter_komparasi_harga_pasar). TANPA batas ini, produk dgn
    # histori data bertahun-tahun akan menghasilkan chart yang sangat lebar
    # (ribuan titik data), yang gambar PNG-nya walau ukuran FILE-nya kecil,
    # dimensi PIKSELnya bisa melebihi batas insertInlineImage Google Docs
    # API ("the provided image is too large") -- ini persis kasus yang
    # ditemukan saat generate batch utk produk dgn data histori panjang.
    #
    # Kolom 'tanggal_terbit' dikonversi ke datetime64 dulu (bisa jadi objek
    # date/string/Timestamp campuran tergantung driver DB), supaya
    # perbandingan tanggal di bawah tidak error krn mismatch tipe data.
    df['tanggal_terbit'] = pd.to_datetime(df['tanggal_terbit'])
    max_date = df['tanggal_terbit'].max()
    min_date_filter = max_date - pd.DateOffset(years=1)
    df = df[df['tanggal_terbit'] >= min_date_filter].copy()
    if df.empty:
        return None

    default_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
    df_plot = pd.DataFrame()
    warna_map = {}
    label_yang_tampil = []

    for idx, item in enumerate(default_komparasi_list):
        majalah = item.get("majalah")
        incoterm = item.get("incoterm")
        tampil_chart = item.get("tampil_chart", True)
        temp_df = df[(df['nama_majalah'] == majalah) & (df['incoterm'] == incoterm)].copy()
        if temp_df.empty:
            continue
        temp_df['label_komparasi'] = temp_df['nama_majalah'] + ' - ' + temp_df['incoterm']
        temp_df['label_komparasi'] = temp_df['label_komparasi'].apply(lambda x: MAPPING_SINGKATAN.get(x, x))
        df_plot = pd.concat([df_plot, temp_df], ignore_index=True)
        label_singkat = MAPPING_SINGKATAN.get(f"{majalah} - {incoterm}", f"{majalah} - {incoterm}")
        warna_map[label_singkat] = default_colors[idx % len(default_colors)]
        if tampil_chart:
            label_yang_tampil.append(label_singkat)

    if df_plot.empty:
        return None

    df_plot['harga_avg'] = (df_plot['harga_min'] + df_plot['harga_max']) / 2
    df_plot['tanggal_terbit'] = pd.to_datetime(df_plot['tanggal_terbit'])
    df_plot = df_plot.sort_values('tanggal_terbit')
    y_col, y_label, jenis_harga = 'harga_avg', 'Harga Rata-rata (USD/MT)', 'AVERAGE'

    df_plot_chart = df_plot[df_plot['label_komparasi'].isin(label_yang_tampil)].copy()

    # -- Harga Perolehan (selalu ditampilkan, sama seperti chart interaktif) --
    df_hp = _kb_load_harga_perolehan(load_data, db_value, df['tanggal_terbit'].min(), df['tanggal_terbit'].max())
    label_hp_dipakai = None
    if not df_hp.empty:
        df_hp = df_hp.copy()
        df_hp['tanggal_terbit'] = pd.to_datetime(df_hp['tanggal_terbit'])
        df_hp['label_komparasi'] = LABEL_HARGA_PEROLEHAN
        df_hp[y_col] = df_hp['harga_perolehan']
        df_plot_chart = pd.concat([df_plot_chart, df_hp[['tanggal_terbit', 'label_komparasi', y_col]]], ignore_index=True)
        warna_map[LABEL_HARGA_PEROLEHAN] = WARNA_HARGA_PEROLEHAN_DEFAULT
        label_hp_dipakai = LABEL_HARGA_PEROLEHAN

    return gdocs_export.render_chart_matplotlib(
        df_plot_chart=df_plot_chart, y_col=y_col, y_label=y_label, jenis_harga=jenis_harga,
        label_bb=label_bb, warna_map=warna_map, label_harga_perolehan=label_hp_dipakai,
    )


def _render_tombol_export_ringkasan(load_data, tahun_data, nama_produk_aktif, tabel_gabungan_aktif,
                                      bulan_terpilih_aktif, filter_hasil_kb_aktif):
    """2 tombol export Google Docs: produk yang sedang aktif di layar saja,
    atau seluruh 9 produk (urutan tetap, lihat URUTAN_BATCH_EXPORT_RINGKASAN)
    dalam 1 dokumen bernomor."""
    import gdocs_export_ringkasan

    tgl_hari_ini = datetime.now()
    tanggal_update_str = f"{tgl_hari_ini.day:02d} {BULAN_INDO_KOMPARASI[tgl_hari_ini.month]} {tgl_hari_ini.year}"

    col_single, col_batch = st.columns(2)

    with col_single:
        if st.button(
            f":material/description: Generate Docs ({nama_produk_aktif})",
            type="primary", use_container_width=True, key="ksb_gen_docs_single",
        ):
            if tabel_gabungan_aktif is None:
                st.warning("Tidak ada tabel Ringkasan untuk produk ini.")
            else:
                with st.spinner(f"Membuat dokumen Google Docs untuk {nama_produk_aktif}..."):
                    try:
                        df_chart_stock = None
                        virtual_tersedia = _get_daftar_virtual_produk_chart(load_data, tahun_data)
                        if nama_produk_aktif in virtual_tersedia and bulan_terpilih_aktif:
                            df_chart_stock = _get_data_chart_harian(load_data, nama_produk_aktif, tahun_data)
                            if not df_chart_stock.empty:
                                bulan_num_map = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "mei": 5, "jun": 6,
                                                  "jul": 7, "agust": 8, "sep": 9, "okt": 10, "nop": 11, "des": 12}
                                angka_bulan = [bulan_num_map[b] for b in bulan_terpilih_aktif if b in bulan_num_map]
                                df_chart_stock = df_chart_stock[df_chart_stock['tanggal'].dt.month.isin(angka_bulan)]

                        image_bytes_komparasi = None
                        if filter_hasil_kb_aktif is not None:
                            image_bytes_komparasi = _render_image_komparasi_untuk_export(load_data, filter_hasil_kb_aktif)

                        doc_url = gdocs_export_ringkasan.generate_google_doc_ringkasan(
                            nama_produk=nama_produk_aktif,
                            tabel_gabungan=tabel_gabungan_aktif,
                            tanggal_update_str=tanggal_update_str,
                            df_chart_stock=df_chart_stock,
                            image_bytes_komparasi=image_bytes_komparasi,
                        )
                        st.success("Dokumen Google Docs berhasil dibuat!")
                        st.link_button(":material/open_in_new: Buka Google Docs", doc_url, use_container_width=False)
                    except Exception as e:
                        st.error(f"Gagal membuat Google Docs: {e}")

    with col_batch:
        if st.button(
            ":material/library_books: Generate Docs (Semua Produk)",
            type="primary", use_container_width=True, key="ksb_gen_docs_batch",
        ):
            with st.spinner("Membuat kompilasi dokumen Ringkasan seluruh produk... (mungkin memakan waktu)"):
                try:
                    list_data_produk = []
                    for nama_produk in URUTAN_BATCH_EXPORT_RINGKASAN:
                        hasil = _ambil_data_lengkap_produk_untuk_export(load_data, tahun_data, nama_produk)
                        if hasil:
                            list_data_produk.append(hasil)

                    if not list_data_produk:
                        st.warning("Tidak ada data yang valid untuk di-export.")
                    else:
                        doc_url = gdocs_export_ringkasan.generate_google_doc_ringkasan_batch(
                            list_data_produk=list_data_produk,
                            tanggal_update_str=tanggal_update_str,
                        )
                        st.success("Dokumen kompilasi Google Docs berhasil dibuat!")
                        st.link_button(":material/open_in_new: Buka Dokumen Kompilasi", doc_url, use_container_width=False)
                except Exception as e:
                    st.error(f"Gagal membuat Dokumen Kompilasi: {e}")


def _render_image_komparasi_untuk_export(load_data, filter_hasil_kb):
    """Bangun PNG bytes chart Komparasi Harga Pasar dari filter_hasil_kb yang
    SEDANG AKTIF di layar (hasil _render_filter_komparasi_harga_pasar) --
    dipakai khusus tombol 'Generate Docs (Produk Ini)' supaya WYSIWYG
    (dokumen persis sesuai filter yang sedang dipilih user), berbeda dari
    _render_image_komparasi_dari_default yang dipakai proses batch."""
    if filter_hasil_kb is None:
        return None

    df = filter_hasil_kb["df"]
    label_bb = filter_hasil_kb["label_bb"]
    db_value = filter_hasil_kb["db_value"]
    start_date = filter_hasil_kb["start_date"]
    end_date = filter_hasil_kb["end_date"]
    jenis_harga = filter_hasil_kb["jenis_harga"]
    komparasi_data = filter_hasil_kb["komparasi_data"]
    warna_map = dict(filter_hasil_kb["warna_map"])
    warna_harga_perolehan = filter_hasil_kb["warna_harga_perolehan"]

    df_plot = pd.DataFrame()
    for item in komparasi_data:
        majalah = item["majalah"]
        incoterms = item["incoterms"]
        temp_df = df[(df['nama_majalah'] == majalah) & (df['incoterm'].isin(incoterms)) &
                     (df['tanggal_terbit'] >= start_date) & (df['tanggal_terbit'] <= end_date)].copy()
        if not temp_df.empty:
            temp_df['label_komparasi'] = temp_df['nama_majalah'] + ' - ' + temp_df['incoterm']
            temp_df['label_komparasi'] = temp_df['label_komparasi'].apply(lambda x: MAPPING_SINGKATAN.get(x, x))
            df_plot = pd.concat([df_plot, temp_df], ignore_index=True)

    if df_plot.empty:
        return None

    df_plot['harga_avg'] = (df_plot['harga_min'] + df_plot['harga_max']) / 2
    df_plot['tanggal_terbit'] = pd.to_datetime(df_plot['tanggal_terbit'])
    df_plot = df_plot.sort_values('tanggal_terbit')

    if jenis_harga == "MIN":
        y_col, y_label = 'harga_min', 'Harga Minimum (USD/MT)'
    elif jenis_harga == "MAX":
        y_col, y_label = 'harga_max', 'Harga Maksimum (USD/MT)'
    else:
        y_col, y_label = 'harga_avg', 'Harga Rata-rata (USD/MT)'

    label_yang_tampil = []
    for item in komparasi_data:
        if item.get("tampil_chart", True):
            for incoterm in item["incoterms"]:
                label_asli = f"{item['majalah']} - {incoterm}"
                label_singkat = MAPPING_SINGKATAN.get(label_asli, label_asli)
                label_yang_tampil.append(label_singkat)

    df_plot_chart = df_plot[df_plot['label_komparasi'].isin(label_yang_tampil)].copy()

    df_hp = _kb_load_harga_perolehan(load_data, db_value, start_date, end_date)
    label_hp_dipakai = None
    if not df_hp.empty:
        df_hp = df_hp.copy()
        df_hp['tanggal_terbit'] = pd.to_datetime(df_hp['tanggal_terbit'])
        df_hp['label_komparasi'] = LABEL_HARGA_PEROLEHAN
        df_hp[y_col] = df_hp['harga_perolehan']
        df_plot_chart = pd.concat([df_plot_chart, df_hp[['tanggal_terbit', 'label_komparasi', y_col]]], ignore_index=True)
        warna_map[LABEL_HARGA_PEROLEHAN] = warna_harga_perolehan
        label_hp_dipakai = LABEL_HARGA_PEROLEHAN

    if df_plot_chart.empty:
        return None

    return gdocs_export.render_chart_matplotlib(
        df_plot_chart=df_plot_chart, y_col=y_col, y_label=y_label, jenis_harga=jenis_harga,
        label_bb=label_bb, warna_map=warna_map, label_harga_perolehan=label_hp_dipakai,
    )

def _render_data_mentah(df_long):
    st.markdown(
        "<p style='font-size:13px; opacity:0.6; margin-bottom:12px;'>"
        "Data ditampilkan apa adanya sesuai urutan baris di file Excel sumber. "
        "Nilai kosong (-) di Excel ditampilkan sebagai kosong di sini."
        "</p>", unsafe_allow_html=True
    )

    df_wide = _pivot_wide(df_long)
    if df_wide.empty:
        st.info("Tidak ada data.")
        return

    fmt_cols = [c for c in df_wide.columns if c not in ('Label', 'Kategori')]
    df_display = df_wide.copy()
    for c in fmt_cols:
        df_display[c] = df_display[c].apply(lambda v: f"{v:,.0f}" if pd.notna(v) else "")
    df_display['Kategori'] = df_display['Kategori'].fillna("-").replace("", "-")

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        height=min(600, 40 + 35 * len(df_display)),
    )
    st.caption(f"Total {len(df_display)} baris label untuk produk ini.")


# -----------------------------------------------------------------------
# TAB: KATEGORISASI (teks bebas per produk + formula)
# -----------------------------------------------------------------------

def _render_kategorisasi(load_data, df_long, get_engine_fn, sumber_sheet, produk, tahun_data):
    st.markdown(
        "<p style='font-size:13px; opacity:0.6; margin-bottom:12px;'>"
        "Tandai setiap baris label dengan nama kategori bebas (mis. 'Stok Awal', 'Produksi', dst). "
        "Beberapa baris boleh memakai nama kategori yang sama -- nilainya akan dijumlahkan otomatis "
        "di tab Ringkasan. Kosongkan bila baris tidak relevan."
        "</p>", unsafe_allow_html=True
    )

    df_label = (
        df_long[['id', 'urutan_baris', 'label_baris', 'kategori']]
        .drop_duplicates(subset=['urutan_baris'])
        .sort_values('urutan_baris')
        .reset_index(drop=True)
    )
    df_label['kategori'] = df_label['kategori'].fillna("")

    kategori_terpakai = sorted(set(k for k in df_label['kategori'].tolist() if k))
    if kategori_terpakai:
        st.caption("Kategori yang sudah dipakai di produk ini: " + ", ".join(f"`{k}`" for k in kategori_terpakai))

    editor_key = f"editor_kategori_{sumber_sheet}_{produk}_{tahun_data}"
    df_editor = df_label[['label_baris', 'kategori']].rename(
        columns={'label_baris': 'Label', 'kategori': 'Kategori'}
    )

    edited = st.data_editor(
        df_editor,
        use_container_width=True,
        hide_index=True,
        height=min(600, 40 + 35 * len(df_editor)),
        column_config={
            "Label": st.column_config.TextColumn("Label", disabled=True, width="large"),
            "Kategori": st.column_config.TextColumn(
                "Kategori", width="medium",
                help="Ketik nama kategori bebas. Kosongkan jika baris ini tidak relevan."
            ),
        },
        key=editor_key,
    )

    col_simpan, col_info = st.columns([1, 4])
    with col_simpan:
        simpan = st.button(
            ":material/save: Simpan Kategori", type="primary",
            key=f"btn_simpan_kategori_{sumber_sheet}_{produk}_{tahun_data}"
        )

    if simpan:
        updates = []
        for i, row in edited.iterrows():
            urutan = df_label.iloc[i]['urutan_baris']
            kategori_baru = (row['Kategori'] or "").strip()
            kategori_lama = (df_label.iloc[i]['kategori'] or "").strip()
            if kategori_baru != kategori_lama:
                updates.append({'urutan_baris': urutan, 'kategori': kategori_baru})

        if not updates:
            st.info("Tidak ada perubahan kategori untuk disimpan.")
        else:
            engine = get_engine_fn()
            total_updated = 0
            with engine.begin() as conn:
                for u in updates:
                    kategori_val = u['kategori'] if u['kategori'] else None
                    result = conn.execute(
                        text("""
                            UPDATE kondisi_stock_bb_raw
                            SET kategori = :kategori, updated_at = CURRENT_TIMESTAMP
                            WHERE sumber_sheet = :sumber AND produk = :produk
                              AND tahun_data = :tahun AND urutan_baris = :urutan
                        """),
                        {
                            'kategori': kategori_val, 'sumber': sumber_sheet, 'produk': produk,
                            'tahun': tahun_data, 'urutan': int(u['urutan_baris']),
                        }
                    )
                    total_updated += result.rowcount

            st.cache_data.clear()
            st.success(f"Berhasil menyimpan {len(updates)} perubahan kategori ({total_updated} record diupdate).")
            st.rerun()

    with col_info:
        n_kosong = (df_label['kategori'] == "").sum()
        n_total = len(df_label)
        if n_kosong > 0:
            st.caption(f":material/warning: {n_kosong} dari {n_total} baris belum dikategorikan.")
        else:
            st.caption(f":material/check_circle: Semua {n_total} baris sudah dikategorikan.")

    st.markdown("<hr style='margin:20px 0;'>", unsafe_allow_html=True)
    st.markdown("**:material/functions: Kategori Formula (opsional)**")
    st.markdown(
        "<p style='font-size:13px; opacity:0.6; margin-bottom:12px;'>"
        "Buat kategori tambahan yang nilainya dihitung otomatis dari kategori lain di atas "
        "(mis. 'Stok Akhir' = Stok Awal + Produksi + Impor − Pemakaian)."
        "</p>", unsafe_allow_html=True
    )

    df_formula = _get_formula_list(load_data, sumber_sheet, produk)

    if not df_formula.empty:
        for _, frow in df_formula.iterrows():
            try:
                komponen = json.loads(frow['komponen']) if isinstance(frow['komponen'], str) else frow['komponen']
            except Exception:
                komponen = []
            rumus_str = ""
            for i, k in enumerate(komponen):
                if i == 0:
                    rumus_str += f"{k['kategori']}"
                else:
                    rumus_str += f" {k['operator']} {k['kategori']}"
            col_txt, col_del = st.columns([5, 1])
            with col_txt:
                st.markdown(f"- **{frow['kategori_hasil']}** = {rumus_str}")
            with col_del:
                if st.button("Hapus", icon=":material/delete:", key=f"del_formula_{frow['id']}"):
                    engine = get_engine_fn()
                    _hapus_formula(engine, int(frow['id']))
                    st.cache_data.clear()
                    st.rerun()

    with st.expander("Tambah Kategori Formula Baru", icon=":material/add:"):
        opsi_kategori = kategori_terpakai if kategori_terpakai else []
        if not opsi_kategori:
            st.info("Belum ada kategori yang ditandai di atas. Tandai beberapa baris dulu sebelum membuat formula.")
        else:
            nama_hasil = st.text_input("Nama Kategori Hasil (mis. 'Stok Akhir')", key=f"formula_nama_{sumber_sheet}_{produk}")

            n_komponen = st.number_input("Jumlah komponen", min_value=1, max_value=6, value=2, key=f"formula_n_{sumber_sheet}_{produk}")

            komponen_input = []
            for i in range(int(n_komponen)):
                c1, c2 = st.columns([1, 3]) if i == 0 else st.columns([1, 3])
                with c1:
                    if i == 0:
                        st.markdown("<div style='padding-top:28px; text-align:center;'>—</div>", unsafe_allow_html=True)
                        op = "+"
                    else:
                        op = st.selectbox("Operator", OPERATOR_OPTIONS, key=f"formula_op_{sumber_sheet}_{produk}_{i}", label_visibility="collapsed" if i > 0 else "visible")
                with c2:
                    kat = st.selectbox(
                        f"Kategori komponen {i+1}", opsi_kategori,
                        key=f"formula_kat_{sumber_sheet}_{produk}_{i}",
                        label_visibility="visible"
                    )
                komponen_input.append({'kategori': kat, 'operator': op})

            if st.button("Simpan Formula", type="primary", icon=":material/save:", key=f"btn_simpan_formula_{sumber_sheet}_{produk}"):
                if not nama_hasil.strip():
                    st.error("Nama kategori hasil tidak boleh kosong.")
                else:
                    engine = get_engine_fn()
                    _simpan_formula(engine, sumber_sheet, produk, nama_hasil.strip(), komponen_input)
                    st.cache_data.clear()
                    st.success(f"Formula '{nama_hasil.strip()}' berhasil disimpan.")
                    st.rerun()


# -----------------------------------------------------------------------
# TAB: RENCANA KEBUTUHAN BB (sheet 'Data BB <tahun>', shipment per komoditas)
# -----------------------------------------------------------------------

def _render_tab_rencana_bb(load_data):
    """Render isi tab 'Rencana Kebutuhan BB'. Sumber data terpisah dari
    kondisi_stock_bb_raw -- pakai dropdown tahun sendiri (rbb_tahun) karena
    file Excel-nya juga selalu diupload terpisah dari file Pupuk/Bahan Baku."""

    tahun_list_rbb = _get_tahun_tersedia_rbb(load_data)
    if not tahun_list_rbb:
        st.info(
            "Belum ada data Rencana Kebutuhan BB di database. Silakan upload data "
            "terlebih dahulu lewat menu **Manajemen Data → Kondisi Stock BB** "
            "(kolom upload 'File Rencana Kebutuhan BB')."
        )
        return

    col_tahun, _ = st.columns([1, 3])
    with col_tahun:
        tahun_pilih_rbb = st.selectbox("Tahun Data", options=tahun_list_rbb, index=0, key="rbb_tahun")

    daftar_komoditas = _get_daftar_komoditas_rbb(load_data, tahun_pilih_rbb)
    if not daftar_komoditas:
        st.info(f"Tidak ada data untuk tahun {tahun_pilih_rbb}.")
        return

    komoditas_pilih = st.selectbox(
        "Pilih Komoditas", options=daftar_komoditas, key="rbb_komoditas"
    )

    df_long = _get_data_komoditas_rbb(load_data, komoditas_pilih, tahun_pilih_rbb)
    if df_long.empty:
        st.info("Tidak ada data untuk komoditas ini.")
        return

    # -- Info ringkas komoditas (kolom R-X), diambil dari baris pertama --
    info = df_long.iloc[0]
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Estimasi Qty/Shipment", info['estimasi_qty_shipment'] or "-")
    with col2:
        st.metric("Posisi Stok", info['posisi_stok'] or "-")
    with col3:
        st.metric("Safety Stock", info['safety_stock'] or "-")
    with col4:
        st.metric("Harga Perolehan Terakhir", info['harga_perolehan_terakhir'] or "-")

    if info['keterangan'] or info['rute_kapal_terdampak'] or info['mitigasi_risiko']:
        with st.expander("Keterangan & Mitigasi Risiko", icon=":material/info:"):
            if info['keterangan']:
                st.markdown(f"**Keterangan:**\n\n{info['keterangan']}")
            if info['rute_kapal_terdampak']:
                st.markdown(f"**Rute Kapal Terdampak:**\n\n{info['rute_kapal_terdampak']}")
            if info['mitigasi_risiko']:
                st.markdown(f"**Mitigasi Risiko:**\n\n{info['mitigasi_risiko']}")

    st.markdown("<br>", unsafe_allow_html=True)

    # -- Filter rentang bulan --
    bulan_tersedia = [b for b in BULAN_KEY_ORDER_RBB if b in df_long['bulan'].unique()]
    bulan_label_terpilih = st.multiselect(
        "Filter bulan (kosongkan untuk tampilkan semua)",
        options=[BULAN_KEY_TO_LABEL_RBB[b] for b in bulan_tersedia],
        default=[],
        key=f"rbb_filter_bulan_{komoditas_pilih}",
    )

    # -- Tabel shipment per origin/suplier --
    st.markdown(f"**Rencana Kedatangan/Kebutuhan - {komoditas_pilih}**")
    st.markdown(
        "<p style='font-size:13px; opacity:0.6; margin-bottom:12px;'>"
        "Data ditampilkan apa adanya sesuai isi sel Excel sumber (tanggal, nama kapal, "
        "kuantitas, dan info PO/laycan/ETA bila ada)."
        "</p>", unsafe_allow_html=True
    )

    df_wide = _pivot_shipment_wide(df_long)
    if df_wide.empty:
        st.info("Tidak ada data shipment untuk ditampilkan.")
        return

    if bulan_label_terpilih:
        kolom_tampil = ['Origin', 'Suplier', 'Harga (USD/MT)'] + bulan_label_terpilih
        kolom_tampil = [c for c in kolom_tampil if c in df_wide.columns]
        df_wide = df_wide[kolom_tampil]

    df_display = df_wide.fillna("-").replace("", "-")

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        height=min(600, 60 + 45 * len(df_display)),
    )
    st.caption(f"Total {len(df_display)} baris origin/suplier untuk komoditas ini.")


# -----------------------------------------------------------------------
# TAB: RINGKASAN (transpose: kategori = baris, bulan = kolom, filter rentang)
# -----------------------------------------------------------------------

def _bentuk_baris_shipment_rbb(load_data, produk, tahun_data, bulan_key_terpilih):
    """Bentuk baris tambahan berisi rencana shipment (dari rencana_bb_raw)
    utk disisipkan ke tabel Ringkasan, kalau produk ini punya pemetaan ke
    komoditas Data BB (lihat PRODUK_KE_KOMODITAS_RBB).

    Return DataFrame dgn index = label baris HTML 2-baris (mis. '- Agrifields
    <br>Origin : Egypt MG') dan kolom = label bulan terpilih (mis.
    'September'), berisi teks shipment mentah persis dari Excel sumber
    (baris multi-baris asli digabung pakai <br> juga -- lihat pemanggil
    fungsi ini utk konversi \\n -> <br> pada isi_shipment). Baris dgn
    suplier 'Kebutuhan belum ada kontrak' TIDAK disertakan. Baris yang,
    untuk SELURUH bulan terpilih, tidak punya isi shipment sama sekali juga
    tidak disertakan (spt Hongkong JH yg kosong di bulan yg dipilih).

    Label & isi sengaja pakai tag HTML <br> (bukan '\\n') karena tabel akhir
    dirender lewat st.markdown(df.to_html(...), unsafe_allow_html=True) --
    st.dataframe tidak bisa menampilkan line break di dalam sel/index.

    Return DataFrame kosong kalau produk tidak punya pemetaan komoditas,
    atau tidak ada data shipment sama sekali.
    """
    mapping = PRODUK_KE_KOMODITAS_RBB.get(produk)
    if not mapping:
        return pd.DataFrame()
    komoditas = mapping["komoditas"]

    df_rbb = _get_data_komoditas_rbb(load_data, komoditas, tahun_data)
    if df_rbb.empty:
        return pd.DataFrame()

    # label bulan tabel utama (Ringkasan) memakai nama bulan panjang
    # ("September"), sedangkan key bulan (bulan_key_terpilih) memakai kunci
    # internal ("sep") yg SAMA persis dgn kolom 'bulan' di rencana_bb_raw.
    kolom_label = [BULAN_KEY_TO_LABEL[b] for b in bulan_key_terpilih]

    # PENTING: origin+suplier yang sama bisa muncul berkali-kali dalam 1
    # komoditas (mis. 'Ju Nong' muncul di beberapa urutan_baris berbeda
    # dengan formula harga berbeda2) -- jadi TIDAK boleh pakai label baris
    # sbg dict key (akan saling menimpa). Dikumpulkan sbg list of dict yang
    # tetap membedakan tiap urutan_baris sbg baris terpisah, baru label
    # ditentukan belakangan setelah tahu apakah label tsb unik atau tidak.
    baris_list = []  # [{'urutan_baris':..., 'label':..., **isi_per_bulan}]

    for urutan_baris, grp in df_rbb.groupby('urutan_baris'):
        suplier = grp['suplier'].iloc[0]
        origin = grp['origin'].iloc[0]

        if suplier and str(suplier).strip().lower() == RBB_SUPLIER_BELUM_KONTRAK:
            continue  # skip baris "belum ada kontrak"

        isi_per_bulan = {}
        ada_isi = False
        for bkey, blabel in zip(bulan_key_terpilih, kolom_label):
            baris_bulan = grp[grp['bulan'] == bkey]
            isi = baris_bulan['isi_shipment'].iloc[0] if not baris_bulan.empty else None
            if isi is not None and not pd.isna(isi) and str(isi).strip() != '':
                # Buang baris "PO LN : ..." dari isi shipment -- info ini
                # tidak perlu ditampilkan di tab Ringkasan, cukup baris
                # Depart/ETA/MV/Qty (lihat instruksi: sisakan 4 baris).
                baris_teks = [
                    l for l in str(isi).strip().split('\n')
                    if not l.strip().lower().startswith('po ln')
                ]
                isi_bersih = '<br>'.join(baris_teks).strip()
                if isi_bersih:
                    isi_per_bulan[blabel] = isi_bersih
                    ada_isi = True
                else:
                    isi_per_bulan[blabel] = None
            else:
                isi_per_bulan[blabel] = None

        if not ada_isi:
            continue  # baris ini kosong utk SEMUA bulan yg dipilih -> jangan tampilkan

        label_baris = f"- {suplier}<br>Origin : {origin}"
        baris_list.append({'urutan_baris': urutan_baris, 'label': label_baris, **isi_per_bulan})

    if not baris_list:
        return pd.DataFrame()

    baris_list.sort(key=lambda b: b['urutan_baris'])

    # Kalau ada label yang sama persis (origin+suplier duplikat), beri suffix
    # supaya tidak hilang saat dijadikan index DataFrame (mis. baris 1 & 8
    # sama2 'Ju Nong' -- tetap ditampilkan sbg 2 baris terpisah).
    label_count = {}
    index_final = []
    for b in baris_list:
        label_count[b['label']] = label_count.get(b['label'], 0) + 1
        index_final.append(b['label'])
    label_seen = {}
    for i, b in enumerate(baris_list):
        lbl = b['label']
        if label_count[lbl] > 1:
            label_seen[lbl] = label_seen.get(lbl, 0) + 1
            index_final[i] = f"{lbl} ({label_seen[lbl]})"

    df_shipment = pd.DataFrame(
        [{k: v for k, v in b.items() if k not in ('urutan_baris', 'label')} for b in baris_list],
        index=index_final,
    )
    df_shipment = df_shipment[kolom_label]  # pastikan urutan kolom sesuai bulan terpilih
    return df_shipment


def _render_ringkasan(load_data, tahun_data, df_long, df_formula, produk, sumber_sheet=None, urutan_preset=None):
    """Return (bulan_key_terpilih, tabel_gabungan): bulan_key_terpilih dipakai
    utk filter chart Stock harian, tabel_gabungan (DataFrame kategori +
    shipment, index=Keterangan boleh berisi tag <br>) dipakai utk export
    Google Docs (lihat _render_tab_ringkasan & tombol Generate Docs)."""
    pivot_dasar = _hitung_agregat_kategori(df_long)

    if pivot_dasar.empty:
        st.info("Belum ada baris yang dikategorikan untuk produk ini.")
        return [], None

    pivot_lengkap = _terapkan_formula(pivot_dasar, df_formula)

    if urutan_preset is None:
        urutan_preset = []

    kategori_ada = list(pivot_lengkap.index)
    urutan_final = [k for k in urutan_preset if k in kategori_ada] + \
                   sorted([k for k in kategori_ada if k not in urutan_preset])
    pivot_lengkap = pivot_lengkap.loc[urutan_final]

    bulan_tersedia = [b for b in BULAN_KEY_ORDER if b != 'realisasi' and b in pivot_lengkap.columns]
    if not bulan_tersedia:
        st.info("Tidak ada data bulanan untuk kategori yang sudah ditandai.")
        return [], None

    current_month_idx = datetime.now().month - 1
    cal_keys = ['jan', 'feb', 'mar', 'apr', 'mei', 'jun', 'jul', 'agust', 'sep', 'okt', 'nop', 'des']

    target_keys = cal_keys[current_month_idx : current_month_idx + 3]
    default_bulan = [b for b in target_keys if b in bulan_tersedia]

    if not default_bulan:
        default_bulan = bulan_tersedia[-3:] if len(bulan_tersedia) >= 3 else bulan_tersedia

    bulan_label_terpilih = st.multiselect(
        "Pilih rentang bulan yang ditampilkan",
        options=[BULAN_KEY_TO_LABEL[b] for b in bulan_tersedia],
        default=[BULAN_KEY_TO_LABEL[b] for b in default_bulan],
        key=f"ksb_filter_bulan_{produk}"
    )

    if not bulan_label_terpilih:
        st.info("Pilih minimal 1 bulan untuk ditampilkan.")
        return [], None

    label_to_key = {v: k for k, v in BULAN_KEY_TO_LABEL.items()}
    bulan_key_terpilih = [label_to_key[l] for l in bulan_label_terpilih]
    bulan_key_terpilih = [b for b in bulan_tersedia if b in bulan_key_terpilih]

    st.markdown(f"**Ringkasan - {produk}**")

    tabel = pivot_lengkap[bulan_key_terpilih].copy()
    tabel.columns = [BULAN_KEY_TO_LABEL[b] for b in bulan_key_terpilih]

    fmt_func = lambda v: f"{v:,.0f}" if pd.notna(v) else "-"
    if hasattr(tabel, "map"):
        tabel_display = tabel.map(fmt_func)
    else:
        tabel_display = tabel.applymap(fmt_func)
    tabel_display.index.name = "Keterangan"

    # -- Sisipkan baris rencana shipment (Data BB) kalau produk ini punya
    # pemetaan ke komoditas Data BB (lihat PRODUK_KE_KOMODITAS_RBB).
    # Baris shipment disisipkan TEPAT SETELAH baris kategori tertentu
    # (mis. ZA disisipkan setelah baris 'Impor'), bukan selalu di paling
    # bawah -- lihat 'setelah_kategori' pada PRODUK_KE_KOMODITAS_RBB.
    df_shipment = _bentuk_baris_shipment_rbb(load_data, produk, tahun_data, bulan_key_terpilih)
    tabel_gabungan = tabel_display  # default kalau tidak ada shipment sama sekali
    if not df_shipment.empty:
        df_shipment_display = df_shipment.copy()
        for c in df_shipment_display.columns:
            df_shipment_display[c] = df_shipment_display[c].apply(
                lambda v: v if (v is not None and not pd.isna(v)) else "-"
            )
        df_shipment_display.index.name = "Keterangan"

        mapping = PRODUK_KE_KOMODITAS_RBB.get(produk, {})
        setelah_kategori = mapping.get("setelah_kategori")

        if setelah_kategori and setelah_kategori in tabel_display.index:
            # Sisipkan persis setelah baris 'setelah_kategori' ditemukan.
            posisi = list(tabel_display.index).index(setelah_kategori) + 1
            tabel_gabungan = pd.concat([
                tabel_display.iloc[:posisi],
                df_shipment_display,
                tabel_display.iloc[posisi:],
            ])
        else:
            # Fallback: kategori acuan tidak ditemukan di tabel produk ini
            # (mis. user belum menandai kategori tsb) -> taruh di paling
            # bawah spy datanya tetap terlihat, bukan hilang diam2.
            tabel_gabungan = pd.concat([tabel_display, df_shipment_display])

        # Baris shipment berisi tag HTML <br> (label 2-baris '- Suplier' /
        # 'Origin : X', dan isi shipment multi-baris) yang tidak bisa
        # dirender oleh st.dataframe (grid biasa hanya teks polos) -- jadi
        # tabel gabungan dirender sbg HTML lewat st.markdown supaya <br>
        # benar2 tampil sbg baris baru, bukan teks literal.
        #
        # index.name diubah jadi kolom biasa (reset_index) sebelum to_html()
        # -- kalau tetap dibiarkan sbg index.name, to_html() menghasilkan 2
        # baris <thead> terpisah (1 baris nama bulan, 1 baris lagi cuma utk
        # label 'Keterangan'), sehingga header tampak pecah jadi 2 baris.
        tabel_gabungan_html = tabel_gabungan.reset_index().rename(columns={'index': 'Keterangan'})
        html_table = tabel_gabungan_html.to_html(escape=False, index=False)
        st.markdown(
            """
            <style>
            .ksb-ringkasan-table table { width: 100%; border-collapse: collapse; font-size: 14px; }
            .ksb-ringkasan-table th, .ksb-ringkasan-table td {
                border: 1px solid rgba(128,128,128,0.3); padding: 8px 10px;
                text-align: left; vertical-align: top; white-space: normal;
            }
            .ksb-ringkasan-table th { background: rgba(128,128,128,0.08); font-weight: 600; }
            .ksb-ringkasan-table td:first-child { font-weight: 600; background: rgba(128,128,128,0.04); text-align: left; }
            .ksb-ringkasan-table th:not(:first-child),
            .ksb-ringkasan-table td:not(:first-child) { text-align: center; }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div class='ksb-ringkasan-table' style='overflow-x:auto;'>{html_table}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.dataframe(tabel_display, use_container_width=True)

    # Kembalikan key bulan terpilih (utk filter chart Stock) & tabel gabungan
    # lengkap (utk export Google Docs)
    return bulan_key_terpilih, tabel_gabungan


# -----------------------------------------------------------------------
# CHART HARIAN (line chart Safety Stock vs Stock PG, dari sheet 'Stock Chart')
# -----------------------------------------------------------------------

def _render_chart_harian(load_data, nama_produk, tahun_data, bulan_terpilih=None):
    """Menampilkan line chart harian jika nama_produk cocok dengan salah satu
    virtual_produk yang punya data di kondisi_stock_bb_chart_harian. Kalau
    tidak ada datanya, bagian ini disembunyikan diam-diam (tidak ada pesan
    error/kosong yang mengganggu)."""
    virtual_tersedia = _get_daftar_virtual_produk_chart(load_data, tahun_data)
    if nama_produk not in virtual_tersedia:
        return

    df_chart = _get_data_chart_harian(load_data, nama_produk, tahun_data)
    if df_chart.empty:
        return

    if bulan_terpilih:
        bulan_num_map = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4,
            "mei": 5, "jun": 6, "jul": 7, "agust": 8,
            "sep": 9, "okt": 10, "nop": 11, "des": 12
        }
        angka_bulan_terpilih = [bulan_num_map[b] for b in bulan_terpilih if b in bulan_num_map]
        
        df_chart = df_chart[df_chart['tanggal'].dt.month.isin(angka_bulan_terpilih)]

    if df_chart.empty:
        return

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"**:material/show_chart: Stock {nama_produk}**")

    daftar_jenis = sorted(df_chart['jenis'].unique())

    if daftar_jenis == ['default']:
        chart_data = (
            df_chart[['tanggal', 'safety_stock', 'stock_pg']]
            .rename(columns={'safety_stock': 'Safety Stock', 'stock_pg': 'Stock PG'})
        )
        
        # Ubah menjadi long format untuk Altair
        chart_data_melted = chart_data.melt(id_vars=['tanggal'], var_name='Kategori', value_name='Nilai')
        
        # Render menggunakan Altair untuk kontrol format label X yang akurat.
        # Legend "Kategori" diposisikan di bawah chart (bukan default di
        # kanan) supaya konsisten dgn chart Komparasi Harga Pasar yang
        # legend-nya juga di bawah.
        c = alt.Chart(chart_data_melted).mark_line().encode(
            x=alt.X('tanggal:T', axis=alt.Axis(format='%d %b', title='Tanggal')),
            y=alt.Y('Nilai:Q', title='Jumlah Stock'),
            color=alt.Color(
                'Kategori:N',
                scale=alt.Scale(range=["#4A90D9", "#E24949"]),
                legend=alt.Legend(orient='bottom', direction='horizontal', title='Kategori')
            )
        ).interactive()
        
        st.altair_chart(c, use_container_width=True)
        
    else:
        pivot_stock = df_chart.pivot(index='tanggal', columns='jenis', values='stock_pg')
        pivot_stock.columns = [f"Stock PG {j}" for j in pivot_stock.columns]

        pivot_safety = df_chart.pivot(index='tanggal', columns='jenis', values='safety_stock')
        pivot_safety.columns = [f"Safety Stock {j}" for j in pivot_safety.columns]

        # Reset index agar tanggal kembali menjadi kolom biasa
        chart_data = pivot_safety.join(pivot_stock).reset_index()
        
        # Ubah menjadi long format
        chart_data_melted = chart_data.melt(id_vars=['tanggal'], var_name='Kategori', value_name='Nilai')
        
        # Render menggunakan Altair. Legend "Kategori" diposisikan di bawah
        # chart, sama seperti kasus di atas.
        c = alt.Chart(chart_data_melted).mark_line().encode(
            x=alt.X('tanggal:T', axis=alt.Axis(format='%d %b', title='Tanggal')),
            y=alt.Y('Nilai:Q', title='Jumlah Stock'),
            color=alt.Color(
                'Kategori:N',
                legend=alt.Legend(orient='bottom', direction='horizontal', title='Kategori')
            )
        ).interactive()
        
        st.altair_chart(c, use_container_width=True)