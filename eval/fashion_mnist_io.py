"""Load Fashion-MNIST test vectors without PyTorch (IDX + gzip)."""

from __future__ import annotations

import gzip
import struct
from pathlib import Path
from urllib.request import urlretrieve

BASE = "http://fashion-mnist.s3-website.eu-central-1.amazonaws.com"
FILES = {
    "images": "t10k-images-idx3-ubyte.gz",
    "labels": "t10k-labels-idx1-ubyte.gz",
}


def _ensure_downloaded(cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    for name in FILES.values():
        dest = cache_dir / name
        if not dest.is_file():
            urlretrieve(f"{BASE}/{name}", dest)


def load_test_set(cache_dir: Path) -> tuple[bytes, list[int]]:
    _ensure_downloaded(cache_dir)
    img_path = cache_dir / FILES["images"]
    lbl_path = cache_dir / FILES["labels"]
    with gzip.open(img_path, "rb") as f:
        magic, n, rows, cols = struct.unpack(">IIII", f.read(16))
        if magic != 2051:
            raise ValueError("bad image magic")
        data = f.read()
    with gzip.open(lbl_path, "rb") as f:
        magic, n = struct.unpack(">II", f.read(8))
        if magic != 2049:
            raise ValueError("bad label magic")
        labels = list(f.read())
    return data, labels


def image_at(data: bytes, rows: int, cols: int, index: int) -> bytes:
    size = rows * cols
    off = index * size
    return data[off : off + size]
