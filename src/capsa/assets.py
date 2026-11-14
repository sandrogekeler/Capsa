"""Turn a list of files into a list of assets: what the catalogue shows as one tile."""

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from capsa.scanner import FileRecord, Kind
from capsa.thumbnails import image_size

# Words in a texture's file name that say which map it is.
COLOR_WORDS = {"color", "basecolor", "albedo", "diffuse", "diff", "col"}
MAP_WORDS = COLOR_WORDS | {
    "roughness",
    "gloss",
    "glossiness",
    "mask",
    "rough",
    "metalness",
    "metallic",
    "normal",
    "normalgl",
    "normaldx",
    "nor",
    "displacement",
    "disp",
    "height",
    "ambientocclusion",
    "ao",
    "opacity",
    "emission",
    "specular",
}

# A frame number: the last run of digits in a file name, as in "caustics_0001.png".
FRAME = re.compile(r"^(.*?)(\d+)$")
MIN_FRAMES = 3

# Houdini writes its own copy of a texture as "<file name>.rat" beside it.
COMPANION_SUFFIX = ".rat"


@dataclass(frozen=True)
class Asset:
    name: str
    kind: Kind
    path: Path  # the folder of a material, the file of anything else
    cover: Path | None  # the image to show for it, if one is on disk
    files: tuple[FileRecord, ...]


def map_word(record: FileRecord) -> str | None:
    """Which map a texture is ("roughness"), or None if its name does not say."""
    if record.kind != Kind.TEXTURE or is_companion(record):
        return None
    for word in re.split(r"[^a-z0-9]+", record.path.stem.lower()):
        if word in MAP_WORDS:
            return word
    return None


def is_companion(record: FileRecord) -> bool:
    return record.path.name.lower().endswith(COMPANION_SUFFIX)


def group(files: list[FileRecord]) -> list[Asset]:
    by_folder: dict[Path, list[FileRecord]] = defaultdict(list)
    for record in files:
        by_folder[record.path.parent].append(record)

    assets: list[Asset] = []
    for folder in sorted(by_folder):
        records = by_folder[folder]
        # Two different maps side by side make a texture set: one material.
        if len({map_word(record) for record in records} - {None}) >= 2:
            assets.append(material(folder, records))
        else:
            found, rest = sequences(folder, records)
            assets.extend(found)
            assets.extend(single_files(rest))
    return assets


def material(folder: Path, records: list[FileRecord]) -> Asset:
    images = [r for r in records if r.kind == Kind.TEXTURE and not is_companion(r)]
    # A picture that is no map is the preview the download came with.
    previews = [r for r in images if map_word(r) is None]
    colors = [r for r in images if map_word(r) in COLOR_WORDS]
    candidates = previews or colors
    cover = candidates[0].path if candidates else None
    return Asset(folder.name, Kind.MATERIAL, folder, cover, tuple(records))


def sequences(folder: Path, records: list[FileRecord]) -> tuple[list[Asset], list[FileRecord]]:
    """Image sequences in one folder, and the files that belong to none.

    A sequence is at least MIN_FRAMES images whose names differ only in a frame
    number of the same width, and whose numbers have no gap.
    """
    runs: dict[tuple[str, int, str], list[tuple[int, FileRecord]]] = defaultdict(list)
    for record in records:
        if record.kind != Kind.TEXTURE or is_companion(record):
            continue
        match = FRAME.match(record.path.stem)
        if match:
            prefix, digits = match.groups()
            key = (prefix, len(digits), record.path.suffix.lower())
            runs[key].append((int(digits), record))

    found: list[Asset] = []
    taken: set[Path] = set()
    for (prefix, width, suffix), frames in runs.items():
        numbers = sorted(number for number, _ in frames)
        if len(frames) < MIN_FRAMES or numbers[-1] - numbers[0] + 1 != len(frames):
            continue
        frames.sort(key=lambda frame: frame[0])
        first = frames[0][1].path
        # Companion .rat files of the frames join the sequence.
        names = {record.path.name for _, record in frames}
        members = [
            r
            for r in records
            if r.path.name in names
            or (is_companion(r) and r.path.name[: -len(COMPANION_SUFFIX)] in names)
        ]
        taken.update(r.path for r in members)
        name = prefix.rstrip("_.- ") or folder.name
        pattern = folder / f"{prefix}{'#' * width}{first.suffix}"
        found.append(Asset(name, Kind.SEQUENCE, pattern, first, tuple(members)))
    return found, [r for r in records if r.path not in taken]


def single_files(records: list[FileRecord]) -> list[Asset]:
    by_name = {record.path.name: record for record in records}
    companions: dict[str, list[FileRecord]] = defaultdict(list)
    for record in records:
        source = record.path.name[: -len(COMPANION_SUFFIX)]
        if is_companion(record) and source in by_name:
            companions[source].append(record)
            del by_name[record.path.name]

    assets = []
    for name, record in by_name.items():
        kind = Kind.HDRI if is_panorama(record) else record.kind
        shows_itself = kind in (Kind.TEXTURE, Kind.HDRI) and not is_companion(record)
        assets.append(
            Asset(
                record.path.stem,
                kind,
                record.path,
                record.path if shows_itself else None,
                (record, *companions[name]),
            )
        )
    return assets


def is_panorama(record: FileRecord) -> bool:
    """Whether an .exr on its own is an HDRI: twice as wide as it is high.

    An equirectangular HDRI is 2:1; a render saved as .exr usually is not. Inside
    a material an .exr is a map and never gets here. A header OpenImageIO cannot
    read keeps the old rule: an HDRI.
    """
    if record.path.suffix.lower() != ".exr":
        return False
    size = image_size(record.path)
    return size is None or size[0] == 2 * size[1]
