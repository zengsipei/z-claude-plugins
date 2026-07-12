#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
feishu_config 启用/凭据判定的零网络单测（纯标准库，对应候选 D / issue #4）。

断言 should_notify / has_credentials 为可预测纯函数。
load_config 仅做轻量冒烟（返回含 enabled_events 的 dict）。

运行：cd hooks && python -m unittest test_feishu_config -v
"""

import unittest

import feishu_config


class TestShouldNotify(unittest.TestCase):
    def test_enabled_event(self):
        cfg = {"enabled_events": ["Stop", "Notification"]}
        self.assertTrue(feishu_config.should_notify("Stop", cfg))
        self.assertTrue(feishu_config.should_notify("Notification", cfg))

    def test_disabled_event(self):
        cfg = {"enabled_events": ["Stop"]}
        self.assertFalse(feishu_config.should_notify("SubagentStop", cfg))

    def test_missing_enabled_events_key(self):
        self.assertFalse(feishu_config.should_notify("Stop", {}))

    def test_context_param_accepted_and_ignored(self):
        # context 是预留 seam，本期不改变判定结果
        cfg = {"enabled_events": ["Stop"]}
        self.assertTrue(feishu_config.should_notify("Stop", cfg, context={"cwd": "/x"}))


class TestHasCredentials(unittest.TestCase):
    FULL = {"app_id": "a", "app_secret": "s", "receive_id": "r"}

    def test_all_present(self):
        self.assertTrue(feishu_config.has_credentials(self.FULL))

    def test_missing_app_id(self):
        self.assertFalse(feishu_config.has_credentials({**self.FULL, "app_id": ""}))

    def test_missing_app_secret(self):
        self.assertFalse(feishu_config.has_credentials({**self.FULL, "app_secret": None}))

    def test_missing_receive_id(self):
        self.assertFalse(feishu_config.has_credentials({**self.FULL, "receive_id": ""}))

    def test_empty_dict(self):
        self.assertFalse(feishu_config.has_credentials({}))


class TestLoadConfigSmoke(unittest.TestCase):
    def test_returns_dict_with_enabled_events(self):
        cfg = feishu_config.load_config()
        self.assertIsInstance(cfg, dict)
        self.assertIn("enabled_events", cfg)
        self.assertIsInstance(cfg["enabled_events"], list)


if __name__ == "__main__":
    unittest.main()
