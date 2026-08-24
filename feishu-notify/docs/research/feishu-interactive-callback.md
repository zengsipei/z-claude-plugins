# 调研：飞书双向互动卡片可行性（候选6）

> Wayfinder 地图 [#5](https://github.com/zengsipei/z-claude-plugins/issues/5) · research ticket [#11](https://github.com/zengsipei/z-claude-plugins/issues/11)
> 类型：research（AFK 读文档）· 强度：Speculative · 日期：2026-07-12
> 目的：为 fog「候选6 升级判定」提供事实依据——**是否升级为设计 ticket / 是否需重开 [ADR-0001](../adr/0001-为什么通知-hook-用纯-stdlib.md)**。

## 一句话结论

**技术可行，但不建议进 v1。** 双向互动卡片（点按钮回传给本地处理）在飞书平台完全支持，但**任一实现路径都需要一个常驻进程**，且长连接路径还引入第三方 SDK `lark-oapi`——两点分别击穿 ADR-0001 的「无服务器」与「纯 stdlib」两条铁律。若确要做，须**另立 ADR-0002** 为「双向能力」单开一个 opt-in 的常驻 daemon，而非在通知 hook 子进程里塞回调。

---

## 1. 飞书互动卡片 + 按钮回调机制（事实）

飞书卡片支持**回传交互组件**（按钮等）。用户点击后触发回调 `card.action.trigger`（schema 2.0，推送方式 Webhook）。

- **回调类型**：`card.action.trigger`（新版）。应用类型：自建应用可用。权限：开启任一即可；`user_id` 敏感字段需额外「获取用户 user ID」权限。
- **搭建**：在卡片搭建工具给交互组件创建「请求回调」事件，可带字符串或对象类型的**回传参数**（`Button_xxx` name + 自定义 value）。
- **硬约束**：用户点击后，服务端须在 **3 秒内以 HTTP 200 响应**，通过 `toast` / 更新卡片 / 保持不变 三选一反馈；超时客户端报「请求错误」。
- **回调结构**：`{ schema, header{event_id, token, create_time}, event{...operator, action, host, context{open_message_id, open_chat_id}} }`。校验用应用 Verification Token。

来源：
- [卡片回传交互回调](https://open.feishu.cn/document/feishu-cards/card-callback-communication?lang=zh-CN)
- [处理卡片回调](https://open.feishu.cn/document/uAjLw4CM/ukzMukzMukzM/feishu-cards/handle-card-callbacks?lang=zh-CN)
- [添加自定义交互事件](https://open.feishu.cn/document/uAjLw4CM/ukzMukzMukzM/feishu-cards/feishu-card-cardkit/add-interactive-events?lang=zh-CN)
- [回调概述](https://open.feishu.cn/document/event-subscription-guide/callback-subscription/callback-overview?lang=zh-CN)

---

## 2. 回调接收方案对比（成本 / 复杂度）

飞书回调订阅只有两种方式，二选一：

| 维度 | 长连接 WebSocket | HTTP Webhook |
| --- | --- | --- |
| 公网 IP / 域名 / HTTPS | **不需要** ✅ | 必须（含 SSL 证书） |
| 内网穿透（本地开发） | 不需要 | 需 ngrok/花生壳等 |
| 依赖 | **`pip install lark-oapi`**（+ 传递依赖 websockets） | stdlib `http.server` 可写，但需公网入站 |
| 常驻进程 | **需要**（`nohup`/`screen`/系统服务，SDK 自带心跳 + 自动重连） | 需要（HTTP server 常驻） |
| 数据落地 | 本地处理，不出内网 ✅ | 经公网服务器 |
| 适用 | 个人本地 / 小团队 / 敏感数据 | 企业生产 / 高并发 |
| 端到端时延 | 实时（长连接推送） | 实时（HTTP 回调） |

**长连接示例（官方 Python SDK）**：
```python
import lark_oapi as lark
handler = lark.EventDispatcherHandler.builder("", "") \
    .register_p2_im_message_receive_v1(on_msg).build()
cli = lark.ws.Client(APP_ID, APP_SECRET, event_handler=handler)
cli.start()   # 连上 wss://open.feishu.cn/event，主线程阻塞直到进程退出
```

> 对**个人电脑**场景，长连接明显优于 Webhook：免公网 IP、免域名、免内网穿透、数据不出本地、30 分钟可跑通。代价是**必须常驻 + 引入第三方 SDK**。

来源：
- [使用长连接接收事件（官方）](https://open.feishu.cn/document/ukTMukTMukTM/uYDNxYjL2QTM24iN0EjN/event-subscription-configure-/request-url-configuration-case?lang=zh-CN)
- [飞书机器人长连接完整接入实战](https://www.cnblogs.com/wyx-114514/p/20546882)
- [本地搭建飞书机器人（免公网）](https://developer.cloud.tencent.cn/article/2670675)

---

## 3. 与 ADR-0001 的具体冲突点

[ADR-0001](../adr/0001-为什么通知-hook-用纯-stdlib.md) 三条铁律：**① 纯 stdlib ② 无服务器（无常驻进程）③ 子进程无状态**。当前通知 hook 是 Claude Code 触发的一次性子进程——发完卡片即退出。

| ADR-0001 铁律 | 双向回调是否冲突 | 说明 |
| --- | --- | --- |
| ① 纯 stdlib | **冲突（长连接）** | Python stdlib 无 WebSocket 客户端，飞书长连接为私有协议，只能经 `lark-oapi`。Webhook 路径可纯 stdlib（`http.server`），但被②卡死。 |
| ② 无服务器 / 无常驻 | **冲突（两条路都冲突）** | 回调是**异步入站**：用户何时点按钮不可知，须有进程随时在线并在 3 秒内响应。一次性子进程 hook 结构上无法承接。 |
| ③ 子进程无状态 | **冲突** | 「发卡的子进程」与「收回调的进程」是两个生命周期；要把点击结果关联回原请求（如批准某次工具调用），必须跨进程共享状态（消息 id ↔ 待决动作）。 |

**有无轻量替代（免常驻）？** —— 无。
- 飞书事件（含 `im.message.receive_v1` 用户回复消息）**均为推送式**，同样走长连接/webhook 订阅，不存在「拉取未读/未处理回调」的轮询 HTTP 端点可供一次性子进程周期性调用。
- 即便改用「读用户回复的文本消息」代替按钮，仍要常驻订阅——省不掉常驻这一条。

---

## 4. 若要做：最小架构

把「双向」与「通知」彻底解耦，通知 hook 一个字节都不动：

```
通知 hook 子进程（现状，ADR-0001 不变）
    └─ 发互动卡片（在卡片上挂回传按钮 + value=动作标识）→ 立即退出

飞书回调 daemon（新增，opt-in 常驻）
    ├─ lark-oapi 长连接（免公网，SDK 心跳+重连）
    ├─ 收到 card.action.trigger → 3 秒内 toast/更新卡片
    ├─ 落一份「待决动作」状态（如 .pending_actions.json，消息 id ↔ 动作）
    └─ 执行动作（如写批准标志文件，供 Claude 侧 PreToolUse 读取放行）
```

- **依赖**：`lark-oapi`（第三方，需 venv 隔离，违反纯 stdlib）。
- **进程模型**：一个 opt-in daemon（`nohup`/系统服务），与 hook 完全分离；不装 daemon 则退化为纯单向通知（现状），零影响。
- **状态**：跨进程共享一个磁盘状态文件（与候选2 `.throttle_state.json` 同思路，但语义更重——它是「待决动作」而非「best-effort 时间戳」，漏读会导致审批卡住，可靠性要求更高）。
- **安全面**：App Secret 常驻内存 + Verification Token 校验回调来源；daemon 端口/连接仅出站 wss，无入站暴露（长连接优势）。

这套架构**必须重开/修订 ADR-0001**：把「无服务器」约束的范围从「整个插件」收窄到「通知 hook 子进程」，并新立 **ADR-0002：双向能力为何需要 opt-in 常驻 daemon**，明确它与单向 hook 的边界与降级路径。

---

## 5. 升级判定（交给 fog graduate）

| 判断 | 结论 |
| --- | --- |
| 技术可行性 | ✅ 可行（长连接免公网，个人电脑友好） |
| 与 ADR-0001 | ❌ 冲突「纯 stdlib」+「无服务器」+「子进程无状态」全部三条 |
| 是否升级为设计 ticket（进 v1） | **否**。引入常驻 daemon + 第三方 SDK 是架构级负担，违背个人工具箱「轻量、零运维、装好即用」初衷；当前无明确的远程审批刚需。 |
| 若未来确有需求 | 另立 **ADR-0002** 承接常驻 daemon，按第 4 节最小架构做**独立 opt-in 组件**，通知 hook 保持纯单向不变。 |

**建议 fog「候选6 升级判定」graduate 为**：*不升级、暂不做*——保留本调研为链接资产；一旦出现「想在手机上点一下就批准 Claude 的工具调用」这类真实需求，再以 ADR-0002 + 新地图承接，而非污染现有单向通知链路。
