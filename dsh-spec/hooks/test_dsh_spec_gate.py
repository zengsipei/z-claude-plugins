"""一致性测试：dsh-spec gate 常量 ⇔ RULES.md 附录声明。

RULES.md「附：脚手架清单」末尾两行是 `dsh-spec-gate.py` 中 `ADOPT_MARKERS`
与 `NOTE_PREFIXES` 两组常量的唯一声明处；本测试解析该声明并断言常量与之一致
——附录改了清单而忘改 gate.py 常量时，本测试变红。

运行方式：cd hooks && python -m unittest test_dsh_spec_gate -v
"""
import importlib.util
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
RULES = (HERE / ".." / "RULES.md").resolve()

_spec = importlib.util.spec_from_file_location("dsh_spec_gate", HERE / "dsh-spec-gate.py")
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

# 附录声明行的固定前缀（与 RULES.md 附录两行声明一一对应）。
_ADOPT_LINE = "- gate 采纳标记（`ADOPT_MARKERS`）："
_NOTE_LINE = "- 留账路径（`NOTE_PREFIXES`）："


def _declared_values(line_prefix: str) -> tuple[str, ...]:
    """从 RULES.md 附录声明行提取反引号代码段（即声明的常量取值）。"""
    for line in RULES.read_text(encoding="utf-8").splitlines():
        if line.startswith(line_prefix):
            return tuple(re.findall(r"`([^`]+)`", line[len(line_prefix):]))
    raise AssertionError(f"RULES.md 附录缺少声明行：{line_prefix!r}")


class ConstantConsistencyTest(unittest.TestCase):
    def test_adopt_markers_match_rules_appendix(self):
        self.assertEqual(gate.ADOPT_MARKERS, _declared_values(_ADOPT_LINE))

    def test_note_prefixes_match_rules_appendix(self):
        self.assertEqual(gate.NOTE_PREFIXES, _declared_values(_NOTE_LINE))


# 行为测试统一用一个具体存在的标记，不引用 gate.ADOPT_MARKERS —— 免得行为测试
# 跟常量的具体内容耦合；常量本身由 ConstantConsistencyTest 单独守。
_ADOPTED = (".agents/notes",)


class ShouldWarnBehaviorTest(unittest.TestCase):
    """#43 严格「有账」语义 + 采纳判定：免临时 git 仓，直接喂 porcelain 行。"""

    def test_clean_tree_no_warn(self):
        self.assertFalse(gate.should_warn([], _ADOPTED))

    def test_not_adopted_never_warns(self):
        # 无任何采纳标记：只有 docs/adr/ 的陌生仓库静默（不对称见 RULES.md 附录）。
        lines = [" M src/a.py", "?? src/b.py"]
        self.assertFalse(gate.should_warn(lines, ()))

    def test_plain_change_without_note_warns(self):
        self.assertTrue(gate.should_warn([" M src/a.py"], _ADOPTED))

    def test_added_or_modified_note_counts(self):
        for xy in ("A ", " M", "M ", "C ", "MM"):
            with self.subTest(xy=xy):
                self.assertFalse(
                    gate.should_warn([f"{xy} .agents/notes/n.md"], _ADOPTED)
                )

    def test_untracked_note_counts(self):
        self.assertFalse(gate.should_warn(["?? docs/adr/0001-x.md"], _ADOPTED))

    def test_deleted_note_still_warns(self):
        self.assertTrue(
            gate.should_warn([" D .agents/notes/n.md", " M src/a.py"], _ADOPTED)
        )

    def test_rename_source_note_still_warns(self):
        # 账被挪走：源端是 note，目标端不是 → 仍提醒。
        self.assertTrue(
            gate.should_warn(["R  .agents/notes/n.md -> src/a.py"], _ADOPTED)
        )

    def test_rename_target_note_counts(self):
        self.assertFalse(
            gate.should_warn(
                ["R  src/a.py -> .agents/notes/n.md", " M src/b.py"], _ADOPTED
            )
        )

    def test_mixed_changes_with_one_live_note_no_warn(self):
        lines = [" M src/a.py", " D src/b.py", "?? .agents/notes/new.md"]
        self.assertFalse(gate.should_warn(lines, _ADOPTED))


if __name__ == "__main__":
    unittest.main()
