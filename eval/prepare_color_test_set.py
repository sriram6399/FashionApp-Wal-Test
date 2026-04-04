"""
Download ~50 color clothing/fashion photos from Wikimedia Commons for evaluation.

Uses the Commons API (no API key). Writes eval/test_images/color_XXX.<ext> and ground_truth.json.
Expected labels default to null — add manual garment_type etc. in ground_truth.json for accuracy metrics,
or use for qualitative / OpenAI runs only.

Run from repo root:
  python eval/prepare_color_test_set.py

"""

from __future__ import annotations

import json
import mimetypes
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "FashionInspirationEval/1.0 (https://github.com/; educational dataset prep)"
TARGET = 50
# Commons rate-limits rapid downloads; stay polite (see https://commons.wikimedia.org/wiki/Commons:API).
DOWNLOAD_DELAY_SEC = 2.5
API_DELAY_SEC = 1.0
HTTP_429_RETRY_SLEEP = (15, 30, 60)
CATEGORIES = [
    "Category:Dresses",
    "Category:T-shirts",
    "Category:Jeans",
    "Category:Outerwear",
    "Category:Footwear",
    "Category:Skirts",
]


def _get(params: dict) -> dict:
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        COMMONS_API + "?" + q,
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def _collect_titles(max_files: int) -> list[str]:
    titles: list[str] = []
    seen: set[str] = set()
    for cat in CATEGORIES:
        if len(titles) >= max_files:
            break
        cont: str | None = None
        while len(titles) < max_files:
            params: dict[str, str | int] = {
                "action": "query",
                "format": "json",
                "list": "categorymembers",
                "cmtitle": cat,
                "cmtype": "file",
                "cmlimit": 50,
            }
            if cont:
                params["cmcontinue"] = cont
            data = _get(params)
            q = data.get("query") or {}
            for m in q.get("categorymembers") or []:
                t = m.get("title") or ""
                if not t.startswith("File:"):
                    continue
                low = t.lower()
                if low.endswith((".svg", ".gif", ".webp")):
                    continue
                if not low.endswith((".jpg", ".jpeg", ".png")):
                    continue
                if t in seen:
                    continue
                seen.add(t)
                titles.append(t)
                if len(titles) >= max_files:
                    return titles
            cont = (data.get("continue") or {}).get("cmcontinue")
            if not cont:
                break
            time.sleep(API_DELAY_SEC)
        time.sleep(API_DELAY_SEC)
    return titles


def _image_urls(titles: list[str]) -> list[tuple[str, str]]:
    """Return list of (title, full_url)."""
    out: list[tuple[str, str]] = []
    batch = 40
    for i in range(0, len(titles), batch):
        chunk = titles[i : i + batch]
        params = {
            "action": "query",
            "format": "json",
            "prop": "imageinfo",
            "titles": "|".join(chunk),
            "iiprop": "url|mime|size",
        }
        data = _get(params)
        pages = (data.get("query") or {}).get("pages") or {}
        for _pid, page in pages.items():
            title = page.get("title") or ""
            infos = page.get("imageinfo") or []
            if not infos:
                continue
            info = infos[0]
            url = info.get("url")
            size = int(info.get("size") or 0)
            if not url or size > 18 * 1024 * 1024:
                continue
            out.append((title, url))
        time.sleep(API_DELAY_SEC)
    return out


def _download(url: str, dest: Path) -> None:
    for attempt in range(len(HTTP_429_RETRY_SLEEP) + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=120) as r:
                dest.write_bytes(r.read())
            return
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < len(HTTP_429_RETRY_SLEEP):
                time.sleep(HTTP_429_RETRY_SLEEP[attempt])
                continue
            raise


def main() -> None:
    root = Path(__file__).resolve().parent
    out_dir = root / "test_images"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Querying Wikimedia Commons for image titles…")
    # Request extra titles so we can still reach TARGET after skips / rate limits.
    titles = _collect_titles(max(TARGET * 2, 80))
    if len(titles) < TARGET:
        print(f"Warning: only found {len(titles)} image titles (wanted {TARGET}).")

    print("Resolving download URLs…")
    pairs = _image_urls(titles)
    records: list[dict] = []

    for title, url in pairs:
        if len(records) >= TARGET:
            break
        ext = Path(urllib.parse.urlparse(url).path).suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png"):
            guess, _ = mimetypes.guess_type(url)
            ext = ".jpg" if guess == "image/jpeg" else ".png" if guess == "image/png" else ".jpg"
        fname = f"color_{len(records):03d}{ext}"
        path = out_dir / fname
        try:
            print(f"  [{len(records) + 1}/{TARGET}] {fname}")
            _download(url, path)
        except (urllib.error.HTTPError, urllib.error.URLError, OSError, TimeoutError) as e:
            print(f"  skip {title}: {e}")
            time.sleep(DOWNLOAD_DELAY_SEC)
            continue
        records.append(
            {
                "file": fname,
                "source": "wikimedia_commons",
                "source_title": title,
                "source_url": url,
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
        )
        time.sleep(DOWNLOAD_DELAY_SEC)

    (root / "ground_truth.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"Wrote {len(records)} color images to {out_dir} and ground_truth.json")
    if len(records) < TARGET:
        print(f"Note: got {len(records)}/{TARGET} — re-run later or increase DOWNLOAD_DELAY_SEC if rate-limited.")
    print("Tip: set expected.garment_type (and other fields) in ground_truth.json for per-attribute accuracy.")


if __name__ == "__main__":
    main()
