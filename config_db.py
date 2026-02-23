"""
config_db.py — Konfigurasi dan koneksi database
"""

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text


@st.cache_resource
def get_db_engine():
    """Create database connection (cached).

    Streamlit Cloud → isi di Settings > Secrets:
        [database]
        url = "postgresql://user:password@host/dbname?sslmode=require"

    Lokal → isi variabel DB_* di bawah (fallback jika Secrets tidak ada).
    """
    try:
        conn_url = st.secrets["database"]["url"]
    except (KeyError, FileNotFoundError):
        DB_HOST     = 'localhost'
        DB_PORT     = '5432'
        DB_NAME     = 'pr_po_monitoring'
        DB_USER     = 'postgres'
        DB_PASSWORD = 'Hx4Khos2'
        conn_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    # Neon: paksa search_path = public di setiap koneksi
    if "options=" not in conn_url:
        sep = "&" if "?" in conn_url else "?"
        conn_url += f"{sep}options=-csearch_path%3Dpublic"

    engine = create_engine(
        conn_url,
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=5,
        connect_args={"connect_timeout": 10}
    )
    return engine


@st.cache_data(ttl=300)
def load_data(query: str) -> pd.DataFrame:
    """Eksekusi query SQL dan kembalikan sebagai DataFrame (di-cache 5 menit)."""
    engine = get_db_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
    return df
