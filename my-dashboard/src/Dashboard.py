"""
Ross Dashboard (Streamlit)
--------------------------
Central landing page for the Personal Server Ecosystem.
Provides quick navigation links to other running services and basic PC control.

Features:
- **Navigation**: Links to News Reader, CSV Analyzer, RAG Workbench, etc.
- **PC Control**: WOL (Wake-on-LAN) and SSH reboot controls for network devices.
- **Monitoring**: Displays system status (via `pc_control` module).
"""
import streamlit as st
from pc_control import PCControl
import json
import os

# 페이지 설정
st.set_page_config(page_title="Ross Dashboard", layout="centered")

# 글꼴 크기를 위한 CSS (모바일 최적화)
st.markdown("""
<style>
h1 { font-size: 1.8rem !important; }
h2 { font-size: 1.5rem !important; }
</style>
""", unsafe_allow_html=True)

st.title("🖥️ Ross Dashboard!!")

# --- App Navigation Links ---
st.markdown("### 🚀 Applications")

# Row 1
col_nav1, col_nav2 = st.columns(2)

with col_nav1:
    st.link_button("📊 CSV Analyzer", "http://ross-server:8502", use_container_width=True)
    
with col_nav2:
    st.empty()

st.markdown("---")


# CSS 스타일 로드
PCControl.load_css()

# 설정 파일 로드
CONFIG_FILE = "config.json"
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as f:
        config_data = json.load(f)
        # 리스트인 경우(구버전)와 딕셔너리인 경우(신버전) 모두 처리
        if isinstance(config_data, list):
            devices = config_data
        else:
            devices = config_data.get("devices", [])
else:
    st.error(f"Configuration file '{CONFIG_FILE}' not found.")
    devices = []

# PC 인스턴스 생성 및 UI 렌더링
for device in devices:
    pc = PCControl(
        name=device["name"], 
        host=device["host"], 
        mac=device["mac"], 
        ssh_user=device["ssh_user"]
    )
    pc.render_ui()
    st.markdown("---") # 구분선 추가

# Open Web UI Shortcut
st.markdown("### 🌐 AI Web Services")
st.link_button("🚀 Open Web UI", "http://ross-server:3000", use_container_width=True)
