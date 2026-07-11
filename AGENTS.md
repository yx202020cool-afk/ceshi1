# AGENTS.md

后续任何 Codex 任务都应先阅读本文件。

## 项目目标

维护一个可长期运行的中文 A 股每日全局复盘与板块资金分析系统。系统用于研究和复盘，不构成投资建议，不提供自动下单能力。

## 数据真实性规则

- 演示数据必须明确标注为演示数据。
- 真实数据失败时不得静默切换为演示数据。
- 不得伪造接口成功、新闻、公告、资金流或行情数字。
- 没有证据时必须显示“证据不足”。
- 所有报告必须包含数据来源、Provider、数据截止时间、数据状态和质量警告。

## 数据时间规则

- 时间统一使用 `Asia/Shanghai`。
- 所有时间字段必须带时区。
- 不得使用未来数据。
- 盘中预览不得描述成最终收盘结果。
- 定时任务只应在 A 股交易日运行。

## 禁止前视偏差

- 历史验证必须使用当时可获得的数据。
- 板块历史成分必须使用当日有效成分。
- 不得用当前成分回填历史。
- 不得选择性展示表现最好的区间。

## 资金流口径规则

- 统一使用表达：“按当前数据供应商口径计算的主力资金流指标”。
- 不得说主力资金流完整代表全部真实机构或全部真实资金。
- 不同供应商口径不得直接合并或比较。
- 数据源不支持的资金字段必须显示“不支持”，不得估算或虚构。

## 板块分类规则

- 行业板块和概念板块必须分开排名、分开展示。
- 不同供应商或不同分类体系不得混排。
- 每个板块必须保留 taxonomy、provider、classification_system 和成分有效期。

## 大语言模型边界

- LLM 只能用于改写已计算结果、压缩已有新闻公告证据和生成中文说明。
- LLM 不得生成行情数字、排名、生命周期、资金流、新闻链接或因果结论。
- 没有 LLM 密钥时，系统必须仍能使用确定性模板生成完整中文报告。

## 安全规则

- 密钥只能来自环境变量或 `.env`，不得写入代码。
- 日志不得打印完整密钥。
- 外部输入必须校验。
- 下载文件名必须校验，防止路径穿越。
- 数据库写入必须使用参数化语句。
- Docker 容器使用非 root 用户运行。
- PostgreSQL 默认只绑定本机地址，不直接暴露到公网。

## 编码规范

- 数据层、计算层、解释层和展示层分离。
- 配置、评分权重和阈值不得硬编码在业务流程中，应放入 `configs/default_config.json`。
- 演示 Provider 可以使用固定种子生成数据，但必须可复现。
- 真实 Provider 缺权限时应抛出明确错误。

## 测试命令

```bash
python -m pytest
python -m ruff check ashare_replay tests
python -m mypy ashare_replay
```

## 启动命令

Windows 双击：

```text
start_windows.bat
```

macOS/Linux：

```bash
sh start.sh
```

本机开发：

```bash
python -m ashare_replay.cli generate-all --date today
python -m streamlit run ashare_replay/ui/streamlit_app.py --server.port 8501
python -m uvicorn ashare_replay.api:app --host 127.0.0.1 --port 8000
```

## 完成标准

- 演示模式可以不需要密钥运行。
- 三种报告版本可以生成。
- 行业和概念板块分开排名。
- 龙头评分可追溯到子分数。
- 生命周期判断显示触发规则。
- 候选观察池包含风险和失效条件。
- 报告输出 JSON、Markdown、HTML、PDF、CSV。
- 测试、静态检查和类型检查通过。

## 每次修改后必须执行

```bash
python -m pytest
python -m ruff check ashare_replay tests
python -m mypy ashare_replay
```
