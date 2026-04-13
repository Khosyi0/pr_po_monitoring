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


def init_settings_table():
    """Membuat tabel app_settings jika belum ada."""
    try:
        engine = get_db_engine()
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    setting_key VARCHAR(50) PRIMARY KEY,
                    setting_value VARCHAR(255)
                )
            """))
    except Exception:
        pass

@st.cache_data(ttl=86400)
def get_setting(key: str, default_value: str = "") -> str:
    """Mengambil nilai pengaturan dari database."""
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            res = conn.execute(text("SELECT setting_value FROM app_settings WHERE setting_key = :k"), {"k": key}).fetchone()
            if res:
                return res[0]
    except Exception:
        init_settings_table()
    return default_value

def set_setting(key: str, value: str):
    """Menyimpan nilai pengaturan ke database."""
    init_settings_table()
    try:
        engine = get_db_engine()
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO app_settings (setting_key, setting_value) 
                VALUES (:k, :v) 
                ON CONFLICT (setting_key) DO UPDATE SET setting_value = EXCLUDED.setting_value
            """), {"k": key, "v": str(value)})
                try:
            get_setting.clear()
        except Exception:
            pass
    except Exception as e:
        st.error(f"Gagal menyimpan pengaturan: {e}")

