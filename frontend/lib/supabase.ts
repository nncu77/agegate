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

const PROJECT_URL = "https://gofhvetpebcklknqyvgp.supabase.co";
const PROJECT_ANON_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdvZmh2ZXRwZWJja2xrbnF5dmdwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkwODQ2NjcsImV4cCI6MjA5NDY2MDY2N30.HObTGLTgzrFqHzUceUHIvUHzxO1tfrQHLG1TP2EIkdA";

function resolveEnv(
  raw: string | undefined,
  fallback: string,
  minLength: number,
): string {
  const v = raw?.trim();
  if (!v || v.length < minLength) return fallback;
  return v;
}

const url = resolveEnv(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  PROJECT_URL,
  20,
);
const anonKey = resolveEnv(
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  PROJECT_ANON_KEY,
  200,
);

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
