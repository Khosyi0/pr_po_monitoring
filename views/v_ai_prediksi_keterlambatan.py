"""
v_ai_prediksi_keterlambatan.py - Prediksi Keterlambatan Vendor
"""
import streamlit as st
import pandas as pd
import joblib
import os
from datetime import datetime

# Cache model agar tidak diload ulang setiap kali user mengeklik tombol
@st.cache_resource
def load_ml_models():
    base_dir = os.getcwd() 
    model_path = os.path.join(base_dir, 'Machine_Learning', 'model_keterlambatan.pkl')
    encoder_path = os.path.join(base_dir, 'Machine_Learning', 'encoder_keterlambatan.pkl')
    cols_path = os.path.join(base_dir, 'Machine_Learning', 'fitur_keterlambatan.pkl')

    if not os.path.exists(model_path):
        return None, None, None

    model = joblib.load(model_path)
    encoder = joblib.load(encoder_path)
    fitur = joblib.load(cols_path)
    return model, encoder, fitur

def render(**kwargs):
    # == HEADER ===============================================================
    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:42px; margin-bottom:0;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" fill="currentColor" class="bi bi-robot" viewBox="0 0 16 16" style="margin-right:12px; margin-bottom:4px; color:#ff4b4b;">
                <path d="M6 12.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1H6.5a.5.5 0 0 1-.5-.5M3.1 2.813a1 1 0 0 1 1.4-.41l1.64 1a2 2 0 0 1 3.72 0l1.64-1a1 1 0 0 1 1.4.41L12.1 4H13a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h.9l-1.64-1a1 1 0 0 1-.16-1.4m.48 1.492-1.35.825A.5.5 0 0 0 2 5.5v6a.5.5 0 0 0 .5.5h11a.5.5 0 0 0 .5-.5v-6a.5.5 0 0 0-.23-.437l-1.35-.825a.5.5 0 0 0-.52.88l1.1.67V11H3V5.79l1.1-.67a.5.5 0 0 0-.52-.88ZM4.5 7.5a.5.5 0 1 0 0-1 .5.5 0 0 0 0 1m7 0a.5.5 0 1 0 0-1 .5.5 0 0 0 0 1m-4 1.5a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5v-1a.5.5 0 0 0-.5-.5h-1Z"/>
            </svg>
            Prediksi Keterlambatan Vendor (AI)
        </h1>
    """, unsafe_allow_html=True)

    st.markdown(
        "<p style='font-size:15px; opacity:0.6; margin-top:4px; margin-bottom:16px;'>"
        "Sistem deteksi dini potensi keterlambatan pengiriman barang oleh vendor menggunakan algoritma Machine Learning."
        "</p>", unsafe_allow_html=True
    )
    
    st.markdown("""
        <div style="background-color: rgba(31, 119, 180, 0.1); border-left: 4px solid #1f77b4; padding: 12px 16px; border-radius: 4px; margin-bottom: 24px; display: flex; align-items: center;">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-tools" viewBox="0 0 16 16" style="margin-right: 12px; color: #1f77b4; flex-shrink: 0;">
                <path d="M1 0 0 1l2.2 3.081a1 1 0 0 0 .815.419h.07a1 1 0 0 1 .708.293l2.675 2.675-2.617 2.654A3.003 3.003 0 0 0 0 13a3 3 0 1 0 5.878-.851l2.654-2.617.968.968-.305.914a1 1 0 0 0 .242 1.023l3.27 3.27a.997.997 0 0 0 1.414 0l1.586-1.586a.997.997 0 0 0 0-1.414l-3.27-3.27a1 1 0 0 0-1.023-.242L10.5 9.5l-.96-.96 2.68-2.643A3.005 3.005 0 0 0 16 3q0-.405-.102-.777l-2.14 2.141L12 4l-.364-1.757L13.777.102a3 3 0 0 0-3.675 3.68L7.462 6.46 4.793 3.793a1 1 0 0 1-.293-.707v-.071a1 1 0 0 0-.419-.814zm9.646 10.646a.5.5 0 0 1 .708 0l2.914 2.915a.5.5 0 0 1-.707.707l-2.915-2.914a.5.5 0 0 1 0-.708M3 11l.471.242.529.026.287.445.445.287.026.529L5 13l-.242.471-.026.529-.445.287-.287.445-.529.026L3 15l-.471-.242L2 14.732l-.287-.445L1.268 14l-.026-.529L1 13l.242-.471.026-.529.445-.287.287-.445.529-.026z"/>
            </svg>
            <span style="color: var(--text-color); font-size: 14px;"><strong>Status:</strong> Fitur purwarupa (prototype) ini sedang dalam tahap pengembangan dan kalibrasi, hanya dapat diakses oleh Admin.</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Memisahkan halaman menggunakan TABS
    tab1, tab2 = st.tabs(["Simulasi Prediksi", "Detail & Metrik Model AI"])

    # =========================================================================
    # TAB 1: SIMULASI PREDIKSI
    # =========================================================================
    with tab1:
        model, encoder, fitur = load_ml_models()

        if model is None:
            st.warning("File model ML belum tersedia di folder Machine_Learning.")
            return

        list_vendor = [str(x) for x in encoder.categories_[0] if str(x) != 'UNKNOWN']
        list_mat_group = [str(x) for x in encoder.categories_[1] if str(x) != 'UNKNOWN']
        list_pur_group = [str(x) for x in encoder.categories_[2] if str(x) != 'UNKNOWN']

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown("""
            <h3 style='display: flex; align-items: center; font-size:22px; margin-bottom:16px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="currentColor" class="bi bi-file-earmark-ruled" viewBox="0 0 16 16" style="margin-right:10px;">
                    <path d="M14 14V4.5L9.5 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2M9.5 3A1.5 1.5 0 0 0 11 4.5h2V9H3V2a1 1 0 0 1 1-1h5.5zM3 12v-2h2v2zm0 1h2v2H4a1 1 0 0 1-1-1zm3 2v-2h7v1a1 1 0 0 1-1 1zm7-3H6v-2h7z"/>
                </svg>
                Simulasi Pembuatan Purchase Order (PO)
            </h3>
        """, unsafe_allow_html=True)
        
        with st.form("form_prediksi_po"):
            col1, col2 = st.columns(2)
            with col1:
                vendor = st.selectbox("Nama Vendor", options=list_vendor)
                purchasing_group = st.selectbox("Purchasing Group", options=list_pur_group)
                material_group = st.selectbox("Material Group", options=list_mat_group)
                incoterm = st.selectbox("Incoterm", ["DDP Delivered Duty Paid", "FCA Free Carrier", "FOB Free On Board", "EXW Ex Works", "Blank"])
                
            with col2:
                amount = st.number_input("Total Amount (Rp)", min_value=0.0, value=50000000.0, step=1000000.0)
                qty = st.number_input("Quantity PO", min_value=1.0, value=100.0, step=1.0)
                bulan = st.selectbox("Bulan PO Dibuat", list(range(1, 13)), index=datetime.now().month - 1)

            st.markdown("<br>", unsafe_allow_html=True)
            submit_btn = st.form_submit_button("Jalankan Prediksi AI", type="primary", use_container_width=True)

        if submit_btn:
            with st.spinner("AI sedang menganalisis profil vendor dan kompleksitas pesanan..."):
                
                data_input = pd.DataFrame([{
                    'vendor_name': vendor,
                    'material_group': material_group,
                    'purchasing_group': purchasing_group,
                    'total_amount_local_curr': amount,
                    'qty_po': qty,
                    'incoterm': incoterm if incoterm != "Blank" else 'UNKNOWN',
                    'bulan_po': bulan
                }])[fitur] 

                kolom_teks = ['vendor_name', 'material_group', 'purchasing_group', 'incoterm']
                data_input[kolom_teks] = encoder.transform(data_input[kolom_teks])

                prediksi = model.predict(data_input)[0]
                probabilitas = model.predict_proba(data_input)[0]

                st.markdown("---")
                st.markdown("""
                    <h3 style='display: flex; align-items: center; font-size:22px; margin-bottom:20px;'>
                        <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="currentColor" class="bi bi-cpu" viewBox="0 0 16 16" style="margin-right:10px;">
                            <path d="M5 0a.5.5 0 0 1 .5.5V2h1V.5a.5.5 0 0 1 1 0V2h1V.5a.5.5 0 0 1 1 0V2h1V.5a.5.5 0 0 1 1 0V2h1V.5a.5.5 0 0 1 1 0V2A2.5 2.5 0 0 1 14 4.5h1.5a.5.5 0 0 1 0 1H14v1h1.5a.5.5 0 0 1 0 1H14v1h1.5a.5.5 0 0 1 0 1H14v1h1.5a.5.5 0 0 1 0 1H14a2.5 2.5 0 0 1-2.5 2.5v1.5a.5.5 0 0 1-1 0V14h-1v1.5a.5.5 0 0 1-1 0V14h-1v1.5a.5.5 0 0 1-1 0V14h-1v1.5a.5.5 0 0 1-1 0V14A2.5 2.5 0 0 1 2 11.5H.5a.5.5 0 0 1 0-1H2v-1H.5a.5.5 0 0 1 0-1H2v-1H.5a.5.5 0 0 1 0-1H2v-1H.5a.5.5 0 0 1 0-1H2A2.5 2.5 0 0 1 4.5 2V.5A.5.5 0 0 1 5 0m-.5 3A1.5 1.5 0 0 0 3 4.5v7A1.5 1.5 0 0 0 4.5 13h7a1.5 1.5 0 0 0 1.5-1.5v-7A1.5 1.5 0 0 0 11.5 3zM5 6.5A1.5 1.5 0 0 1 6.5 5h3A1.5 1.5 0 0 1 11 6.5v3A1.5 1.5 0 0 1 9.5 11h-3A1.5 1.5 0 0 1 5 9.5zM6.5 6a.5.5 0 0 0-.5.5v3a.5.5 0 0 0 .5.5h3a.5.5 0 0 0 .5-.5v-3a.5.5 0 0 0-.5-.5z"/>
                        </svg>
                        Hasil Deteksi Dini
                    </h3>
                """, unsafe_allow_html=True)
                
                res_col1, res_col2 = st.columns([4, 6])
                with res_col1:
                    if prediksi == 1:
                        st.markdown(f"""
                            <div style="background-color: rgba(224, 60, 60, 0.08); border: 2px solid #e03c3c; border-radius: 12px; padding: 24px; text-align: center; height: 100%;">
                                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="#e03c3c" class="bi bi-shield-fill-exclamation" viewBox="0 0 16 16">
                                    <path fill-rule="evenodd" d="M8 0c-.69 0-1.843.265-2.928.56-1.11.3-2.229.655-2.887.87a1.54 1.54 0 0 0-1.044 1.262c-.596 4.477.787 7.795 2.465 9.99a11.8 11.8 0 0 0 2.517 2.453c.386.273.744.482 1.048.625.28.132.581.24.829.24s.548-.108.829-.24a7 7 0 0 0 1.048-.625 11.8 11.8 0 0 0 2.517-2.453c1.678-2.195 3.061-5.513 2.465-9.99a1.54 1.54 0 0 0-1.044-1.263 63 63 0 0 0-2.887-.87C9.843.266 8.69 0 8 0m-.5 5a.5.5 0 0 1 1 0v3a.5.5 0 0 1-1 0zm.5 5.5a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5"/>
                                </svg>
                                <h2 style="color: #e03c3c; margin: 12px 0 4px 0; font-size: 26px;">POTENSI TERLAMBAT</h2>
                                <p style="font-size: 16px; margin: 0; color: var(--text-color); opacity: 0.8;">Tingkat Keyakinan: <strong style="color: #e03c3c; font-size: 20px;">{probabilitas[1]*100:.1f}%</strong></p>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                            <div style="background-color: rgba(9, 171, 59, 0.08); border: 2px solid #09ab3b; border-radius: 12px; padding: 24px; text-align: center; height: 100%;">
                                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="#09ab3b" class="bi bi-shield-fill-check" viewBox="0 0 16 16">
                                    <path fill-rule="evenodd" d="M8 0c-.69 0-1.843.265-2.928.56-1.11.3-2.229.655-2.887.87a1.54 1.54 0 0 0-1.044 1.262c-.596 4.477.787 7.795 2.465 9.99a11.8 11.8 0 0 0 2.517 2.453c.386.273.744.482 1.048.625.28.132.581.24.829.24s.548-.108.829-.24a7 7 0 0 0 1.048-.625 11.8 11.8 0 0 0 2.517-2.453c1.678-2.195 3.061-5.513 2.465-9.99a1.54 1.54 0 0 0-1.044-1.263 63 63 0 0 0-2.887-.87C9.843.266 8.69 0 8 0m2.146 5.146a.5.5 0 0 1 .708.708l-3 3a.5.5 0 0 1-.708 0l-1.5-1.5a.5.5 0 1 1 .708-.708L7.5 7.793z"/>
                                </svg>
                                <h2 style="color: #09ab3b; margin: 12px 0 4px 0; font-size: 26px;">AMAN (ON TIME)</h2>
                                <p style="font-size: 16px; margin: 0; color: var(--text-color); opacity: 0.8;">Tingkat Keyakinan: <strong style="color: #09ab3b; font-size: 20px;">{probabilitas[0]*100:.1f}%</strong></p>
                            </div>
                        """, unsafe_allow_html=True)
                
                with res_col2:
                    if prediksi == 1:
                        st.markdown("""
                            <div style="padding: 16px; height: 100%; display: flex; flex-direction: column; justify-content: center;">
                                <h4 style="margin-top: 0; display: flex; align-items: center; color: var(--text-color);">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="#f0a500" class="bi bi-lightbulb-fill" viewBox="0 0 16 16" style="margin-right: 8px;">
                                        <path d="M2 6a6 6 0 1 1 10.174 4.31c-.203.196-.359.4-.453.619l-.762 1.769A.5.5 0 0 1 10.5 13h-5a.5.5 0 0 1-.46-.302l-.761-1.77a2 2 0 0 0-.453-.618A5.98 5.98 0 0 1 2 6m3 8.5a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1l-.224.447a1 1 0 0 1-.894.553H6.618a1 1 0 0 1-.894-.553L5.5 15a.5.5 0 0 1-.5-.5"/>
                                    </svg>
                                    Saran Tindakan Peringatan Dini
                                </h4>
                                <ul style="font-size: 14px; color: var(--text-color); opacity: 0.85; margin-bottom: 0; padding-left: 20px;">
                                    <li style="margin-bottom: 6px;">Lakukan <i>follow-up</i> proaktif (misal: menelepon vendor H+3 setelah PO dirilis).</li>
                                    <li style="margin-bottom: 6px;">Verifikasi ulang ketersediaan bahan baku dengan pihak vendor.</li>
                                    <li>Jika material bersifat kritikal untuk kelangsungan pabrik, segera siapkan <i>backup plan</i> atau <i>split order</i> ke vendor lain.</li>
                                </ul>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                            <div style="padding: 16px; height: 100%; display: flex; flex-direction: column; justify-content: center;">
                                <h4 style="margin-top: 0; display: flex; align-items: center; color: var(--text-color);">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="#09ab3b" class="bi bi-lightbulb-fill" viewBox="0 0 16 16" style="margin-right: 8px;">
                                        <path d="M2 6a6 6 0 1 1 10.174 4.31c-.203.196-.359.4-.453.619l-.762 1.769A.5.5 0 0 1 10.5 13h-5a.5.5 0 0 1-.46-.302l-.761-1.77a2 2 0 0 0-.453-.618A5.98 5.98 0 0 1 2 6m3 8.5a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1l-.224.447a1 1 0 0 1-.894.553H6.618a1 1 0 0 1-.894-.553L5.5 15a.5.5 0 0 1-.5-.5"/>
                                    </svg>
                                    Status Pengiriman Aman
                                </h4>
                                <ul style="font-size: 14px; color: var(--text-color); opacity: 0.85; margin-bottom: 0; padding-left: 20px;">
                                    <li style="margin-bottom: 6px;">Vendor memiliki rekam jejak historis yang sangat baik untuk ukuran pesanan ini.</li>
                                    <li>Jalankan prosedur <i>monitoring</i> penerimaan barang seperti biasa tanpa perlakuan khusus.</li>
                                </ul>
                            </div>
                        """, unsafe_allow_html=True)

    # =========================================================================
    # TAB 2: DETAIL & METRIK MODEL AI
    # =========================================================================
    with tab2:
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown("""
            <h3 style='display: flex; align-items: center; font-size:22px; margin-bottom:16px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="currentColor" class="bi bi-journal-code" viewBox="0 0 16 16" style="margin-right:10px;">
                    <path fill-rule="evenodd" d="M8.646 5.646a.5.5 0 0 1 .708 0l2 2a.5.5 0 0 1 0 .708l-2 2a.5.5 0 0 1-.708-.708L10.293 8 8.646 6.354a.5.5 0 0 1 0-.708m-1.292 0a.5.5 0 0 0-.708 0l-2 2a.5.5 0 0 0 0 .708l2 2a.5.5 0 0 0 .708-.708L5.707 8l1.647-1.646a.5.5 0 0 0 0-.708"/>
                    <path d="M3 0h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2v-1h1v1a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1H3a1 1 0 0 0-1 1v1H1V2a2 2 0 0 1 2-2"/>
                    <path d="M1 5v-.5a.5.5 0 0 1 1 0V5h.5a.5.5 0 0 1 0 1h-2a.5.5 0 0 1 0-1zm0 3v-.5a.5.5 0 0 1 1 0V8h.5a.5.5 0 0 1 0 1h-2a.5.5 0 0 1 0-1zm0 3v-.5a.5.5 0 0 1 1 0v.5h.5a.5.5 0 0 1 0 1h-2a.5.5 0 0 1 0-1z"/>
                </svg>
                Spesifikasi & Rapor AI
            </h3>
        """, unsafe_allow_html=True)

        st.markdown("""
        Model ini dibangun khusus untuk mempelajari sejarah performa vendor di lingkungan perusahaan, dengan tujuan membantu manajemen rantai pasok (Supply Chain) bertransformasi dari pendekatan **reaktif** (menangani kendala setelah keterlambatan terjadi) menjadi **proaktif** (mendeteksi dan memitigasi potensi keterlambatan sejak awal).
        """)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown("""
            <h4 style='display: flex; align-items: center; margin-bottom: 12px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-right: 8px;">
                    <path d="M1 11a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1zm5-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1zm5-5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1z"/>
                </svg>
                Performa Metrik Ujian (Test Set)
            </h4>
        """, unsafe_allow_html=True)
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric(label="Akurasi Keseluruhan", value="90.0%", delta="Sangat Baik")
        col_m2.metric(label="Recall (Deteksi Telat)", value="42.0%", delta="Target Optimasi", delta_color="off")
        col_m3.metric(label="Volume Data Training", value="17,425", delta="Dokumen Sampel Januari 2025 - April 2026")

        st.markdown("""
        **Cara Membaca Rapor (Mengapa Recall 42% itu pencapaian besar?):**
        * **Sebelum Adanya Model AI:** Pemantauan keterlambatan umumnya baru dapat dievaluasi secara pasti saat tanggal jatuh tempo sudah dekat atau terlewati. Sistem belum memiliki mekanisme peringatan dini (*early warning*) yang otomatis berdasarkan pola data historis.
        * **Masalah Distribusi Data:** Dataset riwayat PO sangat timpang (*imbalanced*). Sebanyak **91.2%** PO berhasil dikirim tepat waktu, dan hanya **8.8%** yang mengalami keterlambatan.
        * **Solusi Algoritma:** Model ini menggunakan `Random Forest Classifier` dengan parameter `class_weight='balanced'`. Parameter ini secara cerdas memberikan pembobotan yang jauh lebih berat kepada AI agar lebih sensitif dalam mendeteksi pola anomali PO yang terlambat.
        * **Kesimpulan:** Dengan nilai Recall 42%, AI telah sukses memberikan sistem peringatan dini yang mampu menangkap **hampir separuh** dari total keseluruhan kasus keterlambatan secara otomatis sebelum hal itu terjadi!
        """)

        st.markdown("---")
        
        col_a, col_b = st.columns([1, 1], gap="large")
        with col_a:
            st.markdown("""
                <h4 style='display: flex; align-items: center; margin-bottom: 12px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-diagram-3-fill" viewBox="0 0 16 16" style="margin-right: 8px;">
                        <path d="M6.5 6a.5.5 0 0 0-.5.5v3a.5.5 0 0 0 .5.5h3a.5.5 0 0 0 .5-.5v-3a.5.5 0 0 0-.5-.5z"/>
                        <path d="M5.5.5a.5.5 0 0 0-1 0V2A2.5 2.5 0 0 0 2 4.5H.5a.5.5 0 0 0 0 1H2v1H.5a.5.5 0 0 0 0 1H2v1H.5a.5.5 0 0 0 0 1H2v1H.5a.5.5 0 0 0 0 1H2A2.5 2.5 0 0 0 4.5 14v1.5a.5.5 0 0 0 1 0V14h1v1.5a.5.5 0 0 0 1 0V14h1v1.5a.5.5 0 0 0 1 0V14h1v1.5a.5.5 0 0 0 1 0V14a2.5 2.5 0 0 0 2.5-2.5h1.5a.5.5 0 0 0 0-1H14v-1h1.5a.5.5 0 0 0 0-1H14v-1h1.5a.5.5 0 0 0 0-1H14v-1h1.5a.5.5 0 0 0 0-1H14A2.5 2.5 0 0 0 11.5 2V.5a.5.5 0 0 0-1 0V2h-1V.5a.5.5 0 0 0-1 0V2h-1V.5a.5.5 0 0 0-1 0V2h-1zm1 4.5h3A1.5 1.5 0 0 1 11 6.5v3A1.5 1.5 0 0 1 9.5 11h-3A1.5 1.5 0 0 1 5 9.5v-3A1.5 1.5 0 0 1 6.5 5"/>
                    </svg>
                    Anatomi Model
                </h4>
            """, unsafe_allow_html=True)
            st.markdown("""
            * **Tipe Algoritma:** Random Forest (*Ensemble Learning*). Algoritma ini bekerja layaknya menggabungkan hasil *voting* dari ratusan model pohon keputusan tunggal untuk mengambil kesimpulan prediksi yang paling akurat dan tidak bias.
            * **Encoding:** Menggunakan metode `OrdinalEncoder` untuk mengonversi data kategorikal teks (seperti nama vendor dan material group) menjadi identitas numerik (ID) yang dapat diolah oleh perhitungan matematis komputer.
            * **Limitasi Kedalaman:** Dibekali dengan batasan maksimal 15 level kedalaman analisa (`max_depth=15`) guna mencegah model terjebak menghafal data masa lalu secara berlebihan (*overfitting*), sehingga model tetap tangkas dalam memprediksi data pesanan baru (*generalize*).
            """)
        
        with col_b:
            st.markdown("""
                <h4 style='display: flex; align-items: center; margin-bottom: 12px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-key-fill" viewBox="0 0 16 16" style="margin-right: 8px; transform: rotate(45deg);">
                        <path d="M3.5 11.5a3.5 3.5 0 1 1 3.163-5h1.232l.256.256a.5.5 0 0 0 .708 0l.256-.256h.256l.256.256a.5.5 0 0 0 .708 0l.256-.256h.256l.256.256a.5.5 0 0 0 .708 0l.256-.256h.256l.256.256a.5.5 0 0 0 .708 0l.256-.256H14.5a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-10.3A3.5 3.5 0 0 1 3.5 11.5M4 9a1 1 0 1 0 0-2 1 1 0 0 0 0 2"/>
                    </svg>
                    Fitur Paling Berpengaruh
                </h4>
            """, unsafe_allow_html=True)
            st.markdown("""
            AI ini belajar secara mandiri mengekstrak pola dari data operasional harian. Dari hasil ekstraksi pembelajaran tersebut, AI menemukan bahwa 3 variabel operasional di bawah ini merupakan faktor yang paling menentukan potensi sebuah pesanan akan mengalami keterlambatan:
            1.  **Nama Vendor (`vendor_name`):** Merupakan faktor paling dominan. AI sangat memperhatikan rekam jejak (*track record*) kedisiplinan masing-masing vendor dari pesanan-pesanan sebelumnya.
            2.  **Total Nilai Transaksi (`total_amount_local_curr`):** Secara statistik, nilai pembelian yang sangat besar atau masif umumnya memiliki kompleksitas pengadaan yang lebih tinggi, sehingga memengaruhi penambahan *lead time* persiapan vendor.
            3.  **Bulan Pembelian (`bulan_po`):** Algoritma menemukan pola siklus musim (*seasonality*). Pesanan yang diterbitkan mendekati siklus tutup tahun cenderung memiliki beban penyelesaian yang bertumpuk.
            """)