"""
utils.py - Fungsi pembantu: format uang, CSS, dan filter kondisi SQL
"""

import streamlit as st
import pandas as pd
from google import genai
import base64
import os

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
# SIPS WHERE CLAUSE BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_sips_where(date_from=None, date_to=None,
                     selected_nama=None, selected_bagian=None,
                     extra: list = None) -> str:
    """
    Bangun WHERE clause untuk query vw_sips.
    - Filter bagian hanya aktif jika selected_bagian bukan ['All']
    - Sertakan extra=['nilai_sla IS NOT NULL'] dsb. jika perlu kondisi tambahan
    """
    wp = ["1=1"]
    if extra:
        wp.extend(extra)
    if date_from:
        wp.append(f"requisition_date >= '{date_from}'")
    if date_to:
        wp.append(f"requisition_date <= '{date_to}'")
    if selected_bagian and "All" not in selected_bagian:
        bg = ", ".join(f"'{b}'" for b in selected_bagian)
        wp.append(f"bagian IN ({bg})")
    if selected_nama and "All" not in selected_nama:
        nms = ", ".join(f"'{n}'" for n in selected_nama)
        wp.append(f"nama IN ({nms})")
    return " AND ".join(wp)

# ─────────────────────────────────────────────────────────────────────────────
# KOMPONEN AI ANALYST (GEMINI)
# ─────────────────────────────────────────────────────────────────────────────

def render_chat_analyst(konteks_data_teks: str, nama_halaman: str):
    """Merender antarmuka chat LLM secara sebaris (inline) dengan kotak scrollable."""
    st.divider()

    img_path = "assets/Mia_icon.png"
    img_b64 = ""

    if os.path.exists(img_path):
        with open(img_path, "rb") as img_file:
            img_b64 = base64.b64encode(img_file.read()).decode()

    if img_b64:
        # Jika gambar ditemukan, jadikan icon bulat (border-radius: 50%)
        icon_html = f'<img src="data:image/png;base64,{img_b64}" width="38" height="38" style="margin-right: 12px; border-radius: 50%; object-fit: cover; border: 2px solid #1f77b4;">'
    else:
        # Fallback (cadangan) jika gambar tidak ditemukan, gunakan emoji
        icon_html = '<span style="font-size: 32px; margin-right: 12px;">🕵️‍♀️</span>'
    
    # Header AI
    st.markdown(f"""
        <h1 style='display: flex; align-items: center; font-size:28px; color: #1f77b4; margin-bottom: 5px;'>
            {icon_html}
            Tanya ke Mia (Asisten Pengadaan Barang)
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
            with st.chat_message("assistant", avatar="assets/Mia_icon.png"):
                with st.spinner("Tunggu, Mia sedang menganalisis data..."):
                    try:
                        # Rakit Prompt Rahasia
                        system_prompt = f"""
                        Kamu adalah asisten AI bernama Mia, seorang analis data perempuan yang ceria, sangat teliti, dan bersikap layaknya "detektif" andal yang sedang menyelidiki data sistem perusahaan.
                        
                        Tugas dan Aturan Ketat Mia:
                        1. IDENTITAS & GAYA BAHASA: Namamu adalah Mia, detektif data pengadaan. HANYA perkenalkan dirimu secara penuh jika user SECARA EKSPLISIT bertanya "siapa kamu", "kamu siapa", "perkenalkan dirimu", atau sejenisnya. Jika user hanya menyapa ("halo", "hai", dll.) atau langsung mengajukan pertanyaan data, JANGAN memperkenalkan diri — langsung jawab pertanyaannya saja dengan gaya yang ceria dan to the point. Gunakan gaya bahasa yang ceria, ramah, sedikit playful (gunakan kata "aku" dan "kamu"), tapi tetap SANGAT OBJEKTIF dan tajam saat menganalisis angka.
                        2. FAKTUAL & OBJEKTIF: Jawab HANYA berdasarkan data di bawah. JIKA DATA TIDAK ADA, katakan dengan nada detektif: "Hmm, sepertinya jejak data itu tidak kutemukan di layar saat ini 🔍."
                        3. NO HALLUCINATION: Sebagai detektif, kamu pantang mengarang bukti! JANGAN PERNAH mengarang angka, nama vendor, atau metrik yang tidak ada di data.
                        4. BATASAN DOMAIN: Kamu hanya menyelidiki kasus transaksi, anggaran, vendor, dan dashboard ini. Tolak dengan sopan dan lucu jika diajak bahas resep masakan, coding, atau hal di luar kasus.
                        5. FORMAT: Berikan analisis yang terstruktur, tebalkan angka penting, pastikan format angka menggunakan standar Rupiah yang rapi, dan tambahkan sedikit emoji (seperti 📉, 💡, 🚨) agar laporannya tidak membosankan.
                        
                        Berikut adalah BUKTI-BUKTI DATA yang sedang tayang di layar saat ini:
                        --- MULAI BUKTI DATA ---
                        {konteks_data_teks}
                        --- AKHIR BUKTI DATA ---
                        
                        Pertanyaan dari User: {user_input}
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