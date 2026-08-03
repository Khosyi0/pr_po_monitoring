"""
v_summary.py - Executive Summary Dashboard
Halaman khusus presentasi direksi dengan satu tampilan (Single Page), Filter Bulan, dan Tren PR-PO.
Termasuk Editor KPI Bulanan (Khusus Admin) di dalamnya.
"""

import streamlit as st
import pandas as pd
import numpy as np
import calendar
import plotly.graph_objects as go
from zoneinfo import ZoneInfo
from datetime import datetime
from sqlalchemy import text  
from config_db import get_setting, set_setting, get_db_engine  
from utils import format_idr, format_number, format_idr_short, idr_axis, build_sips_bagian_cond

# =============================================================================
# KONSTANTA EDITOR & DATABASE
# =============================================================================
MONTHS_ID = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
ARAH_OPTIONS = [">", ">=", "<", "<=", "="]
ARAH_LABELS = {">": "nilai > target", ">=": "nilai ≥ target", "<": "nilai < target", "<=": "nilai ≤ target", "=": "nilai = target"}
FIELD_LABELS = {"nilai": "Pencapaian", "target": "Target", "free_text": "Keterangan"}

KPI_DEFS = [
    {"key": "KPI_NET_INCOME",      "label": "Net Income",                 "fields": ["nilai", "target", "free_text"]},
    {"key": "KPI_COST_OPT",        "label": "% Cost Optimization",        "fields": ["nilai", "target", "free_text"]},
    {"key": "KPI_PENAGIHAN",       "label": "% Penagihan Despatch",       "fields": ["nilai", "target", "free_text"]},
    {"key": "KPI_PDN",             "label": "% Pembelian PDN",            "fields": ["nilai", "target", "free_text"]},
    {"key": "KPI_TRADING_NPK",     "label": "% Pelaksanaan Trading NPK",  "fields": ["nilai", "target", "free_text"]},
    {"key": "KPI_SLA_PEMBEBASAN",  "label": "% Kecepatan Pembebasan Impor","fields": ["target", "free_text"]},
    {"key": "KPI_OTOBOS",          "label": "Total OTOBOS",               "fields": ["target", "free_text"]},
    {"key": "KPI_ON_SPEC",         "label": "On Spec",                    "fields": ["nilai"]},
    {"key": "KPI_TALENT_DEV",      "label": "% Talent Development",       "fields": ["nilai", "target", "free_text"]},
    {"key": "KPI_ZSO_BB",          "label": "% Zero Stock Out BB",        "fields": ["nilai", "target", "free_text"]},
    {"key": "KPI_ZSO_KANTONG",     "label": "% Zero Stock Out Kantong",   "fields": ["nilai", "target", "free_text"]},
    {"key": "KPI_PRODUKTIVITAS",   "label": "Produktivitas PR-PO",        "fields": ["target", "free_text"]},
    {"key": "KPI_UTILISASI",       "label": "% Utilisasi Single Platform","fields": ["target", "free_text"]},
    {"key": "KPI_SAFETY",          "label": "# Safety Score",             "fields": ["nilai", "target", "free_text"]},
    {"key": "KPI_LAPORAN_KINERJA", "label": "Penyusunan Laporan Kinerja", "fields": ["nilai", "target", "free_text"]},
    {"key": "KPI_IZIN_IMPOR",      "label": "Pemenuhan Izin Impor",       "fields": ["nilai", "target", "free_text"]},
    {"key": "KPI_EFISIENSI_BAGIAN_ALPATA", "label": "Efisiensi (ALPATA)", "fields": ["target"]},
    {"key": "KPI_EFISIENSI_BAGIAN_BARUM",  "label": "Efisiensi (BARUM)",  "fields": ["target"]},
    {"key": "KPI_EFISIENSI_BAGIAN_BBBD",   "label": "Efisiensi (BB/BD/BP)", "fields": ["target"]},
]

DEFAULT_ARAH = {
    "KPI_NET_INCOME": ">=", "KPI_COST_OPT": ">=", "KPI_PENAGIHAN": ">=", "KPI_PDN": ">=", 
    "KPI_TRADING_NPK": ">=", "KPI_SLA_PEMBEBASAN": ">=", "KPI_OTOBOS": ">=", "KPI_ON_SPEC": ">=", 
    "KPI_TALENT_DEV": ">=", "KPI_ZSO_BB": ">=", "KPI_ZSO_KANTONG": ">=", "KPI_PRODUKTIVITAS": ">", 
    "KPI_UTILISASI": ">=", "KPI_SAFETY": ">=", "KPI_LAPORAN_KINERJA": "<", "KPI_IZIN_IMPOR": ">=",
    "KPI_EFISIENSI_BAGIAN_ALPATA": ">", "KPI_EFISIENSI_BAGIAN_BARUM": ">", "KPI_EFISIENSI_BAGIAN_BBBD": ">",
}

# =============================================================================
# FUNGSI DATABASE 
# =============================================================================
def _get_all_kpi_for_range(engine, kpi_keys, date_from, date_to):
    """Ambil data KPI dari database untuk bulan terakhir yang terisi pada rentang tanggal"""
    if not engine or not kpi_keys: return {}
    
    placeholders = ", ".join([f"'{k}'" for k in kpi_keys])
    sql = f"""
        SELECT kpi_key, year, month, field, value
        FROM kpi_monthly_values
        WHERE kpi_key IN ({placeholders})
          AND (year > :dy1 OR (year = :dy2 AND month >= :dm1))
          AND (year < :dy3 OR (year = :dy4 AND month <= :dm2))
        ORDER BY kpi_key, year DESC, month DESC
    """
    params = {
        "dy1": date_from.year, "dy2": date_from.year, "dm1": date_from.month,
        "dy3": date_to.year,   "dy4": date_to.year,   "dm2": date_to.month
    }
    
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).fetchall()

    from collections import defaultdict
    grouped = defaultdict(lambda: defaultdict(dict))
    for kpi_key, year, month, field, value in rows:
        grouped[kpi_key][(year, month)][field] = value

    result = {}
    for kpi_key in kpi_keys:
        ym_dict = grouped.get(kpi_key, {})
        found = {}
        for ym in sorted(ym_dict.keys(), reverse=True):
            fields = ym_dict[ym]
            if any(v.strip() for v in fields.values()):
                found = fields
                break
        result[kpi_key] = found
    return result

def _get_all_monthly_data(engine, kpi_keys, year):
    """Ambil semua data mentah untuk editor tabel (1 tahun)"""
    if not engine or not kpi_keys: return {}
    
    placeholders = ", ".join([f"'{k}'" for k in kpi_keys])
    sql = f"SELECT kpi_key, month, field, value FROM kpi_monthly_values WHERE kpi_key IN ({placeholders}) AND year = :y ORDER BY kpi_key, month"
    
    with engine.connect() as conn:
        rows = conn.execute(text(sql), {"y": year}).fetchall()

    from collections import defaultdict
    result = defaultdict(dict)
    for kpi_key, month, field, value in rows:
        result[(kpi_key, month)][field] = value
    return dict(result)

def _save_kpi_monthly_bulk(engine, kpi_key, year, month, fields):
    sql = """
        INSERT INTO kpi_monthly_values (kpi_key, year, month, field, value, updated_at)
        VALUES (:kpi_key, :year, :month, :field, :value, NOW())
        ON CONFLICT (kpi_key, year, month, field)
        DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
    """
    with engine.begin() as conn:
        for field, value in fields.items():
            conn.execute(text(sql), {
                "kpi_key": kpi_key, 
                "year": year, 
                "month": month, 
                "field": field, 
                "value": str(value)
            })

# =============================================================================
# KOMPONEN EDITOR ADMIN
# =============================================================================
def render_admin_editor(engine, current_year):
    with st.expander("Editor Nilai KPI Bulanan (Admin Area)", expanded=False, icon=":material/edit:"):
        year_options = list(range(current_year - 2, current_year + 2))
        col_year, col_refresh, _ = st.columns([1, 1, 4])
        
        with col_year:
            selected_year = st.selectbox("Pilih Tahun Edit", options=year_options, index=year_options.index(current_year), key="editor_year")
        with col_refresh:
            st.button("Refresh Data", icon=":material/refresh:", key="btn_refresh_editor")

        all_keys = [kpi["key"] for kpi in KPI_DEFS]
        raw_data = _get_all_monthly_data(engine, all_keys, selected_year)

        # Siapkan kolom dan baris untuk Data Editor
        col_headers = ["Bulan"]
        col_meta = []
        for kpi in KPI_DEFS:
            for field in kpi["fields"]:
                # FORMAT BARU: Field | KPI Label
                col_headers.append(f"{FIELD_LABELS.get(field, field)} | {kpi['label']}")
                col_meta.append((kpi["key"], field))

        rows = []
        for m_idx, m_name in enumerate(MONTHS_ID, start=1):
            row = {"Bulan": m_name}
            for (kpi_key, field) in col_meta:
                kpi_label = next(k['label'] for k in KPI_DEFS if k['key'] == kpi_key)
                col_name = f"{FIELD_LABELS.get(field, field)} | {kpi_label}"
                row[col_name] = raw_data.get((kpi_key, m_idx), {}).get(field, "")
            rows.append(row)

        df_edit = pd.DataFrame(rows)

        col_config = {"Bulan": st.column_config.TextColumn("Bulan", disabled=True, width="small")}
        for (kpi_key, field) in col_meta:
            kpi_label = next(k['label'] for k in KPI_DEFS if k['key'] == kpi_key)
            col_name = f"{FIELD_LABELS.get(field, field)} | {kpi_label}"
            col_config[col_name] = st.column_config.TextColumn(col_name, width="medium")

        st.caption("Klik langsung pada tabel untuk mengubah data. Tekan enter, lalu klik simpan di bawah.")
        edited_df = st.data_editor(df_edit, column_config=col_config, use_container_width=True, hide_index=True, key=f"tbl_editor_{selected_year}")

        st.write("**Kondisi Hijau (Arah Perbandingan)** - Berlaku untuk 1 tahun penuh")
        arah_current = {}
        for kpi in KPI_DEFS:
            found_arah = DEFAULT_ARAH.get(kpi["key"], ">=")
            for m in range(1, 13):
                val = raw_data.get((kpi["key"], m), {}).get("arah", "")
                if val:
                    found_arah = val
                    break
            arah_current[kpi["key"]] = found_arah

        arah_new = {}
        kpi_has_arah = [kpi for kpi in KPI_DEFS if "target" in kpi["fields"] or kpi["key"] in DEFAULT_ARAH]
        for i in range(0, len(kpi_has_arah), 3):
            cols = st.columns(3)
            for j, kpi in enumerate(kpi_has_arah[i:i + 3]):
                with cols[j]:
                    cur_arah = arah_current[kpi["key"]]
                    cur_idx = ARAH_OPTIONS.index(cur_arah) if cur_arah in ARAH_OPTIONS else 1
                    arah_new[kpi["key"]] = st.selectbox(kpi["label"], options=ARAH_OPTIONS, index=cur_idx, format_func=lambda x: ARAH_LABELS[x], key=f"arah_{kpi['key']}")

        if st.button("Simpan Semua Perubahan", type="primary", icon=":material/save:", use_container_width=True):
            _proses_simpan_editor(engine, edited_df, col_meta, selected_year, arah_new)

def _proses_simpan_editor(engine, edited_df, col_meta, year, arah_new):
    """Helper untuk memproses klik tombol simpan admin"""
    saved_count = 0
    for m_idx, m_name in enumerate(MONTHS_ID, start=1):
        row = edited_df[edited_df["Bulan"] == m_name].iloc[0]
        kpi_fields = {}
        
        for (kpi_key, field) in col_meta:
            kpi_label = next(k['label'] for k in KPI_DEFS if k['key'] == kpi_key)
            col_name = f"{FIELD_LABELS.get(field, field)} | {kpi_label}"
            val = str(row.get(col_name, "") or "").strip()
            if kpi_key not in kpi_fields: kpi_fields[kpi_key] = {}
            kpi_fields[kpi_key][field] = val

        for kpi_key, fields in kpi_fields.items():
            if arah_new.get(kpi_key): fields["arah"] = arah_new[kpi_key]
            if any(v for v in fields.values() if v and v != arah_new.get(kpi_key, "")):
                _save_kpi_monthly_bulk(engine, kpi_key, year, m_idx, fields)
                saved_count += 1
    
    st.success(f"✅ Berhasil menyimpan {saved_count} update data!")
    st.rerun()

# =============================================================================
# CSS: tampilan kartu KPI yang bersih & print-friendly
# =============================================================================
SUMMARY_CSS = """
<style>
/* == Card KPI & Chart Wrapper ============================================== */
.sum-card, div[data-testid="stPlotlyChart"] {
    border-radius: 12px !important;
    background-color: var(--secondary-background-color) !important;
    background-image: linear-gradient(rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.08)) !important;
    border: 1px solid rgba(128, 128, 128, 0.25) !important;
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08) !important;
    page-break-inside: avoid;
    break-inside: avoid;
}

.sum-card {
    /* Memaksa spesifikasi sisi kiri untuk menimpa aturan border umum di atas */
    border-left-width: 6px !important;
    border-left-style: solid !important;
    border-left-color: var(--text-color) !important;
}

/* Kelas tambahan untuk warna dinamis */
.sum-card.border-green { border-left-color: #09ab3b !important; }
.sum-card.border-red   { border-left-color: #e03c3c !important; }

div[data-testid="stPlotlyChart"] {
    /* Jangan gunakan padding di sini agar iframe tidak overflow! */
    overflow: hidden !important; 
}

/* == Text Colors (Pasti Aman Mengikuti Tema Streamlit) == */
.sum-icon {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    border-radius: 10px;
    background: rgba(128, 128, 128, 0.1) !important;
    color: var(--text-color) !important; /* Warna ikon aman */
}

.sum-card {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    
    /* Hapus height: 145px yang kaku, ganti dengan ini: */
    min-height: 145px !important; 
    height: 100%; 
    
    padding: 20px 18px 16px 18px;
}

.sum-body { 
    flex: 1; 
    min-width: 0; 
}

.sum-label {
    font-size: 12.5px;
    margin: 0 0 6px 0 !important; /* Memaksa jarak judul ke angka hanya 6px */
    line-height: 1.3;
    font-weight: 500;
    color: var(--text-color) !important;
    opacity: 0.75;
}

.sum-value {
    font-size: 2rem !important;
    font-weight: 600 !important;
    margin: 0 0 4px 0 !important; /* Memaksa jarak angka ke Target hanya 4px */
    line-height: 1.1 !important;
    color: var(--text-color) !important;
    white-space: normal !important;
    word-wrap: break-word !important;
    display: block !important;
}

.sum-delta { 
    font-size: 12px; 
    margin: 0; 
    color: var(--text-color) !important;
    opacity: 0.6;
}

/* Warna KPI khusus (Hijau, Merah, Oranye) dipertahankan karena terlihat di kedua mode */
.sum-delta-green { font-size: 12px; color: #09ab3b !important; margin: 0; font-weight: 600; }
.sum-delta-red   { font-size: 12px; color: #e03c3c !important; margin: 0; font-weight: 600; }
.sum-delta-orange{ font-size: 12px; color: #f0a500 !important; margin: 0; font-weight: 600; }

.sum-row-label {
    font-size: 14px; font-weight: 700; letter-spacing: 0.04em;
    text-transform: uppercase; color: var(--text-color); margin: 6px 0 6px 4px;
}

@media screen { .pagebreak { display: none; } }

/* == Print styles =========================================================== */
@media print {
    body { zoom: 0.75 !important; }
    [data-testid="stSidebar"], [data-testid="stSidebarNav"], [data-testid="stToolbar"], footer, header { display: none !important; }
    @page { margin: 1.5cm; size: A4 portrait; }
    .pagebreak { page-break-before: always !important; display: block !important; height: 0; }
    .sum-card, div[data-testid="stPlotlyChart"] {
        page-break-inside: avoid !important; border: 1px solid #ccc !important;
        box-shadow: none !important; background: transparent !important;
    }
    .sum-value, .sum-label, .sum-delta { color: #111 !important; }
    [data-testid="stHorizontalBlock"], div[data-testid="stPlotlyChart"] { break-inside: avoid !important; }
}

/* == Kartu Pendukung OTOBOS (Ukuran Lebih Kecil & Pendek) == */
.sum-card-small {
    padding: 16px 14px 14px 14px !important;
    min-height: 90px !important; 
    height: auto !important; 
}

/* == Kartu Utama Total OTOBOS (Disesuaikan tingginya) == */
.sum-card-otobos-total {
    min-height: 110px !important; 
    height: auto !important;
    padding-bottom: 16px !important;
}

.sum-card-small .sum-label {
    font-size: 11px !important; 
}

.sum-card-small .sum-value {
    font-size: 1.5rem !important; 
    margin: 4px 0 0 0 !important;
}

.sum-card-small .sum-icon {
    width: 40px !important;
    height: 40px !important;
}

.sum-card-small .sum-icon svg {
    width: 24px !important; 
    height: 24px !important;
}

/* == Posisi tombol popover di dalam kartu KPI == */
div[data-testid="stHorizontalBlock"] > div {
    position: relative; /* Membuat setiap kolom menjadi container relatif */
}
div[data-testid="stPopover"] {
    position: absolute;
    top: 10px;
    right: 10px;
    width: 40px;
    z-index: 10;
}
/* Menyembunyikan tombol popover saat di-print */
@media print {
    div[data-testid="stPopover"] {
        display: none !important;
    }
}
</style>
"""

# =============================================================================
# Helpers
# =============================================================================

def _svg(path_d: str, size: int = 40) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'fill="currentColor" viewBox="0 0 16 16"><path d="{path_d}"/></svg>'
    )

def _card(icon_d: str, label: str, value: str,
          delta: str = "", delta_type: str = "neutral", border_class: str = "") -> str:
    delta_cls = {
        "green":  "sum-delta-green",
        "red":    "sum-delta-red",
        "orange": "sum-delta-orange",
    }.get(delta_type, "sum-delta")
    delta_html = f'<p class="{delta_cls}">{delta}</p>' if delta else ""
    return f"""<div class="sum-card {border_class}">
    <div class="sum-icon">{_svg(icon_d, 36)}</div>
    <div class="sum-body">
        <p class="sum-label">{label}</p>
        <p class="sum-value">{value}</p>{delta_html}
    </div>
</div>"""

def _row_label(text: str) -> None:
    st.markdown(f'<div class="sum-row-label">{text}</div>', unsafe_allow_html=True)

def _parse_label_to_num(label: str) -> float | None:
    import re
    s = str(label).strip()
    if not s or s == "-":
        return None

    has_rp  = bool(re.search(r'Rp', s, re.IGNORECASE))
    
    s_clean = s.replace(".", "").replace(",", ".")
    nums = re.findall(r'[\d]+(?:\.[\d]+)?', s_clean)

    if not nums:
        return None

    try:
        num = float(nums[0])
    except ValueError:
        return None

    if has_rp:
        upper = s.upper()
        if re.search(r'\bT\b|TRILIUN', upper):
            num *= 1_000_000_000_000
        elif re.search(r'\bM\b|MILIAR', upper):
            num *= 1_000_000_000
        elif re.search(r'\bJT\b|\bJUTA\b', upper):
            num *= 1_000_000

    return num

def _eval_kpi_color(nilai_label: str, target_label: str, arah: str):
    n = _parse_label_to_num(nilai_label)
    t = _parse_label_to_num(target_label)
    if n is None or t is None:
        return "neutral", ""

    if   arah == ">":  color = "green" if n >  t else "red"
    elif arah == ">=": color = "green" if n >= t else "red"
    elif arah == "<":  color = "green" if n <  t else "red"
    elif arah == "<=": color = "green" if n <= t else "red"
    elif arah == "=":  color = "green" if abs(n - t) / max(abs(t), 1e-9) < 0.00001 else "red"
    else:              return "neutral", ""

    return color, f"border-{color}"

ICONS = {
    "file_text":   "M5 4a.5.5 0 0 0 0 1h6a.5.5 0 0 0 0-1zm-.5 2.5A.5.5 0 0 1 5 6h6a.5.5 0 0 1 0 1H5a.5.5 0 0 1-.5-.5M5 8a.5.5 0 0 0 0 1h6a.5.5 0 0 0 0-1zm0 2a.5.5 0 0 0 0 1h3a.5.5 0 0 0 0-1zM3 0h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2m0 1a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1z",
    "bag":         "M8 1a2.5 2.5 0 0 1 2.5 2.5V4h-5v-.5A2.5 2.5 0 0 1 8 1m3.5 3v-.5a3.5 3.5 0 1 0-7 0V4H1v10a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V4zM2 5h12v9a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1z",
    "percent":     "M13.442 2.558a.625.625 0 0 1 0 .884l-10 10a.625.625 0 1 1-.884-.884l10-10a.625.625 0 0 1 .884 0M4.5 6a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3m0 1a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5m7 6a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3m0 1a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5",
    "house":       "M8.707 1.5a1 1 0 0 0-1.414 0L.646 8.146a.5.5 0 0 0 .708.708L2 8.207V13.5A1.5 1.5 0 0 0 3.5 15h9a1.5 1.5 0 0 0 1.5-1.5V8.207l.646.647a.5.5 0 0 0 .708-.708zM7 14V9h2v5zm3 0V9a1 1 0 0 0-1-1H7a1 1 0 0 0-1 1v5H3.5a.5.5 0 0 1-.5-.5V7.207l5-5 5 5V13.5a.5.5 0 0 1-.5.5z",
    "people":      "M7 14s-1 0-1-1 1-4 5-4 5 3 5 4-1 1-1 1zm4-6a3 3 0 1 0 0-6 3 3 0 0 0 0 6m-5.784 6A2.24 2.24 0 0 1 5 13c0-1.355.68-2.75 1.936-3.72A6.3 6.3 0 0 0 5 9c-4 0-5 3-5 4s1 1 1 1zM4.5 8a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5",
    "clock":       "M8 3.5a.5.5 0 0 0-1 0V9a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0 0 .496-.868L8 8.71zM8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16m7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0",
    "truck":       "M0 3.5A1.5 1.5 0 0 1 1.5 2h9A1.5 1.5 0 0 1 12 3.5V5h1.02a1.5 1.5 0 0 1 1.17.563l1.481 1.85a1.5 1.5 0 0 1 .329.938V10.5a1.5 1.5 0 0 1-1.5 1.5H14a2 2 0 1 1-4 0H5a2 2 0 1 1-3.998-.085A1.5 1.5 0 0 1 0 10.5zm1.294 7.456A2 2 0 0 1 4.732 11h5.536a2 2 0 0 1 .732-.732V3.5a.5.5 0 0 0-.5-.5h-9a.5.5 0 0 0-.5.5v7a.5.5 0 0 0 .294.456M12 10a2 2 0 0 1 1.732 1h.768a.5.5 0 0 0 .5-.5V8.35a.5.5 0 0 0-.11-.312l-1.48-1.85A.5.5 0 0 0 13.02 6H12zm-9 1a1 1 0 1 0 0 2 1 1 0 0 0 0-2m9 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2",
    "check_circle":"M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16M10.97 4.97a.235.235 0 0 0-.02.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-1.071-1.05",
    "search":      "M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001q.044.06.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1 1 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0",
    "refresh":     "M11.534 7h3.932a.25.25 0 0 1 .192.41l-1.966 2.36a.25.25 0 0 1-.384 0l-1.966-2.36a.25.25 0 0 1 .192-.41m-11 2h3.932a.25.25 0 0 0 .192-.41L2.692 6.23a.25.25 0 0 0-.384 0L.342 8.59A.25.25 0 0 0 .534 9 M8 3c-1.552 0-2.94.707-3.857 1.818a.5.5 0 1 1-.771-.636A6.002 6.002 0 0 1 13.917 7H12.9A5 5 0 0 0 8 3M3.1 9a5.002 5.002 0 0 0 8.757 2.182.5.5 0 1 1 .771.636A6.002 6.002 0 0 1 2.083 9z",
    "lock":        "M8 1a2 2 0 0 1 2 2v4H6V3a2 2 0 0 1 2-2m3 6V3a3 3 0 0 0-6 0v4a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2",
    "check_all":   "M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16 M10.97 4.97a.75.75 0 0 1 1.07 1.05l-3.99 4.99a.75.75 0 0 1-1.08.02L4.324 8.384a.75.75 0 1 1 1.06-1.06l2.094 2.093 3.473-4.425z",
    "graph_up":    "M0 0h1v15h15v1H0zm14.817 3.113a.5.5 0 0 1 .07.704l-4.5 5.5a.5.5 0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5 0 0 1 .758-.06l2.609 2.61 4.15-5.073a.5.5 0 0 1 .704-.07",
    "currency":    "M8 10a2 2 0 1 0 0-4 2 2 0 0 0 0 4 M0 4a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H1a1 1 0 0 1-1-1zm3 0a2 2 0 0 1-2 2v4a2 2 0 0 1 2 2h10a2 2 0 0 1 2-2V6a2 2 0 0 1-2-2z",
    "calendar":    "M3.5 0a.5.5 0 0 1 .5.5V1h8V.5a.5.5 0 0 1 1 0V1h1a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2h1V.5a.5.5 0 0 1 .5-.5M1 4v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V4z",
    "bar_chart":   "M1 11a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1zm5-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1zm5-5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1z",
    "box":         "M8.186 1.113a.5.5 0 0 0-.372 0L1.846 3.5 8 5.961 14.154 3.5zM15 4.239l-6.5 2.6v7.922l6.5-2.6V4.24zM7.5 14.762V6.838L1 4.239v7.923zM7.443.184a1.5 1.5 0 0 1 1.114 0l7.129 2.852A.5.5 0 0 1 16 3.5v8.662a1 1 0 0 1-.629.928l-7.185 2.874a.5.5 0 0 1-.372 0L.63 13.09a1 1 0 0 1-.63-.928V3.5a.5.5 0 0 1 .314-.464z",
    "building":    "M4 2.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm3 0a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm3.5-.5a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5v-1a.5.5 0 0 0-.5-.5zM4 5.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zM7.5 5a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5v-1a.5.5 0 0 0-.5-.5zm2.5.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zM4.5 8a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5v-1a.5.5 0 0 0-.5-.5zm2.5.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm3.5-.5a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5v-1a.5.5 0 0 0-.5-.5z M2 1a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1zm11 0H3v14h3v-2.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 .5.5V15h3z"
}

# =============================================================================
# RENDER UTAMA
# =============================================================================

def render(load_data, **kwargs):
    st.markdown(SUMMARY_CSS, unsafe_allow_html=True)

    is_admin = kwargs.get("is_admin", False)
    
    engine = None
    try:
        engine = get_db_engine()
    except Exception as e:
        st.error(f"Gagal terhubung ke database: {e}")

    tz_wib = ZoneInfo("Asia/Jakarta")
    current_year = datetime.now(tz_wib).year

    # == EDITOR KPI ADMIN AREA ================================================
    if is_admin and engine:
        render_admin_editor(engine, current_year)
        st.markdown("---")

    sap_date_str = get_setting("DATA_UPDATE_SAP", "2026-05-31")
    try: DATA_UPDATE_SAP = datetime.strptime(sap_date_str, "%Y-%m-%d").date()
    except: DATA_UPDATE_SAP = datetime(2026, 5, 31).date()

    ink_date_str = get_setting("DATA_UPDATE_INKLARING", "2026-05-31")
    try: DATA_UPDATE_INKLARING = datetime.strptime(ink_date_str, "%Y-%m-%d").date()
    except: DATA_UPDATE_INKLARING = datetime(2026, 5, 31).date()

    sips_date_str = get_setting("DATA_UPDATE_SIPS", "2026-05-31")
    try: DATA_UPDATE_SIPS = datetime.strptime(sips_date_str, "%Y-%m-%d").date()
    except: DATA_UPDATE_SIPS = datetime(2026, 5, 31).date()

    st.markdown("""
        <h1 style='display:flex; align-items:center; font-size:52px; margin-bottom:0;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="42" height="42" fill="currentColor"
                 viewBox="0 0 16 16" style="margin-right:12px; margin-bottom:8px;">
                <path d="M0 0h1v15h15v1H0zm14.817 3.113a.5.5 0 0 1 .07.704l-4.5 5.5a.5.5
                         0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5
                         0 0 1 .758-.06l2.609 2.61 4.15-5.073a.5.5 0 0 1 .704-.07"/>
            </svg>
            Executive Summary
        </h1>
    """, unsafe_allow_html=True)
    st.markdown(
        "<p style='font-size:15px; opacity:0.55; margin-top:0; margin-bottom: 24px;'>"
        "Ringkasan dan Laporan Pengadaan Barang</p>",
        unsafe_allow_html=True
    )

    st.markdown(
        f"<p style='font-size:13px; font-weight:600; margin-bottom:4px; display:flex; align-items:center; gap:6px;'>"
        f"{_svg(ICONS['calendar'], 14)} Filter Periode</p>", 
        unsafe_allow_html=True
    )
    
    tipe_filter = st.radio("Tipe Filter", ["Rentang Bulan", "Triwulanan"], horizontal=True, label_visibility="collapsed")
    months_id = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

    if tipe_filter == "Rentang Bulan":
        # 1. Definisikan opsi tahun dan opsi 12 bulan murni
        year_options = list(range(current_year - 2, current_year + 2))
        months_id = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        
        # Opsi default berdasarkan tanggal update data SAP/SIPS
        default_year_idx = year_options.index(DATA_UPDATE_SIPS.year) if DATA_UPDATE_SIPS.year in year_options else len(year_options) - 1
        default_start_month_idx = 0  # Januari
        default_end_month_idx = DATA_UPDATE_SIPS.month - 1  # Bulan dari DATA_UPDATE_SIPS
        
        # 2. Bagi menjadi 3 kolom: Tahun, Pilihan Bulan Dari, Pilihan Bulan Sampai
        col_year_select, col_start, col_end, _ = st.columns([1, 1.2, 1.2, 1.6])
        
        with col_year_select:
            selected_year = st.selectbox("Tahun", options=year_options, index=default_year_idx, key="summary_select_year")
        with col_start:
            start_month_pure = st.selectbox("Bulan Dari", options=months_id, index=default_start_month_idx, key="summary_select_start_m")
        with col_end:
            end_month_pure = st.selectbox("Bulan Sampai", options=months_id, index=default_end_month_idx, key="summary_select_end_m")

        # 3. Konversi pilihan ke objek date untuk query database
        start_m_idx = months_id.index(start_month_pure) + 1
        date_from = datetime(selected_year, start_m_idx, 1).date()

        end_m_idx = months_id.index(end_month_pure) + 1
        last_day = calendar.monthrange(selected_year, end_m_idx)[1]
        date_to = datetime(selected_year, end_m_idx, last_day).date()
    else:
        opsi_triwulan = ["TW I (Jan - Mar)", "TW II (Apr - Jun)", "TW III (Jul - Sep)", "TW IV (Okt - Des)"]
        opsi_tahun = list(range(current_year - 2, current_year + 2))
        
        m = DATA_UPDATE_SIPS.month
        if m <= 3: def_q = 0
        elif m <= 6: def_q = 1
        elif m <= 9: def_q = 2
        else: def_q = 3

        col_tri, col_tahun, _ = st.columns([1.2, 0.8, 3])
        with col_tri:
            pilihan_q = st.selectbox("Pilih Triwulan", options=opsi_triwulan, index=def_q, label_visibility="collapsed")
        with col_tahun:
            pilihan_t = st.selectbox("Pilih Tahun", options=opsi_tahun, index=opsi_tahun.index(DATA_UPDATE_SIPS.year), label_visibility="collapsed")

        if pilihan_q == "TW I (Jan - Mar)":
            date_from = datetime(pilihan_t, 1, 1).date()
            date_to = datetime(pilihan_t, 3, 31).date()
        elif pilihan_q == "TW II (Apr - Jun)":
            date_from = datetime(pilihan_t, 4, 1).date()
            date_to = datetime(pilihan_t, 6, 30).date()
        elif pilihan_q == "TW III (Jul - Sep)":
            date_from = datetime(pilihan_t, 7, 1).date()
            date_to = datetime(pilihan_t, 9, 30).date()
        else:
            date_from = datetime(pilihan_t, 10, 1).date()
            date_to = datetime(pilihan_t, 12, 31).date()

    st.markdown(
        f"<p style='font-size:16px; margin-top:6px;'>"
        f"Data SIPS per {DATA_UPDATE_SIPS.strftime('%d %B %Y')} "
        f"&nbsp;|&nbsp; Dicetak: {datetime.now(tz_wib).strftime('%d %B %Y %H:%M')}</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    dt_from_pd = pd.to_datetime(date_from).replace(day=1)
    dt_to_pd   = pd.to_datetime(date_to).replace(day=1) 

    # =========================================================================
    # AMBIL DATA KPI BULANAN DARI DATABASE (Cache 1x Query)
    # =========================================================================
    all_kpi_keys = [k["key"] for k in KPI_DEFS]
    kpi_monthly_cache = {}
    if engine:
        try:
            kpi_monthly_cache = _get_all_kpi_for_range(engine, all_kpi_keys, date_from, date_to)
        except Exception as e:
            st.warning(f"⚠️ Gagal memuat data KPI bulanan: {e}")

    # =========================================================================
    # DEFINISI LOGIKA FILTER SIPS 
    # =========================================================================
    where_pr = f"tgl_disposisi_buyer >= '{date_from}' AND tgl_disposisi_buyer <= '{date_to}'"
    po_date_cond = f"""(
        tgl_po >= '{date_from}'::date AND tgl_po <= '{date_to}'::date
    )"""
    where_gabungan = f"(({where_pr}) OR ({po_date_cond} AND UPPER(TRIM(status)) IN ('CLOSED','PROSES PO')))"

    # == Eksekusi Kueri =======================================================
    trend_query = f"""
    WITH pr_bulanan AS (
        SELECT DATE_TRUNC('month', tgl_disposisi_buyer)::date AS month, COUNT(*) AS total_pr
        FROM vw_sips WHERE {where_pr} GROUP BY 1
    ),
    po_bulanan AS (
        SELECT DATE_TRUNC('month', COALESCE(tgl_po, tgl_disposisi_buyer))::date AS month, COUNT(*) AS total_po
        FROM vw_sips WHERE UPPER(TRIM(status)) IN ('CLOSED','PROSES PO') AND {po_date_cond} GROUP BY 1
    )
    SELECT TO_CHAR(COALESCE(pr_bulanan.month, po_bulanan.month), 'YYYY-MM-01')::date AS month,
           COALESCE(pr_bulanan.total_pr, 0) AS total_pr, COALESCE(po_bulanan.total_po, 0) AS total_po
    FROM pr_bulanan FULL OUTER JOIN po_bulanan ON pr_bulanan.month = po_bulanan.month ORDER BY 1
    """

    value_trend_query = f"""
    SELECT TO_CHAR(DATE_TRUNC('month', COALESCE(tgl_po, tgl_disposisi_buyer)), 'YYYY-MM-01')::date AS month,
           SUM(CASE WHEN UPPER(TRIM(status)) IN ('CLOSED', 'PROSES PO') THEN oe_pr ELSE 0 END) AS total_oe,
           SUM(CASE WHEN UPPER(TRIM(status)) IN ('CLOSED', 'PROSES PO') THEN nilai_item_po ELSE 0 END) AS total_po_val
    FROM vw_sips WHERE UPPER(TRIM(status)) IN ('CLOSED', 'PROSES PO') AND {po_date_cond} GROUP BY 1 ORDER BY 1
    """

    sips_otobos_query = f"""
    SELECT
        SUM(CASE WHEN {where_pr} THEN 1 ELSE 0 END) AS total_pr,
        SUM(CASE WHEN UPPER(TRIM(status)) IN ('CLOSED','PROSES PO') AND {po_date_cond} THEN 1 ELSE 0 END) AS total_po,
        ROUND(AVG(CASE WHEN UPPER(TRIM(status)) IN ('CLOSED', 'PROSES PO') AND {po_date_cond} THEN pr_po_days END)::numeric, 2) AS avg_pr_po,
        COALESCE(SUM(CASE WHEN UPPER(TRIM(status)) IN ('CLOSED','PROSES PO') AND {po_date_cond} THEN nilai_sla END), 0) AS sla_ontime,
        SUM(CASE WHEN persen_po_sr_mr <= 1.0 AND UPPER(TRIM(status)) IN ('CLOSED','PROSES PO') AND {po_date_cond} THEN 1 ELSE 0 END) AS on_budget_count,
        COALESCE(SUM(CASE WHEN UPPER(TRIM(status)) IN ('CLOSED', 'PROSES PO') AND {po_date_cond} AND (outline_agreement IS NULL OR TRIM(outline_agreement) = '') THEN oe_pr END), 0) AS sips_oe_total,
        COALESCE(SUM(CASE WHEN UPPER(TRIM(status)) IN ('CLOSED', 'PROSES PO') AND {po_date_cond} AND (outline_agreement IS NULL OR TRIM(outline_agreement) = '') THEN nilai_item_po END), 0) AS sips_po_total,
        COALESCE(SUM(CASE WHEN UPPER(TRIM(status)) IN ('CLOSED', 'PROSES PO') AND {po_date_cond} AND (outline_agreement IS NULL OR TRIM(outline_agreement) = '') THEN oe_pr END), 0) AS sips_oe_na,
        COALESCE(SUM(CASE WHEN UPPER(TRIM(status)) IN ('CLOSED', 'PROSES PO') AND {po_date_cond} AND (outline_agreement IS NULL OR TRIM(outline_agreement) = '') THEN nilai_item_po END), 0) AS sips_po_na
    FROM vw_sips WHERE {where_gabungan}
    """

    sap_kpi_query = f"""
    SELECT
        COUNT(poi.nomor_po) AS total_po,
        COUNT(CASE WHEN poi.status_pengiriman = 'SELESAI' THEN 1 END) AS po_delivered,
        COUNT(CASE WHEN poi.on_time_delivery = 'TEPAT WAKTU' THEN 1 END) AS po_ontime,
        COUNT(CASE WHEN poi.on_time_delivery IN ('TEPAT WAKTU','TERLAMBAT') THEN 1 END) AS po_delivered_total,
        COALESCE(SUM(CASE WHEN poh.vendor_code IN ('4000000011', '4000000012') THEN poi.total_amount_local_curr ELSE 0 END), 0) AS total_sinergi_pi
    FROM po_items poi JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
    WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
    """

    eproc_kpi_query = f"""
    SELECT COUNT(*) AS total_dokumen, SUM(CASE WHEN LOWER(TRIM(metode)) = 'eproc' THEN 1 ELSE 0 END) AS total_eproc
    FROM data_eproc WHERE tgl_dokumen >= '{date_from}' AND tgl_dokumen <= '{date_to}'
    """

    eproc_emp_query = f"""
    SELECT UPPER(TRIM(pic)) AS nama_join, COUNT(*) AS total_dokumen_eproc, SUM(CASE WHEN LOWER(TRIM(metode)) = 'eproc' THEN 1 ELSE 0 END) AS total_eproc_method
    FROM data_eproc WHERE tgl_dokumen >= '{date_from}' AND tgl_dokumen <= '{date_to}' GROUP BY UPPER(TRIM(pic))
    """

    inklaring_query = f"""
    SELECT komoditi, start_bongkar, selesai_bongkar, spjm, tgl_sppb
    FROM inklaring_impor
    WHERE tgl_eta >= '{date_from}' AND tgl_eta <= '{date_to}'
    """

    with st.spinner("Memuat data laporan..."):
        try:
            trend_data = load_data(trend_query)
            val_trend_data = load_data(value_trend_query)
            sips_otobos_data = load_data(sips_otobos_query)
            sap_kpi_data = load_data(sap_kpi_query)
            eproc_kpi_data = load_data(eproc_kpi_query)
            eproc_emp_data = load_data(eproc_emp_query)
            inklaring_data = load_data(inklaring_query)
        except Exception as e:
            st.error(f"Gagal memuat data: {e}")
            return

    # Proses tanggal untuk chart
    today = datetime.now(tz_wib).date()
    def resolve_month_date(month_ts):
        y, m = month_ts.year, month_ts.month
        cy, cm = today.year, today.month
        if (y, m) == (cy, cm): return pd.Timestamp(today)
        elif (y, m) < (cy, cm): return pd.Timestamp(y, m, calendar.monthrange(y, m)[1])
        else: return month_ts

    def fmt_date(ts): return f"{ts.day} {ts.strftime('%b')} {ts.year}"

    if not trend_data.empty:
        trend_data['month'] = pd.to_datetime(trend_data['month']).dt.tz_localize(None)
        trend_data = trend_data.sort_values('month')
        trend_data['cum_pr'] = trend_data['total_pr'].cumsum()
        trend_data['cum_po'] = trend_data['total_po'].cumsum()
        trend_data = trend_data[(trend_data['month'] >= dt_from_pd) & (trend_data['month'] <= dt_to_pd)]
        trend_data['month_display'] = trend_data['month'].apply(resolve_month_date)
        trend_data['hover_label'] = trend_data['month_display'].apply(fmt_date)

    if not val_trend_data.empty:
        val_trend_data['month'] = pd.to_datetime(val_trend_data['month']).dt.tz_localize(None)
        val_trend_data = val_trend_data.sort_values('month')
        val_trend_data['cum_oe'] = val_trend_data['total_oe'].cumsum()
        val_trend_data['cum_po'] = val_trend_data['total_po_val'].cumsum()
        val_trend_data = val_trend_data[(val_trend_data['month'] >= dt_from_pd) & (val_trend_data['month'] <= dt_to_pd)]
        val_trend_data['month_display'] = val_trend_data['month'].apply(resolve_month_date)
        val_trend_data['hover_label'] = val_trend_data['month_display'].apply(fmt_date)
        val_trend_data['oe_fmt'] = val_trend_data['total_oe'].apply(format_idr)
        val_trend_data['po_fmt'] = val_trend_data['total_po_val'].apply(format_idr)
        val_trend_data['cum_oe_fmt'] = val_trend_data['cum_oe'].apply(format_idr)
        val_trend_data['cum_po_fmt'] = val_trend_data['cum_po'].apply(format_idr)

    if not sips_otobos_data.empty:
        s_po = int(sips_otobos_data['total_po'][0] or 0)
        s_ontime = float(sips_otobos_data['sla_ontime'][0] or 0)
        s_onbudget = int(sips_otobos_data['on_budget_count'][0] or 0)
        sla_on_time_pct = (s_ontime / s_po * 100) if s_po > 0 else 0.0
        sla_on_budget_pct = (s_onbudget / s_po * 100) if s_po > 0 else 0.0
        sips_total_pr = int(sips_otobos_data['total_pr'][0] or 0)
        sips_total_po = s_po
        sips_pr_without = sips_total_pr - sips_total_po
        sips_pct_pr_po = (sips_total_po / sips_total_pr * 100) if sips_total_pr > 0 else 0.0
        sips_avg_lt = float(sips_otobos_data['avg_pr_po'][0] or 0)
        sips_oe_total = float(sips_otobos_data['sips_oe_total'][0] or 0)
        sips_po_total = float(sips_otobos_data['sips_po_total'][0] or 0)
        sips_oe_na = float(sips_otobos_data['sips_oe_na'][0] or 0)
        sips_po_na = float(sips_otobos_data['sips_po_na'][0] or 0)
        sips_savings = sips_oe_na - sips_po_na
        sips_savings_pct = (sips_savings / sips_oe_na * 100) if sips_oe_na > 0 else 0.0
    else:
        sla_on_time_pct = sla_on_budget_pct = sips_total_pr = sips_total_po = sips_pr_without = sips_pct_pr_po = sips_avg_lt = sips_oe_total = sips_po_total = sips_savings = sips_savings_pct = 0.0

    if not sap_kpi_data.empty:
        sap_total_po = int(sap_kpi_data['total_po'][0] or 0)
        sap_po_delivered = int(sap_kpi_data['po_delivered'][0] or 0)
        sap_po_ontime = int(sap_kpi_data['po_ontime'][0] or 0)
        sap_po_del_tot = int(sap_kpi_data['po_delivered_total'][0] or 0)
        sap_sinergi_pi_val = float(sap_kpi_data['total_sinergi_pi'][0] or 0)
        sap_pct_pengiriman = (sap_po_delivered / sap_total_po * 100) if sap_total_po > 0 else 0.0
        sap_ketepatan_pct = (sap_po_ontime / sap_po_del_tot * 100) if sap_po_del_tot > 0 else 0.0
    else:
        sap_pct_pengiriman = sap_ketepatan_pct = sap_sinergi_pi_val = 0.0

    # =========================================================================
    # KALKULASI KPI INKLARING / PEMBEBASAN IMPOR (SLA EPP)
    # =========================================================================
    persen_sla_epp = 0.0
    if 'inklaring_data' in locals() and not inklaring_data.empty:
        df_ink = inklaring_data.copy()
        df_ink['selesai_bongkar'] = pd.to_datetime(df_ink['selesai_bongkar'], errors='coerce')
        df_ink['tgl_sppb'] = pd.to_datetime(df_ink['tgl_sppb'], errors='coerce')

        df_ink['Bebas_Hari'] = (df_ink['tgl_sppb'] - df_ink['selesai_bongkar'].dt.normalize()).dt.days
        is_hijau_mask = df_ink['spjm'].fillna('').astype(str).str.strip().isin(['', '0', '0.0'])
        df_ink['Keterangan_Jalur'] = np.where(is_hijau_mask, 'HIJAU', 'MERAH')

        df_ink['SLA_Target'] = np.where(df_ink['komoditi'] == 'SA', 15, 
                                      np.where(df_ink['Keterangan_Jalur'] == 'MERAH', 8, 0))

        df_ink['Score_SLA'] = np.where(
            df_ink['Bebas_Hari'].isna() | (df_ink['Bebas_Hari'] == 0), 
            0, 
            np.where(df_ink['SLA_Target'] >= df_ink['Bebas_Hari'], 1, 0)
        )

        total_data_ink = len(df_ink)
        total_score_1_ink = (df_ink['Score_SLA'] == 1).sum()
        persen_sla_epp = (total_score_1_ink / total_data_ink) * 100 if total_data_ink > 0 else 0.0

    _ARAH_SYM = {">": ">", ">=": "≥", "<": "<", "<=": "≤", "=": "="}

    # =========================================================================
    # KONEKSI KPI KE DATABASE
    # =========================================================================
    
    # Fungsi utama untuk menembak ke cache DB bulanan / fallback dengan AUTO FORMAT
    def _load_kpi(prefix: str, default_arah: str = ">="):
        monthly = kpi_monthly_cache.get(prefix, {})
        
        nilai     = (monthly.get("nilai", "") or get_setting(f"{prefix}_NILAI", "-")).strip() or "-"
        target    = (monthly.get("target", "") or get_setting(f"{prefix}_TARGET", "-")).strip() or "-"
        arah      = (monthly.get("arah", "") or get_setting(f"{prefix}_ARAH", default_arah)).strip() or default_arah
        free_text = (monthly.get("free_text", "") or get_setting(f"{prefix}_FREE_TEXT", "")).strip()

        # --- AUTO FORMATTER UNTUK ANGKA MENTAH ---
        def auto_format(val, kpi_type):
            if val == "-" or not val: return val
            # Jika user sudah ngetik Rp, %, M, T, atau ada spasi/garis miring, biarkan (berarti sudah diformat manual)
            if any(c.isalpha() or c in ['%', '/'] for c in val.replace(" ", "")): 
                return val
            
            try:
                # Ubah teks angka murni jadi float
                num = float(val.replace(",", "."))
                
                # Format ke Rupiah Singkat (Miliar / Triliun)
                if kpi_type == "KPI_NET_INCOME":
                    if num >= 1_000_000_000_000:
                        return f"Rp {num/1_000_000_000_000:,.2f} T".replace(",", "X").replace(".", ",").replace("X", ".")
                    elif num >= 1_000_000_000:
                        return f"Rp {num/1_000_000_000:,.2f} M".replace(",", "X").replace(".", ",").replace("X", ".")
                    else:
                        return f"Rp {num:,.0f}".replace(",", ".")
                        
                # Format ke Persentase
                elif kpi_type in ["KPI_COST_OPT", "KPI_PENAGIHAN", "KPI_PDN", "KPI_TRADING_NPK", "KPI_ZSO_BB", "KPI_ZSO_KANTONG", "KPI_TALENT_DEV", "KPI_SLA_PEMBEBASAN", "KPI_PRODUKTIVITAS", "KPI_UTILISASI"]:
                    return f"{num:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")
                
                else:
                    return val
            except ValueError:
                return val

        # Terapkan auto-format sebelum dilempar ke UI
        nilai_tampil = auto_format(nilai, prefix)
        target_tampil = auto_format(target, prefix)
        # -----------------------------------------

        color, border = _eval_kpi_color(nilai_tampil, target_tampil, arah)
        sym   = _ARAH_SYM.get(arah, "")
        delta = f"Target: {sym} {target_tampil}".strip() if target_tampil != "-" else "Target: -"
        if free_text:
            delta = f"{delta} | {free_text}"
        return nilai_tampil, target_tampil, arah, color, border, delta

    # 1. On Spec
    _onspec_monthly = kpi_monthly_cache.get("KPI_ON_SPEC", {})
    _on_spec_override = _onspec_monthly.get("nilai", "") or get_setting("KPI_ON_SPEC_NILAI", "")
    sla_on_spec_pct = 99.30
    if _on_spec_override:
        try:
            _clean_val = _on_spec_override.replace("%", "").strip().replace(",", ".")
            sla_on_spec_pct = float(_clean_val)
        except ValueError:
            pass

    # 2. Total OTOBOS
    otobos_val = (sla_on_time_pct + sla_on_budget_pct + sla_on_spec_pct) / 3
    color_otobos = "green" if otobos_val >= 90 else "red"
    _otobos_monthly   = kpi_monthly_cache.get("KPI_OTOBOS", {})
    _otobos_ft = _otobos_monthly.get("free_text", "") or get_setting("KPI_OTOBOS_FREE_TEXT", "")
    _otobos_tgt = _otobos_monthly.get("target", "") or get_setting("KPI_OTOBOS_TARGET", "90%")
    _otobos_arah = _otobos_monthly.get("arah", "") or get_setting("KPI_OTOBOS_ARAH", ">=")
    _otobos_sym  = _ARAH_SYM.get(_otobos_arah, "≥")
    
    # Format the target if it's raw
    def auto_format_target(val):
        if val == "-" or not val: return val
        if any(c.isalpha() or c in ['%', '/'] for c in val.replace(" ", "")): return val
        try: return f"{float(val.replace(',', '.')):,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")
        except: return val

    otobos_delta = f"Target: {_otobos_sym} {auto_format_target(_otobos_tgt)}"
    if _otobos_ft: otobos_delta = f"{otobos_delta} | {_otobos_ft}"

    # 3. Produktivitas
    _prod_monthly   = kpi_monthly_cache.get("KPI_PRODUKTIVITAS", {})
    _prod_target    = _prod_monthly.get("target", "") or get_setting("KPI_PRODUKTIVITAS_TARGET", "90%")
    _prod_arah      = _prod_monthly.get("arah", "") or get_setting("KPI_PRODUKTIVITAS_ARAH", ">")
    _prod_free_text = _prod_monthly.get("free_text", "") or get_setting("KPI_PRODUKTIVITAS_FREE_TEXT", "")
    _prod_color, _  = _eval_kpi_color(f"{sips_pct_pr_po:.2f}%", _prod_target, _prod_arah)
    color_produktivitas = _prod_color if _prod_color in ("green", "red") else ("green" if sips_pct_pr_po > 90 else "red")
    _prod_sym = _ARAH_SYM.get(_prod_arah, ">")
    
    _prod_target_fmt = auto_format_target(_prod_target)
    produktivitas_delta = f"Target: {_prod_sym} {_prod_target_fmt}".strip() if _prod_target_fmt and _prod_target_fmt != "-" else "Target: -"
    if _prod_free_text: produktivitas_delta = f"{produktivitas_delta} | {_prod_free_text}"
    st.session_state["_aktual_KPI_PRODUKTIVITAS"] = sips_pct_pr_po

    # 4. Kecepatan Pembebasan
    _pem_monthly   = kpi_monthly_cache.get("KPI_SLA_PEMBEBASAN", {})
    _pem_target    = _pem_monthly.get("target", "") or get_setting("KPI_SLA_PEMBEBASAN_TARGET", "80%")
    _pem_arah      = _pem_monthly.get("arah", "") or get_setting("KPI_SLA_PEMBEBASAN_ARAH", ">=")
    _pem_free_text = _pem_monthly.get("free_text", "") or get_setting("KPI_SLA_PEMBEBASAN_FREE_TEXT", "")
    _pem_color, _  = _eval_kpi_color(f"{persen_sla_epp:.2f}%", _pem_target, _pem_arah)
    pembebasan_color_db = _pem_color if _pem_color in ("green", "red") else ("green" if persen_sla_epp >= 80 else "red")
    _pem_sym = _ARAH_SYM.get(_pem_arah, "≥")
    
    _pem_target_fmt = auto_format_target(_pem_target)
    sla_pembebasan_delta = f"Target: {_pem_sym} {_pem_target_fmt}".strip()
    if _pem_free_text: sla_pembebasan_delta = f"{sla_pembebasan_delta} | {_pem_free_text}"
    st.session_state["_aktual_KPI_SLA_PEMBEBASAN"] = sla_on_time_pct

    # 5. Izin Impor
    _izin_monthly    = kpi_monthly_cache.get("KPI_IZIN_IMPOR", {})
    izin_impor_nilai = (_izin_monthly.get("nilai", "") or get_setting("KPI_IZIN_IMPOR_NILAI", "100%")).strip() or "100%"
    _izin_tgt        = _izin_monthly.get("target", "") or get_setting("KPI_IZIN_IMPOR_TARGET", "2 / 2")
    _izin_ft         = _izin_monthly.get("free_text", "") or get_setting("KPI_IZIN_IMPOR_FREE_TEXT", "")
    _izin_legacy_delta = get_setting("KPI_IZIN_IMPOR_DELTA", "Target: 2 / 2")
    izin_impor_delta = f"Target: {_izin_tgt}" if _izin_tgt and _izin_tgt != "-" else _izin_legacy_delta
    if _izin_ft: izin_impor_delta = f"{izin_impor_delta} | {_izin_ft}"

    # 6. Efisiensi Pengadaan Global (Tidak masuk tabel DB bulanan)
    efisiensi_pengadaan_delta = get_setting("KPI_EFISIENSI_PENGADAAN_DELTA", "Target: > 2%")
    _efisiensi_free_text = get_setting("KPI_EFISIENSI_PENGADAAN_FREE_TEXT", "")
    if _efisiensi_free_text: efisiensi_pengadaan_delta = f"{efisiensi_pengadaan_delta} | {_efisiensi_free_text}"

    # 7. Eksekusi standard _load_kpi
    ni_nilai,   ni_target,   ni_arah,   ni_color,   ni_border,   ni_delta   = _load_kpi("KPI_NET_INCOME")
    co_nilai,   co_target,   co_arah,   co_color,   co_border,   co_delta   = _load_kpi("KPI_COST_OPT")
    pd_nilai,   pd_target,   pd_arah,   pd_color,   pd_border,   pd_delta   = _load_kpi("KPI_PENAGIHAN")
    pdn_nilai,  pdn_target,  pdn_arah,  pdn_color,  pdn_border,  pdn_delta  = _load_kpi("KPI_PDN")
    npk_nilai,  npk_target,  npk_arah,  npk_color,  npk_border,  npk_delta  = _load_kpi("KPI_TRADING_NPK")
    zbb_nilai,  zbb_target,  zbb_arah,  zbb_color,  zbb_border,  zbb_delta  = _load_kpi("KPI_ZSO_BB", default_arah=">=")
    zkn_nilai,  zkn_target,  zkn_arah,  zkn_color,  zkn_border,  zkn_delta  = _load_kpi("KPI_ZSO_KANTONG", default_arah=">=")
    usp_nilai,  usp_target,  usp_arah,  usp_color,  usp_border,  usp_delta  = _load_kpi("KPI_UTILISASI")
    saf_nilai,  saf_target,  saf_arah,  saf_color,  saf_border,  saf_delta  = _load_kpi("KPI_SAFETY", default_arah=">=")
    tde_nilai,  tde_target,  tde_arah,  tde_color,  tde_border,  tde_delta  = _load_kpi("KPI_TALENT_DEV")
    laporan_kinerja_nilai, laporan_kinerja_target, laporan_kinerja_arah, laporan_kinerja_color, laporan_kinerja_border, laporan_kinerja_delta = _load_kpi("KPI_LAPORAN_KINERJA", default_arah="<")

    # Override Utilisasi Single Platform jika ada data DB asli EPROC
    if not eproc_kpi_data.empty and pd.notna(eproc_kpi_data['total_dokumen'][0]) and eproc_kpi_data['total_dokumen'][0] > 0:
        tot_dok = float(eproc_kpi_data['total_dokumen'][0])
        tot_epr = float(eproc_kpi_data['total_eproc'][0])
        util_pct = (tot_epr / tot_dok) * 100
        usp_nilai = f"{format_number(util_pct, decimals=2)}%"
        usp_color, usp_border = _eval_kpi_color(usp_nilai, usp_target, usp_arah)

    # 8. Mappings Warna lainnya
    color_kecepatan = "green" if sips_avg_lt <= 55 else "red"
    color_efisiensi_pengadaan = "green" if sips_savings_pct > 2 else "red"
    color_pengiriman = "green" if sap_pct_pengiriman > 80 else "red"
    color_ketepatan = "green" if sap_ketepatan_pct > 90 else "red"
    border_class_map = {"green": "border-green", "red": "border-red"}

    # =========================================================================
    # DIALOG EDIT (FALLBACK) - Dibiarkan fungsinya agar Laporan Bagian (Bagian 3) tidak error
    # =========================================================================
    def _dialog_full(title: str, prefix: str, default_arah: str = ">="):
        @st.dialog(f"Edit Fallback KPI: {title}")
        def _dlg():
            st.markdown("<p style='font-size:13px; opacity:0.6; margin-bottom:16px;'>⚠️ Edit di sini hanya mengubah nilai <b>legacy (get_setting)</b>. Untuk mengubah per-bulan, gunakan halaman <b>Editor KPI Bulanan</b>.</p>", unsafe_allow_html=True)
            inp_nilai = st.text_input("Nilai Pencapaian", value=get_setting(f"{prefix}_NILAI", "-"))
            inp_target = st.text_input("Target", value=get_setting(f"{prefix}_TARGET", "-"))
            _cur_arah = get_setting(f"{prefix}_ARAH", default_arah)
            _cur_idx  = ARAH_OPTIONS.index(_cur_arah) if _cur_arah in ARAH_OPTIONS else 1
            inp_arah = st.radio("Kondisi hijau", options=ARAH_OPTIONS, index=_cur_idx, format_func=lambda x: ARAH_LABELS[x])
            inp_free_text = st.text_input("Free Text (opsional)", value=get_setting(f"{prefix}_FREE_TEXT", ""))
            col_s, col_c = st.columns(2)
            with col_s:
                if st.button("Simpan", type="primary", use_container_width=True):
                    set_setting(f"{prefix}_NILAI",  inp_nilai.strip()  or "-")
                    set_setting(f"{prefix}_TARGET", inp_target.strip() or "-")
                    set_setting(f"{prefix}_ARAH",   inp_arah)
                    set_setting(f"{prefix}_FREE_TEXT", inp_free_text.strip())
                    st.rerun()
            with col_c:
                if st.button("Batal", use_container_width=True): st.rerun()
        return _dlg

    def _dialog_efisiensi_bagian(bagian_label: str, prefix: str):
        @st.dialog(f"Edit Target Efisiensi: {bagian_label}")
        def _dlg():
            inp_target = st.text_input("Target (%)", value=get_setting(f"{prefix}_TARGET", ""))
            _cur_arah = get_setting(f"{prefix}_ARAH", ">")
            _cur_idx  = ARAH_OPTIONS.index(_cur_arah) if _cur_arah in ARAH_OPTIONS else 0
            inp_arah = st.radio("Kondisi hijau", options=ARAH_OPTIONS, index=_cur_idx, format_func=lambda x: ARAH_LABELS[x])
            col_s, col_c = st.columns(2)
            with col_s:
                if st.button("Simpan", type="primary", use_container_width=True):
                    set_setting(f"{prefix}_TARGET", inp_target.strip() or "-")
                    set_setting(f"{prefix}_ARAH",   inp_arah)
                    st.rerun()
            with col_c:
                if st.button("Batal", use_container_width=True): st.rerun()
        return _dlg

    dlg_utilisasi = _dialog_full("% Utilisasi Single Platform Pengadaan", "KPI_UTILISASI")

    # =========================================================================
    # RENDER BAGIAN 1: KPI PENGADAAN BARANG (SIPS)
    # Catatan: Semua Tombol Edit telah dihapus dari antarmuka ini sesuai instruksi.
    # =========================================================================
    st.markdown(
        f"<h2 style='display:flex; align-items:center; font-size:32px; margin: 0 0 4px 0; font-weight:700; color:var(--text-color);'>"
        f"<span style='margin-right:12px; transform: translateY(4px); display:inline-flex; align-items:center;'>{_svg(ICONS['graph_up'], 32)}</span>"
        f"KPI Pengadaan Barang"
        f"</h2>"
        f"<p style='font-size:15px; font-weight:500; opacity:0.75; margin: 0 0 16px 0;'>"
        f"Periode: <b>{date_from.strftime('%d %B %Y')} s.d. {date_to.strftime('%d %B %Y')}</b></p>", 
        unsafe_allow_html=True
    )

    # ── Baris 1: Financial ────────────────────────────────────────────────
    _row_label("Financial")
    c1, c2, c3 = st.columns(3)
    with c1: 
        st.markdown(_card(ICONS["currency"], "Net Income", ni_nilai, ni_delta, ni_color, border_class=ni_border), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Keterangan"):
            st.info("**Net Income**\n\Surat dari SDM")
    with c2: 
        st.markdown(_card(ICONS["graph_up"], "% Cost Optimization", co_nilai, co_delta, co_color, border_class=co_border), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Keterangan"):
            st.info("**% Cost Optimization**\n\nSurat dari SDM")
    with c3: 
        st.markdown(_card(ICONS["truck"], "% Penagihan Despatch", pd_nilai, pd_delta, pd_color, border_class=pd_border), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Keterangan"):
            st.info("**% Penagihan Despatch**\n\nKonfirmasi BB")
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── Baris 2: Customer ─────────────────────────────────────────────────
    _row_label("Customer")
    c4, c5, c6 = st.columns(3)
    with c4: 
        st.markdown(_card(ICONS["house"], "% Pembelian PDN terhadap Total Pengadaan", pdn_nilai, pdn_delta, pdn_color, border_class=pdn_border), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Keterangan"):
            st.info("**% Pembelian PDN**\n\nLaporan Kompartemen ManLog")
    with c5: 
        st.markdown(_card(ICONS["refresh"], "% Pelaksanaan Trading Pupuk NPK", npk_nilai, npk_delta, npk_color, border_class=npk_border), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Keterangan"):
            st.info("**% Trading NPK**\n\n-")
    with c6:
        pembebasan_val = f"{format_number(persen_sla_epp, decimals=2)}%"
        pembebasan_border = border_class_map.get(pembebasan_color_db, "")
        st.markdown(_card(ICONS["clock"], "% Kecepatan Pembebasan Barang Impor", pembebasan_val, sla_pembebasan_delta, pembebasan_color_db, border_class=pembebasan_border), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Keterangan"):
            st.info("**% Kecepatan Pembebasan Impor**\n\nPersentase barang impor yang berhasil dibebaskan (SPPB) sesuai target SLA.")
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── Baris 3: % OTOBOS Barang ──────────────────────────────────────────
    _row_label("% OTOBOS Barang")
    c7, c8, c9, c10 = st.columns([2, 1, 1, 1])
    with c7:
        border_cls = border_class_map.get(color_otobos, "")
        st.markdown(_card(ICONS["search"], "Total OTOBOS", f"{format_number(otobos_val, decimals=2)}%", otobos_delta, color_otobos, border_class=f"{border_cls} sum-card-otobos-total"), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Keterangan"):
            st.info("**Total OTOBOS**\n\nKalkulasi rata-rata dari skor On Time, On Budget, dan On Spec.\n\n`= (On Time + On Budget + On Spec) / 3`")
    with c8:
        st.markdown(_card(ICONS["clock"], "On Time", f"{format_number(sla_on_time_pct, decimals=2)}%", border_class="sum-card-small"), unsafe_allow_html=True)
    with c9:
        st.markdown(_card(ICONS["currency"], "On Budget", f"{format_number(sla_on_budget_pct, decimals=2)}%", border_class="sum-card-small"), unsafe_allow_html=True)
    with c10:
        st.markdown(_card(ICONS["check_all"], "On Spec", f"{format_number(sla_on_spec_pct, decimals=2)}%", border_class="sum-card-small"), unsafe_allow_html=True)
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── Baris 4 & 5: Learning & Growth + Internal Business Process ────────
    
    # 1. Pisahkan Label/Header menggunakan rasio kolom 1 banding 2
    lbl_c1, lbl_c2 = st.columns([1, 2])
    with lbl_c1:
        _row_label("Learning & Growth")
    with lbl_c2:
        _row_label("Internal Business Process")

    # 2. Baris Atas (Card 1, 3, dan 5)
    r1_c1, r1_c2, r1_c3 = st.columns(3)
    with r1_c1:
        st.markdown(_card(ICONS["people"],  "% Talent Development Effectiveness", tde_nilai, tde_delta, tde_color, border_class=tde_border), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Keterangan"):
            st.info("**Talent Development**\n\nSurat dari SDM")
    with r1_c2:
        st.markdown(_card(ICONS["box"], "% Zero Stock Out Bahan Baku", zbb_nilai, zbb_delta, zbb_color, border_class=zbb_border), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Keterangan"):
            st.info("**Zero Stock Out Bahan Baku**\n\nLaporan Kompartemen ManLog")
    with r1_c3:
        st.markdown(_card(ICONS["bag"], "% Zero Stock Out Kantong", zkn_nilai, zkn_delta, zkn_color, border_class=zkn_border), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Keterangan"):
            st.info("**Zero Stock Out Kantong**\n\nLaporan Kompartemen ManLog")
            
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # 3. Baris Bawah (Card 2, 4, dan 6)
    r2_c1, r2_c2, r2_c3 = st.columns(3)
    with r2_c1:
        st.markdown(_card(ICONS["percent"], "Produktivitas PR-PO", f"{format_number(sips_pct_pr_po, decimals=2)}%", produktivitas_delta, color_produktivitas, border_class=border_class_map.get(color_produktivitas, "")), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Keterangan"):
            st.info("**Produktivitas PR-PO**\n\nRasio Purchase Requisition (PR) yang berhasil dikonversi menjadi Purchase Order (PO).\n\n`= (Total PO / Total PR) x 100%`")
    with r2_c2:
        st.markdown(_card(ICONS["building"], "% Utilisasi Single Platform Pengadaan", usp_nilai, usp_delta, usp_color, border_class=usp_border), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Keterangan"):
            st.info("**Utilisasi Single Platform**\n\nSIPS (Metode Tender)")
    with r2_c3:
        st.markdown(_card(ICONS["check_circle"], "# Safety Score Pengadaan Barang", saf_nilai, saf_delta, saf_color, border_class=saf_border), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Keterangan"):
            st.info("**Safety Score**\n\nEposh V2")
            
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── Baris 6 ──────────────────────────────────────────────────────────
    st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
    c17, c18 = st.columns(2)
    with c17:
        st.markdown(_card(ICONS["file_text"], "Penyusunan Laporan Kinerja", laporan_kinerja_nilai, laporan_kinerja_delta, laporan_kinerja_color, border_class=laporan_kinerja_border), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Keterangan"):
            st.info("**Laporan Kinerja**\n\n-")
    with c18:
        izin_impor_color = "green"
        izin_impor_border = border_class_map.get(izin_impor_color, "")
        st.markdown(_card(ICONS["lock"], "Pemenuhan Izin Impor", izin_impor_nilai, izin_impor_delta, izin_impor_color, border_class=izin_impor_border), unsafe_allow_html=True)
        with st.popover(":material/visibility:", help="Keterangan"):
            st.info("**Pemenuhan Izin Impor**\n\n-")

    st.markdown("<hr style='margin: 24px 0 16px 0; border-color: rgba(128,128,128,0.2);'>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ═════════════════════════════════════════════════════════════════════════
    # BAGIAN 2: LAPORAN PENGADAAN BARANG (Kiri: Volume | Kanan: Nilai)
    # ═════════════════════════════════════════════════════════════════════════
    
    st.markdown('<div class="pagebreak"></div>', unsafe_allow_html=True)
    
    st.markdown(
        f"<h2 style='display:flex; align-items:center; font-size:32px; margin: 0 0 4px 0; font-weight:700; color:var(--text-color);'>"
        f"<span style='margin-right:12px; transform: translateY(4px); display:inline-flex; align-items:center;'>{_svg(ICONS['file_text'], 32)}</span>"
        f"Laporan Pengadaan Barang"
        f"</h2>"
        f"<p style='font-size:15px; font-weight:500; opacity:0.75; margin: 0 0 16px 0;'>"
        f"Periode: <b>{date_from.strftime('%d %B %Y')} s.d. {date_to.strftime('%d %B %Y')}</b></p>", 
        unsafe_allow_html=True
    )

    col_kiri, col_kanan = st.columns(2, gap="large")

    with col_kiri:
        st.markdown(
            f"<h3 style='font-size:20px; margin-bottom:16px; color:var(--text-color);'>"
            f"<span style='margin-right:8px; vertical-align: middle;'>{_svg(ICONS['box'], 26)}</span>"
            f"<span style='vertical-align: middle;'>Realisasi Item PR-PO</span>"
            f"</h3>", 
            unsafe_allow_html=True
        )

        c11, c12 = st.columns(2)
        with c11:
            st.markdown(_card(ICONS["file_text"], "Total PR", format_number(sips_total_pr), f"{format_number(sips_total_po)} sudah memiliki PO"), unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Keterangan"):
                st.info("**Total PR**\n\nJumlah keseluruhan dokumen Purchase Requisition pada periode yang dipilih.")
        with c12:
            st.markdown(_card(ICONS["bag"], "Total PO", format_number(sips_total_po), "Status Closed & Proses PO"), unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Keterangan"):
                st.info("**Total PO**\n\nJumlah Purchase Order yang berhasil diterbitkan (khusus dokumen berstatus *Closed* atau *Proses PO*).")
        
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        c13, c14 = st.columns(2)
        with c13:
            st.markdown(_card(ICONS["clock"], "PR On Progress", format_number(sips_pr_without), ""), unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Keterangan"):
                st.info("**PR On Progress**\n\nJumlah dokumen PR yang masih diproses oleh tim pengadaan dan belum dikonversi menjadi PO.\n\n`= Total PR - Total PO`")
        with c14:
            st.markdown(_card(ICONS["percent"], "% PR-PO", f"{format_number(sips_pct_pr_po, decimals=2)}%", ""), unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Keterangan"):
                st.info("**% PR-PO**\n\nPersentase tingkat konversi penyelesaian dari dokumen PR menjadi PO.\n\n`= (Total PO / Total PR) x 100%`")

        st.markdown("<hr style='margin: 24px 0 16px 0; border-color: rgba(128,128,128,0.2);'>", unsafe_allow_html=True)
        
        if not trend_data.empty:
            chart_type = st.pills("Tampilan:", options=["Per Bulan (Stacked Bar)", "Kumulatif (Line)"], default="Per Bulan (Stacked Bar)", key="pills_trend_summary_count")
            tick_vals = trend_data['month_display'].tolist()
            tick_text = trend_data['hover_label'].tolist()
            fig1 = go.Figure()

            if chart_type == "Kumulatif (Line)":
                fig1.add_trace(go.Scatter(x=trend_data['month_display'], y=trend_data['cum_pr'], mode='lines+markers', name='PR Created', line=dict(color='#1f77b4', width=2), customdata=trend_data[['hover_label']], hovertemplate='<b>%{customdata[0]}</b><br>Kumulatif PR: %{y}<extra></extra>'))
                fig1.add_trace(go.Scatter(x=trend_data['month_display'], y=trend_data['cum_po'], mode='lines+markers', name='PO Created', line=dict(color='#2ca02c', width=2), customdata=trend_data[['hover_label']], hovertemplate='<b>%{customdata[0]}</b><br>Kumulatif PO: %{y}<extra></extra>'))
                y_axis_title = 'Cumulative Count'
            else:
                fig1.add_trace(go.Bar(x=trend_data['month_display'], y=trend_data['total_pr'], name='PR Created', marker_color='#1f77b4', customdata=trend_data[['hover_label']], hovertemplate='<b>%{customdata[0]}</b><br>PR Created: %{y}<extra></extra>'))
                fig1.add_trace(go.Bar(x=trend_data['month_display'], y=trend_data['total_po'], name='PO Created', marker_color='#2ca02c', customdata=trend_data[['hover_label']], hovertemplate='<b>%{customdata[0]}</b><br>PO Created: %{y}<extra></extra>'))
                fig1.update_layout(barmode='group') 
                y_axis_title = 'Count per Month'
        
            fig1.update_layout(height=350, xaxis_title='', yaxis_title=y_axis_title, xaxis=dict(tickmode='array', tickvals=tick_vals, ticktext=tick_text, tickangle=-30), margin=dict(t=60, b=10, l=10, r=30), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("Tidak ada data tren.")

    # == SISI KANAN: NILAI PENGADAAN ==========================================
    with col_kanan:
        st.markdown(
            f"<h3 style='font-size:20px; margin-bottom:16px; color:var(--text-color);'>"
            f"<span style='margin-right:8px; vertical-align: middle;'>{_svg(ICONS['currency'], 26)}</span>"
            f"<span style='vertical-align: middle;'>Realisasi Nilai PR-PO</span>"
            f"</h3>", 
            unsafe_allow_html=True
        )

        c15, c16 = st.columns(2)
        with c15:
            st.markdown(_card(ICONS["currency"], "Total OE", format_idr(sips_oe_total), "OE dari PR (Closed/Proses PO)"), unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Keterangan"):
                st.info("**Total OE**\n\nTotal nilai anggaran/Owner's Estimate (OE) dari dokumen PR yang sudah diproses menjadi PO (khusus Non-Agreement).")
        with c16:
            st.markdown(_card(ICONS["bag"], "Total Nilai PO", format_idr(sips_po_total), "Seluruh realisasi PO"), unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Keterangan"):
                st.info("**Total Nilai PO**\n\nTotal nilai akhir/realisasi dari dokumen PO yang diterbitkan (khusus Non-Agreement).")

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        c17, c18 = st.columns(2)
        with c17:
            st.markdown(_card(ICONS["graph_up"], "Efisiensi", format_idr(sips_savings)), unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Keterangan"):
                st.info("**Efisiensi (Rp)**\n\nTotal nominal Rupiah penghematan yang berhasil dilakukan dalam pengadaan.\n\n`= Total OE - Total Nilai PO`")
        with c18:
            st.markdown(_card(ICONS["percent"], "% Efisiensi", f"{format_number(sips_savings_pct, decimals=2)}%"), unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Keterangan"):
                st.info("**% Efisiensi**\n\nPersentase penghematan pengadaan terhadap nilai anggaran/OE awal.\n\n`= (Efisiensi Rp / Total OE) x 100%`")

        st.markdown("<hr style='margin: 24px 0 16px 0; border-color: rgba(128,128,128,0.2);'>", unsafe_allow_html=True)

        if not val_trend_data.empty:
            chart_type_val = st.pills("Tampilan:", options=["Per Bulan (Bar)", "Kumulatif (Line)"], default="Per Bulan (Bar)", key="pills_trend_summary_val")
            fig2 = go.Figure()

            if chart_type_val == "Kumulatif (Line)":
                fig2.add_trace(go.Scatter(x=val_trend_data['month_display'], y=val_trend_data['cum_oe'], mode='lines+markers', name='Estimasi PR (OE)', line=dict(color='#1f77b4', width=3, shape='spline'), fill='tozeroy', fillcolor='rgba(31,119,180,0.1)', customdata=val_trend_data[['hover_label', 'cum_oe_fmt']], hovertemplate='<b>%{customdata[0]}</b><br>Kumulatif Estimasi PR: %{customdata[1]}<extra></extra>'))
                fig2.add_trace(go.Scatter(x=val_trend_data['month_display'], y=val_trend_data['cum_po'], mode='lines+markers', name='Nilai PO', line=dict(color='#2ca02c', width=3, shape='spline'), fill='tozeroy', fillcolor='rgba(44,160,44,0.1)', customdata=val_trend_data[['hover_label', 'cum_po_fmt']], hovertemplate='<b>%{customdata[0]}</b><br>Kumulatif Nilai PO: %{customdata[1]}<extra></extra>'))
                max_val = max(val_trend_data['cum_oe'].max(), val_trend_data['cum_po'].max())
            else:
                fig2.add_trace(go.Bar(x=val_trend_data['month_display'], y=val_trend_data['total_oe'], name='Estimasi PR (OE)', marker_color='#1f77b4', customdata=val_trend_data[['hover_label', 'oe_fmt']], hovertemplate='<b>%{customdata[0]}</b><br>Estimasi PR: %{customdata[1]}<extra></extra>'))
                fig2.add_trace(go.Bar(x=val_trend_data['month_display'], y=val_trend_data['total_po_val'], name='Nilai PO', marker_color='#2ca02c', customdata=val_trend_data[['hover_label', 'po_fmt']], hovertemplate='<b>%{customdata[0]}</b><br>Nilai PO: %{customdata[1]}<extra></extra>'))
                fig2.update_layout(barmode='group')
                max_val = max(val_trend_data['total_oe'].max(), val_trend_data['total_po_val'].max())

            fig2.update_layout(height=350, xaxis_title='', yaxis_title='Total Value (IDR)', yaxis={**idr_axis(max_val), 'gridcolor': 'rgba(128,128,128,0.1)'}, xaxis=dict(tickmode='array', tickvals=val_trend_data['month_display'].tolist(), ticktext=val_trend_data['hover_label'].tolist(), tickangle=-30, showgrid=False), margin=dict(t=60, b=10, l=10, r=30), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Tidak ada data tren nilai.")

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<hr style='margin: 24px 0 16px 0; border-color: rgba(128,128,128,0.2);'>", unsafe_allow_html=True)

    # ═════════════════════════════════════════════════════════════════════════
    # BAGIAN 3: LAPORAN BAGIAN
    # ═════════════════════════════════════════════════════════════════════════
    
    st.markdown('<div class="pagebreak"></div>', unsafe_allow_html=True)

    st.markdown(
        f"<h2 style='display:flex; align-items:center; font-size:32px; margin: 0 0 4px 0; font-weight:700; color:var(--text-color);'>"
        f"<span style='margin-right:12px; transform: translateY(4px); display:inline-flex; align-items:center;'>{_svg(ICONS['building'], 32)}</span>"
        f"Laporan Bagian"
        f"</h2>"
        f"<p style='font-size:15px; font-weight:500; opacity:0.75; margin: 0 0 24px 0;'>"
        f"Periode: <b>{date_from.strftime('%d %B %Y')} s.d. {date_to.strftime('%d %B %Y')}</b></p>", 
        unsafe_allow_html=True
    )

    pilihan_bagian = st.pills("Pilih Bagian:", options=["ALPATA", "BARUM", "BB/BD/BP"], default="ALPATA", key="pills_laporan_bagian", label_visibility="collapsed")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    _bagian_filter_cond = build_sips_bagian_cond([pilihan_bagian], date_to=date_to)
    bagian_query = f"""
    SELECT
        SUM(CASE WHEN {where_pr} THEN 1 ELSE 0 END) AS total_pr,
        SUM(CASE WHEN UPPER(TRIM(status)) IN ('CLOSED','PROSES PO') AND {po_date_cond} THEN 1 ELSE 0 END) AS total_po,
        ROUND(AVG(CASE WHEN UPPER(TRIM(status)) IN ('CLOSED', 'PROSES PO') AND {po_date_cond} THEN pr_po_days END)::numeric, 2) AS avg_pr_po,
        COALESCE(SUM(CASE WHEN UPPER(TRIM(status)) IN ('CLOSED','PROSES PO') AND {po_date_cond} THEN nilai_sla END), 0) AS sla_ontime,
        COALESCE(SUM(CASE WHEN UPPER(TRIM(status)) IN ('CLOSED', 'PROSES PO') AND {po_date_cond} AND (outline_agreement IS NULL OR TRIM(outline_agreement) = '') THEN oe_pr END), 0) AS sips_oe_total,
        COALESCE(SUM(CASE WHEN UPPER(TRIM(status)) IN ('CLOSED', 'PROSES PO') AND {po_date_cond} AND (outline_agreement IS NULL OR TRIM(outline_agreement) = '') THEN nilai_item_po END), 0) AS sips_po_total,
        COALESCE(SUM(CASE WHEN UPPER(TRIM(status)) IN ('CLOSED', 'PROSES PO') AND {po_date_cond} AND (outline_agreement IS NULL OR TRIM(outline_agreement) = '') THEN oe_pr END), 0) AS sips_oe_na,
        COALESCE(SUM(CASE WHEN UPPER(TRIM(status)) IN ('CLOSED', 'PROSES PO') AND {po_date_cond} AND (outline_agreement IS NULL OR TRIM(outline_agreement) = '') THEN nilai_item_po END), 0) AS sips_po_na,
        SUM(CASE WHEN persen_po_sr_mr <= 1.0 AND UPPER(TRIM(status)) IN ('CLOSED','PROSES PO') AND {po_date_cond} THEN 1 ELSE 0 END) AS on_budget_count
    FROM vw_sips WHERE {where_gabungan} AND {_bagian_filter_cond}
    """

    with st.spinner(f"Memuat performa bagian {pilihan_bagian}..."):
        try:
            b_data = load_data(bagian_query)
        except Exception as e:
            st.error(f"Gagal memuat data bagian: {e}")
            b_data = pd.DataFrame()

    if not b_data.empty:
        b_total_pr  = int(b_data['total_pr'][0] or 0)
        b_total_po  = int(b_data['total_po'][0] or 0)
        b_ontime    = float(b_data['sla_ontime'][0] or 0)
        b_lt        = float(b_data['avg_pr_po'][0] or 0)
        b_onbudget  = int(b_data['on_budget_count'][0] or 0)
        pct_ontime   = (b_ontime / b_total_po * 100) if b_total_po > 0 else 0.0
        pct_onbudget = (b_onbudget / b_total_po * 100) if b_total_po > 0 else 0.0
        b_sips_oe_na = float(b_data['sips_oe_na'][0] or 0)
        b_sips_po_na = float(b_data['sips_po_na'][0] or 0)
        b_efis_val   = b_sips_oe_na - b_sips_po_na
        b_efis_pct   = (b_efis_val / b_sips_oe_na * 100) if b_sips_oe_na > 0 else 0.0

        _bagian_key_map = {"ALPATA": "ALPATA", "BARUM": "BARUM", "BB/BD/BP": "BBBD"}
        _bagian_key     = _bagian_key_map.get(pilihan_bagian, pilihan_bagian)
        _efis_prefix    = f"KPI_EFISIENSI_BAGIAN_{_bagian_key}"

        st.session_state[f"_aktual_{_efis_prefix}"] = b_efis_pct
        # Membaca dari Tabel Bulanan (Cache) terlebih dahulu
        _efis_monthly = kpi_monthly_cache.get(_efis_prefix, {})
        _efis_target = (_efis_monthly.get("target", "") or get_setting(f"{_efis_prefix}_TARGET", "")).strip() or "-"
        _efis_arah   = (_efis_monthly.get("arah", "") or get_setting(f"{_efis_prefix}_ARAH", ">")).strip() or ">"
        
        # Otomatis konversi angka mentah (misal: 5 -> 5.00%)
        _efis_target_fmt = auto_format_target(_efis_target)

        if _efis_target_fmt and _efis_target_fmt != "-":
            _efis_color_key, _ = _eval_kpi_color(f"{b_efis_pct:.4f}%", _efis_target_fmt, _efis_arah)
            tipe_efis_tampil = _efis_color_key if _efis_color_key in ("green", "red") else ("green" if b_efis_val >= 0 else "red")
        else:
            tipe_efis_tampil = "green" if b_efis_val >= 0 else "red"

        _efis_sym = _ARAH_SYM.get(_efis_arah, ">")
        if _efis_target_fmt and _efis_target_fmt != "-": 
            str_efis_delta = f"Target: {_efis_sym} {_efis_target_fmt}"
        else: 
            str_efis_delta = ""

        col_onbudget = "#09ab3b" if pct_onbudget >= 80 else "#f0a500"
        col_ontime   = "#09ab3b" if pct_ontime >= 80 else "#f0a500"
        col_efis     = "#09ab3b" if b_efis_val >= 0 else "#e03c3c"
        
        str_onbudget = f"{pct_onbudget:.2f}%".replace('.', ',')
        str_ontime   = f"{pct_ontime:.2f}%".replace('.', ',')
        str_efis_pct = f"{b_efis_pct:+.2f}%".replace('.', ',')

        str_onbudget_tampil = str_onbudget
        tipe_budget_tampil  = "green" if pct_onbudget >= 80 else "red"
        str_efis_pct_tampil = f"{str_efis_pct} <span style='font-size: 0.7em; font-weight: 500; opacity: 0.85;'>({format_idr(b_efis_val)})</span>"

        b_otobos_val = (pct_ontime + pct_onbudget + sla_on_spec_pct) / 3
        tipe_otobos_bagian = "green" if b_otobos_val >= 90 else "red"
        str_otobos_bagian = f"{format_number(b_otobos_val, decimals=2)}%"

        b_pct_pr_po = (b_total_po / b_total_pr * 100) if b_total_pr > 0 else 0.0
        b_prod_color, _ = _eval_kpi_color(f"{b_pct_pr_po:.2f}%", _prod_target, _prod_arah)
        tipe_prod_bagian = b_prod_color if b_prod_color in ("green", "red") else ("green" if b_pct_pr_po > 90 else "red")
        str_prod_bagian = f"{format_number(b_pct_pr_po, decimals=2)}%"

        karyawan_query_early = f"""
        SELECT
            nama,
            SUM(CASE WHEN {where_pr} THEN 1 ELSE 0 END) AS total_pr,
            SUM(CASE WHEN UPPER(TRIM(status)) IN ('CLOSED','PROSES PO') AND {po_date_cond} THEN 1 ELSE 0 END) AS total_po,
            ROUND(AVG(CASE WHEN UPPER(TRIM(status)) IN ('CLOSED', 'PROSES PO') AND {po_date_cond} THEN pr_po_days END)::numeric, 2) AS avg_pr_po,
            COALESCE(SUM(CASE WHEN UPPER(TRIM(status)) IN ('CLOSED','PROSES PO') AND {po_date_cond} THEN nilai_sla END), 0) AS sla_ontime,
            COALESCE(SUM(CASE WHEN UPPER(TRIM(status)) IN ('CLOSED', 'PROSES PO') AND {po_date_cond} AND (outline_agreement IS NULL OR TRIM(outline_agreement) = '') THEN oe_pr END), 0) AS sips_oe_total,
            COALESCE(SUM(CASE WHEN UPPER(TRIM(status)) IN ('CLOSED', 'PROSES PO') AND {po_date_cond} AND (outline_agreement IS NULL OR TRIM(outline_agreement) = '') THEN nilai_item_po END), 0) AS sips_po_total,
            COALESCE(SUM(CASE WHEN UPPER(TRIM(status)) IN ('CLOSED', 'PROSES PO') AND {po_date_cond} AND (outline_agreement IS NULL OR TRIM(outline_agreement) = '') THEN oe_pr END), 0) AS sips_oe_na,
            COALESCE(SUM(CASE WHEN UPPER(TRIM(status)) IN ('CLOSED', 'PROSES PO') AND {po_date_cond} AND (outline_agreement IS NULL OR TRIM(outline_agreement) = '') THEN nilai_item_po END), 0) AS sips_po_na,
            SUM(CASE WHEN persen_po_sr_mr <= 1.0 AND UPPER(TRIM(status)) IN ('CLOSED','PROSES PO') AND {po_date_cond} THEN 1 ELSE 0 END) AS on_budget_count
        FROM vw_sips WHERE {where_gabungan} AND {_bagian_filter_cond}
        GROUP BY nama ORDER BY total_pr DESC
        """
        with st.spinner(f"Memuat data bagian {pilihan_bagian}..."):
            karyawan_data = load_data(karyawan_query_early)

        b_eproc_pct   = 0.0
        b_eproc_nilai = "-"
        b_eproc_delta = usp_delta  
        b_eproc_color = "neutral"
        b_eproc_border = ""
        if not karyawan_data.empty and not eproc_emp_data.empty:
            _df_k = karyawan_data.copy()
            _df_e = eproc_emp_data.copy()
            _df_k['nama_join'] = _df_k['nama'].astype(str).str.upper().str.split(',').str[0].str.strip()
            _df_e['nama_join'] = _df_e['nama_join'].astype(str).str.split(',').str[0].str.strip()
            _merged = pd.merge(_df_k[['nama_join']], _df_e, on='nama_join', how='left')
            _tot_dok  = _merged['total_dokumen_eproc'].fillna(0).sum()
            _tot_epr  = _merged['total_eproc_method'].fillna(0).sum()
            if _tot_dok > 0:
                b_eproc_pct   = (_tot_epr / _tot_dok) * 100
                b_eproc_nilai = f"{format_number(b_eproc_pct, decimals=2)}%"
                b_eproc_color, b_eproc_border = _eval_kpi_color(b_eproc_nilai, usp_target, usp_arah)
                b_eproc_delta = usp_delta 

        if is_admin: dlg_efisiensi_bagian = _dialog_efisiensi_bagian(pilihan_bagian, _efis_prefix)

        r1c1, r1c2, r1c3 = st.columns(3)
        with r1c1: 
            st.markdown(_card(ICONS["currency"], "On Budget", str_onbudget_tampil, "", tipe_budget_tampil), unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Keterangan"):
                st.info("**On Budget**\n\nPersentase PO di bagian ini yang realisasi nilainya tidak melebihi estimasi/SR awal (≤ 100%).")
        with r1c2: 
            tipe_time = "green" if pct_ontime >= 80 else "red"
            st.markdown(_card(ICONS["check_circle"], "On Time", str_ontime, "", tipe_time), unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Keterangan"):
                st.info("**On Time**\n\nPersentase PO di bagian ini yang berhasil diselesaikan tepat waktu sesuai target SLA yang ditetapkan.")
        with r1c3: 
            st.markdown(_card(ICONS["search"], "Total OTOBOS", str_otobos_bagian, otobos_delta, tipe_otobos_bagian, border_class=border_class_map.get(tipe_otobos_bagian, "")), unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Keterangan"):
                st.info("**Total OTOBOS (Bagian)**\n\nRata-rata skor performa On Time, On Budget, dan On Spec spesifik untuk dokumen yang ditangani oleh bagian ini.")

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        r2c1, r2c2, r2c3 = st.columns(3)
        with r2c1:
            st.markdown(_card(ICONS["graph_up"], "Efisiensi", str_efis_pct_tampil, str_efis_delta, tipe_efis_tampil, border_class=border_class_map.get(tipe_efis_tampil, "")), unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Keterangan"):
                st.info("**Efisiensi (Non-Agreement)**\n\nPersentase dan nominal penghematan realisasi PO terhadap anggaran awal (OE), dihitung secara spesifik untuk item **Non-Agreement** pada bagian ini.")
        with r2c2:
            st.markdown(_card(ICONS["building"], "% Single Platform", b_eproc_nilai if b_eproc_nilai != "-" else "-", b_eproc_delta, b_eproc_color, border_class=b_eproc_border), unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Keterangan"):
                st.info("**% Single Platform**\n\nPersentase dokumen pengadaan pada bagian ini yang diproses secara digital melalui sistem EPROC.")
        with r2c3:
            st.markdown(_card(ICONS["percent"], "Produktivitas PR-PO", str_prod_bagian, produktivitas_delta, tipe_prod_bagian, border_class=border_class_map.get(tipe_prod_bagian, "")), unsafe_allow_html=True)
            with st.popover(":material/visibility:", help="Keterangan"):
                st.info("**Produktivitas PR-PO**\n\nRasio konversi penyelesaian dokumen Purchase Requisition (PR) menjadi Purchase Order (PO) oleh tim di bagian ini.")

        st.markdown("<hr style='margin: 32px 0; border-color: rgba(128,128,128,0.2);'>", unsafe_allow_html=True)

        st.markdown(
            f"<h3 style='font-size:20px; margin-bottom:16px; color:var(--text-color);'>"
            f"<span style='margin-right:8px; vertical-align: middle;'>{_svg(ICONS['people'], 26)}</span>"
            f"<span style='vertical-align: middle;'>Kinerja Karyawan</span>"
            f"</h3>", 
            unsafe_allow_html=True
        )

        if not karyawan_data.empty:
            df_karyawan = karyawan_data.copy()
            if not eproc_emp_data.empty:
                df_karyawan['nama_join'] = df_karyawan['nama'].astype(str).str.upper().str.split(',').str[0].str.strip()
                eproc_emp_data['nama_join'] = eproc_emp_data['nama_join'].astype(str).str.split(',').str[0].str.strip()
                df_karyawan = pd.merge(df_karyawan, eproc_emp_data, on='nama_join', how='left')
                df_karyawan['total_dokumen_eproc'] = df_karyawan['total_dokumen_eproc'].fillna(0)
                df_karyawan['total_eproc_method'] = df_karyawan['total_eproc_method'].fillna(0)
                df_karyawan['% Single Platform'] = (df_karyawan['total_eproc_method'] / df_karyawan['total_dokumen_eproc'].replace(0, float('nan')) * 100).fillna(0)
            else:
                df_karyawan['% Single Platform'] = 0.0

            df_karyawan['Total PR'] = df_karyawan['total_pr']
            df_karyawan['Total PO'] = df_karyawan['total_po']
            df_karyawan['PO/PR'] = (df_karyawan['total_po'] / df_karyawan['total_pr'].replace(0, float('nan')) * 100).fillna(0).apply(lambda x: f"{x:.1f}%")
            df_karyawan['PR-PO (Hari)'] = df_karyawan['avg_pr_po'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "0.0")
            df_karyawan['% On Time'] = (df_karyawan['sla_ontime'] / df_karyawan['total_po'].replace(0, float('nan')) * 100).fillna(0)
            df_karyawan['Efisiensi Rp_val'] = df_karyawan['sips_oe_na'] - df_karyawan['sips_po_na']
            df_karyawan['Efisiensi %'] = (df_karyawan['Efisiensi Rp_val'] / df_karyawan['sips_oe_na'].replace(0, float('nan')) * 100).fillna(0)
            df_karyawan['% On Budget'] = (df_karyawan['on_budget_count'] / df_karyawan['total_po'].replace(0, float('nan')) * 100).fillna(0)
            df_karyawan['% On Spec'] = 99.30
            df_karyawan['OTOBOS'] = ((df_karyawan['% On Time'] + df_karyawan['% On Budget'] + df_karyawan['% On Spec']) / 3).fillna(0)
            
            df_karyawan['% On Time'] = df_karyawan['% On Time'].apply(lambda x: f"{x:.2f}%")
            df_karyawan['Efisiensi %'] = df_karyawan['Efisiensi %'].apply(lambda x: f"{x:.2f}%")
            df_karyawan['Efisiensi Rp'] = df_karyawan['Efisiensi Rp_val'].apply(lambda x: format_idr_short(x) if pd.notna(x) else "0")
            df_karyawan['% On Budget'] = df_karyawan['% On Budget'].apply(lambda x: f"{x:.2f}%")
            df_karyawan['% On Spec'] = df_karyawan['% On Spec'].apply(lambda x: f"{x:.2f}%")
            df_karyawan['OTOBOS'] = df_karyawan['OTOBOS'].apply(lambda x: f"{x:.2f}%")
            df_karyawan['% Single Platform'] = df_karyawan['% Single Platform'].apply(lambda x: f"{x:.2f}%") 
            
            df_table = df_karyawan[['nama', 'Total PR', 'Total PO', 'PO/PR', 'PR-PO (Hari)', '% On Time', 'Efisiensi %', 'Efisiensi Rp', '% On Budget', '% On Spec', 'OTOBOS', '% Single Platform']].rename(columns={'nama': 'Nama'})
            df_table.index = df_table.index + 1
            st.dataframe(df_table, use_container_width=True)

            import io
            _excel_buf = io.BytesIO()
            with pd.ExcelWriter(_excel_buf, engine="openpyxl") as _writer:
                df_table.to_excel(_writer, index=True, sheet_name="Kinerja Karyawan")
            _excel_bytes = _excel_buf.getvalue()

            import base64
            _b64 = base64.b64encode(_excel_bytes).decode()
            _filename = f"Kinerja_Karyawan_{pilihan_bagian}.xlsx"
            _mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

            st.markdown(f"""
                <a href="data:{_mime};base64,{_b64}" download="{_filename}" style="text-decoration:none;">
                    <button style="
                        background-color: #e03c3c;
                        color: white;
                        border: none;
                        padding: 4px 12px;
                        border-radius: 6px;
                        font-size: 12px;
                        font-weight: 600;
                        cursor: pointer;
                        display: inline-flex;
                        align-items: center;
                        gap: 6px;
                        margin-top: 2px;
                    ">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24"
                            fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                            <polyline points="7 10 12 15 17 10"/>
                            <line x1="12" y1="15" x2="12" y2="3"/>
                        </svg>
                        Download sebagai XLSX
                    </button>
                </a>
            """, unsafe_allow_html=True)
        else:
            st.info(f"Tidak ada data kinerja karyawan untuk bagian **{pilihan_bagian}** pada periode ini.")
            
        st.markdown("<hr style='margin: 32px 0; border-color: rgba(128,128,128,0.2);'>", unsafe_allow_html=True)

        st.markdown(
            f"<h3 style='font-size:20px; margin-bottom:16px; color:var(--text-color);'>"
            f"<span style='margin-right:8px; vertical-align: middle;'>{_svg(ICONS['box'], 26)}</span>"
            f"<span style='vertical-align: middle;'>Tren Realisasi Item PR-PO</span>"
            f"</h3>", 
            unsafe_allow_html=True
        )

        trend_bagian_query = f"""
        WITH pr_bulanan AS (
            SELECT DATE_TRUNC('month', tgl_disposisi_buyer)::date AS month, COUNT(*) AS total_pr
            FROM vw_sips WHERE {where_pr} AND {_bagian_filter_cond} GROUP BY 1
        ),
        po_bulanan AS (
            SELECT DATE_TRUNC('month', COALESCE(tgl_po, tgl_disposisi_buyer))::date AS month, COUNT(*) AS total_po
            FROM vw_sips WHERE UPPER(TRIM(status)) IN ('CLOSED','PROSES PO') AND {po_date_cond} AND {_bagian_filter_cond} GROUP BY 1
        )
        SELECT TO_CHAR(COALESCE(pr_bulanan.month, po_bulanan.month), 'YYYY-MM-01')::date AS month,
               COALESCE(pr_bulanan.total_pr, 0) AS total_pr, COALESCE(po_bulanan.total_po, 0) AS total_po
        FROM pr_bulanan FULL OUTER JOIN po_bulanan ON pr_bulanan.month = po_bulanan.month ORDER BY 1
        """

        with st.spinner(f"Memuat tren bagian {pilihan_bagian}..."):
            trend_bagian_data = load_data(trend_bagian_query)

        if not trend_bagian_data.empty:
            trend_bagian_data['month'] = pd.to_datetime(trend_bagian_data['month']).dt.tz_localize(None)
            trend_bagian_data = trend_bagian_data.sort_values('month')
            trend_bagian_data = trend_bagian_data[(trend_bagian_data['month'] >= dt_from_pd) & (trend_bagian_data['month'] <= dt_to_pd)]
            trend_bagian_data['month_display'] = trend_bagian_data['month'].apply(resolve_month_date)
            trend_bagian_data['hover_label'] = trend_bagian_data['month_display'].apply(fmt_date)

            fig_trend_bagian = go.Figure()
            fig_trend_bagian.add_trace(go.Bar(x=trend_bagian_data['month_display'], y=trend_bagian_data['total_pr'], name='PR Created', marker_color='#1f77b4', customdata=trend_bagian_data[['hover_label']], hovertemplate='<b>%{customdata[0]}</b><br>PR Created: %{y}<extra></extra>'))
            fig_trend_bagian.add_trace(go.Bar(x=trend_bagian_data['month_display'], y=trend_bagian_data['total_po'], name='PO Created', marker_color='#2ca02c', customdata=trend_bagian_data[['hover_label']], hovertemplate='<b>%{customdata[0]}</b><br>PO Created: %{y}<extra></extra>'))
            
            fig_trend_bagian.update_layout(barmode='group', height=360, xaxis_title='', yaxis_title='Jumlah Item', xaxis=dict(tickmode='array', tickvals=trend_bagian_data['month_display'].tolist(), ticktext=trend_bagian_data['hover_label'].tolist(), tickangle=-30), margin=dict(t=60, b=10, l=10, r=30), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_trend_bagian, use_container_width=True)
        else:
            st.info(f"Tidak ada data tren untuk bagian **{pilihan_bagian}**.")
            
        st.markdown("<br><br>", unsafe_allow_html=True)
    else:
        st.info(f"Tidak ada transaksi PO untuk bagian **{pilihan_bagian}** pada periode ini.")