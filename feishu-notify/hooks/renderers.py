#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件 -> 通道无关消息 渲染注册表（候选 B，对应 issue #2；候选3 扩展见 issue #8）。

职责单一：把 hook 事件渲染成「通道无关 4 元组」(color, title, primary, event_details)。
各 Notifier 适配器（feishu / webhook / …）再把它转成自己的格式，互不干扰。

- color: 卡片头模板色（orange / green / blue / grey ...）
- title: 卡片头标题（事件专属）
- primary: 主块（高亮）文本 —— 事件的核心信息
- event_details: 可选，事件专属的附加详情（多数事件为 None）；
                 交由 assemble_card 归入「详情块」（hr + 灰字降级）

共享 assemble_card 负责统一拼装飞书卡片：主块高亮 + hr + 灰字详情块
（项目 / 会话 / 时间）。新增一个事件通知 = 写一个 renderer + 在 RENDERERS 注册一行，
不必改 assemble_card 主干，也不碰发送/启用逻辑。

仅依赖标准库，零网络。
"""

import os
import time


def _project(payload):
    cwd = payload.get("cwd") or ""
    return os.path.basename(cwd.rstrip("/\\")) or "未知项目"


def _tool_name(payload):
    return payload.get("tool_name") or "未知工具"


# ---- 各事件 renderer：只吃 payload，返回 4 元组 (color, title, primary, event_details) ----


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


def render_session_start(payload):
    src = payload.get("source")
    note = "（%s）" % src if src else ""
    return ("blue", "🚀 会话开始", "新的 Claude Code 会话已启动，开始为你工作。%s" % note, None)


def render_session_end(payload):
    return ("grey", "🌙 会话结束", "本次会话已结束。", None)


def render_pre_tool_use(payload):
    # 纯通知「即将执行 X」，不接回调（回调属候选6 范围）
    return ("orange", "⚠️ 即将执行", "即将执行工具：**%s**" % _tool_name(payload), None)


def render_post_tool_use(payload):
    return ("green", "🛠 已执行", "工具 **%s** 执行完毕。" % _tool_name(payload), None)


def render_unknown(event, payload):
    """未注册事件的兜底：灰底、标题带事件名，主块说明未知事件。"""
    return ("grey", "ℹ️ %s" % event, "事件：%s" % event, None)


# 平铺注册表：事件名 -> 只吃 payload 的纯函数 renderer
RENDERERS = {
    "Notification": render_notification,
    "Stop": render_stop,
    "SubagentStop": render_subagentstop,
    "UserPromptSubmit": render_user_prompt_submit,
    "SessionStart": render_session_start,
    "SessionEnd": render_session_end,
    "PreToolUse": render_pre_tool_use,
    "PostToolUse": render_post_tool_use,
}


def render_message(event, payload):
    """通道无关消息：返回 4 元组 (color, title, primary, event_details)。

    各 Notifier 适配器据此自渲染，飞书卡片只是其中一种形态。
    """
    renderer = RENDERERS.get(event)
    if renderer:
        return renderer(payload)
    return render_unknown(event, payload)


def assemble_card(event, payload):
    """飞书专属拼装：4 元组 -> 飞书卡片 dict（不发送）。

    认知分层：主块（primary）高亮突出，详情块（项目/会话/时间）用 hr 分隔 +
    灰字降级，让核心信息一眼可见。
    """
    color, title, primary, event_details = render_message(event, payload)

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
