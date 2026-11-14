"""Make a small preview image of an image file, and read an image's size.

Reads the source file and writes only into the cache folder it is given.
"""

import hashlib
import logging
import os
from pathlib import Path

import OpenImageIO as oiio

SIZE = 512  # longest side in pixels; a catalogue tile on a 4k screen is smaller
LINEAR_SUFFIXES = {".exr", ".hdr"}  # stored as light values, not as screen colours

log = logging.getLogger(__name__)


def thumbnail_path(source: Path, cache: Path) -> Path:
    """Where the thumbnail of `source` lives. A changed file gets a new name."""
    stat = source.stat()
    key = f"{source}|{stat.st_size}|{stat.st_mtime_ns}"
    return cache / f"{hashlib.sha256(key.encode()).hexdigest()[:32]}.jpg"


def make_thumbnail(source: Path, cache: Path) -> Path | None:
    """Return the thumbnail of `source`, making it first if the cache lacks it.

    Returns None when the file is not an image OpenImageIO can read.
    """
    target = thumbnail_path(source, cache)
    if target.exists():
        return target

    image = oiio.ImageBuf(str(source))
    if image.has_error:
        log.warning("No thumbnail for %s: %s", source, image.geterror())
        return None

    spec = image.spec()
    # One channel is a grey map: repeat it. Otherwise the first three are the colour.
    order = (0, 1, 2) if spec.nchannels >= 3 else (0, 0, 0)
    small = oiio.ImageBufAlgo.channels(image, order)

    scale = min(1.0, SIZE / max(spec.width, spec.height))
    width = max(1, round(spec.width * scale))
    height = max(1, round(spec.height * scale))
    if scale < 1.0:
        small = oiio.ImageBufAlgo.resize(small, roi=oiio.ROI(0, width, 0, height))
    if source.suffix.lower() in LINEAR_SUFFIXES:
        small = oiio.ImageBufAlgo.colorconvert(small, "linear", "sRGB")

    # Write under another name first: a crash must not leave half a file that
    # the next call would take for a finished thumbnail.
    cache.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(".part.jpg")
    if small.has_error or not small.write(str(part), "uint8"):
        log.warning("No thumbnail for %s: %s", source, small.geterror())
        part.unlink(missing_ok=True)
        return None
    os.replace(part, target)
    return target


def image_size(source: Path) -> tuple[int, int] | None:
    """Width and height in pixels, from the file's header alone.

    Returns None when OpenImageIO cannot read the file.
    """
    image = oiio.ImageInput.open(str(source))
    if image is None:
        log.warning("No size for %s: %s", source, oiio.geterror())
        return None
    spec = image.spec()
    image.close()
    return spec.width, spec.height
