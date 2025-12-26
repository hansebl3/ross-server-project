import json
import os

paths = [
    "/home/ross/pythonproject/rag/src/llm_config.json",
    "/home/ross/pythonproject/rag_diary/src/llm_config.json"
]

new_providers = [
    {
        "name": "remote",
        "display_name": "Ollama (2080ti)",
        "url": "http://100.65.53.9:11434",
        "type": "ollama"
    },
    {
        "name": "3950x",
        "display_name": "LM Studio (3950x)",
        "url": "http://100.110.190.110:1234/v1",
        "type": "openai"
    }
]

for path in paths:
    if os.path.exists(path):
        with open(path, "r") as f:
            data = json.load(f)
        
        # Add custom_providers
        if "custom_providers" not in data:
            data["custom_providers"] = []
            
        # Merge/Overwrite
        # simplistic approach: if name exists, update, else append
        current = {p['name']: p for p in data["custom_providers"]}
        for np in new_providers:
            current[np['name']] = np
            
        data["custom_providers"] = list(current.values())
        
        with open(path, "w") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Updated {path}")
    else:
        print(f"File not found: {path}")
