import streamlit as st
import logging
# 모듈 임포트
from modes import general_analysis, auto_validation

# 로깅 설정 (애플리케이션 전역 설정)
logging.basicConfig(filename='debug.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s', force=True)

# 페이지 설정 (반드시 가장 먼저 호출되어야 함)
st.set_page_config(layout="wide", page_title="CSV & DB Time Series Analyzer")

def main():
    """
    메인 애플리케이션 진입점.
    사이드바 네비게이션을 통해 'General Analysis'와 'Auto Validation' 모드를 전환합니다.
    """
    st.title("CSV & DB Time Series Analyzer")

    # 사이드바 네비게이션
    st.sidebar.title("Navigation")
    mode = st.sidebar.radio("Go to", ["General Analysis", "Auto Validation"])

    # 선택된 모드에 따라 해당 모듈의 run() 함수 실행
    if mode == "General Analysis":
        general_analysis.run()
    elif mode == "Auto Validation":
        auto_validation.run()

if __name__ == "__main__":
    main()
