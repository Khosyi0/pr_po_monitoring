"""
context_builder.py - Pengumpul konteks global untuk Melati (AI Analyst)

Logika lintas sistem:
  • Saat berada di halaman SAP  → konteks SAP pakai filter AKTIF, konteks SIPS pakai filter DEFAULT
  • Saat berada di halaman SIPS → konteks SIPS pakai filter AKTIF, konteks SAP pakai filter DEFAULT

Hanya query AGREGAT (KPI ringkasan) yang dijalankan, tidak ada raw data ribuan baris.
Hasil disimpan di st.session_state["global_context"] dan di-refresh saat filter berubah.
"""

import streamlit as st
from datetime import datetime, timedelta
from utils import format_idr, format_number

# =============================================================================
# FINGERPRINT FILTER: untuk mendeteksi perubahan filter
# =============================================================================

def _fingerprint_sap(date_from, date_to, selected_department,
                     exclude_dept, selected_p_group,
                     exclude_purchasing_group, selected_bagian, exclude_bagian) -> str:
    return (f"{date_from}|{date_to}|{sorted(selected_department)}|{exclude_dept}"
            f"|{sorted(selected_p_group)}|{exclude_purchasing_group}"
            f"|{sorted(selected_bagian)}|{exclude_bagian}")

def _fingerprint_sips(date_from, date_to, selected_nama, selected_bagian) -> str:
    return f"{date_from}|{date_to}|{sorted(selected_nama)}|{sorted(selected_bagian)}"

# =============================================================================
# QUERY KPI SAP: hanya agregat
# =============================================================================

def _fetch_sap_context(load_data, filter_conditions,
                       bagian_pr_cond, bagian_po_cond,
                       teks_filter: str,
                       date_from=None, date_to=None) -> str:
    """Jalankan query KPI ringkasan SAP dan kembalikan string konteks."""
    try:
        bagian_po_poi = bagian_po_cond.replace('bagian_po', 'poi.bagian_po')

        # Fallback: jika date_from/date_to tidak tersedia, ambil dari filter_conditions
        if not date_from or not date_to:
            import re
            m_from = re.search(r"first_full_release >= '([^']+)'", filter_conditions)
            m_to   = re.search(r"first_full_release <= '([^']+)'", filter_conditions)
            date_from = m_from.group(1) if m_from else '2026-01-01'
            date_to   = m_to.group(1)   if m_to   else '2026-12-31'

        # PR query: filter by first_full_release (hanya PR yang sudah full release di periode tsb)
        pr_q = f"""
        SELECT
            COUNT(DISTINCT CASE WHEN no_pr != 'No PR' AND {bagian_pr_cond}
                THEN no_pr || '-' || line_item_pr::text END)              AS total_pr,
            COUNT(DISTINCT CASE WHEN nomor_po IS NOT NULL AND no_pr != 'No PR' AND {bagian_pr_cond}
                THEN no_pr || '-' || line_item_pr::text END)              AS pr_with_po,
            COUNT(DISTINCT CASE WHEN nomor_po IS NULL AND no_pr != 'No PR' AND {bagian_pr_cond}
                THEN no_pr || '-' || line_item_pr::text END)              AS pr_without_po,
            COALESCE(SUM(CASE WHEN {bagian_pr_cond} THEN oe ELSE 0 END), 0) AS total_estimasi
        FROM vw_pr_po_complete
        WHERE {filter_conditions}
          AND first_full_release IS NOT NULL
        """

        # PO query: filter by date_ordered
        po_q = f"""
        SELECT
            COUNT(poi.nomor_po)                                           AS total_po,
            COALESCE(SUM(poi.total_amount_local_curr), 0)                 AS total_po_amount,
            ROUND(AVG(
                CASE WHEN poi.first_full_release IS NOT NULL AND poh.date_ordered IS NOT NULL
                THEN (poh.date_ordered::date - poi.first_full_release::date)
                END
            )::numeric, 2)                                                        AS avg_lead_time,
            COUNT(DISTINCT poh.nomor_po)                                  AS total_po_distinct,
            COUNT(DISTINCT CASE WHEN poi.status_pengiriman = 'SELESAI'
                THEN poh.nomor_po END)                                    AS po_delivered,
            COUNT(DISTINCT CASE WHEN poi.on_time_delivery = 'TEPAT WAKTU'
                THEN poh.nomor_po END)                                    AS po_ontime,
            COUNT(DISTINCT CASE WHEN poi.on_time_delivery IN ('TEPAT WAKTU','TERLAMBAT')
                THEN poh.nomor_po END)                                    AS po_delivered_total
        FROM po_items poi
        JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
        WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
          AND {bagian_po_poi}
        """

        vendor_q = f"""
        SELECT vendor_name, COUNT(DISTINCT poi.nomor_po) AS total_po,
               SUM(poi.total_amount_local_curr) AS total_value
        FROM po_items poi
        JOIN purchase_orders poh ON poi.nomor_po = poh.nomor_po
        LEFT JOIN vendors v ON poh.vendor_code = v.vendor_code
        WHERE poh.date_ordered >= '{date_from}' AND poh.date_ordered <= '{date_to}'
          AND {bagian_po_poi} AND v.vendor_name IS NOT NULL
        GROUP BY vendor_name ORDER BY total_value DESC LIMIT 5
        """

        pr_kpi = load_data(pr_q)
        po_kpi = load_data(po_q)
        vend   = load_data(vendor_q)

        pr_r = pr_kpi.iloc[0]
        po_r = po_kpi.iloc[0]
        total_pr      = int(pr_r["total_pr"]       or 0)
        total_po      = int(po_r["total_po"]       or 0)
        pr_with_po    = int(pr_r["pr_with_po"]     or 0)
        pr_without    = int(pr_r["pr_without_po"]  or 0)
        estimasi      = float(pr_r["total_estimasi"]  or 0)
        po_amount     = float(po_r["total_po_amount"] or 0)
        savings       = estimasi - po_amount
        savings_pct   = ((savings / estimasi) * 100) if estimasi > 0 else 0.0
        _alt          = po_r["avg_lead_time"]
        avg_lt        = float(_alt) if _alt is not None else 0.0
        po_dist       = int(po_r["total_po_distinct"]  or 0)
        po_delivered  = int(po_r["po_delivered"]       or 0)
        po_ontime     = int(po_r["po_ontime"]          or 0)
        po_del_tot    = int(po_r["po_delivered_total"] or 0)
        produktivitas = (pr_with_po / total_pr  * 100) if total_pr  > 0 else 0.0
        pct_kirim     = (po_delivered / po_dist * 100) if po_dist   > 0 else 0.0
        ketepatan     = (po_ontime / po_del_tot * 100) if po_del_tot > 0 else 0.0

        lines = [
            "## [SAP] FILTER AKTIF", teks_filter, "",
            "## [SAP] RINGKASAN KPI PR-PO",
            f"- Total PR: {format_number(total_pr)} item "
            f"(Dengan PO: {format_number(pr_with_po)}, Pending: {format_number(pr_without)})",
            f"- Total PO: {format_number(total_po)} | Total PO Unik: {format_number(po_dist)}",
            f"- Produktivitas PR→PO: {produktivitas:.1f}%",
            f"- Total OE (Estimasi): {format_idr(estimasi)}",
            f"- Total Realisasi PO: {format_idr(po_amount)}",
            f"- Total Savings: {format_idr(savings)} ({savings_pct:.1f}%)",
            f"- Avg Lead Time Proses PO: {avg_lt:.1f} hari",
            f"- % Pengiriman Selesai: {pct_kirim:.1f}%",
            f"- % Ketepatan Pengiriman: {ketepatan:.1f}%", "",
        ]

        if not vend.empty:
            lines.append("## [SAP] TOP 5 VENDOR (Nilai PO Terbesar)")
            lines.append(vend.to_markdown(index=False))
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        return f"## [SAP] Konteks tidak tersedia\nError: {e}\n"

# =============================================================================
# QUERY KPI SIPS: hanya agregat
# =============================================================================

def _fetch_sips_context(load_data, date_from, date_to,
                        selected_nama, selected_bagian, teks_filter: str) -> str:
    """Jalankan query KPI ringkasan SIPS dan kembalikan string konteks."""
    try:
        wp = ["1=1", "status IN ('Closed','Proses PO')"]
        if date_from:
            wp.append(f"requisition_date >= '{date_from}'")
        if date_to:
            wp.append(f"requisition_date <= '{date_to}'")
        if selected_bagian and "All" not in selected_bagian:
            bgs = ", ".join(f"'{b}'" for b in selected_bagian)
            wp.append(f"bagian IN ({bgs})")
        if selected_nama and "All" not in selected_nama:
            nms = ", ".join(f"'{n}'" for n in selected_nama)
            wp.append(f"nama IN ({nms})")
        where = " AND ".join(wp)

        kpi_q = f"""
        SELECT
            COUNT(DISTINCT no_pr)                                               AS total_pr,
            COUNT(DISTINCT CASE WHEN status IN ('Closed','Proses PO')
                THEN no_pr END)                                                 AS total_po,
            ROUND(AVG(pr_po_days)::numeric, 1)                                  AS avg_pr_po,
            ROUND(AVG(realisasi_sla)::numeric, 1)                               AS avg_real_sla,
            ROUND(AVG(standar_sla)::numeric, 1)                                 AS avg_std_sla,
            ROUND(SUM(CASE WHEN nilai_sla = 1 THEN 1.0 END)
                / NULLIF(COUNT(CASE WHEN nilai_sla IS NOT NULL THEN 1 END), 0)
                * 100, 1)                                                       AS pct_ontime,
            ROUND(SUM(oe_pr)::numeric / 1e9, 2)                                 AS total_oe_milyar,
            ROUND(SUM(nilai_item_po)::numeric / 1e9, 2)                         AS total_po_milyar,
            ROUND((1 - SUM(nilai_item_po) / NULLIF(SUM(oe_pr), 0)) * 100, 2)    AS efisiensi_pct
        FROM vw_sips
        WHERE {where}
        """

        perf_q = f"""
        SELECT nama,
               COUNT(DISTINCT no_pr) AS total_pr,
               COUNT(DISTINCT CASE WHEN status IN ('Closed','Proses PO') THEN no_pr END) AS total_po,
               ROUND(AVG(pr_po_days)::numeric, 1) AS avg_pr_po,
               ROUND(SUM(CASE WHEN nilai_sla = 1 THEN 1.0 END)
                   / NULLIF(COUNT(CASE WHEN nilai_sla IS NOT NULL THEN 1 END), 0)
                   * 100, 1) AS pct_ontime
        FROM vw_sips
        WHERE {where}
        GROUP BY nama ORDER BY pct_ontime DESC NULLS LAST
        """

        kpi  = load_data(kpi_q)
        perf = load_data(perf_q)

        r = kpi.iloc[0]
        total_pr      = int(r["total_pr"]        or 0)
        total_po      = int(r["total_po"]        or 0)
        avg_pr_po     = float(r["avg_pr_po"]     or 0)
        avg_real      = float(r["avg_real_sla"]  or 0)
        avg_std       = float(r["avg_std_sla"]   or 0)
        pct_ontime    = float(r["pct_ontime"]    or 0)
        oe_m          = float(r["total_oe_milyar"]  or 0)
        po_m          = float(r["total_po_milyar"]  or 0)
        efisiensi_pct = float(r["efisiensi_pct"] or 0)
        konversi      = (total_po / total_pr * 100) if total_pr > 0 else 0.0

        lines = [
            "## [SIPS] FILTER AKTIF", teks_filter, "",
            "## [SIPS] RINGKASAN KPI SIPS",
            f"- Total PR SIPS: {format_number(total_pr)}",
            f"- Total PO SIPS: {format_number(total_po)} (Konversi: {konversi:.1f}%)",
            f"- Rata-rata PR-PO (Disposisi→PO, hari kalender): {avg_pr_po:.1f} hari",
            f"- Rata-rata Realisasi SLA (hari kerja): {avg_real:.1f} hari "
            f"(Standar rata-rata: {avg_std:.1f} hari)",
            f"- % On Time SLA: {pct_ontime:.1f}%",
            f"- Total OE: Rp {oe_m:.2f} Milyar",
            f"- Total Realisasi PO: Rp {po_m:.2f} Milyar",
            f"- Efisiensi Anggaran: {efisiensi_pct:.2f}%", "",
        ]

        if not perf.empty:
            lines.append("## [SIPS] PERFORMA PER KARYAWAN")
            lines.append(perf.to_markdown(index=False))
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        return f"## [SIPS] Konteks tidak tersedia\nError: {e}\n"

# =============================================================================
# FUNGSI UTAMA: dipanggil dari app.py setiap render
# =============================================================================

def build_global_context(
    load_data,
    is_sips: bool,
    # SAP params
    filter_conditions, bagian_pr_cond, bagian_po_cond, teks_filter_sap,
    # SIPS params
    sips_date_from, sips_date_to, sips_selected_nama, sips_selected_bagian, teks_filter_sips,
    # SAP default params (dipakai saat halaman SIPS aktif)
    default_filter_conditions, default_bagian_pr_cond, default_bagian_po_cond,
    default_teks_filter_sap,
    # SIPS default params (dipakai saat halaman SAP aktif)
    default_sips_date_from, default_sips_date_to,
    default_sips_selected_nama, default_sips_selected_bagian, default_teks_filter_sips,
    # Tanggal aktif SAP (untuk query PO by date_ordered)
    date_from=None, date_to=None,
):
    """
    Kumpulkan konteks gabungan SAP + SIPS.

    Saat di halaman SAP  : SAP pakai filter AKTIF, SIPS pakai filter DEFAULT
    Saat di halaman SIPS : SIPS pakai filter AKTIF, SAP pakai filter DEFAULT
    """

    # == Hitung fingerprint kondisi saat ini ==================================
    fp_sap_active   = filter_conditions + bagian_pr_cond + bagian_po_cond + str(date_from) + str(date_to)
    fp_sips_active  = _fingerprint_sips(sips_date_from, sips_date_to, sips_selected_nama, sips_selected_bagian)
    fp_now = f"{is_sips}|{fp_sap_active}|{fp_sips_active}"

    # == Jika filter tidak berubah, pakai cache session_state =================
    if (st.session_state.get("_ctx_fingerprint") == fp_now
            and "global_context" in st.session_state):
        return st.session_state["global_context"]

    # == Bangun konteks baru ===================================================
    if is_sips:
        # Halaman SIPS aktif → SIPS pakai filter AKTIF, SAP pakai filter DEFAULT (DIPERBAIKI)
        ctx_sips = _fetch_sips_context(
            load_data, sips_date_from, sips_date_to,
            sips_selected_nama, sips_selected_bagian,
            teks_filter_sips + " *(filter aktif dari sidebar)*"
        )
        ctx_sap = _fetch_sap_context(
            load_data, default_filter_conditions,
            default_bagian_pr_cond, default_bagian_po_cond,
            default_teks_filter_sap + " *(filter default - halaman SIPS sedang aktif)*",
            date_from=date_from, date_to=date_to
        )
    else:
        # Halaman SAP aktif → SAP pakai filter AKTIF, SIPS pakai filter DEFAULT (DIPERBAIKI)
        ctx_sap = _fetch_sap_context(
            load_data, filter_conditions,
            bagian_pr_cond, bagian_po_cond,
            teks_filter_sap + " *(filter aktif dari sidebar)*",
            date_from=date_from, date_to=date_to
        )
        ctx_sips = _fetch_sips_context(
            load_data, default_sips_date_from, default_sips_date_to,
            default_sips_selected_nama, default_sips_selected_bagian,
            default_teks_filter_sips + " *(filter default - halaman SAP sedang aktif)*"
        )

    header = (
        "# KONTEKS DATA DASHBOARD MONITORING\n"
        f"Diambil pada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Halaman aktif: {'SIPS' if is_sips else 'PR-PO SAP'}\n\n"
        "---\n"
        "# BAGIAN 1 - DATA PR-PO SAP\n"
    )
    separator = "\n---\n# BAGIAN 2 - DATA SIPS\n"

    full_context = header + ctx_sap + separator + ctx_sips

    # Simpan ke session_state
    st.session_state["global_context"]    = full_context
    st.session_state["_ctx_fingerprint"]  = fp_now

    return full_context

# =============================================================================
# INDEKS PENCARIAN HALAMAN (SITEMAP)
# =============================================================================
SEARCH_INDEX = [
    # --- EXECUTIVE SUMMARY ---
    {
        "page_title": "Executive Summary",
        "section": "KPI Pengadaan Barang",
        "items": [
            "Pengelolaan Anggaran Operasional", "Sinergi PI Group", "Produktivitas PR-PO",
            "Kecepatan Proses PO", "% Pengiriman Barang (GR/PO)", "Ketepatan Pengiriman Barang",
            "Pemenuhan SLA Pembebasan Barang", "Efisiensi Pengadaan (PO/OE)", "Pemenuhan Izin Impor",
            "Total SLA OTOBOS", "SLA - On Time", "SLA - On Budget", "SLA - On Spec"
        ],
        "keywords": ["kpi", "pengadaan", "barang", "summary"],
        "description": "Menampilkan kartu performa metrik utama seperti Sinergi, Produktivitas, Kecepatan, dan rincian SLA OTOBOS."
    },
    {
        "page_title": "Executive Summary",
        "section": "Laporan Pengadaan Barang",
        "items": [
            "Total PR", "Total PO", "PR On Progress", "% PR-PO",
            "Total Estimasi PR (OE)", "Total Nilai PO", "Efisiensi", "% Efisiensi",
            "Tren Realisasi Item PR-PO", "Tren Realisasi Nilai PR-PO"
        ],
        "keywords": ["laporan", "pengadaan", "volume", "nilai", "kumulatif", "summary"],
        "description": "Menampilkan grafik tren dan perbandingan antara total volume serta nilai PR vs PO secara keseluruhan."
    },
    {
        "page_title": "Executive Summary",
        "section": "Laporan Bagian",
        "items": [
            "On Budget", "On Time", "Lead Time (PR → PO)", "Efisiensi",
            "Tabel Kinerja Karyawan", "Tren Realisasi Item PR-PO per Bagian"
        ],
        "keywords": ["bagian", "alpata", "barum", "bb/bd/bp", "karyawan", "buyer", "summary"],
        "description": "Menampilkan laporan performa spesifik, tabel kinerja individu karyawan, dan grafik tren per Bagian."
    },
    # --- DASHBOARD MONITORING SAP ---
    {
        "page_title": "Dashboard Monitoring SAP",
        "section": "Key Performance Indicators",
        "items": [
            "Total PR", "Total PO", "Produktivitas PR-PO", "Total Savings", 
            "Total Estimasi PR", "Pengelolaan Anggaran Operasional", "Sinergi PI Group", 
            "Kecepatan Proses PO", "% Pengiriman Barang", "Ketepatan Pengiriman Barang", 
            "Efisiensi Pengadaan", "Pemenuhan Izin Impor"
        ],
        "keywords": ["kpi", "dashboard", "sap", "formula"],
        "description": "Kumpulan kartu metrik utama pengadaan barang dari data SAP beserta detail formula perhitungannya."
    },
    {
        "page_title": "Dashboard Monitoring SAP",
        "section": "PR Status by Department",
        "items": ["PR Status by Department Chart"],
        "keywords": ["grafik", "departemen", "belum diproses"],
        "description": "Grafik batang yang membandingkan jumlah PR yang sudah memiliki PO dan yang belum per departemen."
    },
    {
        "page_title": "Dashboard Monitoring SAP",
        "section": "Top 10 Vendors by PO Value",
        "items": ["Top 10 Vendors by PO Value Chart", "Filter Vendor B01, Investasi, Lainnya"],
        "keywords": ["grafik", "peringkat", "vendor", "supplier", "rupiah"],
        "description": "Peringkat 10 vendor dengan total nilai transaksi PO terbesar."
    },
    {
        "page_title": "Dashboard Monitoring SAP",
        "section": "PR-PO Creation Trend",
        "items": ["PR-PO Creation Trend Chart", "Kumulatif (Running Total)"],
        "keywords": ["grafik", "tren", "pembuatan", "bulan"],
        "description": "Grafik pergerakan jumlah pembuatan PR dan PO per bulan."
    },
    {
        "page_title": "Dashboard Monitoring SAP",
        "section": "Lead Time Distribution",
        "items": ["Lead Time Distribution Pie Chart"],
        "keywords": ["grafik", "pie", "waktu proses", "hari"],
        "description": "Grafik pie sebaran waktu yang dibutuhkan untuk memproses PR hingga menjadi PO."
    },
    {
        "page_title": "Dashboard Monitoring SAP",
        "section": "Top 10 PR Without PO (Pending)",
        "items": ["Tabel Top 10 PR Pending Tertua"],
        "keywords": ["tabel", "lama", "insight", "belum diproses"],
        "description": "Tabel rincian 10 PR tertua yang masih berstatus pending."
    },
    {
        "page_title": "Dashboard Monitoring SAP",
        "section": "Delivery Performance",
        "items": ["Delivery Performance Pie Chart"],
        "keywords": ["grafik", "pie", "tepat waktu", "terlambat", "in progress"],
        "description": "Grafik proporsi status pengiriman barang dari vendor."
    },
    {
        "page_title": "Dashboard Monitoring SAP",
        "section": "Material Category Value",
        "items": ["Material Category Value Bar Chart"],
        "keywords": ["grafik", "abc indicator", "analisis pareto"],
        "description": "Grafik total nilai belanja PO yang dikelompokkan berdasarkan kategori material ABC."
    },
    # --- DETAIL DATA SAP ---
    {
        "page_title": "Detailed PR-PO SAP Data",
        "section": "Detailed PR-PO SAP Data",
        "items": [
            "Search Data (No PR, No PO, Material, Vendor)", 
            "Tabel Rincian PR-PO", 
            "Download Data Excel (XLSX)"
        ],
        "keywords": [
            "tabel", "detail", "rincian", "raw data", "data mentah", "download", 
            "ekspor", "excel", "xlsx", "pencarian spesifik", "search", "sap"
        ],
        "description": "Tabel data mentah (raw data) seluruh transaksi PR dan PO dari SAP dengan fitur pencarian spesifik dan unduh ke format Excel."
    },
    # --- EVALUASI HARGA BARANG SAP ---
    {
        "page_title": "Evaluasi Harga Barang",
        "section": "KPI Harga Barang",
        "items": [
            "Total Material Unik", "Total OE", "Total Realisasi PO", 
            "Selisih OE vs Realisasi", "Item PO Melebihi OE", "Item Sesuai/Di Bawah OE"
        ],
        "keywords": ["kpi", "evaluasi", "harga", "oe", "estimasi", "realisasi", "selisih", "overspend", "under", "formula"],
        "description": "Kartu metrik yang menampilkan performa harga barang, membandingkan anggaran estimasi (OE) dengan realisasi PO."
    },
    {
        "page_title": "Evaluasi Harga Barang",
        "section": "OE vs Realisasi Harga PO",
        "items": ["OE vs Realisasi Harga PO (per Material)"],
        "keywords": ["grafik", "scatter chart", "oe vs realisasi", "harga", "material", "overspend"],
        "description": "Grafik scatter yang membandingkan nilai rata-rata estimasi (OE) dengan realisasi PO per material."
    },
    {
        "page_title": "Evaluasi Harga Barang",
        "section": "Top 10 Overspend & Efisiensi",
        "items": ["Top 10 Material: Overspend Terbesar", "Top 10 Material: Efisiensi Terbesar"],
        "keywords": ["grafik", "bar chart", "overspend", "rugi", "efisiensi", "hemat", "material", "harga"],
        "description": "Grafik material dengan selisih harga terburuk (overspend) dan penghematan terbaik (efisiensi) terhadap OE."
    },
    {
        "page_title": "Evaluasi Harga Barang",
        "section": "Variasi Harga & Tren Historis",
        "items": ["Variasi Harga Antar Vendor", "Tren Harga Historis per Material"],
        "keywords": ["grafik", "harga vendor", "perbandingan harga", "tren harga", "inflasi", "historis", "line chart"],
        "description": "Grafik perbandingan harga satuan material antar vendor dan tren pergerakan harganya dari waktu ke waktu."
    },
    {
        "page_title": "Evaluasi Harga Barang",
        "section": "Ranking Vendor Keseluruhan",
        "items": [
            "Perbandingan Vendor: Harga · Kecepatan · Reliabilitas", 
            "Peta Risiko Vendor: Nilai PO vs % Selisih terhadap OE", 
            "% Realisasi vs OE per Vendor", 
            "Tabel Lengkap Ranking Vendor"
        ],
        "keywords": ["tabel", "grafik", "ranking vendor", "kinerja vendor", "reliabilitas", "on time", "lead time", "kuadran", "risiko"],
        "description": "Evaluasi dan pemeringkatan vendor berdasarkan harga, kecepatan proses (lead time), dan ketepatan pengiriman."
    },
    {
        "page_title": "Evaluasi Harga Barang",
        "section": "Detail Evaluasi Harga per Material",
        "items": ["Detail Evaluasi Harga per Material", "Download Evaluasi Harga Excel (XLSX)"],
        "keywords": ["tabel", "detail", "rincian harga", "download", "excel", "status harga"],
        "description": "Tabel rincian evaluasi harga per material beserta status kewajarannya untuk diunduh."
    },
    # --- KINERJA PURCHASING GROUP ---
    {
        "page_title": "Kinerja Purchasing Group",
        "section": "KPI Ringkasan",
        "items": [
            "Total Item PR", "Total Item PO", "Total OE", "Total Realisasi PO", 
            "Efisiensi", "Avg Lead Time"
        ],
        "keywords": ["kpi", "kinerja", "pg", "ringkasan", "total pr", "total po", "oe", "efisiensi", "lead time"],
        "description": "Kartu metrik ringkasan performa pengadaan secara keseluruhan lintas Purchasing Group."
    },
    {
        "page_title": "Kinerja Purchasing Group",
        "section": "Overview per Purchasing Group",
        "items": [
            "Tabel Ringkasan per Purchasing Group", 
            "Perbandingan Nilai OE vs Realisasi PO", 
            "% Efisiensi per Purchasing Group", 
            "Rata-rata Lead Time per Purchasing Group", 
            "% Konversi PR → PO per Purchasing Group"
        ],
        "keywords": ["tabel", "grafik", "bar chart", "perbandingan oe", "efisiensi", "konversi", "rata-rata", "pg"],
        "description": "Tabel detail dan kumpulan grafik yang membandingkan performa (nilai, efisiensi, lead time, konversi) antar Purchasing Group."
    },
    {
        "page_title": "Kinerja Purchasing Group",
        "section": "Breakdown Metode Tender & Kecepatan",
        "items": [
            "KPI Kecepatan Proses", "Median Lead Time", "Rentang Lead Time", "On-Time (≤55 Hari)", "Terlambat (>55 Hari)",
            "Kontrak vs Non-Kontrak per Purchasing Group", "Distribusi Turn Around per Purchasing Group", 
            "Detail per Purchasing Group × Turn Around", "Lead Time: Kontrak vs Non-Kontrak", 
            "Tren Lead Time per Bulan", "Ringkasan Kecepatan per Purchasing Group × Jenis Tender",
            "Download Data Kontrak (XLSX)", "Download Ringkasan Kecepatan (XLSX)"
        ],
        "keywords": [
            "breakdown", "metode tender", "kontrak", "normal", "turn around", "ta", 
            "kecepatan", "lead time", "tren", "distribusi", "tabel", "download", "excel"
        ],
        "description": "Analisis mendalam mengenai kecepatan proses PO berdasarkan jenis tender (Kontrak/Normal) dan kegiatan pemeliharaan (Turn Around)."
    },
    # --- HALAMAN ALERT SAP ---
    {
        "page_title": "Halaman Alert SAP",
        "section": "PR Pending Mendekati Kadaluarsa (> 30 Hari)",
        "items": ["Tabel PR Pending Mendekati Kadaluarsa"],
        "keywords": ["alert", "warning", "pr pending", "kadaluarsa", "belum diproses", "30 hari", "anomali"],
        "description": "Menampilkan daftar PR yang belum diproses menjadi PO selama lebih dari 30 hari sejak dibuat."
    },
    {
        "page_title": "Halaman Alert SAP",
        "section": "PO Overdue (Melewati Delivery Date)",
        "items": ["Tabel PO Overdue (Melewati Delivery Date)"],
        "keywords": ["alert", "warning", "po overdue", "melewati", "delivery date", "jatuh tempo", "terlambat", "belum dikirim"],
        "description": "Menampilkan daftar PO yang tanggal pengirimannya sudah lewat namun barang belum diterima semua."
    },
    {
        "page_title": "Halaman Alert SAP",
        "section": "Rekap Aging PO (Belum Dikirim)",
        "items": ["Grafik Rekap Aging PO (Belum Dikirim)"],
        "keywords": ["grafik", "bar chart", "aging", "umur po", "belum dikirim", "rentang", "waktu"],
        "description": "Grafik batang jumlah PO yang belum dikirim berdasarkan kelompok rentang umurnya."
    },
    {
        "page_title": "Halaman Alert SAP",
        "section": "Monitoring PO Status",
        "items": [
            "Grafik Monitoring PO Status", 
            "Tabel Ringkasan PO Status", 
            "List PO per Status", 
            "Filter Status PO (A, B, Kosong)", 
            "Download List PO (XLSX)"
        ],
        "keywords": ["grafik", "tabel", "monitoring", "po status", "aktif", "closed", "selesai", "kosong", "download"],
        "description": "Visualisasi dan daftar rincian dokumen PO berdasarkan statusnya di sistem (Aktif / Closed)."
    },
    {
        "page_title": "Halaman Alert SAP",
        "section": "Grafik PO Terlambat",
        "items": [
            "Total Item PO Terlambat", 
            "Rata-rata Keterlambatan", 
            "Keterlambatan Terpanjang", 
            "Total Nilai PO Terlambat", 
            "Distribusi Keterlambatan (Bucket)", 
            "Top 10 Purchasing Group Terlambat", 
            "Top 10 Vendor Terlambat"
        ],
        "keywords": ["grafik", "kpi", "terlambat", "distribusi", "peringkat vendor", "peringkat pg", "late", "overdue"],
        "description": "Dasbor khusus yang menganalisis PO terlambat berdasarkan rentang waktu, Purchasing Group, dan Vendor."
    },
    {
        "page_title": "Halaman Alert SAP",
        "section": "PO Outstanding (Belum GR, Belum Jatuh Tempo)",
        "items": [
            "Total Item PO Outstanding", 
            "Kritis (≤ 7 Hari)", 
            "Perlu Pantau (8–30 Hari)", 
            "Total Nilai Outstanding", 
            "Filter Sisa Hari", 
            "Tabel PO Outstanding", 
            "Download PO Outstanding (XLSX)"
        ],
        "keywords": ["tabel", "kpi", "po outstanding", "belum gr", "belum jatuh tempo", "kritis", "pantau", "sisa hari"],
        "description": "Daftar PO yang masih dalam proses pengiriman (belum jatuh tempo) yang perlu dipantau untuk mencegah keterlambatan."
    },
    # --- DASHBOARD MONITORING SIPS ---
    {
        "page_title": "Dashboard Monitoring SIPS",
        "section": "SIPS Key Performance Indicators",
        "items": [
            "Total PR", "Total PO", "PO/PR", "Rata-rata PR-PO", "SLA On Time", 
            "OE Proses PO", "OE Closed", "Total OE", "PO Proses PO", "PO Closed", 
            "Efisiensi %", "Efisiensi Rp", "% On Budget"
        ],
        "keywords": ["kpi", "sips", "dashboard", "formula", "oe", "efisiensi", "on budget", "po/pr", "rupiah"],
        "description": "Kumpulan kartu metrik utama pengadaan barang dari data SIPS (Sistem Informasi Pengadaan Barang dan Jasa)."
    },
    {
        "page_title": "Dashboard Monitoring SIPS",
        "section": "Pemenuhan SLA berdasarkan Prioritas",
        "items": [
            "% On Time SLA", "% Kontribusi Normal", "% Kontribusi TA", 
            "% Kontribusi Investasi", "% Kontribusi Urgent", "% Kontribusi Emergency"
        ],
        "keywords": ["kpi", "sla", "prioritas", "urgent", "emergency", "ta", "investasi", "tepat waktu"],
        "description": "Kartu metrik kontribusi persentase dari PO dengan prioritas tertentu yang on-time terhadap total PO keseluruhan."
    },
    {
        "page_title": "Dashboard Monitoring SIPS",
        "section": "Pipeline & Trend PR-PO SIPS",
        "items": ["Pipeline & Trend PR-PO SIPS", "Distribusi Status PR SIPS"],
        "keywords": ["grafik", "pie chart", "line chart", "trend", "status", "kumulatif", "distribusi", "aktif", "closed"],
        "description": "Grafik pergerakan jumlah pembuatan PR dan PO SIPS per bulan dan distribusi status akhirnya."
    },
    {
        "page_title": "Dashboard Monitoring SIPS",
        "section": "Performa SLA per Karyawan",
        "items": ["Performa SLA per Karyawan", "Distribusi Waktu PR → PO"],
        "keywords": ["grafik", "bar chart", "histogram", "sla", "karyawan", "buyer", "lead time", "waktu proses", "kecepatan"],
        "description": "Grafik pencapaian SLA tepat waktu per karyawan dan histogram persebaran lama proses PR ke PO."
    },
    {
        "page_title": "Dashboard Monitoring SIPS",
        "section": "Beban Kerja (Volume Dokumen) per Karyawan",
        "items": ["Beban Kerja (Volume Dokumen) per Karyawan"],
        "keywords": ["grafik", "bar chart", "beban kerja", "karyawan", "buyer", "volume", "dokumen", "pr", "po"],
        "description": "Grafik jumlah dokumen PR yang ditangani masing-masing karyawan beserta persentase yang berhasil dikonversi ke PO."
    },
    {
        "page_title": "Dashboard Monitoring SIPS",
        "section": "Proporsi PO Kontrak vs Non-Kontrak per Karyawan",
        "items": ["Proporsi PO Kontrak vs Non-Kontrak per Karyawan"],
        "keywords": ["grafik", "stacked bar", "kontrak", "non-kontrak", "outline agreement", "karyawan", "buyer"],
        "description": "Grafik perbandingan item PO yang menggunakan kontrak payung (Outline Agreement) dengan tender normal per karyawan."
    },
    {
        "page_title": "Dashboard Monitoring SIPS",
        "section": "Perbandingan Nilai OE vs PO per Karyawan",
        "items": ["Perbandingan Nilai OE vs PO per Karyawan", "Download Semua Data Chart (XLSX)"],
        "keywords": ["grafik", "grouped bar", "oe vs po", "nilai", "efisiensi", "penghematan", "karyawan", "buyer", "rupiah", "download"],
        "description": "Grafik perbandingan total nilai anggaran (OE) dengan realisasi aktual (PO) untuk melihat nilai penghematan tiap karyawan."
    },
    # --- HALAMAN DETAIL SIPS ---
    {
        "page_title": "Detailed SIPS Data",
        "section": "Detailed SIPS Data",
        "items": [
            "Search Data SIPS (No PR, No PO, Short Text, Nama)", 
            "Tabel Rincian Data SIPS", 
            "Download Data SIPS Excel (XLSX)"
        ],
        "keywords": [
            "tabel", "detail", "rincian", "raw data", "data mentah", "download", 
            "ekspor", "excel", "xlsx", "pencarian spesifik", "search", "sips", "karyawan"
        ],
        "description": "Tabel data mentah (raw data) seluruh log pengadaan dari SIPS dengan fitur pencarian spesifik dan unduh ke format Excel."
    },
    # --- ANALISIS WAKTU PROSES SIPS ---
    {
        "page_title": "Analisis Waktu Proses SIPS",
        "section": "Ringkasan Waktu",
        "items": [
            "Rata-rata PR-PO", "Rata-rata Realisasi SLA", "Waktu Pra-Disposisi",
            "Rata-rata End-to-End", "Rata-rata SLA Headroom", "% On Time SLA"
        ],
        "keywords": ["kpi", "waktu", "sips", "sla", "headroom", "pra-disposisi", "end-to-end", "formula"],
        "description": "Kartu metrik ringkasan kinerja waktu proses pengadaan mulai dari pembuatan PR hingga terbitnya PO."
    },
    {
        "page_title": "Analisis Waktu Proses SIPS",
        "section": "Dekomposisi Waktu per Nama",
        "items": ["Dekomposisi Waktu per Nama Chart"],
        "keywords": ["grafik", "stacked bar", "dekomposisi", "waktu", "karyawan", "buyer", "selisih"],
        "description": "Grafik yang memecah total waktu PR-PO menjadi waktu Realisasi SLA dan selisih waktu di luar SLA per karyawan."
    },
    {
        "page_title": "Analisis Waktu Proses SIPS",
        "section": "Pemenuhan SLA per Jenis Pengadaan",
        "items": ["% On Time per Jenis Pengadaan", "Rata-rata Realisasi vs Standard SLA (target)"],
        "keywords": ["grafik", "bar chart", "jenis pengadaan", "kontrak", "non-agreement", "prioritas"],
        "description": "Perbandingan pencapaian SLA berdasarkan jenis kontrak (Agreement/Non-Agreement) dan skala prioritas."
    },
    {
        "page_title": "Analisis Waktu Proses SIPS",
        "section": "SLA Headroom per Nama",
        "items": ["SLA Headroom per Nama Chart"],
        "keywords": ["grafik", "bar chart", "sisa waktu", "headroom", "karyawan", "buyer"],
        "description": "Grafik rata-rata sisa waktu atau selisih antara target SLA dengan realisasi per karyawan."
    },
    {
        "page_title": "Analisis Waktu Proses SIPS",
        "section": "Tren Waktu per Bulan",
        "items": ["Tren Waktu per Bulan Chart"],
        "keywords": ["grafik", "line chart", "combo chart", "tren", "waktu proses", "kecepatan", "bulan"],
        "description": "Grafik pergerakan kecepatan pengadaan dan persentase tepat waktu (On-Time SLA) dari bulan ke bulan."
    },
    {
        "page_title": "Analisis Waktu Proses SIPS",
        "section": "Distribusi Waktu",
        "items": ["Distribusi PR-PO", "Distribusi Realisasi SLA"],
        "keywords": ["grafik", "histogram", "distribusi", "persebaran", "outlier"],
        "description": "Histogram persebaran waktu proses pengadaan untuk mendeteksi anomali atau dokumen yang memakan waktu sangat lama (outlier)."
    },
    {
        "page_title": "Analisis Waktu Proses SIPS",
        "section": "Waktu per Prioritas",
        "items": ["Rata-rata PR-PO & Realisasi SLA per Prioritas", "% On Time per Prioritas"],
        "keywords": ["grafik", "prioritas", "urgent", "emergency", "ta", "investasi", "normal"],
        "description": "Perbandingan kecepatan proses pengadaan dan ketepatan waktu berdasarkan tingkat prioritas dokumen."
    },
    {
        "page_title": "Analisis Waktu Proses SIPS",
        "section": "Waktu Realisasi SLA per Purchasing Group",
        "items": ["Waktu Realisasi SLA per Purchasing Group Chart"],
        "keywords": ["grafik", "bar chart", "waktu", "pg", "purchasing group"],
        "description": "Rata-rata waktu penyelesaian dokumen pengadaan (Realisasi SLA) oleh tiap-tiap Purchasing Group."
    },
    {
        "page_title": "Analisis Waktu Proses SIPS",
        "section": "Resume OTOBOS per Individu",
        "items": ["Tabel Resume OTOBOS per Individu", "Download Resume OTOBOS sebagai XLSX"],
        "keywords": ["tabel", "resume", "otobos", "karyawan", "buyer", "jenis kontrak", "download", "excel"],
        "description": "Tabel rincian ketepatan waktu tiap karyawan yang dibreakdown berdasarkan jenis kontrak beserta opsi untuk diunduh."
    },
    # --- HALAMAN ALERT SIPS ---
    {
        "page_title": "Halaman Alert SIPS",
        "section": "PR Pending Mendekati Kadaluarsa (> 30 Hari)",
        "items": [
            "Tabel PR Pending Mendekati Kadaluarsa", 
            "Download PR Pending SIPS (XLSX)"
        ],
        "keywords": ["alert", "warning", "pr pending", "kadaluarsa", "sips", "30 hari", "belum diproses", "tabel"],
        "description": "Menampilkan daftar PR SIPS yang belum diproses menjadi PO selama lebih dari 30 hari sejak tanggal disposisi buyer."
    },
    {
        "page_title": "Halaman Alert SIPS",
        "section": "Rekap Aging PR Pending (Open)",
        "items": ["Grafik Rekap Aging PR Pending (Open)"],
        "keywords": ["grafik", "bar chart", "aging", "umur pr", "belum diproses", "rentang", "waktu", "sips", "open"],
        "description": "Grafik batang jumlah PR SIPS yang belum diproses berdasarkan kelompok rentang umurnya (0-15 hari, 16-30 hari, dst)."
    },
    {
        "page_title": "Halaman Alert SIPS",
        "section": "Beban Pending per Karyawan",
        "items": ["Grafik Beban Pending per Karyawan", "Overdue SLA"],
        "keywords": ["grafik", "bar chart", "beban kerja", "pending", "karyawan", "buyer", "overdue", "sla", "sips"],
        "description": "Grafik jumlah PR pending per buyer yang dibedakan warnanya berdasarkan status aman (kuning) atau sudah melebihi batas SLA (merah)."
    },
    {
        "page_title": "Halaman Alert SIPS",
        "section": "Monitoring Status PR SIPS",
        "items": [
            "Grafik Monitoring Status PR SIPS", 
            "Tabel Ringkasan Status PR SIPS"
        ],
        "keywords": ["grafik", "tabel", "monitoring", "status pr", "open", "proses po", "closed", "oe", "sips"],
        "description": "Visualisasi dan tabel ringkasan distribusi jumlah PR beserta total nilai anggarannya (OE) berdasarkan status dokumen SIPS."
    },
    # --- DASHBOARD INKLARING BARANG IMPOR ---
    {
        "page_title": "Dashboard Inklaring",
        "section": "Key Performance Indicators",
        "items": [
            "Total PIB", "PIB Selesai", "Kinerja SLA EPP", "Rata-rata Bebas (Hari)", 
            "Rata-rata Waiting Time", "Rata-rata Waktu Proses Bongkar", "Total Biaya"
        ],
        "keywords": ["kpi", "inklaring", "impor", "pib", "sla epp", "biaya", "pajak", "bea masuk", "bongkar", "waiting time"],
        "description": "Kartu metrik ringkasan kinerja inklaring impor, termasuk status penyelesaian PIB, pencapaian SLA EPP, dan total biaya pajak."
    },
    {
        "page_title": "Dashboard Inklaring",
        "section": "Proporsi Keterangan Jalur",
        "items": ["Proporsi Keterangan Jalur Pie Chart"],
        "keywords": ["grafik", "pie chart", "jalur merah", "jalur hijau", "spjm", "pabean", "impor"],
        "description": "Grafik distribusi jumlah dokumen impor berdasarkan jalur kepabeanan (Merah vs Hijau)."
    },
    {
        "page_title": "Dashboard Inklaring",
        "section": "Total Volume Impor per Komoditi",
        "items": ["Total Volume Impor per Komoditi Bar Chart"],
        "keywords": ["grafik", "bar chart", "volume", "komoditi", "impor", "metric ton", "mt", "quantity"],
        "description": "Grafik batang horizontal yang menunjukkan total volume impor (dalam Metric Ton) untuk setiap jenis komoditi."
    },
    {
        "page_title": "Dashboard Inklaring",
        "section": "Peta Asal Negara Impor",
        "items": ["Peta Asal Negara Impor Geo Map"],
        "keywords": ["peta", "map", "negara", "asal", "geografis", "impor", "distribusi", "dunia"],
        "description": "Peta geografis dunia yang menampilkan persebaran negara asal barang impor beserta proporsi frekuensinya."
    },
    {
        "page_title": "Dashboard Inklaring",
        "section": "Top 10 PIB dengan Total Biaya Terbesar",
        "items": ["Top 10 PIB dengan Total Biaya Terbesar Chart"],
        "keywords": ["grafik", "stacked bar", "biaya", "pajak", "bea masuk", "ppn", "pph", "terbesar", "kapal", "aju", "rupiah"],
        "description": "Grafik 10 dokumen kapal/impor dengan nilai pengeluaran pajak terbesar, dirincikan berdasarkan komposisinya (Bea Masuk, PPN, PPH)."
    },
    {
        "page_title": "Dashboard Inklaring",
        "section": "Tabel Rincian SLA per Kapal",
        "items": ["Tabel Rincian SLA per Kapal", "Download Rincian SLA per Kapal (XLSX)"],
        "keywords": ["tabel", "rincian", "sla", "kapal", "aju", "jalur", "komoditi", "download", "excel"],
        "description": "Tabel detail pencapaian waktu dan SLA Inklaring untuk masing-masing kapal/dokumen impor beserta opsi unduh ke format Excel."
    },
    # --- HALAMAN DETAIL INKLARING ---
    {
        "page_title": "Detailed Inklaring Data",
        "section": "Detailed Inklaring Data",
        "items": [
            "Search Data Inklaring (No AJU, SAP, Nama Kapal, Komoditi, Pemasok)", 
            "Tabel Rincian Data Inklaring", 
            "Download Data Inklaring Excel (XLSX)"
        ],
        "keywords": [
            "tabel", "detail", "rincian", "raw data", "data mentah", "download", 
            "ekspor", "excel", "xlsx", "pencarian spesifik", "search", "inklaring", 
            "impor", "pib", "aju", "kapal", "komoditi", "pemasok"
        ],
        "description": "Tabel data mentah (raw data) seluruh dokumen inklaring impor barang dengan fitur pencarian spesifik dan unduh ke format Excel."
    },
    # --- ANALISIS WAKTU PROSES INKLARING ---
    {
        "page_title": "Analisis Waktu Proses Inklaring",
        "section": "Key Performance Indicators Waktu Inklaring",
        "items": [
            "Rata-rata Bebas (Hari)", 
            "Rata-rata Waiting Time", 
            "Rata-rata Waktu Proses Bongkar"
        ],
        "keywords": ["kpi", "inklaring", "waktu", "hari", "bebas", "waiting time", "bongkar", "rata-rata"],
        "description": "Kartu metrik yang menampilkan rata-rata durasi waktu tunggu, waktu bongkar, dan waktu bebas SPPB untuk dokumen inklaring impor."
    },
    {
        "page_title": "Analisis Waktu Proses Inklaring",
        "section": "Bebas Hari per Kapal (Terlama)",
        "items": ["Grafik Bebas Hari per Kapal (Terlama)"],
        "keywords": ["grafik", "bar chart", "bebas hari", "terlama", "sppb", "kapal", "aju", "impor"],
        "description": "Grafik batang yang menampilkan 15 kapal dengan durasi waktu bebas (dari selesai bongkar hingga SPPB terbit) terlama."
    },
    {
        "page_title": "Analisis Waktu Proses Inklaring",
        "section": "Waiting Time per Kapal (Terlama)",
        "items": ["Grafik Waiting Time per Kapal (Terlama)"],
        "keywords": ["grafik", "bar chart", "waiting time", "waktu tunggu", "terlama", "kapal", "aju", "impor", "pib"],
        "description": "Grafik batang yang menampilkan 15 kapal dengan waktu tunggu (waiting time) terlama sejak PIB diterbitkan hingga mulai bongkar."
    },
    {
        "page_title": "Analisis Waktu Proses Inklaring",
        "section": "Waktu Proses Bongkar per Kapal (Terlama)",
        "items": ["Grafik Waktu Proses Bongkar per Kapal (Terlama)"],
        "keywords": ["grafik", "bar chart", "proses bongkar", "lama bongkar", "terlama", "kapal", "aju", "impor"],
        "description": "Grafik batang yang menampilkan 15 kapal dengan proses operasional bongkar muat paling lama."
    },
    {
        "page_title": "Analisis Waktu Proses Inklaring",
        "section": "Timeline Operasional (Waiting Time & Bongkar)",
        "items": ["Gantt Chart Timeline Operasional"],
        "keywords": ["grafik", "gantt chart", "timeline", "jadwal", "waktu", "perjalanan", "kapal", "aju", "impor"],
        "description": "Gantt chart yang memvisualisasikan garis waktu operasional setiap kapal, mulai dari waktu PIB terbit, durasi menunggu, hingga selesai bongkar."
    }
]