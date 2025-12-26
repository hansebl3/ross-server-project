import json
import os

CONF_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

def load_config():
    """Loads configuration from src/config.json"""
    if not os.path.exists(CONF_PATH):
        raise FileNotFoundError(f"Configuration file not found at {CONF_PATH}")
    
    with open(CONF_PATH, 'r') as f:
        return json.load(f)
