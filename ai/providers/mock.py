from __future__ import annotations

from typing import Iterable

from ai.models import AIContext
from ai.providers.base import BaseProvider


class MockProvider(BaseProvider):
    def rephrase(self, text: str, context: AIContext, allowed_citations: Iterable[str]) -> str:
        del context
        del allowed_citations
        line = str(text or "").strip()
        if not line:
            return "Ponker siger: Ingen yderligere tekst."
        if line.lower().startswith("ponker siger"):
            return line
        return f"Ponker siger: {line}"
