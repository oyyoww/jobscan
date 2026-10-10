"""liepin provider：呼叫 liepin-cil（liepin-tech-2026）的 `liepin-cli job search`。

此工具為**求職者端**，job search 原生搜「職位」，正好對應方向 A。
- 執行檔：liepin-cli（Typer/Python，從原始碼安裝）
- 認證：token（liepin-cli setup 或環境變數 LIEPIN_USER_TOKEN），非掃碼
- 搜索：liepin-cli job search --job-name <職位> --address <地點> --page 0 --output json

輸出：--output json 會原樣印出猎聘 /mcp/search-job 的 API JSON 回應。
職位列表的確切欄位與巢狀由伺服器決定，故此處採防禦式解析：
遞迴找出第一個「職位 dict 列表」，再對常見欄位名做容錯映射。
"""

from __future__ import annotations

import json
import shutil

from ..config import Config, SearchSpec
from ..models import Job
from .base import Provider, ProviderResult, run_cli

# jobscan filters -> liepin-cli job search 參數
_FILTER_TO_FLAG = {
    "city": "--address",         # 猎聘以工作地點表示城市
    "salary": "--salary-floor",  # 以最低薪資近似薪資條件
    "experience": "--work-experience",
    "education": "--edu-level",
}

# 常見職位欄位的候選名（容錯映射；涵蓋 /mcp/search-job 實測欄位）
_TITLE_KEYS = ("jobName", "jobTitle", "title", "name")
_COMPANY_KEYS = ("company", "compName", "companyName")
_SALARY_KEYS = ("salary", "salaryDesc", "salaryText")
_CITY_KEYS = ("location", "dqName", "city", "address", "dq", "cityName")
_EXP_KEYS = ("workYears", "workExperience", "requireWorkYears", "experience", "workYear")
_EDU_KEYS = ("education", "eduLevel", "requireEduLevel", "edu")
_URL_KEYS = ("jobDetailUrl", "jobUrl", "url", "link")
_ID_KEYS = ("jobId", "id")
_SKILL_KEYS = ("companyTags", "skills", "jobLabels", "labels")


class LiepinProvider(Provider):
    name = "liepin"

    def is_available(self) -> bool:
        return shutil.which("liepin-cli") is not None

    def _build_args(self, spec: SearchSpec) -> list[str]:
        args = ["liepin-cli", "job", "search", "--job-name", spec.full_query]
        for fkey, flag in _FILTER_TO_FLAG.items():
            value = self.config.filters.get(fkey, "").strip()
            if value:
                args += [flag, value]
        args += ["--page", "0", "--output", "json"]
        return args

    def search(self, spec: SearchSpec) -> ProviderResult:
        result = ProviderResult(provider=self.name, query=spec.full_query)

        if not self.is_available():
            result.error = (
                "找不到 liepin-cli 執行檔，請先安裝 liepin-cil"
                "（uv tool install --from <repo> liepin-cli）"
            )
            return result

        try:
            proc = run_cli(self._build_args(spec))
        except Exception as exc:  # noqa: BLE001
            result.error = f"執行 liepin-cli job search 失敗：{exc}"
            return result

        # 退出碼語意：1=遠端/API 失敗（含 401/403）；2=本地輸入/缺 token
        if proc.returncode == 2:
            tail = (proc.stderr or "").strip().splitlines()
            hint = tail[-1] if tail else "本地輸入或設定錯誤"
            result.error = f"liepin-cli 設定錯誤（可能缺少 token，請執行 liepin-cli setup）：{hint}"
            return result
        if proc.returncode == 1:
            tail = (proc.stderr or proc.stdout or "").strip()[-200:]
            result.error = f"liepin-cli 遠端請求失敗（token 可能失效，請 liepin-cli auth open/setup）：{tail}"
            return result

        payload = _load_json(proc.stdout)
        if payload is None:
            tail = (proc.stderr or proc.stdout or "").strip()[-300:]
            result.error = f"無法解析 liepin-cli JSON 輸出（exit={proc.returncode}）：{tail}"
            return result

        records = _find_job_list(payload)
        for item in records[: self.config.limit]:
            result.jobs.append(_item_to_job(item))
        return result


def _load_json(stdout: str):
    text = (stdout or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        if start == -1:
            start = text.find("[")
        end = max(text.rfind("}"), text.rfind("]"))
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return None
        return None


def _looks_like_job(d: dict) -> bool:
    keys = set(d.keys())
    return any(k in keys for k in _TITLE_KEYS) or any(k in keys for k in _ID_KEYS)


def _find_job_list(payload) -> list:
    """遞迴找出第一個「職位 dict 列表」。找不到則回空列表。"""
    if isinstance(payload, list):
        if payload and all(isinstance(x, dict) for x in payload) and any(_looks_like_job(x) for x in payload):
            return payload
        for item in payload:
            found = _find_job_list(item)
            if found:
                return found
        return []
    if isinstance(payload, dict):
        # 優先常見容器鍵
        for key in ("jobs", "jobList", "jobCardList", "list", "data", "records", "result", "results"):
            if key in payload:
                found = _find_job_list(payload[key])
                if found:
                    return found
        for value in payload.values():
            found = _find_job_list(value)
            if found:
                return found
    return []


def _first(item: dict, keys) -> str:
    for k in keys:
        if item.get(k):
            return str(item[k])
    return ""


def _item_to_job(item: dict) -> Job:
    skills = []
    for k in _SKILL_KEYS:
        if item.get(k):
            skills = item[k]
            break
    if not isinstance(skills, list):
        skills = [str(skills)]
    url = _first(item, _URL_KEYS)
    if not url:
        job_id = _first(item, _ID_KEYS)
        if job_id:
            url = f"https://www.liepin.com/job/{job_id}.shtml"
    return Job(
        source="liepin",
        title=_first(item, _TITLE_KEYS),
        company=_first(item, _COMPANY_KEYS),
        salary=_first(item, _SALARY_KEYS),
        city=_first(item, _CITY_KEYS),
        experience=_first(item, _EXP_KEYS),
        education=_first(item, _EDU_KEYS),
        skills=[str(s) for s in skills],
        url=url,
        raw=item,
    )
