"""
Download Fashion-MNIST (open-source fashion image dataset) and emit PNGs + ground_truth.json.

Run from repo root: python eval/prepare_test_set.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

_EVAL_ROOT = Path(__file__).resolve().parent
if str(_EVAL_ROOT) not in sys.path:
    sys.path.insert(0, str(_EVAL_ROOT))

from fashion_mnist_io import image_at, load_test_set  # noqa: E402

ROWS = 28
COLS = 28

# Canonical garment_type strings we use as ground truth (Fashion-MNIST class names).
CLASS_GARMENT = [
    "t-shirt or top",
    "trouser",
    "pullover",
    "dress",
    "coat",
    "sandal",
    "shirt",
    "sneaker",
    "bag",
    "ankle boot",
]


def main() -> None:
    root = Path(__file__).resolve().parent
    cache = root / ".cache" / "fashion-mnist"
    out_dir = root / "test_images"
    out_dir.mkdir(parents=True, exist_ok=True)

    data, labels = load_test_set(cache)
    n = 50
    records = []
    for i in range(n):
        raw = bytearray(image_at(data, ROWS, COLS, i))
        img = Image.frombytes("L", (COLS, ROWS), bytes(raw))
        up = img.resize((256, 256), Image.Resampling.NEAREST)
        fname = f"fmnist_{i:03d}.png"
        up.save(out_dir / fname, format="PNG")
        cid = labels[i]
        records.append(
            {
                "file": fname,
                "class_id": cid,
                "expected": {
                    "garment_type": CLASS_GARMENT[cid],
                    "style": None,
                    "material": None,
                    "occasion": None,
                    "continent": None,
                    "country": None,
                    "city": None,
                },
            }
        )

    (root / "ground_truth.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"Wrote {n} images to {out_dir} and ground_truth.json")


if __name__ == "__main__":
    main()
