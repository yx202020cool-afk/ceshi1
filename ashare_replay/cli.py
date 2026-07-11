from __future__ import annotations

import argparse
import json
import shutil
from datetime import date, timedelta
from typing import Any

from ashare_replay.config import PROJECT_ROOT, load_settings
from ashare_replay.constants import REPORT_TYPES
from ashare_replay.db import Database
from ashare_replay.logging_config import setup_logging
from ashare_replay.services.backtest import run_demo_backtest, write_demo_historical_fixture
from ashare_replay.services.health import health_status, provider_audit
from ashare_replay.services.ops import docker_environment_check, format_ops_check_text
from ashare_replay.services.report import ReportGenerator
from ashare_replay.services.scheduler import (
    is_trading_day,
    run_manual_backfill,
    run_scheduler_forever,
)
from ashare_replay.time_utils import parse_trade_date


def _latest_trading_day(today: date) -> date:
    cursor = today
    while not is_trading_day(cursor):
        cursor -= timedelta(days=1)
    return cursor


def _parse_cli_date(value: str | None) -> date:
    settings = load_settings()
    parsed = parse_trade_date(value or "today", settings.timezone)
    if (value is None or value == "today") and not is_trading_day(parsed):
        return _latest_trading_day(parsed)
    return parsed


def cmd_init_db(_args: argparse.Namespace) -> None:
    settings = load_settings()
    setup_logging(settings.log_level)
    db = Database(settings.database_url, settings.timezone)
    db.init_db()
    db.upsert_config(settings.config_hash, settings.config)
    print("数据库初始化完成。")


def cmd_health(_args: argparse.Namespace) -> None:
    settings = load_settings()
    setup_logging(settings.log_level)
    print(json.dumps(health_status(settings), ensure_ascii=False, indent=2))


def cmd_provider_audit(args: argparse.Namespace) -> None:
    settings = load_settings()
    setup_logging(settings.log_level)
    result = provider_audit(settings, run_probes=not args.no_probe)
    if args.save:
        out_path = PROJECT_ROOT / "work" / "data" / "provider_audit.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_generate(args: argparse.Namespace) -> None:
    settings = load_settings()
    setup_logging(settings.log_level)
    trade_date = _parse_cli_date(args.date)
    result = run_manual_backfill(settings, trade_date, args.report_type)
    print(json.dumps(result["files"], ensure_ascii=False, indent=2))


def cmd_generate_all(args: argparse.Namespace) -> None:
    settings = load_settings()
    setup_logging(settings.log_level)
    trade_date = _parse_cli_date(args.date)
    generator = ReportGenerator(settings)
    all_files: dict[str, Any] = {}
    for report_type in REPORT_TYPES:
        result = generator.generate(trade_date, report_type)
        all_files[report_type] = result["files"]
    print(json.dumps(all_files, ensure_ascii=False, indent=2))


def cmd_scheduler(args: argparse.Namespace) -> None:
    settings = load_settings()
    setup_logging(settings.log_level)
    if args.once:
        trade_date = _parse_cli_date(args.date)
        for report_type in REPORT_TYPES:
            run_manual_backfill(settings, trade_date, report_type)
        print("单次任务执行完成。")
        return
    run_scheduler_forever(settings, poll_seconds=args.poll_seconds)


def cmd_backtest(args: argparse.Namespace) -> None:
    settings = load_settings()
    setup_logging(settings.log_level)
    start = parse_trade_date(args.start, settings.timezone)
    end = parse_trade_date(args.end, settings.timezone)
    result = run_demo_backtest(settings, start, end)
    out_dir = settings.report_output_dir / "backtest"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"backtest_{start.isoformat()}_{end.isoformat()}.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"summary": result["summary"], "file": str(out_path.relative_to(PROJECT_ROOT))}, ensure_ascii=False, indent=2))


def cmd_build_fixture(args: argparse.Namespace) -> None:
    settings = load_settings()
    setup_logging(settings.log_level)
    start = parse_trade_date(args.start, settings.timezone)
    end = parse_trade_date(args.end, settings.timezone)
    result = write_demo_historical_fixture(settings, start, end, args.output)
    print(
        json.dumps(
            {
                "summary": result["fixture"]["summary"],
                "file": result["file"],
                "trading_days": result["fixture"]["trading_days"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_clean_cache(_args: argparse.Namespace) -> None:
    cache = PROJECT_ROOT / "work" / "cache"
    if cache.exists():
        shutil.rmtree(cache)
    cache.mkdir(parents=True, exist_ok=True)
    print("缓存已清理。")


def cmd_latest(_args: argparse.Namespace) -> None:
    settings = load_settings()
    db = Database(settings.database_url, settings.timezone)
    db.init_db()
    rows = db.latest_reports(10)
    slim = [
        {
            "trade_date": row["trade_date"],
            "report_type": row["report_type"],
            "report_version": row["report_version"],
            "generated_at": row["generated_at"],
            "provider": row["provider"],
            "data_status": row["data_status"],
        }
        for row in rows
    ]
    print(json.dumps(slim, ensure_ascii=False, indent=2))


def cmd_ops_check(args: argparse.Namespace) -> None:
    result = docker_environment_check(run_compose_config=not args.no_compose_config)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_ops_check_text(result))
    if args.strict and not result["can_run_compose"]:
        raise SystemExit(2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="A 股每日全局复盘与板块资金分析系统")
    sub = parser.add_subparsers(required=True)

    init_db = sub.add_parser("init-db", help="初始化数据库")
    init_db.set_defaults(func=cmd_init_db)

    health = sub.add_parser("health", help="检查系统和 Provider 状态")
    health.set_defaults(func=cmd_health)

    provider_check = sub.add_parser("provider-audit", help="检查真实数据 Provider 权限清单")
    provider_check.add_argument("--no-probe", action="store_true", help="只检查配置，不调用外部接口")
    provider_check.add_argument("--save", action="store_true", help="保存结果到 work/data/provider_audit.json")
    provider_check.set_defaults(func=cmd_provider_audit)

    generate = sub.add_parser("generate", help="生成指定日期和版本的报告")
    generate.add_argument("--date", default="today", help="日期，例如 2026-07-10；today 在非交易日会自动取最近交易日")
    generate.add_argument("--report-type", choices=list(REPORT_TYPES), default="POST_CLOSE_FINAL")
    generate.set_defaults(func=cmd_generate)

    generate_all = sub.add_parser("generate-all", help="生成三种报告版本")
    generate_all.add_argument("--date", default="today")
    generate_all.set_defaults(func=cmd_generate_all)

    scheduler = sub.add_parser("scheduler", help="启动定时任务")
    scheduler.add_argument("--once", action="store_true", help="只执行一次三种报告")
    scheduler.add_argument("--date", default="today")
    scheduler.add_argument("--poll-seconds", type=int, default=60)
    scheduler.set_defaults(func=cmd_scheduler)

    backtest = sub.add_parser("backtest", help="运行演示历史验证")
    backtest.add_argument("--start", required=True)
    backtest.add_argument("--end", required=True)
    backtest.set_defaults(func=cmd_backtest)

    fixture = sub.add_parser("build-fixture", help="生成演示长周期历史 Fixture")
    fixture.add_argument("--start", default="2026-04-01")
    fixture.add_argument("--end", default="2026-07-10")
    fixture.add_argument("--output", default="fixtures/demo/long_history_fixture.json")
    fixture.set_defaults(func=cmd_build_fixture)

    clean = sub.add_parser("clean-cache", help="清理缓存")
    clean.set_defaults(func=cmd_clean_cache)

    latest = sub.add_parser("latest", help="列出最近报告")
    latest.set_defaults(func=cmd_latest)

    ops = sub.add_parser("ops-check", help="检查 Docker Desktop 和 Compose 启动条件")
    ops.add_argument("--json", action="store_true", help="输出 JSON")
    ops.add_argument("--strict", action="store_true", help="不可启动时返回非零退出码")
    ops.add_argument("--no-compose-config", action="store_true", help="跳过 docker compose config 检查")
    ops.set_defaults(func=cmd_ops_check)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
