# 备份和恢复

## 本地 SQLite

关闭系统后备份：

- `work/data/ashare_replay.sqlite3`
- `outputs/reports/`
- `.env`

恢复时，把这些文件复制回同名位置，再启动系统。

## Docker PostgreSQL

备份：

```bash
docker compose exec db pg_dump -U ashare -d ashare_review > backup.sql
```

恢复：

```bash
docker compose exec -T db psql -U ashare -d ashare_review < backup.sql
```

不要公开分享 `.env` 和数据库备份，里面可能包含配置、密钥或内部数据。
