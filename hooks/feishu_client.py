#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FeishuClient 深模块：收口飞书 API 面（鉴权 + 发卡片）。

只依赖标准库。内部把 urllib 错误与 `code != 0` 统一包成 FeishuError，
对调用方隐藏 urllib 细节。token 每次现取、无状态。

来源：improve-codebase-architecture 评审候选 A（把散落的 http_post / get_token /
send_message 收成 real seam）。设计约束见 docs/adr/0001-*.md。
"""

import json

import urllib.request
import urllib.error

FEISHU_BASE = "https://open.feishu.cn/open-apis"


class FeishuError(Exception):
    """飞书 API 调用失败的统一错误（隐藏 urllib 细节）。"""
    pass


def _real_post(url, headers, body):
    """真实传输：urllib POST，HTTP/网络错误统一转成 FeishuError。"""
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = ""
        try:
            raw = e.read().decode("utf-8", "replace")
        except Exception:
            pass
        raise FeishuError("HTTP %s: %s" % (e.code, raw))
    except urllib.error.URLError as e:
        raise FeishuError("网络错误: %r" % e)


class FeishuClient:
    """飞书 API 的窄接口深模块。"""

    def __init__(self, app_id, app_secret, receive_id, receive_id_type, transport=None):
        self.app_id = app_id
        self.app_secret = app_secret
        self.receive_id = receive_id
        self.receive_id_type = receive_id_type
        # transport 可注入（默认真实 urllib），便于零网络单测
        self._post = transport or _real_post

    def get_token(self):
        url = FEISHU_BASE + "/auth/v3/tenant_access_token/internal"
        r = self._post(url, {"Content-Type": "application/json"},
                       {"app_id": self.app_id, "app_secret": self.app_secret})
        if r.get("code") != 0:
            raise FeishuError("获取 token 失败: %s" % r)
        return r["tenant_access_token"]

    def send_card(self, card):
        token = self.get_token()
        url = "%s/im/v1/messages?receive_id_type=%s" % (FEISHU_BASE, self.receive_id_type)
        headers = {
            "Authorization": "Bearer %s" % token,
            "Content-Type": "application/json; charset=utf-8",
        }
        body = {
            "receive_id": self.receive_id,
            "msg_type": "interactive",
            "content": json.dumps(card, ensure_ascii=False),
        }
        r = self._post(url, headers, body)
        if r.get("code") != 0:
            raise FeishuError("发送消息失败: %s" % r)
        return r
