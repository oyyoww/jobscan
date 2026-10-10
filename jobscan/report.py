"""把搜索結果整理為 HTML 表格報告。"""

from __future__ import annotations

import html
from datetime import datetime
from typing import Iterable

from .models import Job
from .providers import ProviderResult

_SOURCE_LABEL = {
    "boss": "BOSS 直聘（職位）",
    "liepin": "獵聘（職位）",
}

_CSS = """
:root { --bg:#f6f7f9; --card:#fff; --line:#e5e7eb; --head:#111827; --sub:#6b7280;
        --boss:#00bebd; --liepin:#f5634a; --accent:#2563eb; }
* { box-sizing:border-box; }
body { margin:0; padding:32px; background:var(--bg);
       font-family:-apple-system,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif;
       color:var(--head); }
h1 { font-size:22px; margin:0 0 4px; }
.meta { color:var(--sub); font-size:13px; margin-bottom:20px; }
.summary { display:flex; gap:12px; flex-wrap:wrap; margin-bottom:24px; }
.chip { background:var(--card); border:1px solid var(--line); border-radius:10px;
        padding:10px 14px; font-size:13px; }
.chip b { font-size:18px; display:block; }
.group { background:var(--card); border:1px solid var(--line); border-radius:12px;
         margin-bottom:24px; overflow:hidden; }
.group > header { padding:14px 18px; border-bottom:1px solid var(--line);
                  display:flex; align-items:center; gap:10px; }
.badge { font-size:12px; font-weight:600; color:#fff; border-radius:6px; padding:2px 8px; }
.badge.boss { background:var(--boss); }
.badge.liepin { background:var(--liepin); }
.group h2 { font-size:15px; margin:0; }
.group .q { color:var(--sub); font-size:13px; font-weight:400; }
table { width:100%; border-collapse:collapse; font-size:13px; }
th, td { text-align:left; padding:10px 14px; border-bottom:1px solid var(--line);
         vertical-align:top; }
th { background:#fafafa; color:var(--sub); font-weight:600; white-space:nowrap; }
tr:last-child td { border-bottom:none; }
tr:hover td { background:#f9fafb; }
.title a { color:var(--accent); text-decoration:none; font-weight:600; }
.title a:hover { text-decoration:underline; }
.title span { font-weight:600; }
.salary { color:#b45309; font-weight:600; white-space:nowrap; }
.skills { display:flex; flex-wrap:wrap; gap:4px; }
.tag { background:#eef2ff; color:#3730a3; border-radius:5px; padding:1px 7px; font-size:12px; }
.err { color:var(--liepin); font-size:13px; padding:12px 18px; }
.empty { color:var(--sub); padding:16px 18px; font-size:13px; }
footer { color:var(--sub); font-size:12px; margin-top:24px; }
"""


def _esc(text: str) -> str:
    return html.escape(str(text or ""), quote=True)


def _skills_html(skills: list[str]) -> str:
    if not skills:
        return '<span style="color:#9ca3af">—</span>'
    return '<div class="skills">' + "".join(
        f'<span class="tag">{_esc(s)}</span>' for s in skills
    ) + "</div>"


def _title_html(job: Job) -> str:
    if job.url:
        return f'<span class="title"><a href="{_esc(job.url)}" target="_blank" rel="noopener">{_esc(job.title)}</a></span>'
    return f'<span class="title"><span>{_esc(job.title)}</span></span>'


def _rows_html(jobs: list[Job]) -> str:
    rows = []
    for job in jobs:
        rows.append(
            "<tr>"
            f"<td>{_title_html(job)}</td>"
            f"<td>{_esc(job.company)}</td>"
            f'<td class="salary">{_esc(job.salary) or "—"}</td>'
            f'<td>{_esc(job.city) or "—"}</td>'
            f'<td>{_esc(job.experience) or "—"}</td>'
            f'<td>{_esc(job.education) or "—"}</td>'
            f"<td>{_skills_html(job.skills)}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _group_html(res: ProviderResult) -> str:
    label = _SOURCE_LABEL.get(res.provider, res.provider)
    header = (
        '<header>'
        f'<span class="badge {_esc(res.provider)}">{_esc(res.provider.upper())}</span>'
        f'<h2>{_esc(label)} <span class="q">· 關鍵字：{_esc(res.query)}（{len(res.jobs)} 筆）</span></h2>'
        '</header>'
    )

    if res.error:
        body = f'<div class="err">⚠ {_esc(res.error)}</div>'
    elif not res.jobs:
        body = '<div class="empty">此條件下沒有結果。</div>'
    else:
        body = (
            "<table><thead><tr>"
            "<th>職位</th><th>公司</th><th>薪資</th><th>城市</th>"
            "<th>經驗</th><th>學歷</th><th>技能</th>"
            "</tr></thead><tbody>"
            + _rows_html(res.jobs)
            + "</tbody></table>"
        )
    return f'<section class="group">{header}{body}</section>'


def render_report(results: Iterable[ProviderResult], *, title: str = "jobscan 職位搜索報告") -> str:
    """產生完整 HTML 字串。"""
    results = list(results)
    total_jobs = sum(len(r.jobs) for r in results)
    errors = sum(1 for r in results if r.error)
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    summary = (
        '<div class="summary">'
        f'<div class="chip">結果數<b>{total_jobs}</b></div>'
        f'<div class="chip">搜索組數<b>{len(results)}</b></div>'
        f'<div class="chip">錯誤<b>{errors}</b></div>'
        "</div>"
    )

    groups = "\n".join(_group_html(r) for r in results) or '<div class="empty">沒有任何搜索結果。</div>'

    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)}</title>
<style>{_CSS}</style>
</head>
<body>
<h1>{_esc(title)}</h1>
<div class="meta">產生時間：{generated}</div>
{summary}
{groups}
<footer>由 jobscan 產生 · 資料來源：boss-agent-cli / liepin-cli。請遵守各平台使用條款。</footer>
</body>
</html>
"""
