"""
v_ai_prediksi_sips.py - Prediksi Lead Time SIPS
"""
import streamlit as st
import pandas as pd
import joblib
import os
from datetime import datetime, timedelta

@st.cache_resource
def load_sips_models():
    base_dir = os.getcwd() 
    regressor_path = os.path.join(base_dir, 'Machine_Learning', 'model_sips_leadtime.pkl')
    encoder_path = os.path.join(base_dir, 'Machine_Learning', 'encoder_sips.pkl')
    cols_path = os.path.join(base_dir, 'Machine_Learning', 'fitur_sips.pkl')

    if not all(os.path.exists(p) for p in [regressor_path, encoder_path, cols_path]):
        return None, None, None

    return (
        joblib.load(regressor_path),
        joblib.load(encoder_path),
        joblib.load(cols_path)
    )

def render(**kwargs):
    # == HEADER ===============================================================
    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:42px; margin-bottom:0;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" fill="currentColor" class="bi bi-stopwatch" viewBox="0 0 16 16" style="margin-right:12px; margin-bottom:4px; color:#1f77b4;">
                <path d="M8.5 5.6a.5.5 0 1 0-1 0v2.9h-3a.5.5 0 0 0 0 1H8a.5.5 0 0 0 .5-.5z"/>
                <path d="M6.5 1A.5.5 0 0 1 7 .5h2a.5.5 0 0 1 0 1v.57c1.36.196 2.594.78 3.584 1.64a.715.715 0 0 1 .012-.013l.354-.354-.354-.353a.5.5 0 0 1 .707-.708l1.414 1.415a.5.5 0 1 1-.707.707l-.353-.354-.354.354a.512.512 0 0 1-.013.012A7 7 0 1 1 7 2.071V1.5a.5.5 0 0 1-.5-.5M8 3a6 6 0 1 0 .001 12A6 6 0 0 0 8 3"/>
            </svg>
            Estimator Durasi Pengadaan (Lead Time Forecaster)
        </h1>
    """, unsafe_allow_html=True)

    st.markdown(
        "<p style='font-size:15px; opacity:0.6; margin-top:4px; margin-bottom:24px;'>"
        "Modul kecerdasan buatan berbasis Regresi untuk memproyeksikan durasi pemrosesan dokumen Purchase Requisition (PR) menjadi Purchase Order (PO)."
        "</p>", unsafe_allow_html=True
    )

    tab1, tab2 = st.tabs(["Simulasi Dokumen PR Baru", "Spesifikasi Model AI"])

    with tab1:
        model_lt, encoder, fitur = load_sips_models()

        if model_lt is None:
            st.warning("File model AI untuk SIPS belum tersedia di folder Machine_Learning.")
            return

        # Ekstrak dictionary dari encoder
        list_prioritas = [str(x) for x in encoder.categories_[0] if str(x) != 'UNKNOWN']
        list_kontrak = [str(x) for x in encoder.categories_[1] if str(x) != 'UNKNOWN']
        list_pg = [str(x) for x in encoder.categories_[2] if str(x) != 'UNKNOWN']
        list_req = [str(x) for x in encoder.categories_[3] if str(x) != 'UNKNOWN']

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown("""
            <h3 style='display: flex; align-items: center; font-size:22px; margin-bottom:16px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="currentColor" class="bi bi-file-text" viewBox="0 0 16 16" style="margin-right:10px;">
                    <path d="M5 4a.5.5 0 0 0 0 1h6a.5.5 0 0 0 0-1zm-.5 2.5A.5.5 0 0 1 5 6h6a.5.5 0 0 1 0 1H5a.5.5 0 0 1-.5-.5M5 8a.5.5 0 0 0 0 1h6a.5.5 0 0 0 0-1zm0 2a.5.5 0 0 0 0 1h3a.5.5 0 0 0 0-1z"/>
                    <path d="M2 2a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2zm10-1H4a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1"/>
                </svg>
                Detail Purchase Requisition (PR)
            </h3>
        """, unsafe_allow_html=True)

        with st.form("form_sips_ai"):
            c1, c2 = st.columns(2)
            with c1:
                prioritas = st.selectbox("Tingkat Prioritas", options=list_prioritas)
                kontrak = st.selectbox("Status Kontrak", options=list_kontrak)
                pg = st.selectbox("Purchasing Group (Buyer)", options=list_pg)
                tgl_dispo = st.date_input("Tanggal Mulai (Disposisi Buyer)", value=datetime.now())
            with c2:
                req = st.selectbox("Requisitioner (Departemen Peminta)", options=list_req)
                oe_pr = st.number_input("Nilai Estimasi / OE PR (Rp)", min_value=0.0, value=25000000.0, step=1000000.0)
                # Nilai bulan dispo kita tarik otomatis dari input tanggal
                bulan = tgl_dispo.month
            
            st.markdown("<br>", unsafe_allow_html=True)
            submit_btn = st.form_submit_button("Jalankan Prediksi Timeline", type="primary", use_container_width=True)

        if submit_btn:
            with st.spinner("AI sedang mengkalkulasi kompleksitas dokumen dan beban kerja historis..."):
                # Siapkan input
                data_input = pd.DataFrame([{
                    'prioritas': prioritas,
                    'jenis_kontrak': kontrak,
                    'purchasing_group': pg,
                    'requisitioner': req,
                    'nilai_oe_pr': oe_pr,
                    'bulan_dispo': str(bulan) # Harus string karena kategorikal
                }])[fitur]
                
                # Transform text ke angka
                kolom_teks = ['prioritas', 'jenis_kontrak', 'purchasing_group', 'requisitioner']
                data_input[kolom_teks] = encoder.transform(data_input[kolom_teks])

                # Prediksi Regresi (Durasi Hari)
                prediksi_hari = model_lt.predict(data_input)[0]
                hari_bulat = max(1, int(round(prediksi_hari))) # Minimal 1 hari
                
                # Hitung Proyeksi Tanggal Selesai
                tgl_selesai = tgl_dispo + timedelta(days=hari_bulat)

                st.markdown("---")
                st.markdown("""
                    <h3 style='display: flex; align-items: center; font-size:22px; margin-bottom:20px;'>
                        <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="currentColor" class="bi bi-calendar2-check" viewBox="0 0 16 16" style="margin-right:10px;">
                            <path d="M10.854 8.146a.5.5 0 0 1 0 .708l-3 3a.5.5 0 0 1-.708 0l-1.5-1.5a.5.5 0 0 1 .708-.708L7.5 10.793l2.646-2.647a.5.5 0 0 1 .708 0"/>
                            <path d="M3.5 0a.5.5 0 0 1 .5.5V1h8V.5a.5.5 0 0 1 1 0V1h1a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2h1V.5a.5.5 0 0 1 .5-.5M2 2a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V3a1 1 0 0 0-1-1z"/>
                            <path d="M2.5 4a.5.5 0 0 1 .5-.5h10a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5H3a.5.5 0 0 1-.5-.5z"/>
                        </svg>
                        Hasil Kalkulasi Timeline
                    </h3>
                """, unsafe_allow_html=True)

                res_c1, res_c2 = st.columns([1, 1])

                # Kotak 1: Prediksi Hari
                with res_c1:
                    st.markdown(f"""
                        <div style="background-color: rgba(31, 119, 180, 0.08); border: 2px solid #1f77b4; border-radius: 12px; padding: 24px; text-align: center; height: 100%;">
                            <h4 style="color: var(--text-color); margin-top: 0; opacity: 0.8;">Estimasi Durasi Proses (PR to PO)</h4>
                            <h1 style="color: #1f77b4; font-size: 48px; margin: 10px 0;">{hari_bulat} <span style="font-size: 20px;">Hari</span></h1>
                            <p style="font-size: 14px; margin: 0; color: var(--text-color); opacity: 0.7;">Termasuk waktu libur kalender berjalan</p>
                        </div>
                    """, unsafe_allow_html=True)

                # Kotak 2: Proyeksi Tanggal
                with res_c2:
                    st.markdown(f"""
                        <div style="background-color: rgba(9, 171, 59, 0.08); border: 2px solid #09ab3b; border-radius: 12px; padding: 24px; text-align: center; height: 100%;">
                            <h4 style="color: var(--text-color); margin-top: 0; opacity: 0.8;">Proyeksi PO Terbit</h4>
                            <h1 style="color: #09ab3b; font-size: 32px; margin: 18px 0;">{tgl_selesai.strftime('%d %B %Y')}</h1>
                            <p style="font-size: 14px; margin: 0; color: var(--text-color); opacity: 0.7;">Jika proses dimulai pada {tgl_dispo.strftime('%d %B %Y')}</p>
                        </div>
                    """, unsafe_allow_html=True)

    with tab2:
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown("""
            <h3 style='display: flex; align-items: center; font-size:22px; margin-bottom:16px;'>
                <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="currentColor" class="bi bi-journal-code" viewBox="0 0 16 16" style="margin-right:10px;">
                    <path fill-rule="evenodd" d="M8.646 5.646a.5.5 0 0 1 .708 0l2 2a.5.5 0 0 1 0 .708l-2 2a.5.5 0 0 1-.708-.708L10.293 8 8.646 6.354a.5.5 0 0 1 0-.708m-1.292 0a.5.5 0 0 0-.708 0l-2 2a.5.5 0 0 0 0 .708l2 2a.5.5 0 0 0 .708-.708L5.707 8l1.647-1.646a.5.5 0 0 0 0-.708"/>
                    <path d="M3 0h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2v-1h1v1a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1H3a1 1 0 0 0-1 1v1H1V2a2 2 0 0 1 2-2"/>
                    <path d="M1 5v-.5a.5.5 0 0 1 1 0V5h.5a.5.5 0 0 1 0 1h-2a.5.5 0 0 1 0-1zm0 3v-.5a.5.5 0 0 1 1 0V8h.5a.5.5 0 0 1 0 1h-2a.5.5 0 0 1 0-1zm0 3v-.5a.5.5 0 0 1 1 0v.5h.5a.5.5 0 0 1 0 1h-2a.5.5 0 0 1 0-1z"/>
                </svg>
                Arsitektur Regresi SIPS
            </h3>
        """, unsafe_allow_html=True)

        st.markdown("""
        Berbeda dengan analitik sebelumnya yang berfokus pada eksternal (Vendor/Bea Cukai), halaman ini ditenagai oleh model *Machine Learning Regresi* untuk mengevaluasi dan mengestimasi efisiensi internal (Tim Procurement).
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
        
        col_m1, col_m2 = st.columns(2)
        col_m1.metric(label="Rata-rata Kesalahan (MAE)", value="3.9 Hari", delta="Tingkat Presisi Tinggi", delta_color="normal")
        col_m2.metric(label="Volume Data Training", value="18,938", delta="Dokumen PR ke PO")

        st.markdown("""
        **Evaluasi Rapor Model:**
        * **Kapasitas Deteksi (Regresi):** Berbeda dengan klasifikasi yang menebak kategori, model `RandomForestRegressor` ini dirancang khusus untuk memprediksi keluaran berupa angka berkelanjutan (*continuous numerical value*).
        * **Tingkat Akurasi:** Nilai MAE (*Mean Absolute Error*) sebesar 3.9 Hari mengindikasikan bahwa rata-rata tebakan AI hanya berdeviasi kurang dari 4 hari kalender dari realisasi lapangan.
        * **Business Value:** Dengan deviasi tingkat presisi yang kuat ini, Departemen *User* (Peminta Barang) dan tim *Turn Around* (TA) dapat memercayai angka estimasi AI untuk menyusun jadwal pemeliharaan dan proyek dengan garis waktu (*timeline*) yang lebih realistis serta berbasis data historis empiris.
        """)