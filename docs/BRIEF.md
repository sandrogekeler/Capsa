# Capsa — Project Brief

**Name:** Capsa
**What it is:** Asset library for VFX/3D
**Owner:** Sandro
**Type:** Personal tool + learning project (built with Claude Code)
**Status:** Idea / pre-phase 1

---

## 0. The name

**Capsa** is Latin for *box*: specifically the cylindrical case Romans used to store and carry scrolls.

- **The box:** it holds the library. Every model, texture and HDRI goes in, nothing gets lost.
- **The scroll case:** a capsa didn't hold loose things, it held a *catalogued* collection: scrolls with labels on the ends, so you could find one without unrolling them all. That is the job: index and label, so you find the asset without opening every file.
- **The word lives on:** *capsa* became *case*, *caisse* and *capsule*, all words for something that keeps contents safe and portable.

The mark is the box itself: a squared C turned on its side, with the lid lifted off in the accent blue.

---

## 1. What this is

A personal tool for my Houdini/Solaris (USD, Karma) workflow that lets me:

1. Index the asset folders I already have (models, USD, textures, HDRIs, caches, HDAs) without moving or changing anything.
2. Find any asset fast: thumbnails, search, tags, filters by type.
3. See what an asset is before opening it: preview, metadata, texture sets, dependencies, missing files.
4. Get it into Houdini with one action.

It is also a **learning project**: the goal is not only a working tool, but for me to understand every part of it well enough to explain and extend it without AI.

## 2. Why

- My assets live across drives and downloads in different formats; I re-download or re-build things I already own because I can't find them.
- Existing free options are either tied to one DCC (Blender's asset browser, Houdini's shelf) or are full studio pipelines that are too heavy for one artist.
- Portfolio piece next to Laterna: a second pipeline tool, sharing stack and conventions.
- Learn pipeline/TD concepts: asset metadata, USD composition, image I/O, indexing and search.

## 3. Non-goals

- Not a Prism/ShotGrid/ftrack replacement (no shots, tasks or reviews).
- Not a cloud store or marketplace; files stay where they are on my drives.
- Never moves, renames or rewrites my files. Capsa only reads them and keeps its own index.
- Not multi-user.
- Not distributed publicly or sold.

---

## 4. Features by phase

Each phase must be usable on its own before starting the next.

### Phase 1 — Index & browse (core)
- Library roots: point Capsa at folders; it scans them read-only and keeps watching for changes.
- Asset detection: group files into one asset (e.g. a model plus its texture folder) instead of listing every file.
- Supported first: USD (`.usd/.usda/.usdc/.usdz`), Alembic, FBX, OBJ, textures (EXR, TX, PNG, JPG, TIFF), HDRIs.
- Thumbnails for images and HDRIs (OpenImageIO), cached outside the library.
- Grid browser with search (SQLite full-text), filter by type, size, date.
- Tags, favourites, collections.
- Path copy and "show in Explorer".

### Phase 2 — Inspect
- Asset page with metadata: format, size, units, bounds, poly count, frame range.
- USD summary: prim tree, variants, materials, references and layers it depends on.
- Texture sets: detect PBR sets by naming (basecolor, roughness, normal…) and show them together.
- Dependency check: flag missing textures and broken references.
- HDRI preview with exposure control.
- 3D preview in the browser for USD/glTF-convertible assets.

### Phase 3 — Into Houdini
- Small Houdini Python panel (runs inside my open Houdini session) that browses Capsa and imports the selected asset into SOPs or as a USD reference in LOPs.
- Drag and drop where Houdini allows it.
- Thumbnails for 3D assets: render a turntable still once and cache it.

### Later / maybe
- Versions: see `v001…v00N` of an asset as one item with history.
- Duplicate finder (same file in several places).
- Local AI tagging/search by image content (e.g. "rusty metal", "pine tree").
- Laterna link: show which renders used an asset.
- Publishing assets into a structured library (the step toward a pipeline; see open decisions).

---

## 5. Open decisions (decide with Claude Code, log in DECISIONS.md)

- **Scope:** personal library (index what exists, phases above) vs. production pipeline (publish, versioning, asset structure Capsa controls). The brief assumes *library first*; pipeline features stay in "Later" unless decided otherwise.
- **Stack:** same as Laterna (Python + FastAPI, React, SQLite FTS, usd-core, OpenImageIO) and whether to share code with it.
- **What counts as one asset:** folder-based, name-based, or a sidecar file per asset.
- **Where Capsa's data lives:** one central index vs. small sidecar files next to assets (sidecars would mean writing into my folders).
- **3D thumbnails without a Houdini licence:** usd-core + a lightweight renderer, Blender in background mode, or the browser preview captured to an image.
- **Houdini integration:** Python panel vs. shelf tool vs. a package with both.

Unverified assumptions to check before building:
- That usd-core reads the USD files Houdini writes, including Houdini-specific schemas, well enough for the summary.
- That the OpenImageIO wheels on Windows read EXR and `.tx` correctly, including multi-part EXRs.
- That `.bgeo`/`.sc` can't be read without Houdini; if so, they get file-level info only until phase 3.
- How large my library actually is (file count, size), to know if scanning needs to be clever from day one.

---

## 6. Learning setup

Same setup as Laterna. The code stays clean and normally commented; the explanations live in `docs/`.

```
docs/
├── learn/            # Plain-language explanations, beginner level
│   ├── 00-overview.md        # The whole system explained simply
│   ├── glossary.md           # Every technical term, explained with analogies
│   └── <module>.md           # One file per module: what it does, why, how data flows
├── DECISIONS.md      # One entry per decision: what, why, alternatives, trade-offs
├── CONVENTIONS.md    # Naming, folder structure, code style
└── ARCHITECTURE.md   # Diagram + short description of components
```

### Rules for learning docs
- Assume zero programming background. Use analogies from VFX where possible (e.g. "like a Houdini node network", "like a texture cache").
- Every new module gets a `docs/learn/` page in the same session it is written.
- Every non-obvious choice gets a DECISIONS.md entry.
- After each feature, Claude explains what was built and asks me 2–3 questions to check understanding.
- Once per phase, I change something by hand, without Claude, and note what I learned.

### DECISIONS.md entry format
```
## YYYY-MM-DD — Title
**Decision:** what we chose
**Why:** reason in plain language
**Alternatives:** what else was possible and why not
**Trade-off:** what we give up
```

---

## 7. Notes for Claude Code

- Keep CLAUDE.md short: project summary, stack, commands, conventions. Point to `docs/` by path; do not import the learning docs.
- Work in small steps. Propose a plan before large changes.
- Prefer simple, readable solutions over clever ones; I need to understand them.
- Don't add features beyond the current phase without asking.
- Capsa is read-only towards the library: never write, move or delete files in library roots.
- Never use a Houdini licence from Capsa itself; the Houdini panel runs only inside a session I opened.
- When unsure about USD/Houdini/file-format behaviour, say so and suggest how to verify instead of guessing.

---

## 8. Brand

Settled. Logo files and rules: [`docs/brand/`](brand/README.md).

- Wordmark: squared CAPSA built on a 1u grid (1u = stroke width); the top of each A is a blue lid bar.
- Mark: the box — a C turned 90° with a cut in its base and a blue lid, 5u square, same height as the letters.
- Spacing: one gap g = 0.6u everywhere; A, P and S share one centre line at 2.7u; mark to name and clear space = 3g.
- Dark, minimal; accent blue `#4F8CFF`. Full colour/type system waits until the UI exists.

---

## 9. Portfolio framing

Presented honestly as: *"A personal asset library I designed and directed, built with Claude Code as a learning project. Decisions and architecture are documented in `docs/`."*
