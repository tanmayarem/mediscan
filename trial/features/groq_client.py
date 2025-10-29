import os
import requests
from typing import List, Dict, Optional

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def groq_chat(messages: List[Dict[str, str]],
              model: str = "llama-3.1-8b-instant",
              temperature: float = 0.3,
              max_tokens: int = 600,
              api_key: Optional[str] = None) -> Optional[str]:
    key = api_key or os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    try:
        resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None
