import mysql.connector
import json
import logging
import os

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_config():
    with open('config.json', 'r') as f:
        config = json.load(f)

    # Override with Environment Variables (Secrets)
    if 'news_db' not in config:
        config['news_db'] = {}
        
    config['news_db']['password'] = os.getenv('MARIADB_PASSWORD', config['news_db'].get('password'))
    config['news_db']['user'] = os.getenv('MARIADB_USER', config['news_db'].get('user'))
    config['news_db']['host'] = os.getenv('MARIADB_HOST', config['news_db'].get('host'))
    
    return config

def setup_database():
    from shared.db.mariadb import MariaDBConnector
    
    config = load_config()
    # db_config is used for db_name if needed, but shared connector uses ENV primarily.
    # But let's keep db_name lookup from config as fallback if needed, or just rely on shared.
    target_db = os.getenv("MARIADB_DB", config.get('news_db', {}).get('database', 'news_db'))
    
    try:
        # Connect without DB to ensure creation
        conn = MariaDBConnector().get_connection(db_name="")
        cursor = conn.cursor()
        
        # Create DB
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {target_db}")
        logger.info(f"Database '{target_db}' check/creation completed.")
        
        # Connect to Specific DB
        # Re-connect or use USE? 
        # Shared connector doesn't switch DB easily on existing conn, but we can execute USE.
        cursor.execute(f"USE {target_db}")
        
        # 테이블 생성
        create_table_query = """
        CREATE TABLE IF NOT EXISTS tb_news (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            link VARCHAR(500) NOT NULL,
            published_date VARCHAR(100),
            summary TEXT,
            content TEXT,
            source VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unique_link (link)
        )
        """
        cursor.execute(create_table_query)
        logger.info("Table 'tb_news' check/creation completed.")
        
        cursor.close()
        conn.close()
        logger.info("Database setup finished successfully.")
        
    except Exception as err:
        logger.error(f"Error: {err}")

if __name__ == "__main__":
    setup_database()
