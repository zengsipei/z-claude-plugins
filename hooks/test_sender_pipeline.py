#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通知管道 sender 缝隙的零网络单测（纯标准库，对应候选 C / issue #3）。

断言：card 内容 + sender 调用次数。
- 未启用 -> 不调 sender
- 启用 -> 调一次且 card 匹配 renderers.build_card 产出
- 缺凭据 -> 不调 sender
- sender 抛 FeishuError -> 不冒泡（main 返回 0，永不阻断）

运行：cd hooks && python -m unittest test_sender_pipeline -v
"""

import io
import sys
import unittest
from unittest import mock

import feishu_notify
import renderers


FULL_CFG = {
    "app_id": "app", "app_secret": "secret",
    "receive_id": "recv", "receive_id_type": "union_id",
    "enabled_events": ["Notification", "Stop", "SubagentStop"],
}


class FakeSender:
    def __init__(self):
        self.calls = []

    def __call__(self, card):
        self.calls.append(card)


class TestSenderPipeline(unittest.TestCase):
    def _run(self, stdin_json, sender, cfg=None):
        cfg = cfg if cfg is not None else FULL_CFG
        with mock.patch.object(feishu_notify, "load_config", return_value=cfg):
            old = sys.stdin
            sys.stdin = io.StringIO(stdin_json)
            try:
                return feishu_notify.main(sender=sender)
            finally:
                sys.stdin = old

    def test_disabled_event_does_not_call_sender(self):
        sender = FakeSender()
        rc = self._run('{"hook_event_name":"Bogus"}',
                       sender, cfg={**FULL_CFG, "enabled_events": []})
        self.assertEqual(rc, 0)
        self.assertEqual(sender.calls, [])

    def test_enabled_event_calls_sender_once_with_expected_card(self):
        sender = FakeSender()
        payload = {"hook_event_name": "Stop", "cwd": "/p/proj", "session_id": "sess1"}
        rc = self._run('{"hook_event_name":"Stop","cwd":"/p/proj","session_id":"sess1"}',
                       sender)
        self.assertEqual(rc, 0)
        self.assertEqual(len(sender.calls), 1)
        # card 内容与 renderers.build_card 产出一致（集成契约），
        # 但卡片内的 🕐 时间戳由运行时决定、不可精确比对，比对时去掉时间行
        card = sender.calls[0]
        expected = renderers.build_card("Stop", payload)

        def strip_time(detail_text):
            return "\n".join(l for l in detail_text.split("\n") if not l.startswith("🕐"))

        self.assertEqual(card["header"], expected["header"])
        self.assertEqual(card["elements"][0], expected["elements"][0])
        self.assertEqual(card["elements"][1], expected["elements"][1])
        self.assertEqual(strip_time(card["elements"][2]["text"]["content"]),
                         strip_time(expected["elements"][2]["text"]["content"]))
        self.assertEqual(card["elements"][2]["text_color"], "grey")

    def test_missing_credentials_does_not_call_sender(self):
        sender = FakeSender()
        cfg = {**FULL_CFG, "app_secret": ""}
        rc = self._run('{"hook_event_name":"Stop"}', sender, cfg=cfg)
        self.assertEqual(rc, 0)
        self.assertEqual(sender.calls, [])

    def test_feishu_error_does_not_propagate(self):
        def boom(card):
            raise feishu_notify.FeishuError("boom")

        rc = self._run('{"hook_event_name":"Stop"}', boom)
        self.assertEqual(rc, 0)  # 永不阻断


if __name__ == "__main__":
    unittest.main()
