"""
utils.py - Fungsi pembantu: format uang, CSS, dan filter kondisi SQL
"""

import streamlit as st
import pandas as pd
from google import genai

# ─────────────────────────────────────────────────────────────────────────────
# FORMAT ANGKA & RUPIAH (STANDAR INDONESIA)
# ─────────────────────────────────────────────────────────────────────────────

def format_number(x, decimals=0) -> str:
    """Format angka biasa ke standar Indonesia (titik untuk ribuan, koma untuk desimal)."""
    if x is None or pd.isna(x):
        return "0"
    
    # Gunakan format bawaan python dulu (koma untuk ribuan, titik untuk desimal)
    if decimals > 0:
        raw_formatted = f"{float(x):,.{decimals}f}"
    else:
        raw_formatted = f"{int(x):,}"
        
    # Tukar koma menjadi titik, dan titik menjadi koma
    formatted = raw_formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
    return formatted

def format_currency(x) -> str:
    """Format ke Rp X.XXX (tanpa singkatan T/M/Jt)."""
    if x is None or pd.isna(x) or x == 0:
        return "Rp 0"
    return f"Rp {format_number(x)}"


def format_idr(x) -> str:
    """Format angka menjadi string Rupiah dengan suffix T/M/Jt."""
    if x is None or pd.isna(x) or x == 0:
        return "Rp 0"

    abs_x = abs(x)
    if abs_x >= 1e12:
        val, suffix = x / 1e12, "T"
    elif abs_x >= 1e9:
        val, suffix = x / 1e9, "M"
    elif abs_x >= 1e6:
        val, suffix = x / 1e6, "Jt"
    else:
        return format_currency(x)

    # Format 2 desimal
    formatted = f"{val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    if formatted.endswith(',00'):
        formatted = formatted[:-3]

    return f"Rp {formatted} {suffix}"


def format_idr_short(x) -> str:
    """Format angka ringkas untuk label chart (1 desimal)."""
    if x is None or pd.isna(x) or x == 0:
        return "0"

    abs_x = abs(x)
    if abs_x >= 1e12:
        val, suffix = x / 1e12, "T"
    elif abs_x >= 1e9:
        val, suffix = x / 1e9, "M"
    elif abs_x >= 1e6:
        val, suffix = x / 1e6, "Jt"
    else:
        return format_number(x)

    # Format 1 desimal
    formatted = f"{val:,.1f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    if formatted.endswith(',0'):
        formatted = formatted[:-2]

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

# ─────────────────────────────────────────────────────────────────────────────
# KOMPONEN AI ANALYST (GEMINI)
# ─────────────────────────────────────────────────────────────────────────────

def render_chat_analyst(konteks_data_teks: str, nama_halaman: str):
    """Merender antarmuka chat LLM secara sebaris (inline) dengan kotak scrollable."""
    st.divider()
    
    # Header AI
    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:28px; color: #1f77b4;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="currentColor" class="bi bi-robot" viewBox="0 0 16 16" style="margin-right: 10px;">
              <path d="M6 12.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1h-3a.5.5 0 0 1-.5-.5M3 8.062C3 6.76 4.235 5.765 5.53 5.889a28.68 28.68 0 0 1 4.94 0C11.765 5.765 13 6.76 13 8.062v1.157a.933.933 0 0 1-.765.935c-.845.147-2.34.346-4.235.346-1.895 0-3.39-.2-4.235-.346A.933.933 0 0 1 3 9.219zm4.542-.827a.25.25 0 0 0-.217.068l-.92.9a25 25 0 0 1-1.871-.183.25.25 0 0 0-.068.495c.55.076 1.232.149 2.02.193a.25.25 0 0 0 .189-.071l.754-.736.847 1.71a.25.25 0 0 0 .404.062l.932-.97a25 25 0 0 0 1.922-.188.25.25 0 0 0-.068-.495c-.538.074-1.207.145-1.98.189a.25.25 0 0 0-.166.076l-.754.785-.842-1.7a.25.25 0 0 0-.182-.135Z"/>
              <path d="M8.5 1.866a1 1 0 1 0-1 0V3h-2A4.5 4.5 0 0 0 1 7.5V8a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1v1a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-1a1 1 0 0 0 1-1V9a1 1 0 0 0-1-1v-.5A4.5 4.5 0 0 0 10.5 3h-2zM14 7.5V13a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7.5A3.5 3.5 0 0 1 5.5 4h5A3.5 3.5 0 0 1 14 7.5"/>
            </svg>
            AI Procurement Analyst
        </h1>
    """, unsafe_allow_html=True)
    st.caption(f"Tanyakan *insight* atau kesimpulan dari data yang sedang tampil di halaman **{nama_halaman}**.")

    # 1. Inisialisasi API
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        client = genai.Client(api_key=api_key)
    except Exception:
        st.error("API Key belum dikonfigurasi di file secrets.toml")
        return

    # 2. Setup Memori Sesi
    if "chat_memory" not in st.session_state:
        st.session_state.chat_memory = []

    # =========================================================
    # 3. KOTAK PERCAKAPAN SCROLLABLE (Tinggi Tetap 400px)
    # =========================================================
    chat_box = st.container(height=400)
    
    # Render histori yang sudah ada ke dalam kotak tersebut
    with chat_box:
        if not st.session_state.chat_memory:
            st.info("Ketik pertanyaan Anda di bawah untuk memulai analisis data.")
            
        for msg in st.session_state.chat_memory:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # =========================================================
    # 4. KOTAK INPUT (Inline, diam di tempat)
    # =========================================================
    # Menggunakan form agar teks otomatis terhapus (clear) setelah dikirim
    with st.form(key=f"chat_form_{nama_halaman}", clear_on_submit=True):
        col_input, col_btn = st.columns([9, 1]) # Proporsi 90% input, 10% tombol
        
        with col_input:
            user_input = st.text_input(
                "Prompt AI", 
                placeholder="Contoh: Vendor mana yang nilai PO-nya paling besar?", 
                label_visibility="collapsed" # Menyembunyikan label agar bersih
            )
        with col_btn:
            submit_btn = st.form_submit_button("Kirim", icon=":material/send:")

    # =========================================================
    # 5. LOGIKA EKSEKUSI API
    # =========================================================
    if submit_btn and user_input:
        
        # Simpan pertanyaan user ke memori
        st.session_state.chat_memory.append({"role": "user", "content": user_input})
        
        # Tampilkan langsung ke dalam kotak percakapan yang di-scroll tadi
        with chat_box:
            with st.chat_message("user"):
                st.markdown(user_input)
                
            # Render animasi loading & balasan AI
            with st.chat_message("assistant"):
                with st.spinner("Menganalisis data..."):
                    try:
                        # Rakit Prompt Rahasia
                        system_prompt = f"""
                        Anda adalah Data Analyst senior untuk sistem pengadaan barang (Procurement/SAP/SIPS).
                        
                        Berikut adalah rangkuman data faktual yang sedang dilihat user di layar saat ini:
                        --- MULAI DATA ---
                        {konteks_data_teks}
                        --- AKHIR DATA ---
                        
                        Tugas Anda:
                        1. Jawab pertanyaan user HANYA berdasarkan data di atas. Jangan mengarang vendor atau angka baru.
                        2. Berikan analisis yang tajam, langsung ke poinnya, dan profesional.
                        3. Bold angka nominal dan pastikan formatnya menggunakan standar Rupiah.
                        
                        Pertanyaan User: {user_input}
                        """
                        
                        # Eksekusi API Gemini
                        response = client.models.generate_content(
                            model="gemini-3-flash-preview",
                            contents=system_prompt
                        )
                        
                        # Tampilkan hasil
                        st.markdown(response.text)
                        
                        # Simpan ke memori agar tidak hilang saat filter diubah
                        st.session_state.chat_memory.append({"role": "assistant", "content": response.text})
                    
                    except Exception as e:
                        st.error(f"Terjadi kesalahan saat menghubungi API: {e}")