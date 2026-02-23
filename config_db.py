"""
config_db.py — Konfigurasi dan koneksi database
"""

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

@st.cache_resource
def get_db_engine():
    """Create database connection (cached)."""
    try:
        # Mengambil konfigurasi dari st.secrets (berlaku untuk lokal dan cloud)
        db_config = st.secrets["postgres"]
        conn_url = (
            f"postgresql://{db_config['user']}:{db_config['password']}"
            f"@{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
        )
    except KeyError:
        st.error("Konfigurasi database tidak ditemukan! Pastikan rahasia (secrets) sudah diatur.")
        st.stop()

    # Neon: paksa search_path = public di setiap koneksi
    if "options=" not in conn_url:
        sep = "&" if "?" in conn_url else "?"
        conn_url += f"{sep}options=-csearch_path%3Dpublic"

    # Membuat engine SQLAlchemy
    engine = create_engine(
        conn_url,
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=5,
        connect_args={"connect_timeout": 30}
    )
    return engine

@st.cache_data(ttl=300)
def load_data(query: str) -> pd.DataFrame:
    """Eksekusi query SQL dan kembalikan sebagai DataFrame (di-cache 5 menit)."""
    engine = get_db_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
    return df