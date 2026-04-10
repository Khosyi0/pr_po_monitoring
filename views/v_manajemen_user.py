import streamlit as st
import pandas as pd
from sqlalchemy import text

# ─────────────────────────────────────────────────────────────────────────────
# CSS & ICONS UNTUK KARTU METRIK (Tetap sama seperti sebelumnya)
# ─────────────────────────────────────────────────────────────────────────────

USER_METRIC_CSS = """
<style>
.user-card {
    background: var(--secondary-background-color);
    border-radius: 12px;
    padding: 16px 18px 14px 18px;
    display: flex;
    align-items: flex-start;
    gap: 14px;
    height: 100%;
    border: 1px solid rgba(128,128,128,0.12);
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.user-icon {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    border-radius: 10px;
    background: rgba(128, 128, 128, 0.15); 
    color: var(--text-color); 
}
.user-body { flex: 1; min-width: 0; }
.user-label {
    font-size: 13px;
    opacity: 0.65;
    margin: 0 0 4px 0;
    line-height: 1.3;
    font-weight: 600;
}
.user-value {
    font-size: 1.8rem !important;
    font-weight: 600 !important;
    margin: 0 0 2px 0 !important;
    line-height: 1.1 !important;
    color: var(--text-color);
}
.user-delta {
    font-size: 12px;
    opacity: 0.55;
    margin: 0;
}
/* Menyesuaikan sedikit tampilan dataframe */
[data-testid="stDataFrame"] { margin-bottom: 8px; }
</style>
"""

ICONS = {
    "people":      "M7 14s-1 0-1-1 1-4 5-4 5 3 5 4-1 1-1 1zm4-6a3 3 0 1 0 0-6 3 3 0 0 0 0 6m-5.784 6A2.24 2.24 0 0 1 5 13c0-1.355.68-2.75 1.936-3.72A6.3 6.3 0 0 0 5 9c-4 0-5 3-5 4s1 1 1 1zM4.5 8a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5",
    "check_circle":"M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16M10.97 4.97a.235.235 0 0 0-.02.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-1.071-1.05",
    "key":         "M0 8a4 4 0 0 1 7.465-2H14a.5.5 0 0 1 .354.146l1.5 1.5a.5.5 0 0 1 0 .708l-1.5 1.5a.5.5 0 0 1-.708 0L13 9.207l-.646.647a.5.5 0 0 1-.708 0L11 9.207l-.646.647a.5.5 0 0 1-.708 0L9 9.207l-.646.647A.5.5 0 0 1 8 10h-.535A4 4 0 0 1 0 8zm4-1a1 1 0 1 0 0-2 1 1 0 0 0 0 2z"
}

def _svg(path_d: str, size: int = 24) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'fill="currentColor" viewBox="0 0 16 16"><path fill-rule="evenodd" d="{path_d}"/></svg>'
    )

def _user_card(icon_d: str, label: str, value: str, delta: str = "") -> str:
    delta_html = f'<p class="user-delta">{delta}</p>' if delta else ""
    return f"""<div class="user-card">
    <div class="user-icon">{_svg(icon_d, 22)}</div>
    <div class="user-body">
        <p class="user-label">{label}</p>
        <p class="user-value">{value}</p>{delta_html}
    </div>
</div>"""

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_engine():
    from config_db import get_db_engine
    return get_db_engine()

# (Tambahkan st.cache_data agar loading lebih cepat)
@st.cache_data(ttl=60) 
def _load_user_data(search_term=""):
    try:
        query = """
            SELECT 
                id, username, nama_lengkap, role, bagian, aktif, created_at, last_login 
            FROM melati_users
        """
        params = {}
        
        if search_term:
            query += " WHERE username ILIKE :search OR nama_lengkap ILIKE :search"
            params["search"] = f"%{search_term}%"
            
        query += " ORDER BY id ASC" # Diubah ke ASC agar urutan stabil saat diedit
        
        with _get_engine().connect() as conn:
            df = pd.read_sql(text(query), conn, params=params)
        return df
    except Exception as e:
        st.error(f"Error mengambil data user: {e}")
        return pd.DataFrame()

def _add_user_to_db(username, password, nama_lengkap, role, bagian):
    try:
        sql = """
            INSERT INTO melati_users (username, password_hash, nama_lengkap, role, bagian)
            VALUES (
                :uname, 
                crypt(:pwd, gen_salt('bf', 10)), 
                :nama, 
                :role, 
                :bagian
            )
        """
        params = {
            "uname": username.strip().lower(),
            "pwd": password,
            "nama": nama_lengkap.strip(),
            "role": role,
            "bagian": bagian.strip() if bagian.strip() else None
        }
        
        with _get_engine().begin() as conn:
            conn.execute(text(sql), params)
        return True, ""
    except Exception as e:
        error_msg = str(e).lower()
        if "unique constraint" in error_msg or "duplicate key" in error_msg:
            return False, "Username sudah digunakan. Silakan pilih username lain."
        return False, f"Terjadi kesalahan: {e}"

# --- FUNGSI UPDATE BARU ---
def _update_user_db(user_id, updates):
    if not updates: return True, ""
    
    set_clauses = []
    params = {"id": int(user_id)}
    
    for key, value in updates.items():
        set_clauses.append(f"{key} = :{key}")
        # Tangani nilai None (Kosong)
        params[key] = value.strip() if isinstance(value, str) and value.strip() else value
    
    sql = f"UPDATE melati_users SET {', '.join(set_clauses)} WHERE id = :id"
    
    try:
        with _get_engine().begin() as conn:
            conn.execute(text(sql), params)
        return True, ""
    except Exception as e:
        return False, f"Gagal menyimpan perubahan: {e}"

# ─────────────────────────────────────────────────────────────────────────────
# RENDER
# ─────────────────────────────────────────────────────────────────────────────

def render(**kwargs):
    is_admin_flag = kwargs.get("is_admin", False)
    if not is_admin_flag:
        st.error("Akses Ditolak. Halaman ini khusus untuk Administrator.")
        st.stop()

    st.markdown(USER_METRIC_CSS, unsafe_allow_html=True)

    st.markdown("""
        <h1 style='display:flex; align-items:center; font-size:42px; margin-bottom:0;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" fill="currentColor" 
                 viewBox="0 0 16 16" style="margin-right:12px; margin-bottom:4px;">
                <path d="M8 4.754a3.246 3.246 0 1 0 0 6.492 3.246 3.246 0 0 0 0-6.492zM5.754 8a2.246 2.246 0 1 1 4.492 0 2.246 2.246 0 0 1-4.492 0z"/>
                <path d="M9.796 1.343c-.527-1.79-3.065-1.79-3.592 0l-.094.319a.873.873 0 0 1-1.255.52l-.292-.16c-1.64-.892-3.433.902-2.54 2.541l.159.292a.873.873 0 0 1-.52 1.255l-.319.094c-1.79.527-1.79 3.065 0 3.592l.319.094a.873.873 0 0 1 .52 1.255l-.16.292c-.892 1.64.901 3.434 2.541 2.54l.292-.159a.873.873 0 0 1 1.255.52l.094.319c.527 1.79 3.065 1.79 3.592 0l.094-.319a.873.873 0 0 1 1.255-.52l.292.16c1.64.893 3.434-.902 2.54-2.541l-.159-.292a.873.873 0 0 1 .52-1.255l.319-.094c1.79-.527 1.79-3.065 0-3.592l-.319-.094a.873.873 0 0 1-.52-1.255l.16-.292c.893-1.64-.902-3.433-2.541-2.54l-.292.159a.873.873 0 0 1-1.255-.52l-.094-.319zm-2.633.283c.246-.835 1.428-.835 1.674 0l.094.319a1.873 1.873 0 0 0 2.693 1.115l.291-.16c.764-.415 1.6.42 1.184 1.185l-.159.292a1.873 1.873 0 0 0 1.116 2.692l.318.094c.835.246.835 1.428 0 1.674l-.319.094a1.873 1.873 0 0 0-1.115 2.693l.16.291c.415.764-.42 1.6-1.185 1.184l-.291-.159a1.873 1.873 0 0 0-2.693 1.116l-.094.318c-.246.835-1.428.835-1.674 0l-.094-.319a1.873 1.873 0 0 0-2.692-1.115l-.292.16c-.764.415-1.6-.42-1.184-1.185l.159-.291A1.873 1.873 0 0 0 1.945 8.93l-.319-.094c-.835-.246-.835-1.428 0-1.674l.319-.094A1.873 1.873 0 0 0 3.06 4.377l-.16-.292c-.415-.764.42-1.6 1.185-1.184l.292.159a1.873 1.873 0 0 0 2.692-1.115l.094-.319z"/>
            </svg>
            Manajemen User & Akses
        </h1>
    """, unsafe_allow_html=True)
    
    st.markdown(
        "<p style='font-size:15px; opacity:0.6; margin-top:4px; margin-bottom:24px;'>"
        "Kelola hak akses dan akun pengguna untuk Monitoring Dashboard Pengadaan Barang."
        "</p>", 
        unsafe_allow_html=True
    )
    
    # Tarik Data Utama
    df_all = _load_user_data()
    
    # Hitung Metrik
    total_user = len(df_all)
    user_aktif = len(df_all[df_all['aktif'] == True]) if not df_all.empty else 0
    user_admin = len(df_all[df_all['role'] == 'admin']) if not df_all.empty else 0
    user_viewer = len(df_all[df_all['role'] == 'viewer']) if not df_all.empty else 0

    # ── Bagian 1: Metrik Singkat (Atas) ───────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(_user_card(
            ICONS["people"], "Total User", str(total_user)
        ), unsafe_allow_html=True)
    with col2:
        st.markdown(_user_card(
            ICONS["check_circle"], "User Aktif", str(user_aktif), f"{total_user - user_aktif} Non-Aktif"
        ), unsafe_allow_html=True)
    with col3:
        st.markdown(_user_card(
            ICONS["key"], "Komposisi Role", f"{user_admin} Admin", f"{user_viewer} Viewer"
        ), unsafe_allow_html=True)
        
    st.markdown("<br><br>", unsafe_allow_html=True)

    # ── Bagian 2: Data Editor Interaktif (Update & Soft Delete) ───────────────
    st.subheader("Daftar Pengguna Sistem")
    st.caption("💡 *Tips: Klik pada sel tabel (Nama, Role, Bagian, atau centang Aktif) untuk mengedit data secara langsung.*")
    
    search_query = st.text_input("Cari Username atau Nama Lengkap:", placeholder="Ketik lalu tekan Enter...")
    df_tampil = _load_user_data(search_query) if search_query else df_all
    
    if not df_tampil.empty:
        # Menyiapkan kolom tanggal agar formatnya bagus tapi tetap bisa dipakai referensi ID
        df_edit = df_tampil.copy()
        df_edit['created_at_str'] = pd.to_datetime(df_edit['created_at']).dt.strftime('%d %b %Y %H:%M')
        df_edit['last_login_str'] = pd.to_datetime(df_edit['last_login']).dt.strftime('%d %b %Y %H:%M').fillna("Belum")
        
        # Kolom yang ditampilkan di editor (Buang kolom tanggal asli karena kita pakai versi string-nya)
        df_display = df_edit[['id', 'username', 'nama_lengkap', 'role', 'bagian', 'aktif', 'created_at_str', 'last_login_str']]

        # Menampilkan Data Editor interaktif
        edited_df = st.data_editor(
            df_display,
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True), # ID tidak boleh diedit
                "username": st.column_config.TextColumn("Username", disabled=True, width="medium"), # Username tidak boleh diedit
                "nama_lengkap": st.column_config.TextColumn("Nama Lengkap", width="large"),
                "role": st.column_config.SelectboxColumn("Role", options=["admin", "viewer"], required=True),
                "bagian": st.column_config.TextColumn("Bagian/Dept"),
                "aktif": st.column_config.CheckboxColumn("Aktif (Akses Login)"),
                "created_at_str": st.column_config.TextColumn("Dibuat Pada", disabled=True),
                "last_login_str": st.column_config.TextColumn("Login Terakhir", disabled=True),
            },
            hide_index=True,
            use_container_width=True,
            key="user_editor"
        )
        
        # --- PROSES SIMPAN PERUBAHAN (UPDATE) ---
        # Membandingkan dataframe yang diedit dengan dataframe asli untuk mencari perbedaan
        if st.session_state["user_editor"]["edited_rows"]:
            changes_made = False
            for row_idx, updates in st.session_state["user_editor"]["edited_rows"].items():
                user_id = df_display.iloc[row_idx]['id']
                
                # Update ke database
                success, msg = _update_user_db(user_id, updates)
                if success:
                    changes_made = True
                else:
                    st.error(f"Gagal mengupdate ID {user_id}: {msg}")
            
            if changes_made:
                st.success("✅ Perubahan berhasil disimpan!")
                _load_user_data.clear() # Bersihkan cache
                st.rerun() # Refresh halaman untuk menampilkan data terbaru

    else:
        st.info("Belum ada data user atau pencarian tidak ditemukan.")

    # ── Bagian 3: Form Tambah User (Bawah) ────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.expander("➕ Tambah User Baru", expanded=False):
        with st.form("form_tambah_user", clear_on_submit=True):
            st.markdown("<p style='font-size:13px; opacity:0.8;'><em>Password akan otomatis dienkripsi sebelum disimpan ke database.</em></p>", unsafe_allow_html=True)
            
            c_left, c_right = st.columns(2)
            
            with c_left:
                new_username = st.text_input("Username *", placeholder="e.g., mawar.p")
                new_nama = st.text_input("Nama Lengkap *", placeholder="e.g., mawar")
                new_role = st.selectbox("Role *", options=["viewer", "admin"])
                
            with c_right:
                new_password = st.text_input("Password *", type="password", placeholder="Masukkan password kuat...")
                new_bagian = st.text_input("Bagian", placeholder="e.g., ALPATA, (Kosongkan jika semua bagian)")

            st.markdown("---")
            submitted = st.form_submit_button("Simpan User", type="primary")
            
            if submitted:
                if not new_username or not new_nama or not new_password:
                    st.error("⚠️ Username, Nama Lengkap, dan Password wajib diisi!")
                else:
                    sukses, pesan = _add_user_to_db(new_username, new_password, new_nama, new_role, new_bagian)
                    
                    if sukses:
                        st.success(f"✅ User '{new_username}' berhasil ditambahkan!")
                        _load_user_data.clear() # Bersihkan cache
                        st.rerun()
                    else:
                        st.error(pesan)