"""設定載入：讀 YAML、套用命令列覆蓋、提供預設值。"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


DEFAULTS: dict[str, Any] = {
    "searches": [],
    "filters": {
        "city": "",
        "salary": "",
        "experience": "",
        "education": "",
        "job_type": "",
    },
    "limit": 20,
    "providers": {
        "boss": {"enabled": True},
        "liepin": {"enabled": True},
    },
}


@dataclass
class SearchSpec:
    """單一組搜索：職位關鍵字 + 技能。"""

    query: str
    skills: list[str] = field(default_factory=list)

    @property
    def full_query(self) -> str:
        """把技能併入關鍵字，形成實際送出的搜索詞。"""
        parts = [self.query.strip(), *[s.strip() for s in self.skills if s.strip()]]
        return " ".join(p for p in parts if p)


@dataclass
class Config:
    searches: list[SearchSpec]
    filters: dict[str, str]
    limit: int
    providers: dict[str, dict[str, Any]]

    def enabled_providers(self) -> list[str]:
        return [name for name, cfg in self.providers.items() if cfg.get("enabled")]


def _deep_merge(base: dict, override: dict) -> dict:
    """遞迴合併 override 到 base（不改動輸入）。"""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_config(path: str | Path | None, overrides: dict[str, Any] | None = None) -> Config:
    """載入設定檔並套用覆蓋。

    path 為 None 或檔案不存在時，使用內建預設值（搭配 overrides 可純命令列執行）。
    overrides 支援的鍵：query, city, salary, experience, education, job_type,
    limit, providers（dict）。
    """
    data = copy.deepcopy(DEFAULTS)

    if path is not None:
        p = Path(path)
        if p.exists():
            loaded = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            if not isinstance(loaded, dict):
                raise ValueError(f"設定檔格式錯誤（應為對應表）：{p}")
            data = _deep_merge(data, loaded)

    overrides = overrides or {}

    # 命令列單一 query 覆蓋整份 searches
    if overrides.get("query"):
        data["searches"] = [{"query": overrides["query"], "skills": overrides.get("skills", [])}]

    for fkey in ("city", "salary", "experience", "education", "job_type"):
        if overrides.get(fkey):
            data["filters"][fkey] = overrides[fkey]

    if overrides.get("limit") is not None:
        data["limit"] = overrides["limit"]

    if overrides.get("providers"):
        data["providers"] = _deep_merge(data["providers"], overrides["providers"])

    searches = [
        SearchSpec(query=s["query"], skills=list(s.get("skills", []) or []))
        for s in data["searches"]
        if s.get("query")
    ]

    return Config(
        searches=searches,
        filters={k: str(v or "") for k, v in data["filters"].items()},
        limit=int(data["limit"]),
        providers=data["providers"],
    )
