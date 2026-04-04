"""
Build eval/test_images + ground_truth.json from a Hugging Face image dataset.

Default: Codatta/Fashion-1K (1000 flat-lay / ghost-mannequin color photos, ~164 MB).
This avoids Wikimedia rate limits and is simpler than wiring DeepFashion2 (multi-GB, split zips).

Install once:
  pip install -r eval/requirements-hf.txt

Run from repo root:
  python eval/prepare_hf_fashion_sample.py
  python eval/prepare_hf_fashion_sample.py --limit 100 --dataset Codatta/Fashion-1K

DeepFashion2: not bundled here — use the official repo / Kaggle; this app only needs a folder of
images + ground_truth.json for import_test_set_to_db.py.
"""

from __future__ import annotations

import argparse
import json
from itertools import islice
from pathlib import Path

from PIL import Image


def _save_record(
    idx: int,
    pil: Image.Image,
    out_dir: Path,
    *,
    source: str,
    source_id: str,
) -> dict:
    fname = f"hf_{idx:03d}.jpg"
    path = out_dir / fname
    rgb = pil.convert("RGB")
    rgb.save(path, format="JPEG", quality=92, optimize=True)
    return {
        "file": fname,
        "source": source,
        "source_id": source_id,
        "expected": {
            "garment_type": None,
            "style": None,
            "material": None,
            "occasion": None,
            "continent": None,
            "country": None,
            "city": None,
        },
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Download a sample of fashion images from Hugging Face.")
    p.add_argument("--dataset", default="Codatta/Fashion-1K", help="HF dataset id")
    p.add_argument("--split", default="train", help="Split name")
    p.add_argument("--limit", type=int, default=50, help="Number of images to write")
    p.add_argument(
        "--streaming",
        action="store_true",
        help="Stream rows (less upfront download; may be slower for first rows)",
    )
    args = p.parse_args()

    try:
        from datasets import load_dataset
    except ImportError as e:
        raise SystemExit("Install: pip install -r eval/requirements-hf.txt") from e

    root = Path(__file__).resolve().parent
    out_dir = root / "test_images"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading {args.dataset} ({args.split}), limit={args.limit}…")
    ds = load_dataset(args.dataset, split=args.split, streaming=args.streaming)

    records: list[dict] = []
    for i, row in enumerate(islice(ds, args.limit)):
        img = row.get("image")
        if img is None:
            print(f"  skip row {i}: no image column")
            continue
        if not hasattr(img, "save"):
            from datasets import Image as HFImage

            if isinstance(img, dict) and "bytes" in img:
                from io import BytesIO

                img = Image.open(BytesIO(img["bytes"]))
            elif isinstance(img, HFImage):
                img = img
            else:
                print(f"  skip row {i}: unknown image type {type(img)}")
                continue
        sid = str(row.get("id", row.get("idx", i)))
        rec = _save_record(
            len(records),
            img,
            out_dir,
            source=args.dataset,
            source_id=sid,
        )
        records.append(rec)
        print(f"  [{len(records)}/{args.limit}] {rec['file']}")

    if not records:
        raise SystemExit("No images saved — check dataset id and column names.")

    (root / "ground_truth.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"Wrote {len(records)} image(s) to {out_dir} and ground_truth.json")


if __name__ == "__main__":
    main()
