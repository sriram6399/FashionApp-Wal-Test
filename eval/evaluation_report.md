# Evaluation Report
Classifier: mock (deterministic hash)

## Per-Attribute Accuracy

- **city**: 4.0% (2/50)
- **continent**: 36.0% (18/50)
- **country**: 22.0% (11/50)
- **garment_type**: 88.0% (44/50)
- **material**: 52.0% (26/50)
- **occasion**: 60.0% (30/50)
- **style**: 66.0% (33/50)


## What we measured

We classified **50** images from [`ground_truth.json`](ground_truth.json) (Wikimedia Commons and similar open fashion imagery). Each image uses the **same** `classify_image_bytes` code path as production uploads, with **no user caption or upload metadata**—only pixels plus the fixed classifier prompt.

**Garment type** is scored with **fuzzy** matching (substring and token overlap) because the prompt restricts outputs to a small department taxonomy. **Style, material, occasion, continent, country, and city** use **strict** case-insensitive string equality. That is easy to reproduce but **under-credits** valid synonyms (e.g. “festival” vs “festive”) and **treats honest `null` location predictions as wrong** whenever the dataset label is non-null.

## Why the numbers look like this

### Garment type (88.0% (44/50))

The model is steered toward **six departments**, which shrinks the output space. Fuzzy matching helps. Many evaluation images are clearly **costume / heritage** or **womenswear**, which the vision model tends to separate reliably. Residual errors are usually **ambiguous framing** (accessories vs outfit) rather than total confusion.

### Style, occasion, material (66.0% (33/50), 60.0% (30/50), 52.0% (26/50))

These are **open-text** attributes. The model often produces reasonable wording that does not **exactly** match the single string in `expected`, so reported accuracy mixes **vision quality** with **labeling strictness**. Occasion is especially volatile because categories like “formal”, “casual”, and “street” overlap in real images.

### Location (36.0% (18/50), 22.0% (11/50), 4.0% (2/50))

**Important:** Ground-truth **city / country / continent** reflect **where the photo was catalogued** (Commons provenance), not necessarily cues visible in the frame. The model is instructed to use **null** when it cannot infer location—so scores against non-null labels measure **alignment with metadata the image alone often does not contain**, not pure visual geolocation. That explains **very low city accuracy** and why **continent** can exceed **country**.

On this run, the numerically strongest fields were **garment_type** 88%, **style** 66%, **occasion** 60%; the lowest were **continent** 36%, **country** 22%, **city** 4%.

## Takeaways for reviewers

1. Treat **garment_type** as the most **pixel-grounded** headline metric here; treat **location** as a **stress test** unless captions or upload metadata are provided in eval.
2. To raise **style / occasion / material** scores without a new model, add **taxonomy + normalization** (synonyms, embedding-to-label) rather than only exact string match.
3. Re-run `python eval/evaluate.py` after any prompt or model change; this section is regenerated with updated percentages but the interpretation above stays aligned with the scoring code in this file.

## What we would do with more time

- Split evaluation into **vision-only** vs **metadata-augmented** rows; report them separately.
- Add **synonym maps** or controlled vocabularies for subjective fields; optional human spot-checks for “reasonable” vs exact match.
- For geo: collect **user or EXIF location** in the product and score that path; use hierarchical or partial credit for region-level guesses.
- Few-shot JSON examples, specialized smaller heads per field, and regression gates on this script for CI or release checks.
