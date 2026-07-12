#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
throttle 单测（候选2，issue #7）：纯函数冷却判定 + 跨进程状态文件原子写。

运行：cd hooks && python -m unittest test_throttle -v
"""
import json
import os
import tempfile
import unittest

import throttle


class TestCooldown(unittest.TestCase):
    def test_no_previous_send_not_throttled(self):
        self.assertFalse(throttle.is_within_cooldown("Stop", {}, now=1000, window=30))

    def test_within_window_throttled(self):
        self.assertTrue(throttle.is_within_cooldown("Stop", {"Stop": 1000}, now=1010, window=30))

    def test_past_window_not_throttled(self):
        # 窗口从已发时间算，过期即放行（不吞终态）
        self.assertFalse(throttle.is_within_cooldown("Stop", {"Stop": 1000}, now=1031, window=30))

    def test_per_event_independent(self):
        state = {"Stop": 1000}
        self.assertTrue(throttle.is_within_cooldown("Stop", state, now=1010, window=30))
        self.assertFalse(throttle.is_within_cooldown("SubagentStop", state, now=1010, window=30))


class TestIsThrottled(unittest.TestCase):
    CFG = {"enabled_events": ["Stop"]}

    def test_non_throttled_event_always_passes(self):
        # Notification 不在默认节流集合，即便刚刚发过也不节流（永远直通）
        state = {"Notification": 1000}
        self.assertFalse(throttle.is_throttled("Notification", self.CFG, state=state, now=1005))

    def test_throttled_event_within_window(self):
        state = {"Stop": 1000}
        self.assertTrue(throttle.is_throttled("Stop", self.CFG, state=state, now=1010))

    def test_throttled_event_empty_state_passes(self):
        self.assertFalse(throttle.is_throttled("Stop", self.CFG, state={}, now=1000))

    def test_window_override_from_cfg(self):
        cfg = {"throttle": {"window": 5, "events": ["Stop"]}}
        state = {"Stop": 1000}
        self.assertFalse(throttle.is_throttled("Stop", cfg, state=state, now=1006))
        self.assertTrue(throttle.is_throttled("Stop", cfg, state=state, now=1003))

    def test_events_override_from_cfg(self):
        cfg = {"throttle": {"events": ["Notification"]}}
        state = {"Notification": 1000}
        self.assertTrue(throttle.is_throttled("Notification", cfg, state=state, now=1005))


class TestStateFile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, ".throttle_state.json")

    def test_mark_sent_and_read_roundtrip(self):
        throttle.mark_sent("Stop", now=1234, path=self.path)
        state = throttle.read_state(self.path)
        self.assertEqual(state.get("Stop"), 1234)

    def test_mark_sent_overwrites(self):
        throttle.mark_sent("Stop", now=1, path=self.path)
        throttle.mark_sent("Stop", now=2, path=self.path)
        self.assertEqual(throttle.read_state(self.path)["Stop"], 2)

    def test_read_missing_returns_empty(self):
        self.assertEqual(throttle.read_state(self.path), {})

    def test_write_atomic_no_tmp_leftover(self):
        throttle.write_state({"Stop": 9}, path=self.path)
        self.assertTrue(os.path.exists(self.path))
        self.assertFalse(os.path.exists(self.path + ".tmp"))


if __name__ == "__main__":
    unittest.main()
