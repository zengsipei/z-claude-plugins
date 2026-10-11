"""快照契约测试：守住 team-kit-bridge 技能快照的跨文件一致性。

team-kit-bridge 是 pstack 无损移植的桥接件：只收 pstack playbook 点名的
三个 cursor-team-kit 技能（deslop / control-cli / control-ui），全部为内核，
adapted 恒为空。这里只有两条守卫：内核字节冻结与快照身份格式。

快照身份跨文件的一致性（提交号 ↔ README 溯源行 / CLAUDE.md 缩写 / 机器基准）
**不在这里守** —— 已迁至仓库层的事实守卫 `tools/consistency_facts.json`
（事实名前缀 `team-kit-bridge.`）。这里只剩声明处自身的格式校验：
`upstream_commit` 必须是完整 40 位十六进制。

运行方式：cd team-kit-bridge && python -m unittest discover -s tests -v
"""
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parent.resolve()
BASELINE = HERE / "kernel-baseline.json"
# 快照身份与冻结范围的唯一声明处。README / CLAUDE.md 里的溯源文字是它的副本，
# 由仓库层的事实守卫钉住，不在这里断言。
IDENTITY = PLUGIN / "snapshot.json"

_REGENERATE = "cd team-kit-bridge && python tests/update_baseline.py"


def _identity() -> dict:
    """读唯一声明处 `team-kit-bridge/snapshot.json`。"""
    return json.loads(IDENTITY.read_text(encoding="utf-8"))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


update_baseline = _load_module("update_baseline", HERE / "update_baseline.py")


class KernelFrozenTest(unittest.TestCase):
    """快照字节冻结守卫：snapshot_paths 下每个文件的 sha256 必须与基准一致。

    变红只有两种可能：有人改了快照（该还原），或刚做完重快照（该重生成基准）。
    """

    def _baseline_files(self) -> dict[str, dict[str, str]]:
        return json.loads(BASELINE.read_text(encoding="utf-8"))["files"]

    def test_snapshot_bytes_match_baseline(self):
        changed, missing = [], []
        for rel, expected in self._baseline_files().items():
            path = PLUGIN / rel
            if not path.is_file():
                missing.append(rel)
                continue
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != expected["sha256"]:
                changed.append(f"{rel}（{expected['category']}）")

        if not (changed or missing):
            return
        detail = "；".join(
            part
            for part in (
                f"缺失 {sorted(missing)}" if missing else "",
                f"字节已变 {sorted(changed)}" if changed else "",
            )
            if part
        )
        self.fail(
            f"快照与基准不一致 —— {detail}\n\n"
            f"若刚完成重快照，重生成基准：{_REGENERATE}\n"
            "否则把快照文件还原：内核字节级原样"
            "（纪律见 docs/adr/0001-快照移植纪律.md）。"
        )

    def test_baseline_covers_every_snapshot_file(self):
        """基准必须覆盖快照里的每个文件 —— 否则新加的文件能躲过上一条守卫。"""
        self.assertEqual(
            set(update_baseline.collect()),
            set(self._baseline_files()),
            f"快照目录与基准的文件集合不一致，重生成基准：{_REGENERATE}",
        )


class SnapshotIdentityFormatTest(unittest.TestCase):
    """声明处自身的格式校验：提交号必须是完整的 40 位十六进制。"""

    def test_commit_is_a_full_git_sha(self):
        commit = _identity()["upstream_commit"]
        self.assertEqual(
            40, len(commit),
            f"upstream_commit 必须是 40 位十六进制，实际 {len(commit)} 位：{commit!r}",
        )
        self.assertTrue(
            all(c in "0123456789abcdef" for c in commit),
            f"upstream_commit 含非小写十六进制字符：{commit!r}",
        )


if __name__ == "__main__":
    unittest.main()
