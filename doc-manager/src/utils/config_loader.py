import json
import os

try:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv())
except ImportError:
    pass

CONF_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

def load_config():
    """Loads configuration from src/config.json"""
    if not os.path.exists(CONF_PATH):
        raise FileNotFoundError(f"Configuration file not found at {CONF_PATH}")
    
    with open(CONF_PATH, 'r') as f:
        config = json.load(f)

    # Override with Environment Variables (Secrets)
    if 'database' in config:
        db_conf = config['database']
        db_conf['password'] = os.getenv('POSTGRES_PASSWORD', db_conf.get('password'))
        db_conf['user'] = os.getenv('POSTGRES_USER', db_conf.get('user'))
        db_conf['host'] = os.getenv('POSTGRES_HOST', db_conf.get('host'))
        db_conf['dbname'] = os.getenv('POSTGRES_DB', db_conf.get('dbname'))
        db_conf['port'] = os.getenv('POSTGRES_PORT', db_conf.get('port'))
    
    config['llm_base_url'] = os.getenv('LLM_BASE_URL', config.get('llm_base_url'))
    
    return config
