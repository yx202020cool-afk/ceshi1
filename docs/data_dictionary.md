# 数据字典

核心统一字段：

- `source`：数据来源名称。
- `provider`：Provider 标识。
- `trade_date`：交易日期。
- `as_of`：数据对应的市场时间。
- `effective_at`：数据生效时间。
- `fetched_at`：系统获取数据时间。
- `created_at` / `updated_at`：系统入库时间。
- `report_type`：报告版本。
- `report_version`：报告中文名称。
- `is_final`：是否最终数据。
- `taxonomy`：板块分类，`industry` 或 `concept`。
- `data_status`：正常、延迟、缺失、过期、异常或演示数据。
- `quality_warnings`：数据质量警告。

主要表：

- `stocks`：股票基础信息。
- `trading_calendar`：交易日历。
- `sectors`：板块信息。
- `sector_constituents`：板块历史成分。
- `raw_quotes`：个股行情。
- `sector_quotes`：板块行情。
- `stock_money_flow`：个股资金流。
- `sector_money_flow`：板块资金流。
- `news` / `announcements`：新闻和公告证据。
- `data_snapshots`：原始快照。
- `features`：特征结果。
- `leader_scores`：龙头评分。
- `lifecycle_results`：生命周期判断。
- `watchlist`：候选观察池。
- `reports`：报告记录。
- `job_runs`：任务执行记录。
- `data_quality_issues`：数据质量问题。
- `config_versions`：配置版本。
