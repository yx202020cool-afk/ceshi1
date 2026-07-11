# 架构说明

系统分为七层：

1. 配置层：`configs/default_config.json` 保存报告时间、过滤阈值、评分权重和生命周期阈值。
2. Provider 层：`ashare_replay/providers/` 统一封装交易日历、股票、行情、板块、资金流、新闻和公告。
3. 数据层：`ashare_replay/db.py` 支持 SQLite 本地模式和 PostgreSQL 生产模式。
4. 计算层：`ashare_replay/services/` 负责排名、龙头评分、生命周期、归因、周线资金、候选池和回测。
5. 报告层：`ashare_replay/services/report.py` 生成 JSON、Markdown、HTML、PDF 和 CSV。
6. API 层：`ashare_replay/api.py` 提供健康检查、报告查询和手动生成接口。
7. 展示层：`ashare_replay/ui/streamlit_app.py` 提供中文网页。

Docker Compose 包含 PostgreSQL、FastAPI、Streamlit 和 scheduler 四个服务。普通本地运行默认使用 SQLite，方便开发和演示。
