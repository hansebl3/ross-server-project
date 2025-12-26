import plotly.express as px

def create_full_time_series(df, x_col, y_col, title):
    """
    전체 시계열 데이터에 대한 라인 차트를 생성합니다.
    데이터가 5000개를 초과할 경우 자동으로 다운샘플링합니다.
    """
    # 다운샘플링 로직 (Max 5000개)
    MAX_POINTS = 5000
    if len(df) > MAX_POINTS:
        step = len(df) // MAX_POINTS
        df = df.iloc[::step]
        title += f" (Sampled 1/{step})"

    fig = px.line(df, x=x_col, y=y_col, title=title)
    
    # 6시간 단위 그리드 설정 (6시간 = 21,600,000 밀리초)
    fig.update_xaxes(
        dtick=21600000, 
        tickformat="%Y-%m-%d %H:%M",
        showgrid=True
    )
    return fig

def create_line_chart(df, x_col, y_col, title, x_label, y_label):
    """
    선택된 범위의 시계열 라인 차트를 생성합니다.
    X축과 Y축의 레이블을 사용자가 지정한 값으로 설정할 수 있습니다.
    
    Args:
        df (pd.DataFrame): 데이터프레임
        x_col (str): X축 컬럼명
        y_col (str): Y축 컬럼명
        title (str): 차트 제목
        x_label (str): X축 레이블
        y_label (str): Y축 레이블
        
    Returns:
        plotly.graph_objects.Figure: 생성된 Plotly 차트 객체
    """
    fig = px.line(df, x=x_col, y=y_col, title=title)
    fig.update_layout(xaxis_title=x_label, yaxis_title=y_label)
    return fig

def create_histogram(df, x_col, title, x_label, y_label, nbins=300):
    """
    데이터 분포를 보여주는 히스토그램을 생성합니다.
    
    Args:
        df (pd.DataFrame): 데이터프레임
        x_col (str): 데이터 컬럼명
        title (str): 차트 제목
        x_label (str): X축 레이블 (사용되지 않음, 호환성 유지)
        y_label (str): Y축 레이블 (데이터 값의 의미)
        nbins (int, optional): 히스토그램 빈(bin) 개수. 기본값은 300.
        
    Returns:
        plotly.graph_objects.Figure: 생성된 Plotly 차트 객체
    """
    fig = px.histogram(df, x=x_col, title=title, nbins=nbins)
    # 히스토그램에서 X축은 데이터 값(y_label), Y축은 빈도수(Count)입니다.
    fig.update_layout(xaxis_title=y_label, yaxis_title="Count") 
    return fig

