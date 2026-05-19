"""Supabase client factory.

Single source of truth for `Client` instantiation. Tests can monkey-patch
`get_supabase` to swap in a fake; the rest of the codebase just imports
this and never builds clients ad-hoc.
"""
from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Return a process-wide singleton Supabase client.

    Uses the SERVICE_ROLE key, so DB calls bypass RLS. This is correct
    for the backend (we're the trusted server); never expose this client
    or its key to anything client-side.
    """
    if not settings.supabase_url or not settings.supabase_service_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in backend/.env. "
            "Run with USE_FAKE_DB=true to skip live DB calls."
        )
    return create_client(settings.supabase_url, settings.supabase_service_key)
