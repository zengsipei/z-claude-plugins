# Close：开发流程关闭

`sdlc-close` 负责校验当前工作流的前置产物、收口文档、同步 AI 登记、沉淀知识并写入 `done / 已关闭 / 100%`。Close 不补做设计、实现或脚本执行，也不扩大用户授权。

## 按工作流校验前置产物

先读取 `onlyAI/task-state.json` 的 `workflow`，再校验对应分支。所有分支都要求机器状态与 `status.md` 一致、未确认项为 `0`、无阻塞，主文档已经定稿，并且文档扫描不存在待决策、待确认、待执行、待验证或其他未完成状态。

| workflow | 可关闭状态 | 必需人类主文档 | 不要求 |
|---|---|---|---|
| `standard` | Implement 已完成且 Test 未开始；或 Test 已通过/有条件通过 | `001-设计文档.md`、`002-施工文档.md`；已测试时还需 `003-测试文档.md` | — |
| `debug` | 根因已确认；修复授权下还需修复与验证完成 | `Debug排查记录.md` | 标准设计、施工、测试文档 |
| `script` | 达到用户约定目标、执行和验证完成 | `脚本任务.md` | 标准设计、施工、测试文档 |

标准流程中的临时 Debug 必须先返回保存的原阶段，不得直接 Close。生产脚本处于待批准、待执行或未验证状态时不能关闭。旧任务可以按 Design/Delivery 的兼容规则读取历史分离文档，但新任务只生成聚合文档。

## 测试门禁与二次确认

测试已执行时，结论必须为“通过”，或“有条件通过且遗留风险已明确接受”；失败、执行中或未知状态不能关闭。

当 `sdlc-test` 完全未执行时，包括独立 Debug/Script 仅做了专项验证的情况，允许在其他门禁全部通过后例外关闭：

1. 运行 `close-request`。脚本绑定当前工作树，写入“等待测试风险确认”并输出一次性 token；此时不得写最终关闭状态。
2. 明确告诉用户：任务未执行 `sdlc-test`，专项验证不等于完整质量验证；尚无法确认的回归、兼容、权限、数据安全和运行环境风险必须列明。
3. 等待用户在看到提醒后再次明确回复“确认跳过测试并关闭”。首次 Close 请求不算二次确认，AI 不得代替用户确认。
4. 用户确认后运行 `close-confirm --token [token]`，在 `status.md` 正文和 `summary.md` 记录事实、风险、确认时间与结论。不得生成虚假的 `003-测试文档.md` 或 `onlyAI/` 测试证据。
5. `close-request` 到 `close-confirm` 之间工作树发生变化时 token 失效，必须重新验证受影响内容并再次提醒。用户确认后不再复检工作树指纹，但跳过测试的事实、风险、确认和结论必须留痕；已有失败、未解决缺陷或其他门禁缺口不能改称“跳过测试”绕过。

提醒示例：

```text
⚠️ 本任务尚未执行 sdlc-test，关闭只表示流程已收口，不代表质量验证通过。
如果接受未验证风险，请明确回复“确认跳过测试并关闭”。
```

## 关闭步骤

1. 运行 `close-request` 执行机器状态、工作流和主文档门禁；未测试时完成上节二次确认。
2. 对照实际改动更新当前工作流主文档：
   - Standard：收口设计状态，以及施工文档中的任务、执行、文件/SQL 改动、偏差和遗留项；已测试时同步测试文档结论。
   - Debug：收口根因、决定、修复、文件改动、验证和遗留风险。
   - Script：收口计划、授权、脚本、执行、影响量、验证和遗留风险。
3. 生成或更新 `summary.md`，至少包含目标范围、最终方案、关键决定、交付物、已完成任务、测试事实、验证证据、遗留风险和后续建议；跳过测试时必须包含二次确认记录。
4. 处理知识沉淀：`summary.md` 是必需的本地事实源；外部知识库可用时在 Close 阶段默认同步，无需单独授权，并在 `status.md` 记录目标、标识、时间和结果。能力不可用时记录“仅本地沉淀”，不伪造成功，也不阻断关闭。
5. 有可信 sessionId 时，按 `registration.md` 先 upsert 身份，再同步最终进度：

```bash
python <skill>/scripts/ai_register_core.py upsert \
  --session <sessionId> --tool <工具> --model <模型> \
  --cwd <仓库目录> --branch <当前分支>

python <skill>/scripts/ai_register_core.py close \
  --session <sessionId> --task-dir "docs/[需求目录]/" \
  --completed-task "T-01：[任务]" --progress "100%" \
  --branch <当前分支> --cwd <仓库目录>
```

6. 将实际登记后端和同步结果写入 `status.md`。没有可信 sessionId 时记录跳过原因，不猜测身份，也不阻断本地关闭。批准进入 SDLC 只授权维护任务文档、AI 登记写入和 Close 阶段的知识沉淀同步，不授权业务数据库写入、迁移或生产执行。未测试关闭中的 `100%` 仅表示流程收口。
7. 用状态脚本记录三项收口结果；外部能力失败或不可用可以关闭，但状态与证据不能留空：

```bash
python <skill>/scripts/task_state_core.py close-artifact --task-dir "docs/[需求目录]/" \
  --name summary --status completed --evidence "summary.md 已完成"
python <skill>/scripts/task_state_core.py close-artifact --task-dir "docs/[需求目录]/" \
  --name registration --status skipped --evidence "[无可信 sessionId，已跳过]"
python <skill>/scripts/task_state_core.py close-artifact --task-dir "docs/[需求目录]/" \
  --name knowledge --status local_only --evidence "[结论已沉淀到 summary.md]"
```

登记可按实际结果把 `skipped` 改为 `synced` 或 `failed`；知识沉淀可把 `local_only` 改为 `synced` 或 `failed`。

8. 确认主文档、`summary.md`、三个收口结果及其证据一致后运行 `close-complete`，最后运行 `validate`。最终状态只能由状态脚本写入。

## 后端、幂等与边界

- 登记脚本优先读取 `docs/ai-register.json` 中的 PostgreSQL/MySQL 配置（含 JSON 内 `password`）；不可用时降级到项目 `docs/ai-register.db`。
- 重复 Close 必须幂等：已完成任务按内容去重，session 按主键更新，知识条目不重复创建，已记录的收口结果不重复追加。
- Close 不自动提交、推送、合并、部署、执行生产脚本或删除任务目录；这些动作需要各自授权。

## 退出条件

- 当前 `workflow` 的前置状态和唯一主文档通过门禁，无未确认项和阻塞。
- 测试已通过，或测试完全未执行且用户已经二次确认风险。
- 主文档、`onlyAI/` 证据、实际改动和 `summary.md` 一致；summary、AI 登记、知识沉淀三个 artifact 均有明确终态和证据。
- `close-complete` 与 `validate` 成功，机器状态和投影均为 `done / 已关闭 / 100%`。
