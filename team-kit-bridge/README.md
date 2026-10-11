# team-kit-bridge

> 一句话：pstack playbook 点名的三个 cursor-team-kit 技能，字节冻结搬进 Claude Code。

- **upstream**: cursor/plugins@ccb5507cec1546dc88135c1139c811e6c59115ba (2026-10-08)

本插件是 pstack 无损移植的配套桥接件。上游 pstack 的 playbook 引用
`cursor-team-kit` 插件的三个技能（那是另一个 Cursor 插件，Claude Code 里装不上），
本插件从同一上游仓库的同一提交摘取这三个技能，让引用按原名解析：

| 技能 | 上游职位 |
|---|---|
| `deslop` | 提交前清代码里的 AI 注水（与 pstack 的 `/unslop` 清文字、`/no-comments` 审注释三分工） |
| `control-cli` | CLI / TUI 表面的可重复驱动架配方（tmux / PTY / 性能取证） |
| `control-ui` | 浏览器 / Electron / Web 表面的本地验证配方（Playwright / CDP） |

上游 cursor-team-kit 的其余 15 个技能与 2 个 agent 不在本插件范围；哪天要整套
kit，升级为全量快照时这三个文件原样吸收。

## 装它

```
/plugin marketplace add https://github.com/zengsipei/z-claude-plugins
/plugin install team-kit-bridge@z-claude-plugins
```

建议与 pstack 一起装；单独装也可用。

## 维护

重快照（换上游提交）只改 `snapshot.json` 一处，再跑
`python tests/update_baseline.py` 重生成基准。详见 `CLAUDE.md` 的快照纪律节。
