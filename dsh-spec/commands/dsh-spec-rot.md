---
description: 漂移与一致性巡检——发现文档漂移、无 note 的 commit、测试退化、ADR 过期。参数：[--check all|docs|notes|tests|adr]
allowed-tools: Read, Grep, Bash
---

调用 `dsh-spec-rot` skill，做定期漂移巡检。

把用户参数原样传给 skill：`$ARGUMENTS`

skill 会：按 `--check`（默认 all）逐项检查 `docs`（ARCHITECTURE 与实际结构漂移）/ `notes`（无 note 的 commit）/ `tests`（测试套件退化）/ `adr`（ADR 过期或未标记推翻）→ 输出按严重度排序的发现清单。只报告、不自动修复。
