import base64
import subprocess
import sys
from pathlib import Path

import numpy as np
import OpenImageIO as oiio
from webview.window import FixPoint

from capsa.index import Index
from capsa.library import INDEX_NAME, refresh
from capsa.window import MIN_SIZE, PAGE, Api


def library_with_one_image(tmp_path: Path) -> Path:
    root = tmp_path / "library"
    root.mkdir()
    image = oiio.ImageBuf(oiio.ImageSpec(8, 4, 3, "float"))
    image.set_pixels(oiio.ROI(0, 8, 0, 4), np.full((4, 8, 3), 0.5, dtype=np.float32))
    assert image.write(str(root / "sky.exr")), image.geterror()
    (root / "chair.obj").write_bytes(b"")
    return root


def api_for(tmp_path: Path) -> Api:
    data = tmp_path / "data"
    data.mkdir()
    index = Index(data / INDEX_NAME)
    index.add_root(library_with_one_image(tmp_path))
    refresh(index, data / "thumbnails")
    index.close()
    return Api(data)


def test_search_gives_the_page_plain_values(tmp_path):
    chair, sky = api_for(tmp_path).search("")
    source = tmp_path / "library" / "chair.obj"
    assert isinstance(chair.pop("added"), float)
    assert chair == {
        "name": "chair",
        "kind": "obj",
        "path": str(source),
        "cover": None,
        "size": 0,
        "modified": source.stat().st_mtime,
        "missing": False,
        "favourite": False,
        "tags": [],
        "collections": [],
    }
    assert sky["kind"] == "hdri"


def test_thumbnail_is_a_jpeg_data_url(tmp_path):
    api = api_for(tmp_path)
    (sky,) = api.search("sky")
    url = api.thumbnail(sky["cover"])
    prefix = "data:image/jpeg;base64,"
    assert url.startswith(prefix)
    assert base64.b64decode(url[len(prefix) :])[:2] == b"\xff\xd8"


def test_unreadable_cover_gives_no_thumbnail(tmp_path):
    junk = tmp_path / "junk.rat"
    junk.write_bytes(b"junk")
    assert api_for(tmp_path).thumbnail(str(junk)) is None


def test_page_files_ship_with_the_package():
    for name in (
        "index.html",
        "style.css",
        "app.js",
        "details.js",
        "resize.js",
        "sheet.js",
        "ui.js",
    ):
        assert (PAGE.parent / name).is_file()


def test_explorer_on_windows_selects_the_file(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(subprocess, "Popen", calls.append)
    Api(tmp_path).show_in_explorer(r"D:\Work\Library\my sky.exr")
    # Quotes around the path only: Explorer ignores a quoted "/select,...".
    assert calls == [r'explorer /select,"D:\Work\Library\my sky.exr"']


def test_explorer_on_linux_opens_the_folder(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(subprocess, "Popen", calls.append)
    Api(tmp_path).show_in_explorer(str(tmp_path / "sky.exr"))
    assert calls == [["xdg-open", str(tmp_path)]]


class FolderDialog:
    """Stands in for the pywebview window: its folder dialog answers `chosen`."""

    def __init__(self, chosen: Path | None) -> None:
        self.chosen = chosen

    def create_file_dialog(self, dialog_type):
        return (str(self.chosen),) if self.chosen else None


def test_folders_count_the_assets_of_each_root(tmp_path):
    assert api_for(tmp_path).folders() == [{"path": str(tmp_path / "library"), "assets": 2}]


def test_added_folder_is_found_by_rescan(tmp_path):
    api = api_for(tmp_path)
    second = tmp_path / "second"
    second.mkdir()
    (second / "table.fbx").write_bytes(b"")
    api._window = FolderDialog(second)
    assert api.add_folder() == {"added": str(second)}
    api.rescan()
    assert [a["name"] for a in api.search("")] == ["chair", "sky", "table"]


def test_cancelled_dialog_adds_nothing(tmp_path):
    api = api_for(tmp_path)
    api._window = FolderDialog(None)
    assert api.add_folder() is None
    assert len(api.folders()) == 1


def test_folder_holding_the_index_is_refused(tmp_path):
    api = api_for(tmp_path)
    api._window = FolderDialog(tmp_path)
    assert "lies inside" in api.add_folder()["error"]


def test_tags_come_back_as_the_index_spells_them(tmp_path):
    api = api_for(tmp_path)
    chair = str(tmp_path / "library" / "chair.obj")
    assert api.add_tag(chair, " Wood ") == ["wood"]
    assert api.add_tag(chair, "Dining  Room") == ["dining room", "wood"]
    assert api.remove_tag(chair, "wood") == ["dining room"]
    api.set_favourite(chair, True)
    (found,) = api.search("dining")
    assert found["favourite"]
    assert found["tags"] == ["dining room"]


def test_collections_through_the_bridge(tmp_path):
    api = api_for(tmp_path)
    chair = str(tmp_path / "library" / "chair.obj")
    assert api.create_collection("Props") is None
    assert "already" in api.create_collection("Props")
    api.add_to_collection(chair, "Props")
    assert api.collections() == ["Props"]
    (found,) = api.search("chair")
    assert found["collections"] == ["Props"]
    api.remove_from_collection(chair, "Props")
    api.delete_collection("Props")
    assert api.collections() == []


def test_open_window_serves_scripts_as_javascript(monkeypatch, tmp_path):
    # Windows' registry can map .js to text/plain, and the browser refuses a module sent so.
    import mimetypes

    from capsa import window

    monkeypatch.setattr(window.webview, "create_window", lambda *args, **kwargs: None)
    monkeypatch.setattr(window.webview, "start", lambda: None)
    mimetypes.add_type("text/plain", ".js")
    try:
        window.open_window(tmp_path)
        assert mimetypes.guess_type("app.js")[0] == "text/javascript"
    finally:
        mimetypes.add_type("text/javascript", ".js")


class Window:
    """Records what Api asks of pywebview's window."""

    def __init__(self) -> None:
        self.calls = []

    def resize(self, width, height, fixed):
        self.calls.append(("resize", width, height, fixed))

    def maximize(self):
        self.calls.append(("maximize",))

    def restore(self):
        self.calls.append(("restore",))


def test_resize_keeps_the_opposite_sides_in_place():
    api = Api(Path("unused"))
    api._window = Window()
    for edge in ("se", "w", "n", "nw", "ne"):
        api.resize(900, 600, edge)
    fixed = [call[3] for call in api._window.calls]
    assert fixed == [
        FixPoint.NORTH | FixPoint.WEST,
        FixPoint.NORTH | FixPoint.EAST,
        FixPoint.SOUTH | FixPoint.WEST,
        FixPoint.SOUTH | FixPoint.EAST,
        FixPoint.SOUTH | FixPoint.WEST,
    ]


def test_resize_stops_at_the_minimum_size():
    api = Api(Path("unused"))
    api._window = Window()
    api.resize(100, 2000, "sw")
    assert api._window.calls[0][1:3] == (MIN_SIZE[0], 2000)


def test_maximized_window_is_not_resized():
    api = Api(Path("unused"))
    api._window = Window()
    assert api.toggle_maximize() is True
    api.resize(900, 600, "e")
    assert api.toggle_maximize() is False
    assert api._window.calls == [("maximize",), ("restore",)]
