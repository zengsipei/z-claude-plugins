#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
delivery_rules 单测（候选4，issue #9）：免打扰 / 投递规则纯函数。

运行：cd hooks && python -m unittest test_delivery_rules -v
"""
import unittest

import delivery_rules


class TestBlockedProjects(unittest.TestCase):
    CFG = {"delivery_rules": {"blocked_projects": ["/secret/", "/client/"]}}

    def test_cwd_prefix_blocked(self):
        ctx = {"cwd": "/secret/project", "hour": 12}
        self.assertFalse(delivery_rules.should_deliver("Stop", ctx, self.CFG))

    def test_cwd_not_blocked(self):
        ctx = {"cwd": "/public/project", "hour": 12}
        self.assertTrue(delivery_rules.should_deliver("Stop", ctx, self.CFG))

    def test_empty_blocklist_allows(self):
        cfg = {"delivery_rules": {"blocked_projects": []}}
        ctx = {"cwd": "/anything", "hour": 12}
        self.assertTrue(delivery_rules.should_deliver("Stop", ctx, cfg))


class TestQuietHours(unittest.TestCase):
    CFG = {"delivery_rules": {"quiet_hours": {"start": 22, "end": 8}, "bypass_events": ["Notification"]}}

    def test_quiet_hour_refused(self):
        ctx = {"cwd": "/p", "hour": 23}
        self.assertFalse(delivery_rules.should_deliver("Stop", ctx, self.CFG))

    def test_quiet_hour_cross_midnight_refused(self):
        ctx = {"cwd": "/p", "hour": 7}
        self.assertFalse(delivery_rules.should_deliver("Stop", ctx, self.CFG))

    def test_quiet_hour_boundary_start_included(self):
        ctx = {"cwd": "/p", "hour": 22}
        self.assertFalse(delivery_rules.should_deliver("Stop", ctx, self.CFG))

    def test_quiet_hour_boundary_end_excluded(self):
        ctx = {"cwd": "/p", "hour": 8}
        self.assertTrue(delivery_rules.should_deliver("Stop", ctx, self.CFG))

    def test_daytime_allowed(self):
        ctx = {"cwd": "/p", "hour": 15}
        self.assertTrue(delivery_rules.should_deliver("Stop", ctx, self.CFG))

    def test_non_wrap_quiet(self):
        cfg = {"delivery_rules": {"quiet_hours": {"start": 12, "end": 14}}}
        self.assertFalse(delivery_rules.should_deliver("Stop", {"cwd": "/p", "hour": 13}, cfg))
        self.assertTrue(delivery_rules.should_deliver("Stop", {"cwd": "/p", "hour": 15}, cfg))

    def test_bypass_event_ignores_quiet(self):
        # Notification 绕开 quiet_hours，但仍受项目黑名单约束
        ctx = {"cwd": "/p", "hour": 23}
        self.assertTrue(delivery_rules.should_deliver("Notification", ctx, self.CFG))

    def test_bypass_event_still_blocked_by_project(self):
        cfg = {"delivery_rules": {
            "quiet_hours": {"start": 22, "end": 8},
            "blocked_projects": ["/secret/"],
            "bypass_events": ["Notification"],
        }}
        ctx = {"cwd": "/secret/x", "hour": 23}
        self.assertFalse(delivery_rules.should_deliver("Notification", ctx, cfg))


class TestNoRules(unittest.TestCase):
    def test_default_allows(self):
        ctx = {"cwd": "/p", "hour": 3}
        self.assertTrue(delivery_rules.should_deliver("Stop", ctx, {}))

    def test_missing_hour_uses_local(self):
        # 不传 hour 不应抛错（用运行时本地小时）
        ctx = {"cwd": "/p"}
        self.assertTrue(delivery_rules.should_deliver("Stop", ctx, {}))


if __name__ == "__main__":
    unittest.main()
