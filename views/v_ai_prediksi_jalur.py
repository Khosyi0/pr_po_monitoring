"""
v_ai_prediksi_jalur.py - Halaman Uji Coba Model ML (Prediksi Jalur Inklaring)
"""
import streamlit as st
import pandas as pd
import joblib
import os

# Cache model agar tidak diload ulang setiap kali user berinteraksi
@st.cache_resource
def load_ml_jalur_models():
    base_dir = os.getcwd()
    gb_path = os.path.join(base_dir, 'Machine_Learning', 'model_inklaring_gb.pkl')
    dt_path = os.path.join(base_dir, 'Machine_Learning', 'model_inklaring_dt.pkl')

    if not os.path.exists(gb_path) or not os.path.exists(dt_path):
        return None, None

    model_gb = joblib.load(gb_path)
    model_dt = joblib.load(dt_path)
    return model_gb, model_dt

def render(**kwargs):
    # == HEADER ===============================================================
    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:42px; margin-bottom:0;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" fill="currentColor" class="bi bi-robot" viewBox="0 0 16 16" style="margin-right:12px; margin-bottom:4px; color:#ff4b4b;">
                <path d="M6 12.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1H6.5a.5.5 0 0 1-.5-.5M3.1 2.813a1 1 0 0 1 1.4-.41l1.64 1a2 2 0 0 1 3.72 0l1.64-1a1 1 0 0 1 1.4.41L12.1 4H13a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h.9l-1.64-1a1 1 0 0 1-.16-1.4m.48 1.492-1.35.825A.5.5 0 0 0 2 5.5v6a.5.5 0 0 0 .5.5h11a.5.5 0 0 0 .5-.5v-6a.5.5 0 0 0-.23-.437l-1.35-.825a.5.5 0 0 0-.52.88l1.1.67V11H3V5.79l1.1-.67a.5.5 0 0 0-.52-.88ZM4.5 7.5a.5.5 0 1 0 0-1 .5.5 0 0 0 0 1m7 0a.5.5 0 1 0 0-1 .5.5 0 0 0 0 1m-4 1.5a.5.5 0 0 0-.5.5v1a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5v-1a.5.5 0 0 0-.5-.5h-1Z"/>
            </svg>
            Prediksi Jalur Impor (AI Prototype)
        </h1>
    """, unsafe_allow_html=True)

    st.markdown(
        "<p style='font-size:15px; opacity:0.6; margin-top:4px; margin-bottom:16px;'>"
        "Simulasi prediksi penentuan jalur (Merah vs Hijau) menggunakan dua model Machine Learning sekaligus untuk perbandingan."
        "</p>", unsafe_allow_html=True
    )

    # Custom Alert Info
    st.markdown("""
        <div style="background-color: rgba(31, 119, 180, 0.1); border-left: 4px solid #1f77b4; padding: 12px 16px; border-radius: 4px; margin-bottom: 24px; display: flex; align-items: center;">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-tools" viewBox="0 0 16 16" style="margin-right: 12px; color: #1f77b4; flex-shrink: 0;">
                <path d="M1 0 0 1l2.2 3.081a1 1 0 0 0 .815.419h.07a1 1 0 0 1 .708.293l2.675 2.675-2.617 2.654A3.003 3.003 0 0 0 0 13a3 3 0 1 0 5.878-.851l2.654-2.617.968.968-.305.914a1 1 0 0 0 .242 1.023l3.27 3.27a.997.997 0 0 0 1.414 0l1.586-1.586a.997.997 0 0 0 0-1.414l-3.27-3.27a1 1 0 0 0-1.023-.242L10.5 9.5l-.96-.96 2.68-2.643A3.005 3.005 0 0 0 16 3q0-.405-.102-.777l-2.14 2.141L12 4l-.364-1.757L13.777.102a3 3 0 0 0-3.675 3.68L7.462 6.46 4.793 3.793a1 1 0 0 1-.293-.707v-.071a1 1 0 0 0-.419-.814zm9.646 10.646a.5.5 0 0 1 .708 0l2.914 2.915a.5.5 0 0 1-.707.707l-2.915-2.914a.5.5 0 0 1 0-.708M3 11l.471.242.529.026.287.445.445.287.026.529L5 13l-.242.471-.026.529-.445.287-.287.445-.529.026L3 15l-.471-.242L2 14.732l-.287-.445L1.268 14l-.026-.529L1 13l.242-.471.026-.529.445-.287.287-.445.529-.026z"/>
            </svg>
            <span style="color: var(--text-color); font-size: 14px;"><strong>Status:</strong> Fitur purwarupa (Proof of Concept) ini dibangun dengan dataset sampel terbatas. Hanya dapat diakses oleh Admin untuk keperluan kalibrasi.</span>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # Memisahkan halaman menggunakan TABS
    tab1, tab2 = st.tabs(["Simulasi Prediksi", "Detail & Metrik Model AI"])

    # =========================================================================
    # TAB 1: SIMULASI PREDIKSI
    # =========================================================================
    with tab1:
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown("""
            <h3 style='display: flex; align-items: center; font-size:22px; margin-bottom:16px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="currentColor" class="bi bi-file-earmark-ruled" viewBox="0 0 16 16" style="margin-right:10px;">
                    <path d="M14 14V4.5L9.5 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2M9.5 3A1.5 1.5 0 0 0 11 4.5h2V9H3V2a1 1 0 0 1 1-1h5.5zM3 12v-2h2v2zm0 1h2v2H4a1 1 0 0 1-1-1zm3 2v-2h7v1a1 1 0 0 1-1 1zm7-3H6v-2h7z"/>
                </svg>
                Detail Dokumen Impor
            </h3>
        """, unsafe_allow_html=True)

        with st.form("form_prediksi_jalur"):
            col1, col2 = st.columns(2)

            with col1:
                komoditi = st.selectbox("Jenis Komoditi", [
                    "MOP", "SA", "ROCK PHOSPHATE", "SULPHUR", "UREA", "ZA", "KCL"
                ])
                quantity = st.number_input("Kuantitas Muatan (Metric Ton)", min_value=0.0, value=25000.0, step=1000.0)

            with col2:
                negara = st.selectbox("Asal Negara", [
                    "Rusia", "China", "Vietnam", "Taiwan", "United Arab Emirates",
                    "South Korea", "Egypt", "United States of America", "Canada", "Jordan"
                ])
                pajak = st.number_input("Estimasi Total Pajak (BM + PPN + PPH) (Rp)", min_value=0.0, value=2000000000.0, step=100000000.0)

            st.markdown("<br>", unsafe_allow_html=True)
            submit_btn = st.form_submit_button("Jalankan Prediksi AI", type="primary", use_container_width=True)

        if submit_btn:
            with st.spinner("Mengirim data ke model prediksi jalur..."):
                model_gb, model_dt = load_ml_jalur_models()

                if model_gb is None or model_dt is None:
                    st.error("Gagal memuat model AI. Pastikan file 'model_inklaring_gb.pkl' dan 'model_inklaring_dt.pkl' tersedia di folder Machine_Learning.")
                else:
                    # Kedua pipeline (GB & DT) sudah menyertakan preprocessing
                    # (One-Hot Encoding + Scaling) di dalamnya, sehingga cukup
                    # diberi data mentah dengan nama kolom asli hasil training.
                    data_input = pd.DataFrame([{
                        'KOMODITI': komoditi,
                        'ASAL NEGARA': negara,
                        'QUANTITY (MT)': quantity,
                        'TOTAL': pajak
                    }])

                    pred_gb = model_gb.predict(data_input)[0]
                    proba_gb = model_gb.predict_proba(data_input)[0]

                    pred_dt = model_dt.predict(data_input)[0]
                    proba_dt = model_dt.predict_proba(data_input)[0]

                    st.markdown("---")
                    st.markdown("""
                        <h3 style='display: flex; align-items: center; font-size:22px; margin-bottom:8px;'>
                            <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="currentColor" class="bi bi-cpu" viewBox="0 0 16 16" style="margin-right:10px;">
                                <path d="M5 0a.5.5 0 0 1 .5.5V2h1V.5a.5.5 0 0 1 1 0V2h1V.5a.5.5 0 0 1 1 0V2h1V.5a.5.5 0 0 1 1 0V2A2.5 2.5 0 0 1 14 4.5h1.5a.5.5 0 0 1 0 1H14v1h1.5a.5.5 0 0 1 0 1H14v1h1.5a.5.5 0 0 1 0 1H14v1h1.5a.5.5 0 0 1 0 1H14a2.5 2.5 0 0 1-2.5 2.5v1.5a.5.5 0 0 1-1 0V14h-1v1.5a.5.5 0 0 1-1 0V14h-1v1.5a.5.5 0 0 1-1 0V14h-1v1.5a.5.5 0 0 1-1 0V14A2.5 2.5 0 0 1 2 11.5H.5a.5.5 0 0 1 0-1H2v-1H.5a.5.5 0 0 1 0-1H2v-1H.5a.5.5 0 0 1 0-1H2v-1H.5a.5.5 0 0 1 0-1H2A2.5 2.5 0 0 1 4.5 2V.5A.5.5 0 0 1 5 0m-.5 3A1.5 1.5 0 0 0 3 4.5v7A1.5 1.5 0 0 0 4.5 13h7a1.5 1.5 0 0 0 1.5-1.5v-7A1.5 1.5 0 0 0 11.5 3zM5 6.5A1.5 1.5 0 0 1 6.5 5h3A1.5 1.5 0 0 1 11 6.5v3A1.5 1.5 0 0 1 9.5 11h-3A1.5 1.5 0 0 1 5 9.5zM6.5 6a.5.5 0 0 0-.5.5v3a.5.5 0 0 0 .5.5h3a.5.5 0 0 0 .5-.5v-3a.5.5 0 0 0-.5-.5z"/>
                            </svg>
                            Hasil Analisis Model AI
                        </h3>
                    """, unsafe_allow_html=True)
                    st.markdown(
                        "<p style='font-size:14px; opacity:0.6; margin-top:0; margin-bottom:20px;'>"
                        "Dua model dijalankan sekaligus agar Anda bisa membandingkan hasilnya. "
                        "Jika keduanya sepakat, keyakinan prediksi lebih tinggi; jika berbeda, gunakan sebagai sinyal untuk berhati-hati / cek manual."
                        "</p>", unsafe_allow_html=True
                    )

                    def render_hasil_model(pred, proba, nama_model, badge_text):
                        res_col1, res_col2 = st.columns([4, 6])
                        with res_col1:
                            if pred == 1:  # 1 = Merah
                                st.markdown(f"""
                                    <div style="background-color: rgba(224, 60, 60, 0.08); border: 2px solid #e03c3c; border-radius: 12px; padding: 20px; text-align: center; height: 100%;">
                                        <span style="display:inline-block; background-color:#e03c3c22; color:#e03c3c; font-size:11px; font-weight:600; padding:3px 10px; border-radius:999px; margin-bottom:8px;">{badge_text}</span>
                                        <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" fill="#e03c3c" class="bi bi-shield-fill-exclamation" viewBox="0 0 16 16" style="display:block; margin: 4px auto;">
                                            <path fill-rule="evenodd" d="M8 0c-.69 0-1.843.265-2.928.56-1.11.3-2.229.655-2.887.87a1.54 1.54 0 0 0-1.044 1.262c-.596 4.477.787 7.795 2.465 9.99a11.8 11.8 0 0 0 2.517 2.453c.386.273.744.482 1.048.625.28.132.581.24.829.24s.548-.108.829-.24a7 7 0 0 0 1.048-.625 11.8 11.8 0 0 0 2.517-2.453c1.678-2.195 3.061-5.513 2.465-9.99a1.54 1.54 0 0 0-1.044-1.263 63 63 0 0 0-2.887-.87C9.843.266 8.69 0 8 0m-.5 5a.5.5 0 0 1 1 0v3a.5.5 0 0 1-1 0zm.5 5.5a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5"/>
                                        </svg>
                                        <h2 style="color: #e03c3c; margin: 8px 0 4px 0; font-size: 22px;">JALUR MERAH</h2>
                                        <p style="font-size: 15px; margin: 0; color: var(--text-color); opacity: 0.8;">Keyakinan: <strong style="color: #e03c3c; font-size: 18px;">{proba[1]*100:.1f}%</strong></p>
                                        <p style="font-size: 12px; margin: 6px 0 0 0; color: var(--text-color); opacity: 0.55;">{nama_model}</p>
                                    </div>
                                """, unsafe_allow_html=True)
                            else:  # 0 = Hijau
                                st.markdown(f"""
                                    <div style="background-color: rgba(9, 171, 59, 0.08); border: 2px solid #09ab3b; border-radius: 12px; padding: 20px; text-align: center; height: 100%;">
                                        <span style="display:inline-block; background-color:#09ab3b22; color:#09ab3b; font-size:11px; font-weight:600; padding:3px 10px; border-radius:999px; margin-bottom:8px;">{badge_text}</span>
                                        <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" fill="#09ab3b" class="bi bi-shield-fill-check" viewBox="0 0 16 16" style="display:block; margin: 4px auto;">
                                            <path fill-rule="evenodd" d="M8 0c-.69 0-1.843.265-2.928.56-1.11.3-2.229.655-2.887.87a1.54 1.54 0 0 0-1.044 1.262c-.596 4.477.787 7.795 2.465 9.99a11.8 11.8 0 0 0 2.517 2.453c.386.273.744.482 1.048.625.28.132.581.24.829.24s.548-.108.829-.24a7 7 0 0 0 1.048-.625 11.8 11.8 0 0 0 2.517-2.453c1.678-2.195 3.061-5.513 2.465-9.99a1.54 1.54 0 0 0-1.044-1.263 63 63 0 0 0-2.887-.87C9.843.266 8.69 0 8 0m2.146 5.146a.5.5 0 0 1 .708.708l-3 3a.5.5 0 0 1-.708 0l-1.5-1.5a.5.5 0 1 1 .708-.708L7.5 7.793z"/>
                                        </svg>
                                        <h2 style="color: #09ab3b; margin: 8px 0 4px 0; font-size: 22px;">JALUR HIJAU</h2>
                                        <p style="font-size: 15px; margin: 0; color: var(--text-color); opacity: 0.8;">Keyakinan: <strong style="color: #09ab3b; font-size: 18px;">{proba[0]*100:.1f}%</strong></p>
                                        <p style="font-size: 12px; margin: 6px 0 0 0; color: var(--text-color); opacity: 0.55;">{nama_model}</p>
                                    </div>
                                """, unsafe_allow_html=True)
                        with res_col2:
                            if pred == 1:
                                st.markdown("""
                                    <div style="padding: 12px 16px; height: 100%; display: flex; flex-direction: column; justify-content: center;">
                                        <p style="font-size: 14px; color: var(--text-color); opacity: 0.85; margin-bottom: 10px;">
                                            Dokumen dengan karakteristik ini diidentifikasi rawan terhadap pemeriksaan fisik (Jalur Merah) oleh Bea Cukai.
                                        </p>
                                        <ul style="font-size: 13px; color: var(--text-color); opacity: 0.85; margin-bottom: 0; padding-left: 18px;">
                                            <li style="margin-bottom: 4px;">Siapkan mitigasi waktu tunggu antrean pelabuhan yang lebih lama.</li>
                                            <li>Audit internal kelengkapan dokumen bersama Agen/PPJK sebelum kapal bersandar.</li>
                                        </ul>
                                    </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.markdown("""
                                    <div style="padding: 12px 16px; height: 100%; display: flex; flex-direction: column; justify-content: center;">
                                        <p style="font-size: 14px; color: var(--text-color); opacity: 0.85; margin-bottom: 10px;">
                                            Dokumen dengan parameter ini diprediksi aman dan cenderung langsung diterbitkan SPPB.
                                        </p>
                                        <ul style="font-size: 13px; color: var(--text-color); opacity: 0.85; margin-bottom: 0; padding-left: 18px;">
                                            <li>Monitor jadwal ETA secara reguler dan lanjutkan rencana bongkar muat sesuai jadwal.</li>
                                        </ul>
                                    </div>
                                """, unsafe_allow_html=True)

                    st.markdown("##### 🚀 Model 1: Gradient Boosting *(model utama, akurasi lebih tinggi)*")
                    render_hasil_model(pred_gb, proba_gb, "Gradient Boosting", "MODEL UTAMA")

                    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
                    st.markdown("##### 🌳 Model 2: Decision Tree *(model pembanding, mudah diaudit/dijelaskan)*")
                    render_hasil_model(pred_dt, proba_dt, "Decision Tree", "PEMBANDING")

                    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
                    if pred_gb == pred_dt:
                        st.success("✅ **Kedua model sepakat** pada hasil prediksi yang sama — tingkat keyakinan hasil ini relatif lebih tinggi.")
                    else:
                        st.warning("⚠️ **Kedua model berbeda hasil.** Gunakan ini sebagai sinyal kehati-hatian tambahan dan pertimbangkan pengecekan manual, alih-alih mengandalkan satu prediksi saja.")

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
                Spesifikasi & Rapor AI (Proof of Concept)
            </h3>
        """, unsafe_allow_html=True)

        st.markdown("""
        Sistem ini menjalankan **dua model Machine Learning secara paralel** untuk memetakan aturan probabilistik dari penetapan jalur kapal, sehingga hasil prediksi bisa saling diverifikasi. Melalui model ini, Departemen Pengadaan Barang diharapkan memiliki sistem radar awal untuk membantu mengalokasikan waktu dan mitigasi operasional pelabuhan dengan lebih efisien.
        """)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.markdown("""
            <div style="background-color: rgba(255, 165, 0, 0.08); border-left: 4px solid #f0a500; padding: 10px 16px; border-radius: 4px; margin-bottom: 16px;">
                <span style="color: var(--text-color); font-size: 13.5px;">
                <strong>Catatan jujur:</strong> Semua metrik di bawah dihitung dengan <em>Stratified K-Fold Cross-Validation</em> (bukan satu kali split), karena volume data latih hanya 69 dokumen. Ini membuat estimasi performa lebih bisa dipercaya, tapi tetap bukan jaminan akurasi di produksi — terlebih kebijakan jalur bisa berubah tiap tahun.
                </span>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.markdown("""
            <h4 style='display: flex; align-items: center; margin-bottom: 12px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-bar-chart-fill" viewBox="0 0 16 16" style="margin-right: 8px;">
                    <path d="M1 11a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1zm5-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1zm5-5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1z"/>
                </svg>
                Performa Metrik — Perbandingan 2 Model (Cross-Validation)
            </h4>
        """, unsafe_allow_html=True)

        met_col1, met_col2 = st.columns(2, gap="large")
        with met_col1:
            st.markdown("**🚀 Gradient Boosting** *(model utama)*")
            g1, g2, g3 = st.columns(3)
            g1.metric(label="Akurasi", value="72.7%")
            g2.metric(label="Balanced Acc.", value="69.6%")
            g3.metric(label="ROC AUC", value="0.763")
            g4, g5 = st.columns(2)
            g4.metric(label="Recall (Deteksi Merah)", value="59.4%")
            g5.metric(label="Precision (Merah)", value="62.8%")

        with met_col2:
            st.markdown("**🌳 Decision Tree** *(model pembanding)*")
            d1, d2, d3 = st.columns(3)
            d1.metric(label="Akurasi", value="62.6%")
            d2.metric(label="Balanced Acc.", value="62.0%")
            d3.metric(label="ROC AUC", value="0.725")
            d4, d5 = st.columns(2)
            d4.metric(label="Recall (Deteksi Merah)", value="60.2%")
            d5.metric(label="Precision (Merah)", value="47.9%")

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.metric(label="Volume Data Training", value="69 dokumen", delta="45 Hijau (65%) · 24 Merah (35%)", delta_color="off")

        st.markdown("""
        **Evaluasi Rapor Model:**
        * **Gradient Boosting unggul secara konsisten** di semua metrik dibanding Decision Tree — akurasi maupun ROC AUC-nya lebih tinggi, sehingga dijadikan **model utama**. Namun selisihnya masih dalam rentang wajar mengingat kecilnya data, sehingga Decision Tree tetap ditampilkan sebagai pembanding.
        * **Kenapa dua model ditampilkan sekaligus?** Decision Tree jauh lebih mudah diaudit/dijelaskan (alurnya bisa digambar sebagai pohon keputusan sederhana), sementara Gradient Boosting lebih akurat tapi cara kerjanya lebih sulit dijelaskan secara manual. Saat kedua model **sepakat**, itu sinyal keyakinan yang lebih kuat; saat **berbeda**, sebaiknya dicek manual.
        * **Keseimbangan Kelas:** Dataset pelatihan terdiri dari ~65% Jalur Hijau dan ~35% Jalur Merah — kedua model dilatih dengan pembobotan kelas (*class weighting*) agar tidak bias ke kelas mayoritas.
        * **Peluang Optimasi:** Akurasi prediksi diproyeksikan meningkat signifikan menuju level *production-grade* apabila database Inklaring diisi dengan data historis komprehensif dari beberapa tahun ke belakang, mengingat kebijakan penentuan jalur sendiri bisa berubah dari tahun ke tahun.
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
                    Anatomi Kedua Model
                </h4>
            """, unsafe_allow_html=True)
            st.markdown("""
            * **Gradient Boosting (model utama):** Algoritma *ensemble* yang membangun 200 pohon keputusan kecil (`max_depth=2`) secara bertahap, di mana setiap pohon baru memperbaiki kesalahan pohon sebelumnya. Lebih akurat, tapi bersifat *black-box* — sulit dijelaskan alur logikanya secara manual.
            * **Decision Tree (model pembanding):** Satu pohon keputusan tunggal (`max_depth=4`, `min_samples_leaf=5`). Bersifat *white-box* — seluruh alur logikanya dapat dipetakan, digambar, dan diaudit langkah demi langkah oleh auditor logistik. Batas kedalaman mencegah model sekadar menghafal 69 sampel data latih (*overfitting*).
            * **Encoding & Scaling:** Kedua model menggunakan *pipeline* terpadu yang otomatis menerapkan *One-Hot Encoding* untuk data teks (Komoditi, Asal Negara) dan *Standard Scaling* untuk data numerik (Kuantitas, Total Pajak) — sehingga input cukup data mentah tanpa perlu praproses manual di aplikasi.
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
            Berdasarkan hasil pelatihan Gradient Boosting (model utama), dua fitur berikut mendominasi keputusan (>90% total kontribusi):
            1.  **Total Pajak (`TOTAL`):** Estimasi gabungan BM + PPN + PPH memiliki bobot pengaruh tertinggi terhadap prediksi jalur.
            2.  **Kuantitas Muatan (`QUANTITY (MT)`):** Bobot pengaruh terbesar kedua — muatan dalam tonase besar berkorelasi dengan probabilitas Jalur Merah yang lebih tinggi.
            3.  **Asal Negara & Jenis Komoditi:** Berkontribusi lebih kecil namun tetap relevan — beberapa kombinasi negara asal (mis. Rusia) dan komoditi tertentu (mis. PA, Sulphur) menjadi pembeda tambahan pada kasus-kasus yang tidak jelas hanya dari kuantitas dan pajak saja.

            *Fitur seperti Pelabuhan Muat, Pemasok, dan Pengirim sengaja tidak digunakan karena datanya terlalu beragam (banyak nilai unik) relatif terhadap jumlah data latih yang tersedia, sehingga berisiko membuat model menghafal alih-alih belajar pola umum.*
            """)