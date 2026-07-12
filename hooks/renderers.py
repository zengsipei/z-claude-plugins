#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件 -> 卡片 渲染注册表（候选 B，对应 issue #2）。

职责单一：只把 hook 事件「渲染成飞书卡片 dict」，不碰发送、不碰启用判断。
每个 renderer 是纯函数，只吃 payload，返回 4 元组 (color, title, primary, event_details)：

- color: 卡片头模板色（orange / green / blue / grey ...）
- title: 卡片头标题（事件专属）
- primary: 主块（高亮）文本 —— 事件的核心信息
- event_details: 可选，事件专属的附加详情（多数事件为 None）；
                 交由 assemble_card 归入「详情块」（hr + 灰字降级）

共享 assemble_card 负责统一拼装：主块高亮 + hr + 灰字详情块
（项目 / 会话 / 时间）。新增一个事件通知 = 写一个 renderer + 在 RENDERERS 注册一行，
不必改 assemble_card 主干，也不碰发送/启用逻辑。

仅依赖标准库，零网络。
"""

import os
import time


def _project(payload):
    cwd = payload.get("cwd") or ""
    return os.path.basename(cwd.rstrip("/\\")) or "未知项目"


def render_notification(payload):
    msg = payload.get("message") or "需要你的关注"
    return ("orange", "🔔 待处理", "**%s**" % msg, None)


def render_stop(payload):
    return ("green", "✅ 已完成", "Claude 已完成本轮回复，等待你的下一步。", None)


def render_subagentstop(payload):
    return ("blue", "🧩 子任务完成", "一个子代理任务已结束。", None)


def render_user_prompt_submit(payload):
    p = (payload.get("prompt") or "").strip().replace("\n", " ")
    if len(p) > 60:
        p = p[:60] + "…"
    return ("grey", "📝 已提交", "已提交：%s" % (p or "(空)"), None)


def render_unknown(event, payload):
    """未注册事件的兜底：灰底、标题带事件名，主块说明未知事件。"""
    return ("grey", "ℹ️ %s" % event, "事件：%s" % event, None)


# 平铺注册表：事件名 -> 只吃 payload 的纯函数 renderer
RENDERERS = {
    "Notification": render_notification,
    "Stop": render_stop,
    "SubagentStop": render_subagentstop,
    "UserPromptSubmit": render_user_prompt_submit,
}


def assemble_card(event, payload):
    """按事件选 renderer，拼出完整飞书卡片 dict（不发送）。

    认知分层：主块（primary）高亮突出，详情块（项目/会话/时间）用 hr 分隔 +
    灰字降级，让核心信息一眼可见。
    """
    renderer = RENDERERS.get(event)
    if renderer:
        color, title, primary, event_details = renderer(payload)
    else:
        color, title, primary, event_details = render_unknown(event, payload)

    project = _project(payload)
    details = []
    if event_details:
        details.append(event_details)
    details.append("---")
    details.append("📁 项目：**%s**" % project)
    sid = payload.get("session_id") or ""
    if sid:
        details.append("🔗 会话：`%s`" % sid[:8])
    details.append("🕐 %s" % time.strftime("%H:%M:%S"))

    elements = [
        {"tag": "div", "text": {"tag": "lark_md", "content": primary}},
        {"tag": "hr"},
        {"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(details)},
         "text_size": "sm", "text_color": "grey"},
    ]
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": color,
            "title": {"tag": "plain_text", "content": "%s · %s" % (title, project)},
        },
        "elements": elements,
    }


# 编排层管道集成用名（候选 C 集成点：card = renderers.build_card(...)）
build_card = assemble_card
