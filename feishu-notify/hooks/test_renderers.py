#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
renderers 注册表 + assemble_card 的零网络单测（纯标准库，对应候选 B / issue #2；
候选3 扩展见 issue #8）。

运行：cd hooks && python -m unittest test_renderers -v
"""

import unittest

import renderers
from feishu_config import DEFAULT_ENABLED_EVENTS


class TestRenderersRegistry(unittest.TestCase):
    def test_registered_events_have_renderers(self):
        # 遍历注册表而不列事件名 —— 事件集本身由事实守卫 `feishu.hook-events`
        # 钉在 hooks.json 上，这里再抄一份名字就成了第三份副本。
        for ev, fn in renderers.RENDERERS.items():
            # renderer 只吃 payload，返回 4 元组
            self.assertEqual(len(fn({"cwd": "/x/proj"})), 4)

    def test_unknown_event_uses_fallback(self):
        # 未注册事件走 render_unknown，不抛错、灰底
        card = renderers.assemble_card("SomeNewEvent", {"cwd": "/x/proj"})
        self.assertEqual(card["header"]["template"], "grey")
        self.assertIn("SomeNewEvent", card["header"]["title"]["content"])

    def test_renderers_are_pure_functions(self):
        # 同输入两次调用结果一致，且只依赖 payload
        a = renderers.render_notification({"message": "m"})
        b = renderers.render_notification({"message": "m"})
        self.assertEqual(a, b)

    # ---- 候选3（issue #8）：默认启用开关 ----
    # 「8 个事件是否都注册了」不再在这里硬编码期望集 —— 迁至事实守卫
    # `feishu.hook-events`（声明处是 hooks.json 的事件键，RENDERERS 是副本）。

    def test_default_enabled_opens_session_start_end(self):
        self.assertIn("SessionStart", DEFAULT_ENABLED_EVENTS)
        self.assertIn("SessionEnd", DEFAULT_ENABLED_EVENTS)

    def test_default_enabled_closes_userprompt_pre_post_tool(self):
        # 三者默认关，避免刷屏；需要时自行加入 enabled_events
        self.assertNotIn("UserPromptSubmit", DEFAULT_ENABLED_EVENTS)
        self.assertNotIn("PreToolUse", DEFAULT_ENABLED_EVENTS)
        self.assertNotIn("PostToolUse", DEFAULT_ENABLED_EVENTS)


class TestRendererOutputs(unittest.TestCase):
    def test_notification(self):
        color, title, primary, details = renderers.render_notification({"message": "hi"})
        self.assertEqual(color, "orange")
        self.assertEqual(title, "🔔 待处理")
        self.assertEqual(primary, "**hi**")
        self.assertIsNone(details)

    def test_stop(self):
        color, title, primary, details = renderers.render_stop({})
        self.assertEqual((color, title), ("green", "✅ 已完成"))
        self.assertIn("完成", primary)
        self.assertIsNone(details)

    def test_subagentstop(self):
        color, title, primary, details = renderers.render_subagentstop({})
        self.assertEqual((color, title), ("blue", "🧩 子任务完成"))
        self.assertIsNone(details)

    def test_user_prompt_submit_truncates(self):
        long = "x" * 100
        color, title, primary, details = renderers.render_user_prompt_submit({"prompt": long})
        self.assertEqual(title, "📝 已提交")
        self.assertTrue(primary.endswith("…"))
        self.assertNotIn("\n", primary)
        self.assertIsNone(details)

    def test_user_prompt_submit_empty(self):
        color, title, primary, details = renderers.render_user_prompt_submit({})
        self.assertEqual(primary, "已提交：(空)")

    def test_render_unknown_shape(self):
        color, title, primary, details = renderers.render_unknown("BogusEvent", {})
        self.assertEqual(color, "grey")
        self.assertIn("BogusEvent", title)
        self.assertIn("BogusEvent", primary)

    # ---- 候选3：新 4 个 renderer 形状 ----

    def test_session_start_includes_source(self):
        color, title, primary, details = renderers.render_session_start({"source": "startup"})
        self.assertEqual(title, "🚀 会话开始")
        self.assertIn("startup", primary)

    def test_session_end(self):
        color, title, primary, details = renderers.render_session_end({})
        self.assertEqual(title, "🌙 会话结束")

    def test_pre_tool_use_mentions_tool(self):
        color, title, primary, details = renderers.render_pre_tool_use({"tool_name": "Bash"})
        self.assertEqual(title, "⚠️ 即将执行")
        self.assertIn("Bash", primary)

    def test_post_tool_use_mentions_tool(self):
        color, title, primary, details = renderers.render_post_tool_use({"tool_name": "Read"})
        self.assertEqual(title, "🛠 已执行")
        self.assertIn("Read", primary)

    def test_render_message_falls_back_to_unknown(self):
        out = renderers.render_message("TotallyNew", {})
        self.assertEqual(out[0], "grey")
        self.assertIn("TotallyNew", out[1])


class TestAssembleCard(unittest.TestCase):
    def test_structure_and_layering(self):
        payload = {"cwd": "/home/z/proj", "session_id": "abc123def", "message": "需要确认"}
        card = renderers.build_card("Notification", payload)
        # 头部：颜色 + 标题（事件 · 项目）
        self.assertEqual(card["header"]["template"], "orange")
        self.assertEqual(card["header"]["title"]["content"], "🔔 待处理 · proj")
        # 元素：主块(高亮) + hr + 详情块(灰字降级)
        els = card["elements"]
        self.assertEqual(els[0]["text"]["content"], "**需要确认**")
        self.assertEqual(els[1]["tag"], "hr")
        detail = els[2]["text"]["content"]
        self.assertIn("📁 项目：**proj**", detail)
        self.assertIn("🔗 会话：`abc123de`", detail)
        self.assertIn("🕐", detail)
        self.assertEqual(els[2]["text_color"], "grey")
        self.assertEqual(els[2]["text_size"], "sm")

    def test_unknown_event_card(self):
        card = renderers.build_card("Nope", {"cwd": "/p"})
        self.assertEqual(card["header"]["template"], "grey")
        self.assertIn("Nope", card["header"]["title"]["content"])

    def test_stop_card_has_no_session_when_absent(self):
        card = renderers.build_card("Stop", {"cwd": "/p/proj"})
        detail = card["elements"][2]["text"]["content"]
        self.assertNotIn("🔗 会话", detail)
        self.assertIn("📁 项目：**proj**", detail)

    def test_build_card_still_works(self):
        card = renderers.build_card("Stop", {"session_id": "abc12345", "cwd": "/p/x"})
        self.assertEqual(card["header"]["template"], "green")
        self.assertIn("abc12345", card["elements"][2]["text"]["content"])


if __name__ == "__main__":
    unittest.main()
