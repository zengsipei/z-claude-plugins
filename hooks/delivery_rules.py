#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
免打扰 / 投递规则（候选4，对应 issue #9）。

独立纯函数 should_deliver(event, context, cfg)：context = {cwd, hour}。
规则（v1 只黑名单）：
- blocked_projects：cwd 前缀匹配任一即拒绝（bypass_events 不绕项目黑名单）。
- quiet_hours：{start, end} 免打扰时段，支持跨午夜环绕；bypass_events 中的事件绕开。

context 由编排层填充（cwd 来自 payload、hour 来自运行时本地小时）。
配置块 `delivery_rules` 保持扁平可读；未配置时一律允许投递。

管道位置：should_notify → should_deliver → is_throttled → render → send → mark_sent。
仅依赖标准库，零网络。
"""

import time


def _in_quiet(hour, quiet):
    """hour 是否落在免打扰时段（支持跨午夜环绕，如 start=22,end=8）。"""
    start = quiet.get("start")
    end = quiet.get("end")
    if start is None or end is None:
        return False
    if start <= end:
        return start <= hour < end
    # 跨午夜：hour >= start 或 hour < end（如 22<=h<24 或 0<=h<8）
    return hour >= start or hour < end


def should_deliver(event, context, cfg):
    """是否允许投递。返回 True/False。

    context: {"cwd": str, "hour": int(0-23)}。hour 缺省时用运行时本地小时。
    """
    rules = cfg.get("delivery_rules") or {}
    cwd = context.get("cwd") or ""
    hour = context.get("hour")
    if hour is None:
        hour = time.localtime().tm_hour

    # 1) 项目黑名单（bypass_events 不绕）
    for b in (rules.get("blocked_projects") or []):
        if cwd.startswith(b):
            return False

    # 2) 免打扰时段（bypass_events 绕开）
    quiet = rules.get("quiet_hours")
    if quiet:
        bypass = rules.get("bypass_events") or []
        if event not in bypass and _in_quiet(hour, quiet):
            return False

    return True
