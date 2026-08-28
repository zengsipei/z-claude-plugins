#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 登记共享核心。

优先使用仓库 ``docs/ai-register.json`` 配置的 PostgreSQL 或 MySQL；
配置、驱动或连接不可用时，降级到仓库 ``docs/ai-register.db`` SQLite。
所有后端记录同一组核心字段：session、任务目录、工具、模型、分支、
已完成任务和进度。远程驱动按需导入，SQLite 路径保持零外部依赖。
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from typing import Any, Callable


DEFAULT_DB_RELPATH = os.path.join("docs", "ai-register.db")
DEFAULT_CONFIG_RELPATH = os.path.join("docs", "ai-register.json")
TABLE_NAME = "ai_register"

ALL_COLUMNS = (
    "session_id",
    "tool",
    "model",
    "branch",
    "resume_shell",
    "resume_cli",
    "cwd",
    "task_dir",
    "completed_tasks",
    "feature",
    "progress",
    "source",
    "created_at",
    "updated_at",
)


def now_str() -> str:
    """返回脚本运行环境的本地时间。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def find_repo_root(cwd: str | None = None) -> str:
    """从 cwd 向上查找 Git 根；找不到时退回 cwd。"""
    current = os.path.abspath(cwd or os.getcwd())
    if os.path.isfile(current):
        current = os.path.dirname(current)
    while True:
        if os.path.exists(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return os.path.abspath(cwd or os.getcwd())
        current = parent


def default_db_path(cwd: str | None = None) -> str:
    """返回 Git 根目录下的项目 SQLite 路径。"""
    return os.path.join(find_repo_root(cwd), DEFAULT_DB_RELPATH)


def default_config_path(cwd: str | None = None) -> str:
    """返回 Git 根目录下的远程登记配置路径。"""
    return os.path.join(find_repo_root(cwd), DEFAULT_CONFIG_RELPATH)


def normalize_task_dir(task_dir: str) -> str:
    """统一任务目录分隔符和尾部斜杠。"""
    value = task_dir.strip()
    if not value:
        return value
    value = os.path.normpath(value).replace("\\", "/")
    return value.rstrip("/") + "/"


def detect_git_branch(cwd: str | None = None) -> str | None:
    """从仓库读取当前分支；detached HEAD 或非 Git 目录返回 None。"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=find_repo_root(cwd),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    branch = result.stdout.strip()
    if result.returncode != 0 or not branch or branch == "HEAD":
        return None
    return branch


def build_resume(tool: str | None, session_id: str) -> tuple[str | None, str | None]:
    """按已知工具生成续接命令；未知工具不伪造。"""
    if not tool:
        return (None, None)
    lowered = tool.lower()
    if "codex" in lowered:
        return (f"codex resume {session_id}", "/resume")
    if "claude" in lowered:
        return (f"claude -r {session_id}", f"/resume {session_id}")
    if "grok" in lowered:
        return (f"grok --resume {session_id}", "/resume")
    return (None, None)


def parse_completed_tasks(value: Any) -> list[str]:
    """把 JSON 数组、列表或旧单值转换为去重后的任务列表。"""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        raw_items = value
    else:
        text = str(value).strip()
        if not text:
            return []
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            raw_items = [text]
        else:
            raw_items = decoded if isinstance(decoded, list) else [decoded]
    result: list[str] = []
    for item in raw_items:
        text = str(item).strip()
        if text and text not in result:
            result.append(text)
    return result


def merge_completed_tasks(existing: Any, incoming: Any) -> str:
    """追加并去重已完成任务，以 JSON 文本跨后端保存。"""
    tasks = parse_completed_tasks(existing)
    for task in parse_completed_tasks(incoming):
        if task not in tasks:
            tasks.append(task)
    return json.dumps(tasks, ensure_ascii=False)


def _row_dicts(cursor: Any) -> list[dict[str, Any]]:
    """把不同 DB-API 驱动返回的元组统一转换为字典。"""
    description = cursor.description or []
    names = [getattr(item, "name", item[0]) for item in description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


class SQLiteRegistry:
    """仓库级 SQLite 登记实现。"""

    name = "sqlite"

    def __init__(self, db_path: str):
        self.db_path = os.path.abspath(db_path)

    def _connect(self) -> sqlite3.Connection:
        parent = os.path.dirname(self.db_path)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def ensure(self) -> None:
        conn = self._connect()
        try:
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                  session_id      TEXT PRIMARY KEY,
                  tool            TEXT,
                  model           TEXT,
                  branch          TEXT,
                  resume_shell    TEXT,
                  resume_cli      TEXT,
                  cwd             TEXT,
                  task_dir        TEXT,
                  completed_tasks TEXT,
                  feature         TEXT,
                  progress        TEXT,
                  source          TEXT,
                  created_at      TEXT,
                  updated_at      TEXT
                )
                """
            )
            existing = {
                row["name"] for row in conn.execute(f"PRAGMA table_info({TABLE_NAME})")
            }
            for column in ALL_COLUMNS:
                if column not in existing:
                    conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN {column} TEXT")
            conn.execute(
                f"""UPDATE {TABLE_NAME}
                    SET completed_tasks=feature
                    WHERE (completed_tasks IS NULL OR completed_tasks='')
                      AND feature IS NOT NULL AND feature<>''"""
            )
            conn.commit()
        finally:
            conn.close()

    def upsert_identity(
        self,
        session_id: str,
        tool: str | None = None,
        model: str | None = None,
        cwd: str | None = None,
        source: str | None = None,
        branch: str | None = None,
    ) -> bool:
        if not session_id:
            return False
        self.ensure()
        resume_shell, resume_cli = build_resume(tool, session_id)
        effective_branch = branch or detect_git_branch(cwd)
        ts = now_str()
        conn = self._connect()
        try:
            conn.execute(
                f"""
                INSERT INTO {TABLE_NAME}
                  (session_id, tool, model, branch, resume_shell, resume_cli,
                   cwd, source, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(session_id) DO UPDATE SET
                  tool=COALESCE(excluded.tool, {TABLE_NAME}.tool),
                  model=COALESCE(excluded.model, {TABLE_NAME}.model),
                  branch=COALESCE(excluded.branch, {TABLE_NAME}.branch),
                  resume_shell=COALESCE(excluded.resume_shell, {TABLE_NAME}.resume_shell),
                  resume_cli=COALESCE(excluded.resume_cli, {TABLE_NAME}.resume_cli),
                  cwd=COALESCE(excluded.cwd, {TABLE_NAME}.cwd),
                  source=COALESCE(excluded.source, {TABLE_NAME}.source),
                  updated_at=excluded.updated_at
                """,
                (
                    session_id,
                    tool,
                    model,
                    effective_branch,
                    resume_shell,
                    resume_cli,
                    cwd,
                    source,
                    ts,
                    ts,
                ),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def update_progress(
        self,
        session_id: str,
        task_dir: str | None = None,
        completed_tasks: Any = None,
        progress: str | None = None,
        branch: str | None = None,
    ) -> bool:
        if not session_id:
            return False
        self.ensure()
        ts = now_str()
        conn = self._connect()
        try:
            conn.execute(
                f"INSERT OR IGNORE INTO {TABLE_NAME} "
                "(session_id, created_at, updated_at) VALUES (?,?,?)",
                (session_id, ts, ts),
            )
            sets: list[str] = []
            params: list[Any] = []
            if task_dir is not None:
                sets.append("task_dir=?")
                params.append(normalize_task_dir(task_dir))
            if completed_tasks is not None:
                row = conn.execute(
                    f"SELECT completed_tasks, feature FROM {TABLE_NAME} WHERE session_id=?",
                    (session_id,),
                ).fetchone()
                existing = row["completed_tasks"] or row["feature"] if row else None
                merged = merge_completed_tasks(existing, completed_tasks)
                incoming_tasks = parse_completed_tasks(completed_tasks)
                legacy_feature = incoming_tasks[-1] if incoming_tasks else None
                sets.extend(("completed_tasks=?", "feature=?"))
                params.extend((merged, legacy_feature))
            if progress is not None:
                sets.append("progress=?")
                params.append(progress)
            effective_branch = branch or detect_git_branch()
            if effective_branch is not None:
                sets.append("branch=?")
                params.append(effective_branch)
            sets.append("updated_at=?")
            params.append(ts)
            params.append(session_id)
            conn.execute(
                f"UPDATE {TABLE_NAME} SET {', '.join(sets)} WHERE session_id=?",
                params,
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def query(
        self,
        task_dir: str | None = None,
        keyword: str | None = None,
    ) -> list[dict[str, Any]]:
        if not os.path.exists(self.db_path):
            return []
        self.ensure()
        conn = self._connect()
        try:
            if task_dir:
                cursor = conn.execute(
                    f"SELECT * FROM {TABLE_NAME} "
                    "WHERE task_dir=? COLLATE NOCASE ORDER BY updated_at DESC",
                    (normalize_task_dir(task_dir),),
                )
            elif keyword:
                like = f"%{keyword}%"
                cursor = conn.execute(
                    f"""
                    SELECT * FROM {TABLE_NAME}
                    WHERE task_dir LIKE ? OR completed_tasks LIKE ? OR feature LIKE ?
                       OR cwd LIKE ? OR branch LIKE ? OR source LIKE ? OR session_id LIKE ?
                    ORDER BY updated_at DESC
                    """,
                    (like, like, like, like, like, like, like),
                )
            else:
                cursor = conn.execute(
                    f"SELECT * FROM {TABLE_NAME} ORDER BY updated_at DESC"
                )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()


class RemoteRegistry:
    """PostgreSQL / MySQL 登记实现，驱动按配置后端延迟导入。"""

    def __init__(self, config: dict[str, Any]):
        backend = str(config.get("backend", "")).strip().lower()
        aliases = {
            "pg": "postgresql",
            "postgres": "postgresql",
            "postgresql": "postgresql",
            "mysql": "mysql",
        }
        if backend not in aliases:
            raise ValueError("backend 必须是 postgresql 或 mysql")
        self.name = aliases[backend]
        self.config = config

    def _password(self) -> str | None:
        """从配置 JSON 直接读取 password；缺省或空字符串视为无密码。"""
        if "password" not in self.config:
            return None
        value = self.config.get("password")
        if value is None:
            return None
        text = str(value)
        return text if text else None

    def _connect(self) -> Any:
        host = self.config.get("host", "127.0.0.1")
        database = self.config.get("database")
        user = self.config.get("user")
        if not database or not user:
            raise ValueError("远程登记配置必须包含 database 和 user")
        password = self._password()
        timeout = int(self.config.get("connect_timeout", 3))

        if self.name == "postgresql":
            kwargs: dict[str, Any] = {
                "host": host,
                "port": int(self.config.get("port", 5432)),
                "dbname": database,
                "user": user,
                "connect_timeout": timeout,
            }
            if password is not None:
                kwargs["password"] = password
            if self.config.get("sslmode"):
                kwargs["sslmode"] = self.config["sslmode"]
            try:
                import psycopg  # type: ignore

                return psycopg.connect(**kwargs)
            except ImportError:
                try:
                    import psycopg2  # type: ignore

                    return psycopg2.connect(**kwargs)
                except ImportError as exc:
                    raise RuntimeError("缺少 PostgreSQL 驱动 psycopg/psycopg2") from exc

        kwargs = {
            "host": host,
            "port": int(self.config.get("port", 3306)),
            "database": database,
            "user": user,
            "connect_timeout": timeout,
        }
        if password is not None:
            kwargs["password"] = password
        try:
            import pymysql  # type: ignore

            return pymysql.connect(charset="utf8mb4", autocommit=False, **kwargs)
        except ImportError:
            try:
                import mysql.connector  # type: ignore

                return mysql.connector.connect(**kwargs)
            except ImportError as exc:
                raise RuntimeError(
                    "缺少 MySQL 驱动 pymysql/mysql-connector-python"
                ) from exc

    def ensure(self) -> None:
        conn = self._connect()
        cursor = conn.cursor()
        try:
            session_type = "TEXT" if self.name == "postgresql" else "VARCHAR(255)"
            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                  session_id      {session_type} PRIMARY KEY,
                  tool            TEXT,
                  model           TEXT,
                  branch          TEXT,
                  resume_shell    TEXT,
                  resume_cli      TEXT,
                  cwd             TEXT,
                  task_dir        TEXT,
                  completed_tasks TEXT,
                  feature         TEXT,
                  progress        TEXT,
                  source          TEXT,
                  created_at      VARCHAR(32),
                  updated_at      VARCHAR(32)
                )
                """
            )
            if self.name == "postgresql":
                cursor.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema=current_schema() AND table_name=%s",
                    (TABLE_NAME,),
                )
            else:
                cursor.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema=DATABASE() AND table_name=%s",
                    (TABLE_NAME,),
                )
            existing = {row[0] for row in cursor.fetchall()}
            for column in ALL_COLUMNS:
                if column not in existing:
                    column_type = "VARCHAR(255)" if column == "session_id" else "TEXT"
                    cursor.execute(
                        f"ALTER TABLE {TABLE_NAME} ADD COLUMN {column} {column_type}"
                    )
            cursor.execute(
                f"""UPDATE {TABLE_NAME}
                    SET completed_tasks=feature
                    WHERE (completed_tasks IS NULL OR completed_tasks='')
                      AND feature IS NOT NULL AND feature<>''"""
            )
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def upsert_identity(
        self,
        session_id: str,
        tool: str | None = None,
        model: str | None = None,
        cwd: str | None = None,
        source: str | None = None,
        branch: str | None = None,
    ) -> bool:
        if not session_id:
            return False
        self.ensure()
        resume_shell, resume_cli = build_resume(tool, session_id)
        effective_branch = branch or detect_git_branch(cwd)
        ts = now_str()
        values = (
            session_id,
            tool,
            model,
            effective_branch,
            resume_shell,
            resume_cli,
            cwd,
            source,
            ts,
            ts,
        )
        if self.name == "postgresql":
            sql = f"""
                INSERT INTO {TABLE_NAME}
                  (session_id, tool, model, branch, resume_shell, resume_cli,
                   cwd, source, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(session_id) DO UPDATE SET
                  tool=COALESCE(EXCLUDED.tool, {TABLE_NAME}.tool),
                  model=COALESCE(EXCLUDED.model, {TABLE_NAME}.model),
                  branch=COALESCE(EXCLUDED.branch, {TABLE_NAME}.branch),
                  resume_shell=COALESCE(EXCLUDED.resume_shell, {TABLE_NAME}.resume_shell),
                  resume_cli=COALESCE(EXCLUDED.resume_cli, {TABLE_NAME}.resume_cli),
                  cwd=COALESCE(EXCLUDED.cwd, {TABLE_NAME}.cwd),
                  source=COALESCE(EXCLUDED.source, {TABLE_NAME}.source),
                  updated_at=EXCLUDED.updated_at
            """
        else:
            sql = f"""
                INSERT INTO {TABLE_NAME}
                  (session_id, tool, model, branch, resume_shell, resume_cli,
                   cwd, source, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                  tool=COALESCE(VALUES(tool), tool),
                  model=COALESCE(VALUES(model), model),
                  branch=COALESCE(VALUES(branch), branch),
                  resume_shell=COALESCE(VALUES(resume_shell), resume_shell),
                  resume_cli=COALESCE(VALUES(resume_cli), resume_cli),
                  cwd=COALESCE(VALUES(cwd), cwd),
                  source=COALESCE(VALUES(source), source),
                  updated_at=VALUES(updated_at)
            """
        conn = self._connect()
        cursor = conn.cursor()
        try:
            cursor.execute(sql, values)
            conn.commit()
            return True
        finally:
            cursor.close()
            conn.close()

    def update_progress(
        self,
        session_id: str,
        task_dir: str | None = None,
        completed_tasks: Any = None,
        progress: str | None = None,
        branch: str | None = None,
    ) -> bool:
        if not session_id:
            return False
        self.ensure()
        ts = now_str()
        conn = self._connect()
        cursor = conn.cursor()
        try:
            if self.name == "postgresql":
                cursor.execute(
                    f"INSERT INTO {TABLE_NAME} (session_id, created_at, updated_at) "
                    "VALUES (%s,%s,%s) ON CONFLICT(session_id) DO NOTHING",
                    (session_id, ts, ts),
                )
            else:
                cursor.execute(
                    f"INSERT IGNORE INTO {TABLE_NAME} "
                    "(session_id, created_at, updated_at) VALUES (%s,%s,%s)",
                    (session_id, ts, ts),
                )
            sets: list[str] = []
            params: list[Any] = []
            if task_dir is not None:
                sets.append("task_dir=%s")
                params.append(normalize_task_dir(task_dir))
            if completed_tasks is not None:
                cursor.execute(
                    f"SELECT completed_tasks, feature FROM {TABLE_NAME} WHERE session_id=%s",
                    (session_id,),
                )
                row = cursor.fetchone()
                existing = (row[0] or row[1]) if row else None
                merged = merge_completed_tasks(existing, completed_tasks)
                incoming_tasks = parse_completed_tasks(completed_tasks)
                legacy_feature = incoming_tasks[-1] if incoming_tasks else None
                sets.extend(("completed_tasks=%s", "feature=%s"))
                params.extend((merged, legacy_feature))
            if progress is not None:
                sets.append("progress=%s")
                params.append(progress)
            effective_branch = branch or detect_git_branch()
            if effective_branch is not None:
                sets.append("branch=%s")
                params.append(effective_branch)
            sets.append("updated_at=%s")
            params.extend((ts, session_id))
            cursor.execute(
                f"UPDATE {TABLE_NAME} SET {', '.join(sets)} WHERE session_id=%s",
                params,
            )
            conn.commit()
            return True
        finally:
            cursor.close()
            conn.close()

    def query(
        self,
        task_dir: str | None = None,
        keyword: str | None = None,
    ) -> list[dict[str, Any]]:
        self.ensure()
        conn = self._connect()
        cursor = conn.cursor()
        try:
            if task_dir:
                cursor.execute(
                    f"SELECT * FROM {TABLE_NAME} "
                    "WHERE LOWER(task_dir)=LOWER(%s) ORDER BY updated_at DESC",
                    (normalize_task_dir(task_dir),),
                )
            elif keyword:
                like = f"%{keyword.lower()}%"
                cursor.execute(
                    f"""
                    SELECT * FROM {TABLE_NAME}
                    WHERE LOWER(COALESCE(task_dir,'')) LIKE %s
                       OR LOWER(COALESCE(completed_tasks,'')) LIKE %s
                       OR LOWER(COALESCE(feature,'')) LIKE %s
                       OR LOWER(COALESCE(cwd,'')) LIKE %s
                       OR LOWER(COALESCE(branch,'')) LIKE %s
                       OR LOWER(COALESCE(source,'')) LIKE %s
                       OR LOWER(COALESCE(session_id,'')) LIKE %s
                    ORDER BY updated_at DESC
                    """,
                    (like, like, like, like, like, like, like),
                )
            else:
                cursor.execute(f"SELECT * FROM {TABLE_NAME} ORDER BY updated_at DESC")
            return _row_dicts(cursor)
        finally:
            cursor.close()
            conn.close()


def load_remote_config(config_path: str) -> dict[str, Any]:
    """读取远程登记配置（含 JSON 内 password 字段）。"""
    with open(config_path, "r", encoding="utf-8") as handle:
        config = json.load(handle)
    if not isinstance(config, dict):
        raise ValueError("远程登记配置必须是 JSON 对象")
    return config


def remote_fallback_errors() -> tuple[type[BaseException], ...]:
    """可降级 SQLite 的异常：配置/环境/连接错误与已加载 DB 驱动的 Error 基类。

    刻意不含 AttributeError/TypeError 等编程错误，避免把代码 bug 吞成降级。
    """
    errors: list[type[BaseException]] = [RuntimeError, ValueError, OSError]
    for module_name in ("psycopg", "psycopg2", "pymysql", "mysql.connector"):
        module = sys.modules.get(module_name)
        error = getattr(module, "Error", None)
        if isinstance(error, type) and issubclass(error, BaseException):
            errors.append(error)
    return tuple(errors)


def resolve_registry(
    cwd: str | None = None,
    config_path: str | None = None,
    db_path: str | None = None,
) -> SQLiteRegistry | RemoteRegistry:
    """选择远程登记；无可用远程后端时返回项目 SQLite。"""
    if db_path:
        registry = SQLiteRegistry(db_path)
        registry.ensure()
        return registry
    sqlite_registry = SQLiteRegistry(default_db_path(cwd))
    config = config_path or default_config_path(cwd)
    if not os.path.isfile(config):
        sqlite_registry.ensure()
        return sqlite_registry
    try:
        remote = RemoteRegistry(load_remote_config(config))
        remote.ensure()
        return remote
    except remote_fallback_errors() as exc:  # 远程不可用时必须保留项目级登记能力
        print(
            f"AI register remote backend unavailable; fallback to SQLite: {exc}",
            file=sys.stderr,
        )
        sqlite_registry.ensure()
        return sqlite_registry


def ensure_db(db_path: str) -> sqlite3.Connection:
    """兼容旧调用：确保 SQLite schema 后返回连接。"""
    registry = SQLiteRegistry(db_path)
    registry.ensure()
    return registry._connect()


def upsert_identity(
    db_path: str,
    session_id: str,
    tool: str | None = None,
    model: str | None = None,
    cwd: str | None = None,
    source: str | None = None,
    branch: str | None = None,
) -> bool:
    """兼容旧 API：直接写项目 SQLite 身份字段。"""
    return SQLiteRegistry(db_path).upsert_identity(
        session_id,
        tool=tool,
        model=model,
        cwd=cwd,
        source=source,
        branch=branch,
    )


def update_progress(
    db_path: str,
    session_id: str,
    task_dir: str | None = None,
    feature: str | None = None,
    progress: str | None = None,
    completed_tasks: Any = None,
    branch: str | None = None,
) -> bool:
    """兼容旧 API；feature 作为 completed_tasks 的旧别名。"""
    incoming = completed_tasks if completed_tasks is not None else feature
    return SQLiteRegistry(db_path).update_progress(
        session_id,
        task_dir=task_dir,
        completed_tasks=incoming,
        progress=progress,
        branch=branch,
    )


def query_rows(
    db_path: str,
    task_dir: str | None = None,
    keyword: str | None = None,
) -> list[dict[str, Any]]:
    """兼容旧 API：查询指定项目 SQLite。"""
    return SQLiteRegistry(db_path).query(task_dir=task_dir, keyword=keyword)


def render_table(rows: list[dict[str, Any]]) -> str:
    """把登记结果渲染为可读表格。"""
    if not rows:
        return "（登记库为空或不存在）"
    cols = [
        ("tool", "工具"),
        ("model", "模型"),
        ("session_id", "sessionId"),
        ("branch", "分支"),
        ("progress", "进度"),
        ("completed_tasks", "已完成任务"),
        ("task_dir", "任务目录"),
        ("resume_shell", "resume(shell)"),
        ("updated_at", "更新时间"),
    ]

    def cell(row: dict[str, Any], key: str) -> str:
        value = row.get(key)
        if key == "completed_tasks":
            value = "；".join(parse_completed_tasks(value or row.get("feature")))
        text = "" if value is None else str(value)
        if key == "session_id" and len(text) > 12:
            text = text[:12]
        return text

    headers = [label for _, label in cols]
    table = [headers] + [[cell(row, key) for key, _ in cols] for row in rows]
    widths = [max(len(row[index]) for row in table) for index in range(len(cols))]

    def fmt(row: list[str]) -> str:
        return "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))

    separator = "  ".join("-" * width for width in widths)
    return "\n".join([fmt(table[0]), separator] + [fmt(row) for row in table[1:]])


def _add_backend_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", help="显式指定 SQLite 路径并跳过远程后端")
    parser.add_argument("--config", help="远程登记 JSON 配置路径")
    parser.add_argument("--cwd", help="用于定位 Git 根、配置和 SQLite 的工作目录")


def _add_progress_args(parser: argparse.ArgumentParser, require_task_dir: bool = False) -> None:
    parser.add_argument("--session", required=True)
    parser.add_argument("--task-dir", required=require_task_dir)
    parser.add_argument(
        "--completed-task",
        action="append",
        default=[],
        help="追加一个已完成任务；可重复传入",
    )
    parser.add_argument("--feature", help="兼容旧调用：等价于一个 --completed-task")
    parser.add_argument("--progress")
    parser.add_argument("--branch")
    _add_backend_args(parser)


def _build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI 登记核心 CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    upsert = sub.add_parser("upsert", help="写入或更新会话身份")
    upsert.add_argument("--session", required=True)
    upsert.add_argument("--tool")
    upsert.add_argument("--model")
    upsert.add_argument("--branch")
    upsert.add_argument("--source")
    _add_backend_args(upsert)

    progress = sub.add_parser("progress", help="回填目录、完成任务和进度")
    _add_progress_args(progress)

    close = sub.add_parser("close", help="关闭 SDLC 时同步最终登记进度")
    _add_progress_args(close, require_task_dir=True)

    query = sub.add_parser("query", help="查询当前可用登记后端")
    query.add_argument("--task-dir")
    query.add_argument("--keyword", help="按目录、任务、分支或会话模糊查询")
    _add_backend_args(query)
    return parser


def _run_with_fallback(
    args: argparse.Namespace,
    operation: Callable[[SQLiteRegistry | RemoteRegistry], Any],
) -> tuple[Any, SQLiteRegistry | RemoteRegistry]:
    registry = resolve_registry(
        cwd=getattr(args, "cwd", None),
        config_path=getattr(args, "config", None),
        db_path=getattr(args, "db", None),
    )
    try:
        return operation(registry), registry
    except remote_fallback_errors() as exc:
        if isinstance(registry, SQLiteRegistry):
            raise
        print(
            f"AI register remote operation failed; fallback to SQLite: {exc}",
            file=sys.stderr,
        )
        fallback = SQLiteRegistry(
            getattr(args, "db", None) or default_db_path(getattr(args, "cwd", None))
        )
        fallback.ensure()
        return operation(fallback), fallback


def _completed_tasks_from_args(args: argparse.Namespace) -> list[str]:
    tasks = list(getattr(args, "completed_task", []) or [])
    feature = getattr(args, "feature", None)
    if feature:
        tasks.append(feature)
    return tasks


def main(argv: list[str] | None = None) -> int:
    args = _build_cli().parse_args(argv)

    if args.cmd == "upsert":
        result, registry = _run_with_fallback(
            args,
            lambda store: store.upsert_identity(
                args.session,
                tool=args.tool,
                model=args.model,
                cwd=args.cwd,
                source=args.source,
                branch=args.branch,
            ),
        )
        print(f"backend={registry.name}", file=sys.stderr)
        return 0 if result else 1

    if args.cmd in {"progress", "close"}:
        tasks = _completed_tasks_from_args(args)
        progress = args.progress or ("100%" if args.cmd == "close" else None)
        result, registry = _run_with_fallback(
            args,
            lambda store: store.update_progress(
                args.session,
                task_dir=args.task_dir,
                completed_tasks=tasks or None,
                progress=progress,
                branch=args.branch,
            ),
        )
        print(f"backend={registry.name}", file=sys.stderr)
        return 0 if result else 1

    if args.cmd == "query":
        rows, registry = _run_with_fallback(
            args,
            lambda store: store.query(task_dir=args.task_dir, keyword=args.keyword),
        )
        print(f"backend={registry.name}", file=sys.stderr)
        print(render_table(rows))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
