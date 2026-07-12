#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Code -> 飞书应用私聊通知（wb-toolkit 插件）
只用 Python 标准库，无需 pip 安装任何依赖。

飞书 API 面（鉴权、发卡片、错误封装）已收口进独立深模块
`feishu_client.FeishuClient`，本文件只负责：读事件、建卡片、编排发送。

设计原则：无论如何都不阻断 Claude —— 任何异常都吞掉并以退出码 0 结束，
错误写到同目录 feishu_notify.log 方便排查。
"""

import sys
import os
import json
import time

from feishu_client import FeishuClient, FeishuError

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "feishu_config.json")
LOG_PATH = os.path.join(HERE, "feishu_notify.log")


def log(msg):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write("[%s] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
    except Exception:
        pass


def load_config():
    cfg = {
        "app_id": "",
        "app_secret": "",
        "receive_id": "",
        "receive_id_type": "open_id",  # open_id / user_id / union_id / email / chat_id
        # 想临时关掉某些事件的通知，把它从下面列表删掉即可
        "enabled_events": ["Notification", "Stop", "SubagentStop"],
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception as e:
            log("读取 feishu_config.json 失败: %r" % e)
    # 环境变量覆盖
    for k, env in [
        ("app_id", "FEISHU_APP_ID"),
        ("app_secret", "FEISHU_APP_SECRET"),
        ("receive_id", "FEISHU_RECEIVE_ID"),
        ("receive_id_type", "FEISHU_RECEIVE_ID_TYPE"),
    ]:
        v = os.environ.get(env)
        if v:
            cfg[k] = v
    return cfg


# ---- 事件 -> 卡片样式 映射（精简版） ----
EVENT_STYLE = {
    "Notification": ("orange", "🔔 待处理"),      # 需要权限确认 / 输入空闲，等你操作
    "Stop":         ("green",  "✅ 已完成"),      # Claude 完成一轮回复
    "SubagentStop": ("blue",   "🧩 子任务完成"),  # 子代理执行结束
    "UserPromptSubmit": ("grey", "📝 已提交"),
    "SessionStart": ("grey", "🚀 会话开始"),
}


def build_card(event, payload, cfg):
    color, title = EVENT_STYLE.get(event, ("grey", "ℹ️ %s" % event))
    cwd = payload.get("cwd") or ""
    project = os.path.basename(cwd.rstrip("/\\")) or "未知项目"

    lines = []
    if event == "Notification":
        msg = payload.get("message") or "需要你的关注"
        lines.append("**%s**" % msg)
    elif event == "Stop":
        lines.append("Claude 已完成本轮回复，等待你的下一步。")
    elif event == "SubagentStop":
        lines.append("一个子代理任务已结束。")
    elif event == "UserPromptSubmit":
        p = (payload.get("prompt") or "").strip().replace("\n", " ")
        if len(p) > 60:
            p = p[:60] + "…"
        lines.append("已提交：%s" % (p or "(空)"))
    else:
        lines.append("事件：%s" % event)

    lines.append("---")
    lines.append("📁 项目：**%s**" % project)
    sid = payload.get("session_id") or ""
    if sid:
        lines.append("🔗 会话：`%s`" % sid[:8])
    lines.append("🕐 %s" % time.strftime("%H:%M:%S"))

    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": color,
            "title": {"tag": "plain_text", "content": "%s · %s" % (title, project)},
        },
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(lines)}}
        ],
    }
    return card


def main():
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception as e:
        log("解析 stdin 失败: %r" % e)
        return 0

    event = payload.get("hook_event_name") or "Unknown"
    cfg = load_config()

    if event not in cfg.get("enabled_events", []):
        return 0  # 该事件未启用，静默跳过

    if not cfg.get("app_id") or not cfg.get("app_secret") or not cfg.get("receive_id"):
        log("配置缺失（app_id/app_secret/receive_id），跳过。event=%s" % event)
        return 0

    try:
        card = build_card(event, payload, cfg)
        client = FeishuClient(
            cfg["app_id"], cfg["app_secret"],
            cfg["receive_id"], cfg["receive_id_type"],
        )
        client.send_card(card)
        log("已发送通知: %s" % event)
    except FeishuError as e:
        log("通知失败: %s" % e)
    except Exception as e:
        log("发送失败: %r" % e)

    return 0


if __name__ == "__main__":
    # 永远返回 0，绝不阻断 Claude
    sys.exit(main())
