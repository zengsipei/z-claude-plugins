---
description: 合并前闸门——多轴评审（code 标准评审 / notes 台账审计 / test seam 测试审计 / types 类型退化审计）。参数：[--since <ref>] [--gate strict|warn] [--axis <all|code|notes|test|types>]
allowed-tools: Read, Grep, Bash, Skill
---

调用 `dsh-spec-review` skill 处理。把用户参数原样传给 skill：`$ARGUMENTS`

参数、四轴准则与 gate 语义的权威说明见 `skills/dsh-spec-review/SKILL.md`。
