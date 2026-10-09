# Arena candidate B · pstack minimal viable snapshot (Claude Code)

**Stance (fixed):** Port only what Claude Code loads at runtime — the `skills/**` and `agents/**` markdown trees. Everything else in the upstream `pstack` package is Cursor product surface or human onboarding, not agent payload. “Lossless use” means the **instruction graph** (mode router, playbooks, principles, routed skills, subagent briefs) is byte-preserved and discoverable after install — not that Cursor-only binaries, automations, or model-slug wiring execute identically.

**Upstream snapshot:** `cursor/plugins` @ `ccb5507cec1546dc88135c1139c811e6c59115ba` (path `pstack/` in that repo; local cache dir is the byte source for initial import).

**Prior art:** `sdlc/` snapshot discipline (`snapshot.json`, `kernel-baseline.json`, `update_baseline.py`, `test_snapshot_contract.py`, `.gitattributes`, ADR-0001 / ADR-0002).

---

## 1. Exact directory layout (`pstack/`)

Every file this candidate creates on first landing (110 kernel files under `skills/` + `agents/` come from upstream copy, not listed leaf-by-leaf).

```
pstack/
├── snapshot.json                          # pure-add · identity (ADR-0002)
├── CLAUDE.md                              # pure-add · agent-facing snapshot discipline
├── README.md                              # pure-add · human install + Claude Code caveats
├── .gitattributes                         # pure-add · -text on snapshot trees
├── .claude-plugin/
│   └── plugin.json                        # pure-add · Claude Code marketplace manifest
├── agents/                                # snapshot · 2 files (kernel)
│   ├── comment-sicko.md
│   └── poteto-agent.md
├── skills/                                # snapshot · 50 skill dirs, 106× .md + refs (kernel)
│   ├── architect/
│   ├── arena/
│   ├── …                                  # (48 more skill dirs — same names as upstream)
│   ├── poteto-mode/
│   │   ├── SKILL.md                       # adapted
│   │   ├── playbooks/                     # 23× .md (kernel)
│   │   └── references/                    # kernel (e.g. bugbot-triage.md)
│   │   # NO scripts/ — dropped subtree
│   └── setup-pstack/
│       └── SKILL.md                       # adapted
└── tests/                                 # pure-add · enforcement layer
    ├── __init__.py
    ├── update_baseline.py
    ├── test_snapshot_contract.py
    └── kernel-baseline.json               # generated · do not hand-edit
```

**Snapshot roots (frozen):** `pstack/skills/**` and `pstack/agents/**` only.

**Movable layer (everything else under `pstack/`):** `tests/`, `README.md`, `CLAUDE.md`, `.gitattributes`, `.claude-plugin/`, `snapshot.json`.

**Repo-level files touched on landing:**

| File | Change |
|------|--------|
| `.claude-plugin/marketplace.json` | Add `pstack` entry |
| `tools/run_tests.py` | Append `pstack/tests` to default `TARGETS` |
| `docs/agents/testing.md` | Update default directory list (four → five) |
| `tools/consistency_facts.json` | Add `pstack.*` and `plugins.description.pstack` facts |
| `README.md` (repo root) | Optional one-line market plugin list — only if root README already enumerates plugins |

**Not created:** `hooks/`, `commands/`, `LICENSE` copy (MIT attribution lives in `README.md`); upstream root `README.md`, `.gitignore`, `.cache-complete`.

---

## 2. Top-level source classification

Paths relative to upstream plugin root  
`…/pstack/ccb5507cec1546dc88135c1139c811e6c59115ba/`.

| Subtree | Class | One-line reason |
|---------|--------|-----------------|
| `skills/` (except `skills/poteto-mode/scripts/`) | **kernel** | Claude Code loads skill markdown; this is the product. |
| `skills/poteto-mode/scripts/` | **dropped** | Bun/TS babysit & orch CLIs; wired to Cursor Task/watch-pr; no Claude Code runner. |
| `skills/setup-pstack/SKILL.md` | **adapted** | Writes `~/.cursor/rules/pstack-models.mdc`; must target Claude Code user/project rules and inherit-parent semantics. |
| `skills/poteto-mode/SKILL.md` | **adapted** | Cursor model slugs, `AskQuestion`, `cursor-team-kit` `/deslop`, `subagent_type: poteto-agent` — relabel for Claude Code Task/subagent_types without changing playbook logic. |
| `agents/` | **kernel** | Subagent briefs referenced by poteto-mode; markdown-only. |
| `automations/` | **dropped** | Cursor Automations (Benny); not loadable in Claude Code plugin model. |
| `.cursor-plugin/` | **dropped** | Cursor marketplace manifest; replaced by `.claude-plugin/plugin.json` (pure-add). |
| `docs/guide/` | **dropped** | Human tutorial with Cursor screenshots/flows; agents do not load it; link upstream guide URL from README instead. |
| `assets/` | **dropped** | Logo for Cursor UI; no Claude Code plugin logo slot worth freezing bytes. |
| `README.md` (upstream) | **dropped** | Cursor `/add-plugin` copy; replaced by repo `pstack/README.md` (pure-add). |
| `LICENSE` | **dropped** | Not agent-loaded; MIT line + Lauren Tan / cursor/plugins attribution in pure-add README. |
| `.gitignore`, `.cache-complete` | **dropped** | Cursor cache plumbing; irrelevant in this repo. |

**In-snapshot totals (initial import):** ~108 files under `skills/` (128 upstream skill files − 20 under `scripts/`) + 2 under `agents/` → **~110 baseline entries**. Fifty skill directories, twenty-three playbooks under `poteto-mode/playbooks/`.

**Honest non-loss (called out, not hidden):** Several **kernel** playbooks still *mention* dropped scripts (e.g. babysit → `watch-pr`). Same class of debt as `sdlc`’s dangling hook installers: bytes stay upstream-faithful; CLAUDE.md documents **degrade paths** (`gh`, manual polling, repo `autopilot` skill if present). Resnapshot (D2) is the only time to reconcile upstream script + playbook changes.

---

## 3. `snapshot.json` (exact content)

```json
{
  "upstream_repo": "cursor/plugins",
  "upstream_commit": "ccb5507cec1546dc88135c1139c811e6c59115ba",
  "adapted": [
    "skills/setup-pstack/SKILL.md",
    "skills/poteto-mode/SKILL.md"
  ]
}
```

Paths in `adapted` are relative to **each snapshot root**, with a `skills/` or `agents/` prefix, matching keys in `kernel-baseline.json` (see §4).

Optional human-only note (not in JSON): upstream subpath `pstack/` within the monorepo; import copies from cache path given in the arena brief, not from a live submodule.

---

## 4. Tests and `consistency_facts` entries

### 4.1 Plugin-local tests (`pstack/tests/`)

Mirror `sdlc/tests/` shape but **without** Python CLI smoke tests (pstack snapshot has no in-tree `.py` product code).

**`update_baseline.py`**

- Read `pstack/snapshot.json` only (ADR-0002 D2).
- Walk **`pstack/skills/`** and **`pstack/agents/`** recursively; skip `__pycache__`, `*.pyc`.
- Baseline keys: POSIX paths from plugin root, e.g. `skills/poteto-mode/SKILL.md`, `agents/poteto-agent.md`.
- Fail hard if `adapted` lists a missing path (D6).
- Write `kernel-baseline.json` with `upstream`: `cursor/plugins@ccb5507cec1546dc88135c1139c811e6c59115ba`.

**`test_snapshot_contract.py`**

| Test class | Purpose |
|------------|---------|
| `KernelFrozenTest` | sha256 of every baseline file vs disk; baseline covers exactly `collect()` set (ADR-0001 D3.2). |
| `SnapshotIdentityFormatTest` | `upstream_commit` is 40-char lowercase hex (same as sdlc). |
| `SnapshotInventoryTest` (pure-add) | Structural smoke: `len(skills/*) == 50`; `len(poteto-mode/playbooks/*.md) == 23`; `agents/*.md == 2`; **`poteto-mode/scripts` must not exist**. |

Cross-file identity (README / CLAUDE / baseline ↔ `snapshot.json`) **not** duplicated here — delegated to repo fact guard (ADR-0003 D1).

**Run:** `cd pstack && python -m unittest discover -s tests -v`  
**Regenerate:** `cd pstack && python tests/update_baseline.py`

### 4.2 `tools/run_tests.py`

```python
TARGETS = (
    "sdlc/tests",
    "dsh-spec/hooks",
    "feishu-notify/hooks",
    "pstack/tests",
    "tools",
)
```

### 4.3 New `consistency_facts.json` rows

Copy the sdlc pattern; prefix `pstack.`:

| `name` | `source` | `copies` |
|--------|----------|----------|
| `pstack.upstream-repo-in-readme` | `pstack/snapshot.json` → `upstream_repo` | `pstack/README.md` regex `^- \*\*upstream\*\*: (?P<v>…)` |
| `pstack.upstream-commit-in-readme` | `upstream_commit` | same regex @ group |
| `pstack.commit-abbrev-in-claude-md` | `upstream_commit` | `pstack/CLAUDE.md` regex `cursor/plugins@([0-9a-f]{7,40})` · `prefix_of` |
| `pstack.upstream-repo-in-baseline` | `upstream_repo` | `pstack/tests/kernel-baseline.json` `"upstream"` before `@` |
| `pstack.upstream-commit-in-baseline` | `upstream_commit` | baseline `"upstream"` after `@` |
| `pstack.adapted-set` | `adapted` array | `kernel-baseline.json` keys where `category == "adapted"` |
| `plugins.description.pstack` | `pstack/.claude-plugin/plugin.json` → `description` | `.claude-plugin/marketplace.json` → `plugins[name=pstack].description` |

Self-proof per `docs/agents/testing.md`: break README commit or adapted category → `test_fact_*` red; revert → green.

---

## 5. `pstack/CLAUDE.md` (content outline)

Language: Chinese, matching `sdlc/CLAUDE.md` tone (this repo’s agent convention).

**Sections to include:**

1. **One paragraph** — What pstack is in Claude Code: poteto-mode + principle leaf skills + situational skills; install via marketplace `pstack@z-claude-plugins`.

2. **Snapshot discipline (动手前必读)** — Pointer to `docs/adr/0001` / `0002`.

3. **Classification by directory (D5-style exclusion):**
   - **`pstack/skills/` and `pstack/agents/`** → kernel vs adapted per `kernel-baseline.json` (`python tests/update_baseline.py` prints categories).
   - **Everything else under `pstack/`** → movable layer.

4. **Single fact source:** `snapshot.json`; README/CLAUDE copies pinned by fact guard.

5. **`.gitattributes`:** `skills/**` and `agents/**` are `-text` (Windows CRLF guard, ADR D3.1).

6. **Claude Code vs Cursor (explicit scope):**
   - Dropped: `automations/`, `.cursor-plugin/`, `docs/guide/`, `poteto-mode/scripts/`, assets.
   - `/setup-pstack` writes Claude-compatible rules (document target path chosen at implement time, e.g. user `CLAUDE.md` fragment or `~/.claude/…` — not Cursor `.mdc`).
   - Model lines in adapted `poteto-mode` map to **Claude Code subagent model slugs** available in the user’s harness; no Cursor-only slugs in adapted files.
   - References to `cursor-team-kit` `/deslop`, Cursor Automations, or `watch-pr` CLI: treat as **optional**; use repo skills (`code-review`, `autopilot`) or `gh` instead.

7. **Known legacy (kernel, intentional):** Playbooks that cite dropped scripts remain upstream bytes until next resnapshot; do not “fix” inside kernel files — either adapt at resnapshot or document degrade path here.

8. **Local ADR:** Decisions live in repo root `docs/adr/` if needed (e.g. “minimal snapshot scope”).

**Upstream cite line (abbrev ok):** `cursor/plugins@ccb5507` in body; fact guard enforces prefix of full SHA.

---

## 6. `pstack/README.md` (content outline)

Language: Chinese (match `sdlc/README.md`).

1. **Elevator pitch** — Rigorous agent workflows (poteto-mode, principles, verification-first); Claude Code port of cursor/plugins pstack.

2. **Enable:**
   ```
   /plugin marketplace add https://github.com/zengsipei/z-claude-plugins
   /plugin install pstack@z-claude-plugins
   ```

3. **Quick start (Claude Code):**
   - Run **`setup-pstack`** once (adapted skill) for model/role preferences.
   - Use **`poteto-mode`** (or say “work in poteto style”) for rigorous tasks.
   - **`poteto-help`** for routing questions among the ~50 skills.

4. **What you get / what you don’t:**

   | Loaded | Not shipped in this plugin |
   |--------|----------------------------|
   | 50 skills, 23 playbooks, 23 principles | Cursor Automations (Benny) |
   | 2 agent briefs | TypeScript babysit/orch scripts |
   | | Full human guide (link: `https://github.com/cursor/plugins/tree/main/pstack/docs/guide`) |

5. **Snapshot provenance (machine-pinned line):**
   `- **upstream**: cursor/plugins@ccb5507cec1546dc88135c1139c811e6c59115ba (YYYY-MM-DD)`  
   Date filled at import from GitHub commit metadata (not pinned by fact guard).

6. **License / credit** — MIT; original author Lauren Tan / cursor/plugins; this packaging zsp/z-claude-plugins.

7. **Maintainer note** — Resnapshot = whole replace per ADR D2; run `update_baseline.py` after.

---

## 7. `.claude-plugin/plugin.json` (draft)

```json
{
  "name": "pstack",
  "version": "0.15.15-claude.1",
  "description": "Poteto 式严谨 agent 工作流（poteto-mode、23 条 playbook、原则叶技能与验证优先纪律）的 Claude Code 快照移植；仅含 skills/ 与 agents/ 可加载面。",
  "author": {
    "name": "zsp",
    "url": "https://github.com/zengsipei"
  },
  "homepage": "https://github.com/zengsipei/z-claude-plugins/tree/main/pstack",
  "repository": "https://github.com/zengsipei/z-claude-plugins",
  "license": "MIT",
  "keywords": [
    "pstack",
    "poteto-mode",
    "workflow",
    "principles",
    "agent-style",
    "verification"
  ]
}
```

**`marketplace.json` entry:**

```json
{
  "name": "pstack",
  "source": "./pstack",
  "description": "<same string as plugin.json description>",
  "homepage": "https://github.com/zengsipei/z-claude-plugins/tree/main/pstack",
  "category": "engineering"
}
```

Version suffix `-claude.1` signals packaging fork; upstream semver `0.15.15` noted in README prose only.

---

## 8. Verification surface (“lossless use” for Claude Code)

### 8.1 Automated (CI)

1. `python tools/run_tests.py` green on `ubuntu-latest`.
2. **`KernelFrozenTest`** — any drift in 110 snapshot files fails unless baseline regenerated after intentional resnapshot.
3. **`SnapshotInventoryTest`** — prevents silent shrink (missing skill dir, deleted playbooks, reintroduction of `scripts/`).
4. **`tools/test_consistency.py`** — pstack identity + marketplace description parity.

### 8.2 Import fidelity (one-time, scripted)

**`tools/import_pstack_snapshot.py`** (pure-add at implement time, optional but recommended):

- Input: arena cache path or `git archive` of `cursor/plugins@ccb5507…` subpath `pstack/`.
- Copy `skills/**` except `skills/poteto-mode/scripts/**`; copy `agents/**`.
- Apply adapted templates for the two SKILL.md files (or copy then patch in a dedicated commit).
- Run `update_baseline.py`; commit baseline + snapshot together.

Post-import: `diff -rq` (or Python hash compare) against cache for every included relative path → must match upstream bytes for **kernel** files.

### 8.3 Runtime smoke (manual, pre-merge checklist)

1. Install plugin from local marketplace path.
2. Confirm **50** skills visible / invokable (spot-check: `poteto-mode`, `principle-prove-it-works`, `architect`, `unslop`).
3. Start a session with “use poteto-mode for a small investigation-only task” → agent reads `poteto-mode/SKILL.md`, names principles, picks Investigation playbook.
4. Spawn subagent with **`poteto-agent`** type (or Claude equivalent) → brief loads `agents/poteto-agent.md` + full poteto-mode read.
5. **`setup-pstack`** completes without referencing `~/.cursor/rules`.

### 8.4 What we explicitly do **not** claim

- Cursor model slug parity, Automations, Benny templates, or `watch-pr` binary behavior.
- Pixel-identical repo to upstream tarball (165 files → ~110 + movable layer).

### 8.5 What we **do** claim

- The **same markdown instruction system** Lauren Tan ships for rigorous work is present, frozen, and auditably tied to `ccb5507…`.
- Adapted surface is **minimal (2 files)** and documented; everything else is either byte-kernel or honestly dropped.

---

## 9. Why this is the honest reading of “lossless use”

| If we froze the full 165-file tree | Minimal markdown snapshot |
|-----------------------------------|---------------------------|
| Kernel baseline mixes runnable TS and inert markdown — reviewers cannot tell what matters. | Every baseline byte is loadable agent instructions. |
| `KernelFrozenTest` green while Claude Code cannot run watch-pr → false confidence. | Green baseline ⇒ markdown graph intact; script gaps explicit in CLAUDE.md. |
| Frozen Cursor `.mdc` paths and slugs become lying instructions in Claude Code. | Two adapted SKILL.md files retarget wiring; 108 other files stay trustworthy upstream copies. |
| Larger resnapshot diff noise on upstream churn in automations/docs. | Resnapshot diff focuses on skills/agents — the actual workflow product. |

**Principle:** ADR-0001 defines kernel as “upstream content本体” **for what we port**. Choosing Claude Code as consumer **narrows the port boundary** before snapshotting; that is surface adaptation at the package level, not cherry-pick inside kernel files.

---

## 10. Implementation sequence (for implementers)

1. Create `pstack/` movable-layer files (`snapshot.json`, `.gitattributes`, empty `tests/` scaffold).
2. Run import script → populate `skills/`, `agents/`; delete any accidental `scripts/` copy.
3. Patch **`skills/setup-pstack/SKILL.md`** and **`skills/poteto-mode/SKILL.md`** (adapted); record rationale in commit message.
4. `python pstack/tests/update_baseline.py` → commit `kernel-baseline.json`.
5. Add tests + fact rows + marketplace + `run_tests.py`.
6. Self-proof facts; manual runtime smoke (§8.3).
7. Optional: `docs/adr/0004-pstack-minimal-snapshot-scope.md` if the repo wants the package-level boundary on record.

---

*Candidate B · minimal viable snapshot · Claude Code consumer · arena design package.*
