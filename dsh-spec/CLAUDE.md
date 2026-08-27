# dsh-spec · 插件说明

本插件移植 deepseek-harness（dsh）的活文档与变更台账纪律。安装后，四个命令
（`/dsh-spec-init` `/dsh-spec-note` `/dsh-spec-review` `/dsh-spec-rot`）即可用；
逻辑在同名 skill，命令只做委派。

**全部共享规则（分类 / lifecycle / slug / note 路径与模板 / 阈值 / types 探测链 /
warn-only 宪法 / 归档协议 / rot 六查与 review 四轴枚举）的单一事实源是
[`RULES.md`](RULES.md) §1–§11。**
本文件与其余任何文件只引用、不复述；`/dsh-spec-init` 会把母本复制到消费项目
`.agents/RULES.md`。

## 何时用什么

- **新项目落地纪律** → `/dsh-spec-init`
- **每次非平凡改动后** → `/dsh-spec-note`
- **合并前** → `/dsh-spec-review`（权威闸口，`--gate strict` 可阻断）
- **定期巡检** → `/dsh-spec-rot`（恒 warn-only，§8）

## 设计来源

- 命令/技能集合：D1 (#16)
- 变更台账模板与分类：D2 (#17)
- 分层双闸：D3 (#18)
- 活文档脚手架内容：D4 (#19)
- v2 参数面：#34 / #35 / #36
- RULES.md 单一事实源 + 命令层纯接口化：#38
- 插件机制验证：R3 (#15)
- 地图：`zengsipei/z-claude-plugins#12`
