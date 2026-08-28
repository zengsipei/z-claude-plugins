#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""共享日志：所有 hooks 模块统一写同一份 feishu_notify.log。

单一事实源：日志路径 + 写入格式只在此处定义一次，避免各模块各写一份、
格式日后分叉。仅依赖标准库，零网络。
"""

import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(HERE, "feishu_notify.log")


def log(msg):
    """追加一行到 feishu_notify.log；任何异常都静默吞掉（日志绝不能中断管道）。"""
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write("[%s] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
    except Exception:
        pass
