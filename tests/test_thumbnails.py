import os
from pathlib import Path

import numpy as np
import OpenImageIO as oiio
import pytest

from capsa.thumbnails import SIZE, image_size, make_thumbnail, thumbnail_path


def write_image(path: Path, width: int, height: int, channels: int, value: float) -> Path:
    pixels = np.full((height, width, channels), value, dtype=np.float32)
    image = oiio.ImageBuf(oiio.ImageSpec(width, height, channels, "float"))
    image.set_pixels(oiio.ROI(0, width, 0, height), pixels)
    assert image.write(str(path)), image.geterror()
    return path


def read_pixels(path: Path) -> np.ndarray:
    return oiio.ImageBuf(str(path)).get_pixels(oiio.UINT8)


@pytest.fixture
def library(tmp_path: Path) -> Path:
    folder = tmp_path / "library"
    folder.mkdir()
    return folder


@pytest.fixture
def cache(tmp_path: Path) -> Path:
    return tmp_path / "data" / "thumbnails"


def test_thumbnail_is_a_small_jpeg(library, cache):
    source = write_image(library / "wide.png", 2000, 1000, 3, 0.5)
    thumbnail = make_thumbnail(source, cache)
    assert thumbnail.parent == cache
    assert thumbnail.suffix == ".jpg"
    assert read_pixels(thumbnail).shape == (SIZE // 2, SIZE, 3)


def test_small_image_is_not_enlarged(library, cache):
    source = write_image(library / "tiny.png", 40, 20, 3, 0.5)
    assert read_pixels(make_thumbnail(source, cache)).shape == (20, 40, 3)


def test_png_colours_are_kept(library, cache):
    source = write_image(library / "grey.png", 64, 64, 3, 0.5)
    assert abs(int(read_pixels(make_thumbnail(source, cache))[32, 32, 0]) - 128) <= 2


def test_exr_is_converted_for_the_screen(library, cache):
    # 0.18 is mid grey as light; on a screen that is about 118 of 255, not 46.
    source = write_image(library / "sky.exr", 64, 32, 3, 0.18)
    assert abs(int(read_pixels(make_thumbnail(source, cache))[16, 32, 0]) - 118) <= 3


def test_hdr_brighter_than_white_is_clipped(library, cache):
    source = write_image(library / "sun.hdr", 64, 32, 3, 50.0)
    assert read_pixels(make_thumbnail(source, cache))[16, 32, 0] == 255


def test_grey_map_becomes_grey_rgb(library, cache):
    source = write_image(library / "rough.png", 64, 64, 1, 0.5)
    pixel = read_pixels(make_thumbnail(source, cache))[32, 32]
    assert pixel.shape == (3,)
    assert pixel[0] == pixel[1] == pixel[2]


def test_alpha_is_dropped(library, cache):
    source = write_image(library / "decal.png", 64, 64, 4, 0.5)
    assert read_pixels(make_thumbnail(source, cache)).shape == (64, 64, 3)


def test_first_part_of_multipart_exr_is_used(library, cache):
    source = library / "render.exr"
    first = oiio.ImageSpec(64, 32, 3, "half")
    second = oiio.ImageSpec(64, 32, 3, "half")
    first["name"], second["name"] = "C", "albedo"
    out = oiio.ImageOutput.create(str(source))
    assert out.open(str(source), [first, second])
    out.write_image(np.full((32, 64, 3), 1.0, dtype=np.float32))
    assert out.open(str(source), second, "AppendSubimage")
    out.write_image(np.zeros((32, 64, 3), dtype=np.float32))
    out.close()
    assert read_pixels(make_thumbnail(source, cache))[16, 32, 0] == 255


def test_unreadable_file_gives_none(library, cache):
    source = library / "sky.rat"
    source.write_bytes(b"not an image")
    assert make_thumbnail(source, cache) is None
    assert not cache.exists() or list(cache.iterdir()) == []


def test_second_call_reuses_the_file(library, cache):
    source = write_image(library / "a.png", 64, 64, 3, 0.5)
    first = make_thumbnail(source, cache)
    made = first.stat().st_mtime_ns
    os.utime(first, ns=(made - 10**9, made - 10**9))
    assert make_thumbnail(source, cache) == first
    assert first.stat().st_mtime_ns == made - 10**9


def test_changed_source_gets_a_new_thumbnail(library, cache):
    source = write_image(library / "a.png", 64, 64, 3, 0.2)
    old = make_thumbnail(source, cache)
    write_image(source, 64, 64, 3, 0.8)
    stat = source.stat()
    os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns + 10**9))
    new = make_thumbnail(source, cache)
    assert new != old
    assert new == thumbnail_path(source, cache)
    assert read_pixels(new)[32, 32, 0] > read_pixels(old)[32, 32, 0]


def test_library_is_left_untouched(library, cache):
    source = write_image(library / "a.exr", 64, 64, 3, 0.5)
    (library / "b.rat").write_bytes(b"junk")
    before = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in library.iterdir()}
    make_thumbnail(source, cache)
    make_thumbnail(library / "b.rat", cache)
    after = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in library.iterdir()}
    assert after == before


def test_image_size_reads_the_header(tmp_path: Path):
    assert image_size(write_image(tmp_path / "sky.exr", 16, 8, 3, 0.5)) == (16, 8)


def test_image_size_of_junk_is_none(tmp_path: Path):
    junk = tmp_path / "junk.exr"
    junk.write_bytes(b"junk")
    assert image_size(junk) is None
