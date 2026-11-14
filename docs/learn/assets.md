# Assets

`src/capsa/assets.py`

## What it does

The scanner returns files. You do not think in files: `metal_053B` is one material to you, not twelve PNGs. `group(files)` takes the scanner's list and returns **assets**, the things the catalogue shows as one tile.

It is like the difference between a folder of frames and one image sequence: same files, counted the way you would count them.

## The rules

Capsa looks at one folder at a time.

**1. A folder with a texture set is one material.**
A texture set is two or more different maps side by side. Capsa recognises a map by a word in its file name: `Color`, `Roughness`, `NormalGL`, `Displacement`, `Gloss`, `Mask`, `diff`, `rough`, `nor` and so on. The full list is `MAP_WORDS` at the top of the file.

If a folder has a set, everything directly in that folder belongs to the material: the maps, the `.usdc`, the `.mtlx`, the `.rat` copies. The material is named after the folder.

**2. Numbered frames are one sequence.**
Three or more images whose names differ only in the number at the end, with no number missing, are one **image sequence**: `caustics_1001.png` to `caustics_1240.png`. It is named after the part before the number (`caustics`), or after the folder if there is none. Its path is written the way Houdini and Nuke show a sequence, `caustics_####.png`, one `#` per digit. Its cover is the first frame.

`IMG_4512.jpg`, `IMG_4519.jpg` have gaps: photos, not frames. They stay single files. So do two files, like `v1.png` and `v2.png`.

**3. Any other file is its own asset.**
An HDRI, a model, a logo. It is named after the file.

**4. A `.rat` copy joins its source.**
Houdini writes `goegap_4k.exr.rat` beside `goegap_4k.exr`. That is the same picture twice, so both are one asset. A `.rat` whose source is gone stands alone.

## The cover

Every asset can have a **cover**, the picture shown on its tile.

- Material: the picture in the folder that is not a map, such as the `Metal053B.png` preview that ambientCG ships. If there is none, the colour map.
- A texture or HDRI: the file itself.
- A model, or a lone `.rat`: none yet.

## HDRI or not: the shape

An `.exr` on its own can be an HDRI or a render. Its name does not say which, its shape does: an HDRI in the usual **equirectangular** layout is exactly twice as wide as it is high, like 4096 by 2048. `is_panorama` reads the width and height from the file's header with `image_size` (in `thumbnails.py`), which takes about 0.01 s and leaves the pixels unread. At 2:1 the file is an HDRI, at any other shape a texture.

A header OpenImageIO cannot read keeps the old rule: HDRI.

This is the one place grouping reads a file. The scanner only looks at names and sizes; grouping is where the shape decides.

## What it does not do yet

- Two texture sets in one folder become one material.
- `metalPlates_08_4K` and `metalPlates_08_2K` are two materials, not two resolutions of one.

## Try it

```sh
uv run python -c "from pathlib import Path; from collections import Counter; from capsa.scanner import scan; from capsa.assets import group; assets = group(scan(Path(r'D:\Work\Library')).files); print(len(assets), 'assets'); print(Counter(a.kind.value for a in assets))"
```
