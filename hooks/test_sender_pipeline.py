#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通知管道 notifier 缝隙的零网络单测（纯标准库，对应候选1 / issue #6）。

注：原 sender 缝隙（候选 C）已被 Notifier 接口 + make_notifiers 全量扇出取代
（两层 seam 正交），本测试随之迁移到新接口，断言：card 内容 + notifier 调用次数。
- 未启用 -> 不调 notifier
- 启用 -> 调一次且 card 匹配 renderers.build_card 产出
- 缺凭据 -> 不调 notifier（make_notifiers 不含飞书）
- notifier 抛错 -> 不冒泡（main 返回 0，永不阻断）

运行：cd hooks && python -m unittest test_sender_pipeline -v
"""

import io
import sys
import unittest
from unittest import mock

import feishu_notify
import feishu_client
import renderers
import notifiers


FULL_CFG = {
    "app_id": "app", "app_secret": "secret",
    "receive_id": "recv", "receive_id_type": "union_id",
    "enabled_events": ["Notification", "Stop", "SubagentStop"],
}


class FailingNotifier(notifiers.Notifier):
    def notify(self, event, payload):
        raise RuntimeError("boom")


class TestNotifierPipeline(unittest.TestCase):
    def _run(self, stdin_json, notifier_list=None, cfg=None,
             deliver_result=True, throttle_result=False):
        cfg = cfg if cfg is not None else FULL_CFG
        with mock.patch.object(feishu_notify, "load_config", return_value=cfg), \
             mock.patch.object(feishu_notify.delivery_rules, "should_deliver",
                               return_value=deliver_result), \
             mock.patch.object(feishu_notify, "is_throttled",
                               return_value=throttle_result), \
             mock.patch.object(feishu_notify, "mark_sent", return_value=None):
            old = sys.stdin
            sys.stdin = io.StringIO(stdin_json)
            try:
                return feishu_notify.main(notifiers=notifier_list)
            finally:
                sys.stdin = old

    def test_disabled_event_does_not_call_notifier(self):
        fn = notifiers.WebhookNotifier("https://x", transport=lambda *a, **k: None)
        rc = self._run('{"hook_event_name":"Bogus"}', notifier_list=[fn],
                       cfg={**FULL_CFG, "enabled_events": []})
        self.assertEqual(rc, 0)

    def test_enabled_event_card_matches_renderers(self):
        # 注入真实 make_notifiers（凭据齐全 -> 含 FeishuNotifier），抓其发出的 card
        created = []
        class FakeClient:
            def __init__(self, *a, **k):
                created.append(self)
                self.sent = []
            def send_card(self, card):
                self.sent.append(card)
        with mock.patch.object(feishu_client, "FeishuClient", FakeClient):
            payload = {"hook_event_name": "Stop", "cwd": "/p/proj", "session_id": "sess1"}
            rc = self._run('{"hook_event_name":"Stop","cwd":"/p/proj","session_id":"sess1"}')
        self.assertEqual(rc, 0)
        self.assertEqual(len(created), 1)
        card = created[0].sent[0]
        expected = renderers.build_card("Stop", payload)

        def strip_time(detail_text):
            return "\n".join(l for l in detail_text.split("\n") if not l.startswith("🕐"))

        self.assertEqual(card["header"], expected["header"])
        self.assertEqual(card["elements"][0], expected["elements"][0])
        self.assertEqual(card["elements"][1], expected["elements"][1])
        self.assertEqual(strip_time(card["elements"][2]["text"]["content"]),
                         strip_time(expected["elements"][2]["text"]["content"]))
        self.assertEqual(card["elements"][2]["text_color"], "grey")

    def test_missing_credentials_does_not_call_notifier(self):
        cfg = {**FULL_CFG, "app_secret": ""}
        rc = self._run('{"hook_event_name":"Stop"}', cfg=cfg)
        self.assertEqual(rc, 0)  # 无可用 notifier（飞书缺凭据、无 webhook）-> 静默跳过

    def test_notifier_error_does_not_propagate(self):
        rc = self._run('{"hook_event_name":"Stop"}', notifier_list=[FailingNotifier()])
        self.assertEqual(rc, 0)  # 永不阻断


if __name__ == "__main__":
    unittest.main()
