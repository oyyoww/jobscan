"""boss provider：呼叫 boss-agent-cli 的 `boss search`，解析 JSON 信封為 Job 清單。

boss search 輸出 JSON 信封：{ok, data, pagination, error, hints}
其中 data 為職位 dict 列表，每筆欄位參見 boss_agent_cli JobItem.to_dict：
title/company/salary/city/experience/education/skills/security_id/job_id ...
"""

from __future__ import annotations

import json
import shutil

from ..config import Config, SearchSpec
from ..models import Job
from .base import Provider, ProviderResult, run_cli

# boss search 參數對應 jobscan filters 的鍵
_FILTER_TO_FLAG = {
    "city": "--city",
    "salary": "--salary",
    "experience": "--experience",
    "education": "--education",
    "job_type": "--job-type",
}


class BossProvider(Provider):
    name = "boss"

    def is_available(self) -> bool:
        return shutil.which("boss") is not None

    def _build_args(self, spec: SearchSpec) -> list[str]:
        args = ["boss", "search", spec.full_query]
        for fkey, flag in _FILTER_TO_FLAG.items():
            value = self.config.filters.get(fkey, "").strip()
            if value:
                args += [flag, value]
        return args

    def search(self, spec: SearchSpec) -> ProviderResult:
        result = ProviderResult(provider=self.name, query=spec.full_query)

        if not self.is_available():
            result.error = "找不到 boss 執行檔，請先安裝 boss-agent-cli（uv tool install boss-agent-cli）"
            return result

        args = self._build_args(spec)
        try:
            proc = run_cli(args)
        except Exception as exc:  # noqa: BLE001 - 子程序層面任何失敗都轉為軟錯誤
            result.error = f"執行 boss search 失敗：{exc}"
            return result

        envelope = _parse_envelope(proc.stdout)
        if envelope is None:
            tail = (proc.stderr or proc.stdout or "").strip()[-300:]
            result.error = f"無法解析 boss 輸出（exit={proc.returncode}）：{tail}"
            return result

        if not envelope.get("ok", False):
            err = envelope.get("error") or {}
            code = err.get("code", "UNKNOWN") if isinstance(err, dict) else str(err)
            action = err.get("recovery_action", "") if isinstance(err, dict) else ""
            result.error = f"boss 回報錯誤 [{code}] {action}".strip()
            return result

        items = envelope.get("data") or []
        if not isinstance(items, list):
            items = []
        for item in items[: self.config.limit]:
            result.jobs.append(_item_to_job(item))
        return result


def _parse_envelope(stdout: str) -> dict | None:
    """從 stdout 取出 JSON 信封。boss 保證 stdout 僅輸出 JSON，但保險起見逐行嘗試。"""
    text = (stdout or "").strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                continue
    return None


def _item_to_job(item: dict) -> Job:
    skills = item.get("skills") or item.get("job_labels") or []
    if not isinstance(skills, list):
        skills = [str(skills)]
    security_id = item.get("security_id", "")
    url = f"https://www.zhipin.com/job_detail/?securityId={security_id}" if security_id else ""
    return Job(
        source="boss",
        title=str(item.get("title", "")),
        company=str(item.get("company", "")),
        salary=str(item.get("salary", "")),
        city=str(item.get("city", "")),
        experience=str(item.get("experience", "")),
        education=str(item.get("education", "")),
        skills=[str(s) for s in skills],
        url=url,
        raw=item,
    )
