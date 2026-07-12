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
import feishu_notify


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


class TestNotifyOrchestration(unittest.TestCase):
    FULL_CFG = {
        "app_id": "app", "app_secret": "secret",
        "receive_id": "recv", "receive_id_type": "union_id",
        "enabled_events": ["Notification", "Stop", "SubagentStop"],
    }

    def _run_main(self, stdin_json, cfg=None, client_cls=None):
        cfg = cfg if cfg is not None else self.FULL_CFG
        with mock.patch.object(feishu_notify, "load_config", return_value=cfg):
            patcher = None
            if client_cls is not None:
                patcher = mock.patch.object(feishu_notify, "FeishuClient", client_cls)
                patcher.start()
            old = sys.stdin
            sys.stdin = io.StringIO(stdin_json)
            try:
                return feishu_notify.main()
            finally:
                sys.stdin = old
                if patcher is not None:
                    patcher.stop()

    def test_disabled_event_returns_zero_no_send(self):
        sent = []
        class FakeClient:
            def __init__(self, *a, **k):
                pass
            def send_card(self, card):
                sent.append(card)
        rc = self._run_main('{"hook_event_name":"BogusEvent"}',
                             cfg={**self.FULL_CFG, "enabled_events": []},
                             client_cls=FakeClient)
        self.assertEqual(rc, 0)
        self.assertEqual(sent, [])

    def test_enabled_event_sends_card(self):
        captured = {}
        class FakeClient:
            def __init__(self, *a, **k):
                captured["args"] = (a, k)
            def send_card(self, card):
                captured["card"] = card
        rc = self._run_main('{"hook_event_name":"Stop","session_id":"abc123"}',
                             client_cls=FakeClient)
        self.assertEqual(rc, 0)
        self.assertIn("card", captured)
        self.assertEqual(captured["args"][0][0], "app")

    def test_feishu_error_does_not_propagate(self):
        class FailClient:
            def __init__(self, *a, **k):
                pass
            def send_card(self, card):
                raise FeishuError("boom")
        rc = self._run_main('{"hook_event_name":"Stop"}', client_cls=FailClient)
        self.assertEqual(rc, 0)  # 永不阻断


if __name__ == "__main__":
    unittest.main()
