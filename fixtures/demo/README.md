# 演示 Fixture

DemoProvider 使用固定种子按交易日期和报告版本生成可复现数据。

当前示例报告使用：

- 交易日：2026-07-10
- 版本：`PRE_CLOSE_PREVIEW`、`CLOSE_CONFIRMATION`、`POST_CLOSE_FINAL`

演示数据只用于验证功能流程，不代表真实行情。

生成长周期固定 Fixture：

```bash
python -m ashare_replay.cli build-fixture --start 2026-04-01 --end 2026-07-10
```

默认输出：

```text
fixtures/demo/long_history_fixture.json
```
