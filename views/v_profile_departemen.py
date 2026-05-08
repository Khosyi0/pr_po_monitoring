"""
v_profile_departemen.py - Halaman Profile Departemen
"""
import streamlit as st
import pandas as pd
from sqlalchemy import text

try:
    from config_db import get_db_engine
except ImportError:
    get_db_engine = None

# =============================================================================
# CSS: tampilan kartu metrik & list
# =============================================================================
PROFILE_CSS = """
<style>
.prof-card {
    border-radius: 12px !important;
    background-color: var(--secondary-background-color) !important;
    background-image: linear-gradient(rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.08)) !important;
    border: 1px solid rgba(128, 128, 128, 0.25) !important;
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08) !important;
    border-left-width: 6px !important;
    border-left-style: solid !important;
    border-left-color: var(--text-color) !important;
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 20px 18px;
    margin-bottom: 16px;
    min-height: 110px;
}

/* Class khusus untuk kartu berwarna emas (SVP) */
.prof-card-gold {
    border-left-color: #FFD700 !important;
    background-color: rgba(255, 215, 0, 0.05) !important;
}

.prof-icon {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    border-radius: 10px;
    background: rgba(128, 128, 128, 0.1) !important;
    color: var(--text-color) !important;
}

.prof-body { 
    flex: 1; 
    min-width: 0; 
}

.prof-label {
    font-size: 13px;
    margin: 0 0 4px 0 !important;
    font-weight: 500;
    color: var(--text-color) !important;
    opacity: 0.75;
}

.prof-value {
    font-size: 1.8rem !important;
    font-weight: 600 !important;
    margin: 0 !important;
    line-height: 1.1 !important;
    color: var(--text-color) !important;
}

.emp-list-container {
    background-color: rgba(128, 128, 128, 0.05);
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 8px;
    padding: 12px;
    margin-top: -8px;
    margin-bottom: 16px;
    max-height: 400px;
    overflow-y: auto;
}

.emp-list-item {
    background-color: var(--secondary-background-color);
    border: 1px solid rgba(128, 128, 128, 0.15) !important;
    border-left-width: 4px !important;
    border-left-style: solid !important;
    border-left-color: var(--text-color) !important;
    border-radius: 6px;
    padding: 8px 12px;
    margin-bottom: 8px;
    font-size: 13px;
    font-weight: 500;
    color: var(--text-color);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.emp-list-item-avp {
    border-left-color: #FFD700 !important;
    background-color: rgba(255, 215, 0, 0.08);
}

.emp-empty {
    opacity: 0.5;
    font-style: italic;
    font-weight: 400;
}
</style>
"""

def _svg(path_d: str, size: int = 40) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" fill="currentColor" viewBox="0 0 16 16"><path d="{path_d}"/></svg>'

def _card(icon_d: str, label: str, value: str, is_gold: bool = False) -> str:
    cls = "prof-card prof-card-gold" if is_gold else "prof-card"
    return f"""<div class="{cls}">
    <div class="prof-icon">{_svg(icon_d, 36)}</div>
    <div class="prof-body">
        <p class="prof-label">{label}</p>
        <p class="prof-value">{value}</p>
    </div>
</div>"""

ICONS = {
    "people": "M7 14s-1 0-1-1 1-4 5-4 5 3 5 4-1 1-1 1zm4-6a3 3 0 1 0 0-6 3 3 0 0 0 0 6m-5.784 6A2.24 2.24 0 0 1 5 13c0-1.355.68-2.75 1.936-3.72A6.3 6.3 0 0 0 5 9c-4 0-5 3-5 4s1 1 1 1zM4.5 8a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5",
    "building": "M4 2.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm3 0a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm3.5-.5a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5v-1a.5.5 0 0 0-.5-.5zM4 5.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zM7.5 5a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5v-1a.5.5 0 0 0-.5-.5zm2.5.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zM4.5 8a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5v-1a.5.5 0 0 0-.5-.5zm2.5.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm3.5-.5a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5v-1a.5.5 0 0 0-.5-.5z M2 1a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1zm11 0H3v14h3v-2.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 .5.5V15h3z",
    "crown": "M14.348 14.844a.5.5 0 0 1-.496.446H2.148a.5.5 0 0 1-.496-.446l-.904-8.14a.5.5 0 0 1 .787-.45l3.074 2.149 3.405-4.256a.5.5 0 0 1 .772 0l3.405 4.256 3.074-2.149a.5.5 0 0 1 .787.45l-.904 8.14zM2.674 14h10.652l.776-6.984-2.86 2a.5.5 0 0 1-.682-.118L7.5 4.965l-3.06 3.833a.5.5 0 0 1-.682.118l-2.86-2L2.674 14z"
}

def render(**kwargs):
    st.markdown(PROFILE_CSS, unsafe_allow_html=True)
    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:40px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="35" height="35" fill="currentColor" class="bi bi-building" viewBox="0 0 16 16" style="margin-bottom: 8px; margin-right: 12px;">
                <path d="M6 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6m-5 6s-1 0-1-1 1-4 6-4 6 3 6 4-1 1-1 1zM11 3.5a.5.5 0 0 1 .5-.5h4a.5.5 0 0 1 0 1h-4a.5.5 0 0 1-.5-.5m.5 2.5a.5.5 0 0 0 0 1h4a.5.5 0 0 0 0-1zm2 3a.5.5 0 0 0 0 1h2a.5.5 0 0 0 0-1zm0 3a.5.5 0 0 0 0 1h2a.5.5 0 0 0 0-1z"/>
            </svg>
            Profile Departemen
        </h1>
    """, unsafe_allow_html=True)
    st.markdown("---")

    load_data = kwargs.get('load_data')
    is_admin = kwargs.get('is_admin', False)

    if not load_data:
        st.info("Parameter data tidak ditemukan.")
        return

    # =========================================================================
    # ADMIN MANAGEMENT
    # =========================================================================
    if is_admin:
        with st.expander("⚙️ Manajemen Data Karyawan (Edit Manual)"):
            engine = get_db_engine() if get_db_engine else None
            if engine:
                tab_tambah, tab_hapus = st.tabs(["➕ Tambah / Edit", "🗑️ Hapus"])
                with tab_tambah:
                    with st.form("form_tambah_karyawan"):
                        st.caption("Catatan: Menunjuk seseorang menjadi SVP akan mengeluarkannya dari bagian (independen). Menunjuk AVP akan otomatis menggantikan AVP lama di bagian tersebut.")
                        col_nama, col_bag, col_jab = st.columns([2, 1, 1])
                        inp_nama = col_nama.text_input("Nama Karyawan")
                        inp_bagian = col_bag.selectbox("Bagian", ["ALPATA", "BARUM", "BB/BD/BP", "EPP"])
                        inp_jabatan = col_jab.selectbox("Jabatan", ["Karyawan", "AVP", "SVP"])
                        
                        if st.form_submit_button("Simpan Data", type="primary"):
                            if inp_nama.strip():
                                if inp_jabatan == "SVP":
                                    inp_bagian = "PIMPINAN"

                                with engine.begin() as conn:
                                    if inp_jabatan == "SVP":
                                        conn.execute(text("UPDATE profile_karyawan SET jabatan = 'Karyawan' WHERE jabatan = 'SVP'"))
                                    elif inp_jabatan == "AVP":
                                        conn.execute(text("UPDATE profile_karyawan SET jabatan = 'Karyawan' WHERE bagian = :b AND jabatan = 'AVP'"), {"b": inp_bagian})

                                    cek = conn.execute(text("SELECT 1 FROM profile_karyawan WHERE LOWER(nama) = LOWER(:n)"), {"n": inp_nama.strip()}).fetchone()
                                    if cek:
                                        conn.execute(text("UPDATE profile_karyawan SET bagian = :b, jabatan = :j WHERE LOWER(nama) = LOWER(:n)"), {"n": inp_nama.strip(), "b": inp_bagian, "j": inp_jabatan})
                                    else:
                                        conn.execute(text("INSERT INTO profile_karyawan (nama, bagian, jabatan) VALUES (:n, :b, :j)"), {"n": inp_nama.strip(), "b": inp_bagian, "j": inp_jabatan})
                                
                                st.success(f"Data {inp_nama} berhasil diperbarui.")
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error("Nama karyawan tidak boleh kosong.")

                with tab_hapus:
                    df_list = load_data("SELECT nama FROM profile_karyawan ORDER BY nama")
                    if not df_list.empty:
                        with st.form("form_hapus"):
                            opt_hapus = st.selectbox("Pilih Karyawan", df_list['nama'].tolist())
                            if st.form_submit_button("Hapus"):
                                with engine.begin() as conn:
                                    conn.execute(text("DELETE FROM profile_karyawan WHERE nama = :n"), {"n": opt_hapus})
                                st.success(f"Data {opt_hapus} berhasil dihapus.")
                                st.cache_data.clear()
                                st.rerun()
                    else:
                        st.info("Belum ada data karyawan yang terdaftar.")
        st.markdown("<br>", unsafe_allow_html=True)

    # =========================================================================
    # LOGIKA DATA
    # =========================================================================
    try:
        df_all = load_data("SELECT nama, bagian, jabatan FROM profile_karyawan")
        
        total_count = len(df_all)
        svp_row = df_all[df_all['jabatan'] == 'SVP']
        svp_name = svp_row['nama'].iloc[0] if not svp_row.empty else "(posisi kosong)"

        st.markdown("### Pimpinan & Kapasitas")
        col_total, col_svp = st.columns(2)
        with col_total:
            st.markdown(_card(ICONS['people'], "Total Karyawan", f"{total_count} Orang"), unsafe_allow_html=True)
        with col_svp:
            st.markdown(_card(ICONS['crown'], "Senior Vice President (SVP)", svp_name, is_gold=True), unsafe_allow_html=True)

        st.markdown("#### Jumlah Karyawan per Bagian")
        
        sections = ["ALPATA", "BARUM", "BB/BD/BP", "EPP"]
        cols = st.columns(4)

        for i, section in enumerate(sections):
            with cols[i]:
                df_sec = df_all[df_all['bagian'] == section]
                sec_count = len(df_sec)
                
                st.markdown(_card(ICONS['building'], section, f"{sec_count} Orang"), unsafe_allow_html=True)
                
                df_sec_sorted = df_sec.copy()
                if not df_sec_sorted.empty:
                    df_sec_sorted['sort_rank'] = df_sec_sorted['jabatan'].apply(lambda x: 1 if x == 'AVP' else 2)
                    df_sec_sorted = df_sec_sorted.sort_values(['sort_rank', 'nama'])
                
                has_avp = not df_sec_sorted[df_sec_sorted['jabatan'] == 'AVP'].empty
                
                html_list = "<div class='emp-list-container'>"
                
                if not has_avp:
                    # Menyelaraskan teks posisi kosong agar konsisten
                    html_list += "<div class='emp-list-item emp-list-item-avp emp-empty'><b>(AVP) - (posisi kosong)</b></div>"
                
                for _, row in df_sec_sorted.iterrows():
                    is_avp = row['jabatan'] == 'AVP'
                    cls = "emp-list-item emp-list-item-avp" if is_avp else "emp-list-item"
                    # Memindah tulisan (AVP) ke depan nama
                    label = f"<b>(AVP) {row['nama']}</b>" if is_avp else row['nama']
                    html_list += f"<div class='{cls}'>{label}</div>"
                
                if sec_count == 0 or (sec_count == 1 and has_avp == False and df_sec_sorted.empty):
                    html_list += "<div class='emp-list-item' style='opacity:0.5; text-align:center;'>Belum ada anggota</div>"
                
                html_list += "</div>"
                st.markdown(html_list, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Gagal memuat data: {e}")