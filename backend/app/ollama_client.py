import requests
import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
#MODEL_NAME = "qwen:0.5b"
MODEL_NAME = "qwen2.5:0.5b"


def generate_answer(prompt: str) -> str:
    response = requests.post(
    #     f"{OLLAMA_BASE_URL}/api/generate",
    #     json={
    #         "model": MODEL_NAME,
    #         "prompt": prompt,
    #         "stream": False
    #     },
    #     timeout=120
    # )
    f"{OLLAMA_BASE_URL}/api/chat",
    json={
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }
    )


    response.raise_for_status()
    #return response.json()["response"]
    return response.json()["message"]["content"]
