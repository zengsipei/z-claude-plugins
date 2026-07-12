#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Code -> 飞书应用私聊通知（z-cc-plugin 插件）
只用 Python 标准库，无需 pip 安装任何依赖。

职责拆分（见 issue #1 深化设计）：
- feishu_client.FeishuClient：飞书 API 面（鉴权 + 发卡片），深模块（候选 A）。
- renderers：事件 -> 卡片 dict 渲染注册表（候选 B），纯函数、零网络。
- feishu_config：配置加载 + 启用/凭据判定（候选 D），纯函数、零网络。
- 本文件：只做编排（读 stdin -> 判定启用/凭据 -> 渲染 -> 发送），并提供
  可替换的 sender 缝隙（候选 C）。

设计原则：无论如何都不阻断 Claude —— 任何异常都吞掉并以退出码 0 结束，
错误写到同目录 feishu_notify.log 方便排查。
"""

import sys
import os
import json
import time

from feishu_client import FeishuClient, FeishuError
from feishu_config import load_config, should_notify, has_credentials
import renderers


HERE = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(HERE, "feishu_notify.log")


def log(msg):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write("[%s] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
    except Exception:
        pass


def make_sender(cfg):
    """默认 sender：包真实 FeishuClient.send_card（候选 C）。

    与候选 A 的 transport 注入正交——这里注入的是「管道层 sender 闭包」，
    内部仍走 FeishuClient（其 transport 可再被单测注入）。
    """
    client = FeishuClient(
        cfg["app_id"], cfg["app_secret"],
        cfg["receive_id"], cfg["receive_id_type"],
    )

    def sender(card):
        client.send_card(card)

    return sender


def main(sender=None):
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

    if not has_credentials(cfg):
        log("配置缺失（app_id/app_secret/receive_id），跳过。event=%s" % event)
        return 0

    try:
        card = renderers.build_card(event, payload)
        if sender is None:
            sender = make_sender(cfg)
        sender(card)
        log("已发送通知: %s" % event)
    except FeishuError as e:
        log("通知失败: %s" % e)
    except Exception as e:
        log("发送失败: %r" % e)

    return 0


if __name__ == "__main__":
    # 永远返回 0，绝不阻断 Claude
    sys.exit(main())
