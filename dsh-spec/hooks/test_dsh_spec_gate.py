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


if __name__ == "__main__":
    unittest.main()
