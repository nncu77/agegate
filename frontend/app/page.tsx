"use client";

import Link from "next/link";

import { useAuth } from "@/lib/auth-context";

export default function Home() {
  const { user, signOut } = useAuth();

  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <header className="mb-12 flex items-start justify-between">
        <div>
          <h1 className="text-4xl font-semibold tracking-tight">AgeGate</h1>
          <p className="mt-2 text-stone-600">
            AI 輔助年齡驗證 — 為年齡管制零售場景設計的合規工具
          </p>
        </div>
        <div className="text-right text-sm">
          {user ? (
            <>
              <p className="text-stone-600">{user.email}</p>
              <button
                type="button"
                onClick={signOut}
                className="mt-1 text-stone-500 hover:underline"
              >
                登出
              </button>
            </>
          ) : (
            <Link href="/login" className="text-stone-700 hover:underline">
              店家登入
            </Link>
          )}
        </div>
      </header>

      <section className="space-y-4 text-stone-700">
        <p>
          AgeGate 透過攝影機即時擷取顧客人臉，使用本地推論 ML 模型估測年齡區間，
          並透過保守決策邏輯輔助現場人員判斷是否需要進一步查驗證件。
        </p>
        <p className="text-sm text-stone-500">
          ⚠️ AI 年齡估測為機率性輸出，存在固有誤差。本系統設計上將所有邊界情況導向人工查驗證件，
          不可作為唯一的年齡驗證依據。
        </p>
      </section>

      <nav className="mt-12 grid gap-4 sm:grid-cols-2">
        <Link
          href="/verify"
          className="rounded-lg border border-stone-300 bg-white p-6 transition hover:border-stone-500"
        >
          <div className="text-lg font-medium">操作員介面</div>
          <p className="mt-1 text-sm text-stone-600">
            開啟攝影機進行即時年齡驗證
          </p>
        </Link>
        <Link
          href="/dashboard"
          className="rounded-lg border border-stone-300 bg-white p-6 transition hover:border-stone-500"
        >
          <div className="text-lg font-medium">店家後台</div>
          <p className="mt-1 text-sm text-stone-600">
            查看稽核紀錄、調整門檻設定
          </p>
        </Link>
      </nav>
    </main>
  );
}
