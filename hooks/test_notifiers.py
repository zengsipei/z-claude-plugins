#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
notifiers 单测（候选1，issue #6）：Notifier 接口 + 飞书/Webhook 适配器 +
make_notifiers 全量扇出 + 故障隔离。

运行：cd hooks && python -m unittest test_notifiers -v
"""
import unittest
from unittest import mock

import notifiers
import feishu_client
import feishu_notify


class FakeWebhookTransport:
    def __init__(self):
        self.calls = []
    def __call__(self, url, body, timeout=8):
        self.calls.append({"url": url, "body": body, "timeout": timeout})
        return "ok"


def _boom(url, body, timeout=8):
    raise RuntimeError("boom")


class TestFeishuNotifier(unittest.TestCase):
    CFG = {
        "app_id": "app", "app_secret": "secret",
        "receive_id": "recv", "receive_id_type": "union_id",
    }

    def test_notify_sends_card_via_client(self):
        created = []
        class FakeFeishuClient:
            def __init__(self, *a, **k):
                self.args = (a, k)
                self.sent = []
                created.append(self)
            def send_card(self, card):
                self.sent.append(card)
        with mock.patch.object(feishu_client, "FeishuClient", FakeFeishuClient):
            n = notifiers.FeishuNotifier(self.CFG)
            n.notify("Stop", {"session_id": "abc12345"})
        self.assertEqual(len(created), 1)
        self.assertEqual(len(created[0].sent), 1)
        card = created[0].sent[0]
        self.assertEqual(card["header"]["template"], "green")


class TestWebhookNotifier(unittest.TestCase):
    def test_notify_posts_rendered_message(self):
        t = FakeWebhookTransport()
        n = notifiers.WebhookNotifier("https://hook/x", transport=t)
        n.notify("Stop", {})
        self.assertEqual(len(t.calls), 1)
        body = t.calls[0]["body"]
        self.assertEqual(body["event"], "Stop")
        self.assertEqual(body["title"], "✅ 已完成")
        self.assertIn("Claude", body["text"])


class TestMakeNotifiers(unittest.TestCase):
    BASE = {
        "app_id": "app", "app_secret": "secret",
        "receive_id": "recv", "receive_id_type": "union_id",
        "enabled_events": ["Stop"],
    }

    def test_feishu_added_when_credentials_present(self):
        ns = notifiers.make_notifiers(self.BASE)
        self.assertEqual(len(ns), 1)
        self.assertIsInstance(ns[0], notifiers.FeishuNotifier)

    def test_feishu_skipped_when_credentials_missing(self):
        ns = notifiers.make_notifiers({**self.BASE, "app_id": "", "app_secret": ""})
        self.assertEqual(ns, [])

    def test_webhook_added_from_config(self):
        cfg = {**self.BASE, "notifiers": [
            {"type": "webhook", "enabled": True, "url": "https://hook/x"}
        ]}
        ns = notifiers.make_notifiers(cfg)
        self.assertEqual(len(ns), 2)
        self.assertIsInstance(ns[1], notifiers.WebhookNotifier)

    def test_webhook_disabled_skipped(self):
        cfg = {**self.BASE, "notifiers": [
            {"type": "webhook", "enabled": False, "url": "https://hook/x"}
        ]}
        ns = notifiers.make_notifiers(cfg)
        self.assertEqual(len(ns), 1)  # 仅飞书
        self.assertIsInstance(ns[0], notifiers.FeishuNotifier)

    def test_unknown_type_ignored(self):
        cfg = {**self.BASE, "notifiers": [{"type": "email", "url": "x"}]}
        ns = notifiers.make_notifiers(cfg)
        self.assertEqual(len(ns), 1)


class TestFaultIsolation(unittest.TestCase):
    def test_deliver_isolates_failing_notifier(self):
        good = notifiers.WebhookNotifier("https://ok", transport=FakeWebhookTransport())

        class Recorder(notifiers.Notifier):
            def __init__(self):
                self.called = False
            def notify(self, event, payload):
                self.called = True

        rec = Recorder()
        any_sent = feishu_notify.deliver(
            "Stop", {}, [good, notifiers.WebhookNotifier("https://bad", transport=_boom), rec])
        self.assertTrue(any_sent)     # good 成功
        self.assertTrue(rec.called)   # bad 失败不阻断后续 notifier


if __name__ == "__main__":
    unittest.main()
