import sqlite3
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest

from capsa.assets import Asset, group
from capsa.index import Changes, Index
from capsa.scanner import Kind, scan


def found(root: Path) -> list[Asset]:
    return group(scan(root).files)


@pytest.fixture
def library(tmp_path: Path) -> Path:
    root = tmp_path / "library"
    metal = root / "materials" / "metal_053B"
    metal.mkdir(parents=True)
    (metal / "Metal053B.png").write_bytes(b"preview")
    (metal / "Metal053B_Color.png").write_bytes(b"12345")
    (metal / "Metal053B_Roughness.png").write_bytes(b"123")
    (root / "models").mkdir()
    (root / "models" / "chair.obj").write_bytes(b"obj")
    (root / "sky_sunset.hdr").write_bytes(b"")
    return root


@pytest.fixture
def index(tmp_path: Path, library: Path):
    index = Index(tmp_path / "index.sqlite")
    index.add_root(library)
    yield index
    index.close()


def names(index: Index, text: str) -> list[str]:
    return [asset.name for asset in index.search(text)]


def test_first_scan_adds_every_asset(index: Index, library: Path):
    assert index.update(library, found(library)) == Changes(
        added=3, changed=0, missing=0, regrouped=0
    )


def test_same_scan_twice_changes_nothing(index: Index, library: Path):
    index.update(library, found(library))
    assert index.update(library, found(library)) == Changes(0, 0, 0, 0)


def test_rescan_sees_changed_and_missing_assets(index: Index, library: Path):
    index.update(library, found(library))
    (library / "materials" / "metal_053B" / "Metal053B_Normal.png").write_bytes(b"new map")
    (library / "sky_sunset.hdr").unlink()
    assert index.update(library, found(library)) == Changes(
        added=0, changed=1, missing=1, regrouped=0
    )
    (sky,) = index.search("sunset")
    assert sky.missing
    # Already marked: a third scan does not count it again.
    assert index.update(library, found(library)) == Changes(0, 0, 0, 0)


def test_asset_that_comes_back_is_no_longer_missing(index: Index, library: Path):
    assets = found(library)
    index.update(library, assets)
    index.update(library, [])  # the drive was unplugged
    assert index.search("chair")[0].missing
    assert index.update(library, assets) == Changes(added=0, changed=3, missing=0, regrouped=0)
    assert not index.search("chair")[0].missing


def test_regrouped_asset_is_forgotten_not_missing(index: Index, library: Path):
    # One map: a lone texture. A second map turns the folder into a material.
    folder = library / "decals"
    folder.mkdir()
    (folder / "decal_Roughness.png").write_bytes(b"r")
    index.update(library, found(library))
    assert names(index, "decal") == ["decal_Roughness"]
    (folder / "decal_Gloss.png").write_bytes(b"g")
    changes = index.update(library, found(library))
    assert (changes.added, changes.missing, changes.regrouped) == (1, 0, 1)
    assert names(index, "decal") == ["decals"]


def test_search_without_words_lists_every_asset(index: Index, library: Path):
    index.update(library, found(library))
    assert names(index, "  ") == ["chair", "metal_053B", "sky_sunset"]


def test_search_matches_words_from_their_start(index: Index, library: Path):
    index.update(library, found(library))
    assert names(index, "sunset") == ["sky_sunset"]
    assert names(index, "053") == ["metal_053B"]
    assert names(index, "mat met") == ["metal_053B"]
    assert names(index, "models") == ["chair"]
    assert names(index, "table") == []


def test_search_finds_assets_not_their_files(index: Index, library: Path):
    index.update(library, found(library))
    assert names(index, "roughness") == []


def test_search_survives_search_syntax(index: Index, library: Path):
    index.update(library, found(library))
    assert names(index, 'sky" OR (') == []
    assert names(index, "sky AND") == []


def test_search_returns_the_whole_asset(index: Index, library: Path):
    index.update(library, found(library))
    (metal,) = index.search("metal")
    folder = library / "materials" / "metal_053B"
    assert metal.path == folder
    assert metal.kind == Kind.MATERIAL
    assert metal.cover == folder / "Metal053B.png"
    assert metal.size_bytes == len(b"preview") + 5 + 3
    assert metal.modified_time == max(file.stat().st_mtime for file in folder.iterdir())
    assert not metal.missing
    (chair,) = index.search("chair")
    assert chair.cover is None


def test_index_survives_closing(tmp_path: Path, library: Path):
    path = tmp_path / "index.sqlite"
    first = Index(path)
    first.add_root(library)
    first.update(library, found(library))
    first.close()
    second = Index(path)
    assert second.roots() == [library]
    assert names(second, "sunset") == ["sky_sunset"]
    second.close()


def test_index_inside_a_root_is_refused(library: Path):
    index = Index(library / "index.sqlite")
    with pytest.raises(ValueError, match="inside the library root"):
        index.add_root(library)
    index.close()
    (library / "index.sqlite").unlink()


def test_index_of_another_version_is_refused(tmp_path: Path):
    path = tmp_path / "index.sqlite"
    db = sqlite3.connect(path)
    db.execute("PRAGMA user_version = 99")
    db.close()
    with pytest.raises(RuntimeError, match="version 99"):
        Index(path)


def test_favourite_and_tags_show_in_search(index: Index, library: Path):
    index.update(library, found(library))
    chair = library / "models" / "chair.obj"
    index.set_favourite(chair, True)
    index.add_tag(chair, "  Dining   Room ")
    index.add_tag(chair, "wood")
    (found_chair,) = index.search("chair")
    assert found_chair.favourite
    assert found_chair.tags == ("dining room", "wood")
    index.set_favourite(chair, False)
    index.remove_tag(chair, "wood")
    (found_chair,) = index.search("chair")
    assert not found_chair.favourite
    assert found_chair.tags == ("dining room",)


def test_search_finds_tags(index: Index, library: Path):
    index.update(library, found(library))
    index.add_tag(library / "sky_sunset.hdr", "exterior")
    assert names(index, "exter") == ["sky_sunset"]
    index.remove_tag(library / "sky_sunset.hdr", "exterior")
    assert names(index, "exter") == []


def test_marks_outlive_a_regrouped_asset(index: Index, library: Path):
    # Two frames are two textures; a third makes them one sequence and the
    # textures are forgotten. Removing it brings them back with their marks.
    frames = library / "frames"
    frames.mkdir()
    for number in (1, 2):
        (frames / f"dust_{number:04}.png").write_bytes(b"png")
    index.update(library, found(library))
    first = frames / "dust_0001.png"
    index.set_favourite(first, True)
    index.add_tag(first, "dust")
    (frames / "dust_0003.png").write_bytes(b"png")
    assert index.update(library, found(library)).regrouped == 2
    (sequence,) = index.search("dust")
    assert sequence.kind == Kind.SEQUENCE
    assert sequence.tags == ()
    (frames / "dust_0003.png").unlink()
    index.update(library, found(library))
    (back,) = [asset for asset in index.search("dust") if asset.path == first]
    assert back.favourite
    assert back.tags == ("dust",)


def test_path_outside_every_root_is_refused(index: Index, tmp_path: Path):
    with pytest.raises(ValueError, match="not inside a library root"):
        index.add_tag(tmp_path / "elsewhere.png", "wood")


def test_index_of_version_2_is_upgraded(tmp_path: Path, library: Path):
    path = tmp_path / "index.sqlite"
    db = sqlite3.connect(path)
    db.executescript(VERSION_2)
    db.execute("INSERT INTO roots (path) VALUES (?)", (str(library),))
    db.execute(
        "INSERT INTO assets (root_id, path, name, kind) VALUES (1, 'models/chair.obj', 'chair', 'obj')"
    )
    db.execute("INSERT INTO files VALUES (1, 'models/chair.obj', 3, 0.0, 'obj')")
    db.execute("INSERT INTO assets_search (rowid, path) VALUES (1, 'models/chair.obj')")
    db.execute("PRAGMA user_version = 2")
    db.commit()
    db.close()
    index = Index(path)
    assert names(index, "chair") == ["chair"]
    index.add_tag(library / "models" / "chair.obj", "wood")
    assert names(index, "wood") == ["chair"]
    index.close()
    assert sqlite3.connect(path).execute("PRAGMA user_version").fetchone()[0] == 4


def test_two_openers_upgrade_an_old_index_once(tmp_path: Path):
    # The window opens the index from two threads at once (search and collections).
    path = tmp_path / "index.sqlite"
    db = sqlite3.connect(path)
    db.executescript(VERSION_2)
    db.execute("PRAGMA user_version = 2")
    db.commit()
    db.close()
    start = threading.Barrier(4)
    errors = []

    def open_index():
        start.wait()
        try:
            Index(path).close()
        except Exception as error:
            errors.append(error)

    threads = [threading.Thread(target=open_index) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
    assert sqlite3.connect(path).execute("PRAGMA user_version").fetchone()[0] == 4


def test_upgraded_assets_count_as_found_at_the_upgrade(tmp_path: Path, library: Path):
    path = tmp_path / "index.sqlite"
    db = sqlite3.connect(path)
    db.executescript(VERSION_2)
    db.execute("INSERT INTO roots (path) VALUES (?)", (str(library),))
    db.execute(
        "INSERT INTO assets (root_id, path, name, kind) VALUES (1, 'sky.hdr', 'sky', 'hdri')"
    )
    db.execute("INSERT INTO files VALUES (1, 'sky.hdr', 3, 0.0, 'hdri')")
    db.execute("PRAGMA user_version = 2")
    db.commit()
    db.close()
    before = time.time()
    index = Index(path)
    (sky,) = index.search("")
    assert before - 1 <= sky.added <= time.time() + 1
    index.close()


def test_new_asset_records_when_it_was_found(index: Index, library: Path):
    before = time.time()
    index.update(library, found(library))
    assert all(before <= asset.added <= time.time() for asset in index.search(""))


def test_collections_hold_assets(index: Index, library: Path):
    index.update(library, found(library))
    chair = library / "models" / "chair.obj"
    index.create_collection("  Kitchen  scene ")
    index.create_collection("Props")
    assert index.collections() == ["Kitchen scene", "Props"]
    index.add_to_collection(chair, "Props")
    index.add_to_collection(chair, "Kitchen scene")
    (found_chair,) = index.search("chair")
    assert found_chair.collections == ("Kitchen scene", "Props")
    index.remove_from_collection(chair, "Props")
    index.delete_collection("Kitchen scene")
    assert index.collections() == ["Props"]
    (found_chair,) = index.search("chair")
    assert found_chair.collections == ()


def test_collection_name_must_be_new_and_not_blank(index: Index):
    index.create_collection("Props")
    with pytest.raises(ValueError, match="already a collection"):
        index.create_collection("Props")
    with pytest.raises(ValueError, match="needs a name"):
        index.create_collection("   ")


# The tables of version 2, as PR #28 created them.
VERSION_2 = """
CREATE TABLE roots (id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE);
CREATE TABLE assets (
    id INTEGER PRIMARY KEY,
    root_id INTEGER NOT NULL REFERENCES roots (id),
    path TEXT NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    cover TEXT,
    missing INTEGER NOT NULL DEFAULT 0,
    UNIQUE (root_id, path)
);
CREATE TABLE files (
    asset_id INTEGER NOT NULL REFERENCES assets (id),
    path TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    modified_time REAL NOT NULL,
    kind TEXT NOT NULL
);
CREATE INDEX files_by_asset ON files (asset_id);
CREATE VIRTUAL TABLE assets_search USING fts5 (path);
"""


def test_new_kind_with_the_same_files_is_saved(index: Index, library: Path):
    # A grouping rule can change an asset's kind while its files stay as they are.
    assets = found(library)
    index.update(library, assets)
    sky = next(asset for asset in assets if asset.kind == Kind.HDRI)
    relabelled = [replace(a, kind=Kind.TEXTURE) if a is sky else a for a in assets]
    assert index.update(library, relabelled) == Changes(added=0, changed=1, missing=0, regrouped=0)
    assert {a.name: a.kind for a in index.search("")}[sky.name] == Kind.TEXTURE
