# AGENTS.md

- Issues: GitHub issues in `zengsipei/z-claude-plugins` via `gh`. Read `docs/agents/issue-tracker.md` before creating, reading, listing, commenting, labeling, or closing an issue.
- Triage: label name equals role name. Read `docs/agents/triage-labels.md` before applying or changing a triage label.
- Domain: single-context — root `GLOSSARY.md` plus `docs/adr/`; no `GLOSSARY-MAP.md`. Missing files: proceed. Read `docs/agents/domain.md` before exploring for domain terms or decisions.
- Tests: `python tools/run_tests.py` only. Root `python -m unittest discover` finds 0 tests. One consistency fact = one line in `tools/consistency_facts.json`. Read `docs/agents/testing.md` before running tests or adding a fact.
