import os
import logging
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv
import base64
from sentence_transformers import SentenceTransformer

# Load envs: Root (.env) for secrets, Local (.env) for app config
root_env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
local_env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))

load_dotenv(root_env_path)
load_dotenv(local_env_path) # Local override or addition
logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        # Text Model (Llama.cpp)
        self.text_base_url = os.getenv("TEXT_MODEL_BASE_URL")
        if not self.text_base_url:
            self.text_base_url = "http://localhost:8080/v1"
            logger.info(f"TEXT_MODEL_BASE_URL not set. Using default: {self.text_base_url}")
            
        self.text_api_key = os.getenv("TEXT_MODEL_API_KEY", "sk-no-key-required")
        self.text_client = OpenAI(base_url=self.text_base_url, api_key=self.text_api_key)

        # Vision Model (Ollama)
        self.vl_base_url = os.getenv("VL_MODEL_BASE_URL")
        if not self.vl_base_url:
             self.vl_base_url = "http://localhost:11434/v1"
             
        self.vl_api_key = "ollama" 
        self.vl_client = OpenAI(base_url=self.vl_base_url, api_key=self.vl_api_key)

        # Embedding Model (Local SentenceTransformer)
        self.embedding_model_name = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
        logger.info(f"Loading local embedding model: {self.embedding_model_name}...")
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        logger.info("Local embedding model loaded.")

        # Provider Map
        self.providers = {
            "llama.cpp": self.text_base_url,
            "ollama": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            "openai": "https://api.openai.com/v1"
        }

    def generate_text_summary(self, system_prompt: str, user_content: str, model: str = "default-model", temperature: float = 0.7, max_tokens: int = 2048, provider: str = "llama.cpp") -> Optional[str]:
        """Generates a text summary using the specified provider."""
        try:
            base_url = self.providers.get(provider.lower(), self.text_base_url)
            api_key = self.text_api_key
            if provider.lower() == "openai":
                api_key = os.getenv("OPENAI_API_KEY", "")
            
            # Temporary client for flexibility (lightweight)
            client = OpenAI(base_url=base_url, api_key=api_key)
            
            logger.info(f"Sending request to {provider} ({base_url}) - Model: {model}, Temp: {temperature}...")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Text Generation Failed: {e}")
            return None

    def generate_image_description(self, system_prompt: str, image_path: str, model: str = "llava") -> Optional[str]:
        """Generates an image description using Ollama (VL)."""
        try:
            # Encode image
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            logger.info(f"Sending request to VL Model ({self.vl_base_url})...")
            response = self.vl_client.chat.completions.create(
                model=model, # e.g. "llava" or "bakllava"
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": system_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Vision Generation Failed: {e}")
            return None

    def get_embedding(self, text: str) -> Optional[list[float]]:
        """Generates embeddings using Local SentenceTransformer."""
        try:
            # Local generation
            embedding = self.embedding_model.encode(text).tolist()
            return embedding
        except Exception as e:
            logger.error(f"Embedding Generation Failed: {e}")
            return None
