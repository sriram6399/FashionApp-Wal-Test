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


def build_analysis_section(stats: dict[str, dict[str, int]], images_classified: int) -> str:
    """Methodology narrative with accuracies interpolated from this run."""

    def acc_row(attr: str) -> tuple[float, int, int] | None:
        v = stats.get(attr)
        if not v:
            return None
        t, c = int(v["total"]), int(v["correct"])
        if t == 0:
            return None
        return (c / t, c, t)

    def pct(attr: str) -> str:
        r = acc_row(attr)
        if r is None:
            return "N/A"
        return f"{r[0]:.1%} ({r[1]}/{r[2]})"

    rows: list[tuple[float, str, int, int]] = []
    for attr, v in stats.items():
        t = int(v["total"])
        if t == 0:
            continue
        c = int(v["correct"])
        rows.append((c / t, attr, c, t))
    rows.sort(key=lambda x: -x[0])
    if not rows:
        return (
            "## What we measured\n\n"
            "No scored attributes — ensure non-null `expected` values exist in `ground_truth.json`."
        )

    strongest = ", ".join(f"**{a}** {p:.0%}" for p, a, _, _ in rows[:3])
    weakest = ", ".join(f"**{a}** {p:.0%}" for p, a, _, _ in rows[-3:])

    return f"""## What we measured

We classified **{images_classified}** images from [`ground_truth.json`](ground_truth.json) (Wikimedia Commons and similar open fashion imagery). Each image uses the **same** `classify_image_bytes` code path as production uploads, with **no user caption or upload metadata**—only pixels plus the fixed classifier prompt.

**Garment type** is scored with **fuzzy** matching (substring and token overlap) because the prompt restricts outputs to a small department taxonomy. **Style, material, occasion, continent, country, and city** use **strict** case-insensitive string equality. That is easy to reproduce but **under-credits** valid synonyms (e.g. “festival” vs “festive”) and **treats honest `null` location predictions as wrong** whenever the dataset label is non-null.

## Why the numbers look like this

### Garment type ({pct("garment_type")})

The model is steered toward **six departments**, which shrinks the output space. Fuzzy matching helps. Many evaluation images are clearly **costume / heritage** or **womenswear**, which the vision model tends to separate reliably. Residual errors are usually **ambiguous framing** (accessories vs outfit) rather than total confusion.

### Style, occasion, material ({pct("style")}, {pct("occasion")}, {pct("material")})

These are **open-text** attributes. The model often produces reasonable wording that does not **exactly** match the single string in `expected`, so reported accuracy mixes **vision quality** with **labeling strictness**. Occasion is especially volatile because categories like “formal”, “casual”, and “street” overlap in real images.

### Location ({pct("continent")}, {pct("country")}, {pct("city")})

**Important:** Ground-truth **city / country / continent** reflect **where the photo was catalogued** (Commons provenance), not necessarily cues visible in the frame. The model is instructed to use **null** when it cannot infer location—so scores against non-null labels measure **alignment with metadata the image alone often does not contain**, not pure visual geolocation. That explains **very low city accuracy** and why **continent** can exceed **country**.

On this run, the numerically strongest fields were {strongest}; the lowest were {weakest}.

## Takeaways for reviewers

1. Treat **garment_type** as the most **pixel-grounded** headline metric here; treat **location** as a **stress test** unless captions or upload metadata are provided in eval.
2. To raise **style / occasion / material** scores without a new model, add **taxonomy + normalization** (synonyms, embedding-to-label) rather than only exact string match.
3. Re-run `python eval/evaluate.py` after any prompt or model change; this section is regenerated with updated percentages but the interpretation above stays aligned with the scoring code in this file.

## What we would do with more time

- Split evaluation into **vision-only** vs **metadata-augmented** rows; report them separately.
- Add **synonym maps** or controlled vocabularies for subjective fields; optional human spot-checks for “reasonable” vs exact match.
- For geo: collect **user or EXIF location** in the product and score that path; use hierarchical or partial credit for region-level guesses.
- Few-shot JSON examples, specialized smaller heads per field, and regression gates on this script for CI or release checks.
"""


async def main_async() -> None:
    gt_path = EVAL_DIR / "ground_truth.json"
    img_dir = EVAL_DIR / "test_images"
    if not gt_path.is_file():
        print("Missing ground_truth.json — run: python eval/prepare_color_test_set.py")
        sys.exit(1)
    records = json.loads(gt_path.read_text(encoding="utf-8"))
    stats: dict[str, dict[str, int]] = {}
    images_classified = 0

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
            images_classified += 1
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
    vision_id = settings.vision_model_resolved
    if os.environ.get("OPENROUTER_API_KEY"):
        label = f"OpenRouter — vision `{vision_id}`"
    elif key:
        label = f"OpenAI — vision `{vision_id}`"
    else:
        label = "mock (deterministic hash)"
    print("Classifier:", label)
    print("Per-attribute accuracy (skipped if label is null in ground truth):\n")
    report = [f"# Evaluation Report\nClassifier: {label}\n\n## Per-Attribute Accuracy\n"]
    for attr in sorted(stats.keys()):
        t = stats[attr]["total"]
        c = stats[attr]["correct"]
        if t == 0:
            continue
        acc = (c / t) if t else 0.0
        line = f"- **{attr}**: {acc:.1%} ({c}/{t})"
        print(line)
        report.append(line)

    print(
        "\nNotes: Mock classifier ignores image semantics. Fill `expected` in ground_truth.json "
        "for automated scores; similar garment labels (e.g. shirt vs t-shirt) may need fuzzy matching."
    )
    report.append("\n")
    report.append(build_analysis_section(stats, images_classified))

    with open(EVAL_DIR / "evaluation_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report))


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
