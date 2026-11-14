# Decisions

One entry per non-obvious choice. Newest at the bottom.

```
## YYYY-MM-DD: Title
**Decision:** what we chose
**Why:** reason in plain language
**Alternatives:** what else was possible and why not
**Trade-off:** what we give up
```

## 2026-11-11: Interface layout
**Decision:** Three views (Catalogue, Search, Inspector) in one frameless window, with settings as a side sheet. Spec and clickable prototype in [`docs/design/`](design/README.md).
**Why:** Browsing, finding and inspecting are the three jobs in phases 1 and 2. Keeping them in one window with one selection colour keeps it calm.
**Alternatives:** A pro-tool layout with docked panels and a shortcut bar. Rejected as too busy for a personal library. Shortcuts went into the right-click menu instead.
**Trade-off:** Less on screen at once. Detail like paths of missing files goes to the log, not the window.

## 2026-11-12: Python 3.13, managed with uv
**Decision:** Capsa's core is a Python 3.13 package in `src/capsa/`. uv installs Python and the dependencies and keeps their exact versions in `uv.lock`.
**Why:** The libraries the brief names have Windows wheels for 3.13: usd-core 26.11 supports 3.11 to 3.14, OpenImageIO 3.2.2 supports 3.9 to 3.15 (PyPI, checked 2026-11-11). Python is also Houdini's scripting language. uv is one program for what otherwise takes three (a Python installer, venv, pip), and the same two commands work on Windows and Linux.
**Alternatives:** pip with `requirements.txt`, as in Kompass: no lockfile, and a virtual environment to manage by hand. Python 3.11, to match Houdini 20.5 and 21.0: not needed, a Houdini panel runs in Houdini's own Python and talks to Capsa from outside.
**Trade-off:** uv has to be installed once on every machine.

## 2026-11-12: The roadmap lives in `agent_docs/ROADMAP.md`
**Decision:** One roadmap, at the path the project template and `.claude/suite.json` use.
**Why:** The brief asked for it in `docs/`. Two roadmaps would drift apart.
**Alternatives:** `docs/ROADMAP.md` as in Laterna, with the template's file pointing to it.
**Trade-off:** Capsa and Laterna differ here.

## 2026-11-12: The window is a pywebview window
**Decision:** Capsa opens in its own frameless pywebview window, never as a browser app. The interface inside the window is a web page.
**Why:** The interface spec asks for one frameless window with its own title bar, which a browser tab cannot be. pywebview is one Python package: `frameless=True`, a drag region, and `minimize()` and `maximize()` (https://pywebview.flowrl.com/api/). On Windows it draws the page with Edge WebView2. Chosen by Sandro (2026-11-12, #7).
**Alternatives:** A browser tab only, as in Laterna: no title bar of its own. Tauri with the Python backend as a sidecar: also WebView2 on Windows, so a 3D preview renders the same, but it adds Rust, the C++ Build Tools and a PyInstaller build.
**Trade-off:** No installer comes with it. On Linux pywebview needs Qt or GTK, untested. A preview that matches Karma would need Hydra, which neither option provides.

## 2026-11-12: The scanner reads names, sizes and dates only
**Decision:** A scan lists every file under a library root with its size, modified time and a kind taken from the file name. It opens no file. An `.exr` counts as a texture and an `.hdr` as an HDRI.
**Why:** Names, sizes and dates come from the folder listing, which is fast and cannot damage a file. Telling an HDRI from a texture needs the image's size or its folder, which belongs to asset detection (#15).
**Alternatives:** Open each file during the scan to read its contents: slow on a large library, and one broken file could stop the scan.
**Trade-off:** HDRIs saved as `.exr` show up as textures until asset detection exists.

## 2026-11-12: One central index in SQLite
**Decision:** Everything Capsa knows is in one SQLite file in Capsa's own data folder. Search uses SQLite's FTS5. A file that disappears is marked missing, not removed.
**Why:** The brief forbids writing into library roots, which rules out sidecar files beside assets. SQLite is one file, needs no server and comes with Python, FTS5 included (CPython's Windows build sets `SQLITE_ENABLE_FTS5`; not yet run on Sandro's machine, #11). Marking keeps tags when a drive is unplugged.
**Alternatives:** Sidecar files next to each asset: they travel with the asset, but write into the library. A JSON file: simple, but every search would read all of it.
**Trade-off:** Tags live only in the index. Move an asset folder to another machine and its tags stay behind. Missing rows pile up until something cleans them, which nothing does yet.

## 2026-11-12: What the checks on Sandro's machine showed
**Decision:** Build for the library as it is: 516 files, 9.93 GB, one root on a fixed disk, mostly ambientCG materials and HDRIs. No Component Builder assets, no `.tx`, no Houdini-written USD. Full results: issue #11.
**Why:** usd-core 26.11, OpenImageIO 3.2.2.0 and FTS5 all work on Windows 11 (Python 3.14.5). A walk of the whole library takes 0.02 s. A 256 px thumbnail of an 8k `.exr` or `.hdr` takes 1.4 to 1.9 s. OpenImageIO cannot read `.rat`. A Houdini 21 Component Builder asset names its thumbnail in `assetInfo` (`previews.thumbnails.default.defaultImage`, here `./thumbnail.png`).
**Alternatives:** Build Component Builder detection first, as the interface spec proposes: nothing in the library would use it.
**Trade-off:** Rules fitted to one library. A different folder layout needs new rules.

## 2026-11-12: A texture-set folder is one asset
**Decision:** A folder holding two or more different texture maps is one material, named after the folder, with everything directly in it. Every other file is its own asset. A `.rat` copy joins the file it was made from. A lone `.exr` counts as an HDRI.
**Why:** It matches the library: a material is a folder of maps (`metal_053B/`), an HDRI is one file with an optional `.rat` beside it. No file is written into the library.
**Alternatives:** Every file an asset: 450 material files as 450 tiles. Every lowest folder an asset: `hdri/exterior/4k` would be one tile holding all its HDRIs. A sidecar file per asset: writes into the library.
**Trade-off:** Two sets in one folder merge into one material. Resolutions of one material in sibling folders show as separate materials. An `.exr` that is not an HDRI is mislabelled until the image's proportions are read.

## 2026-11-12: The index stores assets
**Decision:** The index keeps one row per asset and the asset's files beneath it. Search returns assets and looks at their paths, not at the names of the files inside. The schema version is 2; an index of version 1 is refused, not converted.
**Why:** The catalogue shows assets, and tags and favourites will belong to an asset. Searching file names would answer "roughness" with every material in the library.
**Alternatives:** Keep files as the unit and group them on every search: the grouping would run for each keystroke. Convert version 1 files: the only one in existence is a test file.
**Trade-off:** A map cannot be found by its own file name. If a folder turns into a material because maps were added, its former single assets go missing and a new asset appears.


## 2026-11-12: Thumbnails are 512 px JPEGs named after the file's state
**Decision:** A thumbnail is a JPEG, 512 px on its longest side, never larger than the source. Its file name is a hash of the source's path, size and date. `.exr` and `.hdr` are converted from linear to sRGB and clipped at white. Of a file with several parts the first is used, of its channels the first three. The cache folder is handed in by the caller.
**Why:** A changed file gets a new name, so no thumbnail can be stale and nothing has to compare dates. 512 px covers a tile on a 4k screen; the cost is in reading the source (1.4 to 1.9 s for an 8k HDRI on Sandro's machine), not in the size written. OpenImageIO reads every image format in the library except `.rat` and has wheels for Windows and Linux.
**Alternatives:** Naming the thumbnail after the asset's id: needs the index to know when to remake it. PNG: no loss, several times the size. A tone-mapped HDRI: closer to how it lights a scene, but one more look to choose.
**Trade-off:** The thumbnail of a changed or deleted file stays in the cache until something clears it, which nothing does yet. A bright sky clips to white. Making one blocks the caller: running it in the background is the server's job (#17). `.rat`, models and USD files get no thumbnail.

## 2026-11-12: A command line before the window
**Decision:** `capsa add <folder>`, `capsa scan` and `capsa search <words>` run the scanner, grouping, index and thumbnails from a terminal. Capsa's data is in `%LOCALAPPDATA%\Capsa` on Windows and `$XDG_DATA_HOME/capsa` on Linux. Library roots are stored in the index.
**Why:** The parts can be tried on the real library before the server and the window exist, and the window will call the same `refresh`. `%LOCALAPPDATA%` is where Windows keeps data that belongs to one machine; an index of local drive paths should not roam to another.
**Alternatives:** Wait for the window: nothing could be checked on the real library until three more parts are built. A data folder beside the code: lost with a fresh checkout, and inside the repository.
**Trade-off:** One more way in to keep working. `capsa scan` makes thumbnails one after another and prints nothing until a root is done: with many 8k HDRIs the first scan takes minutes.

## 2026-11-12: Numbered frames are one asset
**Decision:** Three or more images in one folder whose names differ only in a trailing number of the same width, with no gap, are one image sequence. `Gloss` and `Mask` count as map words.
**Why:** The first scan of Sandro's library gave 352 assets, 301 of them loose textures; 240 were the frames of one caustics sequence. The marks sets (`_Gloss`, `_Mask`, `_Roughness`) stayed loose because two of their three words were unknown.
**Alternatives:** Any shared prefix with a number: photos like `IMG_4512`, `IMG_4519` would become a sequence. A minimum of 24 frames: short sequences stay loose.
**Trade-off:** A sequence with one missing frame falls apart into single files. Numbered overlays such as `Dust_01` to `Dust_06` become one sequence.

## 2026-11-13: A regrouped asset is forgotten
**Decision:** An asset the scan did not find, whose files the same scan put into other assets, is deleted from the index instead of marked missing.
**Why:** After the sequence rule, the rescan of Sandro's library marked 274 assets missing: the 240 caustics frames and the loose marks maps, all still on disk inside the new sequence and materials. Nothing would ever clear that mark.
**Alternatives:** A command that deletes every missing row: also deletes the rows of an unplugged drive, with their tags.
**Trade-off:** A tag on a regrouped asset is lost. No asset has tags yet.

## 2026-11-13: The window talks to Python through pywebview, in plain JavaScript
**Decision:** The page calls Python through pywebview's JS API (`window.Api`, `pywebview.api.<name>` in JavaScript). No FastAPI, no React, no build step. Thumbnails reach the page as data URLs. Sandro chose this on 2026-11-13 (#7).
**Why:** pywebview's docs: the JS API "allows communication between Python and Javascript domains without a web server". One process, no API server (pywebview only serves the page files on `127.0.0.1`), no CSRF protection to get right, and every file of the page is readable as it is.
**Alternatives:** FastAPI + plain JavaScript: an HTTP API a Houdini panel could reuse, at the cost of a server and CSRF protection. FastAPI + React: the brief's first plan; adds a JavaScript build and React to learn before the first grid.
**Trade-off:** A Houdini panel cannot call the window; it would read the SQLite index itself. Each thumbnail travels as Base64 text, about a third larger than the file. Each call opens its own index connection, because pywebview runs calls in separate threads.

## 2026-11-13: The sidebar shows Materials as a group of its own
**Decision:** Library in the sidebar lists All, Models, Materials, Textures, HDRIs and Caches. Image sequences count as Textures. Missing files appears under Needs attention only when an asset is missing. The page sorts the assets into groups itself from the answer to `search("")`.
**Why:** Most of Sandro's library is ambientCG materials (#11). The design lists no Materials group, and putting them under Textures would hide them among single images.
**Alternatives:** The design's list without Materials. One group per kind: eleven entries, most of them empty.

## 2026-11-13: Favourites and tags are kept by path, not by asset
**Decision:** `favourites` and `tags` name a root and a root-relative path, not an asset id. A rescan that forgets or regroups an asset leaves them in place; an asset with that path picks them up again. Index version 3; a version 2 file is upgraded on open. Sandro chose this on a card (2026-11-13).
**Why:** They are the only data Capsa cannot rebuild from the library. Frames that become a sequence and back, or a folder renamed and renamed back, must not cost them.
**Alternatives:** A column on `assets` or a table keyed by asset id: simpler, but a regroup deletes the row and the tags with it.
**Trade-off:** Marks of a path that never returns stay in the file. They are a few bytes each and nothing shows them.

## 2026-11-13: Assets remember when a scan first found them
**Decision:** `assets.added` holds when a scan first found an asset. Added this week and the Recent sort use it. Assets already in an index of version 3 get the time of the upgrade to version 4. Collections are kept by root and path, as favourites and tags are.
**Why:** "Added" means added to the library, which a file's own date does not say: copying a file keeps its date. The upgrade time is the earliest moment Capsa can vouch for.
**Alternatives:** The newest file's date: wrong for copied files. Zero for old assets: they would never show as recent.
**Trade-off:** For the first week after the upgrade, Added this week holds every asset. A regrouped asset counts as new, since it is a new row.

## 2026-11-13: The page's scripts are JavaScript modules
**Decision:** `app.js` loads `details.js`, `sheet.js` and `ui.js` with `import`. `open_window` registers `.js` as `text/javascript` in Python's `mimetypes` before pywebview starts its server.
**Why:** One script had grown past the 400 lines the checks allow. Modules name what each file uses, so a reader can follow a function to its file. Windows can map `.js` to `text/plain` in the registry, Python reads that map, and a browser refuses to run a module sent as plain text (Django ticket #32041 describes the same failure).
**Alternatives:** Plain scripts sharing global names: no registry risk, but the lint check reports every name from another file as undefined, and nothing says where a name comes from.
**Trade-off:** The page no longer works opened as a file (`file://`); it needs a server, which pywebview always starts.

## 2026-11-14: The page resizes the frameless window
**Decision:** Handles on the page's edges measure a drag and call `Api.resize`, which calls pywebview's `window.resize` with the opposite sides fixed. The window stays frameless.
**Why:** pywebview's maintainer: "Frameless windows are not resizable" ([discussion #1591](https://github.com/r0x0r/pywebview/discussions/1591)). On Windows pywebview sets `FormBorderStyle.None`, which removes the resize border with the title bar. Sandro chose the frameless window (2026-11-12).
**Alternatives:** Windows' own hit-testing (`WM_NCHITTEST`) through ctypes: snapping and the native feel, but Windows-only code against pywebview's internals, and WebView2 covers the whole window, so the border would need a gap. The system title bar: undoes Sandro's choice.
**Trade-off:** One Python call per step of a drag, so resizing may lag behind the pointer. Dragging an edge does not snap the window.

## 2026-11-14: Windows runs window drags itself
**Decision:** On Windows, pressing the title bar or a resize handle calls `Api.begin_drag`, which sends the window `WM_NCLBUTTONDOWN` with the caption or border hit-test code, after `ReleaseCapture`. Elsewhere the page keeps moving and resizing the window step by step. Sandro chose this on a card (2026-11-14). It replaces the page-run drag on Windows from the entry before.
**Why:** With animations off in Windows, Capsa's window still moved and resized with live contents: pywebview's drag region and the resize handles move the window one step per mouse move, and Windows never sees a drag. Sent the border message, Windows runs the drag with the user's settings and Snap. Tauri's WebView2 layer (wry) starts drags the same way.
**Alternatives:** Keep the page-run drag: no Windows-only code, but Windows' settings and Snap do not apply. Answer `WM_NCHITTEST` in the window procedure: Windows would find the borders itself, but WebView2 covers the whole window and receives the mouse first.
**Trade-off:** Windows-only code that reaches pywebview's Windows Forms window (`window.native`) and needs .NET's `Func` through pythonnet. Microsoft documents the border codes for "a resizable window"; whether Windows resizes a borderless window this way is untested until it runs on Sandro's machine.

## 2026-11-14: A lone .exr is an HDRI only at exactly 2:1
**Decision:** Grouping reads the width and height of a lone `.exr` from its header (`thumbnails.image_size`) and calls it an HDRI only when the width is exactly twice the height; otherwise a texture. An unreadable header keeps the old rule, HDRI. `.hdr` files stay HDRIs by their ending. A rescan now also rewrites an asset whose kind or cover changed while its files did not (#29).
**Why:** A render saved as `.exr` was labelled an HDRI. The equirectangular layout HDRIs use is 2:1 by definition, and the header takes about 0.01 s on Sandro's machine (#11). The scanner must not open files, so the test lives in grouping.
**Alternatives:** A tolerance of a pixel or two: no known HDRI needs it. Reading the header in a step after grouping: a second pass over the assets for the same answer.
**Trade-off:** Grouping now reads files, so its tests make real `.exr` files. A cropped or non-equirectangular panorama shows as a texture.

