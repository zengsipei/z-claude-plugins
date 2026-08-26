---
description: 漂移与一致性巡检——六查：docs/notes/tests/adr/simplify/types。参数：[--check all|docs|notes|tests|adr|simplify|types] [--simplify-thresholds k=v,…] [--types-thresholds k=v,…]
allowed-tools: Read, Grep, Bash
---

调用 `dsh-spec-rot` skill，做定期漂移巡检。

把用户参数原样传给 skill：`$ARGUMENTS`

skill 会：按 `--check`（默认 all，六查全跑）逐项检查 `docs`（ARCHITECTURE 与实际结构漂移）/ `notes`（无 note 的 commit）/ `tests`（测试套件退化）/ `adr`（ADR 过期或未标记推翻）/ `simplify`（自包含层：单文件 LOC > 400 warn / > 800 高、导出 > 20；工具增强层：jscpd 重复 / knip 死代码 / sonarjs 圈复杂度，有工具才跑）/ `types`（自包含层：any / 非空断言 / @ts-ignore / as 气味计数，仅 TS/JS；工具增强层：复用消费项目既有类型工具链）→ 输出按严重度排序的发现清单 `{文件, 信号, 度量值, 建议}`。恒 warn-only、零退出、只报告不自动修复；跳过分支（「未配置 <tool>，跳过」「非 TS/JS，跳过」「无类型工具链，跳过」）为一等非致命结果。阈值可经 `--simplify-thresholds` / `--types-thresholds` 局部覆盖，默认值开箱即用。
