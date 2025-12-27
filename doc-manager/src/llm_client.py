import logging
import json
from shared.llm.client import LLMClient as SharedLLMClient

logger = logging.getLogger(__name__)

class RetryableLLMError(Exception):
    pass

class LLMClient:
    def __init__(self):
        # Shared client auto-loads from env LLM_BASE_URL
        self.client = SharedLLMClient()

    def generate_content(self, content, model, prompt_template):
        messages = [{"role": "user", "content": f"{prompt_template}\n\nContent:\n{content}"}]
        try:
            return self.client.generate(messages, model=model, temperature=0.3, max_tokens=4096)
        except Exception as e:
            if "Busy" in str(e) or "503" in str(e):
                 raise RetryableLLMError(f"LLM Error: {e}")
            return f"Error: {e}"

    def extract_metadata(self, content, model, prompt_template):
        full_prompt = (
            f"{prompt_template}\n\n"
            f"Content:\n{content}\n\n"
            "Produce a valid JSON object. Do not include markdown or explanations.\n"
            "Format: {\"keywords\": [\"word1\", \"word2\"], \"title\": \"Descriptive Title\"}"
        )
        messages = [{"role": "user", "content": full_prompt}]
        
        try:
            # We enforce json_mode=True if supported, or rely on prompt
            raw_response = self.client.generate(messages, model=model, temperature=0.1, max_tokens=1024)
            
            # Parse JSON
            import re
            json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            return {"keywords": [], "title": "unknown"}
            
        except Exception as e:
             if "Busy" in str(e):
                 raise RetryableLLMError(f"LLM Busy: {e}")
             logger.error(f"Metadata extraction failed: {e}")
             return {"keywords": [], "title": "unknown"}

    def get_available_models(self):
        return self.client.get_models()
