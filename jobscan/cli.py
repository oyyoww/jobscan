"""jobscan 命令列入口。

子命令：
  run      依設定搜索並產出 HTML 報告（主要功能）
  login    提示如何登入 boss / liepin（實際掃碼需使用者在有瀏覽器的環境操作）
  check    檢查 boss / liepin CLI 是否可用

搜索關鍵字的定義方式有兩種，可混用：
  1) 設定檔 config.yaml（searches / filters / providers）
  2) 命令列參數覆蓋：--query --city --salary --experience --education --job-type
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from .config import load_config
from .providers import REGISTRY
from .report import render_report


def _cmd_run(args: argparse.Namespace) -> int:
    overrides: dict = {}
    if args.query:
        overrides["query"] = args.query
        overrides["skills"] = args.skill or []
    for key in ("city", "salary", "experience", "education", "job_type"):
        val = getattr(args, key)
        if val:
            overrides[key] = val
    if args.limit is not None:
        overrides["limit"] = args.limit
    if args.provider:
        # 僅啟用指定平台
        overrides["providers"] = {
            name: {"enabled": name in args.provider} for name in REGISTRY
        }

    config = load_config(args.config, overrides)

    if not config.searches:
        print("沒有可執行的搜索。請在 config.yaml 設定 searches，或用 --query 指定。", file=sys.stderr)
        return 2

    enabled = config.enabled_providers()
    if not enabled:
        print("沒有啟用任何平台。請在 config.yaml 的 providers 開啟，或用 --provider 指定。", file=sys.stderr)
        return 2

    results = []
    for name in enabled:
        provider_cls = REGISTRY.get(name)
        if provider_cls is None:
            continue
        provider = provider_cls(config)
        for spec in config.searches:
            print(f"[{name}] 搜索：{spec.full_query} ...", file=sys.stderr)
            results.append(provider.search(spec))

    html_text = render_report(results, title=args.title)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_text, encoding="utf-8")
    print(f"報告已產生：{out_path}")

    if args.json_out:
        payload = [
            {"provider": r.provider, "query": r.query, "error": r.error,
             "jobs": [j.to_dict() for j in r.jobs]}
            for r in results
        ]
        Path(args.json_out).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"JSON 已產生：{args.json_out}")

    total = sum(len(r.jobs) for r in results)
    errs = [r for r in results if r.error]
    print(f"共 {total} 筆結果；{len(errs)} 組有錯誤。", file=sys.stderr)
    for r in errs:
        print(f"  - [{r.provider}] {r.query}：{r.error}", file=sys.stderr)
    return 0


def _cmd_login(args: argparse.Namespace) -> int:
    print(
        "認證說明：\n"
        "  BOSS 直聘： boss login          # 掃碼登入，登入態存於 ~/.boss-agent\n"
        "  獵聘：      liepin-cli setup    # token 認證（需可貼上 token 的互動式終端），\n"
        "                                  # 或設環境變數 LIEPIN_USER_TOKEN\n\n"
        "完成後再執行： jobscan run\n"
    )
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    ok = True
    for exe, pkg in (("boss", "boss-agent-cli"), ("liepin-cli", "liepin-cil (liepin-tech-2026)")):
        path = shutil.which(exe)
        if path:
            ver = ""
            try:
                out = subprocess.run(
                    [exe, "--version"], capture_output=True, text=True, timeout=20
                )
                lines = (out.stdout or "").strip().splitlines()
                ver = lines[0] if lines else ""
            except Exception:  # noqa: BLE001
                pass
            print(f"✓ {exe}: {path}  {ver}".rstrip())
        else:
            ok = False
            print(f"✗ {exe}: 未安裝（需 {pkg}）")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="jobscan",
        description="定義搜索關鍵字，呼叫 boss/liepin 搜索職位，整理為 HTML 表格報告。",
    )
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("run", help="搜索並產出 HTML 報告")
    r.add_argument("-c", "--config", default="config.yaml", help="設定檔路徑（預設 config.yaml）")
    r.add_argument("-o", "--output", default="reports/report.html", help="HTML 輸出路徑")
    r.add_argument("--json-out", default="", help="（選填）同時輸出原始結果 JSON 的路徑")
    r.add_argument("--title", default="jobscan 職位搜索報告", help="報告標題")
    # 關鍵字覆蓋
    r.add_argument("-q", "--query", default="", help="職位關鍵字（覆蓋設定檔的 searches）")
    r.add_argument("--skill", action="append", help="技能關鍵字，可重複（搭配 --query）")
    r.add_argument("--city", default="", help="城市")
    r.add_argument("--salary", default="", help="薪資範圍，如 20-40K")
    r.add_argument("--experience", default="", help="經驗，如 3-5年")
    r.add_argument("--education", default="", help="學歷，如 本科")
    r.add_argument("--job-type", dest="job_type", default="", help="職位類型：全职/兼职/实习")
    r.add_argument("--limit", type=int, default=None, help="每組搜索最多筆數")
    r.add_argument(
        "--provider", action="append", choices=list(REGISTRY),
        help="只啟用指定平台，可重複（預設依設定檔）",
    )
    r.set_defaults(func=_cmd_run)

    lo = sub.add_parser("login", help="顯示登入說明")
    lo.set_defaults(func=_cmd_login)

    ck = sub.add_parser("check", help="檢查 boss / liepin CLI 是否可用")
    ck.set_defaults(func=_cmd_check)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
