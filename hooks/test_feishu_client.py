#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FeishuClient + 通知编排 的零网络单测（纯标准库）。

运行：cd hooks && python -m unittest test_feishu_client -v
"""
import sys
import io
import json
import unittest
from unittest import mock

from feishu_client import FeishuClient, FeishuError
import feishu_client
import feishu_notify
import notifiers


AUTH_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
IM_URL_PREFIX = "https://open.feishu.cn/open-apis/im/v1/messages"


class FakeTransport:
    """记录调用，按 URL 返回罐头 JSON，可配置失败。"""
    def __init__(self, token_resp=None, send_resp=None, raise_err=False):
        self.calls = []
        self.token_resp = token_resp or {"code": 0, "tenant_access_token": "T-123"}
        self.send_resp = send_resp or {"code": 0, "data": {}}
        self.raise_err = raise_err

    def __call__(self, url, headers, body):
        self.calls.append({"url": url, "headers": headers, "body": body})
        if self.raise_err:
            raise FeishuError("模拟 HTTP 错误")
        if url == AUTH_URL:
            return self.token_resp
        if url.startswith(IM_URL_PREFIX):
            return self.send_resp
        return {"code": 0}


class TestFeishuClient(unittest.TestCase):
    def _client(self, transport=None):
        return FeishuClient("app", "secret", "recv", "union_id", transport=transport)

    def test_get_token_success(self):
        t = FakeTransport()
        c = self._client(t)
        tok = c.get_token()
        self.assertEqual(tok, "T-123")
        self.assertEqual(t.calls[0]["url"], AUTH_URL)
        self.assertEqual(t.calls[0]["body"]["app_id"], "app")

    def test_get_token_code_not_zero(self):
        t = FakeTransport(token_resp={"code": 1, "msg": "bad"})
        c = self._client(t)
        with self.assertRaises(FeishuError):
            c.get_token()

    def test_send_card_success(self):
        t = FakeTransport()
        c = self._client(t)
        card = {"header": {"title": {"content": "x"}}}
        c.send_card(card)
        # 先取 token，再发消息
        self.assertEqual(len(t.calls), 2)
        self.assertEqual(t.calls[0]["url"], AUTH_URL)
        im = t.calls[1]
        self.assertTrue(im["url"].startswith(IM_URL_PREFIX))
        self.assertIn("receive_id_type=union_id", im["url"])
        self.assertEqual(im["body"]["receive_id"], "recv")
        self.assertEqual(im["body"]["msg_type"], "interactive")
        self.assertEqual(json.loads(im["body"]["content"]), card)
        self.assertEqual(im["headers"]["Authorization"], "Bearer T-123")

    def test_send_card_code_not_zero(self):
        t = FakeTransport(send_resp={"code": 1, "msg": "nope"})
        c = self._client(t)
        with self.assertRaises(FeishuError):
            c.send_card({"a": 1})

    def test_transport_error_wrapped(self):
        t = FakeTransport(raise_err=True)
        c = self._client(t)
        with self.assertRaises(FeishuError):
            c.send_card({"a": 1})


class FakeNotifier(notifiers.Notifier):
    def __init__(self):
        self.calls = []
    def notify(self, event, payload):
        self.calls.append((event, payload))


class FailingNotifier(notifiers.Notifier):
    def notify(self, event, payload):
        raise RuntimeError("boom")


class TestNotifyOrchestration(unittest.TestCase):
    FULL_CFG = {
        "app_id": "app", "app_secret": "secret",
        "receive_id": "recv", "receive_id_type": "union_id",
        "enabled_events": ["Notification", "Stop", "SubagentStop"],
    }

    def _run_main(self, stdin_json, cfg=None, notifier_list=None,
                  throttle_result=False, deliver_result=True):
        """隔离测试编排管道：注入 notifiers，并把 throttle/delivery/mark_sent 做成可控。

        返回 (rc, mark_sent_mock)。
        """
        cfg = cfg if cfg is not None else self.FULL_CFG
        with mock.patch.object(feishu_notify, "load_config", return_value=cfg), \
             mock.patch.object(feishu_notify.delivery_rules, "should_deliver",
                               return_value=deliver_result) as sd, \
             mock.patch.object(feishu_notify, "is_throttled",
                               return_value=throttle_result) as it, \
             mock.patch.object(feishu_notify, "mark_sent", return_value=None) as mk:
            old = sys.stdin
            sys.stdin = io.StringIO(stdin_json)
            try:
                rc = feishu_notify.main(notifiers=notifier_list)
            finally:
                sys.stdin = old
        return rc, mk

    def test_disabled_event_returns_zero_no_send(self):
        fn = FakeNotifier()
        rc, mk = self._run_main('{"hook_event_name":"BogusEvent"}',
                                cfg={**self.FULL_CFG, "enabled_events": []},
                                notifier_list=[fn])
        self.assertEqual(rc, 0)
        self.assertEqual(fn.calls, [])
        mk.assert_not_called()

    def test_enabled_event_delivers_and_marks(self):
        fn = FakeNotifier()
        rc, mk = self._run_main('{"hook_event_name":"Stop","session_id":"abc123"}',
                                 notifier_list=[fn])
        self.assertEqual(rc, 0)
        self.assertEqual(fn.calls, [("Stop", {"hook_event_name": "Stop", "session_id": "abc123"})])
        mk.assert_called_once_with("Stop")

    def test_delivery_rule_rejection_skips(self):
        fn = FakeNotifier()
        rc, mk = self._run_main('{"hook_event_name":"Stop"}',
                                notifier_list=[fn], deliver_result=False)
        self.assertEqual(rc, 0)
        self.assertEqual(fn.calls, [])
        mk.assert_not_called()

    def test_throttle_skip_skips(self):
        fn = FakeNotifier()
        rc, mk = self._run_main('{"hook_event_name":"Stop"}',
                                notifier_list=[fn], throttle_result=True)
        self.assertEqual(rc, 0)
        self.assertEqual(fn.calls, [])
        mk.assert_not_called()

    def test_notifier_failure_does_not_propagate(self):
        rc, mk = self._run_main('{"hook_event_name":"Stop"}',
                                notifier_list=[FailingNotifier()])
        self.assertEqual(rc, 0)  # 永不阻断
        mk.assert_not_called()    # 没成功发送就不 mark_sent

    def test_enabled_event_builds_feishu_notifier_e2e(self):
        created = []
        class FakeClient:
            def __init__(self, *a, **k):
                created.append(self)
                self.sent = []
            def send_card(self, card):
                self.sent.append(card)
        with mock.patch.object(feishu_client, "FeishuClient", FakeClient):
            rc, mk = self._run_main('{"hook_event_name":"Stop"}')
        self.assertEqual(rc, 0)
        # 凭据齐全 → make_notifiers 构建了 FeishuNotifier → 真实走 FeishuClient
        self.assertEqual(len(created), 1)
        self.assertEqual(len(created[0].sent), 1)


if __name__ == "__main__":
    unittest.main()
