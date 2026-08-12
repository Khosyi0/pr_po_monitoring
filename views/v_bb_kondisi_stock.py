import streamlit as st
import pandas as pd
import json
import altair as alt
from datetime import datetime
from sqlalchemy import text


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

OPERATOR_OPTIONS = ["+", "-", "×", "÷"]
OPERATOR_TO_FUNC = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "×": lambda a, b: a * b,
    "÷": lambda a, b: (a / b) if (b not in (0, None) and pd.notna(b)) else None,
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

    tab_pupuk, tab_bb, tab_ringkasan = st.tabs([
        ":material/agriculture: Pupuk",
        ":material/science: Bahan Baku",
        ":material/analytics: Ringkasan"
    ])

    with tab_pupuk:
        _render_sumber(load_data, _get_engine, "Pupuk", tahun_pilih)

    with tab_bb:
        _render_sumber(load_data, _get_engine, "Bahan Baku", tahun_pilih)

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

    if pilihan["type"] == "db":
        df_long = _get_data_produk(load_data, pilihan["sumber"], pilihan["produk"], tahun_data)
        df_formula = _get_formula_list(load_data, pilihan["sumber"], pilihan["produk"])
        nama_untuk_chart = pilihan["produk"]
        bulan_terpilih = _render_ringkasan(df_long, df_formula, pilihan["produk"], pilihan["sumber"])
    else:
        cfg = pilihan["config"]
        df_long = _get_data_virtual(load_data, tahun_data, cfg)
        nama_untuk_chart = pilihan["nama"]

        if df_long.empty:
            st.info("Data mentah untuk produk ini belum tersedia.")
            return

        df_formula = pd.DataFrame(cfg["formula"])
        bulan_terpilih = _render_ringkasan(df_long, df_formula, pilihan["nama"], cfg["sumber_sheet"], urutan_preset=cfg["urutan_tampil"])

    # == Chart harian -- Hanya dirender jika ada bulan yang dipilih
    if bulan_terpilih:
        _render_chart_harian(load_data, nama_untuk_chart, tahun_data, bulan_terpilih)


# -----------------------------------------------------------------------
# TAB: DATA MENTAH
# -----------------------------------------------------------------------

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
# TAB: RINGKASAN (transpose: kategori = baris, bulan = kolom, filter rentang)
# -----------------------------------------------------------------------

def _render_ringkasan(df_long, df_formula, produk, sumber_sheet=None, urutan_preset=None):
    pivot_dasar = _hitung_agregat_kategori(df_long)

    if pivot_dasar.empty:
        st.info("Belum ada baris yang dikategorikan untuk produk ini.")
        return []

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
        return []

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
        return []

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

    st.dataframe(tabel_display, use_container_width=True)
            
    # Kembalikan key bulan yang dipilih untuk difilter pada chart
    return bulan_key_terpilih


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
        
        # Render menggunakan Altair untuk kontrol format label X yang akurat
        c = alt.Chart(chart_data_melted).mark_line().encode(
            x=alt.X('tanggal:T', axis=alt.Axis(format='%d %b', title='Tanggal')),
            y=alt.Y('Nilai:Q', title='Jumlah Stock'),
            color=alt.Color('Kategori:N', scale=alt.Scale(range=["#4A90D9", "#E24949"]))
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
        
        # Render menggunakan Altair
        c = alt.Chart(chart_data_melted).mark_line().encode(
            x=alt.X('tanggal:T', axis=alt.Axis(format='%d %b', title='Tanggal')),
            y=alt.Y('Nilai:Q', title='Jumlah Stock'),
            color='Kategori:N'
        ).interactive()
        
        st.altair_chart(c, use_container_width=True)