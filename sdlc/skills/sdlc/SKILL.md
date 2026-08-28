---
name: sdlc
description: 管理聚合文档、确定性状态和评审闭环的软件开发生命周期。用于用户明确调用 sdlc-design-1、sdlc-design-2、sdlc-implement、sdlc-test、sdlc-debug、sdlc-solo、sdlc-script、sdlc-close、sdlc-history，或明确要求按标准 SDLC 推进、关闭流程、同步 AI 登记及查询历史时。sdlc-debug 和 sdlc-script 只在用户显式调用时触发；普通局部 Bug 和低风险脚本直接处理。强制校验阶段状态、待确认项、改动边界和验证证据。
---

# Software Development Process

以“先形成可评审文档，再通过对抗性问答消除不确定性”为主线推进任务。不要把文件存在视为阶段完成；阶段完成必须同时满足文档状态、待确认项和验证门禁。

## 入口与参考文件

识别用户意图后，先完整读取 `references/task-state.md`，再完整读取对应阶段参考文件后行动：

| 入口 | 参考文件 | 目标 |
|---|---|---|
| 全部 SDLC 入口 | `references/task-state.md` | 使用机器状态与确定性转换维护阶段门禁 |
| `sdlc-design-1`、`sdlc-design-2` | `references/design.md` | 分层完善同一份设计文档并通过 grill 定稿 |
| `sdlc-implement`、`sdlc-test` | `references/delivery.md` | 在聚合施工/测试文档中实施并验证 |
| `sdlc-debug`、`sdlc-script` | `references/debug-script.md` | 使用单一专用文档独立排查或执行脚本 |
| `sdlc-solo` | `references/solo.md` | 仅串联标准流程至测试完成并自动 close |
| `sdlc-close` | `references/close.md` | 校验关闭门禁；未执行测试时经二次确认后收口 |
| `sdlc-history`、AI 登记 | `references/registration.md` | 登记会话、回填进度或查询历史 |

命令是明确入口，不是唯一触发方式。用户已经明确要求某阶段工作时，不要仅因其没有输入完整命令而拒绝推进。

例外：`sdlc-debug`、`sdlc-script` 必须由用户显式调用。未显式调用时，普通局部 Bug 和低风险脚本走 Direct；中高风险脚本只说明风险并请求用户明确进入 `sdlc-script`，不得自动切换。

## 强制前置检查

1. **权限与模式**：用户要求计划、审计或只读时，只分析并输出建议；不得创建 SDLC 文档、登记库或修改代码。实现、修复、执行脚本必须有对应授权。
2. **任务范围**：确认 `docs/[需求目录]/`、系统名称、目标和明确不做的内容。复杂任务缺少任务目录时再向用户确认。
3. **上下文**：设计前读取 `prd/`、适用的 `.agents/AGENTS.md`、现有实现和验证入口。可从仓库查到的事实必须自行查证。
4. **阶段门禁**：读取 `onlyAI/task-state.json`、`status.md` 和前置产物；旧任务缺少机器状态时先迁移并复核。不得仅凭文件存在推断阶段完成。
5. **参考加载**：完整读取当前入口对应的参考文件和需要使用的模板。
6. **会话登记**：按 `references/registration.md` 识别可信身份（SessionStart hook 注入的 sessionId，或协议约定的上下文文件）。仅在身份可信时登记；不得通过“最新 transcript”猜测并行会话身份。进入 SDLC 只授权维护流程文档、AI 登记和 Close 阶段的知识沉淀同步，不授权业务数据库写入、迁移或生产执行。

## 文档与阶段状态

`onlyAI/task-state.json` 是工作流、阶段、门禁和进度的机器事实源，`status.md` 是自动生成的可读投影与人类状态日志。`workflow` 明确区分 `standard / debug / script`，Close 据此校验对应主文档。按 `references/task-state.md` 调用状态脚本，不得手工改写 `status.md` 顶部关键字段；登记、知识库同步和其他人工说明仍写入正文。

阶段建议值：`design-1`、`design-2`、`implement`、`test`、`debug`、`script`、`close`、`done`。

各类主文档使用以下状态链（`status.md` 使用中文标签，机器状态使用英文枚举）：

```text
设计文档：草稿 → 评审中 → 已定稿          # draft → reviewing → final
施工文档：草稿 → 评审中 → 可施工 → 已完成  # draft → reviewing → ready → complete
测试文档：草稿 → 评审中 → 已完成          # draft → reviewing → complete
Debug/脚本主文档：草稿 → 评审中 → 已定稿   # draft → reviewing → final
```

阶段只有在以下条件全部满足时才可完成：

1. 当前主文档状态为“已定稿”或当前阶段约定的最终状态。
2. 未确认项为 `0`，状态脚本扫描主文档后不存在“待决策”“待确认”“待执行”或其他当前阶段未完成状态。
3. grill 中的每个决定已回写主文档；当前阶段要求评审时，机器状态中的 `review` 已完成并包含证据；重大长期决策已记录 ADR。
4. 当前阶段的验证或一致性检查有明确证据。

被明确移出范围的事项可以标记为“范围外”，但必须记录范围变更理由，不能用“范围外”掩盖未解决问题。

## Grill-with-docs 评审协议

需要 grill 时，优先显式调用已安装的 `$grill-with-docs`。该能力不可用时，完整读取并执行 `references/grill-with-docs.md` 中的兼容协议，不能跳过评审门禁。评审纪律（一次一个问题、事实由 AI 自行调查、决定即时回写、ADR/术语沉淀、未确认项归零）以 `references/grill-with-docs.md` 为准，本文件不重复展开。

概要设计和详细设计不再强制使用 `brainstorming` 或特定思维工具。先形成基于证据的完整初稿，再通过 grill 收敛。

## 共同实施约束

- 严格遵守已定稿施工文档的允许文件清单；需要越界时先更新并重新评审施工文档。
- `002-施工文档.md` 内的执行记录和文件改动章节是面向人的交付内容；`onlyAI/` 是面向 AI 的上下文、原始操作和验证证据，不能相互替代。
- 注释遵循仓库既有语言和风格，只为非显然意图、复杂业务与边界条件补充说明，不强制给所有改动添加中文注释。
- 数据库脚本统一放入 `docs/[需求目录]/sql/`。
- 文件改动记录优先使用文件路径、符号/函数和改动意图；行号仅作为最终快照的辅助信息。
- 标准流程施工发现重大设计缺陷时停止当前任务，回退到 `design-2`，更新设计文档并重新通过 grill 门禁。
- Debug 与 Script 是独立工作流：分别只维护 `Debug排查记录.md` 或 `脚本任务.md`，不补建标准设计、施工或测试文档；通用 `status.md`、`summary.md` 与 `onlyAI/` 仍按门禁维护。
- 每个阶段开始、结束、阻塞、回退、关键决策、施工任务完成和测试执行后，立即通过状态脚本同步机器状态与 `status.md`；有可信 sessionId 时同频更新 AI 登记。
- Test 通过后由状态脚本投影为“待关闭 / 95%”；Debug、Script 完成约定目标后投影为“已完成 / 90%”，随后进入 `sdlc-close`，不得用 `update` 伪造“待关闭”。Debug、Script 没有 Solo，Solo 只用于标准流程，并在测试完成后自动执行 `sdlc-close`。只有 Close 通过正常门禁，或在测试完全未执行时完成风险提醒与用户二次确认，且 summary、AI 登记和知识沉淀结果均已留痕，才能写入 `done / 已关闭 / 100%`。
- 若环境提供持久记忆能力，可在最终验证后回写；能力不可用时以 `summary.md` 记录可复用结论，不得因缺少特定记忆工具阻断交付。

## 目录约定

```text
docs/[需求目录]/
├── 001-设计文档.md               # 标准流程；Design-1/2 共用
├── 001-设计文档-评审记录.md      # 可选；评审记录过长时使用
├── 002-施工文档.md               # 标准流程；含计划、执行和文件改动
├── 003-测试文档.md               # 标准流程；含用例、证据和结论
├── Debug排查记录.md              # Debug 独立流程唯一人类主文档
├── 脚本任务.md                    # Script 独立流程唯一人类主文档
├── status.md
├── summary.md                    # close 阶段必须完成的本地知识沉淀
├── glossary.md                   # grill 产生领域术语时生成
├── adr/                          # 重大决策记录
├── sql/
└── onlyAI/
    ├── task-state.json             # 阶段、门禁和进度的机器事实源
    ├── structured-request.json
    ├── context-scan.json
    ├── operations-log.md
    ├── testing.md
    ├── verification.md
    └── review-report.md
```

## 可用资源

- `assets/设计文档模板.md`
- `assets/施工文档模板.md`
- `assets/待确认模板.md`
- `assets/测试文档模板.md`
- `assets/Debug排查记录模板.md`
- `assets/脚本任务模板.md`
- `assets/ai-register.config.example.json`
- `assets/task-state.schema.json`
- `scripts/task_state_core.py`
- `scripts/ai_register_core.py`
