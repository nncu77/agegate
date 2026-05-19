# Test Fixtures

This directory holds binary assets used by ML smoke tests.

## Required files

### `has_face.jpg` (or `.png`)

A single, clearly-visible human face. Used by `test_pipeline_insightface.py`
to confirm that the InsightFace detector finds the face.

**Requirements:**

- Public domain or CC0 licensed (so it can be committed to a public repo)
- Single subject, frontal, well-lit
- Reasonable resolution (e.g., 256–1024 px on the longer side)
- File size < 500 KB (this repo isn't a binary store)

**Suggested sources:**

- [Wikimedia Commons — public domain portraits](https://commons.wikimedia.org/wiki/Category:Public_domain)
- Historical portraits of deceased public figures (no consent concerns)
- Synthetic faces from [thispersondoesnotexist.com](https://thispersondoesnotexist.com)
  (terms-of-use permitting; verify before relying)

After dropping the file here, re-run:

```bash
cd backend && PYTHONPATH=. .venv/Scripts/python -m pytest -m ml -v
```

The skip should disappear and the test should report 1 face detected.

## Why this isn't auto-downloaded

Tests deliberately do not fetch images at runtime — that would:
- Introduce network flakiness into the test suite
- Make CI dependent on third-party URLs staying stable
- Hide a (modest) licensing decision from the maintainer

Shipping the image as a tracked binary makes the dependency explicit
and reproducible across machines.
