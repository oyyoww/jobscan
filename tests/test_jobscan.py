"""jobscan 單元測試：設定載入、boss 解析、報告產生、provider 以 fake CLI 跑通。"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from jobscan.config import load_config, SearchSpec
from jobscan.models import Job
from jobscan.providers import ProviderResult
from jobscan.providers.boss import BossProvider, _item_to_job, _parse_envelope
from jobscan.report import render_report

ROOT = Path(__file__).resolve().parents[1]


# ---------- config ----------

def test_load_config_overrides_query():
    cfg = load_config(None, {"query": "后端", "skills": ["Go"], "city": "深圳"})
    assert len(cfg.searches) == 1
    assert cfg.searches[0].full_query == "后端 Go"
    assert cfg.filters["city"] == "深圳"
    assert set(cfg.enabled_providers()) == {"boss", "liepin"}  # 兩者預設皆啟用


def test_load_config_from_yaml(tmp_path):
    yaml_text = (
        "searches:\n"
        "  - query: 前端\n"
        "    skills: [React]\n"
        "filters:\n"
        "  city: 上海\n"
        "limit: 5\n"
        "providers:\n"
        "  boss: {enabled: true}\n"
        "  liepin: {enabled: true}\n"
    )
    p = tmp_path / "c.yaml"
    p.write_text(yaml_text, encoding="utf-8")
    cfg = load_config(p)
    assert cfg.searches[0].full_query == "前端 React"
    assert cfg.filters["city"] == "上海"
    assert cfg.limit == 5
    assert set(cfg.enabled_providers()) == {"boss", "liepin"}


def test_search_spec_full_query_strips_blanks():
    assert SearchSpec("后端", ["", "Go", " "]).full_query == "后端 Go"


# ---------- boss envelope parsing ----------

def test_parse_envelope_valid():
    sample = json.loads((ROOT / "examples" / "boss_search_sample.json").read_text("utf-8"))
    env = _parse_envelope(json.dumps(sample))
    assert env is not None and env["ok"] is True
    assert len(env["data"]) == 2


def test_item_to_job_maps_fields_and_url():
    item = {
        "title": "后端", "company": "甲", "salary": "20-40K", "city": "深圳",
        "experience": "3-5年", "education": "本科", "skills": ["Go"],
        "security_id": "SID9",
    }
    job = _item_to_job(item)
    assert job.source == "boss"
    assert job.title == "后端"
    assert job.skills == ["Go"]
    assert "SID9" in job.url


# ---------- boss provider with fake CLI ----------

def _make_fake_boss(tmp_path: Path, payload: dict) -> Path:
    """產生一個假的 `boss` 執行檔，忽略參數並印出固定 JSON 信封。

    payload 寫到旁邊的 JSON 檔，由腳本讀出後原樣輸出，避免把 JSON
    字面值（true/false/null）直接內嵌成 Python 原始碼而出錯。
    """
    payload_file = tmp_path / "payload.json"
    payload_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    script = tmp_path / "boss"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        f"sys.stdout.write(open({str(payload_file)!r}, encoding='utf-8').read())\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def test_boss_provider_parses_fake_cli(tmp_path, monkeypatch):
    sample = json.loads((ROOT / "examples" / "boss_search_sample.json").read_text("utf-8"))
    _make_fake_boss(tmp_path, sample)
    monkeypatch.setenv("PATH", str(tmp_path) + ":" + __import__("os").environ["PATH"])

    cfg = load_config(None, {"query": "后端", "city": "深圳", "limit": 20})
    provider = BossProvider(cfg)
    assert provider.is_available()
    res = provider.search(cfg.searches[0])
    assert res.error == ""
    assert len(res.jobs) == 2
    assert res.jobs[0].title == "高级后端工程师(Go)"
    assert res.jobs[0].city == "深圳"


def test_boss_provider_handles_auth_error(tmp_path, monkeypatch):
    payload = {"ok": False, "data": None,
               "error": {"code": "AUTH_REQUIRED", "recovery_action": "boss login"}}
    _make_fake_boss(tmp_path, payload)
    monkeypatch.setenv("PATH", str(tmp_path) + ":" + __import__("os").environ["PATH"])
    cfg = load_config(None, {"query": "后端"})
    res = BossProvider(cfg).search(cfg.searches[0])
    assert "AUTH_REQUIRED" in res.error
    assert res.jobs == []


# ---------- liepin provider ----------

from jobscan.providers.liepin import LiepinProvider, _find_job_list, _item_to_job as _lp_item_to_job


def test_liepin_find_job_list_nested():
    payload = {"data": {"jobCardList": [
        {"jobId": 1, "jobName": "后端", "compName": "甲", "salary": "20-40k",
         "dqName": "深圳", "workExperience": "3-5年", "eduLevel": "本科"},
    ]}}
    jobs = _find_job_list(payload)
    assert len(jobs) == 1 and jobs[0]["jobName"] == "后端"


def test_liepin_find_job_list_top_level_jobs_key():
    assert _find_job_list({"jobs": []}) == []  # 空列表 -> 無職位
    found = _find_job_list({"jobs": [{"jobName": "x"}]})
    assert found and found[0]["jobName"] == "x"


def test_liepin_item_to_job_field_fallbacks_and_url():
    item = {"jobId": 777, "jobTitle": "数据工程师", "companyName": "乙公司",
            "salaryText": "25-45k", "city": "上海", "requireWorkYears": "5年",
            "requireEduLevel": "硕士", "jobLabels": ["Spark", "ETL"]}
    job = _lp_item_to_job(item)
    assert job.source == "liepin"
    assert job.title == "数据工程师"
    assert job.company == "乙公司"
    assert job.salary == "25-45k"
    assert job.skills == ["Spark", "ETL"]
    assert "777" in job.url


def _make_fake_liepin(tmp_path: Path, payload) -> Path:
    payload_file = tmp_path / "lp_payload.json"
    payload_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    script = tmp_path / "liepin-cli"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        f"sys.stdout.write(open({str(payload_file)!r}, encoding='utf-8').read())\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def test_liepin_provider_parses_fake_cli(tmp_path, monkeypatch):
    payload = {"data": {"jobs": [
        {"jobId": 1, "jobName": "后端工程师", "compName": "示例", "salary": "20-40k",
         "dqName": "深圳", "workExperience": "3-5年", "eduLevel": "本科"},
        {"jobId": 2, "jobName": "后端开发", "compName": "示例二", "salary": "25-45k",
         "dqName": "深圳", "workExperience": "不限", "eduLevel": "本科"},
    ]}}
    _make_fake_liepin(tmp_path, payload)
    monkeypatch.setenv("PATH", str(tmp_path) + ":" + __import__("os").environ["PATH"])
    cfg = load_config(None, {"query": "后端", "city": "深圳", "limit": 20})
    provider = LiepinProvider(cfg)
    assert provider.is_available()
    res = provider.search(cfg.searches[0])
    assert res.error == ""
    assert len(res.jobs) == 2
    assert res.jobs[0].title == "后端工程师"
    assert res.jobs[0].source == "liepin"


# ---------- report ----------

def test_render_report_contains_jobs_and_escapes():
    results = [
        ProviderResult(provider="boss", query="后端 <x>", jobs=[
            Job(source="boss", title="后端<b>", company="甲&乙", salary="20K",
                city="深圳", experience="3年", education="本科", skills=["Go"]),
        ]),
        ProviderResult(provider="boss", query="前端", error="AUTH_REQUIRED"),
    ]
    html_text = render_report(results)
    assert "<!DOCTYPE html>" in html_text
    assert "后端&lt;b&gt;" in html_text        # 標題被 HTML escape
    assert "甲&amp;乙" in html_text
    assert "AUTH_REQUIRED" in html_text         # 錯誤區塊呈現
    assert "結果數" in html_text
