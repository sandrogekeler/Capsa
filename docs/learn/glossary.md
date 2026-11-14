# Glossary

Every technical term used in Capsa, in plain language. Alphabetical.

**Asset:** one thing in the catalogue: a material, an HDRI, a model. It can be one file or a folder of files.

**Bridge:** pywebview's link between the page's JavaScript and Python. `window.pywebview.api.search("metal")` in JavaScript runs `Api.search("metal")` in Python and hands back the answer.

**Cache:** files Capsa made and can make again, kept so the work is done once. Deleting the cache loses nothing.

**Catalogue:** Capsa's main view: the sidebar of groups, the grid of tiles and the details of the selected asset.

**Cover:** the picture shown on an asset's tile.

**Collection:** a named set of assets you put together by hand, such as the props of one shot. An asset can be in several.

**Context manager:** an object used with `with`. It runs set-up code when the block starts and clean-up code when it ends, also after an error. `with Index(path) as index:` closes the index file.

**Command line:** a program you run by typing its name and some words in a terminal, such as `capsa scan`. No window.

**Data folder:** the folder where Capsa keeps what it writes: the index and the thumbnails. On Windows `%LOCALAPPDATA%\Capsa`.

**Data URL:** a picture written into a piece of text, `data:image/jpeg;base64,...`, so the page can show it without loading a file.

**Database:** a file built for storing rows of data and finding them again quickly. Capsa's index is one.

**Dataclass:** a small Python class that only holds values, like a row in a spreadsheet. `FileRecord` is one: path, size, date, kind.

**Dependency:** code somebody else wrote that Capsa uses, such as pytest. Like a plugin: Capsa does not work without it, and it has its own version.

**Equirectangular:** a whole panorama unrolled into a flat picture, like a world map: 360° across, 180° up and down, so twice as wide as high. The usual layout of an HDRI.

**Enum:** a fixed list of allowed values with names. `Kind` is one: USD, texture, HDRI and so on. A typo such as `Kind.TEXTRUE` fails at once, where a misspelt word in quotes would pass unnoticed.

**Frameless window:** a window without the system's title bar. Capsa draws its own, with the search box and the minimise, maximise and close buttons.

**Full-text search (FTS5):** a search that looks up words in a prepared list, like the index at the back of a book, and does not read every row.

**Hash:** a short fingerprint computed from some text. The same text always gives the same hash; a changed text gives another one.

**Library root:** a folder you point Capsa at. Everything inside it belongs to the library.

**Linear and sRGB:** two ways to store brightness. Linear stores the amount of light, which is what a renderer computes with. sRGB stores what a screen expects. Showing linear values unconverted looks too dark.

**Hit-test code:** the number Windows uses for a part of a window under the pointer: 2 for the title bar, 10 for the left border and so on. Pressing a part with a code for a border starts a resize.

**Image sequence:** one image per frame, numbered: `caustics_1001.png`, `caustics_1002.png` and so on. Written `caustics_####.png`; Houdini writes `caustics_$F4.png`.

**Lockfile (`uv.lock`):** the exact version of every dependency, written by uv. Like caching a simulation to disk: everybody who opens the project gets the same result, not whatever is newest that day.

**MIME type:** the label a server sends with a file to say what it is, such as `text/javascript` or `image/jpeg`. The browser trusts the label, not the file name.

**Module (JavaScript):** a script that takes pieces from other scripts with `import` and offers its own with `export`. Loaded with `<script type="module">`.

**Mouse capture:** a window keeping all mouse input while a button is down, even when the pointer leaves it. Only one window has it at a time.

**OpenImageIO:** the library that reads and writes image files, the one behind `oiiotool` and `iconvert`. Capsa's first dependency.

**Package:** a folder of Python code that can be imported by name. `src/capsa/` is the `capsa` package.

**pytest:** the program that runs the tests. A test is a small script that checks one behaviour and fails loudly when the behaviour changes.

**ruff:** the program that checks Python code for mistakes and formats it the same way everywhere.

**Texture set:** the maps of one material that belong together: colour, roughness, normal and so on.

**SQLite:** a database that is a single file and needs no server. It comes with Python.

**Schema version:** the number an index file carries for the shape of its tables. When the shape changes, the number goes up, and Capsa upgrades an older file when it opens it.

**Suffix:** the end of a file name that says what the file is, such as `.usd` or `.bgeo.sc`.

**Table:** one spreadsheet inside a database: named columns, one row per thing.

**Transaction:** a group of changes that are written all together or not at all.

**uv:** the tool that installs Python, creates the project's private environment (`.venv`) and runs commands inside it. `uv run pytest` means "run pytest with exactly this project's dependencies".

**Virtual environment (`.venv`):** a private copy of Python's installed packages for one project, so two projects cannot break each other. It is rebuilt from the lockfile and never committed.

**xdg-open:** the Linux command that opens a file or folder with the program the desktop chose for it.
