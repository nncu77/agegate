"use client";

import { useState } from "react";
import Link from "next/link";

import { supabase } from "@/lib/supabase";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSending(true);
    try {
      const { error: err } = await supabase().auth.signInWithOtp({
        email,
        options: {
          emailRedirectTo:
            typeof window !== "undefined"
              ? `${window.location.origin}/dashboard`
              : undefined,
        },
      });
      if (err) throw err;
      setSent(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "登入失敗");
    } finally {
      setSending(false);
    }
  }

  return (
    <main className="mx-auto max-w-md px-6 py-16">
      <header className="mb-8">
        <Link href="/" className="text-sm text-stone-500 hover:underline">
          ← 返回首頁
        </Link>
        <h1 className="mt-2 text-2xl font-semibold">店家登入</h1>
        <p className="mt-1 text-sm text-stone-600">
          輸入 email,我們會寄一條登入連結給你 — 不用密碼
        </p>
      </header>

      {sent ? (
        <div className="rounded-lg border border-green-300 bg-green-50 p-6 text-sm text-green-800">
          <p className="font-medium">登入連結已寄出</p>
          <p className="mt-2">
            請到 <span className="font-mono">{email}</span> 收信,
            點信件中的連結即可完成登入。連結 1 小時內有效。
          </p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-stone-700"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="mt-1 block w-full rounded-md border border-stone-300 px-3 py-2 focus:border-stone-500 focus:outline-none"
              disabled={sending}
            />
          </div>
          {error && (
            <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800">
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={sending || !email}
            className="w-full rounded-lg bg-stone-900 px-6 py-3 text-white font-medium transition disabled:opacity-40 enabled:hover:bg-stone-800"
          >
            {sending ? "寄送中⋯" : "寄送登入連結"}
          </button>
        </form>
      )}

      <p className="mt-8 text-xs text-stone-400">
        本系統僅供註冊店家使用。第一次使用請聯絡管理員開通帳號。
      </p>
    </main>
  );
}
