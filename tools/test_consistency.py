"""事实守卫：把每个事实的副本钉在它的声明处。

**interface 是 `consistency_facts.json` 里的一行** —— 一个事实 = 一个声明处 +
若干副本 + 各自的抽取方式 + 关系。本文件只是它的 implementation：遍历清单、
抽取、比对、一事实一用例报出全部差异。新增一个事实 = 往清单里加一行，不改本文件。

抽取器（六种）：
  md_backticks  {section: "§N"} 或 {line_startswith: "..."} —— 抓反引号内容
  regex_capture {pattern, group, split, expect} —— 正则捕获。split 按分隔符拆开
                捕获到的串；expect 数的是**匹配处数**（"1" | "1+"），不是拆分后的值数
  json_path     {path} —— 点分路径，取标量或数组；支持 `plugins[name=dsh-spec]`
                这样的数组选择器（按字段值挑数组元素，命中数必须恰好 1，否则红）
  json_keys     {path, where} —— 取某层对象的键集，可按 where 过滤
  py_attr       {name, mode: value|keys} —— 按文件路径加载模块取模块级常量
  file_text     {} —— 取整文件文本，配合 contains_all 用

关系（三种）：eq（默认，集合相等）· prefix_of · contains_all

铁律：守卫的任何部分失效都必须是红的。空抽取（声明行被删、正则失配、常量被
改名）即失败；清单自身写错（路径不存在、kind 拼错、缺字段）该条目报失败、其余
照常跑。

运行方式：python tools/test_consistency.py
（或经统一入口：python tools/run_tests.py）
"""
import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MANIFEST = HERE / "consistency_facts.json"

KINDS = ("md_backticks", "regex_capture", "json_path", "json_keys", "py_attr", "file_text")
RELATIONS = ("eq", "prefix_of", "contains_all")

_ENUM_LINE = re.compile(r"^(`[^`]+`)( / `[^`]+`)*$")
# 数组选择器：路径里 `plugins[name=dsh-spec]` 这一段——先取键、再按字段值挑元素
_SELECTOR = re.compile(r"^([A-Za-z0-9_-]+)\[([A-Za-z0-9_-]+)=(.+)\]$")


class FactError(Exception):
    """抽取失败或清单写错。这类失败必须红，绝不静默跳过。"""


# ---------- 抽取 ----------

def _abs(rel):
    if not isinstance(rel, str) or not rel:
        raise FactError(f"路径不是非空字符串：{rel!r}")
    path = ROOT / rel
    if not path.is_file():
        raise FactError(f"文件不存在：{rel}（相对仓库根）")
    return path


def _section_text(text, section):
    """取 `## <section>` 之后、下一个 `## ` 之前的文本。"""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("## ") and section in line:
            start = i + 1
            break
    if start is None:
        raise FactError(f"找不到小节标题 {section!r}")
    end = len(lines)
    for j in range(start, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return "\n".join(lines[start:end])


def _md_backticks(text, spec):
    if "section" in spec:
        for line in _section_text(text, spec["section"]).splitlines():
            if _ENUM_LINE.match(line.strip()):
                return re.findall(r"`([^`]+)`", line)
        raise FactError(f"小节 {spec['section']!r} 里找不到反引号枚举行")
    prefix = spec.get("line_startswith")
    if not prefix:
        raise FactError("md_backticks 需要 section 或 line_startswith")
    for line in text.splitlines():
        if line.startswith(prefix):
            return re.findall(r"`([^`]+)`", line[len(prefix):])
    raise FactError(f"找不到以 {prefix!r} 开头的声明行")


def _regex_capture(text, spec):
    pattern = spec.get("pattern")
    if not pattern:
        raise FactError("regex_capture 需要 pattern")
    try:
        rx = re.compile(pattern, re.MULTILINE)
    except re.error as e:
        raise FactError(f"正则无法编译：{pattern!r}（{e}）")
    group = spec.get("group", 1)
    sep = spec.get("split")
    # expect 数的是「匹配到几处」，不是 split 之后有几个值 —— 一处的
    # `[--class a|b|c]` 拆开是 3 个值，但它只该有一处。
    matches = list(rx.finditer(text))
    if not matches:
        raise FactError(f"正则没有匹配到任何值：{pattern!r}")
    if spec.get("expect", "1+") == "1" and len(matches) != 1:
        raise FactError(f"期望恰好 1 处匹配，实际 {len(matches)} 处：{pattern!r}")
    values = []
    try:
        for m in matches:
            raw = m.group(group)
            values.extend(raw.split(sep) if sep else [raw])
    except IndexError as e:
        raise FactError(f"正则取组 {group!r} 失败：{e}")
    if not values:
        raise FactError(f"正则匹配到了但取不到值：{pattern!r}")
    return values


def _json_data(text, where):
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise FactError(f"{where} 不是合法 JSON：{e}")


def _select_one(items, sel, path, part, where):
    """路径里的 `key[field=value]`：按字段值从数组里挑元素。"""
    field, wanted = sel.group(2), sel.group(3)
    if not isinstance(items, list):
        raise FactError(
            f"{where} 的路径 {path!r} 在 {part!r} 处用了数组选择器，"
            f"但 {sel.group(1)!r} 是 {type(items).__name__}，不是数组"
        )
    hits = [
        e for e in items
        if isinstance(e, dict) and str(e.get(field)) == wanted
    ]
    # 命中 0 个说明名字写错了、2 个说明写得不唯一——两者都必须红，
    # 否则「悄悄没选到」会伪装成一致。
    if len(hits) != 1:
        raise FactError(
            f"{where} 的路径 {path!r} 中 {part!r} 期望恰好 1 个元素，"
            f"实际命中 {len(hits)}"
        )
    return hits[0]


def _dig(data, path, where):
    cur = data
    for part in path.split("."):
        sel = _SELECTOR.match(part)
        key = sel.group(1) if sel else part
        if not isinstance(cur, dict) or key not in cur:
            raise FactError(f"{where} 的路径 {path!r} 不存在（断在 {part!r}）")
        cur = cur[key]
        if sel:
            cur = _select_one(cur, sel, path, part, where)
    return cur


def _json_path(text, spec):
    path = spec.get("path")
    if not path:
        raise FactError("json_path 需要 path")
    value = _dig(_json_data(text, "文件"), path, "JSON")
    if isinstance(value, list):
        values = [str(v) for v in value]
    elif isinstance(value, dict):
        raise FactError(f"json_path 的 {path!r} 指向对象，该用 json_keys")
    else:
        values = [str(value)]
    if not values:
        raise FactError(f"json_path 的 {path!r} 抽到空值")
    return values


def _json_keys(text, spec):
    path = spec.get("path", "")
    node = _json_data(text, "文件") if not path else _dig(
        _json_data(text, "文件"), path, "JSON"
    )
    if not isinstance(node, dict):
        raise FactError(f"json_keys 的 {path!r} 不指向对象")
    where = spec.get("where")
    if where:
        keys = [
            k for k, v in node.items()
            if isinstance(v, dict) and all(v.get(wk) == wv for wk, wv in where.items())
        ]
    else:
        keys = list(node.keys())
    if not keys:
        raise FactError(f"json_keys 的 {path!r} 抽到空键集"
                        + (f"（where={where}）" if where else ""))
    return sorted(str(k) for k in keys)


_PY_MODULES = {}


def _load_py(rel):
    path = _abs(rel)
    key = str(path)
    if key in _PY_MODULES:
        return _PY_MODULES[key]
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(
        "_fact_" + re.sub(r"\W", "_", path.stem), path
    )
    if spec is None or spec.loader is None:
        raise FactError(f"无法加载 python 文件：{rel}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        raise FactError(f"执行 {rel} 时出错：{type(e).__name__}: {e}")
    _PY_MODULES[key] = module
    return module


def _py_attr(rel, spec):
    name = spec.get("name")
    if not name:
        raise FactError("py_attr 需要 name")
    module = _load_py(rel)
    if not hasattr(module, name):
        raise FactError(f"{rel} 里没有 {name}")
    value = getattr(module, name)
    if spec.get("mode", "value") == "keys":
        if not isinstance(value, dict):
            raise FactError(f"{name} 不是 dict，取不了键集")
        return sorted(str(k) for k in value)
    if isinstance(value, (tuple, list, set, frozenset)):
        values = [str(v) for v in value]
    elif isinstance(value, dict):
        values = sorted(str(k) for k in value)
    else:
        values = [str(value)]
    if not values:
        raise FactError(f"{name} 是空的")
    return values


def _file_text(text, spec):
    if not text.strip():
        raise FactError("文件是空的，取不到文本")
    return [text]


_EXTRACTORS = {
    "md_backticks": _md_backticks,
    "regex_capture": _regex_capture,
    "json_path": _json_path,
    "json_keys": _json_keys,
    "file_text": _file_text,
}


def _extract(rel, spec):
    if not isinstance(spec, dict):
        raise FactError(f"抽取声明不是对象：{spec!r}")
    kind = spec.get("kind")
    if kind not in KINDS:
        raise FactError(f"未知 extractor kind {kind!r}，可用：{'/'.join(KINDS)}")
    text = _abs(rel).read_text(encoding="utf-8")
    if kind == "py_attr":
        return _py_attr(rel, spec)
    return _EXTRACTORS[kind](text, spec)


# ---------- 比对 ----------

def _fmt(values, limit=8):
    shown = ", ".join(values[:limit])
    return shown + (f" …（共 {len(values)} 个）" if len(values) > limit else "")


def _compare(relation, declared, values):
    """返回差异描述，无差异则返回 None。"""
    if relation == "prefix_of":
        bad = [v for v in values if not any(d.startswith(v) for d in declared)]
        if bad:
            return f"以下副本值不是声明处任何值的前缀：{_fmt(bad)}"
        return None
    if relation == "contains_all":
        hay = "\n".join(values)
        missing = [d for d in declared if d not in hay]
        if missing:
            return f"副本文本里缺少声明处的值：{_fmt(missing)}"
        return None
    got, want = set(values), set(declared)
    if got == want:
        return None
    only_copy = sorted(got - want)
    only_decl = sorted(want - got)
    parts = []
    if only_decl:
        parts.append(f"副本缺失：{_fmt(only_decl)}")
    if only_copy:
        parts.append(f"副本多出：{_fmt(only_copy)}")
    return "；".join(parts)


def _check(fact):
    name = fact.get("name")
    if not name:
        raise FactError("清单条目缺 name")
    source = fact.get("source")
    copies = fact.get("copies")
    if not isinstance(source, dict) or not source.get("file"):
        raise FactError("缺 source.file")
    if not isinstance(copies, list) or not copies:
        raise FactError("缺 copies（至少一个副本）")

    declared = _extract(source["file"], source.get("extract") or {})
    if not declared:
        raise FactError(f"声明处 {source['file']} 抽到 0 个值")

    problems = []
    for copy in copies:
        rel = copy.get("file")
        relation = copy.get("relation", "eq")
        if relation not in RELATIONS:
            raise FactError(f"未知 relation {relation!r}，可用：{'/'.join(RELATIONS)}")
        values = _extract(rel, copy.get("extract") or {})
        if not values:
            raise FactError(f"副本 {rel} 抽到 0 个值——空抽取即失败，"
                            "守卫不能因为抽不到就假装一致")
        diff = _compare(relation, declared, values)
        if diff:
            problems.append(
                f"  副本 {rel}（{relation}）：{diff}\n"
                f"    声明处取值：{_fmt(declared)}\n"
                f"    副本取值：  {_fmt(values)}"
            )
    if problems:
        raise FactError(
            f"声明处 {source['file']} 与副本不一致\n" + "\n".join(problems)
        )


# ---------- 测试面：一事实一用例 ----------

def _load_facts():
    if not MANIFEST.is_file():
        raise FactError(f"清单文件不存在：{MANIFEST.name}")
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise FactError(f"清单不是合法 JSON：{e}")
    facts = data.get("facts")
    if not isinstance(facts, list) or not facts:
        raise FactError("清单里没有 facts 数组（或为空）")
    names = [f.get("name") for f in facts if isinstance(f, dict)]
    dupes = {n for n in names if names.count(n) > 1}
    if dupes:
        raise FactError(f"清单里有重复的事实名：{sorted(dupes)}")
    return facts


try:
    FACTS = _load_facts()
    MANIFEST_ERROR = None
except FactError as e:
    FACTS = []
    MANIFEST_ERROR = str(e)


class FactConsistencyTest(unittest.TestCase):
    """每条事实一个用例——一次跑出全部差异，不是遇到第一个就停。"""

    def test_manifest_is_readable(self):
        if MANIFEST_ERROR:
            self.fail(f"{MANIFEST.name} 无法作为清单加载：{MANIFEST_ERROR}")


def _make_test(fact):
    def test(self):
        name = fact.get("name", "<无名>")
        try:
            _check(fact)
        except FactError as e:
            self.fail(f"事实 {name}：{e}")
    return test


for _fact in FACTS:
    if not isinstance(_fact, dict):
        continue
    setattr(
        FactConsistencyTest,
        "test_fact_" + re.sub(r"\W", "_", str(_fact.get("name", ""))),
        _make_test(_fact),
    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
