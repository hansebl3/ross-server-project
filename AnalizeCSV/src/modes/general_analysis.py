import streamlit as st
import pandas as pd
from datetime import datetime
import config_manager
import data_loader
import visualizer

def run():
    """
    일반 분석 모드 (General Analysis Mode) 실행 함수
    사용자가 CSV 파일 또는 데이터베이스에서 데이터를 로드하고,
    필터링 및 시각화를 수행할 수 있도록 합니다.
    """
    st.header("General Analysis")
    
    # 데이터 소스 선택 (CSV 파일 또는 MariaDB)
    st.sidebar.header("Data Source")
    source_type = st.sidebar.radio("Select Source", ["CSV File", "Database (MariaDB)"])

    df = None

    # 1. CSV 파일 모드
    if source_type == "CSV File":
        uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])
        if uploaded_file is not None:
            try:
                df = data_loader.load_csv(uploaded_file)
            except Exception as e:
                st.error(f"Error: {e}")

    # 2. 데이터베이스 모드 (MariaDB)
    elif source_type == "Database (MariaDB)":
        # 설정 파일 로드
        config = config_manager.load_config()
        
        st.subheader("Database Connection")
        c1, c2, c3 = st.columns(3)
        with c1:
            host = st.text_input("Host", value=config.get("host", "localhost"))
            port = st.number_input("Port", value=config.get("port", 3306), step=1)
        with c2:
            user = st.text_input("User", value=config.get("user", "root"))
            password = st.text_input("Password", value=config.get("password", ""), type="password")
        with c3:
            database = st.text_input("Database", value=config.get("database", ""))
            table = st.text_input("Table", value=config.get("table", ""))

        st.subheader("Query Settings")
        qc1, qc2 = st.columns(2)
        with qc1:
            date_col_db = st.text_input("Date Column Name (in DB)", value=config.get("date_col_db", "created_at"))
        with qc2:
            # 기본값: 오늘 날짜로 설정
            default_start = datetime.now().date()
            default_end = datetime.now().date()
            date_range = st.date_input("Select Date Range", [default_start, default_end])

        # 데이터 로드 버튼
        if st.button("Connect & Load Data"):
            if len(date_range) == 2:
                start_date, end_date = date_range
                
                # 설정 저장 (비밀번호 포함)
                new_config = {
                    "host": host, "port": port, "user": user, "password": password,
                    "database": database, "table": table, "date_col_db": date_col_db
                }
                config_manager.save_config(new_config)

                try:
                    # 데이터 로드 실행
                    df_loaded = data_loader.load_db(new_config, start_date, end_date)
                    
                    if df_loaded.empty:
                        st.warning("Query returned no data.")
                    else:
                        # 세션 상태에 저장 (새로고침 시 데이터 유지)
                        st.session_state['db_df'] = df_loaded
                        st.success("Data loaded successfully!")
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Please select a valid start and end date.")

        # 세션 상태에서 데이터 복원
        if 'db_df' in st.session_state:
            df = st.session_state['db_df']

    # 데이터가 로드된 경우 처리 로직
    if df is not None and not df.empty:
        try:
            # 데이터 미리보기
            st.subheader("Data Preview")
            st.dataframe(df.head())

            # 2. 컬럼 선택 (Column Selection)
            st.subheader("Configuration")
            col1, col2 = st.columns(2)
            
            with col1:
                # DB 컬럼명과 일치하면 자동 선택 시도
                idx = 0
                if source_type == "Database (MariaDB)" and 'date_col_db' in locals() and date_col_db in df.columns:
                    idx = df.columns.get_loc(date_col_db)
                time_col = st.selectbox("Select Time Column", df.columns, index=idx)
                
            with col2:
                data_col = st.selectbox("Select Data Column (for Graph)", [c for c in df.columns if c != time_col])

            # 날짜 컬럼 파싱 및 정렬
            try:
                df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
                df = df.dropna(subset=[time_col])
                
                if df.empty:
                    st.error("No valid datetime data found in the selected column.")
                    st.stop()
                    
                df = df.sort_values(by=time_col)
            except Exception as e:
                st.error(f"Error parsing time column: {e}")
                st.stop()

            # 3. 고급 데이터 필터 (Advanced Data Filters) - 먼저 적용됨
            st.subheader("Data Filter")
            
            if 'filters' not in st.session_state:
                st.session_state.filters = []

            def add_filter():
                st.session_state.filters.append({'col': df.columns[0], 'op': '==', 'val': ''})

            col_add, _ = st.columns([1, 5])
            if col_add.button("Add Filter Condition"):
                add_filter()

            # 필터 UI 및 적용
            indices_to_remove = []
            for i, f in enumerate(st.session_state.filters):
                c1, c2, c3, c4 = st.columns([2, 1, 2, 1])
                with c1:
                    if f['col'] not in df.columns:
                        f['col'] = df.columns[0]
                    f['col'] = st.selectbox(f"Column", df.columns, key=f"col_{i}", index=df.columns.get_loc(f['col']))
                with c2:
                    ops = ["==", ">", "<", ">=", "<=", "!="]
                    f['op'] = st.selectbox(f"Operator", ops, key=f"op_{i}", index=ops.index(f['op']) if f['op'] in ops else 0)
                with c3:
                    f['val'] = st.text_input(f"Value", value=f['val'], key=f"val_{i}")
                with c4:
                    if st.button("Remove", key=f"rem_{i}"):
                        indices_to_remove.append(i)

            # 필터 삭제 처리
            for i in sorted(indices_to_remove, reverse=True):
                del st.session_state.filters[i]
                st.rerun()

            # 필터 로직 적용
            df_filtered = df.copy()
            for f in st.session_state.filters:
                if f['val']:
                    try:
                        col_type = df[f['col']].dtype
                        val = f['val']
                        if pd.api.types.is_numeric_dtype(col_type):
                            val = float(val)
                        
                        if f['op'] == "==":
                            df_filtered = df_filtered[df_filtered[f['col']] == val]
                        elif f['op'] == ">":
                            df_filtered = df_filtered[df_filtered[f['col']] > val]
                        elif f['op'] == "<":
                            df_filtered = df_filtered[df_filtered[f['col']] < val]
                        elif f['op'] == ">=":
                            df_filtered = df_filtered[df_filtered[f['col']] >= val]
                        elif f['op'] == "<=":
                            df_filtered = df_filtered[df_filtered[f['col']] <= val]
                        elif f['op'] == "!=":
                            df_filtered = df_filtered[df_filtered[f['col']] != val]
                    except Exception as e:
                        st.warning(f"Could not apply filter on {f['col']}: {e}")

            if df_filtered.empty:
                st.warning("No data available after filtering.")
                st.stop()

            # 4. 전체 시계열 개요 (Full Time Series Overview)
            st.subheader("Full Time Series Overview")
            fig_full = visualizer.create_full_time_series(
                df_filtered, time_col, data_col, f"Full Data: {data_col} over Time"
            )
            st.plotly_chart(fig_full, use_container_width=True)

            # 5. 시간 범위 슬라이더 및 분석 설정 (Form으로 감싸기)
            st.subheader("Analysis Settings")
            
            with st.form("analysis_form"):
                st.markdown("#### Time Range Filter")
                min_date = df_filtered[time_col].min().to_pydatetime()
                max_date = df_filtered[time_col].max().to_pydatetime()
                
                if min_date == max_date:
                    st.warning("Not enough data points for a range slider.")
                    start_date, end_date = min_date, max_date
                else:
                    start_date, end_date = st.slider(
                        "Select Time Range",
                        min_value=min_date,
                        max_value=max_date,
                        value=(min_date, max_date),
                        format="YYYY-MM-DD HH:mm"
                    )

                st.markdown("#### Graph Settings")
                custom_label = st.text_input("Custom Graph Label (Y-Axis)", value=data_col)

                c1, c2 = st.columns(2)
                with c1:
                    x_label = st.text_input("X-Axis Label", value=time_col)
                with c2:
                    y_label = st.text_input("Y-Axis Label", value=custom_label)

                submitted = st.form_submit_button("Generate Charts")

            if submitted:
                # 시간 범위 필터링 적용
                mask = (df_filtered[time_col] >= pd.to_datetime(start_date)) & (df_filtered[time_col] <= pd.to_datetime(end_date))
                df_final = df_filtered.loc[mask].copy()

                # 6. 차트 분석 (Analysis) - submitted 상태일 때만 렌더링
                st.subheader("Analysis Results")
                
                chart_col1, chart_col2 = st.columns(2)

                with chart_col1:
                    st.markdown("### Time Series Trend")
                    fig_line = visualizer.create_line_chart(
                        df_final, time_col, data_col, f"{custom_label} over Time", x_label, y_label
                    )
                    st.plotly_chart(fig_line, use_container_width=True)

                with chart_col2:
                    st.markdown("### Histogram")
                    fig_hist = visualizer.create_histogram(
                        df_final, data_col, f"Distribution of {custom_label}", x_label, y_label, nbins=300
                    )
                    st.plotly_chart(fig_hist, use_container_width=True)

                # 7. 데이터 내보내기 (Export Data)
                st.subheader("Export Data")
                csv = df_final.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Filtered Data as CSV",
                    data=csv,
                    file_name='filtered_data.csv',
                    mime='text/csv',
                )

        except Exception as e:
            st.error(f"Error processing data: {e}")
    elif source_type == "CSV File" and df is None:
        st.info("Please upload a CSV file to begin.")
