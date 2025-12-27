import requests
import json
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_llm():
    url = "http://192.168.1.238:8080/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    
    content = "fglkdfjgfdjsgldfj;sl"
    prompt_template = "Extract key technical keywords and a short descriptive title (around 20 characters)."
    
    full_prompt = (
        f"{prompt_template}\n\n"
        f"Content:\n{content}\n\n"
        "Produce a valid JSON object. Do not include markdown or explanations.\n"
        "Format: {\"keywords\": [\"word1\", \"word2\"], \"title\": \"Descriptive Title\"}"
    )
    
    payload = {
        "model": "gpt-oss-20b",
        "messages": [{"role": "user", "content": full_prompt}],
        "temperature": 0.1,
        "max_tokens": 1024
    }
    
    logger.info(f"Sending request to {url}")
    start = time.time()
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=1200)
        response.raise_for_status()
        logger.info(f"Success! Time: {time.time() - start:.2f}s")
        print(response.json())
    except Exception as e:
        logger.error(f"Failed! Time: {time.time() - start:.2f}s Error: {e}")

if __name__ == "__main__":
    test_llm()
