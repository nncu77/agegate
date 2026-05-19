"use client";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

/**
 * Browser-side Supabase client.
 *
 * Uses the anon key, which is *designed* to be exposed in client
 * bundles — RLS policies enforce that an anonymous-key holder can
 * only see/write rows they own (gated by auth.uid()).
 *
 * Never ship the service_role key here.
 */
const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!url || !anonKey) {
  // Fail loud at import time so misconfig doesn't silently produce
  // empty dashboards or "unauthorized" mysteries at runtime.
  throw new Error(
    "Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY in frontend/.env.local",
  );
}

let _client: SupabaseClient | null = null;

export function supabase(): SupabaseClient {
  if (_client === null) {
    _client = createClient(url!, anonKey!, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true, // needed for magic-link callbacks
      },
    });
  }
  return _client;
}
