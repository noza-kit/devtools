# batchimg

OpenCV-based batch resize / rename / trim for images and videos. Shows a
preview of what will happen and asks for confirmation before touching any
files.

## Install

```bash
cd batchimg
pip install -e ".[dev]"
```

From GitHub (this package lives in the `batchimg/` subdirectory of the repo):

```bash
pip install "git+https://github.com/noza-kit/devtools.git#subdirectory=batchimg"
```

## Usage

```bash
batchimg ./photos --resize 800x600 --rename "img_{n}"
```

```
3 file(s) will be processed -> photos/batchimg_out
  [image] a.jpg -> img_0001.jpg
  [image] b.png -> img_0002.jpg
  [video] c.mp4 -> img_0003.mp4
Proceed? [y/N]:
```

By default, originals are left untouched and results are written to
`SOURCE_DIR/batchimg_out` (mirroring subdirectories when `--recursive` is
used). Pass `--in-place` to overwrite files in `SOURCE_DIR` instead, and
`--yes`/`--dry-run` to skip or preview-only the confirmation prompt (handy
for scripting).

Images with neither `--resize` nor `--rename` given, and videos with none of
`--resize`/`--trim-start`/`--trim-end` given, are copied through unchanged
rather than re-encoded, to avoid quality loss / codec surprises.

### Resizing

```bash
batchimg ./photos --resize 800x600                  # fit within 800x600, aspect ratio kept
batchimg ./photos --resize 800x600 --no-keep-aspect  # stretch to exactly 800x600
```

### Renaming

```bash
batchimg ./photos --rename "img_{n}"                 # img_0001.jpg, img_0002.jpg, ...
batchimg ./photos --rename "{date}_{n}"               # 20260304_0001.jpg, ...
batchimg ./photos --rename "{date}_{n}" --date-format "%Y-%m-%d"
batchimg ./photos --rename "img_{n}" --start 100 --digits 3   # img_100.jpg, img_101.jpg, ...
```

Placeholders: `{n}` sequence number (zero-padded per `--digits`), `{date}`
the file's modification time formatted with `--date-format` (default
`%Y%m%d`), `{stem}` the original filename without extension, `{ext}` the
original extension. If the rendered name has no extension, the source file's
extension is appended automatically. Name collisions (e.g. two source files
rendering to the same output name) are resolved as `name (1).ext`,
`name (2).ext`, ...

### Video trimming

```bash
batchimg ./clips --trim-start 5 --trim-end 12   # keep only the 5s-12s range
batchimg ./clips --resize 640x360 --trim-end 30 # resize + trim together
```

### Other options

```bash
batchimg ./photos --pattern "*.jpg,*.png"    # only these globs (default: common image/video extensions)
batchimg ./photos --recursive                # include subdirectories, mirrored in the output
batchimg ./photos --output-dir ./resized     # custom output directory
batchimg ./photos --dry-run                  # preview only, write nothing
batchimg ./photos --yes                      # skip the confirmation prompt
```

## Supported formats

- Images: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tif`, `.tiff`, `.webp`
- Videos: `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm` (written out as `mp4v`-encoded video)

## Development

```bash
pip install -e ".[dev]"
pytest
```
