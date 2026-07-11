from __future__ import annotations

import html as html_lib
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from ashare_replay.config import PROJECT_ROOT, load_settings  # noqa: E402
from ashare_replay.constants import REPORT_TYPES  # noqa: E402
from ashare_replay.services.report import ReportGenerator  # noqa: E402
from ashare_replay.time_utils import parse_trade_date  # noqa: E402

NAV_ITEMS = [
    "今日总览",
    "行业板块",
    "概念板块",
    "板块详情",
    "周线持续流入",
    "候选观察池",
    "历史报告",
    "数据健康",
    "系统设置",
]

COLUMN_LABELS = {
    "sector_name": "板块",
    "taxonomy": "类型",
    "change_pct": "涨跌幅",
    "amount": "成交额(亿)",
    "main_net_inflow": "主力资金流(亿)",
    "net_inflow_ratio": "资金/成交额",
    "up_count": "上涨",
    "down_count": "下跌",
    "flat_count": "平盘",
    "limit_up_count": "涨停",
    "limit_down_count": "跌停",
    "break_limit_count": "炸板",
    "lifecycle_stage": "生命周期",
    "stock_code": "代码",
    "stock_name": "名称",
    "rank_in_sector": "板块排名",
    "leader_type": "龙头类型",
    "money_flow": "资金流",
    "total_score": "评分",
    "candidate_type": "类型",
    "main_sector": "重点板块",
    "main_sector_code": "板块代码",
    "category": "类别",
    "flow_3d": "3日资金",
    "flow_5d": "5日资金",
    "flow_10d": "10日资金",
    "flow_20d": "20日资金",
    "score": "综合分",
    "reason": "理由",
    "invalidation": "失效条件",
    "data_as_of": "数据截止",
}


def esc(value: Any) -> str:
    return html_lib.escape("" if value is None else str(value))


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def fmt_pct(value: Any) -> str:
    if value is None:
        return "不支持"
    return f"{safe_float(value):+.2f}%"


def fmt_money(value: Any) -> str:
    if value is None:
        return "不支持"
    return f"{safe_float(value):,.2f} 亿"


def fmt_ratio(value: Any) -> str:
    if value is None:
        return "不支持"
    return f"{safe_float(value) * 100:.2f}%"


def tone_class(value: Any) -> str:
    number = safe_float(value)
    if number > 0:
        return "positive"
    if number < 0:
        return "negative"
    return "neutral"


def load_latest_report() -> dict[str, Any] | None:
    root = PROJECT_ROOT / "outputs" / "reports"
    files = sorted(
        root.glob("*/POST_CLOSE_FINAL/report.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not files:
        return None
    return json.loads(files[0].read_text(encoding="utf-8"))


def apply_style() -> None:
    st.markdown(
        """
        <style>
        :root {
          --bg: #f5f5f7;
          --panel: rgba(255,255,255,.88);
          --panel-solid: #ffffff;
          --text: #1d1d1f;
          --muted: #6e6e73;
          --line: rgba(0,0,0,.10);
          --accent: #0071e3;
          --accent-soft: #e8f2ff;
          --good: #0a7f42;
          --bad: #b42318;
          --warn: #a15c00;
        }
        html, body, [class*="css"] {
          font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI",
            "Microsoft YaHei", Arial, sans-serif;
        }
        .stApp {
          color: var(--text);
          background:
            linear-gradient(180deg, #ffffff 0%, #f5f5f7 46%, #ffffff 100%);
        }
        header[data-testid="stHeader"], div[data-testid="stToolbar"], footer {
          display: none;
        }
        .block-container {
          max-width: 1240px;
          padding: 1.1rem 2.2rem 3.4rem;
        }
        section[data-testid="stSidebar"] {
          background: rgba(255,255,255,.78);
          border-right: 1px solid var(--line);
          backdrop-filter: blur(18px);
        }
        section[data-testid="stSidebar"] > div {
          padding-top: 1.2rem;
        }
        h1, h2, h3, p {
          letter-spacing: 0;
        }
        h1 {
          font-size: clamp(2.2rem, 5vw, 4.8rem);
          line-height: 1.02;
          font-weight: 760;
          margin-bottom: .75rem;
        }
        h2 {
          font-size: 1.55rem;
          font-weight: 720;
        }
        h3 {
          font-size: 1.05rem;
          font-weight: 680;
        }
        div[data-testid="stMetric"] {
          background: var(--panel-solid);
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 16px 18px;
          box-shadow: 0 18px 50px rgba(0,0,0,.055);
        }
        div[data-testid="stMetric"] label {
          color: var(--muted);
        }
        .brand-lockup {
          padding: 0 0 18px;
        }
        .brand-title {
          font-size: 1.08rem;
          font-weight: 750;
          color: var(--text);
        }
        .brand-subtitle {
          color: var(--muted);
          font-size: .82rem;
          margin-top: 4px;
        }
        .hero {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: linear-gradient(135deg, rgba(255,255,255,.98), rgba(245,245,247,.92) 56%, rgba(232,242,255,.86));
          padding: clamp(26px, 5vw, 58px);
          box-shadow: 0 28px 80px rgba(0,0,0,.075);
          overflow: hidden;
        }
        .hero-summary {
          color: var(--muted);
          font-size: clamp(1rem, 1.7vw, 1.22rem);
          line-height: 1.74;
          max-width: 980px;
        }
        .hero-row, .card-grid, .mini-grid {
          display: grid;
          gap: 14px;
        }
        .hero-row {
          grid-template-columns: repeat(4, minmax(0, 1fr));
          margin-top: 24px;
        }
        .card-grid {
          grid-template-columns: repeat(3, minmax(0, 1fr));
        }
        .mini-grid {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .metric-card, .soft-card, .sector-card, .insight-card {
          background: var(--panel);
          border: 1px solid var(--line);
          border-radius: 8px;
          box-shadow: 0 18px 54px rgba(0,0,0,.055);
        }
        .metric-card {
          padding: 18px;
          min-height: 112px;
        }
        .metric-label, .eyebrow, .muted {
          color: var(--muted);
        }
        .metric-label {
          font-size: .82rem;
          font-weight: 650;
        }
        .metric-value {
          font-size: clamp(1.45rem, 2.3vw, 2.25rem);
          line-height: 1.05;
          font-weight: 780;
          margin-top: 12px;
        }
        .metric-foot {
          color: var(--muted);
          margin-top: 9px;
          font-size: .82rem;
        }
        .soft-card {
          padding: 22px;
        }
        .sector-card {
          padding: 18px;
          min-height: 188px;
        }
        .sector-head {
          display: flex;
          align-items: start;
          justify-content: space-between;
          gap: 12px;
        }
        .sector-name {
          font-size: 1.22rem;
          font-weight: 740;
          line-height: 1.22;
        }
        .sector-sub {
          color: var(--muted);
          font-size: .82rem;
          margin-top: 4px;
        }
        .sector-change {
          font-size: 1.35rem;
          font-weight: 780;
          white-space: nowrap;
        }
        .positive { color: var(--good); }
        .negative { color: var(--bad); }
        .neutral { color: var(--muted); }
        .chip-row {
          display: flex;
          flex-wrap: wrap;
          gap: 7px;
          margin-top: 14px;
        }
        .chip, .status-pill {
          display: inline-flex;
          align-items: center;
          min-height: 26px;
          padding: 4px 10px;
          border-radius: 999px;
          border: 1px solid var(--line);
          background: rgba(255,255,255,.72);
          color: var(--muted);
          font-size: .78rem;
          font-weight: 620;
        }
        .status-pill.blue {
          color: #0059b8;
          background: var(--accent-soft);
          border-color: rgba(0,113,227,.22);
        }
        .status-pill.warn {
          color: var(--warn);
          background: #fff7e8;
          border-color: rgba(161,92,0,.22);
        }
        .section-head {
          margin: 34px 0 14px;
          display: flex;
          justify-content: space-between;
          align-items: end;
          gap: 16px;
        }
        .section-title {
          font-size: 1.7rem;
          font-weight: 760;
          line-height: 1.1;
        }
        .section-note {
          color: var(--muted);
          font-size: .92rem;
          margin-top: 6px;
        }
        .insight-card {
          padding: 18px;
        }
        .risk-item {
          border: 1px solid rgba(180,35,24,.14);
          background: #fff7f6;
          color: #7a271a;
          border-radius: 8px;
          padding: 12px 14px;
          margin-bottom: 9px;
          line-height: 1.55;
        }
        div[data-testid="stDataFrame"] {
          border: 1px solid var(--line);
          border-radius: 8px;
          overflow: hidden;
          box-shadow: 0 14px 42px rgba(0,0,0,.045);
        }
        .stButton > button, .stDownloadButton > button {
          border-radius: 999px;
          border: 1px solid rgba(0,113,227,.25);
          background: #0071e3;
          color: #fff;
          font-weight: 680;
          min-height: 42px;
          padding: 0 18px;
        }
        .stButton > button:hover, .stDownloadButton > button:hover {
          border-color: #0064c8;
          background: #006edb;
          color: #fff;
        }
        div[role="radiogroup"] label {
          border-radius: 8px;
          padding: 6px 8px;
        }
        .empty-state {
          max-width: 760px;
          margin: 8vh auto 0;
          text-align: center;
        }
        @media (max-width: 980px) {
          .hero-row, .card-grid, .mini-grid {
            grid-template-columns: 1fr;
          }
          .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def require_password(settings: Any) -> bool:
    if settings.app_password in {"", "change-me"}:
        return True
    if st.session_state.get("authenticated"):
        return True
    st.markdown(
        """
        <div class="empty-state hero">
          <span class="status-pill blue">私密访问</span>
          <h1>A 股每日全局复盘</h1>
          <p class="hero-summary">请输入访问密码后继续查看报告、板块排名和候选观察池。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _, center, _ = st.columns([1, 1.4, 1])
    with center:
        password = st.text_input("访问密码", type="password", label_visibility="collapsed")
        if st.button("进入系统", use_container_width=True):
            if password == settings.app_password:
                st.session_state["authenticated"] = True
                st.rerun()
            st.error("密码不正确")
    return False


def page_header(title: str, subtitle: str, eyebrow: str = "") -> None:
    label = f'<span class="status-pill blue">{esc(eyebrow)}</span>' if eyebrow else ""
    st.markdown(
        '<div class="section-head"><div>'
        f"{label}"
        f'<div class="section-title">{esc(title)}</div>'
        f'<div class="section-note">{esc(subtitle)}</div>'
        "</div></div>",
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, foot: str = "", tone: str = "neutral") -> str:
    foot_html = f'<div class="metric-foot">{esc(foot)}</div>' if foot else ""
    return (
        '<div class="metric-card">'
        f'<div class="metric-label">{esc(label)}</div>'
        f'<div class="metric-value {tone}">{esc(value)}</div>'
        f"{foot_html}</div>"
    )


def render_metric_grid(cards: list[str], class_name: str = "hero-row") -> None:
    st.markdown(f'<div class="{class_name}">{"".join(cards)}</div>', unsafe_allow_html=True)


def dataframe(rows: list[dict[str, Any]], columns: list[str] | None = None, height: int | None = None) -> None:
    if not rows:
        st.info("暂无数据")
        return
    df = pd.DataFrame(rows)
    if columns:
        df = df[[col for col in columns if col in df.columns]]
    for col in ["lifecycle"]:
        if col in df.columns:
            df["lifecycle_stage"] = df[col].apply(
                lambda value: value.get("stage", "") if isinstance(value, dict) else value
            )
            df = df.drop(columns=[col])
    rename = {key: value for key, value in COLUMN_LABELS.items() if key in df.columns}
    df = df.rename(columns=rename)
    table_height = height or min(560, 54 + max(len(df), 3) * 36)
    st.dataframe(df, use_container_width=True, hide_index=True, height=table_height)


def sector_card(row: dict[str, Any], label: str) -> str:
    change = row.get("change_pct")
    flow = row.get("main_net_inflow")
    lifecycle = row.get("lifecycle", {})
    leaders = "、".join(item.get("stock_name", "") for item in row.get("leaders_top5", [])[:3]) or "暂无"
    return f"""
    <div class="sector-card">
      <div class="sector-head">
        <div>
          <div class="sector-name">{esc(row.get("sector_name", ""))}</div>
          <div class="sector-sub">{esc(label)} · {esc(lifecycle.get("stage", "无法判断"))}</div>
        </div>
        <div class="sector-change {tone_class(change)}">{esc(fmt_pct(change))}</div>
      </div>
      <div class="chip-row">
        <span class="chip">资金 {esc(fmt_money(flow))}</span>
        <span class="chip">成交 {esc(fmt_money(row.get("amount")))}</span>
        <span class="chip">上涨 {esc(row.get("up_count", 0))}</span>
      </div>
      <div class="sector-sub" style="margin-top:16px;">代表个股：{esc(leaders)}</div>
    </div>
    """


def render_sector_cards(rows: list[dict[str, Any]], label: str) -> None:
    st.markdown(
        f'<div class="card-grid">{"".join(sector_card(row, label) for row in rows[:3])}</div>',
        unsafe_allow_html=True,
    )


def render_hero(report: dict[str, Any]) -> None:
    meta = report["metadata"]
    market = report["market_overview"]
    status_tone = "warn" if meta.get("data_status") == "demo" else "blue"
    st.markdown(
        f"""
        <div class="hero">
          <div class="chip-row" style="margin-top:0;">
            <span class="status-pill blue">{esc(meta["report_version"])}</span>
            <span class="status-pill">{esc(meta["trade_date"])}</span>
            <span class="status-pill">{esc(meta["as_of"])}</span>
            <span class="status-pill {status_tone}">{esc(meta["data_status"])}</span>
          </div>
          <h1>A 股每日全局复盘</h1>
          <p class="hero-summary">{esc(report["summary"])}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_metric_grid(
        [
            metric_card("市场状态", str(market["state"]), "由指数、涨跌家数、情绪指标综合判断", "neutral"),
            metric_card("成交额", fmt_money(market["market_amount"]), f"较前值 {fmt_pct(market['amount_change_pct'])}", "neutral"),
            metric_card("上涨 / 下跌", f"{market['up_count']} / {market['down_count']}", f"广度 {market['breadth']:.1%}", "positive" if market["up_count"] >= market["down_count"] else "negative"),
            metric_card("涨停 / 跌停", f"{market['limit_up_count']} / {market['limit_down_count']}", f"炸板率 {market['break_limit_rate']:.1%}", "neutral"),
        ]
    )


def overview_page(report: dict[str, Any]) -> None:
    render_hero(report)
    market = report["market_overview"]

    left, right = st.columns([1.3, 1], gap="large")
    with left:
        page_header("盘面触发条件", "系统使用确定性规则给出的状态解释，不使用主观预测。")
        chips = "".join(f'<span class="chip">{esc(item)}</span>' for item in market["triggered_conditions"])
        st.markdown(f'<div class="soft-card"><div class="chip-row">{chips}</div></div>', unsafe_allow_html=True)
        st.markdown(" ")
        st.progress(min(max(float(market.get("breadth", 0)), 0), 1), text=f"上涨广度 {market.get('breadth', 0):.1%}")
        st.progress(
            min(max(float(market.get("profit_effect", 0)), 0), 1),
            text=f"赚钱效应 {market.get('profit_effect', 0):.1%}",
        )
    with right:
        page_header("风格线索", "只展示当前数据已支持的结构性信息。")
        styles = "".join(f'<span class="chip">{esc(item)}</span>' for item in market.get("style_preference", []))
        st.markdown(
            f"""
            <div class="soft-card">
              <div class="metric-label">大小盘线索</div>
              <div class="metric-value" style="font-size:1.55rem;">{esc(market.get("large_vs_small", "暂无"))}</div>
              <div class="chip-row">{styles}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    page_header("强势方向", "行业和概念分开展示，不混排不同分类体系。")
    tab1, tab2 = st.tabs(["行业前三", "概念前三"])
    with tab1:
        render_sector_cards(report["industry"]["gainers_top3"], "行业")
    with tab2:
        render_sector_cards(report["concept"]["gainers_top3"], "概念")

    page_header("风险提示", "这些提示会进入报告文件，便于外部分享时保留上下文。")
    for risk in report["risks"]:
        st.markdown(f'<div class="risk-item">{esc(risk)}</div>', unsafe_allow_html=True)


def filter_sector_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    controls = st.columns([1.2, 1, 1, 1], gap="small")
    with controls[0]:
        keyword = st.text_input("搜索板块", placeholder="输入板块名称", label_visibility="collapsed")
    with controls[1]:
        only_up = st.toggle("只看上涨", value=False)
    with controls[2]:
        only_inflow = st.toggle("只看净流入", value=False)
    with controls[3]:
        sort_by = st.selectbox("排序", ["涨跌幅", "资金流", "成交额"], label_visibility="collapsed")

    filtered = rows
    if keyword:
        filtered = [row for row in filtered if keyword.strip() in str(row.get("sector_name", ""))]
    if only_up:
        filtered = [row for row in filtered if safe_float(row.get("change_pct")) > 0]
    if only_inflow:
        filtered = [row for row in filtered if safe_float(row.get("main_net_inflow")) > 0]
    sort_key = {"涨跌幅": "change_pct", "资金流": "main_net_inflow", "成交额": "amount"}[sort_by]
    return sorted(filtered, key=lambda row: safe_float(row.get(sort_key)), reverse=True)


def taxonomy_page(report: dict[str, Any], section_key: str, title: str) -> None:
    section = report[section_key]
    page_header(title, "涨跌、资金、生命周期和龙头评分集中在一个页面，便于快速扫描。", section["taxonomy_label"])
    render_metric_grid(
        [
            metric_card("板块数量", str(len(section["all_ranked"])), "当前分类体系下的可排名板块"),
            metric_card("涨幅第一", section["gainers_top3"][0]["sector_name"], fmt_pct(section["gainers_top3"][0]["change_pct"]), tone_class(section["gainers_top3"][0]["change_pct"])),
            metric_card("资金第一", section["fund_flow_top"][0]["sector_name"], fmt_money(section["fund_flow_top"][0]["main_net_inflow"]), tone_class(section["fund_flow_top"][0]["main_net_inflow"])),
        ],
        "card-grid",
    )

    tabs = st.tabs(["概览", "涨幅前三", "资金流入", "完整排名"])
    columns = ["sector_name", "change_pct", "amount", "main_net_inflow", "net_inflow_ratio", "up_count", "down_count", "lifecycle"]
    with tabs[0]:
        render_sector_cards(section["gainers_top3"], section["taxonomy_label"])
    with tabs[1]:
        dataframe(section["gainers_top3"], columns)
    with tabs[2]:
        dataframe(section["fund_flow_top"], columns)
    with tabs[3]:
        filtered = filter_sector_rows(section["all_ranked"])
        dataframe(filtered, columns, height=620)

    page_header("重点板块龙头评分", "展开板块可以看前五只代表性股票和规则证据。")
    for row in section["gainers_top3"] + section["losers_top3"]:
        with st.expander(f"{row['sector_name']} · 生命周期：{row['lifecycle']['stage']}", expanded=False):
            st.markdown("触发规则：" + "；".join(row["lifecycle"]["triggered_rules"]))
            leaders = row["leaders_top5"]
            if leaders:
                chart_df = pd.DataFrame(leaders)[["stock_name", "total_score"]].set_index("stock_name")
                st.bar_chart(chart_df, height=220)
            dataframe(
                leaders,
                ["stock_code", "stock_name", "rank_in_sector", "total_score", "leader_type", "change_pct", "money_flow"],
            )
            st.caption(row["attribution"]["summary"])


def sector_detail_page(report: dict[str, Any]) -> None:
    sectors = report["industry"]["all_ranked"] + report["concept"]["all_ranked"]
    sectors = sorted(sectors, key=lambda row: abs(safe_float(row.get("change_pct"))), reverse=True)
    page_header("板块详情", "选择一个板块，查看资金、生命周期、龙头评分和证据链。")
    names = [f"{row['taxonomy']}｜{row['sector_name']}｜{fmt_pct(row['change_pct'])}" for row in sectors]
    selected = st.selectbox("选择板块", names, label_visibility="collapsed")
    row = sectors[names.index(selected)]

    render_metric_grid(
        [
            metric_card("板块", row["sector_name"], row["taxonomy"]),
            metric_card("涨跌幅", fmt_pct(row["change_pct"]), "相对强度 " + fmt_pct(row.get("relative_strength")), tone_class(row["change_pct"])),
            metric_card("资金流", fmt_money(row["main_net_inflow"]), "资金/成交额 " + fmt_ratio(row.get("net_inflow_ratio")), tone_class(row["main_net_inflow"])),
            metric_card("生命周期", row["lifecycle"]["stage"], f"置信度 {row['lifecycle']['confidence']:.0%}"),
        ]
    )

    left, right = st.columns([1, 1], gap="large")
    with left:
        page_header("生命周期规则", row["lifecycle"]["invalidation"])
        chips = "".join(f'<span class="chip">{esc(item)}</span>' for item in row["lifecycle"]["triggered_rules"])
        st.markdown(f'<div class="soft-card"><div class="chip-row">{chips}</div></div>', unsafe_allow_html=True)
        st.markdown(" ")
        st.caption(row["attribution"]["summary"])
    with right:
        page_header("龙头评分明细", "分数越高，说明在当前板块内的强度和资金口径越靠前。")
        if row["leaders_top5"]:
            chart_df = pd.DataFrame(row["leaders_top5"])[["stock_name", "total_score"]].set_index("stock_name")
            st.bar_chart(chart_df, height=260)
    dataframe(row["leaders_top5"])
    page_header("原因和证据", "没有证据时系统会明确显示证据不足。")
    dataframe(row["attribution"]["evidence"])


def weekly_flow_page(report: dict[str, Any]) -> None:
    page_header("周线持续流入", "按当前数据供应商口径计算，适合观察持续性，不代表全部真实资金。")
    rows = report["weekly_flow"]
    top_n = st.slider("显示数量", min_value=5, max_value=min(max(len(rows), 5), 30), value=min(12, max(len(rows), 5)))
    scoped = rows[:top_n]
    if scoped:
        chart_df = pd.DataFrame(scoped)[["sector_name", "flow_5d", "flow_10d", "flow_20d"]].set_index("sector_name")
        st.bar_chart(chart_df, height=340)
    dataframe(scoped, ["sector_name", "taxonomy", "category", "flow_5d", "flow_10d", "flow_20d", "score"])


def watchlist_page(report: dict[str, Any]) -> None:
    page_header("候选观察池", "只作为研究观察清单，包含风险和失效条件，不输出交易指令。")
    rows = report["watchlist"]
    types = ["全部", *sorted({row.get("candidate_type", "") for row in rows if row.get("candidate_type")})]
    c1, c2 = st.columns([1, 1])
    with c1:
        selected_type = st.selectbox("类型", types)
    with c2:
        min_score = st.slider("最低评分", 0, 100, 55)
    filtered = [
        row for row in rows
        if (selected_type == "全部" or row.get("candidate_type") == selected_type)
        and safe_float(row.get("total_score")) >= min_score
    ]
    render_metric_grid(
        [
            metric_card("候选数量", str(len(filtered)), "已按当前筛选条件更新"),
            metric_card("最高评分", str(max([safe_float(row.get("total_score")) for row in filtered], default=0)), "仅用于相对排序"),
        ],
        "mini-grid",
    )
    dataframe(
        filtered,
        ["stock_code", "stock_name", "main_sector", "candidate_type", "total_score", "reason", "invalidation", "data_as_of"],
        height=620,
    )


def history_page(settings: Any, report: dict[str, Any]) -> None:
    page_header("历史报告", "查看已生成版本，也可以手动补跑某个交易日。")
    root = settings.report_output_dir
    rows = []
    for path in sorted(root.glob("*/*/report.json"), reverse=True):
        item = json.loads(path.read_text(encoding="utf-8"))
        rows.append(
            {
                "日期": item["metadata"]["trade_date"],
                "版本": item["metadata"]["report_version"],
                "数据截止": item["metadata"]["as_of"],
                "状态": item["metadata"]["data_status"],
                "路径": str(path.relative_to(PROJECT_ROOT)),
            }
        )
    dataframe(rows, height=430)

    latest_dir = settings.report_output_dir / report["metadata"]["trade_date"] / report["metadata"]["report_type"]
    st.markdown('<div class="section-note">下载当前报告</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for col, (label, filename, mime) in zip(
        cols,
        [
            ("JSON", "report.json", "application/json"),
            ("Markdown", "report.md", "text/markdown"),
            ("HTML", "report.html", "text/html"),
            ("观察池 CSV", "watchlist.csv", "text/csv"),
        ],
        strict=False,
    ):
        path = latest_dir / filename
        if path.exists():
            col.download_button(label, path.read_bytes(), file_name=filename, mime=mime, use_container_width=True)

    with st.container(border=True):
        st.subheader("重新生成")
        c1, c2, c3 = st.columns([1, 1.2, 1])
        with c1:
            trade_date = st.text_input("日期", value="today")
        with c2:
            report_type_options = ["PRE_CLOSE_PREVIEW", "CLOSE_CONFIRMATION", "POST_CLOSE_FINAL"]
            selected_report_type = st.selectbox(
                "版本",
                report_type_options,
                format_func=lambda key: str(REPORT_TYPES[key]["label"]),
            )
            report_type = selected_report_type or "POST_CLOSE_FINAL"
        with c3:
            st.write("")
            st.write("")
            generate = st.button("生成报告", use_container_width=True)
        if generate:
            with st.spinner("正在生成报告"):
                parsed = parse_trade_date(trade_date, settings.timezone)
                result = ReportGenerator(settings).generate(parsed, report_type)
            st.success("生成完成")
            st.json(result["files"])


def health_page(report: dict[str, Any]) -> None:
    meta = report["metadata"]
    page_header("数据健康", "所有报告都保留来源、Provider、数据状态和质量警告。")
    render_metric_grid(
        [
            metric_card("Provider", meta["provider"], meta["source"]),
            metric_card("数据状态", meta["data_status"], "demo 表示演示数据"),
            metric_card("报告时区", meta["timezone"], "所有时间字段带时区"),
        ],
        "card-grid",
    )
    page_header("质量警告", "分享给朋友时也应保留这些提示。")
    for warning in meta["quality_warnings"]:
        st.markdown(f'<div class="risk-item">{esc(warning)}</div>', unsafe_allow_html=True)
    with st.expander("查看完整元数据"):
        st.json(meta)


def settings_page(report: dict[str, Any]) -> None:
    page_header("系统设置", "密钥不会在普通网页中明文展示；这里只显示当前报告使用的配置视图。")
    st.json(report["settings_view"])


def empty_state(settings: Any) -> None:
    st.markdown(
        """
        <div class="empty-state hero">
          <span class="status-pill blue">等待第一份报告</span>
          <h1>A 股每日全局复盘</h1>
          <p class="hero-summary">还没有生成报告。可以先生成最近交易日的演示报告，用于检查页面和流程。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        if st.button("生成最近交易日报告", use_container_width=True):
            with st.spinner("正在生成"):
                ReportGenerator(settings).generate(parse_trade_date("today", settings.timezone), "POST_CLOSE_FINAL")
            st.rerun()


def sidebar_nav(report: dict[str, Any] | None) -> str:
    st.sidebar.markdown(
        """
        <div class="brand-lockup">
          <div class="brand-title">A 股全局复盘</div>
          <div class="brand-subtitle">市场 · 板块 · 资金 · 候选池</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if report:
        meta = report["metadata"]
        st.sidebar.caption(f"{meta['trade_date']} · {meta['report_version']}")
        st.sidebar.caption(f"Provider：{meta['provider']} · {meta['data_status']}")
    return st.sidebar.radio("页面", NAV_ITEMS, label_visibility="collapsed")


def main() -> None:
    settings = load_settings()
    st.set_page_config(
        page_title="A 股每日全局复盘",
        page_icon="A",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    apply_style()
    if not require_password(settings):
        return
    report = load_latest_report()
    if report is None:
        empty_state(settings)
        return

    page = sidebar_nav(report)
    if page == "今日总览":
        overview_page(report)
    elif page == "行业板块":
        taxonomy_page(report, "industry", "行业板块")
    elif page == "概念板块":
        taxonomy_page(report, "concept", "概念板块")
    elif page == "板块详情":
        sector_detail_page(report)
    elif page == "周线持续流入":
        weekly_flow_page(report)
    elif page == "候选观察池":
        watchlist_page(report)
    elif page == "历史报告":
        history_page(settings, report)
    elif page == "数据健康":
        health_page(report)
    else:
        settings_page(report)


if __name__ == "__main__":
    main()
