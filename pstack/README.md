# pstack

> 一句话：把 Cursor 官方 pstack 插件搬进 Claude Code——poteto 的严谨 agent 工作流，少写、写对。

- **upstream**: cursor/plugins@ccb5507cec1546dc88135c1139c811e6c59115ba (2026-10-08)

本插件是上游 [`cursor/plugins`](https://github.com/cursor/plugins) 仓库 `pstack/`
目录的快照移植（纪律见仓库根 `docs/adr/0001`）。装上后得到的是上游那一整套
agent 工作流：`poteto-mode` 入口路由、23 个 playbook、23 条原则叶技能，以及
how / why / architect / arena / interrogate / swarm / unslop 等支撑技能。

## 装它

```
/plugin marketplace add https://github.com/zengsipei/z-claude-plugins
/plugin install pstack@z-claude-plugins
```

## 用它

- 直接说 `/poteto-mode`，或「用 poteto 风格做这件事」——入口技能
  `poteto-mode` 会按任务类型路由到对应 playbook（修 bug、做功能、调查、
  多阶段计划、自主跑到底……）。
- 单独用支撑技能也行：`/how` 讲清一个子系统、`/why` 查设计动机、
  `/architect` 先出结构再写码、`/no-comments` 清注释。

## 包含什么

| 目录 | 内容 |
|---|---|
| `skills/` | 44 个技能：1 个模式入口（poteto-mode）+ 23 个原则叶 + 工作流与工具技能 |
| `agents/` | 2 个 agent 说明：poteto-agent（poteto 风格路由目标）、comment-sicko（注释洁癖审查员） |
| `docs/` `automations/` `assets/` | 上游指南、自动化配置、logo，随快照留存作参考 |
| `upstream/` | 上游 README 原文（为给本文件腾位置而移入，字节未动） |

## 与上游的差异

只有 3 个文件动过字节（`snapshot.json` 的 `adapted` 清单是唯一声明处）：
`comment-sicko` 与 `poteto-mode` 两个 frontmatter 名字从带空格改成可寻址的
kebab-case，`no-comments` 里的引用跟随改名。其余 161 个文件与上游字节级一致，
由 `tests/` 里的冻结守卫执法。

## 维护

重快照（换上游提交）只改 `snapshot.json` 一处，再跑
`python tests/update_baseline.py` 重生成基准。详见 `CLAUDE.md` 的快照纪律节。
