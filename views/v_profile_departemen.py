"""
v_profile_departemen.py - Halaman Profile Departemen
"""
import streamlit as st
import pandas as pd
from datetime import date, datetime
from sqlalchemy import text

try:
    from config_db import get_db_engine
except ImportError:
    get_db_engine = None

# =============================================================================
# CSS
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

.prof-body { flex: 1; min-width: 0; }

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

.prof-subtext {
    font-size: 12px;
    margin: 4px 0 0 0 !important;
    color: var(--text-color) !important;
    opacity: 0.6;
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

.emp-empty { opacity: 0.5; font-style: italic; font-weight: 400; }
</style>
"""

def _svg(path_d: str, size: int = 40) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" fill="currentColor" viewBox="0 0 16 16"><path d="{path_d}"/></svg>'

def _card(icon_d: str, label: str, value: str, is_gold: bool = False, subtext: str = "") -> str:
    cls = "prof-card prof-card-gold" if is_gold else "prof-card"
    subtext_html = f'\n        <p class="prof-subtext">{subtext}</p>' if subtext else ""
    return f"""<div class="{cls}">
    <div class="prof-icon">{_svg(icon_d, 36)}</div>
    <div class="prof-body">
        <p class="prof-label">{label}</p>
        <p class="prof-value">{value}</p>{subtext_html}
    </div>
</div>"""

ICONS = {
    "people":   "M7 14s-1 0-1-1 1-4 5-4 5 3 5 4-1 1-1 1zm4-6a3 3 0 1 0 0-6 3 3 0 0 0 0 6m-5.784 6A2.24 2.24 0 0 1 5 13c0-1.355.68-2.75 1.936-3.72A6.3 6.3 0 0 0 5 9c-4 0-5 3-5 4s1 1 1 1zM4.5 8a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5",
    "building": "M4 2.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm3 0a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm3.5-.5a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5v-1a.5.5 0 0 0-.5-.5zM4 5.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zM7.5 5a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5v-1a.5.5 0 0 0-.5-.5zm2.5.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zM4.5 8a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5v-1a.5.5 0 0 0-.5-.5zm2.5.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm3.5-.5a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5v-1a.5.5 0 0 0-.5-.5z M2 1a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1zm11 0H3v14h3v-2.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 .5.5V15h3z",
    "crown":    "M14.348 14.844a.5.5 0 0 1-.496.446H2.148a.5.5 0 0 1-.496-.446l-.904-8.14a.5.5 0 0 1 .787-.45l3.074 2.149 3.405-4.256a.5.5 0 0 1 .772 0l3.405 4.256 3.074-2.149a.5.5 0 0 1 .787.45l-.904 8.14zM2.674 14h10.652l.776-6.984-2.86 2a.5.5 0 0 1-.682-.118L7.5 4.965l-3.06 3.833a.5.5 0 0 1-.682.118l-2.86-2L2.674 14z",
    "arrow":    "M8 3a.5.5 0 0 1 .5.5v2h2a.5.5 0 0 1 0 1h-2v2a.5.5 0 0 1-1 0v-2h-2a.5.5 0 0 1 0-1h2v-2A.5.5 0 0 1 8 3z",
}

BAGIAN_LIST = ["ALPATA", "BARUM", "BB/BD/BP", "EPP"]
SECTION_CAPACITIES = {"ALPATA": 10, "BARUM": 7, "BB/BD/BP": 8, "EPP": 6}


# =============================================================================
# PANEL ADMIN: MANAJEMEN KARYAWAN (profile_karyawan)
# =============================================================================

def _panel_manajemen_karyawan(load_data, engine):
    """Panel untuk tambah/edit/hapus data di tabel profile_karyawan (struktur organisasi)."""
    with st.expander("Manajemen Data Karyawan (Edit Manual)", icon=":material/settings:"):
        tab_tambah, tab_hapus = st.tabs(["Tambah / Edit", "Hapus"])

        with tab_tambah:
            with st.form("form_tambah_karyawan"):
                st.caption(
                    "Catatan: Menunjuk seseorang menjadi VP akan mengeluarkannya dari bagian (independen). "
                    "Menunjuk AVP akan otomatis menggantikan AVP lama di bagian tersebut."
                )
                col_nama, col_bag, col_jab = st.columns([2, 1, 1])
                inp_nama    = col_nama.text_input("Nama Karyawan")
                inp_bagian  = col_bag.selectbox("Bagian", BAGIAN_LIST)
                inp_jabatan = col_jab.selectbox("Jabatan", ["Karyawan", "AVP", "VP"])

                if st.form_submit_button("Simpan Data", type="primary"):
                    if inp_nama.strip():
                        bagian_simpan = "PIMPINAN" if inp_jabatan == "VP" else inp_bagian
                        with engine.begin() as conn:
                            if inp_jabatan == "VP":
                                conn.execute(text(
                                    "UPDATE profile_karyawan SET jabatan = 'Karyawan' WHERE jabatan = 'VP'"
                                ))
                            elif inp_jabatan == "AVP":
                                conn.execute(text(
                                    "UPDATE profile_karyawan SET jabatan = 'Karyawan' "
                                    "WHERE bagian = :b AND jabatan = 'AVP'"
                                ), {"b": bagian_simpan})

                            cek = conn.execute(text(
                                "SELECT 1 FROM profile_karyawan WHERE LOWER(nama) = LOWER(:n)"
                            ), {"n": inp_nama.strip()}).fetchone()
                            if cek:
                                conn.execute(text(
                                    "UPDATE profile_karyawan SET bagian = :b, jabatan = :j "
                                    "WHERE LOWER(nama) = LOWER(:n)"
                                ), {"n": inp_nama.strip(), "b": bagian_simpan, "j": inp_jabatan})
                            else:
                                conn.execute(text(
                                    "INSERT INTO profile_karyawan (nama, bagian, jabatan) VALUES (:n, :b, :j)"
                                ), {"n": inp_nama.strip(), "b": bagian_simpan, "j": inp_jabatan})

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
                            conn.execute(text(
                                "DELETE FROM profile_karyawan WHERE nama = :n"
                            ), {"n": opt_hapus})
                        st.success(f"Data {opt_hapus} berhasil dihapus.")
                        st.cache_data.clear()
                        st.rerun()
            else:
                st.info("Belum ada data karyawan yang terdaftar.")


# =============================================================================
# PANEL ADMIN: MANAJEMEN RIWAYAT BAGIAN SIPS (karyawan_bagian_history)
# =============================================================================

def _panel_riwayat_bagian(load_data, engine):
    """
    Panel untuk mengelola historis keanggotaan bagian karyawan SIPS.
    Ini yang menentukan bagian karyawan pada laporan berdasarkan tanggal transaksi.
    """
    with st.expander("Manajemen Riwayat Bagian SIPS (Mutasi Karyawan)", icon=":material/sync:"):
        st.info(
            "**Cara kerja:** Setiap karyawan SIPS bisa punya lebih dari satu riwayat bagian. "
            "Laporan akan otomatis menggunakan bagian yang berlaku sesuai tanggal transaksi. "
            "Misalnya, karyawan yang pindah dari BARUM ke ALPATA per 1 Juni 2026: "
            "laporan Januari–Mei tetap masuk BARUM, laporan Juni+ masuk ALPATA."
        )

        tab_lihat, tab_tambah, tab_tutup, tab_hapus = st.tabs(
            ["Lihat Riwayat", "Tambah Riwayat Baru", "Tutup Riwayat Aktif", "Hapus"]
        )

        # -- Tab: Lihat Riwayat ------------------------------------------------
        with tab_lihat:
            df_history = load_data("""
                SELECT
                    kbh.id,
                    se.nama,
                    kbh.nik,
                    kbh.bagian,
                    kbh.berlaku_dari,
                    kbh.berlaku_sampai,
                    kbh.keterangan,
                    CASE WHEN kbh.berlaku_sampai IS NULL THEN '✅ Aktif' ELSE '🔒 Selesai' END AS status_aktif
                FROM karyawan_bagian_history kbh
                LEFT JOIN sips_employees se ON kbh.nik = se.nik
                ORDER BY se.nama, kbh.berlaku_dari DESC
            """)

            if df_history.empty:
                st.info("Belum ada riwayat bagian. Jalankan migration SQL terlebih dahulu.")
            else:
                # Filter per bagian untuk memudahkan navigasi
                col_f1, col_f2 = st.columns(2)
                filter_bagian_h = col_f1.selectbox(
                    "Filter Bagian", ["Semua"] + BAGIAN_LIST, key="hist_filter_bagian"
                )
                filter_status_h = col_f2.selectbox(
                    "Filter Status", ["Semua", "✅ Aktif", "🔒 Selesai"], key="hist_filter_status"
                )

                df_show = df_history.copy()
                if filter_bagian_h != "Semua":
                    df_show = df_show[df_show['bagian'] == filter_bagian_h]
                if filter_status_h != "Semua":
                    df_show = df_show[df_show['status_aktif'] == filter_status_h]

                st.dataframe(
                    df_show[['nama', 'nik', 'bagian', 'berlaku_dari', 'berlaku_sampai', 'status_aktif', 'keterangan']],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "nama":           st.column_config.TextColumn("Nama"),
                        "nik":            st.column_config.TextColumn("NIK"),
                        "bagian":         st.column_config.TextColumn("Bagian"),
                        "berlaku_dari":   st.column_config.DateColumn("Berlaku Dari", format="DD MMM YYYY"),
                        "berlaku_sampai": st.column_config.DateColumn("Berlaku Sampai", format="DD MMM YYYY"),
                        "status_aktif":   st.column_config.TextColumn("Status"),
                        "keterangan":     st.column_config.TextColumn("Keterangan"),
                    }
                )

        # -- Tab: Tambah Riwayat Baru ------------------------------------------
        with tab_tambah:
            st.caption(
                "Gunakan ini untuk: menambah karyawan baru ke bagian, atau mencatat mutasi "
                "(tambahkan riwayat baru dengan tanggal mulai yang sesuai)."
            )

            # Ambil daftar karyawan dari sips_employees
            df_emp = load_data("SELECT nik, nama FROM sips_employees ORDER BY nama")
            if df_emp.empty:
                st.warning("Belum ada karyawan di database SIPS. Jalankan ETL terlebih dahulu.")
            else:
                emp_options = {
                    f"{row['nama']} ({row['nik']})": row['nik']
                    for _, row in df_emp.iterrows()
                }

                with st.form("form_tambah_history"):
                    col_e, col_b = st.columns([2, 1])
                    sel_emp    = col_e.selectbox("Karyawan", list(emp_options.keys()))
                    sel_bagian = col_b.selectbox("Bagian Tujuan", BAGIAN_LIST)

                    col_d1, col_d2 = st.columns(2)
                    inp_dari   = col_d1.date_input(
                        "Berlaku Dari", value=date.today(),
                        help="Tanggal mulai karyawan ini masuk ke bagian tersebut."
                    )
                    inp_sampai = col_d2.date_input(
                        "Berlaku Sampai (kosongkan jika masih aktif)",
                        value=None, min_value=date(2020, 1, 1),
                        help="Isi hanya jika sudah tahu kapan berakhirnya. Kosongkan = aktif.",
                    )
                    inp_ket = st.text_input(
                        "Keterangan (opsional)",
                        placeholder="cth: Mutasi dari BARUM, penambahan formasi, dll."
                    )

                    if st.form_submit_button("➕ Tambah Riwayat", type="primary"):
                        nik_terpilih = emp_options[sel_emp]
                        berlaku_sampai_val = inp_sampai if inp_sampai else None

                        # Validasi: berlaku_dari tidak boleh setelah berlaku_sampai
                        if berlaku_sampai_val and inp_dari > berlaku_sampai_val:
                            st.error("Tanggal 'Berlaku Dari' tidak boleh setelah 'Berlaku Sampai'.")
                        else:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    INSERT INTO karyawan_bagian_history
                                        (nik, bagian, berlaku_dari, berlaku_sampai, keterangan)
                                    VALUES (:nik, :bagian, :dari, :sampai, :ket)
                                """), {
                                    'nik':    nik_terpilih,
                                    'bagian': sel_bagian,
                                    'dari':   inp_dari,
                                    'sampai': berlaku_sampai_val,
                                    'ket':    inp_ket.strip() or None,
                                })
                            st.success(
                                f"Riwayat berhasil ditambahkan: {sel_emp} → {sel_bagian} "
                                f"mulai {inp_dari.strftime('%d %b %Y')}."
                            )
                            st.cache_data.clear()
                            st.rerun()

        # -- Tab: Tutup Riwayat Aktif ------------------------------------------
        with tab_tutup:
            st.caption(
                "Gunakan ini saat karyawan pindah bagian: tutup riwayat lamanya "
                "dengan mengisi tanggal berakhir, lalu tambahkan riwayat baru di tab sebelumnya."
            )

            df_aktif = load_data("""
                SELECT
                    kbh.id,
                    COALESCE(se.nama, kbh.nik) AS nama,
                    kbh.nik,
                    kbh.bagian,
                    kbh.berlaku_dari
                FROM karyawan_bagian_history kbh
                LEFT JOIN sips_employees se ON kbh.nik = se.nik
                WHERE kbh.berlaku_sampai IS NULL
                ORDER BY se.nama, kbh.berlaku_dari
            """)

            if df_aktif.empty:
                st.info("Tidak ada riwayat aktif saat ini.")
            else:
                # Buat label untuk selectbox
                df_aktif['label'] = df_aktif.apply(
                    lambda r: f"{r['nama']} → {r['bagian']} (sejak {r['berlaku_dari'].strftime('%d %b %Y') if hasattr(r['berlaku_dari'], 'strftime') else r['berlaku_dari']})",
                    axis=1
                )
                id_map = dict(zip(df_aktif['label'], df_aktif['id']))

                with st.form("form_tutup_history"):
                    sel_aktif  = st.selectbox("Pilih Riwayat Aktif yang Ingin Ditutup", list(id_map.keys()))
                    tgl_tutup  = st.date_input(
                        "Tutup per Tanggal",
                        value=date.today(),
                        help="Tanggal terakhir karyawan ini ada di bagian tersebut (inklusif)."
                    )
                    ket_tutup  = st.text_input(
                        "Keterangan Penutupan (opsional)",
                        placeholder="cth: Mutasi ke ALPATA per Juni 2026"
                    )

                    if st.form_submit_button("🔒 Tutup Riwayat", type="primary"):
                        id_terpilih = int(id_map[sel_aktif]) 
                        with engine.connect() as conn: # <-- UBAH JADI CONNECT
                            # Cek berlaku_dari agar berlaku_sampai tidak lebih awal
                            row_check = conn.execute(text(
                                "SELECT berlaku_dari FROM karyawan_bagian_history WHERE id = :id"
                            ), {'id': id_terpilih}).fetchone()
                            
                            berlaku_dari_db = row_check[0] if row_check else None
                            
                            # Konversi ke objek date dengan aman
                            if isinstance(berlaku_dari_db, str):
                                try:
                                    berlaku_dari_db = datetime.strptime(berlaku_dari_db[:10], "%Y-%m-%d").date()
                                except ValueError:
                                    pass
                            elif isinstance(berlaku_dari_db, datetime):
                                berlaku_dari_db = berlaku_dari_db.date()

                            if berlaku_dari_db and tgl_tutup < berlaku_dari_db:
                                st.error(
                                    f"Tanggal tutup ({tgl_tutup.strftime('%d %b %Y')}) tidak boleh sebelum "
                                    f"tanggal berlaku dari ({berlaku_dari_db.strftime('%d %b %Y')})."
                                )
                            else:
                                keterangan_baru = ket_tutup.strip() or None
                                conn.execute(text("""
                                    UPDATE karyawan_bagian_history
                                    SET berlaku_sampai = :sampai,
                                        keterangan     = COALESCE(:ket, keterangan)
                                    WHERE id = :id
                                """), {
                                    'sampai': tgl_tutup.strftime('%Y-%m-%d'),
                                    'ket': keterangan_baru, 
                                    'id': id_terpilih
                                })
                                
                                conn.commit() # <--- KUNCI UTAMA: PAKSA COMMIT TRANSAKSI KE DATABASE!
                                
                                st.success(f"Riwayat berhasil ditutup per {tgl_tutup.strftime('%d %b %Y')}.")
                                
                                # Sapu bersih SEMUA jenis cache Streamlit
                                st.cache_data.clear()
                                try:
                                    st.cache_resource.clear()
                                except:
                                    pass
                                
                                st.rerun()

        # -- Tab: Hapus Riwayat ------------------------------------------------
        with tab_hapus:
            st.caption(
                "⚠️ Hapus riwayat hanya jika data dimasukkan salah. "
                "Untuk mutasi normal, gunakan 'Tutup Riwayat Aktif'."
            )

            df_semua = load_data("""
                SELECT
                    kbh.id,
                    COALESCE(se.nama, kbh.nik) AS nama,
                    kbh.bagian,
                    kbh.berlaku_dari,
                    kbh.berlaku_sampai
                FROM karyawan_bagian_history kbh
                LEFT JOIN sips_employees se ON kbh.nik = se.nik
                ORDER BY se.nama, kbh.berlaku_dari DESC
            """)

            if df_semua.empty:
                st.info("Belum ada riwayat.")
            else:
                df_semua['label'] = df_semua.apply(
                    lambda r: (
                        f"{r['nama']} → {r['bagian']} "
                        f"({r['berlaku_dari']} s/d "
                        f"{'sekarang' if pd.isna(r['berlaku_sampai']) or r['berlaku_sampai'] is None else r['berlaku_sampai']})"
                    ),
                    axis=1
                )
                id_map_hapus = dict(zip(df_semua['label'], df_semua['id']))

                with st.form("form_hapus_history"):
                    sel_hapus = st.selectbox("Pilih Riwayat yang Akan Dihapus", list(id_map_hapus.keys()))
                    konfirmasi = st.checkbox("Saya yakin ingin menghapus riwayat ini")
                    if st.form_submit_button("🗑️ Hapus", type="primary"):
                        if konfirmasi:
                            with engine.begin() as conn:
                                conn.execute(text(
                                    "DELETE FROM karyawan_bagian_history WHERE id = :id"
                                ), {'id': id_map_hapus[sel_hapus]})
                            st.success("Riwayat berhasil dihapus.")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.warning("Centang konfirmasi terlebih dahulu.")


# =============================================================================
# RENDER UTAMA
# =============================================================================

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
    is_admin  = kwargs.get('is_admin', False)

    if not load_data:
        st.info("Parameter data tidak ditemukan.")
        return

    # =========================================================================
    # PANEL ADMIN
    # =========================================================================
    if is_admin:
        engine = get_db_engine() if get_db_engine else None
        if engine:
            _panel_manajemen_karyawan(load_data, engine)
            st.markdown("<br>", unsafe_allow_html=True)
            _panel_riwayat_bagian(load_data, engine)
            st.markdown("<br>", unsafe_allow_html=True)

    # =========================================================================
    # TAMPILAN PROFIL DEPARTEMEN
    # =========================================================================
    try:
        df_all = load_data("SELECT nama, bagian, jabatan FROM profile_karyawan")

        total_count   = len(df_all)
        vp_row        = df_all[df_all['jabatan'] == 'VP']
        vp_name       = vp_row['nama'].iloc[0] if not vp_row.empty else "(posisi kosong)"
        total_capacity = 32
        empty_total   = total_capacity - total_count

        st.markdown("### Pimpinan & Kapasitas")
        col_total, col_vp = st.columns(2)
        with col_total:
            st.markdown(_card(
                ICONS['people'], "Total Karyawan", f"{total_count} Orang",
                subtext=f"Kapasitas: {total_capacity} Kursi | Kosong: {empty_total}"
            ), unsafe_allow_html=True)
        with col_vp:
            st.markdown(_card(
                ICONS['crown'], "Vice President (VP)", vp_name, is_gold=True
            ), unsafe_allow_html=True)

        st.markdown("#### Jumlah Karyawan per Bagian")
        cols = st.columns(4)

        for i, section in enumerate(BAGIAN_LIST):
            with cols[i]:
                df_sec    = df_all[df_all['bagian'] == section]
                sec_count = len(df_sec)
                capacity  = SECTION_CAPACITIES.get(section, 0)
                empty_sec = capacity - sec_count

                st.markdown(_card(
                    ICONS['building'], section, f"{sec_count} Orang",
                    subtext=f"Kapasitas: {capacity} Kursi | Kosong: {empty_sec}"
                ), unsafe_allow_html=True)

                df_sec_sorted = df_sec.copy()
                if not df_sec_sorted.empty:
                    df_sec_sorted['sort_rank'] = df_sec_sorted['jabatan'].apply(
                        lambda x: 1 if x == 'AVP' else 2
                    )
                    df_sec_sorted = df_sec_sorted.sort_values(['sort_rank', 'nama'])

                has_avp = not df_sec_sorted[df_sec_sorted['jabatan'] == 'AVP'].empty
                html_list = "<div class='emp-list-container'>"

                if not has_avp:
                    html_list += "<div class='emp-list-item emp-list-item-avp emp-empty'><b>(AVP) - (posisi kosong)</b></div>"

                for _, row in df_sec_sorted.iterrows():
                    is_avp = row['jabatan'] == 'AVP'
                    cls    = "emp-list-item emp-list-item-avp" if is_avp else "emp-list-item"
                    label  = f"<b>(AVP) {row['nama']}</b>" if is_avp else row['nama']
                    html_list += f"<div class='{cls}'>{label}</div>"

                if sec_count == 0:
                    html_list += "<div class='emp-list-item' style='opacity:0.5; text-align:center;'>Belum ada anggota</div>"

                html_list += "</div>"
                st.markdown(html_list, unsafe_allow_html=True)

        # =====================================================================
        # RINGKASAN RIWAYAT BAGIAN SIPS (info untuk semua user)
        # =====================================================================
        st.markdown("---")
        st.markdown("### Keanggotaan Bagian SIPS (Berdasarkan Tanggal Transaksi)")
        st.caption(
            "Tabel di bawah menampilkan karyawan yang terdaftar di sistem SIPS beserta "
            "riwayat keanggotaan bagiannya. Laporan SIPS akan menggunakan bagian yang "
            "berlaku sesuai tanggal transaksi masing-masing."
        )

        df_history_pub = load_data("""
            SELECT
                se.nama,
                kbh.bagian,
                kbh.berlaku_dari,
                kbh.berlaku_sampai,
                CASE WHEN kbh.berlaku_sampai IS NULL THEN '✅ Aktif' ELSE '🔒 Selesai' END AS status
            FROM karyawan_bagian_history kbh
            LEFT JOIN sips_employees se ON kbh.nik = se.nik
            ORDER BY se.nama, kbh.berlaku_dari DESC
        """)

        if not df_history_pub.empty:
            # Highlight baris aktif
            st.dataframe(
                df_history_pub,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "nama":           st.column_config.TextColumn("Nama Karyawan"),
                    "bagian":         st.column_config.TextColumn("Bagian"),
                    "berlaku_dari":   st.column_config.DateColumn("Berlaku Dari", format="DD MMM YYYY"),
                    "berlaku_sampai": st.column_config.DateColumn("Berlaku Sampai", format="DD MMM YYYY"),
                    "status":         st.column_config.TextColumn("Status"),
                }
            )
        else:
            st.info("Belum ada data riwayat bagian SIPS. Admin dapat menambahkan via panel di atas.")

    except Exception as e:
        st.error(f"Gagal memuat data: {e}")