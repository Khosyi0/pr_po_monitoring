"""
utils.py — Fungsi pembantu: format uang, CSS, dan filter kondisi SQL
"""

import streamlit as st
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# FORMAT RUPIAH
# ─────────────────────────────────────────────────────────────────────────────

def format_idr(x) -> str:
    """Format angka menjadi string Rupiah dengan suffix T/M/Jt."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "Rp 0"

    if abs(x) >= 1e12:
        val, suffix = x / 1e12, "T"
    elif abs(x) >= 1e9:
        val, suffix = x / 1e9, "M"
    elif abs(x) >= 1e6:
        val, suffix = x / 1e6, "Jt"
    else:
        formatted = f"{x:,.0f}".replace(',', '.')
        return f"Rp {formatted}"

    formatted = f"{val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    return f"Rp {formatted} {suffix}"


def format_idr_short(x) -> str:
    """Format angka ringkas untuk label chart (1 desimal)."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "0"

    if abs(x) >= 1e12:
        val, suffix = x / 1e12, "T"
    elif abs(x) >= 1e9:
        val, suffix = x / 1e9, "M"
    elif abs(x) >= 1e6:
        val, suffix = x / 1e6, "Jt"
    else:
        return f"{x:,.0f}".replace(',', '.')

    formatted = f"{val:,.1f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    return f"{formatted} {suffix}"


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────────────────────────────────────

def inject_css():
    """Inject custom CSS adaptive light/dark mode ke halaman."""
    st.markdown("""
<style>
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] div {
        color: var(--text-color);
    }
    h1 {
        color: #1f77b4;
    }
    .stMultiSelect, .stDateInput {
        background-color: transparent;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# FILTER SQL BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_filter_conditions(
    date_from, date_to,
    selected_department, exclude_dept,
    selected_p_group, exclude_purchasing_group
) -> str:
    """Bangun string kondisi WHERE untuk query SQL dari nilai filter sidebar."""
    conditions = [
        f"tgl_create_pr >= '{date_from}'",
        f"tgl_create_pr <= '{date_to}'"
    ]

    if selected_department and 'All' not in selected_department:
        dept_list = "','".join(selected_department)
        if exclude_dept:
            conditions.append(f"(department_code NOT IN ('{dept_list}') OR department_code IS NULL)")
        else:
            conditions.append(f"department_code IN ('{dept_list}')")

    if selected_p_group and 'All' not in selected_p_group:
        pg_list = "','".join(selected_p_group)
        if exclude_purchasing_group:
            conditions.append(f"(purchasing_group NOT IN ('{pg_list}') OR purchasing_group IS NULL)")
        else:
            conditions.append(f"purchasing_group IN ('{pg_list}')")

    return " AND ".join(conditions)


def build_bagian_conditions(selected_bagian, exclude_bagian) -> tuple[str, str]:
    """Kembalikan tuple (bagian_pr_cond, bagian_po_cond) untuk filter bagian."""
    if 'All' not in selected_bagian and selected_bagian:
        bagian_list = "','".join(selected_bagian)
        if exclude_bagian:
            pr = f"(bagian_pr NOT IN ('{bagian_list}') OR bagian_pr IS NULL)"
            po = f"(bagian_po NOT IN ('{bagian_list}') OR bagian_po IS NULL)"
        else:
            pr = f"bagian_pr IN ('{bagian_list}')"
            po = f"bagian_po IN ('{bagian_list}')"
        return pr, po
    return "1=1", "1=1"
