# z-claude-plugins

个人 Claude Code 插件市场（monorepo）：根目录 `marketplace.json` 暴露若干独立插件，本仓同时是插件的开发地。术语表按 single-context 维护（见 `docs/agents/domain.md`）。

## Language

**采纳（adopted）**:
一个仓库被 dsh-spec 视为已落地台账纪律——存在 `.agents/` 台账结构。
_Avoid_: 启用、激活

**采纳标记（adoption markers）**:
判定采纳所查的文件集合，dsh 专属三项：`.agents/notes`、`.agents/RULES.md`、`.agents/LEDGER.md`；由 RULES.md 附录声明，gate 钩子据此判定。
_Avoid_: 检测文件、触发文件

**留账路径（account paths）**:
能证明「一批改动留下了账」的路径前缀：`.agents/notes/` 与 `docs/adr/`。
_Avoid_: note 前缀（note 只是留账的一种形态）

**有账（has account）**:
变更集中存在以「存在/新增」形态（新增/修改/复制/改名进入/未跟踪）出现的留账路径文件；仅删除不算。
_Avoid_: 有 note、写了 note

**脚手架清单（scaffold checklist）**:
`/dsh-spec-init` 在消费项目生成的结构清单；RULES.md 附录是其唯一声明，采纳标记与留账路径皆为其中声明的子集。
_Avoid_: 目录清单、初始化列表

**分层双闸（two-layer gate）**:
dsh-spec 的两层触发：提醒闸口（Stop hook，恒 warn-only、零退出）与权威闸口（`/dsh-spec-review`，人触发、可 strict 非零退出）。
_Avoid_: 双闸门、双重检查

**入口词（entry word）**:
sdlc 技能的显式调用词，`sdlc-` 前缀共九个：design-1、design-2、implement、test、debug、script、solo、close、history。是明确入口但非唯一触发方式；debug 与 script 仅显式调用可进入。
_Avoid_: 命令、slash 命令（sdlc 无命令面，入口词靠 description 触发）

**AI 登记（AI registration）**:
跨会话、跨工具、跨仓库续接的会话台账，由 `ai_register_core.py` 维护；远程 PG/MySQL 配置存在时优先，否则降级项目 SQLite。只记会话身份与进度，不代替任务状态机。
_Avoid_: 注册、登记数据库

**可信 sessionId 来源（trusted sessionId source）**:
session 身份的两个同级可信入口：SessionStart 钩子注入、钩子写出的约定上下文文件；任取其一即可登记，不得凭 transcript 时间戳或「最新会话」猜测。
_Avoid_: 会话 ID 推断

**台账（ledger）**:
dsh-spec 在采纳仓库落地的留账体系，由采纳标记三件套承载；sdlc 的需求目录产物不属于台账，两插件互不记账。
_Avoid_: 账本、notes 体系

**需求目录（requirement directory）**:
sdlc 在消费项目的每需求文档工作区 `docs/[需求目录]/`，承载设计/施工/测试文档、status.md、summary.md、glossary.md、adr/ 与 onlyAI/；不是 dsh-spec 的留账路径。
_Avoid_: 需求文件夹、任务目录

**快照（snapshot）**:
上游仓库某一提交的只读映像，移植与保真的基准。
约束见 [`docs/adr/0001`](docs/adr/0001-快照移植纪律.md) D1（以提交指认，不以版本号）。
_Avoid_: 版本、release

**重快照（re-snapshot）**:
在新提交上整体重跑一次移植，是上游更新入库的方式。
约束见 [`docs/adr/0001`](docs/adr/0001-快照移植纪律.md) D2（整体重跑，不做增量）。
_Avoid_: 增量同步、cherry-pick、定期同步

**表面适配（surface adaptation）**:
移植时被允许改写的那一层：入口与接线面。
约束见 [`docs/adr/0001`](docs/adr/0001-快照移植纪律.md) D3（内核 / 适配面 / 纯新增三分类与清单）。
_Avoid_: 本地化、重构、改造

**事实（fact）**:
一个在多处被表述的值或值集合（提交号、枚举、常量、路径前缀）。判定标志：改一处就必须改另一处，否则静默不一致。
_Avoid_: 变量、配置项（太窄，只覆盖代码里的形态）

**声明处（declaration site）**:
事实的唯一权威声明位置，由**人做决定的那一侧**承载——对外契约或规则文档，不是实现。
_Avoid_: 源头（不区分是哪一侧）、single source of truth（那是原则，不是位置）

**副本（copy）**:
被声明处驱动、必须跟随它的表述——实现里的常量、文档里的文字、机器产物的字段。登记处与守卫边界见 [`docs/adr/0003`](docs/adr/0003-事实守卫的边界与插件隔离约束.md)。
_Avoid_: 引用、镜像
