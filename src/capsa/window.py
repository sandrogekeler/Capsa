# aislop-ignore-file hallucinated-import -- the pywebview package is imported as "webview"
"""Capsa's window: a frameless pywebview window showing the index as a grid.

The page in `web/` calls the methods of `Api` as `window.pywebview.api.<name>`.
No web server of our own: pywebview passes the calls between JavaScript and Python.
"""

import base64
import ctypes
import mimetypes
import subprocess
import sys
import threading
from ctypes import wintypes
from pathlib import Path

import webview
from webview.window import FixPoint

from capsa.index import Index
from capsa.library import INDEX_NAME, THUMBNAILS_NAME, refresh
from capsa.thumbnails import make_thumbnail

PAGE = Path(__file__).parent / "web" / "index.html"
MIN_SIZE = (720, 480)  # in logical pixels, as the page measures them

# What Windows' own title bar and borders send when pressed: the message, and the
# hit-test code naming the part (WinUser.h, documented under WM_NCHITTEST).
WM_NCLBUTTONDOWN = 0x00A1
VK_LBUTTON, VK_RBUTTON, SM_SWAPBUTTON = 0x01, 0x02, 23
HIT_TESTS = {"move": 2, "w": 10, "e": 11, "n": 12, "nw": 13, "ne": 14, "s": 15, "sw": 16, "se": 17}


class Api:
    def __init__(self, data: Path) -> None:
        self._data = data
        self._window: webview.Window | None = None
        self._maximized = False
        # A rescan and the page's thumbnail calls run in different threads and can
        # make the same thumbnail at once. They take turns.
        self._thumbnails = threading.Lock()

    # pywebview runs each call in its own thread, and an SQLite connection belongs
    # to the thread that opened it, so every call opens the index for itself.
    def _index(self) -> Index:
        return Index(self._data / INDEX_NAME)

    def search(self, text: str) -> list[dict]:
        with self._index() as index:
            return [
                {
                    "name": asset.name,
                    "kind": asset.kind.value,
                    "path": str(asset.path),
                    "cover": str(asset.cover) if asset.cover else None,
                    "size": asset.size_bytes,
                    "modified": asset.modified_time,
                    "missing": asset.missing,
                    "favourite": asset.favourite,
                    "tags": list(asset.tags),
                    "added": asset.added,
                    "collections": list(asset.collections),
                }
                for asset in index.search(text)
            ]

    def set_favourite(self, path: str, favourite: bool) -> None:
        with self._index() as index:
            index.set_favourite(Path(path), favourite)

    def add_tag(self, path: str, tag: str) -> list[str]:
        """Tag an asset. Returns all its tags, as the index spells them."""
        with self._index() as index:
            index.add_tag(Path(path), tag)
            return index.tags(Path(path))

    def remove_tag(self, path: str, tag: str) -> list[str]:
        with self._index() as index:
            index.remove_tag(Path(path), tag)
            return index.tags(Path(path))

    def collections(self) -> list[str]:
        with self._index() as index:
            return index.collections()

    def create_collection(self, name: str) -> str | None:
        """Make a collection. Returns why it could not be made, or None."""
        with self._index() as index:
            try:
                index.create_collection(name)
            except ValueError as error:
                return str(error)
        return None

    def delete_collection(self, name: str) -> None:
        with self._index() as index:
            index.delete_collection(name)

    def add_to_collection(self, path: str, name: str) -> None:
        with self._index() as index:
            index.add_to_collection(Path(path), name)

    def remove_from_collection(self, path: str, name: str) -> None:
        with self._index() as index:
            index.remove_from_collection(Path(path), name)

    def folders(self) -> list[dict]:
        """The library roots, each with the number of assets in it."""
        with self._index() as index:
            assets = index.search("")
            return [
                {"path": str(root), "assets": sum(a.path.is_relative_to(root) for a in assets)}
                for root in index.roots()
            ]

    def add_folder(self) -> dict | None:
        """Ask for a folder and add it as a library root. None when the dialog is cancelled."""
        chosen = self._window.create_file_dialog(webview.FileDialog.FOLDER)
        if not chosen:
            return None
        folder = Path(chosen[0]).resolve()
        with self._index() as index:
            try:
                index.add_root(folder)
            except ValueError as error:
                return {"error": str(error)}
        return {"added": str(folder)}

    def rescan(self) -> None:
        """Scan every library root, as `capsa scan` does."""
        with self._thumbnails, self._index() as index:
            refresh(index, self._data / THUMBNAILS_NAME)

    def thumbnail(self, cover: str) -> str | None:
        """The thumbnail of a cover image as a data URL the page can show."""
        with self._thumbnails:
            path = make_thumbnail(Path(cover), self._data / THUMBNAILS_NAME)
        if path is None:
            return None
        return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()

    def show_in_explorer(self, path: str) -> None:
        """Open the folder that holds `path` in the system file manager."""
        if sys.platform == "win32":
            # A string, not a list: list quoting would wrap "/select,..." in quotes,
            # and Explorer only accepts the quotes around the path.
            subprocess.Popen(f'explorer /select,"{path}"')
        else:
            subprocess.Popen(["xdg-open", str(Path(path).parent)])

    def minimize(self) -> None:
        self._window.minimize()

    def toggle_maximize(self) -> bool:
        """Maximise or restore the window. Returns whether it is now maximised."""
        if self._maximized:
            self._window.restore()
        else:
            self._window.maximize()
        self._maximized = not self._maximized
        return self._maximized

    def native_frame(self) -> bool:
        """True where Windows moves and resizes the window (`begin_drag`).

        Elsewhere the page does it: pywebview's drag region and `resize`.
        """
        return sys.platform == "win32"

    def begin_drag(self, part: str) -> None:
        """Let Windows move the window (`part` "move") or resize it from an edge ("n", "se" ...).

        The page calls this when the mouse button goes down on the title bar or an
        edge handle. Windows then runs the drag as for any window, with the user's
        settings: outline or live contents, Snap.
        """
        if self._maximized:
            return
        from System import Func, Type  # .NET, through pythonnet; pywebview loads it on Windows

        # Capsa's own copy of user32, so the argument types set here touch nobody else.
        user32 = ctypes.WinDLL("user32")
        user32.PostMessageW.argtypes = [
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        form = self._window.native  # pywebview's Windows Forms window
        hwnd = form.Handle.ToInt64()
        cursor = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(cursor))
        # The pointer's screen position packed into one number, x low and y high.
        where = ((cursor.y & 0xFFFF) << 16) | (cursor.x & 0xFFFF)

        def start() -> None:
            # A quick click can end before this call arrives. Windows would then start
            # a drag with the button already up, and the window would follow the
            # pointer until the next click. GetAsyncKeyState reads the physical
            # buttons, so a left-handed mouse presses the right one.
            button = VK_RBUTTON if user32.GetSystemMetrics(SM_SWAPBUTTON) else VK_LBUTTON
            if not user32.GetAsyncKeyState(button) & 0x8000:
                return
            # The page holds the mouse while the button is down. Windows' drag needs it.
            user32.ReleaseCapture()
            user32.PostMessageW(hwnd, WM_NCLBUTTONDOWN, HIT_TESTS[part], where)

        # Windows wants both calls from the thread that owns the window.
        form.Invoke(Func[Type](start))

    def resize(self, width: int, height: int, edge: str) -> None:
        """Give the window a new size while the page's edge handle `edge` is dragged.

        `edge` names the sides that move: "n", "se", "w" and so on. The opposite
        sides stay where they are. pywebview cannot resize a frameless window
        itself, so the page measures the drag and calls this.
        """
        if self._maximized:
            return
        # Clamped here, not left to Windows: a window held at its east side would
        # otherwise move when its width stops shrinking.
        width = max(int(width), MIN_SIZE[0])
        height = max(int(height), MIN_SIZE[1])
        fixed = FixPoint.EAST if "w" in edge else FixPoint.WEST
        fixed |= FixPoint.SOUTH if "n" in edge else FixPoint.NORTH
        self._window.resize(width, height, fixed)

    def close(self) -> None:
        self._window.destroy()


def open_window(data: Path) -> None:
    # pywebview serves the page from a small local server that names each file's
    # type from Python's mimetypes. On Windows those come from the registry, which
    # some programs set to text/plain for .js, and a browser runs a module script
    # only when it arrives as JavaScript.
    mimetypes.add_type("text/javascript", ".js")
    api = Api(data)
    api._window = webview.create_window(
        "Capsa",
        str(PAGE),
        js_api=api,
        frameless=True,
        easy_drag=False,
        width=1280,
        height=800,
        min_size=MIN_SIZE,
        background_color="#0B0B0C",
    )
    webview.start()
