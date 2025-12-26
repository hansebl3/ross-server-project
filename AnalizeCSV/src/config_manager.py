import json
import os

CONFIG_FILE = "db_config.json"

def load_config():
    """
    설정 파일(db_config.json)을 로드합니다.
    파일이 존재하지 않거나 에러가 발생하면 빈 딕셔너리를 반환합니다.
    
    Returns:
        dict: 설정 정보를 담은 딕셔너리
    """
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
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
