from __future__ import annotations

REPORT_TYPES = {
    "PRE_CLOSE_PREVIEW": {
        "label": "14:50 盘中预览版",
        "time": "14:50",
        "is_final": False,
        "note": "盘中预览，非最终收盘数据",
    },
    "CLOSE_CONFIRMATION": {
        "label": "15:10 收盘行情确认版",
        "time": "15:10",
        "is_final": False,
        "note": "收盘行情已确认，部分资金数据可能仍为暂定",
    },
    "POST_CLOSE_FINAL": {
        "label": "17:30 盘后资金完整版",
        "time": "17:30",
        "is_final": True,
        "note": "当日最终研究版本",
    },
}

TAXONOMY_LABELS = {
    "industry": "行业板块",
    "concept": "概念板块",
}

DATA_STATUS = {
    "normal": "正常",
    "delayed": "延迟",
    "missing": "缺失",
    "expired": "过期",
    "abnormal": "异常",
    "demo": "演示数据",
}

DISCLAIMER = (
    "本系统仅用于市场研究和复盘，不构成投资建议；不承诺收益，"
    "不输出无条件买入、卖出或仓位指令，不提供自动下单能力。"
)
