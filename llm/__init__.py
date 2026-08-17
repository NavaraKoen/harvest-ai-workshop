import os

from .base import BaseLLM, Message
from .ollama_llm import OllamaLLM
from .openai_llm import OpenAILLM

__all__ = ["BaseLLM", "Message", "OllamaLLM", "OpenAILLM", "create_llm"]


def create_llm() -> BaseLLM:
    """Create an LLM instance based on environment configuration."""
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()

    if provider == "openai":
        return OpenAILLM(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
        )

    # Default: Ollama (local)
    return OllamaLLM(
        model=os.getenv("OLLAMA_MODEL", "mistral"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    )
