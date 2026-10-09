# Arena synthesis · pstack snapshot port

Arena for the pstack port design. Two candidates, one dropped out, one delivered. The shipped design diverges from the surviving candidate's recommendation; this note records why.

## Candidates

- **A · maximal snapshot** — `claude-opus-5-thinking-high`. **Dropped out**: model unavailable on the current plan, agent never ran, no artifact.
- **B · minimal viable snapshot** — delivered `docs/arena-pstack/candidate-b.md`. Recommends freezing only `skills/` + `agents/` (~110 files), dropping `automations/`, `docs/guide/`, `assets/`, `.cursor-plugin/`, and `skills/poteto-mode/scripts/`, and adapting two SKILL.md files for Claude Code model/rules wiring.

## What shipped

Maximal snapshot. Everything under the upstream plugin root is frozen byte-identical, including the trees B recommended dropping. Three-file adapted surface (`comment-sicko.md`, `no-comments/SKILL.md`, `poteto-mode/SKILL.md`) covering only identifier renames, not B's proposed behavioral rewiring.

## Why B's recommendation was not taken

B optimizes for "every frozen byte must be loadable by Claude Code," and treats the Cursor-only trees as dead weight. That is a real concern, but the cost of dropping them is higher than the cost of keeping them.

- **Re-snapshot safety** (ADR-0001 D2). The repo's update path is whole-tree replacement against a new upstream commit. A maximal snapshot makes that a single `robocopy`/`git archive` with no per-file judgment. B's minimal snapshot re-introduces a hand-maintained drop-list on every re-snapshot, which is exactly the drift vector ADR-0001 was written to remove.
- **Cursor references are load-bearing prose, not dead code.** The playbooks that mention `cursor-team-kit`, `watch-pr`, and Cursor cloud agents are read by the agent as *instructions it can adapt*, not as binaries it must execute. Freezing them preserves the upstream intent; B's plan to rewrite them into Claude Code form would have put the two most-changed upstream files onto the hand-merge path on every re-snapshot.
- **The "false green" risk B names is real but smaller than it looks.** A frozen TS script that cannot run is honest — the failure surfaces at use time. The CLAUDE.md "已知遗留" section documents these gaps, mirroring how `sdlc` handles its dangling hook installers.

## What was taken from B

- The seven consistency-fact rows (`pstack.*` and `plugins.description.pstack`) — shipped exactly as B specified.
- The `CLAUDE.md` "Claude Code vs Cursor" scope section — shipped as the 已知遗留 table.
- The general README shape — shipped in condensed form.
- The kernel-baseline test structure (`KernelFrozenTest`, `SnapshotIdentityFormatTest`) — shipped, generalized from sdlc's single-dir snapshot to pstack's multi-path snapshot via `snapshot_paths`.

## Dropout note

Candidate A produced no artifact. Its stance (maximal snapshot) was nonetheless the shipped shape, chosen on the ADR-0001 grounds above rather than from its analysis.
