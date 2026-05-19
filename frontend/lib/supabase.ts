"use client";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

/**
 * Browser-side Supabase client.
 *
 * Uses the anon key, which is *designed* to be exposed in client
 * bundles — RLS policies enforce that an anon-key holder can only
 * see/write rows they own (gated by auth.uid()).
 *
 * Never ship the service_role key here.
 *
 * Project values are baked in as fallbacks because the env var path
 * has bitten us twice now — once with a stray trailing slash on
 * SUPABASE_URL, once with the anon key getting truncated to 118 chars
 * on paste into Vercel's UI. Since NEXT_PUBLIC_* values are inlined
 * into the client bundle anyway, hardcoding adds NO security exposure
 * over env vars. Env vars still win when present and well-formed,
 * which keeps multi-environment deploys possible later.
 */

// Hardcoded. Env vars caused too many issues (truncated paste on
// Vercel, trailing slash on HF Space). NEXT_PUBLIC_* values ship in
// the bundle anyway — see lib/supabase.ts header docstring.
const url = "https://gofhvetpebcklknqyvgp.supabase.co";
const anonKey =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdvZmh2ZXRwZWJja2xrbnF5dmdwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkwODQ2NjcsImV4cCI6MjA5NDY2MDY2N30.HObTGLTgzrFqHzUceUHIvUHzxO1tfrQHLG1TP2EIkdA";

let _client: SupabaseClient | null = null;

export function supabase(): SupabaseClient {
  if (_client === null) {
    _client = createClient(url, anonKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true, // needed for magic-link callbacks
      },
    });
  }
  return _client;
}
