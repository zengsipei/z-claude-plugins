# dsh-spec · 插件说明与纪律规则

本插件移植 deepseek-harness（dsh）的活文档与变更台账纪律。安装后，四个命令
（`/dsh-spec-init` `/dsh-spec-note` `/dsh-spec-review` `/dsh-spec-rot`）即可用；
逻辑在同名 skill，命令只做委派。

## 何时用什么

- **新项目落地纪律** → `/dsh-spec-init`：生成 SPEC.md / ARCHITECTURE.md / docs/adr/ / .agents/notes/ / .agents/LEDGER.md，并向项目 CLAUDE.md 追加规则块。
- **每次非平凡改动后** → `/dsh-spec-note`：在 `.agents/notes/<lifecycle>/<class>/<date>-<slug>.md` 留一笔，必含 `## Problem` / `## Decision|Proposal` / **必填** `## Alternatives considered` / `## Consequences`，并同步 LEDGER.md。
- **合并前** → `/dsh-spec-review`：委派 `code-review` 做标准评审，再审计每个改动是否有对应 note/ADR；`--gate strict`（默认）缺 note 即阻断。
- **定期巡检** → `/dsh-spec-rot`：发现文档漂移、无 note 的 commit、测试退化、ADR 过期；只报告不自动修。

## 分类法（六类，照抄 dsh）

`feature` / `bug-fix` / `simplification` / `architecture` / `process` / `testing`。
轻量架构权衡记 `architecture` note；正式、难逆转、需存档的架构决策走 `docs/adr/<nnnn>-<slug>.md`（顺序编号 0001+），note 内链接指向对应 ADR。

## 命名约束

- note slug：kebab-case、纯 ASCII 小写、≤40 字符、禁中文/大写，例 `add-retry-backoff`。
- note 路径：` .agents/notes/<lifecycle>/<class>/<date>-<slug>.md`（lifecycle 在外：proposed/implemented/rejected）。

## 闸门状态

评审/预推闸门（`hooks/dsh-spec-gate.py`）为 no-op 占位，行为由 D3 (#18) 决定；当前不阻断任何流程。

## 设计来源

- 命令/技能集合：D1 (#16)
- 变更台账模板与分类：D2 (#17)
- 活文档脚手架内容：D4 (#19)
- 插件机制验证：R3 (#15)
- 地图：`zengsipei/z-claude-plugins#12`
