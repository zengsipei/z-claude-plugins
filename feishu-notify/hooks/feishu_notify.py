#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Code -> 通知（z-claude-plugins 插件，多通道）。

只用 Python 标准库，无需 pip。职责拆分（见 issue #1 深化 + #5 架构地图）：
- feishu_client.FeishuClient：飞书 API 面（鉴权 + 发卡片），深模块（候选 A）。
- renderers：事件 -> 通道无关 4 元组，各 Notifier 自渲染（候选 B）。
- feishu_config：配置加载 + 启用判定（候选 D）。
- delivery_rules：免打扰 / 投递规则（候选4，issue #9）。
- throttle：节流 / 去重闸门（候选2，issue #7）。
- notifiers：Notifier 接口 + 多适配器 + 全量扇出（候选1，issue #6）。
- 本文件：编排（读 stdin -> 启用判定 -> 投递规则 -> 节流 -> 扇出发送 -> mark_sent）。

管道（锁定顺序，见地图 fog「候选2 与候选4 管道顺序 = 投递规则在前、节流在后」）：
    should_notify → should_deliver → is_throttled → render(各 notifier) → send → mark_sent

设计原则：无论如何都不阻断 Claude —— 任何异常都吞掉并以退出码 0 结束，
错误写到同目录 feishu_notify.log 方便排查。
"""

import sys
import os
import json
import time

from feishu_config import load_config, should_notify
import delivery_rules
from throttle import is_throttled, mark_sent
import notifiers as notifier_mod


HERE = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(HERE, "feishu_notify.log")


def log(msg):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write("[%s] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
    except Exception:
        pass


def build_context(payload):
    """填充投递规则 context：cwd 来自 payload，hour 来自运行时本地小时。"""
    return {
        "cwd": payload.get("cwd") or "",
        "hour": time.localtime().tm_hour,
    }


def deliver(event, payload, notifiers):
    """对单个事件扇出到所有 notifier，故障隔离（一个失败不阻断其它）。

    返回是否有任一 notifier 成功发送。
    """
    any_sent = False
    for n in notifiers:
        try:
            n.notify(event, payload)
            any_sent = True
        except Exception as e:
            log("notifier %s 发送失败: %r" % (type(n).__name__, e))
    return any_sent


def main(notifiers=None):
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception as e:
        log("解析 stdin 失败: %r" % e)
        return 0

    event = payload.get("hook_event_name") or "Unknown"
    cfg = load_config()

    if not should_notify(event, cfg):
        return 0  # 该事件未启用，静默跳过

    context = build_context(payload)
    if not delivery_rules.should_deliver(event, context, cfg):
        log("投递规则拒绝: %s (cwd=%s)" % (event, context["cwd"]))
        return 0

    if is_throttled(event, cfg):
        log("节流跳过: %s" % event)
        return 0

    if notifiers is None:
        notifiers = notifier_mod.make_notifiers(cfg)
    if not notifiers:
        log("无可用 notifier（配置缺失），跳过。event=%s" % event)
        return 0

    if deliver(event, payload, notifiers):
        mark_sent(event)
        log("已发送通知: %s" % event)
    return 0


if __name__ == "__main__":
    # 永远返回 0，绝不阻断 Claude
    sys.exit(main())
