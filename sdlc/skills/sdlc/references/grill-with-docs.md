# Grill-with-docs 兼容协议

当已安装的 `$grill-with-docs` 不可用时，使用本协议保持相同的核心评审语义。该协议参考 `mattpocock/skills` 的 grill 工作流：一次只问一个问题、事实由 AI 调查、决定由用户作出，并在过程中持续形成 ADR 与术语记录。

来源：

- https://www.skills.sh/mattpocock/skills/grill-with-docs
- https://github.com/mattpocock/skills/blob/main/skills/engineering/grill-with-docs/SKILL.md
- https://github.com/mattpocock/skills/blob/main/skills/productivity/grilling/SKILL.md

## 执行步骤

1. 读取待评审主文档、适用代码、PRD、既有 ADR 和 glossary。
2. 扫描并建立问题队列，优先级依次为：需求口径、不可逆风险、跨系统契约、数据一致性、失败恢复、验证能力、成本优化。
3. 对队首问题先自行查证事实；如果事实足以唯一确定答案，直接更新文档并记录证据，不向用户提问。
4. 对需要决策的问题，一次只输出：
   - 问题及其影响；
   - 可行选项；
   - AI 推荐及理由；
   - 请求用户作出一个明确选择。
5. 等待用户回答。收到回答后立即：
   - 更新评审记录状态；
   - 修改主文档受影响章节；
   - 必要时创建或更新 ADR、glossary；
   - 重新扫描由该决定引出的后续问题。
6. 重复步骤 3-5，直到队列为空。
7. 最后执行反向一致性检查：目标能否由方案实现、方案能否由任务落实、风险是否有缓解措施、每项验收是否有验证入口。
8. 向用户请求确认已经达到共同理解；确认后将主文档定稿。

## 禁止行为

- 一次抛出多个需要用户同时回答的问题。
- 询问可以从仓库或工具查到的事实。
- 只在聊天里记录决定而不更新文档。
- 用 AI 自动决定产品语义、高风险或不可逆事项。
- 未确认项未归零就宣布评审完成。
