#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SDLC 任务状态核心。

``onlyAI/task-state.json`` 是机器事实源，``status.md`` 是面向人的投影。
脚本只使用 Python 标准库，负责状态门禁、原子写入、关闭二次确认和兼容迁移。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator


SCHEMA_VERSION = 3
STATE_RELPATH = Path("onlyAI") / "task-state.json"
LOCK_RELPATH = Path("onlyAI") / ".task-state.lock"
LOCK_STALE_SECONDS = 60.0

WORKFLOWS = {"standard", "debug", "script"}

PHASES = {
    "design-1",
    "design-2",
    "implement",
    "test",
    "debug",
    "script",
    "close",
    "done",
}
STATES = {
    "in_progress",
    "awaiting_confirmation",
    "blocked",
    "investigating",
    "root_cause_confirmed",
    "reviewing",
    "fixing",
    "awaiting_verification",
    "awaiting_approval",
    "executing",
    "verified",
    "rolled_back",
    "completed",
    "awaiting_close",
    "closed",
}
DOCUMENT_STATES = {
    "draft",
    "reviewing",
    "ready",
    "final",
    "complete",
}
TEST_STATES = {
    "not_started",
    "running",
    "passed",
    "conditional",
    "failed",
    "skipped_confirmed",
    "unknown",
}
CLOSE_STATES = {"open", "awaiting_test_confirmation", "ready", "closed"}
REVIEW_STATUSES = {"not_required", "pending", "in_progress", "completed"}
SCRIPT_RISKS = {"low", "medium", "high", "unknown"}
SCRIPT_ENVIRONMENTS = {"local", "test", "staging", "production", "unknown"}

CLOSE_ARTIFACT_STATUSES = {
    "summary": {"pending", "completed"},
    "registration": {"pending", "synced", "skipped", "failed"},
    "knowledge": {"pending", "local_only", "synced", "failed"},
}

PHASE_STATE_TRANSITIONS = {
    "design-1": {
        "in_progress": {"reviewing", "awaiting_confirmation", "blocked"},
        "reviewing": {"in_progress", "awaiting_confirmation", "blocked"},
        "awaiting_confirmation": {"in_progress", "reviewing", "blocked"},
        "blocked": {"in_progress", "reviewing", "awaiting_confirmation"},
    },
    "design-2": {
        "in_progress": {"reviewing", "awaiting_confirmation", "blocked"},
        "reviewing": {"in_progress", "awaiting_confirmation", "blocked"},
        "awaiting_confirmation": {"in_progress", "reviewing", "blocked"},
        "blocked": {"in_progress", "reviewing", "awaiting_confirmation"},
    },
    "implement": {
        "in_progress": {"reviewing", "awaiting_confirmation", "blocked"},
        "reviewing": {"in_progress", "awaiting_confirmation", "blocked"},
        "awaiting_confirmation": {"in_progress", "reviewing", "blocked"},
        "blocked": {"in_progress", "reviewing", "awaiting_confirmation"},
    },
    "test": {
        "in_progress": {"blocked"},
        "blocked": {"in_progress"},
    },
    "debug": {
        "investigating": {"root_cause_confirmed", "blocked"},
        "root_cause_confirmed": {"reviewing", "fixing", "blocked"},
        "reviewing": {"fixing", "blocked"},
        "fixing": {"awaiting_verification", "blocked"},
        "awaiting_verification": {"verified", "blocked"},
        "blocked": {
            "investigating",
            "root_cause_confirmed",
            "reviewing",
            "fixing",
            "awaiting_verification",
        },
    },
    "script": {
        "in_progress": {"reviewing", "awaiting_approval", "executing", "blocked"},
        "reviewing": {"awaiting_approval", "executing", "blocked"},
        "awaiting_approval": {"executing", "blocked"},
        "executing": {"verified", "rolled_back", "blocked"},
        "blocked": {"in_progress", "reviewing", "awaiting_approval", "executing"},
    },
}

DOCUMENT_UNRESOLVED_STATES = {
    "design-1": {"草稿", "评审中", "待决策", "阻塞"},
    "design-2": {"草稿", "评审中", "待决策", "阻塞"},
    "implement": {
        "草稿",
        "评审中",
        "可施工",
        "待确认",
        "待决策",
        "未开始",
        "进行中",
        "阻塞",
        "回退",
        "待处理",
    },
    "test": {"草稿", "评审中", "待执行", "失败", "未通过", "阻塞", "Open", "开放"},
    "debug": {"草稿", "评审中", "待验证", "待决策", "阻塞"},
    "script": {"草稿", "评审中", "待确认", "待决策", "待执行", "待批准", "阻塞"},
}

PHASE_PROGRESS = {
    "design-1": 10,
    "design-2": 30,
    "implement": 50,
    "test": 80,
    "debug": 10,
    "script": 10,
}
PHASE_COMPLETED_PROGRESS = {
    "design-1": 25,
    "design-2": 45,
    "implement": 75,
    "debug": 90,
    "script": 90,
}

STATE_LABELS = {
    "in_progress": "进行中",
    "awaiting_confirmation": "待确认",
    "blocked": "阻塞",
    "investigating": "排查中",
    "root_cause_confirmed": "根因已确认",
    "reviewing": "评审中",
    "fixing": "修复中",
    "awaiting_verification": "待验证",
    "awaiting_approval": "待批准",
    "executing": "执行中",
    "verified": "已验证",
    "rolled_back": "已回滚",
    "completed": "已完成",
    "awaiting_close": "待关闭",
    "closed": "已关闭",
}
DOCUMENT_LABELS = {
    "draft": "草稿",
    "reviewing": "评审中",
    "ready": "可施工",
    "final": "已定稿",
    "complete": "已完成",
}
REVERSE_STATE_LABELS = {value: key for key, value in STATE_LABELS.items()}
REVERSE_DOCUMENT_LABELS = {value: key for key, value in DOCUMENT_LABELS.items()}


class TaskStateError(RuntimeError):
    """任务状态不满足命令约束。"""


def now_iso() -> str:
    """返回带时区的本地 ISO 时间。"""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def new_review(required: bool = False) -> dict[str, Any]:
    """创建阶段评审状态。"""
    return {
        "required": required,
        "status": "pending" if required else "not_required",
        "evidence": [],
        "updated_at": None,
    }


def new_script_context(
    risk: str | None = None, environment: str | None = None
) -> dict[str, Any]:
    """创建 Script 风险、批准与结果状态。"""
    effective_risk = risk or "unknown"
    effective_environment = environment or "unknown"
    approval_required = effective_environment == "production"
    return {
        "risk": effective_risk,
        "environment": effective_environment,
        "approval": {
            "required": approval_required,
            "approved": False,
            "evidence": [],
            "approved_at": None,
        },
        "outcome": None,
    }


def new_close_state() -> dict[str, Any]:
    """创建 Close 状态及必须留痕的收口结果。"""
    return {
        "state": "open",
        "confirmation": None,
        "closed_at": None,
        "artifacts": {
            name: {"status": "pending", "evidence": [], "updated_at": None}
            for name in CLOSE_ARTIFACT_STATUSES
        },
    }


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        timeout=15,
        check=False,
    )


def find_git_root(cwd: Path) -> Path | None:
    """返回 Git 根目录；非 Git 项目返回 None。"""
    try:
        result = _run_git(["rev-parse", "--show-toplevel"], cwd)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return Path(result.stdout.decode("utf-8", errors="replace").strip()).resolve()


def detect_branch(cwd: Path) -> str | None:
    root = find_git_root(cwd)
    if root is None:
        return None
    result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], root)
    branch = result.stdout.decode("utf-8", errors="replace").strip()
    if result.returncode != 0 or not branch or branch == "HEAD":
        return None
    return branch


def working_tree_fingerprint(task_dir: Path) -> str:
    """计算 Git HEAD、已跟踪差异和未跟踪内容的指纹。

    关闭请求自身会更新 ``status.md`` 与 ``task-state.json``，因此排除这两个文件。
    """
    root = find_git_root(task_dir)
    if root is None:
        raise TaskStateError("未执行测试的二次确认需要 Git 仓库以绑定当前实现版本")

    excluded = {
        (task_dir / "status.md").resolve(),
        (task_dir / STATE_RELPATH).resolve(),
    }
    digest = hashlib.sha256()
    head = _run_git(["rev-parse", "HEAD"], root)
    if head.returncode != 0:
        raise TaskStateError("无法读取 Git HEAD，不能生成关闭确认指纹")
    digest.update(head.stdout)

    relative_task_dir = task_dir.resolve().relative_to(root).as_posix()
    excluded_pathspecs = [
        f":(top,literal,exclude){relative_task_dir}/status.md",
        f":(top,literal,exclude){relative_task_dir}/{STATE_RELPATH.as_posix()}",
    ]
    diff = _run_git(["diff", "--binary", "HEAD", "--", ".", *excluded_pathspecs], root)
    if diff.returncode != 0:
        raise TaskStateError("无法读取 Git 工作树差异，不能生成关闭确认指纹")
    digest.update(diff.stdout)

    untracked = _run_git(["ls-files", "--others", "--exclude-standard", "-z"], root)
    if untracked.returncode != 0:
        raise TaskStateError("无法读取未跟踪文件，不能生成关闭确认指纹")
    for raw_path in sorted(item for item in untracked.stdout.split(b"\0") if item):
        relative = raw_path.decode("utf-8", errors="surrogateescape")
        path = (root / relative).resolve()
        if path in excluded or not path.is_file():
            continue
        digest.update(relative.encode("utf-8", errors="surrogateescape"))
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def validate_state(state: dict[str, Any]) -> list[str]:
    """执行零依赖结构校验并返回错误列表。"""
    errors: list[str] = []
    required = {
        "schema_version",
        "task_id",
        "system",
        "title",
        "task_dir",
        "workflow",
        "phase",
        "state",
        "document_state",
        "progress",
        "open_items",
        "blockers",
        "phase_evidence",
        "execution",
        "test",
        "review",
        "close",
        "debug_mode",
        "script",
        "branch",
        "return_phase",
        "return_context",
        "debug_outcome",
        "revision",
        "created_at",
        "updated_at",
        "migration",
    }
    missing = sorted(required - state.keys())
    if missing:
        errors.append(f"缺少字段：{', '.join(missing)}")
        return errors
    if state["schema_version"] != SCHEMA_VERSION:
        errors.append(f"不支持的 schema_version：{state['schema_version']}")
    for name in ("task_id", "system", "title", "task_dir", "created_at", "updated_at"):
        if not isinstance(state[name], str) or not state[name].strip():
            errors.append(f"{name} 必须是非空字符串")
    if not isinstance(state["workflow"], str) or state["workflow"] not in WORKFLOWS:
        errors.append(f"非法 workflow：{state['workflow']}")
    if not isinstance(state["phase"], str) or state["phase"] not in PHASES:
        errors.append(f"非法 phase：{state['phase']}")
    if not isinstance(state["state"], str) or state["state"] not in STATES:
        errors.append(f"非法 state：{state['state']}")
    if (
        not isinstance(state["document_state"], str)
        or state["document_state"] not in DOCUMENT_STATES
    ):
        errors.append(f"非法 document_state：{state['document_state']}")
    if (
        not isinstance(state["progress"], int)
        or isinstance(state["progress"], bool)
        or not 0 <= state["progress"] <= 100
    ):
        errors.append("progress 必须是 0~100 的整数")
    if (
        not isinstance(state["open_items"], int)
        or isinstance(state["open_items"], bool)
        or state["open_items"] < 0
    ):
        errors.append("open_items 必须是非负整数")
    if not isinstance(state["blockers"], list) or any(
        not isinstance(item, str) for item in state["blockers"]
    ):
        errors.append("blockers 必须是字符串数组")
    elif len(state["blockers"]) != len(set(state["blockers"])):
        errors.append("blockers 不能包含重复项")
    elif state["blockers"] and state["state"] != "blocked":
        errors.append("存在 blockers 时 state 必须为 blocked")
    if not isinstance(state["phase_evidence"], list) or any(
        not isinstance(item, str) for item in state["phase_evidence"]
    ):
        errors.append("phase_evidence 必须是字符串数组")
    execution = state.get("execution", {})
    if not isinstance(execution, dict):
        errors.append("execution 必须是对象")
    else:
        tasks = execution.get("tasks")
        completed_task_ids = execution.get("completed_task_ids")
        if not isinstance(tasks, dict):
            errors.append("execution.tasks 必须是对象")
        else:
            expected_completed: list[str] = []
            for task_id, item in tasks.items():
                if not isinstance(task_id, str) or not task_id:
                    errors.append("execution.tasks 的键必须是非空字符串")
                    continue
                if not isinstance(item, dict):
                    errors.append(f"施工任务 {task_id} 必须是对象")
                    continue
                status = item.get("status")
                evidence = item.get("evidence")
                if not isinstance(status, str) or status not in {
                    "planned",
                    "in_progress",
                    "completed",
                    "blocked",
                }:
                    errors.append(f"施工任务 {task_id} 状态非法：{status}")
                if not isinstance(evidence, list) or any(
                    not isinstance(value, str) for value in evidence
                ):
                    errors.append(f"施工任务 {task_id} evidence 必须是字符串数组")
                elif status == "completed" and not evidence:
                    errors.append(f"施工任务 {task_id} completed 时必须有验证证据")
                if status == "completed":
                    expected_completed.append(task_id)
        if not isinstance(completed_task_ids, list) or any(
            not isinstance(item, str) for item in completed_task_ids
        ):
            errors.append("execution.completed_task_ids 必须是字符串数组")
        elif isinstance(tasks, dict) and sorted(completed_task_ids) != sorted(
            expected_completed
        ):
            errors.append("execution.completed_task_ids 与 tasks 完成状态不一致")
        next_task_id = execution.get("next_task_id")
        if next_task_id is not None and not isinstance(next_task_id, str):
            errors.append("execution.next_task_id 必须是字符串或 null")
    test = state.get("test", {})
    if not isinstance(test, dict):
        errors.append("test 必须是对象")
    else:
        test_state = test.get("state")
        evidence = test.get("evidence")
        if not isinstance(test_state, str) or test_state not in TEST_STATES:
            errors.append(f"非法 test.state：{test_state}")
        if not isinstance(evidence, list) or any(
            not isinstance(value, str) for value in evidence
        ):
            errors.append("test.evidence 必须是字符串数组")
        elif test_state in {"passed", "conditional"} and not evidence:
            errors.append(f"test.state={test_state} 时必须有验证证据")
        if not isinstance(test.get("risk_accepted"), bool):
            errors.append("test.risk_accepted 必须是布尔值")
        elif test_state == "conditional" and not test["risk_accepted"]:
            errors.append("test.state=conditional 时必须明确接受遗留风险")
        elif test_state == "skipped_confirmed" and not test["risk_accepted"]:
            errors.append("test.state=skipped_confirmed 时必须记录风险已接受")
    review = state.get("review", {})
    if not isinstance(review, dict):
        errors.append("review 必须是对象")
    else:
        if not isinstance(review.get("required"), bool):
            errors.append("review.required 必须是布尔值")
        review_status = review.get("status")
        if review_status not in REVIEW_STATUSES:
            errors.append(f"非法 review.status：{review_status}")
        review_evidence = review.get("evidence")
        if not isinstance(review_evidence, list) or any(
            not isinstance(value, str) for value in review_evidence
        ):
            errors.append("review.evidence 必须是字符串数组")
        elif review_status == "completed" and not review_evidence:
            errors.append("review.status=completed 时必须有证据")
        if review.get("required") and review_status == "not_required":
            errors.append("必需评审不能标记为 not_required")
        if not review.get("required") and review_status in {"pending", "in_progress"}:
            errors.append("非必需评审不能处于 pending/in_progress")
        if state.get("phase") == "implement" and not review.get("required"):
            errors.append("Implement 阶段必须要求 Grill/评审")
    close = state.get("close", {})
    if not isinstance(close, dict):
        errors.append("close 必须是对象")
    else:
        close_state = close.get("state")
        if not isinstance(close_state, str) or close_state not in CLOSE_STATES:
            errors.append(f"非法 close.state：{close_state}")
        confirmation = close.get("confirmation")
        if confirmation is not None and not isinstance(confirmation, dict):
            errors.append("close.confirmation 必须是对象或 null")
        if close_state == "awaiting_test_confirmation" and not isinstance(
            confirmation, dict
        ):
            errors.append("等待未测试确认时必须存在 close.confirmation")
        elif close_state == "awaiting_test_confirmation":
            confirmation_required = {
                "token_hash",
                "working_tree_fingerprint",
                "state_revision",
                "requested_at",
                "confirmed_at",
            }
            missing_confirmation = sorted(confirmation_required - confirmation.keys())
            if missing_confirmation:
                errors.append(
                    "close.confirmation 缺少字段：" + ", ".join(missing_confirmation)
                )
            if state["state"] != "awaiting_confirmation":
                errors.append("等待未测试确认时 state 必须为 awaiting_confirmation")
        if close_state == "ready" and state["phase"] != "close":
            errors.append("close.state=ready 时 phase 必须为 close")
        if close.get("closed_at") is not None and not isinstance(
            close.get("closed_at"), str
        ):
            errors.append("close.closed_at 必须是字符串或 null")
        artifacts = close.get("artifacts")
        if not isinstance(artifacts, dict):
            errors.append("close.artifacts 必须是对象")
        else:
            for name, allowed_statuses in CLOSE_ARTIFACT_STATUSES.items():
                artifact = artifacts.get(name)
                if not isinstance(artifact, dict):
                    errors.append(f"close.artifacts.{name} 必须是对象")
                    continue
                artifact_status = artifact.get("status")
                if artifact_status not in allowed_statuses:
                    errors.append(
                        f"非法 close.artifacts.{name}.status：{artifact_status}"
                    )
                artifact_evidence = artifact.get("evidence")
                if not isinstance(artifact_evidence, list) or any(
                    not isinstance(value, str) for value in artifact_evidence
                ):
                    errors.append(f"close.artifacts.{name}.evidence 必须是字符串数组")
                elif artifact_status != "pending" and not artifact_evidence:
                    errors.append(f"close.artifacts.{name} 终态必须有证据")
            if close_state == "closed" and any(
                artifact.get("status") == "pending"
                for artifact in artifacts.values()
                if isinstance(artifact, dict)
            ):
                errors.append("关闭完成时所有 close artifacts 必须有终态")
    debug_mode = state.get("debug_mode")
    if debug_mode not in {None, "diagnose", "fix", "unknown"}:
        errors.append("debug_mode 必须是 diagnose、fix、unknown 或 null")
    script = state.get("script", {})
    if not isinstance(script, dict):
        errors.append("script 必须是对象")
    else:
        if script.get("risk") not in SCRIPT_RISKS:
            errors.append(f"非法 script.risk：{script.get('risk')}")
        if script.get("environment") not in SCRIPT_ENVIRONMENTS:
            errors.append(f"非法 script.environment：{script.get('environment')}")
        approval = script.get("approval")
        if not isinstance(approval, dict):
            errors.append("script.approval 必须是对象")
        else:
            if not isinstance(approval.get("required"), bool):
                errors.append("script.approval.required 必须是布尔值")
            if not isinstance(approval.get("approved"), bool):
                errors.append("script.approval.approved 必须是布尔值")
            approval_evidence = approval.get("evidence")
            if not isinstance(approval_evidence, list) or any(
                not isinstance(value, str) for value in approval_evidence
            ):
                errors.append("script.approval.evidence 必须是字符串数组")
            elif approval.get("approved") and not approval_evidence:
                errors.append("生产执行批准必须有证据")
            if approval.get("approved") and not approval.get("required"):
                errors.append("非生产 Script 不应记录生产执行批准")
            expected_approval = script.get("environment") == "production"
            if approval.get("required") != expected_approval:
                errors.append("script.approval.required 必须与生产环境一致")
        if script.get("outcome") not in {None, "verified", "rolled_back"}:
            errors.append("script.outcome 必须是 verified、rolled_back 或 null")
        if (
            state.get("workflow") == "script"
            and script.get("risk") in {"medium", "high"}
            and isinstance(review, dict)
            and not review.get("required")
        ):
            errors.append("中高风险 Script 必须要求 Grill/评审")
    if state["branch"] is not None and not isinstance(state["branch"], str):
        errors.append("branch 必须是字符串或 null")
    if state["return_phase"] is not None and (
        not isinstance(state["return_phase"], str)
        or state["return_phase"] not in PHASES
    ):
        errors.append("return_phase 必须是合法阶段或 null")
    if state["return_context"] is not None and not isinstance(
        state["return_context"], dict
    ):
        errors.append("return_context 必须是对象或 null")
    elif isinstance(state["return_context"], dict):
        context = state["return_context"]
        context_required = {
            "phase",
            "state",
            "document_state",
            "progress",
            "open_items",
            "blockers",
            "phase_evidence",
            "review",
        }
        missing_context = sorted(context_required - context.keys())
        if missing_context:
            errors.append("return_context 缺少字段：" + ", ".join(missing_context))
        else:
            if not isinstance(context["phase"], str) or context["phase"] not in PHASES:
                errors.append("return_context.phase 非法")
            if not isinstance(context["state"], str) or context["state"] not in STATES:
                errors.append("return_context.state 非法")
            if (
                not isinstance(context["document_state"], str)
                or context["document_state"] not in DOCUMENT_STATES
            ):
                errors.append("return_context.document_state 非法")
            if (
                not isinstance(context["progress"], int)
                or isinstance(context["progress"], bool)
                or not 0 <= context["progress"] <= 100
            ):
                errors.append("return_context.progress 必须是 0~100 的整数")
            if (
                not isinstance(context["open_items"], int)
                or isinstance(context["open_items"], bool)
                or context["open_items"] < 0
            ):
                errors.append("return_context.open_items 必须是非负整数")
            if not isinstance(context["blockers"], list) or any(
                not isinstance(item, str) for item in context["blockers"]
            ):
                errors.append("return_context.blockers 必须是字符串数组")
            if not isinstance(context["phase_evidence"], list) or any(
                not isinstance(item, str) for item in context["phase_evidence"]
            ):
                errors.append("return_context.phase_evidence 必须是字符串数组")
            context_review = context["review"]
            if not isinstance(context_review, dict):
                errors.append("return_context.review 必须是对象")
            else:
                if not isinstance(context_review.get("required"), bool):
                    errors.append("return_context.review.required 必须是布尔值")
                if context_review.get("status") not in REVIEW_STATUSES:
                    errors.append("return_context.review.status 非法")
                context_review_evidence = context_review.get("evidence")
                if not isinstance(context_review_evidence, list) or any(
                    not isinstance(item, str) for item in context_review_evidence
                ):
                    errors.append(
                        "return_context.review.evidence 必须是字符串数组"
                    )
            if state["return_phase"] != context["phase"]:
                errors.append("return_phase 与 return_context.phase 不一致")
            if state["phase"] != "debug":
                errors.append("return_context 只能在 debug 阶段存在")
    if state["return_phase"] is not None and state["return_context"] is None:
        errors.append("return_phase 存在时必须同时保存 return_context")
    if state["debug_outcome"] not in {None, "diagnosed", "verified"}:
        errors.append("debug_outcome 必须是 diagnosed、verified 或 null")
    if state["migration"] is not None and not isinstance(state["migration"], dict):
        errors.append("migration 必须是对象或 null")
    if (
        not isinstance(state["revision"], int)
        or isinstance(state["revision"], bool)
        or state["revision"] < 1
    ):
        errors.append("revision 必须是正整数")
    close_state_value = close.get("state") if isinstance(close, dict) else None
    if state["phase"] == "close" and close_state_value != "ready":
        migration_pending = isinstance(state["migration"], dict) and state[
            "migration"
        ].get("requires_review")
        if not migration_pending:
            errors.append("phase=close 时 close.state 必须为 ready")
    if state["phase"] == "done":
        if (
            state["state"] != "closed"
            or close_state_value != "closed"
            or state["progress"] != 100
        ):
            errors.append("phase=done 时必须为 closed / 100%")
    if close_state_value == "closed" and state["phase"] != "done":
        errors.append("close.state=closed 时 phase 必须为 done")
    workflow_phases = {
        "standard": {"design-1", "design-2", "implement", "test", "debug", "close", "done"},
        "debug": {"debug", "close", "done"},
        "script": {"script", "close", "done"},
    }
    if (
        state.get("workflow") in workflow_phases
        and state.get("phase") not in workflow_phases[state["workflow"]]
    ):
        errors.append(
            f"workflow={state['workflow']} 不允许 phase={state.get('phase')}"
        )
    return errors


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


class TaskStateStore:
    """维护单个任务目录的机器状态与人类状态投影。"""

    def __init__(self, task_dir: str | os.PathLike[str]):
        self.task_dir = Path(task_dir).resolve()
        self.state_path = self.task_dir / STATE_RELPATH
        self.status_path = self.task_dir / "status.md"
        self.lock_path = self.task_dir / LOCK_RELPATH

    @contextmanager
    def lock(self, timeout: float = 10.0) -> Iterator[None]:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + timeout
        while True:
            try:
                descriptor = os.open(
                    self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                )
            except FileExistsError:
                # 持锁操作均为亚秒级文件读写；超龄锁视为崩溃残留，回收后重试
                try:
                    lock_age = time.time() - self.lock_path.stat().st_mtime
                except OSError:
                    lock_age = 0.0
                if lock_age > LOCK_STALE_SECONDS:
                    try:
                        self.lock_path.unlink()
                    except OSError:
                        pass
                    continue
                if time.monotonic() >= deadline:
                    raise TaskStateError(
                        f"任务状态正被其他会话更新：{self.lock_path}；"
                        "若确认没有其他会话在运行，可手动删除该锁文件后重试"
                    )
                time.sleep(0.05)
            else:
                os.close(descriptor)
                break
        try:
            yield
        finally:
            try:
                self.lock_path.unlink()
            except FileNotFoundError:
                pass

    def load(self) -> dict[str, Any]:
        if not self.state_path.is_file():
            raise TaskStateError(
                f"任务状态不存在：{self.state_path}；请先运行 init 或 migrate"
            )
        try:
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise TaskStateError(f"无法读取任务状态：{exc}") from exc
        if not isinstance(state, dict):
            raise TaskStateError("task-state.json 顶层必须是对象")
        state = self._upgrade_state(state)
        errors = validate_state(state)
        if errors:
            raise TaskStateError("；".join(errors))
        return state

    def initialize(
        self,
        *,
        system: str,
        title: str,
        phase: str = "design-1",
        branch: str | None = None,
        debug_mode: str | None = None,
        script_risk: str | None = None,
        script_environment: str | None = None,
    ) -> dict[str, Any]:
        if phase not in {"design-1", "debug", "script"}:
            raise TaskStateError("新任务只能从 design-1、debug 或 script 初始化")
        if phase == "debug" and debug_mode not in {"diagnose", "fix"}:
            raise TaskStateError("Debug 初始化必须指定 debug_mode=diagnose 或 fix")
        if phase == "script":
            if script_risk not in {"low", "medium", "high"}:
                raise TaskStateError("Script 初始化必须指定 low/medium/high 风险")
            if script_environment not in {"local", "test", "staging", "production"}:
                raise TaskStateError(
                    "Script 初始化必须指定 local/test/staging/production 环境"
                )
        if self.state_path.exists():
            raise TaskStateError(f"任务状态已存在：{self.state_path}")
        if self.status_path.exists():
            raise TaskStateError(
                "status.md 已存在；旧任务请使用 migrate，避免覆盖人工状态"
            )
        timestamp = now_iso()
        document_state = "draft"
        state_name = "investigating" if phase == "debug" else "in_progress"
        workflow = {
            "design-1": "standard",
            "debug": "debug",
            "script": "script",
        }[phase]
        state = {
            "schema_version": SCHEMA_VERSION,
            "task_id": self.task_dir.name,
            "system": system.strip(),
            "title": title.strip(),
            "task_dir": self._display_task_dir(),
            "workflow": workflow,
            "phase": phase,
            "state": state_name,
            "document_state": document_state,
            "progress": PHASE_PROGRESS.get(phase, 0),
            "open_items": 0,
            "blockers": [],
            "phase_evidence": [],
            "execution": {"tasks": {}, "completed_task_ids": [], "next_task_id": None},
            "test": {"state": "not_started", "evidence": [], "risk_accepted": False},
            "review": new_review(
                phase == "script" and script_risk in {"medium", "high"}
            ),
            "close": new_close_state(),
            "debug_mode": debug_mode if phase == "debug" else None,
            "script": new_script_context(
                script_risk if phase == "script" else None,
                script_environment if phase == "script" else None,
            ),
            "branch": branch or detect_branch(self.task_dir),
            "return_phase": None,
            "return_context": None,
            "debug_outcome": None,
            "revision": 1,
            "created_at": timestamp,
            "updated_at": timestamp,
            "migration": None,
        }
        if not state["system"] or not state["title"]:
            raise TaskStateError("system 和 title 不能为空")
        with self.lock():
            self._save(state, "init", f"初始化 {phase} 阶段")
        return state

    def migrate(
        self, *, system: str | None = None, title: str | None = None
    ) -> dict[str, Any]:
        if self.state_path.exists():
            raise TaskStateError(f"任务状态已存在：{self.state_path}")
        if not self.status_path.is_file():
            raise TaskStateError("缺少 status.md，无法迁移；请使用 init")
        fields = self._read_status_fields()
        warnings: list[str] = []
        phase = fields.get("当前阶段", "design-1").strip()
        if phase not in PHASES:
            warnings.append(f"无法识别阶段 {phase!r}，已使用 design-1")
            phase = "design-1"
        state_name = REVERSE_STATE_LABELS.get(fields.get("状态", ""), "in_progress")
        if fields.get("状态") and fields["状态"] not in REVERSE_STATE_LABELS:
            warnings.append(f"无法识别状态 {fields['状态']!r}，已使用进行中")
        document_state = REVERSE_DOCUMENT_LABELS.get(
            fields.get("文档状态", ""), "draft"
        )
        open_items = self._parse_int(fields.get("未确认项"), 0, warnings, "未确认项")
        progress_text = (fields.get("整体进度") or "0").rstrip("%")
        progress = self._parse_int(progress_text, 0, warnings, "整体进度")
        progress = max(0, min(100, progress))
        timestamp = now_iso()
        close_state = "closed" if phase == "done" else "open"
        if phase == "done":
            state_name = "closed"
            document_state = "final"
            progress = 100
        test_state = "unknown" if phase in {"test", "close", "done"} else "not_started"
        workflow = self._infer_workflow(phase)
        migrated_close = new_close_state()
        migrated_close["state"] = close_state
        migrated_close["closed_at"] = timestamp if phase == "done" else None
        if phase == "done":
            for name, artifact in migrated_close["artifacts"].items():
                artifact["status"] = {
                    "summary": "completed",
                    "registration": "skipped",
                    "knowledge": "local_only",
                }[name]
                artifact["evidence"] = ["旧任务已关闭；需在迁移复核中核对实际结果"]
                artifact["updated_at"] = timestamp
        state = {
            "schema_version": SCHEMA_VERSION,
            "task_id": self.task_dir.name,
            "system": (system or fields.get("系统") or "待确认").strip(),
            "title": (title or fields.get("任务") or self.task_dir.name).strip(),
            "task_dir": self._display_task_dir(),
            "workflow": workflow,
            "phase": phase,
            "state": state_name,
            "document_state": document_state,
            "progress": progress,
            "open_items": open_items,
            "blockers": [],
            "phase_evidence": [],
            "execution": {"tasks": {}, "completed_task_ids": [], "next_task_id": None},
            "test": {"state": test_state, "evidence": [], "risk_accepted": False},
            "review": new_review(phase == "implement"),
            "close": migrated_close,
            "debug_mode": "unknown" if workflow == "debug" else None,
            "script": new_script_context(),
            "branch": detect_branch(self.task_dir),
            "return_phase": None,
            "return_context": None,
            "debug_outcome": None,
            "revision": 1,
            "created_at": timestamp,
            "updated_at": timestamp,
            "migration": {
                "source": "status.md",
                "requires_review": True,
                "warnings": warnings,
                "migrated_at": timestamp,
            },
        }
        with self.lock():
            self._save(state, "migrate", "从 status.md 迁移；机器状态需要复核")
        return state

    def update(
        self,
        *,
        document_state: str | None = None,
        open_items: int | None = None,
        state_name: str | None = None,
        evidence: list[str] | None = None,
        add_blockers: list[str] | None = None,
        resolve_blockers: list[str] | None = None,
        clear_blockers: bool = False,
        note: str = "更新任务状态",
    ) -> dict[str, Any]:
        if document_state is not None and document_state not in DOCUMENT_STATES:
            raise TaskStateError(f"非法 document_state：{document_state}")
        if open_items is not None and open_items < 0:
            raise TaskStateError("open_items 不能为负数")
        if state_name is not None:
            if state_name not in STATES:
                raise TaskStateError(f"非法 state：{state_name}")
            if state_name in {"completed", "awaiting_close", "closed"}:
                raise TaskStateError(
                    "completed/awaiting_close/closed 必须通过专用命令写入"
                )
        with self.lock():
            state = self.load()
            if state["phase"] == "done" or state["close"]["state"] == "closed":
                raise TaskStateError("已关闭任务不可再更新")
            self._invalidate_confirmation(state)
            if state_name is not None:
                self._require_state_transition(state, state_name)
            evidence_values = [
                value.strip() for value in (evidence or []) if value.strip()
            ]
            if state_name in {"root_cause_confirmed", "verified", "rolled_back"}:
                if not evidence_values:
                    raise TaskStateError(f"状态 {state_name} 必须记录 evidence")
            for value in evidence_values:
                if value not in state["phase_evidence"]:
                    state["phase_evidence"].append(value)
            previous_document_state = state["document_state"]
            if document_state is not None:
                state["document_state"] = document_state
            if open_items is not None:
                state["open_items"] = open_items
            blockers = [] if clear_blockers else list(state["blockers"])
            for blocker in add_blockers or []:
                value = blocker.strip()
                if value and value not in blockers:
                    blockers.append(value)
            for blocker in resolve_blockers or []:
                blockers = [item for item in blockers if item != blocker]
            state["blockers"] = blockers
            if state["open_items"] > 0:
                state["review"]["required"] = True
                if state["review"]["status"] != "completed":
                    state["review"]["status"] = "pending"
            if state_name == "reviewing":
                state["review"]["required"] = True
                state["review"]["status"] = "in_progress"
                state["review"]["updated_at"] = now_iso()
            if state["phase"] == "implement":
                if document_state in {
                    "complete",
                } and previous_document_state not in {
                    "ready",
                    "complete",
                }:
                    raise TaskStateError(
                        "施工文档必须先达到 ready，才能标记 complete"
                    )
                if document_state == "ready" and (state["open_items"] or blockers):
                    raise TaskStateError("施工文档存在未确认项或阻塞时不能标记 ready")
                if document_state == "ready":
                    self._require_review_completed(state)
                if document_state == "final":
                    raise TaskStateError("施工文档完成状态必须使用 complete，不能使用 final")
            if document_state == "final" and state["review"]["required"]:
                self._require_review_completed(state)
            if state_name in {"fixing", "awaiting_approval", "executing"}:
                self._require_review_completed(state)
            if state["phase"] == "script" and state_name == "executing":
                approval = state["script"]["approval"]
                if approval["required"] and not approval["approved"]:
                    raise TaskStateError("生产 Script 未记录执行批准，不能进入 executing")
            if blockers and state_name is not None and state_name != "blocked":
                raise TaskStateError("存在阻塞项时 state 只能为 blocked")
            if blockers:
                state["state"] = "blocked"
            elif state_name is not None:
                state["state"] = state_name
            elif state["open_items"] > 0:
                state["state"] = "awaiting_confirmation"
            elif state["state"] in {"blocked", "awaiting_confirmation"}:
                if state["phase"] in {"debug", "script"}:
                    raise TaskStateError(
                        "Debug/Script 解除阻塞或确认后必须显式指定恢复状态"
                    )
                state["state"] = "in_progress"
            return self._commit(state, "update", note)

    def record_review(
        self,
        status: str,
        *,
        evidence: list[str] | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        """记录当前阶段的 Grill/评审过程与证据。"""
        if status not in {"in_progress", "completed"}:
            raise TaskStateError("review 状态只能是 in_progress 或 completed")
        with self.lock():
            state = self.load()
            if state["phase"] in {"test", "close", "done"}:
                raise TaskStateError(f"{state['phase']} 阶段不使用 review 命令")
            self._invalidate_confirmation(state)
            state["review"]["required"] = True
            for value in evidence or []:
                value = value.strip()
                if value and value not in state["review"]["evidence"]:
                    state["review"]["evidence"].append(value)
            if status == "in_progress":
                self._require_state_transition(state, "reviewing")
                state["state"] = "reviewing"
            else:
                if state["review"]["status"] != "in_progress":
                    raise TaskStateError("完成 Grill/评审前必须先进入 in_progress")
                self._require_clear_gates(state)
                if not state["review"]["evidence"]:
                    raise TaskStateError("完成 Grill/评审必须记录 evidence")
                if state["phase"] in {"design-1", "design-2", "implement"}:
                    self._require_state_transition(state, "in_progress")
                    state["state"] = "in_progress"
            state["review"]["status"] = status
            state["review"]["updated_at"] = now_iso()
            return self._commit(
                state,
                "review",
                note or f"阶段评审 → {status}",
            )

    def configure_debug(self, mode: str, *, note: str | None = None) -> dict[str, Any]:
        """为旧 Debug 状态补齐 diagnose/fix 授权模式。"""
        if mode not in {"diagnose", "fix"}:
            raise TaskStateError("Debug mode 只能是 diagnose 或 fix")
        with self.lock():
            state = self.load()
            if state["phase"] != "debug":
                raise TaskStateError("configure-debug 只能在 debug 阶段使用")
            if state["state"] not in {"investigating", "root_cause_confirmed"}:
                raise TaskStateError("Debug 开始修复或完成后不能更改授权模式")
            state["debug_mode"] = mode
            return self._commit(state, "configure-debug", note or f"Debug 模式 → {mode}")

    def configure_script(
        self,
        risk: str,
        environment: str,
        *,
        note: str | None = None,
    ) -> dict[str, Any]:
        """为 Script 记录风险、环境和相应门禁。"""
        if risk not in {"low", "medium", "high"}:
            raise TaskStateError("Script risk 只能是 low、medium 或 high")
        if environment not in {"local", "test", "staging", "production"}:
            raise TaskStateError(
                "Script environment 只能是 local、test、staging 或 production"
            )
        with self.lock():
            state = self.load()
            if state["workflow"] != "script" or state["phase"] != "script":
                raise TaskStateError("configure-script 只能用于独立 Script 工作流")
            if state["state"] not in {"in_progress", "reviewing", "awaiting_approval"}:
                raise TaskStateError("Script 执行开始后不能更改风险或环境")
            previous = state["script"]
            state["script"] = new_script_context(risk, environment)
            if previous.get("approval", {}).get("approved") and environment == "production":
                state["script"]["approval"] = previous["approval"]
            required = risk in {"medium", "high"}
            if required and state["review"]["status"] != "completed":
                state["review"] = new_review(True)
            elif not required and state["review"]["status"] != "completed":
                state["review"] = new_review(False)
            return self._commit(
                state,
                "configure-script",
                note or f"Script 风险/环境 → {risk}/{environment}",
            )

    def approve_script(
        self,
        evidence: list[str],
        *,
        note: str | None = None,
    ) -> dict[str, Any]:
        """记录生产 Script 的独立执行批准。"""
        values = [value.strip() for value in evidence if value.strip()]
        if not values:
            raise TaskStateError("生产执行批准必须记录 evidence")
        with self.lock():
            state = self.load()
            if state["workflow"] != "script" or state["phase"] != "script":
                raise TaskStateError("approve-script 只能用于独立 Script 工作流")
            if state["state"] != "awaiting_approval":
                raise TaskStateError("Script 必须先进入 awaiting_approval")
            approval = state["script"]["approval"]
            if not approval["required"]:
                raise TaskStateError("非生产 Script 不需要生产执行批准")
            approval["approved"] = True
            approval["evidence"] = list(dict.fromkeys(values))
            approval["approved_at"] = now_iso()
            return self._commit(state, "approve-script", note or "生产执行已批准")

    def record_close_artifact(
        self,
        name: str,
        status: str,
        *,
        evidence: list[str],
        note: str | None = None,
    ) -> dict[str, Any]:
        """记录 summary、AI 登记和知识沉淀的实际收口结果。"""
        if name not in CLOSE_ARTIFACT_STATUSES:
            raise TaskStateError(f"未知 Close artifact：{name}")
        if status == "pending" or status not in CLOSE_ARTIFACT_STATUSES[name]:
            raise TaskStateError(f"非法 {name} artifact 状态：{status}")
        values = [value.strip() for value in evidence if value.strip()]
        if not values:
            raise TaskStateError("Close artifact 终态必须记录 evidence")
        with self.lock():
            state = self.load()
            if state["phase"] != "close" or state["close"]["state"] != "ready":
                raise TaskStateError("close-artifact 只能在 Close 门禁就绪后使用")
            if name == "summary" and status == "completed":
                if not (self.task_dir / "summary.md").is_file():
                    raise TaskStateError("summary artifact 完成前必须存在 summary.md")
            artifact = state["close"]["artifacts"][name]
            artifact["status"] = status
            artifact["evidence"] = list(dict.fromkeys(values))
            artifact["updated_at"] = now_iso()
            return self._commit(
                state,
                "close-artifact",
                note or f"Close artifact {name} → {status}",
            )

    def review_migration(
        self,
        *,
        test_state: str | None = None,
        evidence: list[str] | None = None,
        risk_accepted: bool = False,
        note: str = "已复核迁移状态",
    ) -> dict[str, Any]:
        """确认旧 ``status.md`` 迁移结果已经人工复核。"""
        with self.lock():
            state = self.load()
            migration = state.get("migration")
            if not isinstance(migration, dict):
                raise TaskStateError("当前任务不是从旧 status.md 迁移，无需复核")
            if not migration.get("requires_review"):
                return state
            if state["test"]["state"] == "unknown":
                if test_state not in {"not_started", "passed", "conditional", "failed"}:
                    raise TaskStateError(
                        "旧任务的测试状态未知；migration-review 必须显式提供 --test-state"
                    )
                test_evidence = []
                for value in evidence or []:
                    value = value.strip()
                    if value and value not in test_evidence:
                        test_evidence.append(value)
                if test_state in {"passed", "conditional"} and not test_evidence:
                    raise TaskStateError(
                        "迁移为测试通过或有条件通过时必须提供 --evidence"
                    )
                if test_state == "conditional" and not risk_accepted:
                    raise TaskStateError(
                        "迁移为有条件通过时必须显式提供 --risk-accepted"
                    )
                state["test"] = {
                    "state": test_state,
                    "evidence": test_evidence,
                    "risk_accepted": bool(risk_accepted),
                }
                if state["phase"] == "close":
                    state["phase"] = "test"
                    state["progress"] = 80
                state["blockers"] = [
                    item for item in state["blockers"] if item != "测试未通过"
                ]
                if test_state == "failed":
                    state["blockers"].append("测试未通过")
                    state["state"] = "blocked"
                elif state["phase"] == "test" and test_state in {
                    "passed",
                    "conditional",
                }:
                    state["state"] = "awaiting_close"
                    state["progress"] = 95
                elif state["phase"] in {"test", "close"}:
                    state["state"] = "in_progress"
            migration["requires_review"] = False
            migration["reviewed_at"] = now_iso()
            migration["review_note"] = note
            return self._commit(state, "migration-review", note)

    def start_phase(
        self,
        phase: str,
        *,
        debug_mode: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        if phase not in PHASES - {"close", "done"}:
            raise TaskStateError(f"不能通过 start 进入阶段：{phase}")
        if phase == "debug" and debug_mode not in {"diagnose", "fix"}:
            raise TaskStateError("进入 Debug 必须指定 debug_mode=diagnose 或 fix")
        with self.lock():
            state = self.load()
            self._require_migration_reviewed(state)
            self._invalidate_confirmation(state)
            current = state["phase"]
            if phase == "debug" and current != "done":
                if state["workflow"] != "standard":
                    raise TaskStateError("只有标准工作流可以插入 Debug 阶段")
                if current in {"debug", "close"}:
                    raise TaskStateError(f"不能从 {current} 阶段重复或插入 Debug")
                state["return_phase"] = current
                state["return_context"] = {
                    "phase": current,
                    "state": state["state"],
                    "document_state": state["document_state"],
                    "progress": state["progress"],
                    "open_items": state["open_items"],
                    "blockers": list(state["blockers"]),
                    "phase_evidence": list(state["phase_evidence"]),
                    "review": json.loads(json.dumps(state["review"])),
                }
                state["debug_outcome"] = None
            else:
                allowed = {
                    ("design-1", "design-2"),
                    ("design-2", "implement"),
                    ("implement", "test"),
                }
                if current == "debug" and state["state"] == "completed":
                    target = state.get("return_phase")
                    if target is not None:
                        allowed.add(("debug", target))
                if (current, phase) not in allowed or state["state"] != "completed":
                    raise TaskStateError(
                        f"不允许从 {current}/{state['state']} 进入 {phase}"
                    )
                if current == "debug" and isinstance(state.get("return_context"), dict):
                    context = state["return_context"]
                    if context.get("phase") != phase:
                        raise TaskStateError("Debug 返回阶段与保存的上下文不一致")
                    state["phase"] = phase
                    state["document_state"] = context["document_state"]
                    state["progress"] = context["progress"]
                    state["open_items"] = context["open_items"]
                    state["blockers"] = list(context["blockers"])
                    state["phase_evidence"] = list(
                        context.get("phase_evidence") or []
                    )
                    state["review"] = json.loads(
                        json.dumps(context.get("review") or new_review())
                    )
                    if state.get("debug_outcome") == "verified":
                        if phase == "test":
                            state["test"]["state"] = "running"
                            state["blockers"] = [
                                item
                                for item in state["blockers"]
                                if item != "测试未通过"
                            ]
                        if state["blockers"]:
                            state["state"] = "blocked"
                        elif state["open_items"]:
                            state["state"] = "awaiting_confirmation"
                        else:
                            state["state"] = "in_progress"
                    else:
                        state["state"] = context["state"]
                    state["return_phase"] = None
                    state["return_context"] = None
                    state["debug_mode"] = None
                    return self._commit(
                        state,
                        "start",
                        note or f"Debug 完成，返回 {phase} 阶段",
                    )
            state["phase"] = phase
            if current == "debug":
                state["return_phase"] = None
                state["return_context"] = None
            state["state"] = "investigating" if phase == "debug" else "in_progress"
            state["document_state"] = "draft"
            state["progress"] = PHASE_PROGRESS.get(phase, state["progress"])
            state["open_items"] = 0
            state["blockers"] = []
            state["phase_evidence"] = []
            state["review"] = new_review(phase == "implement")
            state["debug_mode"] = debug_mode if phase == "debug" else None
            if phase == "test":
                state["test"]["state"] = "running"
            return self._commit(state, "start", note or f"进入 {phase} 阶段")

    def complete_phase(self, *, note: str | None = None) -> dict[str, Any]:
        with self.lock():
            state = self.load()
            self._require_migration_reviewed(state)
            self._require_clear_gates(state)
            self._require_review_completed(state)
            phase = state["phase"]
            self._require_phase_document_resolved(phase)
            if phase in {"design-1", "design-2"}:
                self._require_document(state, {"final"})
            elif phase == "implement":
                self._require_document(state, {"complete"})
                tasks = state["execution"]["tasks"]
                if not tasks:
                    raise TaskStateError("施工任务为空；请先使用 task 命令登记任务")
                incomplete = sorted(
                    task_id
                    for task_id, item in tasks.items()
                    if item.get("status") != "completed"
                )
                if incomplete:
                    raise TaskStateError(f"仍有未完成施工任务：{', '.join(incomplete)}")
                if state["execution"]["next_task_id"] is not None:
                    raise TaskStateError("next_task_id 尚未清空，不能完成 implement")
            elif phase == "debug":
                self._require_document(state, {"final", "complete"})
                if state["debug_mode"] == "unknown":
                    raise TaskStateError("旧 Debug 状态必须先使用 configure-debug 明确模式")
                required_state = {
                    "diagnose": "root_cause_confirmed",
                    "fix": "verified",
                }.get(state["debug_mode"])
                if state["state"] != required_state:
                    raise TaskStateError(
                        f"Debug {state['debug_mode']} 必须达到 {required_state}"
                    )
                if not state["phase_evidence"]:
                    raise TaskStateError("Debug 完成前必须记录根因或验证 evidence")
                state["debug_outcome"] = (
                    "diagnosed"
                    if state["debug_mode"] == "diagnose"
                    else "verified"
                )
            elif phase == "script":
                self._require_document(state, {"final", "complete"})
                if state["script"]["risk"] == "unknown" or state["script"][
                    "environment"
                ] == "unknown":
                    raise TaskStateError(
                        "旧 Script 状态必须先使用 configure-script 明确风险和环境"
                    )
                if state["state"] not in {"verified", "rolled_back"}:
                    raise TaskStateError(
                        "Script 只有在 verified 或已验证 rolled_back 时才能完成"
                    )
                if not state["phase_evidence"]:
                    raise TaskStateError("Script 完成前必须记录验证或回滚 evidence")
                state["script"]["outcome"] = state["state"]
            else:
                raise TaskStateError(
                    f"{phase} 阶段不能使用 complete；请使用 test/close 专用命令"
                )
            state["state"] = "completed"
            state["progress"] = PHASE_COMPLETED_PROGRESS.get(phase, state["progress"])
            return self._commit(state, "complete", note or f"完成 {phase} 阶段")

    def record_task(
        self,
        task_id: str,
        status: str,
        *,
        evidence: list[str] | None = None,
        next_task: str | None = None,
        clear_next: bool = False,
        note: str | None = None,
    ) -> dict[str, Any]:
        if status not in {"planned", "in_progress", "completed", "blocked"}:
            raise TaskStateError(f"非法施工任务状态：{status}")
        task_id = task_id.strip()
        if not task_id:
            raise TaskStateError("task_id 不能为空")
        with self.lock():
            state = self.load()
            self._require_migration_reviewed(state)
            if state["phase"] != "implement":
                raise TaskStateError("task 命令只能在 implement 阶段使用")
            if status in {"in_progress", "completed"} and state[
                "document_state"
            ] not in {
                "ready",
                "complete",
            }:
                raise TaskStateError("施工文档未达到 ready，不能开始或完成编码任务")
            self._invalidate_confirmation(state)
            tasks = state["execution"]["tasks"]
            item = tasks.setdefault(
                task_id, {"status": "planned", "evidence": [], "updated_at": now_iso()}
            )
            item["status"] = status
            item["updated_at"] = now_iso()
            for value in evidence or []:
                value = value.strip()
                if value and value not in item["evidence"]:
                    item["evidence"].append(value)
            if status == "completed" and not item["evidence"]:
                raise TaskStateError(
                    f"施工任务 {task_id} 标记 completed 前必须记录验证证据"
                )
            completed = sorted(
                key
                for key, value in tasks.items()
                if value.get("status") == "completed"
            )
            state["execution"]["completed_task_ids"] = completed
            if clear_next:
                state["execution"]["next_task_id"] = None
            elif next_task is not None:
                state["execution"]["next_task_id"] = next_task.strip() or None
            elif status == "in_progress":
                state["execution"]["next_task_id"] = task_id
            elif (
                status == "completed" and state["execution"]["next_task_id"] == task_id
            ):
                state["execution"]["next_task_id"] = None
            if status == "blocked":
                state["state"] = "blocked"
            elif state["state"] == "blocked" and all(
                value.get("status") != "blocked" for value in tasks.values()
            ):
                state["state"] = "in_progress"
            if tasks:
                ratio = len(completed) / len(tasks)
                state["progress"] = min(74, 50 + round(24 * ratio))
            return self._commit(state, "task", note or f"施工任务 {task_id} → {status}")

    def record_test(
        self,
        result: str,
        *,
        evidence: list[str] | None = None,
        risk_accepted: bool = False,
        note: str | None = None,
    ) -> dict[str, Any]:
        if result not in {"running", "passed", "conditional", "failed"}:
            raise TaskStateError(f"非法测试结果：{result}")
        if result == "conditional" and not risk_accepted:
            raise TaskStateError("有条件通过必须显式提供 --risk-accepted")
        with self.lock():
            state = self.load()
            self._require_migration_reviewed(state)
            if state["phase"] != "test":
                raise TaskStateError("test 命令只能在 test 阶段使用")
            self._invalidate_confirmation(state)
            if result in {"passed", "conditional"}:
                self._require_phase_document_resolved("test")
            state["test"]["state"] = result
            state["test"]["risk_accepted"] = bool(risk_accepted)
            for value in evidence or []:
                value = value.strip()
                if value and value not in state["test"]["evidence"]:
                    state["test"]["evidence"].append(value)
            if result in {"passed", "conditional"} and not state["test"]["evidence"]:
                raise TaskStateError(f"测试标记 {result} 前必须记录验证证据")
            state["blockers"] = [
                item for item in state["blockers"] if item != "测试未通过"
            ]
            if result in {"passed", "conditional"}:
                state["state"] = "awaiting_close"
                state["document_state"] = "complete"
                state["progress"] = 95
            elif result == "failed":
                state["state"] = "blocked"
                state["document_state"] = "reviewing"
                state["progress"] = 80
                state["blockers"].append("测试未通过")
            else:
                state["state"] = "in_progress"
                state["progress"] = 80
            return self._commit(state, "test", note or f"测试结果 → {result}")

    def request_close(
        self, *, fingerprint: str | None = None
    ) -> tuple[dict[str, Any], str | None]:
        with self.lock():
            state = self.load()
            if state["phase"] == "done":
                return state, None
            if state["phase"] == "close" and state["close"]["state"] == "ready":
                return state, None
            self._require_migration_reviewed(state)
            self._require_clear_gates(state)
            test_state = state["test"]["state"]
            if test_state == "failed":
                raise TaskStateError("测试未通过，不能关闭")
            if test_state in {"running", "unknown"}:
                raise TaskStateError(
                    f"测试状态为 {test_state}，不能按未执行测试例外关闭"
                )
            if test_state == "conditional" and not state["test"]["risk_accepted"]:
                raise TaskStateError("有条件通过的遗留风险尚未明确接受")
            self._require_workflow_ready_for_close(state)
            if test_state == "not_started":
                token = secrets.token_urlsafe(18)
                current_fingerprint = fingerprint or working_tree_fingerprint(
                    self.task_dir
                )
                artifacts = state["close"]["artifacts"]
                state["state"] = "awaiting_confirmation"
                state["close"] = {
                    "state": "awaiting_test_confirmation",
                    "confirmation": {
                        "token_hash": hashlib.sha256(token.encode("utf-8")).hexdigest(),
                        "working_tree_fingerprint": current_fingerprint,
                        "state_revision": state["revision"] + 1,
                        "requested_at": now_iso(),
                        "confirmed_at": None,
                    },
                    "closed_at": None,
                    "artifacts": artifacts,
                }
                saved = self._commit(
                    state,
                    "close-request",
                    "测试未执行：等待用户明确确认跳过测试并关闭",
                )
                return saved, token
            if test_state not in {"passed", "conditional", "skipped_confirmed"}:
                raise TaskStateError(f"测试状态 {test_state} 不允许关闭")
            state["phase"] = "close"
            state["state"] = "in_progress"
            state["document_state"] = "final"
            state["progress"] = 95
            state["close"]["state"] = "ready"
            state["close"]["confirmation"] = state["close"].get("confirmation")
            return self._commit(state, "close-request", "关闭门禁已就绪"), None

    def confirm_close(
        self,
        token: str,
        *,
        fingerprint: str | None = None,
        note: str = "用户已确认跳过测试并关闭",
    ) -> dict[str, Any]:
        with self.lock():
            state = self.load()
            close = state["close"]
            confirmation = close.get("confirmation")
            if close["state"] != "awaiting_test_confirmation" or not isinstance(
                confirmation, dict
            ):
                raise TaskStateError("当前不存在待确认的未测试关闭请求")
            if state["revision"] != confirmation.get("state_revision"):
                raise TaskStateError("关闭请求后任务状态已变化，请重新发起关闭")
            token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
            if not secrets.compare_digest(
                token_hash, str(confirmation.get("token_hash", ""))
            ):
                raise TaskStateError("关闭确认 token 无效")
            current_fingerprint = fingerprint or working_tree_fingerprint(self.task_dir)
            if current_fingerprint != confirmation.get("working_tree_fingerprint"):
                self._invalidate_confirmation(state)
                self._commit(
                    state,
                    "close-invalidated",
                    "关闭请求后工作树已变化；必须重新验证受影响阶段",
                )
                raise TaskStateError(
                    "关闭请求后代码、设计或依赖已变化；请重新验证受影响阶段，再提醒并确认"
                )
            confirmation.pop("token_hash", None)
            confirmation["confirmed_at"] = now_iso()
            confirmation["decision"] = note
            state["test"]["state"] = "skipped_confirmed"
            state["test"]["risk_accepted"] = True
            state["phase"] = "close"
            state["state"] = "in_progress"
            state["document_state"] = "final"
            state["progress"] = 95
            state["close"]["state"] = "ready"
            return self._commit(state, "close-confirm", note)

    def complete_close(self, *, note: str = "开发流程已关闭") -> dict[str, Any]:
        with self.lock():
            state = self.load()
            if state["phase"] == "done" and state["close"]["state"] == "closed":
                return state
            self._require_clear_gates(state)
            if state["phase"] != "close" or state["close"]["state"] != "ready":
                raise TaskStateError(
                    "关闭门禁尚未就绪；请先运行 close-request/close-confirm"
                )
            if state["test"]["state"] not in {
                "passed",
                "conditional",
                "skipped_confirmed",
            }:
                raise TaskStateError("测试状态不允许完成关闭")
            if not (self.task_dir / "summary.md").is_file():
                raise TaskStateError("缺少 summary.md，不能完成关闭")
            pending_artifacts = [
                name
                for name, artifact in state["close"]["artifacts"].items()
                if artifact["status"] == "pending" or not artifact["evidence"]
            ]
            if pending_artifacts:
                raise TaskStateError(
                    "Close 收口结果尚未记录：" + ", ".join(pending_artifacts)
                )
            documents = self._require_workflow_documents(
                state,
                include_test=state["test"]["state"] in {"passed", "conditional"},
            )
            self._require_documents_resolved(documents)
            state["phase"] = "done"
            state["state"] = "closed"
            state["document_state"] = "final"
            state["progress"] = 100
            state["close"]["state"] = "closed"
            state["close"]["closed_at"] = now_iso()
            return self._commit(state, "close-complete", note)

    def validate_consistency(self) -> list[str]:
        state = self.load()
        errors = validate_state(state)
        fields = self._read_status_fields()
        expected = self._status_fields(state)
        for name, value in expected.items():
            if fields.get(name) != value:
                errors.append(
                    f"status.md 字段不一致：{name}={fields.get(name)!r}，期望 {value!r}"
                )
        if state["phase"] == "done" and state["close"]["state"] != "closed":
            errors.append("phase=done 时 close.state 必须为 closed")
        if state["close"]["state"] == "closed" and state["progress"] != 100:
            errors.append("关闭任务的 progress 必须为 100")
        return errors

    def _display_task_dir(self) -> str:
        root = find_git_root(self.task_dir)
        if root is not None:
            try:
                relative = self.task_dir.relative_to(root)
            except ValueError:
                pass
            else:
                return relative.as_posix().rstrip("/") + "/"
        return self.task_dir.as_posix().rstrip("/") + "/"

    def _commit(self, state: dict[str, Any], event: str, note: str) -> dict[str, Any]:
        state["revision"] += 1
        state["updated_at"] = now_iso()
        errors = validate_state(state)
        if errors:
            raise TaskStateError("；".join(errors))
        self._save(state, event, note)
        return state

    def _save(self, state: dict[str, Any], event: str, note: str) -> None:
        errors = validate_state(state)
        if errors:
            raise TaskStateError("；".join(errors))
        atomic_write_json(self.state_path, state)
        atomic_write_text(self.status_path, self._render_status(state, event, note))

    def _status_fields(self, state: dict[str, Any]) -> dict[str, str]:
        return {
            "系统": state["system"],
            "任务": state["title"],
            "工作流": state["workflow"],
            "当前阶段": state["phase"],
            "状态": STATE_LABELS[state["state"]],
            "文档状态": DOCUMENT_LABELS[state["document_state"]],
            "未确认项": str(state["open_items"]),
            "整体进度": f"{state['progress']}%",
            "最后更新": state["updated_at"],
        }

    def _render_status(self, state: dict[str, Any], event: str, note: str) -> str:
        fields = self._status_fields(state)
        existing = (
            self.status_path.read_text(encoding="utf-8")
            if self.status_path.is_file()
            else ""
        )
        field_pattern = re.compile(
            r"^(系统|任务|工作流|当前阶段|状态|文档状态|未确认项|整体进度|最后更新)[：:].*$"
        )
        body_lines = [
            line for line in existing.splitlines() if not field_pattern.match(line)
        ]
        while body_lines and not body_lines[0].strip():
            body_lines.pop(0)
        header = [f"{name}：{value}" for name, value in fields.items()]
        if "## 状态日志" not in body_lines:
            if body_lines:
                body_lines.extend(["", "## 状态日志"])
            else:
                body_lines.append("## 状态日志")
        body_lines.append(f"- {state['updated_at']} [{event}] {note}")
        return "\n".join([*header, "", *body_lines]).rstrip() + "\n"

    def _read_status_fields(self) -> dict[str, str]:
        if not self.status_path.is_file():
            return {}
        result: dict[str, str] = {}
        pattern = re.compile(
            r"^(系统|任务|工作流|当前阶段|状态|文档状态|未确认项|整体进度|最后更新)[：:]\s*(.*)$"
        )
        for line in self.status_path.read_text(encoding="utf-8").splitlines():
            match = pattern.match(line)
            if match:
                result[match.group(1)] = match.group(2).strip()
        return result

    @staticmethod
    def _parse_int(
        value: str | None, default: int, warnings: list[str], name: str
    ) -> int:
        try:
            return int(value) if value is not None else default
        except ValueError:
            warnings.append(f"无法解析{name} {value!r}，已使用 {default}")
            return default

    @staticmethod
    def _require_clear_gates(state: dict[str, Any]) -> None:
        if state["open_items"] != 0:
            raise TaskStateError(f"仍有 {state['open_items']} 个未确认项")
        if state["blockers"]:
            raise TaskStateError(f"仍有阻塞项：{'；'.join(state['blockers'])}")

    @staticmethod
    def _require_review_completed(state: dict[str, Any]) -> None:
        review = state["review"]
        if review["required"] and review["status"] != "completed":
            raise TaskStateError("当前阶段的 Grill/评审尚未完成并记录证据")

    @staticmethod
    def _require_state_transition(state: dict[str, Any], target: str) -> None:
        current = state["state"]
        if target == current:
            return
        phase = state["phase"]
        allowed = PHASE_STATE_TRANSITIONS.get(phase, {}).get(current, set())
        if target not in allowed:
            raise TaskStateError(f"不允许 {phase} 状态从 {current} 进入 {target}")

    @staticmethod
    def _require_document(state: dict[str, Any], allowed: set[str]) -> None:
        if state["document_state"] not in allowed:
            raise TaskStateError(
                f"文档状态必须为 {', '.join(sorted(allowed))}，当前为 {state['document_state']}"
            )

    @staticmethod
    def _require_migration_reviewed(state: dict[str, Any]) -> None:
        migration = state.get("migration")
        if isinstance(migration, dict) and migration.get("requires_review"):
            raise TaskStateError(
                "旧 status.md 迁移状态尚未复核；请先运行 migration-review"
            )

    def _upgrade_state(self, state: dict[str, Any]) -> dict[str, Any]:
        """在内存中补齐旧版状态；下一次成功提交时持久化新版结构。"""
        version = state.get("schema_version")
        if version == SCHEMA_VERSION:
            return state
        if version not in {1, 2}:
            return state
        upgraded = json.loads(json.dumps(state))
        upgraded["schema_version"] = SCHEMA_VERSION
        if version == 1:
            upgraded["workflow"] = self._infer_workflow(str(state.get("phase", "")))
        upgraded["phase_evidence"] = list(upgraded.get("phase_evidence") or [])
        phase = str(upgraded.get("phase", ""))
        document_state = upgraded.get("document_state")
        review_required = phase == "implement"
        review = new_review(review_required)
        if review_required and document_state in {"ready", "final", "complete"}:
            review["status"] = "completed"
            review["evidence"] = [
                "兼容升级：旧状态的施工文档已达到可施工或完成状态"
            ]
            review["updated_at"] = upgraded.get("updated_at") or now_iso()
        upgraded["review"] = review
        workflow = upgraded.get("workflow")
        upgraded["debug_mode"] = "unknown" if workflow == "debug" else None
        upgraded["script"] = new_script_context()
        close = dict(upgraded.get("close") or {})
        upgraded_close = new_close_state()
        upgraded_close.update(
            {
                "state": close.get("state", "open"),
                "confirmation": close.get("confirmation"),
                "closed_at": close.get("closed_at"),
            }
        )
        if upgraded_close["state"] == "closed":
            for name, artifact in upgraded_close["artifacts"].items():
                artifact["status"] = {
                    "summary": "completed",
                    "registration": "skipped",
                    "knowledge": "local_only",
                }[name]
                artifact["evidence"] = ["兼容升级：旧状态已关闭，实际结果待复核"]
                artifact["updated_at"] = upgraded.get("updated_at") or now_iso()
        upgraded["close"] = upgraded_close
        return upgraded

    def _infer_workflow(self, phase: str) -> str:
        if phase == "debug":
            return "debug"
        if phase == "script":
            return "script"
        if phase in {"close", "done"}:
            standard_new = all(
                (self.task_dir / name).is_file()
                for name in ("001-设计文档.md", "002-施工文档.md")
            )
            standard_legacy = all(
                (self.task_dir / name).is_file()
                for name in ("001-概要设计.md", "002-详细设计.md", "003-施工文档.md")
            )
            if standard_new or standard_legacy:
                return "standard"
            if (self.task_dir / "脚本任务.md").is_file():
                return "script"
            if any(
                (self.task_dir / name).is_file()
                for name in ("Debug排查记录.md", "006-Debug排查记录.md")
            ):
                return "debug"
        return "standard"

    def _require_workflow_ready_for_close(self, state: dict[str, Any]) -> None:
        workflow = state["workflow"]
        phase = state["phase"]
        test_state = state["test"]["state"]
        self._require_document(state, {"final", "complete"})
        if workflow == "standard":
            if phase == "debug":
                raise TaskStateError("标准工作流中的 Debug 必须先返回原阶段")
            valid_untested = (
                phase == "implement"
                and state["state"] == "completed"
                and test_state == "not_started"
            )
            valid_tested = (
                phase == "test"
                and state["state"] == "awaiting_close"
                and test_state in {"passed", "conditional"}
            )
            if not (valid_untested or valid_tested):
                raise TaskStateError("标准工作流尚未完成施工或测试关闭门禁")
        elif workflow == "debug":
            if phase != "debug" or state["state"] != "completed":
                raise TaskStateError("Debug 工作流尚未完成排查/修复与验证")
        elif workflow == "script":
            if phase != "script" or state["state"] != "completed":
                raise TaskStateError("Script 工作流尚未达到约定目标并完成验证")
        documents = self._require_workflow_documents(
            state,
            include_test=test_state in {"passed", "conditional"},
        )
        self._require_documents_resolved(documents)

    def _require_workflow_documents(
        self, state: dict[str, Any], *, include_test: bool
    ) -> list[tuple[Path, str]]:
        workflow = state["workflow"]
        documents: list[tuple[Path, str]] = []
        if workflow == "standard":
            design_new = (self.task_dir / "001-设计文档.md").is_file()
            design_legacy = all(
                (self.task_dir / name).is_file()
                for name in ("001-概要设计.md", "002-详细设计.md")
            )
            if not (design_new or design_legacy):
                raise TaskStateError("缺少标准工作流设计文档：001-设计文档.md")
            if design_new:
                documents.append((self.task_dir / "001-设计文档.md", "design-2"))
            else:
                documents.extend(
                    (self.task_dir / name, "design-2")
                    for name in ("001-概要设计.md", "002-详细设计.md")
                )
            construction = next(
                (
                    self.task_dir / name
                    for name in ("002-施工文档.md", "003-施工文档.md")
                    if (self.task_dir / name).is_file()
                ),
                None,
            )
            if construction is None:
                raise TaskStateError("缺少标准工作流施工文档：002-施工文档.md")
            documents.append((construction, "implement"))
            if include_test:
                testing = next(
                    (
                        self.task_dir / name
                        for name in ("003-测试文档.md", "005-测试报告.md")
                        if (self.task_dir / name).is_file()
                    ),
                    None,
                )
                if testing is None:
                    raise TaskStateError("缺少标准工作流测试文档：003-测试文档.md")
                documents.append((testing, "test"))
        elif workflow == "debug":
            debug_document = next(
                (
                    self.task_dir / name
                    for name in ("Debug排查记录.md", "006-Debug排查记录.md")
                    if (self.task_dir / name).is_file()
                ),
                None,
            )
            if debug_document is None:
                raise TaskStateError("缺少 Debug 工作流主文档：Debug排查记录.md")
            documents.append((debug_document, "debug"))
        elif workflow == "script":
            script_document = self.task_dir / "脚本任务.md"
            if not script_document.is_file():
                raise TaskStateError("缺少 Script 工作流主文档：脚本任务.md")
            documents.append((script_document, "script"))
        return documents

    def _require_phase_document_resolved(self, phase: str) -> None:
        names = {
            "design-1": ("001-设计文档.md",),
            "design-2": ("001-设计文档.md",),
            "implement": ("002-施工文档.md",),
            "test": ("003-测试文档.md",),
            "debug": ("Debug排查记录.md",),
            "script": ("脚本任务.md",),
        }.get(phase)
        if names is None:
            return
        path = next(
            (self.task_dir / name for name in names if (self.task_dir / name).is_file()),
            None,
        )
        if path is None:
            raise TaskStateError(f"缺少 {phase} 阶段主文档：{names[0]}")
        documents = [(path, phase)]
        if phase in {"design-1", "design-2"}:
            review = self.task_dir / "001-设计文档-评审记录.md"
            if review.is_file():
                documents.append((review, phase))
        self._require_documents_resolved(documents)

    @staticmethod
    def _require_documents_resolved(documents: list[tuple[Path, str]]) -> None:
        unresolved: list[str] = []
        for path, phase in documents:
            states = DOCUMENT_UNRESOLVED_STATES[phase]
            for line_number, value in TaskStateStore._document_unresolved_items(
                path, states
            ):
                unresolved.append(f"{path.name}:{line_number}={value}")
        if unresolved:
            raise TaskStateError("主文档仍有未解决项：" + "；".join(unresolved))

    @staticmethod
    def _document_unresolved_items(
        path: Path, states: set[str]
    ) -> list[tuple[int, str]]:
        result: list[tuple[int, str]] = []
        field_pattern = re.compile(
            r"^(?:[-*>]\s*)?(?:文档状态|状态|最终结论|当前状态|结论)[：:]\s*(.+)$",
            re.IGNORECASE,
        )
        table_row_index = 0
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            stripped = line.strip()
            candidates: list[str] = []
            if stripped.startswith("|") and stripped.endswith("|"):
                table_row_index += 1
                # Markdown 表格首行是列名，不能把“失败”“阻塞”等列名误判为任务状态。
                if table_row_index == 1:
                    continue
                cells = [cell.strip() for cell in stripped[1:-1].split("|")]
                if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                    continue
                candidates.extend(cells)
            else:
                table_row_index = 0
                match = field_pattern.match(stripped)
                if match:
                    candidates.append(match.group(1).strip())
            for candidate in candidates:
                values = {
                    value.strip(" `*_[]()")
                    for value in re.split(r"[/、,，;；]", candidate)
                }
                matched = sorted(states & values)
                if matched:
                    result.append((line_number, "/".join(matched)))
        return result

    @staticmethod
    def _invalidate_confirmation(state: dict[str, Any]) -> None:
        if state["close"]["state"] == "awaiting_test_confirmation":
            artifacts = state["close"].get("artifacts") or new_close_state()[
                "artifacts"
            ]
            state["close"] = new_close_state()
            state["close"]["artifacts"] = artifacts
            if state["state"] == "awaiting_confirmation":
                state["state"] = "in_progress"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SDLC 任务状态核心 CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    def task_dir_argument(command: argparse.ArgumentParser) -> None:
        command.add_argument("--task-dir", required=True, help="docs/[任务目录]/")

    init = sub.add_parser("init", help="初始化机器状态和 status.md")
    task_dir_argument(init)
    init.add_argument("--system", required=True)
    init.add_argument("--title", required=True)
    init.add_argument(
        "--phase", choices=["design-1", "debug", "script"], default="design-1"
    )
    init.add_argument("--branch")
    init.add_argument(
        "--debug-mode",
        choices=["diagnose", "fix"],
        help="Debug 初始化时必填：仅诊断或包含修复",
    )
    init.add_argument(
        "--script-risk",
        choices=["low", "medium", "high"],
        help="Script 初始化时必填：风险等级",
    )
    init.add_argument(
        "--script-environment",
        choices=["local", "test", "staging", "production"],
        help="Script 初始化时必填：目标环境",
    )

    migrate = sub.add_parser("migrate", help="从旧 status.md 生成待复核机器状态")
    task_dir_argument(migrate)
    migrate.add_argument("--system")
    migrate.add_argument("--title")

    migration_review = sub.add_parser(
        "migration-review", help="确认旧状态迁移结果已经复核"
    )
    task_dir_argument(migration_review)
    migration_review.add_argument(
        "--test-state",
        choices=["not_started", "passed", "conditional", "failed"],
        help="旧阶段为 test/close 时必须明确测试事实",
    )
    migration_review.add_argument("--evidence", action="append", default=[])
    migration_review.add_argument("--risk-accepted", action="store_true")
    migration_review.add_argument("--note", default="已复核迁移状态")

    show = sub.add_parser("show", help="输出当前机器状态")
    task_dir_argument(show)

    validate = sub.add_parser("validate", help="校验机器状态与 status.md 一致性")
    task_dir_argument(validate)

    update = sub.add_parser("update", help="更新文档状态、未确认项、阻塞和阶段内状态")
    task_dir_argument(update)
    update.add_argument("--document-state", choices=sorted(DOCUMENT_STATES))
    update.add_argument("--open-items", type=int)
    update.add_argument("--state", choices=sorted(STATES))
    update.add_argument("--evidence", action="append", default=[])
    update.add_argument("--add-blocker", action="append", default=[])
    update.add_argument("--resolve-blocker", action="append", default=[])
    update.add_argument("--clear-blockers", action="store_true")
    update.add_argument("--note", default="更新任务状态")

    start = sub.add_parser("start", help="通过门禁进入下一阶段或 Debug")
    task_dir_argument(start)
    start.add_argument(
        "--phase", required=True, choices=sorted(PHASES - {"close", "done"})
    )
    start.add_argument(
        "--debug-mode",
        choices=["diagnose", "fix"],
        help="进入 Debug 时必填：仅诊断或包含修复",
    )
    start.add_argument("--note")

    review = sub.add_parser("review", help="记录当前阶段 Grill/评审状态和证据")
    task_dir_argument(review)
    review.add_argument(
        "--status", required=True, choices=["in_progress", "completed"]
    )
    review.add_argument("--evidence", action="append", default=[])
    review.add_argument("--note")

    configure_debug = sub.add_parser(
        "configure-debug", help="为迁移的 Debug 状态明确诊断/修复授权"
    )
    task_dir_argument(configure_debug)
    configure_debug.add_argument("--mode", required=True, choices=["diagnose", "fix"])
    configure_debug.add_argument("--note")

    configure_script = sub.add_parser(
        "configure-script", help="为迁移的 Script 状态明确风险与目标环境"
    )
    task_dir_argument(configure_script)
    configure_script.add_argument(
        "--risk", required=True, choices=["low", "medium", "high"]
    )
    configure_script.add_argument(
        "--environment",
        required=True,
        choices=["local", "test", "staging", "production"],
    )
    configure_script.add_argument("--note")

    approve_script = sub.add_parser(
        "approve-script", help="记录生产 Script 的明确执行批准"
    )
    task_dir_argument(approve_script)
    approve_script.add_argument("--evidence", action="append", required=True)
    approve_script.add_argument("--note")

    complete = sub.add_parser(
        "complete", help="完成当前设计、实施、Debug 或 Script 阶段"
    )
    task_dir_argument(complete)
    complete.add_argument("--note")

    task = sub.add_parser("task", help="登记施工任务状态和证据")
    task_dir_argument(task)
    task.add_argument("--id", required=True)
    task.add_argument(
        "--status",
        required=True,
        choices=["planned", "in_progress", "completed", "blocked"],
    )
    task.add_argument("--evidence", action="append", default=[])
    task.add_argument("--next-task")
    task.add_argument("--clear-next", action="store_true")
    task.add_argument("--note")

    test = sub.add_parser("test", help="记录测试状态和证据")
    task_dir_argument(test)
    test.add_argument(
        "--result",
        required=True,
        choices=["running", "passed", "conditional", "failed"],
    )
    test.add_argument("--evidence", action="append", default=[])
    test.add_argument("--risk-accepted", action="store_true")
    test.add_argument("--note")

    close_request = sub.add_parser(
        "close-request", help="执行关闭门禁或发起未测试二次确认"
    )
    task_dir_argument(close_request)

    close_confirm = sub.add_parser("close-confirm", help="确认跳过测试并进入关闭阶段")
    task_dir_argument(close_confirm)
    close_confirm.add_argument("--token", required=True)
    close_confirm.add_argument("--note", default="用户已确认跳过测试并关闭")

    close_artifact = sub.add_parser(
        "close-artifact", help="记录 summary、AI 登记或知识沉淀结果"
    )
    task_dir_argument(close_artifact)
    close_artifact.add_argument(
        "--name", required=True, choices=sorted(CLOSE_ARTIFACT_STATUSES)
    )
    close_artifact.add_argument("--status", required=True)
    close_artifact.add_argument("--evidence", action="append", required=True)
    close_artifact.add_argument("--note")

    close_complete = sub.add_parser(
        "close-complete", help="完成文档收口后写入 done/100 percent"
    )
    task_dir_argument(close_complete)
    close_complete.add_argument("--note", default="开发流程已关闭")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = TaskStateStore(args.task_dir)
    try:
        if args.command == "init":
            state = store.initialize(
                system=args.system,
                title=args.title,
                phase=args.phase,
                branch=args.branch,
                debug_mode=args.debug_mode,
                script_risk=args.script_risk,
                script_environment=args.script_environment,
            )
        elif args.command == "migrate":
            state = store.migrate(system=args.system, title=args.title)
        elif args.command == "migration-review":
            state = store.review_migration(
                test_state=args.test_state,
                evidence=args.evidence,
                risk_accepted=args.risk_accepted,
                note=args.note,
            )
        elif args.command == "show":
            state = store.load()
        elif args.command == "validate":
            errors = store.validate_consistency()
            if errors:
                for error in errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print("task-state valid")
            return 0
        elif args.command == "update":
            state = store.update(
                document_state=args.document_state,
                open_items=args.open_items,
                state_name=args.state,
                evidence=args.evidence,
                add_blockers=args.add_blocker,
                resolve_blockers=args.resolve_blocker,
                clear_blockers=args.clear_blockers,
                note=args.note,
            )
        elif args.command == "start":
            state = store.start_phase(
                args.phase,
                debug_mode=args.debug_mode,
                note=args.note,
            )
        elif args.command == "review":
            state = store.record_review(
                args.status,
                evidence=args.evidence,
                note=args.note,
            )
        elif args.command == "configure-debug":
            state = store.configure_debug(args.mode, note=args.note)
        elif args.command == "configure-script":
            state = store.configure_script(
                args.risk,
                args.environment,
                note=args.note,
            )
        elif args.command == "approve-script":
            state = store.approve_script(args.evidence, note=args.note)
        elif args.command == "complete":
            state = store.complete_phase(note=args.note)
        elif args.command == "task":
            state = store.record_task(
                args.id,
                args.status,
                evidence=args.evidence,
                next_task=args.next_task,
                clear_next=args.clear_next,
                note=args.note,
            )
        elif args.command == "test":
            state = store.record_test(
                args.result,
                evidence=args.evidence,
                risk_accepted=args.risk_accepted,
                note=args.note,
            )
        elif args.command == "close-request":
            state, token = store.request_close()
            if token:
                print("WARNING: 测试未执行；关闭只表示流程收口，不表示质量验证通过。")
                print("用户明确确认后再运行 close-confirm。")
                print(f"confirmation_token={token}")
        elif args.command == "close-confirm":
            state = store.confirm_close(args.token, note=args.note)
        elif args.command == "close-artifact":
            state = store.record_close_artifact(
                args.name,
                args.status,
                evidence=args.evidence,
                note=args.note,
            )
        elif args.command == "close-complete":
            state = store.complete_close(note=args.note)
        else:
            raise TaskStateError(f"未知命令：{args.command}")
    except TaskStateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
