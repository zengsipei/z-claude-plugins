# team-kit-bridge · 插件说明

本插件是 pstack 无损移植的配套桥接件：从上游 `cursor/plugins` 的
`cursor-team-kit` 插件摘取 pstack playbook 点名的三个技能（`deslop` ·
`control-cli` · `control-ui`），让 Claude Code 里这些引用按原名解析。安装后
`/deslop` 可直接说，另两个技能按其描述触发。

通用行为守则（Think Before Coding / Simplicity First / Surgical Changes /
Goal-Driven Execution）见仓库根 `AGENTS.md`，不在插件内复述。

## 快照纪律（动手前必读）

本插件是上游 `cursor/plugins@ccb5507`（2026-10-08）的**微快照移植**：只收
cursor-team-kit 的三个技能文件，纪律与 pstack 相同（见仓库根
[`docs/adr/0001-快照移植纪律.md`](../docs/adr/0001-快照移植纪律.md)）。

分类按 `snapshot.json` 的 `snapshot_paths` 声明一刀切，不靠清单维护：

- **`snapshot_paths` 之外的一切都是可动层**，自由改。目前这一层有 `tests/` ·
  `README.md` · `CLAUDE.md`（本文件） · `.gitattributes` ·
  `.claude-plugin/plugin.json` · `snapshot.json`；以后新增的文件自动属于这一层。
- **`snapshot_paths` 声明的 `skills/`** 之内全部是内核：与上游字节级一致，
  动一个字节就要整体重快照。**本插件没有已适配面**（adapted 恒为空）。

**上游身份、冻结范围与已适配面清单的唯一声明处是插件根的
[`snapshot.json`](snapshot.json)。** 本文件与 README 里的溯源文字都只是副本，由
仓库层事实守卫（`tools/consistency_facts.json`，前缀 `team-kit-bridge.`）
钉住——改副本不改事实，改事实请改 `snapshot.json`，再跑
`python tests/update_baseline.py` 重生成基准。

内核冻结由 `tests/test_team_kit_bridge_snapshot_contract.py::KernelFrozenTest` 执法——比对
`tests/kernel-baseline.json` 里每个文件的 sha256。它变红只有两种可能：有人改了
快照（还原它），或刚做完重快照（跑 `python tests/update_baseline.py`）。

`skills/**` 在 `.gitattributes` 里标为 `-text`，git 不做换行符转换，快照与
上游字节级 1:1。

## 为什么只有三个技能

pstack 的 playbook 只点名这三个 cursor-team-kit 技能；其余 15 个技能与
2 个 agent 是 Cursor 生态的通用工具，不在 pstack 的引用面里。只桥接被引用的，
触发面最小、维护面最小。上游挪动技能路径时，重快照需要人看一眼（上游 README
的技能表不再覆盖这三个名字就是信号）。升级为全量快照时这三个文件原样吸收。

## 本地降级（Windows，内核字节不动）

`control-cli` 的 Minimal tmux Harness 假设有 POSIX 工具链，Windows 本机没有
tmux。本机装了 Herdr（终端多路复用器，`herdr` 0.9.0）：Claude Code 会话跑在
Herdr 管的 pane 里（`HERDR_ENV=1`）时，逐条翻译配方——`tmux new-session -d`
→ `herdr pane split --current --no-focus`，`send-keys` → `herdr pane run`，
轮询 `capture-pane` → `herdr pane wait-output --match/--regex` +
`herdr pane read --source recent-unwrapped`，`kill-session` → 关掉自己创建的
pane。不在 Herdr 里时退回技能自带的 PTY probe。pstack `create-verification-skill`
里的 tmux/PTY 配方同理。agent 就地翻译，不在快照里改。

## 本地决策

本插件的本地决策记录放仓库根 `docs/adr/`（决策跟仓，不跟插件）。
