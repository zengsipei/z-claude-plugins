#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
节流 / 去重闸门（候选2，对应 issue #7）。

独立深模块，纯函数 + 跨进程轻量状态文件（子进程无状态，ADR-0001）。
管道位置：should_notify → should_deliver → is_throttled → render → send → mark_sent。
仅发送成功后 mark_sent（不吞终态——窗口从「已发时间」算，过期即放行）。

v1：事件全局冷却（按事件名记时间戳），按项目留 seam；默认节流 Stop/SubagentStop，
Notification 等永远直通。状态落 hooks/.throttle_state.json（JSON、原子写无锁）。
仅依赖标准库，零网络。
"""

import os
import json
import time


HERE = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(HERE, ".throttle_state.json")

DEFAULT_WINDOW = 30  # 秒
DEFAULT_THROTTLED_EVENTS = ["Stop", "SubagentStop"]


def _now():
    return time.time()


def _cooldown_key(event):
    """状态字典的键。v1 仅按事件名冷却（全局）。

    按项目留 seam：未来要「按项目冷却」只需在此把 event 升维成
    (event, project) 之类，is_within_cooldown / mark_sent 都走这一个入口，
    其余逻辑不变。这是 v1 与 per-project 之间的唯一切换点。
    """
    return event


def read_state(path=STATE_PATH):
    """读状态文件；缺失/损坏返回空 dict（不抛，节流模块不应中断管道）。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def write_state(state, path=STATE_PATH):
    """原子写：先写临时文件再 os.replace，避免半截文件（无锁、够用）。"""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f)
    os.replace(tmp, path)


def is_within_cooldown(event, state, now, window=DEFAULT_WINDOW):
    """窗口从「已发时间」算；上次为空或窗口已过 → False（不节流、不吞终态）。"""
    last = state.get(_cooldown_key(event))
    if last is None:
        return False
    return (now - last) < window


def is_throttled(event, cfg, state=None, now=None,
                 window=DEFAULT_WINDOW, throttled_events=None):
    """该事件是否应被节流（跳过）。永远直通：不在 throttled_events 中的事件。

    cfg 的 `throttle` 块可覆盖 events / window；缺省用 DEFAULT_*。
    """
    if throttled_events is None:
        throttled_events = (cfg.get("throttle") or {}).get("events") or DEFAULT_THROTTLED_EVENTS
    if event not in throttled_events:
        return False
    if state is None:
        state = read_state()
    if now is None:
        now = _now()
    w = (cfg.get("throttle") or {}).get("window") or window
    return is_within_cooldown(event, state, now, w)


def mark_sent(event, now=None, path=STATE_PATH):
    """记录该事件已发送成功（仅发送成功后调用）。"""
    state = read_state(path)
    state[_cooldown_key(event)] = now if now is not None else _now()
    write_state(state, path)
