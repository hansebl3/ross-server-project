"""
Configuration Manager for AnalizeCSV
------------------------------------
Handles loading and saving of database configurations.
Prioritizes environment variables (secrets) over local JSON files.
"""
import json
import os

CONFIG_FILE = "db_config.json"

def load_config():
    """
    설정 파일(db_config.json)을 로드합니다.
    Loads configuration from `db_config.json`.
    
    Security Note:
    - Overrides sensitive keys (like 'password') with environment variables 
      (e.g., `ANALIZE_DB_PASSWORD`) if they exist.
    
    Returns:
        dict: 설정 정보를 담은 딕셔너리 (Merged config).
    """
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            
            # Env Override
            config['password'] = os.getenv("ANALIZE_DB_PASSWORD", config.get('password'))
            return config
        except:
            return {}
    return {}

def save_config(config):
    """
    설정 정보를 파일(db_config.json)에 저장합니다.
    
    Args:
        config (dict): 저장할 설정 정보
    """
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)
