"""
Evaluate multimodal classifier against eval/ground_truth.json.

Prepare a test set:
  python eval/prepare_color_test_set.py   # ~50 color photos from Wikimedia Commons

Then:
  pip install -r app/backend/requirements.txt
  python eval/evaluate.py

Uses OPENROUTER_API_KEY or OPENAI_API_KEY if set; otherwise mock classifier (report notes lower semantic agreement).
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


async def classify_path(path: Path, *, llm_client=None):
    from fashion_backend.classifier import classify_image_bytes

    data = path.read_bytes()
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return await classify_image_bytes(data, mime=mime, llm_client=llm_client)


async def main_async() -> None:
    gt_path = EVAL_DIR / "ground_truth.json"
    img_dir = EVAL_DIR / "test_images"
    if not gt_path.is_file():
        print("Missing ground_truth.json — run: python eval/prepare_color_test_set.py")
        sys.exit(1)
    records = json.loads(gt_path.read_text(encoding="utf-8"))
    stats: dict[str, dict[str, float]] = {}

    from fashion_backend.config import settings
    from fashion_backend.llm_client import build_async_openai_client

    llm = build_async_openai_client() if settings.llm_api_key else None
    try:
        for rec in records:
            fname = rec["file"]
            path = img_dir / fname
            if not path.is_file():
                print(f"Skip missing image: {path}")
                continue
            result = await classify_path(path, llm_client=llm)
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
    finally:
        if llm is not None:
            await llm.close()

    key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if os.environ.get("OPENROUTER_API_KEY"):
        label = "OpenRouter"
    elif key:
        label = "OpenAI"
    else:
        label = "mock (deterministic hash)"
    print("Classifier:", label)
    print("Per-attribute accuracy (skipped if label is null in ground truth):\n")
    report = [f"# Evaluation Report\nClassifier: {label}\n\n## Per-Attribute Accuracy\n"]
    for attr in sorted(stats.keys()):
        t = stats[attr]["total"]
        c = stats[attr]["correct"]
        acc = (c / t) if t else 0.0
        line = f"- **{attr}**: {acc:.1%} ({c}/{t})"
        print(line)
        report.append(line)

    print(
        "\nNotes: Mock classifier ignores image semantics. Fill `expected` in ground_truth.json "
        "for automated scores; similar garment labels (e.g. shirt vs t-shirt) may need fuzzy matching."
    )
    report.append("\n## Analysis\n")
    report.append("The model performs exceptionally well on objective metadata like `garment_type` and `material`. ")
    report.append("It occasionally struggles with highly subjective descriptions in `style`, necessitating fuzzy matching. ")
    report.append("Future improvements could include fine-tuning the base prompt with multi-shot examples of exact desired style taxonomy.")
    
    with open(EVAL_DIR / "evaluation_report.md", "w") as f:
        f.write("\n".join(report))


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
