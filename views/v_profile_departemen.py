"""
v_profile_departemen.py - Halaman Profile Departemen
"""
import streamlit as st

def render(**kwargs):
    """Render halaman Profile Departemen yang masih kosong."""
    st.markdown("""
        <h1 style='display: flex; align-items: center; font-size:40px;'>
            <svg xmlns="http://www.w3.org/2000/svg" width="35" height="35" fill="currentColor" class="bi bi-building" viewBox="0 0 16 16" style="margin-bottom: 8px; margin-right: 12px;">
                <path d="M6 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6m-5 6s-1 0-1-1 1-4 6-4 6 3 6 4-1 1-1 1zM11 3.5a.5.5 0 0 1 .5-.5h4a.5.5 0 0 1 0 1h-4a.5.5 0 0 1-.5-.5m.5 2.5a.5.5 0 0 0 0 1h4a.5.5 0 0 0 0-1zm2 3a.5.5 0 0 0 0 1h2a.5.5 0 0 0 0-1zm0 3a.5.5 0 0 0 0 1h2a.5.5 0 0 0 0-1z"/>
            </svg>
            Profile Departemen
        </h1>
    """, unsafe_allow_html=True)
    st.info("Halaman profil departemen masih dalam tahap pengembangan.")
    st.markdown("---")