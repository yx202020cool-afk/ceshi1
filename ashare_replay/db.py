from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from ashare_replay.config import PROJECT_ROOT, Settings, resolve_path
from ashare_replay.time_utils import iso_now


class Database:
    def __init__(self, database_url: str, timezone: str = "Asia/Shanghai") -> None:
        self.database_url = database_url
        self.timezone = timezone
        self.kind = "postgres" if database_url.startswith(("postgresql://", "postgres://")) else "sqlite"

    def _sqlite_path(self) -> Path:
        raw = self.database_url.removeprefix("sqlite:///")
        return resolve_path(raw)

    @contextmanager
    def connect(self) -> Iterator[Any]:
        if self.kind == "sqlite":
            db_path = self._sqlite_path()
            db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
        else:
            try:
                import psycopg
                from psycopg.rows import dict_row
            except ImportError as exc:
                raise RuntimeError("PostgreSQL 模式需要安装 psycopg[binary]。") from exc
            with psycopg.connect(self.database_url, row_factory=dict_row) as pg_conn:
                yield pg_conn

    def _sql(self, sql: str) -> str:
        if self.kind == "sqlite":
            return sql
        return re.sub(r":([A-Za-z_][A-Za-z0-9_]*)", r"%(\1)s", sql)

    def init_db(self) -> None:
        migration = (
            PROJECT_ROOT / "migrations" / "001_init_postgres.sql"
            if self.kind == "postgres"
            else PROJECT_ROOT / "migrations" / "001_init_sqlite.sql"
        )
        sql = migration.read_text(encoding="utf-8")
        with self.connect() as conn:
            if self.kind == "sqlite":
                conn.executescript(sql)
            else:
                for statement in [part.strip() for part in sql.split(";") if part.strip()]:
                    conn.execute(statement)

    def query(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        with self.connect() as conn:
            cur = conn.execute(self._sql(sql), params or {})
            rows = cur.fetchall()
            return [dict(row) for row in rows]

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> None:
        with self.connect() as conn:
            conn.execute(self._sql(sql), params or {})

    def upsert_provider_health(self, payload: dict[str, Any]) -> None:
        payload = dict(payload)
        payload.setdefault("updated_at", iso_now(self.timezone))
        self.execute(
            """
            INSERT INTO provider_health (
                provider_name, status, mode, last_success_at, last_error_at,
                last_error, uses_demo_data, is_final, updated_at
            )
            VALUES (
                :provider_name, :status, :mode, :last_success_at, :last_error_at,
                :last_error, :uses_demo_data, :is_final, :updated_at
            )
            ON CONFLICT(provider_name) DO UPDATE SET
                status=excluded.status,
                mode=excluded.mode,
                last_success_at=excluded.last_success_at,
                last_error_at=excluded.last_error_at,
                last_error=excluded.last_error,
                uses_demo_data=excluded.uses_demo_data,
                is_final=excluded.is_final,
                updated_at=excluded.updated_at
            """,
            payload,
        )

    def upsert_config(self, config_hash: str, config: dict[str, Any]) -> None:
        self.execute(
            """
            INSERT INTO config_versions(config_hash, config_json, created_at)
            VALUES(:config_hash, :config_json, :created_at)
            ON CONFLICT(config_hash) DO UPDATE SET config_json=excluded.config_json
            """,
            {
                "config_hash": config_hash,
                "config_json": json.dumps(config, ensure_ascii=False, sort_keys=True),
                "created_at": iso_now(self.timezone),
            },
        )

    def save_report(self, report: dict[str, Any], file_map: dict[str, str]) -> None:
        metadata = report["metadata"]
        generation = report["generation"]
        report_id = generation["report_id"]
        now = iso_now(self.timezone)
        self.execute(
            """
            INSERT INTO reports (
                report_id, trade_date, report_type, report_version, is_final,
                snapshot_id, config_version, weights_version, code_version, provider,
                data_status, quality_warnings, report_json, reproducible_key, generated_at
            )
            VALUES (
                :report_id, :trade_date, :report_type, :report_version, :is_final,
                :snapshot_id, :config_version, :weights_version, :code_version, :provider,
                :data_status, :quality_warnings, :report_json, :reproducible_key, :generated_at
            )
            ON CONFLICT(trade_date, report_type, reproducible_key) DO UPDATE SET
                report_json=excluded.report_json,
                data_status=excluded.data_status,
                quality_warnings=excluded.quality_warnings,
                generated_at=excluded.generated_at
            """,
            {
                "report_id": report_id,
                "trade_date": metadata["trade_date"],
                "report_type": metadata["report_type"],
                "report_version": metadata["report_version"],
                "is_final": int(bool(metadata["is_final"])),
                "snapshot_id": generation["snapshot_id"],
                "config_version": generation["config_version"],
                "weights_version": generation["weights_version"],
                "code_version": generation["code_version"],
                "provider": metadata["provider"],
                "data_status": metadata["data_status"],
                "quality_warnings": json.dumps(metadata["quality_warnings"], ensure_ascii=False),
                "report_json": json.dumps(report, ensure_ascii=False, sort_keys=True),
                "reproducible_key": generation["reproducible_key"],
                "generated_at": generation["generated_at"],
            },
        )
        for file_type, file_path in file_map.items():
            self.execute(
                """
                INSERT INTO report_files(report_id, file_type, file_path, created_at)
                VALUES(:report_id, :file_type, :file_path, :created_at)
                ON CONFLICT(report_id, file_type, file_path) DO NOTHING
                """,
                {
                    "report_id": report_id,
                    "file_type": file_type,
                    "file_path": file_path,
                    "created_at": now,
                },
            )

    def save_snapshot(self, snapshot: dict[str, Any]) -> None:
        self.execute(
            """
            INSERT INTO data_snapshots (
                snapshot_id, provider, trade_date, as_of, report_type,
                payload_json, payload_hash, created_at
            )
            VALUES (
                :snapshot_id, :provider, :trade_date, :as_of, :report_type,
                :payload_json, :payload_hash, :created_at
            )
            ON CONFLICT(snapshot_id) DO UPDATE SET payload_json=excluded.payload_json
            """,
            snapshot,
        )

    def record_job(
        self,
        run_id: str,
        job_name: str,
        trade_date: str,
        report_type: str | None,
        status: str,
        message: str = "",
        ended_at: str | None = None,
    ) -> None:
        now = iso_now(self.timezone)
        self.execute(
            """
            INSERT INTO job_runs(
                run_id, job_name, trade_date, report_type, status,
                started_at, ended_at, message, created_at
            )
            VALUES(
                :run_id, :job_name, :trade_date, :report_type, :status,
                :started_at, :ended_at, :message, :created_at
            )
            ON CONFLICT(run_id) DO UPDATE SET
                status=excluded.status,
                ended_at=excluded.ended_at,
                message=excluded.message
            """,
            {
                "run_id": run_id,
                "job_name": job_name,
                "trade_date": trade_date,
                "report_type": report_type,
                "status": status,
                "started_at": now,
                "ended_at": ended_at,
                "message": message,
                "created_at": now,
            },
        )

    def latest_reports(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.query(
            """
            SELECT trade_date, report_type, report_version, is_final, provider,
                   data_status, generated_at, report_json
            FROM reports
            ORDER BY generated_at DESC
            LIMIT :limit
            """,
            {"limit": limit},
        )


def make_database(settings: Settings) -> Database:
    return Database(settings.database_url, settings.timezone)
