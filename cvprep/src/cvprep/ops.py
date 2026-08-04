"""One-liner OpenCV preprocessing operations.

Every function takes an image as its first argument (a numpy array in
OpenCV's BGR/grayscale convention) and returns a new array. They're plain
functions so they can be used directly, or driven from a config-defined
pipeline via cvprep.pipeline.OPS.
"""

from __future__ import annotations

import cv2
import numpy as np


def resize(image, width=None, height=None, scale=None, interpolation=cv2.INTER_LINEAR):
    """Resize by explicit size, a uniform scale factor, or one dimension
    (the other is computed to preserve aspect ratio)."""
    if scale is not None:
        return cv2.resize(image, None, fx=scale, fy=scale, interpolation=interpolation)

    if width is None and height is None:
        raise ValueError("resize requires width, height, and/or scale")

    h, w = image.shape[:2]
    if width is None:
        width = round(w * (height / h))
    elif height is None:
        height = round(h * (width / w))

    return cv2.resize(image, (width, height), interpolation=interpolation)


def normalize(image, mean=None, std=None, scale=1.0 / 255.0, dtype="float32"):
    """Scale pixel values (default: uint8 [0, 255] -> float [0, 1]), then
    optionally standardize with a per-channel mean/std (e.g. ImageNet stats)."""
    out = image.astype(dtype) * scale
    if mean is not None:
        out = out - np.array(mean, dtype=dtype)
    if std is not None:
        out = out / np.array(std, dtype=dtype)
    return out


def roi_crop(image, x, y, width, height):
    """Crop a rectangular region of interest given its top-left corner and size."""
    return image[y : y + height, x : x + width]


def grayscale(image):
    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def blur(image, ksize=5, sigma=0.0):
    """Gaussian blur. ksize is rounded up to the nearest odd number."""
    k = ksize if ksize % 2 == 1 else ksize + 1
    return cv2.GaussianBlur(image, (k, k), sigma)


def canny_edge(image, threshold1=100, threshold2=200, aperture_size=3, l2_gradient=False):
    """Canny edge detection. Runs on a grayscale copy if given a color image."""
    src = grayscale(image) if image.ndim == 3 else image
    return cv2.Canny(
        src, threshold1, threshold2, apertureSize=aperture_size, L2gradient=l2_gradient
    )


def threshold(image, thresh=127, maxval=255, method="binary", otsu=False):
    """Fixed or Otsu thresholding. method: binary, binary_inv, trunc, tozero, tozero_inv."""
    methods = {
        "binary": cv2.THRESH_BINARY,
        "binary_inv": cv2.THRESH_BINARY_INV,
        "trunc": cv2.THRESH_TRUNC,
        "tozero": cv2.THRESH_TOZERO,
        "tozero_inv": cv2.THRESH_TOZERO_INV,
    }
    if method not in methods:
        raise ValueError(f"Unknown threshold method: {method!r}")

    src = grayscale(image) if image.ndim == 3 else image
    flag = methods[method] | (cv2.THRESH_OTSU if otsu else 0)
    _, out = cv2.threshold(src, thresh, maxval, flag)
    return out


def rotate(image, angle, scale=1.0, center=None):
    """Rotate by `angle` degrees counter-clockwise around the image center (or a given point)."""
    h, w = image.shape[:2]
    if center is None:
        center = (w / 2, h / 2)
    matrix = cv2.getRotationMatrix2D(center, angle, scale)
    return cv2.warpAffine(image, matrix, (w, h))


def flip(image, mode="horizontal"):
    codes = {"horizontal": 1, "vertical": 0, "both": -1}
    if mode not in codes:
        raise ValueError(f"Unknown flip mode: {mode!r}")
    return cv2.flip(image, codes[mode])


def equalize_hist(image):
    """Histogram equalization. Runs on a grayscale copy if given a color image."""
    src = grayscale(image) if image.ndim == 3 else image
    return cv2.equalizeHist(src)


def denoise(image, h=10, template_window=7, search_window=21):
    """Non-local means denoising."""
    if image.ndim == 3:
        return cv2.fastNlMeansDenoisingColored(
            image, None, h, h, template_window, search_window
        )
    return cv2.fastNlMeansDenoising(image, None, h, template_window, search_window)
