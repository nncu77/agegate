#!/usr/bin/env python3
"""Download public-domain test face fixtures from Wikimedia Commons.

Run once after `git clone`. Idempotent — skips files that already exist.

The downloaded fixtures are NOT committed to the repo (binary assets);
they are reproducible from this script. This keeps the repo small
while making the test setup explicit and license-traceable.

Usage:
    python scripts/download_test_fixtures.py

Output:
    backend/tests/fixtures/age_<N>_<slug>.jpg     — one per portrait
    backend/tests/fixtures/has_face.jpg           — alias of the first one
    backend/tests/fixtures/fixtures.json          — metadata + license

Each portrait below should be Public Domain (PD-US-expired, PD-old-100,
or similar). If you discover an entry whose license is not actually PD,
remove it from this script and document why in the commit message.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "backend" / "tests" / "fixtures"
FIXTURES_JSON = FIXTURES_DIR / "fixtures.json"

USER_AGENT = "AgeGate-test-fixture-downloader/1.0 (https://example.com)"

# Curated PD historical portraits with documented ages.
# `commons_file` is the canonical filename on Wikimedia Commons
# (visible at https://commons.wikimedia.org/wiki/File:<name>).
# The Wikimedia API resolves it to the actual download URL so we
# don't need to know the internal hash path.
PORTRAITS = [
    {
        "commons_file": "Einstein_1921_by_F_Schmutzer_-_restoration.jpg",
        "expected_age": 42,
        "subject": "Albert Einstein",
        "year": 1921,
        "license": "PD-old-100",
        "filename": "age_42_einstein.jpg",
    },
    {
        "commons_file": "Mark_Twain_by_AF_Bradley.jpg",
        "expected_age": 72,
        "subject": "Mark Twain",
        "year": 1907,
        "license": "PD-old-100",
        "filename": "age_72_twain.jpg",
    },
    {
        "commons_file": "Marie_Curie_c1920.jpg",
        "expected_age": 53,
        "subject": "Marie Curie",
        "year": 1920,
        "license": "PD-old-100",
        "filename": "age_53_curie.jpg",
    },
    {
        "commons_file": "N.Tesla.JPG",
        "expected_age": 37,
        "subject": "Nikola Tesla",
        "year": 1893,
        "license": "PD-US-expired",
        "filename": "age_37_tesla.jpg",
    },
    {
        "commons_file": "Abraham_Lincoln_O-77_matte_collodion_print.jpg",
        "expected_age": 56,
        "subject": "Abraham Lincoln",
        "year": 1865,
        "license": "PD-old-100",
        "filename": "age_56_lincoln.jpg",
    },
]


def resolve_url(commons_file: str) -> str:
    """Use Wikimedia API to resolve a Commons filename to a download URL."""
    api = (
        "https://commons.wikimedia.org/w/api.php?"
        + urllib.parse.urlencode(
            {
                "action": "query",
                "titles": f"File:{commons_file}",
                "prop": "imageinfo",
                "iiprop": "url|mime|size",
                "format": "json",
            }
        )
    )
    req = urllib.request.Request(api, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    for _, page in data.get("query", {}).get("pages", {}).items():
        if "imageinfo" in page and page["imageinfo"]:
            return page["imageinfo"][0]["url"]
        if "missing" in page:
            raise RuntimeError(f"Not found on Commons: File:{commons_file}")
    raise RuntimeError(f"Unexpected API response for File:{commons_file}: {data}")


def download(url: str, dest: Path) -> int:
    """Download URL to dest, return bytes written."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as f:
        shutil.copyfileobj(resp, f)
    return dest.stat().st_size


def main() -> int:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    metadata: list[dict] = []
    failed: list[str] = []

    for p in PORTRAITS:
        entry = dict(p)
        dest = FIXTURES_DIR / p["filename"]
        if dest.exists():
            print(f"  skip  {p['filename']} (exists, {dest.stat().st_size} bytes)")
        else:
            try:
                print(f"  fetch {p['commons_file']} ...")
                url = resolve_url(p["commons_file"])
                size = download(url, dest)
                print(f"  saved {p['filename']} ({size} bytes)")
                entry["source_url"] = url
            except Exception as e:
                print(f"  FAIL  {p['commons_file']}: {e}")
                failed.append(p["commons_file"])
                continue

        entry["sha256"] = hashlib.sha256(dest.read_bytes()).hexdigest()
        entry["bytes"] = dest.stat().st_size
        metadata.append(entry)

    # Alias the first downloaded portrait as the generic has_face.jpg
    has_face = FIXTURES_DIR / "has_face.jpg"
    if not has_face.exists() and metadata:
        first = FIXTURES_DIR / metadata[0]["filename"]
        if first.exists():
            shutil.copy(first, has_face)
            print(f"  alias has_face.jpg <- {first.name}")

    FIXTURES_JSON.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"\nWrote metadata: {FIXTURES_JSON}")

    if failed:
        print(f"\nFAILED to download: {failed}", file=sys.stderr)
        print(
            "Edit PORTRAITS in this script with correct Commons filenames.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
