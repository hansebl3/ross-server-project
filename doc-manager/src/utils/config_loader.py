import json
import os

CONF_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

def load_config():
    """Loads configuration from src/config.json"""
    if not os.path.exists(CONF_PATH):
        raise FileNotFoundError(f"Configuration file not found at {CONF_PATH}")
    
    with open(CONF_PATH, 'r') as f:
        config = json.load(f)

    # Override with Environment Variables (Secrets)
    if 'database' in config:
        config['database']['password'] = os.getenv('DB_PASSWORD', config['database'].get('password'))
        config['database']['user'] = os.getenv('DB_USER', config['database'].get('user'))
        config['database']['host'] = os.getenv('DB_HOST', config['database'].get('host'))
    
    config['llm_base_url'] = os.getenv('OLLAMA_BASE_URL', config.get('llm_base_url'))
    
    return config
