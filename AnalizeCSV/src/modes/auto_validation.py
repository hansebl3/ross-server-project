import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import logging
import config_manager
import data_loader

def run_standard_validation():
    """
    자동 검증 모드 (Auto Validation Mode) 실행 함수
    PLC 및 Vision 데이터를 로드하고, Work Center (Unit) 별로 필터링하여
    시각화 및 분석을 수행합니다.
    """
    st.header("Auto Validation")
    
    # 설정 로드
    config = config_manager.load_config()
    
    # 데이터 소스 선택 (Database 또는 CSV 파일)
    st.sidebar.markdown("---")
    av_source_type = st.sidebar.radio("Auto Validation Data Source", ["Database", "CSV Files"])

    # 데이터 로드 섹션 (데이터가 없으면 펼침, 있으면 접음)
    has_data = 'df_plc' in st.session_state and 'df_vision' in st.session_state
    with st.expander("Data Loading Settings", expanded=not has_data):
        
        if av_source_type == "Database":
            # DB 연결 정보 (공통)
            st.subheader("Database Connection")
            c1, c2, c3 = st.columns(3)
            with c1:
                host = st.text_input("Host", value=config.get("host", "localhost"), key="av_host")
                port = st.number_input("Port", value=config.get("port", 3306), step=1, key="av_port")
            with c2:
                user = st.text_input("User", value=config.get("user", "root"), key="av_user")
                password = st.text_input("Password", value=config.get("password", ""), type="password", key="av_password")
            with c3:
                database = st.text_input("Database", value=config.get("database", ""), key="av_database")
            
            # 테이블 정보 (PLC & Vision)
            st.subheader("Table Settings")
            t1, t2 = st.columns(2)
            with t1:
                st.markdown("**PLC Data Table**")
                table_plc = st.text_input("Table Name", value=config.get("table_plc", "tb_unit_data"), key="av_table_plc")
                date_col_plc = st.text_input("Date Column", value=config.get("date_col_plc", "ent_date"), key="av_date_plc")
            with t2:
                st.markdown("**Vision Data Table**")
                table_vision = st.text_input("Table Name", value=config.get("table_vision", "tb_result"), key="av_table_vision")
                date_col_vision = st.text_input("Date Column", value=config.get("date_col_vision", "ent_date"), key="av_date_vision")

            # 날짜 범위 선택
            st.subheader("Date Range")
            default_start = datetime.now().date()
            default_end = datetime.now().date()
            date_range = st.date_input("Select Date Range (Auto Validation)", [default_start, default_end])

            # 데이터 로드 버튼
            if st.button("Load Data (from DB)"):
                if len(date_range) == 2:
                    start_date, end_date = date_range
                    
                    # 설정 저장
                    new_config = config.copy()
                    new_config.update({
                        "host": host, "port": port, "user": user, "password": password, "database": database,
                        "table_plc": table_plc, "date_col_plc": date_col_plc,
                        "table_vision": table_vision, "date_col_vision": date_col_vision
                    })
                    config_manager.save_config(new_config)
                    
                    try:
                        # PLC 데이터 로드
                        plc_config = new_config.copy()
                        plc_config['table'] = table_plc
                        plc_config['date_col_db'] = date_col_plc
                        df_plc = data_loader.load_db(plc_config, start_date, end_date)
                        
                        # Vision 데이터 로드
                        vision_config = new_config.copy()
                        vision_config['table'] = table_vision
                        vision_config['date_col_db'] = date_col_vision
                        df_vision = data_loader.load_db(vision_config, start_date, end_date)
                        
                        if df_plc.empty or df_vision.empty:
                            st.warning("One or both queries returned no data.")
                        else:
                            st.session_state['df_plc'] = df_plc
                            st.session_state['df_vision'] = df_vision
                            # 상태 초기화
                            if 'current_work_cent' in st.session_state: del st.session_state.current_work_cent
                            if 'plc_filters' in st.session_state: del st.session_state.plc_filters
                            st.success(f"Loaded PLC: {len(df_plc)} rows, Vision: {len(df_vision)} rows")
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"Error loading data: {e}")
                else:
                    st.warning("Please select a valid date range.")

        else: # CSV Files
            st.subheader("Upload CSV Files")
            c1, c2 = st.columns(2)
            with c1:
                plc_file = st.file_uploader("Upload PLC Data (CSV)", type=["csv"])
            with c2:
                vision_file = st.file_uploader("Upload Vision Data (CSV)", type=["csv"])
            
            if st.button("Load Data (from CSV)"):
                if plc_file and vision_file:
                    try:
                        df_plc = data_loader.load_csv(plc_file)
                        df_vision = data_loader.load_csv(vision_file)

                        # 날짜 컬럼 변환 (CSV는 문자열로 로드되므로)
                        # PLC: ent_date 가정
                        if 'ent_date' in df_plc.columns:
                            df_plc['ent_date'] = pd.to_datetime(df_plc['ent_date'], errors='coerce')
                        
                        # Vision: ent_date 가정
                        if 'ent_date' in df_vision.columns:
                            df_vision['ent_date'] = pd.to_datetime(df_vision['ent_date'], errors='coerce')

                        st.session_state['df_plc'] = df_plc
                        st.session_state['df_vision'] = df_vision
                        
                        # 상태 초기화
                        if 'current_work_cent' in st.session_state: del st.session_state.current_work_cent
                        if 'plc_filters' in st.session_state: del st.session_state.plc_filters
                        
                        st.success(f"Loaded PLC: {len(df_plc)} rows, Vision: {len(df_vision)} rows")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error loading CSVs: {e}")
                else:
                    st.warning("Please upload both PLC and Vision CSV files.")


    # 데이터 로드 후 처리
    if has_data:
        df_plc = st.session_state['df_plc']
        df_vision = st.session_state['df_vision']
        
        # 상태 초기화
        if 'current_work_cent' not in st.session_state:
            st.session_state.current_work_cent = 1
        if 'plc_filters' not in st.session_state:
            st.session_state.plc_filters = {} # {work_cent: {start_time, end_time, d5017_min, d5017_max}}

        logging.info(f"Auto Validation Mode: current_work_cent={st.session_state.current_work_cent}")

        # Step 1: PLC Data Filtering (Iterative)
        if st.session_state.current_work_cent <= 4:
            wc = st.session_state.current_work_cent
            st.markdown(f"### Step 1: PLC Data Filtering - Unit {wc}")
            logging.info(f"Rendering Step 1 for WC {wc}")
            
            # work_cent 필터링
            if 'work_cent' in df_plc.columns:
                try:
                    df_plc['work_cent'] = pd.to_numeric(df_plc['work_cent'], errors='coerce')
                except:
                    pass
                df_wc = df_plc[df_plc['work_cent'] == wc]
            else:
                st.error("Column 'work_cent' not found in PLC data.")
                logging.error("Column 'work_cent' not found")
                st.stop()
            
            if df_wc.empty:
                st.warning(f"No data for Unit {wc}. Skipping...")
                logging.warning(f"No data for WC {wc}")
                if st.button("Next Unit"):
                    st.session_state.current_work_cent += 1
                    st.rerun()
            else:
                # D5017 컬럼 확인
                d5017_col = 'D5017'
                if d5017_col not in df_wc.columns:
                    st.error(f"Column '{d5017_col}' not found in PLC data.")
                    logging.error(f"Column '{d5017_col}' not found")
                    st.stop()

                # 1. 컨트롤 위젯 먼저 배치 (Real-time update를 위해)
                min_date = df_wc['ent_date'].min().to_pydatetime()
                max_date = df_wc['ent_date'].max().to_pydatetime()
                
                # 기본값 설정 (이전 설정이 있으면 사용)
                default_time = (min_date, max_date)
                default_min_val = 20.0 # User requested default
                default_max_val = 150.0 # User requested default
                
                st.markdown("#### Filter Settings")
                c1, c2 = st.columns(2)
                with c1:
                    time_range = st.slider(
                        f"Select Time Range (Unit {wc})",
                        min_value=min_date,
                        max_value=max_date,
                        value=default_time,
                        format="YYYY-MM-DD HH:mm:ss",
                        key=f"slider_wc_{wc}"
                    )
                with c2:
                    d5017_min = st.number_input(f"Pressure Min (Unit {wc})", value=default_min_val, key=f"min_wc_{wc}")
                    d5017_max = st.number_input(f"Pressure Max (Unit {wc})", value=default_max_val, key=f"max_wc_{wc}")

                # 2. 필터링 적용 및 그래프 그리기
                mask_time = (df_wc['ent_date'] >= pd.to_datetime(time_range[0])) & (df_wc['ent_date'] <= pd.to_datetime(time_range[1]))
                mask_val = (df_wc[d5017_col] >= d5017_min) & (df_wc[d5017_col] <= d5017_max)
                
                df_wc_filtered = df_wc[mask_time & mask_val]
                
                st.markdown(f"**Pressure Trend (Filtered Preview) - {len(df_wc_filtered)} rows**")
                if not df_wc_filtered.empty:
                    fig = px.line(df_wc_filtered, x='ent_date', y=d5017_col, title=f"Pressure over Time (Unit {wc}) - Filtered")
                    st.plotly_chart(fig, use_container_width=True, key=f"preview_wc_{wc}", config={'displayModeBar': True})
                else:
                    st.warning("No data selected with current filters.")

                # Confirm 버튼
                if st.button(f"Confirm Settings for Unit {wc}"):
                    # 설정 저장
                    st.session_state.plc_filters[wc] = {
                        'start_time': time_range[0],
                        'end_time': time_range[1],
                        'd5017_min': d5017_min,
                        'd5017_max': d5017_max
                    }
                    logging.info(f"Confirmed settings for WC {wc}: {st.session_state.plc_filters[wc]}")
                    st.session_state.current_work_cent += 1
                    st.rerun()

        # Step 2 & 3: Vision Filtering & Visualization
        else:
            logging.info("Entering Step 2 & 3: Visualization")
            try:
                # Step 2: Data Filtering & Synchronization
                st.markdown("### Step 3: Visualization")

                # Iterate through each configured Work Center
                for wc, f in st.session_state.plc_filters.items():
                    st.markdown(f"---")
                    st.markdown(f"### Unit {wc} Analysis")
                    
                    # 1. Filter PLC Data for this WC
                    mask_wc = df_plc['work_cent'] == wc
                    mask_time = (df_plc['ent_date'] >= pd.to_datetime(f['start_time'])) & (df_plc['ent_date'] <= pd.to_datetime(f['end_time']))
                    mask_val = (df_plc['D5017'] >= f['d5017_min']) & (df_plc['D5017'] <= f['d5017_max'])
                    
                    df_plc_wc = df_plc[mask_wc & mask_time & mask_val]
                    
                    # 2. Filter Vision Data for this WC (mapped to unit)
                    # Ensure 'unit' is numeric for comparison
                    if 'unit' in df_vision.columns:
                         # Try to convert to numeric if it's not already, but don't fail hard if it's mixed
                        try:
                            df_vision['unit'] = pd.to_numeric(df_vision['unit'], errors='coerce')
                        except:
                            pass
                    
                    mask_unit = df_vision['unit'] == wc
                    
                    start_buffered = pd.to_datetime(f['start_time']) + timedelta(seconds=1)
                    end_buffered = pd.to_datetime(f['end_time']) - timedelta(seconds=1)
                    
                    if start_buffered < end_buffered:
                        mask_time_vision = (df_vision['ent_date'] >= start_buffered) & (df_vision['ent_date'] <= end_buffered)
                        df_vision_wc = df_vision[mask_unit & mask_time_vision]
                    else:
                        df_vision_wc = pd.DataFrame()

                    st.write(f"Filtered PLC Data (Unit {wc}): {len(df_plc_wc)} rows")
                    st.write(f"Filtered Vision Data (Unit {wc}): {len(df_vision_wc)} rows")
                    
                    if df_plc_wc.empty:
                        st.warning(f"No PLC data for Unit {wc} with current filters.")
                        continue
                    
                    # Calculate Statistics
                    stats = {}
                    # PLC stats
                    stats['Pressure'] = {'mean': df_plc_wc['D5017'].mean(), 'std': df_plc_wc['D5017'].std()}
                    stats['RPM'] = {'mean': df_plc_wc['D5018'].mean(), 'std': df_plc_wc['D5018'].std()}
                    
                    # Vision stats
                    if not df_vision_wc.empty:
                        if 'tangent' in df_vision_wc.columns:
                            stats['Amplitude'] = {'mean': df_vision_wc['tangent'].mean(), 'std': df_vision_wc['tangent'].std()}
                        if 'distance' in df_vision_wc.columns:
                            stats['Distance'] = {'mean': df_vision_wc['distance'].mean(), 'std': df_vision_wc['distance'].std()}
                        if 'angle' in df_vision_wc.columns:
                            stats['Angle'] = {'mean': df_vision_wc['angle'].mean(), 'std': df_vision_wc['angle'].std()}


                    # 3x3 Grid Visualization using Subplots
                    fig = make_subplots(
                        rows=3, cols=3,
                        subplot_titles=(
                            "1. Temperature (Zone 1~4)", 
                            f"2. Pressure (Mean={stats['Pressure']['mean']:.2f}, Std={stats['Pressure']['std']:.2f})", 
                            f"3. RPM (Mean={stats['RPM']['mean']:.2f}, Std={stats['RPM']['std']:.2f})",
                            "", 
                            f"Pressure Dist (Range: ±5)", 
                            f"RPM Dist (Range: ±10)",
                            f"Amplitude Dist (Range: ±0.1) Mean={stats.get('Amplitude', {}).get('mean', 0):.4f} Std={stats.get('Amplitude', {}).get('std', 0):.4f}" if 'Amplitude' in stats else "Amplitude Dist", 
                            f"Distance Dist (Range: ±50) Mean={stats.get('Distance', {}).get('mean', 0):.2f} Std={stats.get('Distance', {}).get('std', 0):.2f}" if 'Distance' in stats else "Distance Dist", 
                            f"Angle Dist (Range: ±3) Mean={stats.get('Angle', {}).get('mean', 0):.2f} Std={stats.get('Angle', {}).get('std', 0):.2f}" if 'Angle' in stats else "Angle Dist"
                        ),
                        vertical_spacing=0.15,
                        horizontal_spacing=0.05
                    )

                    # Row 1 Col 1: Temperature
                    for col, color in zip(['D5002', 'D5004', 'D5023', 'D5025'], ['blue', 'skyblue', 'red', 'pink']):
                        fig.add_trace(go.Scatter(x=df_plc_wc['ent_date'], y=df_plc_wc[col], mode='lines', name=col, line=dict(color=color)), row=1, col=1)

                    # Row 1 Col 2: Pressure
                    fig.add_trace(go.Scatter(x=df_plc_wc['ent_date'], y=df_plc_wc['D5017'], mode='lines', name='Pressure', line=dict(color='blue')), row=1, col=2)
                    
                    # Row 1 Col 3: RPM
                    fig.add_trace(go.Scatter(x=df_plc_wc['ent_date'], y=df_plc_wc['D5018'], mode='lines', name='RPM', line=dict(color='green')), row=1, col=3)

                    # Row 2 Col 2: Pressure Histogram
                    # Range: Mean +- 5
                    p_mean = stats['Pressure']['mean']
                    p_range = 5
                    fig.add_trace(go.Histogram(
                        x=df_plc_wc['D5017'], 
                        xbins=dict(start=p_mean-p_range, end=p_mean+p_range, size=(2*p_range)/100),
                        autobinx=False,
                        name='Pressure Dist', 
                        marker_color='blue'
                    ), row=2, col=2)
                    fig.update_xaxes(range=[p_mean - p_range, p_mean + p_range], row=2, col=2)

                    # Row 2 Col 3: RPM Histogram
                    # Range: Mean +- 10
                    r_mean = stats['RPM']['mean']
                    r_range = 10
                    fig.add_trace(go.Histogram(
                        x=df_plc_wc['D5018'], 
                        xbins=dict(start=r_mean-r_range, end=r_mean+r_range, size=(2*r_range)/100),
                        autobinx=False,
                        name='RPM Dist', 
                        marker_color='green'
                    ), row=2, col=3)
                    fig.update_xaxes(range=[r_mean - r_range, r_mean + r_range], row=2, col=3)

                    # Row 3 (Vision Data)
                    if not df_vision_wc.empty:
                        # Row 3 Col 1: Amplitude
                        if 'Amplitude' in stats:
                            a_mean = stats['Amplitude']['mean']
                            a_range = 0.1
                            fig.add_trace(go.Histogram(
                                x=df_vision_wc['tangent'], 
                                xbins=dict(start=a_mean-a_range, end=a_mean+a_range, size=(2*a_range)/100),
                                autobinx=False,
                                name='Amplitude', 
                                marker_color='purple'
                            ), row=3, col=1)
                            fig.update_xaxes(range=[a_mean - a_range, a_mean + a_range], row=3, col=1)
                        
                        # Row 3 Col 2: Distance
                        if 'Distance' in stats:
                            d_mean = stats['Distance']['mean']
                            d_range = 50
                            fig.add_trace(go.Histogram(
                                x=df_vision_wc['distance'], 
                                xbins=dict(start=d_mean-d_range, end=d_mean+d_range, size=(2*d_range)/100),
                                autobinx=False,
                                name='Distance', 
                                marker_color='orange'
                            ), row=3, col=2)
                            fig.update_xaxes(range=[d_mean - d_range, d_mean + d_range], row=3, col=2)

                        # Row 3 Col 3: Angle
                        if 'Angle' in stats:
                            an_mean = stats['Angle']['mean']
                            an_range = 3
                            fig.add_trace(go.Histogram(
                                x=df_vision_wc['angle'], 
                                xbins=dict(start=an_mean-an_range, end=an_mean+an_range, size=(2*an_range)/100),
                                autobinx=False,
                                name='Angle', 
                                marker_color='teal'
                            ), row=3, col=3)
                            fig.update_xaxes(range=[an_mean - an_range, an_mean + an_range], row=3, col=3)
                    
                    # Update Layout
                    fig.update_layout(
                        height=900, 
                        width=1200, 
                        title_text=f"Unit {wc} Analysis Overview",
                        showlegend=False
                    )
                    
                    # Display the single figure
                    st.plotly_chart(fig, use_container_width=True, key=f"grid_wc_{wc}", config={'displayModeBar': True})

                    
                    # CSV Export Buttons
                    c_exp1, c_exp2 = st.columns(2)
                    with c_exp1:
                        csv_plc = df_plc_wc.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label=f"Download PLC Data (Unit {wc})",
                            data=csv_plc,
                            file_name=f'plc_data_unit_{wc}.csv',
                            mime='text/csv',
                            key=f"dl_plc_{wc}"
                        )
                    with c_exp2:
                        if not df_vision_wc.empty:
                            csv_vision = df_vision_wc.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label=f"Download Vision Data (Unit {wc})",
                                data=csv_vision,
                                file_name=f'vision_data_unit_{wc}.csv',
                                mime='text/csv',
                                key=f"dl_vision_{wc}"
                            )

                # Reload Button
                st.markdown("---")
                if st.button("Reload Graphs"):
                    st.rerun()

                if st.button("Restart Auto Validation"):
                    del st.session_state.current_work_cent
                    del st.session_state.plc_filters
                    st.rerun()

            except Exception as e:
                st.error(f"An error occurred during visualization: {e}")
                logging.exception("Error in Auto Validation Visualization")

def run_weighing_data_filtering():
    """
    Weighing Data Filtering Mode
    엑셀 파일을 업로드받아 전후 시간을 필터링하고 그래프를 그려주는 기능
    """
    st.header("Weighing Data Filtering")
    
    # 1. Excel File Upload
    uploaded_file = st.file_uploader("Upload Weighing Data (Excel)", type=["xlsx", "xls"])
    
    if uploaded_file:
        try:
            # Load Excel file
            df = pd.read_excel(uploaded_file)
            st.success(f"Loaded {len(df)} rows from {uploaded_file.name}")
            
            st.markdown("### Data Preview")
            st.dataframe(df.head())
            
            # 2. Column Selection
            st.markdown("### Column Selection")
            columns = df.columns.tolist()
            
            c1, c2 = st.columns(2)
            with c1:
                time_col = st.selectbox("Select Time Column", columns, index=0 if columns else None)
            with c2:
                value_col = st.selectbox("Select Value Column", columns, index=1 if len(columns) > 1 else 0)
                
            if time_col and value_col:
                # Convert time column to datetime
                try:
                    df[time_col] = pd.to_datetime(df[time_col])
                except Exception as e:
                    st.error(f"Error converting '{time_col}' to datetime: {e}")
                    return

                # 3. Time Filtering
                st.markdown("### Time Filtering")
                
                min_time = df[time_col].min().to_pydatetime()
                max_time = df[time_col].max().to_pydatetime()
                
                # Slider for time range
                time_range = st.slider(
                    "Select Time Range",
                    min_value=min_time,
                    max_value=max_time,
                    value=(min_time, max_time),
                    format="YYYY-MM-DD HH:mm:ss"
                )
                
                # Filter data
                mask = (df[time_col] >= time_range[0]) & (df[time_col] <= time_range[1])
                df_filtered = df[mask].copy()
                
                # 4. Data Correction (Cumulative Weight)
                st.markdown("### Data Correction")
                use_correction = st.checkbox("Enable Cumulative Correction (Stitch Drops)", value=False)
                
                if use_correction:
                    drop_threshold = st.number_input(
                        "Drop Threshold (Negative Value)", 
                        value=-1000.0, 
                        step=10.0,
                        help="If the difference between consecutive points is less than this value, it's considered a drop."
                    )
                    
                    # Correction Algorithm
                    values = df_filtered[value_col].values
                    corrected_values = []
                    current_offset = 0
                    
                    if len(values) > 0:
                        corrected_values.append(values[0])
                        for i in range(1, len(values)):
                            delta = values[i] - values[i-1]
                            if delta < drop_threshold:
                                # Drop detected!
                                # Calculate offset to make the current point continue from the previous point
                                # We want: corrected_current ~= corrected_prev + (small expected increase)
                                # But we don't know the expected increase.
                                # Simple approach: Treat the drop as if it didn't happen.
                                # The 'gap' is the drop amount. We add that gap back to all future points.
                                # gap = values[i-1] - values[i]
                                # current_offset += gap
                                
                                # Better approach for "stitching":
                                # We want the new segment to start exactly where the old one ended?
                                # Or just remove the negative delta?
                                # If we just ignore the negative delta, we assume 0 change at that instant.
                                # Let's try: offset += (values[i-1] - values[i])
                                current_offset += (values[i-1] - values[i])
                            
                            corrected_values.append(values[i] + current_offset)
                            
                    df_filtered[f'{value_col}_corrected'] = corrected_values
                    plot_y_col = f'{value_col}_corrected'
                    st.info(f"Correction applied. Total offset accumulated: {current_offset:.2f}")
                else:
                    plot_y_col = value_col

                st.write(f"Filtered Data: {len(df_filtered)} rows ({len(df_filtered)/len(df)*100:.1f}%)")
                
                # 5. Visualization
                if not df_filtered.empty:
                    fig = px.line(df_filtered, x=time_col, y=plot_y_col, title=f"{plot_y_col} over Time")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Download filtered data
                    csv = df_filtered.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Filtered Data (CSV)",
                        data=csv,
                        file_name='filtered_weighing_data.csv',
                        mime='text/csv'
                    )
                else:
                    st.warning("No data selected with current filters.")
                    
        except Exception as e:
            st.error(f"Error processing file: {e}")

def run():
    """
    Auto Validation Entry Point
    Sub-navigation for Standard Validation and Weighing Data Filtering
    """
    # Sidebar Sub-navigation
    st.sidebar.markdown("---")
    sub_mode = st.sidebar.radio("Auto Validation Menu", ["Standard Validation", "Weighing Data Filtering"])
    
    if sub_mode == "Standard Validation":
        run_standard_validation()
    elif sub_mode == "Weighing Data Filtering":
        run_weighing_data_filtering()

