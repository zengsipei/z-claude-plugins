---
description: 漂移与一致性巡检——六查：docs/notes/tests/adr/simplify/types。恒 warn-only。参数：[--check all|docs|notes|tests|adr|simplify|types] [--simplify-thresholds k=v,…] [--types-thresholds k=v,…]
allowed-tools: Read, Grep, Bash
---

调用 `dsh-spec-rot` skill 处理。把用户参数原样传给 skill：`$ARGUMENTS`

参数与六查定义的权威说明见 `skills/dsh-spec-rot/SKILL.md` 与 `.agents/RULES.md`（或插件母本 `RULES.md`）§6–§9。
