"""Abstração de provedor de IA, configurável por ambiente.

A plataforma funciona integralmente sem IA. Nenhuma credencial é exposta ao
cliente; chamadas ocorrem exclusivamente no servidor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AIMessage:
    role: str  # system | user | assistant
    content: str


@dataclass
class AICompletion:
    text: str
    model: str
    provider: str
    usage: dict | None = None
    citations: list[dict] = field(default_factory=list)


class AIProvider(Protocol):
    name: str

    def complete(self, messages: list[AIMessage], *, temperature: float = 0.2) -> AICompletion:
        ...


class DisabledProvider:
    name = "disabled"

    def complete(self, messages: list[AIMessage], *, temperature: float = 0.2) -> AICompletion:
        raise RuntimeError("Nenhum provedor de IA configurado.")


class OpenAICompatibleProvider:
    """Cliente para APIs compatíveis com OpenAI (OpenAI, Azure, Ollama/vLLM...)."""

    name = "openai"

    def __init__(self, model: str, api_key: str, base_url: str | None = None) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")

    def complete(self, messages: list[AIMessage], *, temperature: float = 0.2) -> AICompletion:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": settings.ai_max_output_tokens,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=60) as client:
            response = client.post(
                f"{self.base_url}/chat/completions", json=payload, headers=headers
            )
            response.raise_for_status()
            data = response.json()

        text = data["choices"][0]["message"]["content"]
        return AICompletion(
            text=text,
            model=self.model,
            provider=self.name,
            usage=data.get("usage"),
        )


def get_provider() -> AIProvider:
    if not settings.ai_enabled:
        return DisabledProvider()
    if settings.ai_provider in ("openai", "local"):
        return OpenAICompatibleProvider(
            model=settings.ai_model or "gpt-4o-mini",
            api_key=settings.ai_api_key,
            base_url=settings.ai_base_url or None,
        )
    return DisabledProvider()
