# Thumbnails

`src/capsa/thumbnails.py`

## What it does

`make_thumbnail(source, cache)` opens one image and saves a small copy of it as a JPEG in the cache folder. It returns the path of that copy. The catalogue will show the copy, not the 8k original.

It is the first part of Capsa that opens your files. It only reads them. The one folder it writes to is the cache folder it is given, which is part of Capsa's own data.

## The steps

1. Work out the thumbnail's file name (see below). If that file exists, return it and stop.
2. Open the image with OpenImageIO. If it cannot read the file, return nothing.
3. Keep the first three channels: red, green, blue. Alpha is dropped. A map with one channel, like roughness, is repeated three times and stays grey.
4. Shrink it so the longer side is 512 pixels. A smaller image keeps its size.
5. If the file is an `.exr` or `.hdr`, convert it from linear to sRGB.
6. Save it as a JPEG.

## Why `.exr` and `.hdr` need converting

An `.exr` stores light: 0.18 is a mid grey, and the sun can be 50 or 5000. A JPEG stores numbers for a screen, from 0 to 255. Copy the light values straight across and the picture comes out far too dark. It is the same kind of step as the view transform in Houdini's render view, in its plainest form: Capsa does not use your OCIO config, so colours can differ a little from Houdini.

Anything brighter than white is clipped to white. A thumbnail of a sky with a sun shows a white disc, not the detail inside it.

## The file name is the cache key

The thumbnail's name is a **hash** of three things: the source's path, its size and its date. It looks like `3f9a...c2.jpg`.

Save a new version of a texture and its size or date changes. That gives another name, the file with that name does not exist, and the thumbnail is made again. Nothing has to compare dates or remember what is out of date.

The old thumbnail stays in the cache. Nothing clears it yet.

## What gets no thumbnail

- `.rat`: OpenImageIO cannot read it. The `.exr` or `.hdr` beside it gets one.
- Models and USD files: that is phase 3.
- A broken or empty image.

For these, `make_thumbnail` returns `None` and writes one line to the log.

## The size alone

`image_size(path)` opens the file with `oiio.ImageInput`, reads the header and closes it again: width and height, no pixels. Grouping uses it to tell an HDRI from a render ([assets.md](assets.md)).

## An EXR with several parts

A Karma render can hold several images in one file: beauty, albedo and more. Capsa takes the first. In the render from your machine that is `C`, the beauty.

## Speed

On your machine an 8k HDRI takes 1.4 to 1.9 seconds and a 4k one about half a second. Almost all of that is reading the big file. The function works on one file and waits until it is done. Making hundreds without freezing the window is the job of the part that calls it, which does not exist yet.

## Try it

```sh
uv run python -c "from pathlib import Path; from capsa.thumbnails import make_thumbnail; print(make_thumbnail(Path(r'D:\Work\Library\hdri\exterior\4k\goegap_4k.exr'), Path('thumbnails')))"
```

Replace the path with one of your HDRIs. The thumbnail lands in a `thumbnails` folder where you ran the command. Open it and compare it with the HDRI in Houdini.
