"""以樣本資料產生 HTML 報告，用來預覽報告長相（免登入、免連線）。

執行：python examples/demo_report.py
輸出：reports/sample_report.html
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jobscan.models import Job
from jobscan.providers import ProviderResult
from jobscan.report import render_report


def build_sample_results() -> list[ProviderResult]:
    boss = ProviderResult(
        provider="boss",
        query="后端工程师 Go Kubernetes",
        jobs=[
            Job(
                source="boss", title="高级后端工程师(Go)", company="示例科技",
                salary="30-50K·14薪", city="深圳", experience="3-5年", education="本科",
                skills=["Go", "Kubernetes", "MySQL", "gRPC"],
                url="https://www.zhipin.com/job_detail/?securityId=SAMPLE1",
            ),
            Job(
                source="boss", title="后端开发工程师", company="示例网络",
                salary="25-40K", city="深圳", experience="3-5年", education="本科",
                skills=["Go", "Redis", "微服务"],
                url="https://www.zhipin.com/job_detail/?securityId=SAMPLE2",
            ),
        ],
    )
    boss_err = ProviderResult(
        provider="boss",
        query="前端工程师 React TypeScript",
        error="boss 回報錯誤 [AUTH_REQUIRED] boss login",
    )
    liepin = ProviderResult(
        provider="liepin",
        query="后端工程师",
        jobs=[
            Job(
                source="liepin", title="资深后端工程师", company="獵聘示例公司",
                salary="30-45K", city="深圳", experience="5-10年", education="本科",
                skills=["Go", "分布式", "微服务"],
                url="https://www.liepin.com/job/123456.shtml",
            ),
        ],
    )
    return [boss, boss_err, liepin]


def main() -> int:
    results = build_sample_results()
    html_text = render_report(results, title="jobscan 樣本報告（示範資料）")
    out = Path(__file__).resolve().parents[1] / "reports" / "sample_report.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_text, encoding="utf-8")
    print(f"樣本報告已產生：{out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
