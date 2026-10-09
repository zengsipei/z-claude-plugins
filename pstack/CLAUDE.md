# pstack · 插件说明

本插件移植 Cursor 官方 pstack 插件：poteto 的严谨 agent 工作流——`poteto-mode`
路由 + 23 个 playbook + 23 条原则叶技能 + how/why/architect/arena/interrogate/
swarm 等工作流技能。安装后，说「/poteto-mode」或「用 poteto 风格做这件事」即可触发；
入口技能是 `skills/poteto-mode/SKILL.md`，两个 agent 说明在 `agents/`。

通用行为守则（Think Before Coding / Simplicity First / Surgical Changes /
Goal-Driven Execution）见仓库根 `AGENTS.md`，不在插件内复述。

## 快照纪律（动手前必读）

本插件是上游 `cursor/plugins@ccb5507`（2026-10-08）的**快照移植**，不是普通源码
目录。动任何文件前先判定它属于哪一类；判据与纪律见仓库根
[`docs/adr/0001-快照移植纪律.md`](../docs/adr/0001-快照移植纪律.md)。

分类按 `snapshot.json` 的 `snapshot_paths` 声明一刀切，不靠清单维护：

- **`snapshot_paths` 之外的一切都是可动层**，自由改。目前这一层有 `tests/` ·
  `README.md` · `CLAUDE.md`（本文件） · `.gitattributes` ·
  `.claude-plugin/plugin.json` · `snapshot.json`；以后新增的文件自动属于这一层。
- **`snapshot_paths` 声明的九个路径**（`skills/` `agents/` `automations/` `docs/`
  `assets/` `upstream/` `.cursor-plugin/` `LICENSE` `.gitignore`）之内分两类，
  类别记在机器基准里，不靠人记——跑 `python tests/update_baseline.py` 会打印
  当前清单：
  - **禁区**（`category: kernel`）：与上游字节级一致，动一个字节就要整体重快照。
  - **已适配面**（`category: adapted`）：可按本仓惯例改写，改了要能说明理由。

**上游身份、冻结范围与已适配面清单的唯一声明处是插件根的
[`snapshot.json`](snapshot.json)。** 本文件与 README 里的溯源文字都只是副本，由
仓库层事实守卫（`tools/consistency_facts.json`，前缀 `pstack.`）钉住——改副本
不改事实，改事实请改 `snapshot.json`，再跑上面的命令重生成基准。

内核冻结由 `tests/test_pstack_snapshot_contract.py::KernelFrozenTest` 执法——比对
`tests/kernel-baseline.json` 里每个文件的 sha256。它变红只有两种可能：有人改了
快照（还原它），或刚做完重快照（跑 `python tests/update_baseline.py`）。

`snapshot_paths` 内的路径在 `.gitattributes` 里标为 `-text`，git 不做换行符
转换，快照与上游字节级 1:1。

## 已适配面（3 个，理由）

| 文件 | 改动 | 理由 |
|---|---|---|
| `agents/comment-sicko.md` | frontmatter `name: Comment Sicko` → `comment-sicko` | agent 名字必须是可寻址标识符，空格名在 Task `subagent_type` 里不可用 |
| `skills/no-comments/SKILL.md` | 四处 `Comment Sicko` 引用 → `` `comment-sicko` `` | 跟随上一行的改名，入口面一致性 |
| `skills/poteto-mode/SKILL.md` | frontmatter `name: Poteto Mode` → `poteto-mode` | skill 名应与目录名一致（kebab-case） |

三处都是入口与接线面，不动任何 playbook / 原则正文。

## 已知遗留（在禁区里，等下次重快照）

上游内容以 Cursor 为宿主写成，以下引用在 Claude Code 里没有对应物，**保持原字节**、
靠 agent 就地降级，不在快照里改：

- **`skills/poteto-mode/scripts/`**：bun/TypeScript 辅助工具（`watch-pr`、`orch`、
  `worktree-audit.sh`、`check-plan.mjs`）。没有任何 SKILL.md 直接引用它们；
  `worktree-cleanup` playbook 引用了 `worktree-audit.sh`（路径仍在，脚本本体可用，
  只是 Windows 下需自行用 bash 跑）。
- **`cursor-team-kit` 的 `/deslop`、`control-cli`、`control-ui`**：poteto-mode 的
  若干 playbook 引用它们，那是另一个 Cursor 插件；本仓未装时引用落空，用本仓已有的
  review 手段替代。
- **Cursor cloud agents / worktree 语义**：`autopilot-*`、`orchestrate`、`shipping`
  等 playbook 提到 `environment: "cloud"` 与 Cursor worktree；Claude Code 的 Task
  工具有自己的 background/cloud 语义，按当下工具能力解释。
- **`setup-pstack` 写 `~/.cursor/rules/pstack-models.mdc`**：该技能描述的是 Cursor
  的规则文件路径；在 Claude Code 里对应的模型配置入口不同，技能未适配，仅随快照
  留存作参考。
- **`docs/guide/` 与 `automations/benny/`**：面向 Cursor 用户的上手指南与自动化
  配置，保留作参考。

## 本地决策

本插件的本地决策记录放仓库根 `docs/adr/`（决策跟仓，不跟插件）。
