from typing import List

import httpx

from .base import BaseLLM, Message


class OllamaLLM(BaseLLM):
    def __init__(
        self,
        model: str = "mistral",
        base_url: str = "http://localhost:11434",
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def chat(self, messages: List[Message]) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            # Solution for Workshop Block 2.1 — ask Ollama to constrain output to
            # syntactically valid JSON. Note this does NOT guarantee our schema
            # (message/next_action keys, valid action type) is honored — only that
            # the output parses as JSON. Schema-level repair still lives in
            # temporal_app/activities/llm_activities.py (see Block 2.2).
            "format": "json",
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            return response.json()["message"]["content"]
