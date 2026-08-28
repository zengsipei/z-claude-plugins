"""dsh-spec gate 的决策行为测试（纯函数，免临时 git 仓）。

`ADOPT_MARKERS` / `NOTE_PREFIXES` 两组常量与 `RULES.md` 附录声明的一致性
**不在这里守** —— 已迁至仓库层的事实守卫 `tools/consistency_facts.json`
（事实 `dsh-spec.gate-adopt-markers` / `dsh-spec.gate-note-prefixes`）。

运行方式：cd hooks && python -m unittest test_dsh_spec_gate -v
"""
import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent

_spec = importlib.util.spec_from_file_location("dsh_spec_gate", HERE / "dsh-spec-gate.py")
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

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
