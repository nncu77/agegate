"use client";

import { useState } from "react";
import Link from "next/link";

import { Camera } from "@/components/Camera";
import { DecisionDisplay, type DecisionData } from "@/components/DecisionDisplay";
import { recordOverride, verifyImage } from "@/lib/api";

// TODO: replace with the logged-in store's ID from Supabase Auth context.
// For development we use a fixed demo store ID.
const DEMO_STORE_ID = "00000000-0000-0000-0000-000000000001";

export default function VerifyPage() {
  const [result, setResult] = useState<DecisionData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCapture(image: string | string[]) {
    setLoading(true);
    setError(null);
    try {
      const data = await verifyImage(image, DEMO_STORE_ID);
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "驗證失敗");
    } finally {
      setLoading(false);
    }
  }

  async function handleOverride(finalDecision: "pass" | "reject") {
    if (!result) return;
    try {
      await recordOverride(result.request_id, finalDecision);
      // Reset to allow next verification
      setResult(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "記錄覆寫失敗");
    }
  }

  function reset() {
    setResult(null);
    setError(null);
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-10">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <Link href="/" className="text-sm text-stone-500 hover:underline">
            ← 返回首頁
          </Link>
          <h1 className="mt-2 text-2xl font-semibold">操作員介面</h1>
          <p className="text-sm text-stone-600">
            擷取顧客人臉以執行年齡驗證
          </p>
        </div>
      </header>

      {!result && (
        <Camera onCapture={handleCapture} disabled={loading} />
      )}

      {loading && (
        <div className="mt-6 text-center text-stone-500">
          正在分析影像⋯
        </div>
      )}

      {error && (
        <div className="mt-6 rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}

      {result && (
        <div className="mt-6 space-y-4">
          <DecisionDisplay data={result} onOverride={handleOverride} />
          <button
            type="button"
            onClick={reset}
            className="w-full rounded-lg border border-stone-300 px-4 py-2 text-sm text-stone-700 hover:bg-stone-100"
          >
            重新驗證
          </button>
        </div>
      )}

      <footer className="mt-12 text-xs text-stone-400">
        本系統 AI 估測為輔助參考,不可取代法定身分證件查驗。
      </footer>
    </main>
  );
}
