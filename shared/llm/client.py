import requests
import json
import logging
import os
import time

logger = logging.getLogger(__name__)

class LLMClient:
    """
    Unified LLM Client used by all services.
    Supports OpenAI-compatible endpoints (like Llama.cpp, LM Studio, etc.)
    """
    def __init__(self, base_url=None, api_key=None, default_model=None):
        # Prefer provided args, fallback to ENV, then default
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "http://192.168.1.238:8080/v1")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "dummy-key")
        self.default_model = default_model or "Qwen3-80b-Instruct" # Can be updated dynamically
        
        # Ensure base URL doesn't end with slash
        self.base_url = self.base_url.rstrip('/')

    def generate(self, messages, model=None, temperature=0.7, max_tokens=2048, stream=False, json_mode=False):
        """
        Generic generation method.
        messages: list of dicts [{'role': 'user', 'content': '...'}]
        """
        target_model = model or self.default_model
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            if stream:
                return self._stream_response(url, headers, payload)
            else:
                response = requests.post(url, headers=headers, json=payload, timeout=120)
                response.raise_for_status()
                data = response.json()
                return data['choices'][0]['message']['content']
                
        except Exception as e:
            logger.error(f"LLM Generation Error ({target_model}): {e}")
            return f"Error: {e}"

    def _stream_response(self, url, headers, payload):
        """Generator for streaming responses"""
        try:
            with requests.post(url, headers=headers, json=payload, stream=True, timeout=120) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if line:
                        decoded = line.decode('utf-8')
                        if decoded.startswith("data: "):
                            if decoded == "data: [DONE]":
                                break
                            try:
                                chunk = json.loads(decoded[6:])
                                delta = chunk['choices'][0]['delta'].get('content')
                                if delta:
                                    yield delta
                            except:
                                pass
        except Exception as e:
            yield f"Error: {e}"

    def get_models(self):
        """Fetch available models from the endpoint."""
        try:
            url = f"{self.base_url}/models"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if 'data' in data:
                    return [m['id'] for m in data['data']]
                return [str(m) for m in data]
        except Exception as e:
            logger.warning(f"Failed to fetch models: {e}")
        return [self.default_model]
