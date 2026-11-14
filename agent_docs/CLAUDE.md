# Capsa

Asset library for VFX/3D: a personal tool for Sandro's Houdini/Solaris (USD,
Karma) workflow that indexes existing asset folders and finds assets fast. It
is also a learning project: Sandro must be able to explain and extend every
part without AI. Phase 1 has started: scanner, index, thumbnails, a command
line and a first window. The brief is `docs/BRIEF.md`.

## Stack

- Python 3.13, packaged with uv (`pyproject.toml`, `uv.lock`). OpenImageIO
  reads images; a frameless pywebview window shows plain HTML and JS.
- pytest for unit tests, ruff 0.16.7 through aislop for lint.
- Runs on Windows now and Linux later.
- Planned, not installed: usd-core. No FastAPI, no React (`docs/DECISIONS.md`).

## Project structure

- `src/capsa/`: `scanner.py` lists the files under a library root, `assets.py`
  groups them into assets, `index.py` keeps the assets in SQLite and searches
  them, `thumbnails.py` makes a preview of an image and reads its size,
  `library.py` runs them in order and names the data folder, `window.py` and
  `web/` are the window, `__main__.py` is the `capsa` command.
- `tests/`: unit tests. Houdini is not available in Claude's environment; what
  Sandro's machine showed is in issue #11.
- `docs/`: the brief (`BRIEF.md`), decisions (`DECISIONS.md`), architecture,
  conventions, brand, design and website. `docs/learn/`: beginner
  explanations, one page per module.
- `agent_docs/`: these instructions, the roadmap and the dependency inventory.

## Architecture rules

- Capsa never writes, moves, renames or deletes anything inside a library
  root. Its index, settings and thumbnail cache live in its own data folder.
- Capsa never uses a Houdini licence: no hython, no `hou`, no Houdini
  libraries. Code for Houdini runs only inside a session Sandro opened.
- Capsa contains no SideFX code and never converts or re-saves Houdini files.
- Paths go through `pathlib`. Nothing depends on one operating system.
- Houdini, USD and file-format behaviour: when unsure, say so and propose how
  to verify on Sandro's machine. Never guess.

## Working rules

- Small steps. Propose a plan before a change that touches more than one
  module.
- Stay inside the current phase of the brief. Ask before adding anything from
  a later one.
- Simple, readable code over clever code.
- Every new module gets a `docs/learn/<module>.md` page in the same pull
  request, and new terms go into `docs/learn/glossary.md`.
- Every non-obvious choice gets an entry in `docs/DECISIONS.md`.

## Build & dev commands

```sh
uv run python3 .claude/suite-check.py   # every health check in .claude/suite.json
uv run pytest -q                        # unit tests
uv run capsa scan                       # add <folder>, scan, search <words>
```

`uv run` puts the pinned ruff first on the path; without it the aislop check
is skipped. CI (`.github/workflows/checks.yml`) runs the tests on Windows and
Linux.

## Task tracking
Work is tracked in GitHub Issues. Every issue carries a `type:`, an `area:` and
exactly one priority (`p0`-`p3`) label. The issue forms ask for it and the
`issue-priority` workflow applies it; an issue opened through the API (by an
agent) sets the label in the same call, `p2` when unclear. Close issues from
the pull request with `Fixes #N`.

## Commits & pull requests

- One pull request per piece of work, never one per tweak. Its `## Changelog`
  section gives each change a line (`- feature: ...`, `- fix: ...`,
  `- chore: ...`). Split only for risk, an independent revert or a different
  release.
- Changelog lines and titles are public release-notes copy: imperative,
  sentence case, no trailing period, no em dashes.
- Every pull request needs an `area:` label, plus a `type:` label when it has
  no Changelog section, before it can merge (the `pr-labelled` status). Which
  type: see `.github/pull_request_template.md`.

## Files that come from the template

This repo was created from sandrogekeler/AllesSandro and is kept in step with it
by Renovate (`.copier-answers.yml` records the version). Two kinds of file:

- **Locked** (re-applied on every template update): `.claude/suite-*.py`,
  `.github/workflows/{codeql,scorecard,pr-labelled,labels,template-guard,issue-priority}.yml`
  (CodeQL and Scorecard only on a public repo) and the optional `aislop.yml`,
  `claude.yml`, `.aislop/base.yml`, `.github/scripts/changelog-section.py`,
  `.github/scripts/release-notes.py`,
  `.claude/rules/{writing,simplicity,typography}.md`. Do not edit them here: change
  AllesSandro instead. A local edit is kept but shows up as a merge conflict on
  the next template update.
- **Seeded** (created once, owned by this repo): everything else, including
  this file.

A template-update PR with `<<<<<<< before updating` markers: see
`.claude/rules/template-files.md`.

## Docs

Describe what is on disk, in the present tense. Intent goes in
`agent_docs/ROADMAP.md` as an unchecked item. Unsure whether something landed?
Check before writing it down.

## Do not

- Commit secrets, `.env` files or credentials.
- Edit generated files or lockfiles by hand; regenerate them.

## Deeper rules, loaded on demand

`.claude/rules/*.md`: each one names the paths that load it.
