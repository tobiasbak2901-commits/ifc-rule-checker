from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from ai.models import AIContext


class BaseProvider(ABC):
    @abstractmethod
    def rephrase(self, text: str, context: AIContext, allowed_citations: Iterable[str]) -> str:
        raise NotImplementedError
