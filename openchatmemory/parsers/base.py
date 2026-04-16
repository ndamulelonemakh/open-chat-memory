from __future__ import annotations

from pathlib import Path

from ..schemas import MessageModel


class BaseParser:
    provider: str = "base"

    def parse(self, input_path: Path) -> list[MessageModel]:  # pragma: no cover - abstract
        raise NotImplementedError


class ParserRegistry:
    _registry: dict[str, type[BaseParser]] = {}

    @classmethod
    def register(cls, provider: str, parser_cls: type[BaseParser]) -> None:
        cls._registry[provider.lower()] = parser_cls

    @classmethod
    def get(cls, provider: str) -> type[BaseParser] | None:
        return cls._registry.get(provider.lower())

    @classmethod
    def available(cls) -> list[str]:
        return sorted(cls._registry.keys())
