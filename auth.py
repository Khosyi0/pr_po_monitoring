"""
auth.py - Module autentikasi untuk Monitoring Dashboard

Sistem:
  - Semua user login dengan username + password
  - Role 'admin'  → akses penuh (termasuk CRUD di halaman Isu)
  - Role 'viewer' → akses baca saja
  - Credentials disimpan di tabel melati_users (PostgreSQL)
  - Password di-hash dengan bcrypt via pgcrypto

Cara pakai di app.py:
    from auth import render_login, get_current_user, is_admin, logout

    if not render_login():   # returns True jika sudah authenticated
        st.stop()

    user = get_current_user()  # dict: {id, username, nama_lengkap, role, bagian}
    if is_admin():
        st.write("Halo, Admin!")
"""

import streamlit as st
from sqlalchemy import text
import base64
import os

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS DB
# ─────────────────────────────────────────────────────────────────────────────

def _get_engine():
    """Ambil engine dari config_db (sudah cached)."""
    from config_db import get_db_engine
    return get_db_engine()


def _ensure_table():
    """Buat tabel melati_users & aktifkan pgcrypto jika belum ada."""
    sql = """
    CREATE EXTENSION IF NOT EXISTS pgcrypto;

    CREATE TABLE IF NOT EXISTS melati_users (
        id            SERIAL PRIMARY KEY,
        username      VARCHAR(50)  NOT NULL UNIQUE,
        password_hash TEXT         NOT NULL,
        nama_lengkap  VARCHAR(100) NOT NULL,
        role          VARCHAR(20)  NOT NULL DEFAULT 'viewer',
        bagian        VARCHAR(50),
        aktif         BOOLEAN      NOT NULL DEFAULT TRUE,
        created_at    TIMESTAMP    DEFAULT NOW(),
        last_login    TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_users_username ON melati_users (username);
    """
    try:
        with _get_engine().begin() as conn:
            conn.execute(text(sql))
    except Exception:
        pass  # Tabel mungkin sudah ada, lanjutkan saja


def _verify_password(username: str, password: str) -> dict | None:
    """
    Cek username + password.
    Kembalikan dict user jika valid & aktif, None jika tidak.
    Menggunakan fungsi pgcrypto: crypt(password, password_hash)
    """
    try:
        query = text("""
            SELECT id, username, nama_lengkap, role, bagian, aktif
            FROM melati_users
            WHERE username = :uname
              AND aktif    = TRUE
              AND password_hash = crypt(:pwd, password_hash)
        """)
        with _get_engine().connect() as conn:
            result = conn.execute(query, {"uname": username.strip().lower(),
                                          "pwd":   password})
            row = result.fetchone()
        if row is None:
            return None
        return {
            "id":           row[0],
            "username":     row[1],
            "nama_lengkap": row[2],
            "role":         row[3],
            "bagian":       row[4],
        }
    except Exception as e:
        st.error(f"Error autentikasi: {e}")
        return None


def _update_last_login(user_id: int):
    """Catat waktu login terakhir."""
    try:
        with _get_engine().begin() as conn:
            conn.execute(
                text("UPDATE melati_users SET last_login = NOW() WHERE id = :uid"),
                {"uid": user_id}
            )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# ICON HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _load_icon_b64(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None

_ICON_PATH = "assets/Dashboard_icon.png"
_icon_b64  = _load_icon_b64(_ICON_PATH)


# ─────────────────────────────────────────────────────────────────────────────
# HALAMAN LOGIN
# ─────────────────────────────────────────────────────────────────────────────

def render_login() -> bool:
    """
    Tampilkan halaman login jika belum authenticated.
    Kembalikan True jika user sudah login, False jika belum.
    """
    # Inisialisasi session state auth
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "current_user" not in st.session_state:
        st.session_state.current_user = None

    if st.session_state.authenticated and st.session_state.current_user:
        return True

    # ── CSS halaman login ─────────────────────────────────────────────────────
    st.markdown("""
        <style>
            [data-testid="stSidebar"], 
            [data-testid="stSidebarNav"], 
            [data-testid="stToolbar"] { display: none; }

            /* Spinner dots animasi saat proses login */
            @keyframes _isu_bounce {
                0%, 80%, 100% { transform: scale(0); opacity: 0.3; }
                40%            { transform: scale(1); opacity: 1;   }
            }
            .login-dots {
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 8px;
                padding: 10px 0 6px 0;
            }
            .login-dot {
                width: 10px; height: 10px;
                border-radius: 50%;
                background: #ff4b4b;
                animation: _isu_bounce 1.4s ease-in-out infinite both;
            }
            .login-dot:nth-child(1) { animation-delay: -0.32s; }
            .login-dot:nth-child(2) { animation-delay: -0.16s; }
            .login-dot:nth-child(3) { animation-delay: 0s;     }
            .login-msg {
                text-align: center;
                font-size: 13px;
                opacity: 0.55;
                margin: 0 0 12px 0;
                font-weight: 600;
            }
            
            /* Styling untuk form bawaan Streamlit agar terlihat seperti kartu */
            [data-testid="stForm"] {
                border-radius: 16px !important;
                padding: 32px 28px 24px 28px !important;
                box-shadow: 0 4px 24px rgba(0,0,0,0.08) !important;
                border: 1px solid rgba(128,128,128,0.18) !important;
                background: var(--secondary-background-color) !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # ── Layout terpusat ───────────────────────────────────────────────────────
    _, col_m, _ = st.columns([1, 1.6, 1])
    with col_m:
        # Logo / icon
        if _icon_b64:
            st.markdown(
                f"<div style='text-align:center;margin-bottom:4px;'>"
                f"<img src='data:image/png;base64,{_icon_b64}' "
                f"width='88' height='88' style='border-radius:18px;'></div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                "<div style='text-align:center;font-size:56px;margin-bottom:8px;'>📊</div>",
                unsafe_allow_html=True
            )

        st.markdown("""
            <div style='text-align:center;margin-bottom:16px;'>
                <h2 style='font-size:22px;margin:0 0 4px 20px;'>Monitoring Dashboard</h2>
                <p style='color:#888;font-size:13px;margin:0;'>Pengadaan Barang</p>
            </div>
        """, unsafe_allow_html=True)

        # Cek status loading
        _is_loading = st.session_state.get("_login_loading", False)

        # ── Form Login (Dinamis: Normal vs Loading) ───────────────────────────
        with st.form("login_form", clear_on_submit=False):
            
            # Jika loading, tampilkan animasi di bagian paling atas form
            if _is_loading:
                st.markdown("""
                    <div class="login-dots">
                        <div class="login-dot"></div>
                        <div class="login-dot"></div>
                        <div class="login-dot"></div>
                    </div>
                    <p class="login-msg">Memverifikasi akun...</p>
                """, unsafe_allow_html=True)

            st.markdown(
                "<p style='font-size:13px;font-weight:600;margin:0 0 6px 0;opacity:0.7;'>"
                "USERNAME</p>",
                unsafe_allow_html=True
            )
            # Kolom akan ter-disable (abu-abu) jika sedang loading
            username_input = st.text_input(
                "Username",
                value=st.session_state.get("_login_username", ""),
                placeholder="Masukkan username...",
                label_visibility="collapsed",
                autocomplete="username",
                disabled=_is_loading 
            )

            st.markdown(
                "<p style='font-size:13px;font-weight:600;margin:12px 0 6px 0;opacity:0.7;'>"
                "PASSWORD</p>",
                unsafe_allow_html=True
            )
            password_input = st.text_input(
                "Password",
                type="password",
                value=st.session_state.get("_login_password", ""),
                placeholder="Masukkan password...",
                label_visibility="collapsed",
                autocomplete="current-password",
                disabled=_is_loading
            )

            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button(
                "Masuk", use_container_width=True, type="primary", disabled=_is_loading
            )

        # ── Proses Verifikasi (Berjalan saat _is_loading True) ────────────────
        if _is_loading:
            _ensure_table()
            _user = _verify_password(st.session_state["_login_username"], st.session_state["_login_password"])
            
            # Reset status loading
            st.session_state["_login_loading"] = False
            
            if _user:
                st.session_state.authenticated = True
                st.session_state.current_user  = _user
                _update_last_login(_user["id"])
            else:
                st.session_state["_login_error"] = "Username atau password salah, atau akun tidak aktif."
            
            # Rerun untuk masuk dashboard atau menampilkan error
            st.rerun()

        # ── Tampilkan error jika ada (setelah loading selesai) ────────────────
        if st.session_state.get("_login_error") and not _is_loading:
            st.error(st.session_state.pop("_login_error"))

        # ── Proses saat tombol ditekan (Set Loading = True) ───────────────────
        if submitted and not _is_loading:
            if not username_input.strip() or not password_input:
                st.error("Username dan password tidak boleh kosong.")
            else:
                # Simpan input dan panggil animasi loading
                st.session_state["_login_loading"]  = True
                st.session_state["_login_username"] = username_input.strip().lower()
                st.session_state["_login_password"] = password_input
                st.rerun()

        st.markdown("""
            <p style='text-align:center;color:#aaa;font-size:12px;margin-top:16px;'>
                Hubungi administrator jika lupa password.
            </p>
        """, unsafe_allow_html=True)

    return False

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS YANG DIPAKAI DI SELURUH APP
# ─────────────────────────────────────────────────────────────────────────────

def get_current_user() -> dict | None:
    """Kembalikan dict user yang sedang login, atau None."""
    return st.session_state.get("current_user")


def is_admin() -> bool:
    """True jika user yang login memiliki role 'admin'."""
    user = get_current_user()
    return user is not None and user.get("role") == "admin"


def is_viewer() -> bool:
    """True jika user yang login memiliki role 'viewer'."""
    user = get_current_user()
    return user is not None and user.get("role") == "viewer"


def logout():
    """Reset semua session state terkait auth."""
    st.session_state.authenticated = False
    st.session_state.current_user  = None
    # Bersihkan session state lain yang mungkin sensitif
    for key in list(st.session_state.keys()):
        if key not in ("authenticated", "current_user"):
            del st.session_state[key]


def render_user_info_sidebar():
    """
    Render info user yang sedang login di sidebar bagian bawah.
    Termasuk badge role dan tombol logout.
    """
    user = get_current_user()
    if not user:
        return

    role_color = "#ff4b4b" if user["role"] == "admin" else "#1f77b4"
    role_label = "Admin"   if user["role"] == "admin" else "Viewer"
    bagian_str = user.get("bagian") or "Semua Bagian"

    st.sidebar.markdown(f"""
        <div style='
            background: rgba(128,128,128,0.08);
            border: 1px solid rgba(128,128,128,0.15);
            border-radius: 10px;
            padding: 10px 14px;
            margin-bottom: 8px;
        '>
            <div style='display:flex;align-items:center;gap:8px;margin-bottom:4px;'>
                <span style='
                    background:{role_color};color:#fff;
                    padding:2px 9px;border-radius:12px;
                    font-size:11px;font-weight:700;
                '>{role_label}</span>
                <span style='font-size:13px;font-weight:600;'>{user['nama_lengkap']}</span>
            </div>
            <p style='font-size:11px;opacity:0.5;margin:0;'>
                @{user['username']} &nbsp;·&nbsp; {bagian_str}
            </p>
        </div>
    """, unsafe_allow_html=True)
