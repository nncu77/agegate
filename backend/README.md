---
title: AgeGate Backend
emoji: 🛡️
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
app_port: 7860
short_description: Conservative-decision age verification backend (Portfolio)
---

# AgeGate — Backend API

FastAPI + InsightFace pipeline behind a conservative age-verification
decision policy.

> Portfolio piece. **Not for production use.** AI age estimation is
> probabilistic and cannot replace legal ID checks. See the project root
> [README](https://github.com/nncu77/agegate) for the full story.

## What this Space exposes

| Endpoint | Purpose |
|---|---|
| `GET /health` | liveness probe |
| `GET /ready`  | readiness probe (`{"ready": true}` once ML pipeline is loaded) |
| `POST /api/v1/verify` | age verification (accepts single base64 frame or burst) |
| `POST /api/v1/audit/query` | query audit log entries (RLS-aware) |
| `POST /api/v1/audit/override` | record operator's manual verdict |
| `POST /api/v1/policy` | upsert store policy |

## Architecture notes

- Detection + age estimation both run on InsightFace's `buffalo_l` pack
  (genderage head bundled — no extra model dependency).
- Multi-frame burst input is aggregated via median + std-derived sigma:
  consistent frames → tighter range, inconsistent → wider range and
  more `MANUAL_CHECK` outcomes.
- Audit writes use the Supabase service-role key (bypassing RLS); the
  frontend reads audit logs via the anon key under user-scoped RLS.

## CORS caveat on Hugging Face Spaces

HF Spaces' reverse proxy echoes the request `Origin` header back as
`Access-Control-Allow-Origin` regardless of what FastAPI sets. This
effectively makes the API world-callable. Acceptable for a portfolio
demo; not how you'd run this in production. Use Render/Fly/Railway
when CORS lockdown matters.

## Configuration

Set these in HF Space Settings -> Variables and secrets:

- `SUPABASE_URL` (Variable, public)
- `SUPABASE_SERVICE_KEY` (Secret)
- `CORS_ORIGINS` (Variable) — JSON array of allowed origins,
  e.g. `["https://agegate.vercel.app"]`. Cosmetic on HF Spaces (see above).

The `buffalo_l` model pack is baked into the Docker image at build
time (~280MB) so cold starts skip the download step.
