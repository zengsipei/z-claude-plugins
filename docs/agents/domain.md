# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`GLOSSARY.md`** at the repo root, or
- **`GLOSSARY-MAP.md`** at the repo root if it exists: it points at one `GLOSSARY.md` per context. Read each one relevant to the topic.
- **`docs/adr/`**: read ADRs that touch the area you're about to work in. In multi-context repos, also check `src/<context>/docs/adr/` for context-scoped decisions.

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The `/domain-modeling` skill (reached via `/grill-with-docs` and `/improve-codebase-architecture`) creates them lazily when terms or decisions actually get resolved.

> The "proceed silently" rule is scoped to *absence*, not to a **broken pointer**. A doc that names a file which does not exist is a defect, not a case to ignore quietly — surface it. This repo renamed `CONTEXT.md` → `GLOSSARY.md`; `docs/adr/0001` and `0002` still say `CONTEXT.md` on purpose (accepted ADRs are immutable history) and are not broken pointers.

## File structure

Single-context repo (most repos):

```
/
├── GLOSSARY.md
├── docs/adr/
│   ├── 0001-event-sourced-orders.md
│   └── 0002-postgres-for-write-model.md
└── src/
```

Multi-context repo (presence of `GLOSSARY-MAP.md` at the root):

```
/
├── GLOSSARY-MAP.md
├── docs/adr/                          <- system-wide decisions
└── src/
    ├── ordering/
    │   ├── GLOSSARY.md
    │   └── docs/adr/                  <- context-specific decisions
    └── billing/
        ├── GLOSSARY.md
        └── docs/adr/
```

This repo (`z-claude-plugins`) is **single-context**: one root `GLOSSARY.md` plus `docs/adr/`. No `GLOSSARY-MAP.md`. The repo collocates multiple independent Claude Code plugins (`_template`, `feishu-notify`, `dsh-spec`) but has no shared build/workspace tooling (no `package.json`, no workspace file), so it is treated as an aggregate, not a monorepo.

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `GLOSSARY.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal: either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders), but worth reopening because…_