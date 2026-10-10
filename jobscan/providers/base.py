"""Provider 基底定義與共用的子程序呼叫工具。"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field

from ..config import Config, SearchSpec
from ..models import Job


class ProviderError(Exception):
    """provider 無法完成搜索（CLI 缺失、登入態失效、風控等）。"""


@dataclass
class ProviderResult:
    """單一 provider 對單一 query 的搜索結果。"""

    provider: str
    query: str
    jobs: list[Job] = field(default_factory=list)
    error: str = ""  # 非空代表此次搜索失敗，但不中斷整體流程


class Provider:
    """所有平台 provider 的介面。"""

    name: str = "base"

    def __init__(self, config: Config) -> None:
        self.config = config

    def is_available(self) -> bool:
        """對應 CLI 是否可執行。"""
        raise NotImplementedError

    def search(self, spec: SearchSpec) -> ProviderResult:
        """對單一組搜索條件執行搜索並回傳正規化結果。"""
        raise NotImplementedError


def run_cli(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    """執行外部 CLI。失敗不丟例外，由呼叫端依 returncode / stdout 判斷。

    使用 list 形式的 args（非 shell 字串）以避免注入。
    """
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
