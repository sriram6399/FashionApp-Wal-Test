"""
Evaluate multimodal classifier against eval/ground_truth.json (Fashion-MNIST-derived test set).

Usage (repo root):
  pip install -r app/backend/requirements.txt pillow
  python eval/prepare_test_set.py   # once: downloads FMNIST, writes test_images + ground_truth.json
  python eval/evaluate.py

Uses OPENAI_API_KEY if set; otherwise mock classifier (report notes lower semantic agreement).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "app" / "backend"
sys.path.insert(0, str(BACKEND))

EVAL_DIR = Path(__file__).resolve().parent


def garment_match(expected: str, predicted: str | None) -> bool:
    if not predicted:
        return False
    e = expected.lower().strip()
    p = predicted.lower().strip()
    if e in p or p in e:
        return True
    for token in e.replace("/", " ").replace(",", " ").split():
        t = token.strip()
        if len(t) > 2 and t in p:
            return True
    return False


def scalar_match(expected: str | None, predicted: str | None) -> bool | None:
    if expected is None:
        return None
    if not predicted:
        return False
    return expected.strip().lower() == predicted.strip().lower()


async def classify_path(path: Path):
    from fashion_backend.classifier import classify_image_bytes

    data = path.read_bytes()
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return await classify_image_bytes(data, mime=mime)


async def main_async() -> None:
    gt_path = EVAL_DIR / "ground_truth.json"
    img_dir = EVAL_DIR / "test_images"
    if not gt_path.is_file():
        print("Missing ground_truth.json — run: python eval/prepare_test_set.py")
        sys.exit(1)
    records = json.loads(gt_path.read_text(encoding="utf-8"))
    stats: dict[str, dict[str, float]] = {}

    for rec in records:
        fname = rec["file"]
        path = img_dir / fname
        if not path.is_file():
            print(f"Skip missing image: {path}")
            continue
        result = await classify_path(path)
        exp = rec.get("expected") or {}
        s = result.structured

        pairs = [
            ("garment_type", exp.get("garment_type"), s.garment_type, garment_match),
            ("style", exp.get("style"), s.style, scalar_match),
            ("material", exp.get("material"), s.material, scalar_match),
            ("occasion", exp.get("occasion"), s.occasion, scalar_match),
            ("continent", exp.get("continent"), s.location_context.continent if s.location_context else None, scalar_match),
            ("country", exp.get("country"), s.location_context.country if s.location_context else None, scalar_match),
            ("city", exp.get("city"), s.location_context.city if s.location_context else None, scalar_match),
        ]
        for key, ev, pred, fn in pairs:
            if key not in stats:
                stats[key] = {"correct": 0, "total": 0}
            if fn is garment_match:
                ok = garment_match(str(ev), pred) if ev else None
            else:
                ok = scalar_match(ev, pred)  # type: ignore[arg-type]
            if ok is None:
                continue
            stats[key]["total"] += 1
            if ok:
                stats[key]["correct"] += 1

    use_openai = bool(os.environ.get("OPENAI_API_KEY"))
    print("Classifier:", "OpenAI" if use_openai else "mock (deterministic hash)")
    print("Per-attribute accuracy (skipped if label is null in ground truth):\n")
    for key in sorted(stats.keys()):
        t = stats[key]["total"]
        c = stats[key]["correct"]
        acc = (c / t) if t else 0.0
        print(f"  {key:16} {acc:.1%}  ({c}/{t})")

    print(
        "\nNotes: Fashion-MNIST silhouettes are low-detail; multimodal models may confuse "
        "similar classes (e.g. shirt vs t-shirt). Mock classifier ignores image semantics. "
        "For real-world photos, curate Pexels or street-style images and extend ground_truth.json."
    )


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
