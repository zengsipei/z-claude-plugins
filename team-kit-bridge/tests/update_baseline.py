"""重生成内核字节基准 `kernel-baseline.json`。

team-kit-bridge 的快照纪律与 pstack 相同（见仓库根
`docs/adr/0001-快照移植纪律.md`）：`snapshot.json` 的 `snapshot_paths`
声明的每个路径都是上游快照，内核字节级原样。本脚本为每个快照文件记下
sha256 与类别，供 `test_snapshot_contract.py` 的 `KernelFrozenTest` 比对。

**本脚本不声明任何事实。** 上游身份（仓库与提交号）、冻结范围
（snapshot_paths）与已适配面清单（adapted）的唯一声明处是
`team-kit-bridge/snapshot.json`；本脚本只读它、把声明落到基准里。改快照
身份请改 `snapshot.json`，再跑本脚本。

与 pstack 版的差异：本插件是「三技能微桥接」，快照面只有 `skills/` 下的
三个 SKILL.md，全部为内核（adapted 恒为空）。上游 cursor-team-kit 的其余
15 个技能与 2 个 agent 不在本插件范围内——哪天要整套 kit，升级为全量
快照时这三个文件原样吸收。

何时运行：**重快照之后，且仅在这时**。运行方式：
cd team-kit-bridge && python tests/update_baseline.py
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parent.resolve()
BASELINE = HERE / "kernel-baseline.json"
IDENTITY = PLUGIN / "snapshot.json"

# 编译产物不进快照核对。
SKIP_SUFFIXES = (".pyc",)
SKIP_DIRS = {"__pycache__", "node_modules"}


def load_identity() -> tuple[str, list[str], set[str]]:
    """读唯一声明处 `team-kit-bridge/snapshot.json`。

    返回 (upstream, snapshot_paths, adapted 集合)。"""
    data = json.loads(IDENTITY.read_text(encoding="utf-8"))
    return (
        "%s@%s" % (data["upstream_repo"], data["upstream_commit"]),
        data["snapshot_paths"],
        set(data["adapted"]),
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect(
    snapshot_paths: list[str] | None = None,
    adapted: set[str] | None = None,
) -> dict[str, dict[str, str]]:
    """按 snapshot_paths 声明收集快照文件。两个参数缺省时读唯一声明处。

    未在 adapted 里的文件一律是内核：与上游字节级一致，动一个字节就要走整体
    重快照。声明的某个 snapshot_path 不存在时硬报错——声明写错或重快照时上游
    删了它，两种都要人看一眼。
    """
    if snapshot_paths is None or adapted is None:
        _, snapshot_paths, adapted = load_identity()
    files: dict[str, dict[str, str]] = {}
    missing_paths = []
    for rel in snapshot_paths:
        root = PLUGIN / rel
        if root.is_file():
            candidates = [root]
        elif root.is_dir():
            candidates = sorted(root.rglob("*"))
        else:
            missing_paths.append(rel)
            continue
        for path in candidates:
            if not path.is_file() or path.suffix in SKIP_SUFFIXES:
                continue
            if SKIP_DIRS & set(path.relative_to(PLUGIN).parts):
                continue
            key = path.relative_to(PLUGIN).as_posix()
            files[key] = {
                "sha256": sha256(path),
                "category": "adapted" if key in adapted else "kernel",
            }
    if missing_paths:
        raise SystemExit(
            f"snapshot.json 的 snapshot_paths 里声明的路径不存在：{missing_paths}\n"
            f"两种可能——声明写错，或上游在新提交里删掉了这些路径。\n"
            f"无论哪种都要人看一眼：改 {IDENTITY}，再跑本脚本重生成基准。"
        )
    return files


def main() -> int:
    upstream, snapshot_paths, adapted = load_identity()
    files = collect(snapshot_paths, adapted)

    missing = adapted - set(files)
    if missing:
        raise SystemExit(
            f"snapshot.json 的 adapted 里列出的文件在快照中不存在：{sorted(missing)}\n"
            f"两种可能——声明写错，或上游在新提交里删掉了这些文件。\n"
            f"无论哪种都要人看一眼：改 {IDENTITY}，再跑本脚本重生成基准。"
        )

    baseline = {
        "upstream": upstream,
        "files": files,
    }
    BASELINE.write_text(
        json.dumps(baseline, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    kernel = sum(1 for f in files.values() if f["category"] == "kernel")
    print(
        f"已写入 {BASELINE.relative_to(PLUGIN)}："
        f"{len(files)} 个文件（kernel {kernel} / adapted {len(files) - kernel}）"
    )
    print(f"  上游：{upstream}")
    print(
        "  已适配面："
        + ("、".join(sorted(adapted)) if adapted else "（无）")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
