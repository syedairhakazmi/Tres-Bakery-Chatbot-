import json
import time
import requests

OLLAMA_URL = "http://localhost:11434"
MODEL_NAME = "qwen3:1.7b"

def stream_chat (messages):
    """Send messages to Ollama, yield tokens one by one. Also returns latency."""
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": True,
        "options": {
            "temperature": 0.1,
            "num_predict": 450,
            "num_ctx": 2048,
            "think": False,
            "stop": ["User:", "Customer:", "\n\nUser", "\n\nCustomer"]
        }
    }

    start = time.time ()
    first_token_time = None

    response = requests.post (
        OLLAMA_URL + "/api/chat",
        json = payload,
        stream = True,
        timeout = 120
    )
    response.raise_for_status ()

    for line in response.iter_lines ():
        if line:
            try:
                chunk = json.loads (line)
                token = chunk.get ("message", {}).get ("content", "")
                if token:
                    if first_token_time is None:
                        first_token_time = time.time () - start
                    yield token
                if chunk.get ("done"):
                    break
            except json.JSONDecodeError:
                continue

    total_latency = time.time () - start
    # Yield a special end marker with latency info
    yield "__DONE__:" + str (round (total_latency, 3)) + ":" + str (round (first_token_time or 0, 3))

def check_health ():
    try:
        response = requests.get (OLLAMA_URL + "/api/tags", timeout=5)
        models = response.json ().get ("models", [])
        for model in models:
            if MODEL_NAME in model ["name"]:
                return True
        return False
    except Exception:
        return False
