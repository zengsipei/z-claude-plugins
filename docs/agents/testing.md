# Testing

How to run this repo's tests, and how to add a fact to the consistency guard.

## Run everything

```
python tools/run_tests.py                        # 全部四个目录
python tools/run_tests.py sdlc/tests tools       # 指定目录（相对仓库根）
```

失败退出码非零。四个默认目录：`sdlc/tests` · `dsh-spec/hooks` · `feishu-notify/hooks` · `tools`。

CI（`.github/workflows/ci.yml`，`ubuntu-latest`）跑的就是上面第一条命令，退出码非零即红——workflow 里不再逐个目录抄一遍跑法。

**`python -m unittest discover` 从仓库根跑会得到 0 个测试**——三个插件的测试目录都不是包，Python 3.13 的 discover 不再支持命名空间包，先插 `sys.path` 也无效。所以 `run_tests.py` 逐目录 discover，每个目录的 `top_level_dir` 指自己。不要试图改回单条根级 discover 命令。

各测试文件头部的旧跑法（`cd hooks && python -m unittest …`）仍然可用，但**不是权威**——权威只有上面这条。

## Add a fact

事实 = 一个在多处被表述的值。**声明处**由人做决定的那一侧承载（对外契约 / 规则文档），**副本**是被它驱动的实现与文档。（术语见 `CONTEXT.md`，边界见 `docs/adr/0003`。）

往 `tools/consistency_facts.json` 的 `facts` 数组里加一条，不改 `tools/test_consistency.py`：

```json
{
  "name": "<plugin>.<slug>",
  "note": "为什么这条值得守；写清声明处选的是哪一侧",
  "source": { "file": "<相对仓库根>", "extract": { "kind": "…" } },
  "copies": [
    { "file": "…", "extract": { "kind": "…" } },
    { "file": "…", "extract": { "kind": "file_text" }, "relation": "contains_all" }
  ]
}
```

### Extractors

| kind | 参数 | 取什么 |
|---|---|---|
| `md_backticks` | `section: "§N"` 或 `line_startswith: "…"` | 该行里的反引号内容 |
| `regex_capture` | `pattern` · `group` · `split` · `expect` | 正则捕获组；`split` 再按分隔符拆；`expect` 数的是**匹配处数**（`"1"` / `"1+"`） |
| `json_path` | `path`（点分，支持 `plugins[name=dsh-spec]` 数组选择器） | 标量或数组；选择器按字段值挑数组元素，命中数必须恰好 1，否则该条红 |
| `json_keys` | `path` · `where` | 某层对象的键集，`where` 按字段过滤 |
| `py_attr` | `name` · `mode: value\|keys` | 按文件路径加载模块取模块级常量 |
| `file_text` | — | 整个文件文本，配合 `contains_all` 用 |

### Relations

- `eq`（默认）——集合相等
- `prefix_of`——副本的每个值都是声明处某个值的前缀（例：CLAUDE.md 里写提交号缩写）
- `contains_all`——副本是自然语言文本时，声明处的每个值都要在里面出现（例：技能面的 description）

`custom: "<func>"` 是逃生口，只在声明式表达不了时用，**且必须在该条目旁写注释说明理由**。

### 铁律

守卫的任何部分失效都必须是红的：空抽取（声明行被删、正则失配、常量被改名）即失败；清单自身写错（路径不存在、`kind` 拼错、缺字段）该条目报失败、其余照常跑。

反面教材：`feishu-notify` 原来的 `test_all_8_events_registered` 把期望集硬编码在测试里，守着一个不存在的声明处，改实现是绿的、改测试里那个集合也是绿的。

### 自证

加完一条事实，必须证明它会红：

1. 改坏声明侧或副本侧 → `python tools/run_tests.py` → **该条** `FAIL: test_fact_<name>` 变红，且**不误伤**其它事实
2. `git checkout` 还原 → 转绿

不接受「加完就是绿的」作为验收——那说明不了守卫有没有在工作。

写脚本自证（而非肉眼看）时两个坑：**unittest 的 `-v` 结果写 stderr 不写 stdout**；本机 `core.autocrlf=true`，捕获到的行尾是 `\r\n`，正则别直接锚 `$`。
