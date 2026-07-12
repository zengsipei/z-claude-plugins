#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多通道 Notifier 接口 + 适配器（候选1，对应 issue #6）。

把原 sender 缝隙升级为真实 Notifier 接口：
- Notifier.notify(event, payload)：通道无关窄接口；各适配器内部把「通道无关 4 元组」
  （renderers.render_message 产出）渲染成自己的格式。
- FeishuNotifier：复用 FeishuClient 深模块（守 ADR-0001，纯 stdlib）。
- WebhookNotifier：v1 第二通道，POST 一个简单 JSON 到任意 webhook（守 ADR-0001）。
- make_notifiers(cfg)：全量扇出——按配置构建所有启用的 notifier；飞书顶层配置不动，
  第二通道走独立的 `notifiers` 块。

故障隔离由编排层负责（对每个 notifier 单独 try/except，一个失败不阻断其它）。
仅依赖标准库，零网络（transport 可注入，便于单测）。
"""

import json
import urllib.request
import urllib.error

import renderers
import feishu_client
from feishu_config import has_credentials


class Notifier:
    """通道无关窄接口。子类实现 notify。"""

    def notify(self, event, payload):
        raise NotImplementedError


class FeishuNotifier(Notifier):
    """飞书通道：复用 FeishuClient 深模块发卡片（守 ADR-0001）。"""

    def __init__(self, cfg):
        self.cfg = cfg

    def notify(self, event, payload):
        card = renderers.build_card(event, payload)
        client = feishu_client.FeishuClient(
            self.cfg["app_id"], self.cfg["app_secret"],
            self.cfg["receive_id"], self.cfg["receive_id_type"],
        )
        client.send_card(card)


def _post_json(url, body, timeout=8):
    """真实 webhook 传输：urllib POST JSON，网络错误转 RuntimeError。"""
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "replace")
    except urllib.error.URLError as e:
        raise RuntimeError("Webhook 请求失败: %r" % e)


class WebhookNotifier(Notifier):
    """v1 第二通道：把 4 元组推到任意 webhook（守 ADR-0001，纯 stdlib）。"""

    def __init__(self, url, timeout=8, transport=None):
        self.url = url
        self.timeout = timeout
        self._post = transport or _post_json

    def notify(self, event, payload):
        color, title, primary, event_details = renderers.render_message(event, payload)
        body = {"event": event, "title": title, "text": primary}
        if event_details:
            body["details"] = event_details
        self._post(self.url, body, self.timeout)


def make_notifiers(cfg):
    """全量扇出：返回所有已启用、配置齐全的 notifier 列表（顺序：飞书优先）。

    飞书始终按顶层配置判定（凭据齐全才加入）；第二通道走 `notifiers` 块。
    任一通道缺失都不会让其它通道失效——故障隔离在编排层进一步兜底。
    """
    notifiers = []
    if has_credentials(cfg):
        notifiers.append(FeishuNotifier(cfg))
    for n in (cfg.get("notifiers") or []):
        if not n.get("enabled", True):
            continue
        ntype = n.get("type")
        if ntype == "webhook" and n.get("url"):
            notifiers.append(WebhookNotifier(n["url"], timeout=n.get("timeout", 8)))
        # 未知 type 静默忽略，不影响其它通道
    return notifiers
