"""各招聘平台的 provider：負責呼叫對應 CLI 並正規化為 Job 清單。"""

from __future__ import annotations

from .base import Provider, ProviderError, ProviderResult
from .boss import BossProvider
from .liepin import LiepinProvider

REGISTRY: dict[str, type[Provider]] = {
    "boss": BossProvider,
    "liepin": LiepinProvider,
}

__all__ = [
    "Provider",
    "ProviderError",
    "ProviderResult",
    "BossProvider",
    "LiepinProvider",
    "REGISTRY",
]
