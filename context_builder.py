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


# ─────────────────────────────────────────────────────────────────────────────
# FINGERPRINT FILTER: untuk mendeteksi perubahan filter
# ─────────────────────────────────────────────────────────────────────────────

def _fingerprint_sap(date_from, date_to, selected_department,
                     exclude_dept, selected_p_group,
                     exclude_purchasing_group, selected_bagian, exclude_bagian) -> str:
    return (f"{date_from}|{date_to}|{sorted(selected_department)}|{exclude_dept}"
            f"|{sorted(selected_p_group)}|{exclude_purchasing_group}"
            f"|{sorted(selected_bagian)}|{exclude_bagian}")


def _fingerprint_sips(date_from, date_to, selected_nama, selected_bagian) -> str:
    return f"{date_from}|{date_to}|{sorted(selected_nama)}|{sorted(selected_bagian)}"


# ─────────────────────────────────────────────────────────────────────────────
# QUERY KPI SAP: hanya agregat
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# QUERY KPI SIPS: hanya agregat
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# FUNGSI UTAMA: dipanggil dari app.py setiap render
# ─────────────────────────────────────────────────────────────────────────────

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

    # ── Hitung fingerprint kondisi saat ini ──────────────────────────────────
    fp_sap_active   = filter_conditions + bagian_pr_cond + bagian_po_cond + str(date_from) + str(date_to)
    fp_sips_active  = _fingerprint_sips(sips_date_from, sips_date_to, sips_selected_nama, sips_selected_bagian)
    fp_now = f"{is_sips}|{fp_sap_active}|{fp_sips_active}"

    # ── Jika filter tidak berubah, pakai cache session_state ─────────────────
    if (st.session_state.get("_ctx_fingerprint") == fp_now
            and "global_context" in st.session_state):
        return st.session_state["global_context"]

    # ── Bangun konteks baru ───────────────────────────────────────────────────
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