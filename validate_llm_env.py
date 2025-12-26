import os
import sys

# Set Env Var
os.environ["OPENAI_API_KEY"] = "TEST_KEY_FROM_ENV"

print("--- Testing News Reader LLM Manager ---")
sys.path.append("/home/ross/pythonproject/news-reader/src")
try:
    from modules.llm_manager import LLMManager
    # LLMManager init loads providers which loads config
    # But it might require 'llm_config.json' to exist.
    # The actual file exists in /home/ross/pythonproject/news-reader/src/modules/../../llm_config.json
    # which is /home/ross/pythonproject/news-reader/llm_config.json. It exists.
    
    mgr = LLMManager()
    conf = mgr.get_config()
    print(f"NewsReader API Key: {conf.get('api_keys', {}).get('openai')}")
    assert conf.get('api_keys', {}).get('openai') == "TEST_KEY_FROM_ENV"
    print("PASS")
except Exception as e:
    print(f"FAIL: {e}")

print("\n--- Testing Dashboard LLM Manager ---")
# Reset sys.path to avoid module name collision if any
sys.path = [p for p in sys.path if "news-reader" not in p]
sys.path.append("/home/ross/pythonproject/my-dashboard/src")

# Dashboard LLMManager expects llm_config.json in CWD?
# In get_config(): config_path = "llm_config.json"
# So we must chdir to my-dashboard/src or my-dashboard? 
# The file is likely in my-dashboard/llm_config.json or my-dashboard/src/llm_config.json?
# Let's check where it normally runs. usually from root of project?
# In my-dashboard/src/modules/llm_manager.py, it just says "llm_config.json".
# If the app runs from `src`, then it expects it in `src`. 
# If it runs from `my-dashboard`, it expects it in `my-dashboard`.
# Let's try locating it.
# Check where llm_config.json is for my-dashboard.
# Based on file listing, it is /home/ross/pythonproject/my-dashboard/llm_config.json
# So if running from /home/ross/pythonproject/my-dashboard, it works.

os.chdir("/home/ross/pythonproject/my-dashboard")
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

try:
    # Now we are in my-dashboard, so "llm_config.json" should be found.
    # And we added ./src to path, so "modules" can be imported.
    from modules.llm_manager import LLMManager as DashLLMManager
    mgr = DashLLMManager()
    
    conf = mgr.get_config()
    print(f"Dashboard API Key: {conf.get('api_keys', {}).get('openai')}")
    assert conf.get('api_keys', {}).get('openai') == "TEST_KEY_FROM_ENV"
    print("PASS")
except Exception as e:
    print(f"FAIL: {e}")
