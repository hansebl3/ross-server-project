import requests
import json
import time

url = "http://192.168.1.238:8080/v1/chat/completions"
headers = {"Content-Type": "application/json"}
payload = {
    "model": "qwen3-coder-30b-Instruct", 
    "messages": [{"role": "user", "content": "Hello, are you working?"}],
    "max_tokens": 10
}

print(f"Testing LLM at {url}...")
try:
    start = time.time()
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:200]}")
    print(f"Latency: {time.time() - start:.2f}s")
except Exception as e:
    print(f"LLM Connection Failed: {e}")
