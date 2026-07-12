---
title: 为什么通知 hook 用纯标准库而非官方 SDK/CLI
status: accepted
date: 2026-07-10
deciders: z
---

## 背景（Context）

wb-toolkit 的飞书通知 hook 在每个 Claude hook 事件（Notification / Stop /
SubagentStop）上以**独立子进程**运行，核心约束（写进 README）是：① 纯 Python
标准库、无需 pip；② 永不阻断 Claude（异常全吞、退出码 0）。

飞书官方提供两套更"重"的能力：
- 服务端 SDK `lark-oapi`（Python≥3.8，pip 安装）：托管 tenant_access_token
  生命周期、类型化、语义化接口。
- 飞书 CLI `lark-cli`（Node + `npx install` + OAuth `auth login`）：面向 AI
  Agent 的"操作飞书的手"，覆盖多业务域。

## 决策（Decision）

通知 hook **用纯标准库（urllib）实现**，并把飞书 API 面收口进独立深模块
`hooks/feishu_client.py`（`FeishuClient`）。**不引入官方 SDK，也不引入飞书 CLI。**

## 后果（Consequences）

- 优点：零依赖（契合约束①）；子进程启动极快；错误策略（永不阻断）留在编排层
  `feishu_notify.py`，client 只管传输并统一抛 `FeishuError`。
- 代价：token 生命周期需自管（每次现取、无状态）；需自行跟随飞书 API 变更。
  本场景下代价很小——每次 hook 是独立进程、单通知顶多取一次 token，进程内缓存
  无意义。
- 若未来插件扩展到**多飞书端点**或变为**常驻服务**，应重新评估采用 `lark-oapi`
  （其 token 托管在长驻场景才划算）。

## 范围澄清

本 ADR 仅约束**通知 hook**。更大的「飞书 Agent 项目」（8 个 bot、探索 Lark CLI
集成）属不同范围，CLI 在那里可能合适——勿据此 ADR 反对它。

## 关联

- improve-codebase-architecture 评审候选 A：抽出 `FeishuClient` 深模块。
