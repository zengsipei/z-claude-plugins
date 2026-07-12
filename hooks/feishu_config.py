#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置加载 + 启用/凭据判定（候选 D，对应 issue #4）。

把「是否发送」的启用判断从 feishu_notify.main 收归到本模块，使管道编排层
只关心「判定 -> 渲染 -> 发送」的流程，而不掺杂配置细节：

- load_config():        读取 feishu_config.json + 环境变量覆盖（从 feishu_notify 迁入）
- should_notify(event, cfg, context=None): 只判启用（事件是否在 enabled_events）
- has_credentials(cfg): 只判凭据是否齐全

两个判定都是纯函数、互不耦合，便于零网络单测。

扩展点：should_notify 预留 context 入参（如 cwd / 时间窗），未来可接
「多接收方 receivers」与「条件发送规则」——本期只留 seam，不落地逻辑。
配置保持扁平。

仅依赖标准库，零网络。
"""

import os
import json
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "feishu_config.json")
LOG_PATH = os.path.join(HERE, "feishu_notify.log")


def _log(msg):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write("[%s] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
    except Exception:
        pass


def load_config():
    """读 feishu_config.json，并以环境变量覆盖；返回配置 dict。

    读文件失败时不抛出（配置模块不应中断管道），交由 has_credentials 判定缺失。
    """
    cfg = {
        "app_id": "",
        "app_secret": "",
        "receive_id": "",
        "receive_id_type": "open_id",  # open_id / user_id / union_id / email / chat_id
        # 想临时关掉某些事件的通知，把它从下面列表删掉即可
        "enabled_events": ["Notification", "Stop", "SubagentStop"],
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception as e:
            _log("读取 feishu_config.json 失败: %r" % e)
    # 环境变量覆盖
    for k, env in [
        ("app_id", "FEISHU_APP_ID"),
        ("app_secret", "FEISHU_APP_SECRET"),
        ("receive_id", "FEISHU_RECEIVE_ID"),
        ("receive_id_type", "FEISHU_RECEIVE_ID_TYPE"),
    ]:
        v = os.environ.get(env)
        if v:
            cfg[k] = v
    return cfg


def should_notify(event, cfg, context=None):
    """该事件是否启用通知。

    context: 预留扩展点（未来 receivers / 条件发送规则接入），本期不落地逻辑，
    只接受入参、不影响判定结果。
    """
    return event in cfg.get("enabled_events", [])


def has_credentials(cfg):
    """凭据是否齐全（app_id / app_secret / receive_id 均非空）。"""
    return bool(cfg.get("app_id")) and bool(cfg.get("app_secret")) and bool(cfg.get("receive_id"))
