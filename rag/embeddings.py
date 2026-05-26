import os
from types import SimpleNamespace

import requests


def _api_key():
    return os.getenv("GROQ_API_KEY")


class GroqChatModel:
    def __init__(self):
        self.api_key = _api_key()
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"

    def invoke(self, prompt):
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY is not configured.")

        response = requests.post(
            self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 900,
            },
            timeout=45,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return SimpleNamespace(content=content)


def get_chat_model():
    return GroqChatModel()
