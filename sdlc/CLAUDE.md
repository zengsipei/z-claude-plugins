# sdlc · 插件说明

本插件移植上游 software-dev-process 的软件开发生命周期纪律：文档先行 → 对抗性
评审定稿 → 确定性阶段门禁 → 跨会话登记续接。安装后技能 `sdlc` 即可触发，
9 个入口词（`sdlc-design-1` `sdlc-design-2` `sdlc-implement` `sdlc-test`
`sdlc-debug` `sdlc-solo` `sdlc-script` `sdlc-close` `sdlc-history`）原样可用。

通用行为守则（Think Before Coding / Simplicity First / Surgical Changes /
Goal-Driven Execution）见仓库根 `AGENTS.md`，不在插件内复述。

## 快照纪律（动手前必读）

本插件是上游 `AtlantisYuki/prompt@7cdfc64` 的**快照移植**，不是普通源码目录。
动任何文件前先判定它属于哪一类，判据与完整清单见仓库根
[`docs/adr/0001-快照移植纪律.md`](../docs/adr/0001-快照移植纪律.md)。

- **可动层**（自由改）：`tests/` · `README.md` · `CLAUDE.md`（本文件） ·
  `.claude-plugin/plugin.json` · `hooks/hooks.json` · `hooks/cc_session_start.ps1`
- **禁区**（动一个字节就要整体重快照）：`skills/sdlc/` 下 19 个内核文件——
  `assets/` 全部 · `references/` 除 `registration.md` 外全部 · `scripts/` 全部
- **已适配面**（可改，但要能说明理由）：`skills/sdlc/SKILL.md` ·
  `skills/sdlc/references/registration.md`

内核冻结由 `tests/test_snapshot_contract.py::KernelFrozenTest` 执法——比对
`tests/kernel-baseline.json` 里 21 个文件的 sha256。它变红只有两种可能：有人改了
快照（还原它），或刚做完重快照（跑 `python tests/update_baseline.py`）。

`skills/sdlc/**` 在 `.gitattributes` 里标为 `-text`，git 不做换行符转换，快照
目录与上游字节级 1:1。

**已知遗留**（在禁区里，等下次重快照）：`scripts/install_codex_hook.ps1` 与
`install_grok_hook.ps1` 要安装的 `scripts/hooks/codex|grok_session_start.ps1`
已被丢弃，路径悬空；`SKILL.md` 入口清单已删这两个文件的条目，清单与目录不一致。

## 本地决策

本插件的本地决策记录放仓库根 `docs/adr/`（决策跟仓，不跟插件）。
