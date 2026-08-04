# cvprep

One-liner OpenCV preprocessing, with reusable pipelines defined in a YAML
config so you can switch between presets (resize, normalize, ROI crop, edge
detection, ...) instead of re-writing the same `cv2` calls per script.

## Install

```bash
cd cvprep
pip install -e ".[dev]"
```

From GitHub (this package lives in the `cvprep/` subdirectory of the repo):

```bash
pip install "git+https://github.com/noza-kit/devtools.git#subdirectory=cvprep"
```

## Presets

Pipelines are ordered lists of ops stored in `~/.cvprep/presets.yaml`
(relocatable via the `CVPREP_HOME` env var). Each step is an op name plus its
keyword arguments:

```bash
cvprep init   # writes a starter presets.yaml with example presets
```

```yaml
presets:
  edge_prep:
    - op: grayscale
    - op: blur
      ksize: 5
    - op: canny
      threshold1: 50
      threshold2: 150

  resize_normalize:
    - op: resize
      width: 224
      height: 224
    - op: normalize
      mean: [0.485, 0.456, 0.406]
      std: [0.229, 0.224, 0.225]

  thumbnail:
    - op: resize
      scale: 0.25
```

## CLI

```bash
cvprep list                                   # preset names
cvprep show edge_prep                         # print a preset's steps

cvprep run edge_prep photo.jpg                # -> photo.cvprep.jpg
cvprep run edge_prep photo.jpg -o out.png
cvprep run resize_normalize photo.jpg -o out.npy   # keep raw float array (see note below)
cvprep run edge_prep photo.jpg --show         # also open a preview window

cvprep batch edge_prep ./images/              # -> ./images/cvprep_out/
cvprep batch edge_prep ./images/ -d ./out/ -p "*.jpg,*.png"

cvprep export edge_prep                       # print the pipeline as a standalone .py script
cvprep export edge_prep --output pipeline.py  # write it to a file instead
cvprep export edge_prep --copy                # copy it to the clipboard instead
cvprep export edge_prep -o pipeline.py --input-path photo.jpg --output-path out.jpg
```

`export` turns a preset's steps into a runnable script that calls the same
`cvprep.ops` functions in the same order, e.g. for `edge_prep`:

```python
import cv2
from cvprep import ops


def process(image):
    image = ops.grayscale(image)
    image = ops.blur(image, ksize=5)
    image = ops.canny_edge(image, threshold1=50, threshold2=150)
    return image


if __name__ == "__main__":
    image = cv2.imread('input.jpg')
    result = process(image)
    cv2.imwrite('output.jpg', result)
```

Image codecs can't store arbitrary float ranges, so when an op (like
`normalize`) produces a float array and the output path isn't `.npy`,
`cvprep` min-max rescales it to uint8 for saving — fine for a visual check,
but use a `.npy` output if you need the exact normalized values (e.g. to feed
a model).

## Library

```python
import cv2
from cvprep import Pipeline
from cvprep.ops import resize, canny_edge

image = cv2.imread("photo.jpg")

# from a preset in presets.yaml
pipeline = Pipeline.from_preset("edge_prep")
result = pipeline.run(image)

# or inline, without touching the config file
pipeline = Pipeline.from_steps([{"op": "grayscale"}, {"op": "canny", "threshold1": 50}])
result = pipeline.run(image)

# or call ops directly
result = resize(canny_edge(image), width=224, height=224)
```

## Ops reference

| Op | Key args | Notes |
| --- | --- | --- |
| `resize` | `width`, `height`, `scale` | Give one dimension to preserve aspect ratio, or `scale` for a uniform factor |
| `normalize` | `mean`, `std`, `scale` | Defaults to uint8 [0, 255] -> float32 [0, 1]; mean/std standardizes on top of that |
| `roi_crop` | `x`, `y`, `width`, `height` | Rectangular crop from the top-left corner |
| `grayscale` | — | No-op if already single-channel |
| `blur` | `ksize`, `sigma` | Gaussian blur; even `ksize` is rounded up |
| `canny` / `edge_detect` | `threshold1`, `threshold2`, `aperture_size` | Converts to grayscale first if needed |
| `threshold` | `thresh`, `maxval`, `method`, `otsu` | `method`: `binary`, `binary_inv`, `trunc`, `tozero`, `tozero_inv` |
| `rotate` | `angle`, `scale`, `center` | Degrees, counter-clockwise around the image center by default |
| `flip` | `mode` | `horizontal`, `vertical`, `both` |
| `equalize_hist` | — | Converts to grayscale first if needed |
| `denoise` | `h`, `template_window`, `search_window` | Non-local means denoising |

## Development

```bash
pip install -e ".[dev]"
pytest
```
