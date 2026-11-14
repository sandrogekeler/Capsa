# The window

`src/capsa/window.py`, `src/capsa/web/`

## What it does

`uv run capsa` with no command opens Capsa's window, the **catalogue**. It has a title bar with the search box and three columns:

- **Sidebar:** groups of assets with their counts. Library holds All, Favourites, Models, Materials, Textures (sequences included), HDRIs and Caches. Collections holds the collections you made, Added this week (assets a scan found in the last seven days) and `+ New collection`. Needs attention holds Missing files, shown only when an asset is missing.
- **Grid:** the assets of the chosen group as tiles with thumbnail, name and kind. Above it: a slider for the tile size, a button that switches to a list (one row per asset, with its size) and back, and the sort order. Recent puts the asset a scan found last first, and among assets found together the newest file, Name sorts by name with numbers in number order (`metal_2` before `metal_10`), Size puts the largest first.
- **Details:** the selected asset: preview, name with its star, type, size, date and path, its tags, then Copy path and Show in Explorer.

The gear in the title bar opens **Settings**, a sheet from the right. It lists the library folders with their asset counts. Add folder opens the system's folder dialog, adds the folder and scans. Rescan all scans every folder, as `uv run capsa scan` does. While a scan runs, a blue line travels along the bottom of the title bar. `Esc` closes the sheet.

Typing in the search box narrows the grid and the counts. `Ctrl K` jumps to the search box. Clicking a tile selects it; the selection is the blue bar above it. The star on a tile (shown on hover) or `F` adds the asset to Favourites. `+ tag` or `T` adds a tag; clicking a tag removes it.

Right-clicking a tile opens a menu: Favourites, a tick for each collection the asset is in (click to add or remove), Copy path (`Ctrl C`) and Show in Explorer (`Ctrl E`). Right-clicking a collection in the sidebar offers Delete collection; its assets stay. A missing asset shows its name in orange.

## Two halves

The window is a small web page shown by Windows' own browser engine, WebView2, the one Edge uses. **pywebview** puts that page into a window and connects it to Python.

| Half | Files | Job |
|---|---|---|
| Python | `window.py` | Opens the window. `Api` answers the page's questions. |
| Page | `web/index.html`, `style.css` and four scripts | Draws the title bar, sidebar, grid and details. Asks `Api` for data. |

## The scripts

`index.html` loads `app.js` as a **module**: a script that names what it takes from other scripts with `import`, and what it offers with `export`.

| Script | Job |
|---|---|
| `app.js` | The sidebar, the grid, sorting, the shortcuts. Keeps the assets of the last search. |
| `details.js` | The details panel and its tags. |
| `sheet.js` | The settings sheet. After a rescan it sends a `rescanned` event, and `app.js` searches again. |
| `resize.js` | The handles on the window edges that resize it. |
| `ui.js` | Pieces the others share: buttons, icons, sizes, the toast, the right-click menu, Copy path, Show in Explorer. |

A browser runs a module only when the server says the file is JavaScript. pywebview's server asks Python's `mimetypes`, which on Windows reads the registry, and some programs set `.js` to plain text there. `open_window` tells `mimetypes` that `.js` is JavaScript before the window opens.

## The bridge

In `app.js`:

```js
const assets = await window.pywebview.api.search("metal");
```

That line runs `Api.search("metal")` in Python and waits for the answer: a list of plain values (name, kind, path, cover, size, modified, missing). pywebview turns the Python list into a JavaScript array.

These calls do not go over the network. pywebview does start a small web server on `127.0.0.1` to hand WebView2 the page files; Capsa has no server of its own. The page cannot reach anything `Api` does not offer.

`Api` has eighteen methods: `search`, `thumbnail`, `show_in_explorer`, `set_favourite`, `add_tag`, `remove_tag`, `collections`, `create_collection`, `delete_collection`, `add_to_collection`, `remove_from_collection`, `folders`, `add_folder`, `rescan`, `minimize`, `toggle_maximize`, `resize` and `close`.

pywebview runs every call in a thread of its own. A scan can take a while, and the window stays usable meanwhile: the page only waits for the answer of `rescan` to hide the scan line and fetch the assets again. Thumbnails that are still loading wait until the scan ends: both make thumbnails, and two threads writing the same file at once would clash. A lock (`threading.Lock`) lets one in at a time.

The sidebar needs no method of its own. `search("")` already gives every asset with its kind, and `app.js` sorts them into groups and counts them.

## Copy path and Show in Explorer

Copy path runs in the page: `navigator.clipboard.writeText(path)`, the browser's own clipboard call.

Show in Explorer asks Python, because a page cannot start programs. On Windows `show_in_explorer` runs `explorer /select,"<path>"`, which opens the folder with the file selected. On Linux it opens the folder with `xdg-open`. A sequence selects its first frame, since `name_####.jpg` is not a real file. The button is off for a missing asset.

## Thumbnails

The page draws the tiles first, then asks for one thumbnail after the other with `window.pywebview.api.thumbnail(cover)`. Python makes the thumbnail if the cache does not have it yet, and sends it back as a **data URL**: the JPEG written out as text. The grid appears at once and fills in.

## The title bar

The window is **frameless**: Windows draws no title bar, Capsa draws its own. Dragging the empty part of the bar moves the window. That part is a `div` with the class `pywebview-drag-region`, which pywebview watches for. It lies behind the search box and buttons, so clicking those does not move the window.

## Resizing

A frameless window has no border, and pywebview cannot resize one by itself. `resize.js` puts eight invisible handles on the page: a strip 5 px wide along each edge and a 12 px square in each corner. Each shows the matching resize cursor.

Dragging a handle measures how far the pointer moved on the screen, adds that to the window's size when the drag began, and calls `window.pywebview.api.resize(width, height, edge)`. `edge` names the sides that move, such as `"se"` or `"w"`. `Api.resize` keeps the other sides in place: dragging the left edge keeps the right edge where it is. Python stops the window at 720 by 480 px. A maximised window hides the handles and ignores the call.

A drag sends many sizes. While one call is on its way, the page keeps only the newest size and sends that next, so the window never trails behind a queue of old sizes.

## What it does not do yet

- The scan line shows that a scan runs, not how far it is.
- Sort, tile size and list or grid are forgotten when the window closes.
- The font is a placeholder: IBM Plex if installed, otherwise Segoe UI (#12).
- Maximise is tracked by the button alone: double-clicking the title bar or snapping the window does not update it.
- Resizing does not snap: dragging the top edge to the top of the screen does not stretch the window to full height.
