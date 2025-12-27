import requests
import json
import logging
import os
from utils.config_loader import load_config

logger = logging.getLogger(__name__)

class RetryableLLMError(Exception):
    """Raised when the LLM provider is busy or unavailable (429, 503, Timeout)"""
    pass

class LLMClient:
    def __init__(self):
        config = load_config()
        self.base_url = config.get("llm_base_url", "http://192.168.1.238:8080/v1")

    def generate_content(self, content, model, prompt_template):
        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": f"{prompt_template}\n\nContent:\n{content}"}],
            "temperature": 0.3,
            "max_tokens": 4096,
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=180)
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content']
        except requests.exceptions.HTTPError as he:
            if he.response.status_code in [429, 503]:
                raise RetryableLLMError(f"LLM Busy (Status {he.response.status_code})")
            logger.error(f"HTTP Error calling LLM ({model}): {he}")
            return f"Error: {he}"
        except requests.exceptions.Timeout:
            raise RetryableLLMError("LLM Timeout")
        except Exception as e:
            logger.error(f"Error calling LLM ({model}): {e}")
            return f"Error: {e}"

    def extract_metadata(self, content, model, prompt_template):
        """Extracts keywords and title as a JSON object"""
        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        # Expecting JSON response
        full_prompt = (
            f"{prompt_template}\n\n"
            f"Content:\n{content}\n\n"
            "Produce a valid JSON object. Do not include markdown or explanations.\n"
            "Format: {\"keywords\": [\"word1\", \"word2\"], \"title\": \"Descriptive Title\"}"
        )
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": full_prompt}],
            "temperature": 0.1,
            "max_tokens": 1024
        }
        try:
            logger.info(f"Extracting metadata with timeout=1200 for model {model} (JSON mode: OFF)")
            response = requests.post(url, headers=headers, json=payload, timeout=1200)
            response.raise_for_status()
            
            # Robust JSON extraction
            import re
            raw_content = response.json()['choices'][0]['message']['content']
            json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            return {"keywords": [], "title": "unknown"}
        except requests.exceptions.HTTPError as he:
            if he.response.status_code in [429, 503]:
                raise RetryableLLMError(f"LLM Busy (Status {he.response.status_code})")
            logger.error(f"Metadata extract HTTP error: {he}")
            return {"keywords": [], "title": "unknown"}
        except requests.exceptions.Timeout:
            raise RetryableLLMError("LLM Timeout extracting metadata")
        except Exception as e:
            logger.error(f"Metadata extract error: {e}")
            return {"keywords": [], "title": "unknown"}
            
    def get_available_models(self):
        try:
            response = requests.get(f"{self.base_url}/models", timeout=5)
            data = response.json()
            return [m['id'] for m in data['data']]
        except:
            return ["Qwen3-80b-Instruct", "llama-3-8b"] # Fallback
