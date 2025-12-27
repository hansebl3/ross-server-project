import pandas as pd
import pymysql
from datetime import datetime

def load_csv(uploaded_file):
    """
    업로드된 CSV 파일을 pandas DataFrame으로 로드합니다.
    
    Args:
        uploaded_file: Streamlit file_uploader 객체 또는 파일 경로
        
    Returns:
        pd.DataFrame: 로드된 데이터
        
    Raises:
        Exception: CSV 파일 읽기 실패 시 발생
    """
    try:
        df = pd.read_csv(uploaded_file)
        return df
    except Exception as e:
        raise Exception(f"CSV 읽기 오류: {e}")

def load_db(config, start_date, end_date):
    """
    MariaDB 데이터베이스에서 지정된 기간의 데이터를 로드합니다.
    
    Args:
        config (dict): DB 연결 설정 (host, port, user, password, database, table, date_col_db)
        start_date (datetime.date): 조회 시작 날짜
        end_date (datetime.date): 조회 종료 날짜
        
    Returns:
        pd.DataFrame: 로드된 데이터
        
    Raises:
        Exception: 데이터베이스 연결 또는 쿼리 실행 실패 시 발생
    """
    # 날짜 범위가 전체 하루를 포함하도록 시간 조정 (00:00:00 ~ 23:59:59.999999)
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    try:
        # DB 연결 설정 (Shared Connector)
        from shared.db.mariadb import MariaDBConnector
        connector = MariaDBConnector()
        # Use DB name from config if provided, allowing flexibility (or default to Env)
        target_db = config.get('database') 
        conn = connector.get_connection(db_name=target_db)
        
        # 쿼리 실행
        table = config['table']
        date_col = config['date_col_db']
        
        # SQL Injection 방지를 위해 파라미터 바인딩 사용 (pd.read_sql에서 지원)
        query = f"SELECT * FROM {table} WHERE {date_col} BETWEEN %s AND %s"
        
        df = pd.read_sql(query, conn, params=(start_dt, end_dt))
        conn.close()
        
        return df
        
    except Exception as e:
        raise Exception(f"데이터베이스 오류: {e}")
