"""
v_isu.py - Halaman Isu
Feed isu seperti Discord, detail seperti blog post.
- Admin  → bisa CRUD (buat, edit, hapus)
- Viewer → hanya bisa membaca
Data disimpan di tabel melati_isu (PostgreSQL).
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import text
from config_db import get_db_engine

# ─────────────────────────────────────────────────────────────────────────────
# KONSTANTA
# ─────────────────────────────────────────────────────────────────────────────

KATEGORI_LIST  = ["Operasional", "Harga", "Kebijakan", "Vendor", "Logistik", "Lainnya"]
PRIORITAS_LIST = ["Kritis", "Tinggi", "Normal", "Rendah"]
BAGIAN_LIST    = ["Semua Bagian", "BB/BD/BP", "ALPATA", "BARUM"]
STATUS_LIST    = ["Open", "In Progress", "Resolved", "Closed"]

PRIORITAS_COLOR = {
    "Kritis": ("#e03c3c", "🔴"),
    "Tinggi": ("#f0a500", "🟠"),
    "Normal": ("#1f77b4", "🔵"),
    "Rendah": ("#09ab3b", "🟢"),
}
KATEGORI_ICON = {
    "Operasional": "⚙️", "Harga": "💰", "Kebijakan": "📋",
    "Vendor": "🏭", "Logistik": "🚚", "Lainnya": "📌",
}
STATUS_COLOR = {
    "Open":        ("#6c8ebf", "🔓"),
    "In Progress": ("#f0a500", "⏳"),
    "Resolved":    ("#09ab3b", "✅"),
    "Closed":      ("#888888", "🔒"),
}

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────

ISU_CSS = """
<style>
.isu-card {
    background: var(--secondary-background-color);
    border: 1px solid rgba(128,128,128,0.15);
    border-radius: 12px;
    padding: 18px 20px 14px 20px;
    margin-bottom: 12px;
    transition: border-color 0.15s, box-shadow 0.15s, transform 0.10s;
}
.isu-card:hover {
    border-color: rgba(31,119,180,0.45);
    box-shadow: 0 4px 18px rgba(0,0,0,0.10);
    transform: translateY(-1px);
}
.isu-judul {
    font-size: 17px; font-weight: 700;
    margin: 0 0 5px 0; line-height: 1.3;
}
.isu-deskripsi {
    font-size: 13px; opacity: 0.65;
    margin: 0 0 12px 0; line-height: 1.5;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
.isu-meta {
    display: flex; flex-wrap: wrap;
    gap: 7px; align-items: center;
}
.isu-chip {
    display: inline-flex; align-items: center; gap: 4px;
    background: rgba(128,128,128,0.10);
    padding: 3px 9px; border-radius: 12px;
    font-size: 11.5px; font-weight: 500;
}
.isu-detail-judul {
    font-size: 28px; font-weight: 700;
    line-height: 1.3; margin: 12px 0 16px 0;
}
.isu-empty {
    text-align: center; padding: 60px 20px; opacity: 0.4;
}
.isu-empty-icon { font-size: 48px; margin-bottom: 12px; }
.isu-empty-text { font-size: 16px; }
.viewer-banner {
    background: rgba(31,119,180,0.07);
    border: 1px solid rgba(31,119,180,0.18);
    border-radius: 8px;
    padding: 9px 14px;
    font-size: 13px;
    color: #1f77b4;
    margin-bottom: 16px;
    display: flex; align-items: center; gap: 8px;
}
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _engine():
    return get_db_engine()


def _ensure_table():
    """Buat tabel jika belum ada (auto-migration ringan)."""
    sql = """
    CREATE TABLE IF NOT EXISTS melati_isu (
        id           SERIAL PRIMARY KEY,
        judul        VARCHAR(300) NOT NULL,
        deskripsi    VARCHAR(500) NOT NULL,
        konten       TEXT         NOT NULL,
        kategori     VARCHAR(50)  NOT NULL DEFAULT 'Operasional',
        prioritas    VARCHAR(20)  NOT NULL DEFAULT 'Normal',
        bagian       VARCHAR(50),
        dibuat_oleh  VARCHAR(100) NOT NULL DEFAULT 'Admin',
        status       VARCHAR(20)  NOT NULL DEFAULT 'Open',
        created_at   TIMESTAMP    DEFAULT NOW(),
        updated_at   TIMESTAMP    DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_isu_created ON melati_isu (created_at DESC);
    """
    with _engine().begin() as conn:
        conn.execute(text(sql))


def _load_list(kategori=None, prioritas=None, status=None,
               bagian=None, search=None) -> pd.DataFrame:
    conds = ["1=1"]
    if kategori and kategori != "Semua":
        conds.append(f"kategori = '{kategori}'")
    if prioritas and prioritas != "Semua":
        conds.append(f"prioritas = '{prioritas}'")
    if status and status != "Semua":
        conds.append(f"status = '{status}'")
    if bagian and bagian not in ("Semua", "Semua Bagian"):
        conds.append(f"(bagian = '{bagian}' OR bagian IS NULL)")
    if search:
        s = search.replace("'", "''")
        conds.append(
            f"(judul ILIKE '%{s}%' OR deskripsi ILIKE '%{s}%'"
            f" OR dibuat_oleh ILIKE '%{s}%' OR konten ILIKE '%{s}%')"
        )
    where = " AND ".join(conds)
    q = f"""
        SELECT id, judul, deskripsi, kategori, prioritas, bagian,
               dibuat_oleh, status, created_at, updated_at
        FROM melati_isu
        WHERE {where}
        ORDER BY
            CASE prioritas
                WHEN 'Kritis' THEN 1 WHEN 'Tinggi' THEN 2
                WHEN 'Normal' THEN 3 ELSE 4 END,
            created_at DESC
    """
    with _engine().connect() as conn:
        return pd.read_sql(text(q), conn)


def _load_detail(isu_id: int) -> dict | None:
    with _engine().connect() as conn:
        df = pd.read_sql(text(f"SELECT * FROM melati_isu WHERE id = {isu_id}"), conn)
    return None if df.empty else df.iloc[0].to_dict()


def _create(judul, deskripsi, konten, kategori, prioritas, bagian, dibuat_oleh) -> int:
    sql = text("""
        INSERT INTO melati_isu
            (judul, deskripsi, konten, kategori, prioritas, bagian, dibuat_oleh,
             status, created_at, updated_at)
        VALUES
            (:judul, :deskripsi, :konten, :kategori, :prioritas, :bagian,
             :dibuat_oleh, 'Open', NOW(), NOW())
        RETURNING id
    """)
    with _engine().begin() as conn:
        r = conn.execute(sql, dict(
            judul=judul, deskripsi=deskripsi, konten=konten,
            kategori=kategori, prioritas=prioritas,
            bagian=bagian if bagian != "Semua Bagian" else None,
            dibuat_oleh=dibuat_oleh,
        ))
        return r.fetchone()[0]


def _update(isu_id, judul, deskripsi, konten, kategori, prioritas,
            bagian, dibuat_oleh, status):
    sql = text("""
        UPDATE melati_isu
        SET judul=:judul, deskripsi=:deskripsi, konten=:konten,
            kategori=:kategori, prioritas=:prioritas, bagian=:bagian,
            dibuat_oleh=:dibuat_oleh, status=:status, updated_at=NOW()
        WHERE id=:id
    """)
    with _engine().begin() as conn:
        conn.execute(sql, dict(
            id=isu_id, judul=judul, deskripsi=deskripsi, konten=konten,
            kategori=kategori, prioritas=prioritas,
            bagian=bagian if bagian not in ("Semua Bagian", None, "") else None,
            dibuat_oleh=dibuat_oleh, status=status,
        ))


def _delete(isu_id: int):
    with _engine().begin() as conn:
        conn.execute(text(f"DELETE FROM melati_isu WHERE id = {isu_id}"))


# ─────────────────────────────────────────────────────────────────────────────
# UI HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_dt(dt) -> str:
    if dt is None:
        return "-"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return str(dt)
    diff = datetime.now() - dt.replace(tzinfo=None)
    if diff.days == 0:
        h = diff.seconds // 3600
        m = (diff.seconds % 3600) // 60
        return f"{h} jam lalu" if h > 0 else (f"{m} menit lalu" if m > 0 else "Baru saja")
    if diff.days < 7:
        return f"{diff.days} hari lalu"
    return dt.strftime("%-d %b %Y")


def _go(view, isu_id=None):
    """Pindah antar view dengan rerun."""
    st.session_state['isu_view'] = view
    if isu_id is not None:
        st.session_state['isu_selected_id'] = isu_id
    st.rerun()


def _render_card(row: pd.Series, idx: int, is_admin: bool):
    prio_color, prio_icon = PRIORITAS_COLOR.get(row['prioritas'], ("#888", "⚪"))
    st_color,   st_icon   = STATUS_COLOR.get(row['status'],    ("#888", "❓"))
    kat_icon   = KATEGORI_ICON.get(row['kategori'], "📌")
    bagian_str = row['bagian'] if pd.notna(row.get('bagian')) and row['bagian'] else "Semua Bagian"
    dt_str     = _fmt_dt(row['created_at'])

    st.markdown(f"""
    <div class="isu-card">
        <p class="isu-judul">{kat_icon} {row['judul']}</p>
        <p class="isu-deskripsi">{row['deskripsi']}</p>
        <div class="isu-meta">
            <span class="isu-chip"
                  style="background:{prio_color}22;color:{prio_color};font-weight:700;">
                {prio_icon} {row['prioritas']}
            </span>
            <span class="isu-chip"
                  style="background:{st_color}22;color:{st_color};font-weight:700;">
                {st_icon} {row['status']}
            </span>
            <span class="isu-chip">📂 {row['kategori']}</span>
            <span class="isu-chip">🏢 {bagian_str}</span>
            <span style="margin-left:auto;opacity:0.45;font-size:11px;">
                ✍️ {row['dibuat_oleh']} · 🕐 {dt_str}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Tombol aksi di bawah card
    if is_admin:
        c_open, c_edit, c_del, _ = st.columns([2, 1, 1, 4])
    else:
        c_open, _ = st.columns([2, 6])

    with c_open:
        if st.button("Buka detail →", key=f"open_{row['id']}_{idx}",
                     use_container_width=True):
            _go('detail', int(row['id']))

    if is_admin:
        with c_edit:
            if st.button("✏️ Edit", key=f"edit_{row['id']}_{idx}",
                         use_container_width=True):
                _go('edit', int(row['id']))
        with c_del:
            if st.button("🗑️", key=f"del_{row['id']}_{idx}",
                         help="Hapus isu ini", use_container_width=True):
                st.session_state['isu_confirm_delete'] = int(row['id'])
                _go('detail', int(row['id']))

    st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)


def _render_form(mode="create", data: dict = None):
    """Form buat/edit. Kembalikan tuple semua field."""
    default = data or {}

    judul = st.text_input(
        "Judul Isu *",
        value=default.get('judul', ''),
        placeholder="Tuliskan judul isu secara singkat dan jelas...",
        max_chars=300,
    )
    deskripsi = st.text_area(
        "Deskripsi Singkat *",
        value=default.get('deskripsi', ''),
        placeholder="Ringkasan 1–2 kalimat yang tampil di feed...",
        max_chars=500,
        height=80,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        kategori = st.selectbox(
            "Kategori", KATEGORI_LIST,
            index=KATEGORI_LIST.index(default.get('kategori', 'Operasional'))
                  if default.get('kategori') in KATEGORI_LIST else 0,
        )
    with c2:
        prioritas = st.selectbox(
            "Prioritas", PRIORITAS_LIST,
            index=PRIORITAS_LIST.index(default.get('prioritas', 'Normal'))
                  if default.get('prioritas') in PRIORITAS_LIST else 2,
        )
    with c3:
        bagian_def = default.get('bagian') or "Semua Bagian"
        bagian = st.selectbox(
            "Bagian", BAGIAN_LIST,
            index=BAGIAN_LIST.index(bagian_def)
                  if bagian_def in BAGIAN_LIST else 0,
        )

    status = "Open"
    if mode == "edit":
        status = st.selectbox(
            "Status", STATUS_LIST,
            index=STATUS_LIST.index(default.get('status', 'Open'))
                  if default.get('status') in STATUS_LIST else 0,
        )

    dibuat_oleh = st.text_input(
        "Dibuat oleh *",
        value=default.get('dibuat_oleh', ''),
        placeholder="Nama Anda...",
        max_chars=100,
    )

    st.markdown("**Konten / Isi Lengkap** *(mendukung markdown)*")
    konten = st.text_area(
        "Konten",
        value=default.get('konten', ''),
        placeholder=(
            "Tulis detail isu di sini...\n\n"
            "## Latar Belakang\n...\n\n"
            "## Dampak\n- Poin 1\n- Poin 2\n\n"
            "## Rekomendasi\n..."
        ),
        height=300,
        label_visibility="collapsed",
    )

    if konten:
        with st.expander("👁 Preview konten", expanded=False):
            st.markdown(konten)

    return judul, deskripsi, konten, kategori, prioritas, bagian, dibuat_oleh, status


def _validate(judul, deskripsi, konten, dibuat_oleh) -> list:
    errs = []
    if not judul.strip():       errs.append("Judul tidak boleh kosong.")
    if not deskripsi.strip():   errs.append("Deskripsi tidak boleh kosong.")
    if not konten.strip():      errs.append("Konten tidak boleh kosong.")
    if not dibuat_oleh.strip(): errs.append("Nama pembuat tidak boleh kosong.")
    return errs


# ─────────────────────────────────────────────────────────────────────────────
# VIEW: FEED
# ─────────────────────────────────────────────────────────────────────────────

def _render_feed(is_admin: bool):
    st.markdown(ISU_CSS, unsafe_allow_html=True)

    col_title, col_btn = st.columns([5, 1])
    with col_title:
        st.markdown("""
            <h1 style='display:flex;align-items:center;font-size:52px;margin-bottom:0;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="42" height="42"
                     fill="currentColor" viewBox="0 0 16 16"
                     style="margin-right:12px;margin-bottom:8px;">
                    <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233
                             c-.457.778.091 1.767.98 1.767h13.713c.889 0
                             1.438-.99.98-1.767zM8 5c.535 0 .954.462.9.995l-.35
                             3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0
                             1 8 5m.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2"/>
                </svg>
                Isu
            </h1>
        """, unsafe_allow_html=True)
        st.markdown(
            "<p style='font-size:15px;opacity:0.55;margin-top:0;'>"
            "Pencatatan dan monitoring isu dari seluruh bagian Pengadaan Barang.</p>",
            unsafe_allow_html=True
        )
    with col_btn:
        st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)
        if is_admin:
            if st.button("➕ Buat Isu", type="primary",
                         use_container_width=True, key="btn_buat_top"):
                _go('create')
        else:
            st.markdown(
                "<div style='text-align:right;font-size:12px;opacity:0.4;"
                "padding-top:14px;'>👁 View Only</div>",
                unsafe_allow_html=True
            )

    st.markdown("---")

    if not is_admin:
        st.markdown("""
            <div class="viewer-banner">
                👁 &nbsp;Anda login sebagai <b>Viewer</b>, hanya dapat membaca isu.
                Hubungi administrator untuk membuat atau mengedit isu.
            </div>
        """, unsafe_allow_html=True)

    # Filter bar
    fc1, fc2, fc3, fc4, fc5 = st.columns([2.5, 1.5, 1.5, 1.5, 1.5])
    with fc1:
        search = st.text_input(
            "🔍", placeholder="Cari judul, deskripsi, konten, pembuat...",
            label_visibility="collapsed", key="isu_search"
        )
    with fc2:
        f_kat    = st.selectbox("Kategori",  ["Semua"] + KATEGORI_LIST,
                                label_visibility="collapsed", key="isu_f_kat")
    with fc3:
        f_prio   = st.selectbox("Prioritas", ["Semua"] + PRIORITAS_LIST,
                                label_visibility="collapsed", key="isu_f_prio")
    with fc4:
        f_status = st.selectbox("Status",    ["Semua"] + STATUS_LIST,
                                label_visibility="collapsed", key="isu_f_status")
    with fc5:
        f_bagian = st.selectbox("Bagian",    ["Semua"] + BAGIAN_LIST[1:],
                                label_visibility="collapsed", key="isu_f_bagian")

    try:
        _ensure_table()
        df = _load_list(
            kategori  = f_kat    if f_kat    != "Semua" else None,
            prioritas = f_prio   if f_prio   != "Semua" else None,
            status    = f_status if f_status != "Semua" else None,
            bagian    = f_bagian if f_bagian != "Semua" else None,
            search    = search   or None,
        )
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        return

    # Metrik ringkasan
    if not df.empty:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Isu", len(df))
        m2.metric("Open",         int((df['status'] == 'Open').sum()))
        m3.metric("In Progress",  int((df['status'] == 'In Progress').sum()))
        m4.metric("Selesai",      int(df['status'].isin(['Resolved','Closed']).sum()))
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    if df.empty:
        st.markdown("""
            <div class="isu-empty">
                <div class="isu-empty-icon">📭</div>
                <div class="isu-empty-text">Belum ada isu yang sesuai filter.</div>
            </div>
        """, unsafe_allow_html=True)
    else:
        for idx, row in df.iterrows():
            _render_card(row, idx, is_admin)


# ─────────────────────────────────────────────────────────────────────────────
# VIEW: DETAIL
# ─────────────────────────────────────────────────────────────────────────────

def _render_detail(isu_id: int, is_admin: bool):
    st.markdown(ISU_CSS, unsafe_allow_html=True)

    if st.button("← Kembali ke Feed", key="btn_back"):
        _go('feed')

    try:
        data = _load_detail(isu_id)
    except Exception as e:
        st.error(f"Gagal memuat isu: {e}")
        return
    if data is None:
        st.error("Isu tidak ditemukan.")
        return

    prio_color, prio_icon = PRIORITAS_COLOR.get(data['prioritas'], ("#888", "⚪"))
    st_color,   st_icon   = STATUS_COLOR.get(data['status'],    ("#888", "❓"))
    kat_icon   = KATEGORI_ICON.get(data['kategori'], "📌")
    bagian_str = data['bagian'] if data.get('bagian') else "Semua Bagian"

    # Header detail
    st.markdown(f"""
    <div style='border-bottom:1px solid rgba(128,128,128,0.2);
                padding-bottom:20px;margin-bottom:24px;'>
        <div style='display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;'>
            <span style='background:{prio_color}22;color:{prio_color};
                  padding:4px 12px;border-radius:20px;font-size:12px;font-weight:700;'>
                {prio_icon} {data['prioritas']}
            </span>
            <span style='background:{st_color}22;color:{st_color};
                  padding:4px 12px;border-radius:20px;font-size:12px;font-weight:700;'>
                {st_icon} {data['status']}
            </span>
            <span style='background:rgba(128,128,128,0.12);
                  padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;'>
                {kat_icon} {data['kategori']}
            </span>
            <span style='background:rgba(128,128,128,0.12);
                  padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;'>
                🏢 {bagian_str}
            </span>
        </div>
        <h1 class='isu-detail-judul'>{data['judul']}</h1>
        <p style='font-size:13px;opacity:0.45;margin:0;'>
            ✍️ {data['dibuat_oleh']} &nbsp;·&nbsp;
            🕐 Dibuat: {_fmt_dt(data['created_at'])} &nbsp;·&nbsp;
            🔄 Diperbarui: {_fmt_dt(data['updated_at'])}
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"> *{data['deskripsi']}*")
    st.markdown("---")
    st.markdown(data['konten'])
    st.markdown("---")

    # Aksi: hanya admin
    if is_admin:
        col_edit, col_del, _ = st.columns([1, 1, 5])
        with col_edit:
            if st.button("✏️ Edit Isu", use_container_width=True, key="btn_edit"):
                _go('edit', isu_id)
        with col_del:
            if st.button("🗑️ Hapus", use_container_width=True,
                         type="secondary", key="btn_del"):
                st.session_state['isu_confirm_delete'] = isu_id
                st.rerun()

        # Konfirmasi hapus
        if st.session_state.get('isu_confirm_delete') == isu_id:
            st.warning("⚠️ Yakin ingin menghapus isu ini? Tidak bisa dibatalkan.")
            cc1, cc2, _ = st.columns([1, 1, 5])
            with cc1:
                if st.button("✅ Ya, Hapus", type="primary", key="btn_confirm_del"):
                    try:
                        _delete(isu_id)
                        st.session_state.pop('isu_confirm_delete', None)
                        _go('feed')
                    except Exception as e:
                        st.error(f"Gagal menghapus: {e}")
            with cc2:
                if st.button("❌ Batal", key="btn_cancel_del"):
                    st.session_state.pop('isu_confirm_delete', None)
                    st.rerun()
    else:
        st.markdown("""
            <div class="viewer-banner">
                👁 &nbsp;Anda login sebagai <b>Viewer</b>.
                Hanya admin yang dapat mengedit atau menghapus isu.
            </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# VIEW: CREATE
# ─────────────────────────────────────────────────────────────────────────────

def _render_create():
    st.markdown(ISU_CSS, unsafe_allow_html=True)

    if st.button("← Kembali ke Feed", key="btn_back_create"):
        _go('feed')

    st.markdown("### ➕ Buat Isu Baru")
    st.markdown("---")

    judul, deskripsi, konten, kategori, prioritas, bagian, dibuat_oleh, _ = \
        _render_form(mode="create")

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    cs, cc, _ = st.columns([1.3, 1, 4])
    with cs:
        if st.button("💾 Simpan Isu", type="primary", use_container_width=True,
                     key="btn_save_create"):
            errs = _validate(judul, deskripsi, konten, dibuat_oleh)
            if errs:
                for e in errs:
                    st.error(e)
            else:
                try:
                    _ensure_table()
                    new_id = _create(
                        judul.strip(), deskripsi.strip(), konten.strip(),
                        kategori, prioritas, bagian, dibuat_oleh.strip()
                    )
                    st.success("✅ Isu berhasil dibuat!")
                    _go('detail', new_id)
                except Exception as e:
                    st.error(f"Gagal menyimpan: {e}")
    with cc:
        if st.button("Batal", use_container_width=True, key="btn_cancel_create"):
            _go('feed')


# ─────────────────────────────────────────────────────────────────────────────
# VIEW: EDIT
# ─────────────────────────────────────────────────────────────────────────────

def _render_edit(isu_id: int):
    st.markdown(ISU_CSS, unsafe_allow_html=True)

    if st.button("← Kembali ke Detail", key="btn_back_edit"):
        _go('detail', isu_id)

    st.markdown("### ✏️ Edit Isu")
    st.markdown("---")

    try:
        data = _load_detail(isu_id)
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        return
    if data is None:
        st.error("Isu tidak ditemukan.")
        return

    judul, deskripsi, konten, kategori, prioritas, bagian, dibuat_oleh, status = \
        _render_form(mode="edit", data=data)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    cs, cc, _ = st.columns([1.6, 1, 4])
    with cs:
        if st.button("💾 Simpan Perubahan", type="primary", use_container_width=True,
                     key="btn_save_edit"):
            errs = _validate(judul, deskripsi, konten, dibuat_oleh)
            if errs:
                for e in errs:
                    st.error(e)
            else:
                try:
                    _update(isu_id, judul.strip(), deskripsi.strip(), konten.strip(),
                            kategori, prioritas, bagian, dibuat_oleh.strip(), status)
                    st.success("✅ Perubahan berhasil disimpan!")
                    _go('detail', isu_id)
                except Exception as e:
                    st.error(f"Gagal menyimpan: {e}")
    with cc:
        if st.button("Batal", use_container_width=True, key="btn_cancel_edit"):
            _go('detail', isu_id)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def render(**kwargs):
    # is_admin dikirim dari app.py melalui _summary_view_args
    is_admin_user: bool = kwargs.get('is_admin', False)

    # Inisialisasi session state
    for k, v in [('isu_view', 'feed'), ('isu_selected_id', None),
                 ('isu_confirm_delete', None)]:
        if k not in st.session_state:
            st.session_state[k] = v

    view   = st.session_state.get('isu_view', 'feed')
    isu_id = st.session_state.get('isu_selected_id')

    if view == 'feed':
        _render_feed(is_admin_user)
    elif view == 'detail' and isu_id:
        _render_detail(isu_id, is_admin_user)
    elif view == 'create' and is_admin_user:
        _render_create()
    elif view == 'edit' and isu_id and is_admin_user:
        _render_edit(isu_id)
    else:
        # Viewer mencoba akses halaman admin → redirect ke feed
        _render_feed(is_admin_user)