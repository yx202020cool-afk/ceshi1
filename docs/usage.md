# 使用说明

## 生成三种报告

```bash
python -m ashare_replay.cli generate-all --date today
```

## 生成指定版本

```bash
python -m ashare_replay.cli generate --date 2026-07-10 --report-type POST_CLOSE_FINAL
```

## 查看最近报告

```bash
python -m ashare_replay.cli latest
```

## 健康检查

```bash
python -m ashare_replay.cli health
```

## 真实数据 Provider 自检

默认免费真实源是 AKShare，不需要密钥。切换为真实模式后运行：

```bash
python -m ashare_replay.cli provider-audit --save
```

只检查配置、不访问外部接口：

```bash
python -m ashare_replay.cli provider-audit --no-probe
```

如果改用 Tushare，需要在 `.env` 中设置 `REAL_PROVIDER=tushare` 并填写 `TUSHARE_TOKEN`。

## Docker 启动条件检查

```bash
python -m ashare_replay.cli ops-check
```

不可启动时返回失败状态：

```bash
python -m ashare_replay.cli ops-check --strict
```

## 启动网页

```bash
python -m streamlit run ashare_replay/ui/streamlit_app.py --server.address=127.0.0.1 --server.port=8501
```

## 启动 API

```bash
python -m uvicorn ashare_replay.api:app --host 127.0.0.1 --port 8000
```

## 演示回测

```bash
python -m ashare_replay.cli backtest --start 2026-07-06 --end 2026-07-10
```

## 生成长周期演示 Fixture

```bash
python -m ashare_replay.cli build-fixture --start 2026-04-01 --end 2026-07-10
```

默认输出：

```text
fixtures/demo/long_history_fixture.json
```
