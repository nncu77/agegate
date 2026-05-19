"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth-context";
import { supabase } from "@/lib/supabase";

interface Store {
  id: string;
  name: string;
}

interface Policy {
  store_id: string;
  threshold_age: number;
  buffer_years: number;
  min_face_confidence: number;
  updated_at: string;
}

interface AuditRow {
  id: string;
  store_id: string;
  timestamp: string;
  decision: "pass" | "reject" | "manual_check";
  reason: string;
  age_low: number;
  age_high: number;
  face_confidence: number;
  threshold_used: number;
  buffer_used: number;
  operator_override: string | null;
  operator_note: string | null;
  operator_acted_at: string | null;
}

export default function Dashboard() {
  const { user, loading: authLoading, signOut } = useAuth();
  const router = useRouter();

  const [stores, setStores] = useState<Store[]>([]);
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [auditRows, setAuditRows] = useState<AuditRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingPolicy, setEditingPolicy] = useState(false);

  // Gate: not authed → push to /login
  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [authLoading, user, router]);

  // Fetch store + policy + recent audit when user is ready
  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    (async () => {
      const sb = supabase();
      try {
        const { data: storeData, error: storeErr } = await sb
          .from("stores")
          .select("id, name")
          .order("created_at", { ascending: true });
        if (storeErr) throw storeErr;
        if (cancelled) return;
        setStores(storeData ?? []);

        if (storeData && storeData.length > 0) {
          const firstId = storeData[0].id;
          const { data: pol } = await sb
            .from("policies")
            .select("*")
            .eq("store_id", firstId)
            .maybeSingle();
          if (cancelled) return;
          setPolicy(pol);

          const { data: audit, error: auditErr } = await sb
            .from("audit_logs")
            .select("*")
            .eq("store_id", firstId)
            .order("timestamp", { ascending: false })
            .limit(50);
          if (auditErr) throw auditErr;
          if (cancelled) return;
          setAuditRows(audit ?? []);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "讀取失敗");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user]);

  // 7-day decision counts
  const stats = useMemo(() => {
    const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
    const recent = auditRows.filter(
      (r) => new Date(r.timestamp).getTime() >= weekAgo,
    );
    return {
      total: recent.length,
      pass: recent.filter((r) => r.decision === "pass").length,
      reject: recent.filter((r) => r.decision === "reject").length,
      manual: recent.filter((r) => r.decision === "manual_check").length,
    };
  }, [auditRows]);

  if (authLoading || !user) {
    return (
      <main className="mx-auto max-w-5xl px-6 py-16 text-center text-stone-500">
        正在驗證身分⋯
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <header className="mb-8 flex items-start justify-between">
        <div>
          <Link href="/" className="text-sm text-stone-500 hover:underline">
            ← 返回首頁
          </Link>
          <h1 className="mt-2 text-2xl font-semibold">店家後台</h1>
          <p className="text-sm text-stone-600">{user.email}</p>
        </div>
        <button
          type="button"
          onClick={signOut}
          className="text-sm text-stone-500 hover:underline"
        >
          登出
        </button>
      </header>

      {loading && (
        <div className="rounded-lg border border-stone-200 bg-white p-8 text-center text-stone-500">
          載入中⋯
        </div>
      )}

      {error && (
        <div className="mb-6 rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}

      {!loading && stores.length === 0 && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-6 text-sm text-amber-800">
          這個帳號還沒有任何 store。請聯絡管理員建立 store 並把 owner_id 設成你的 uid。
        </div>
      )}

      {!loading && stores.length > 0 && (
        <>
          <section className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatCard label="近 7 天總筆數" value={stats.total} />
            <StatCard
              label="通過"
              value={stats.pass}
              className="text-decision-pass"
            />
            <StatCard
              label="拒絕"
              value={stats.reject}
              className="text-decision-reject"
            />
            <StatCard
              label="人工複核"
              value={stats.manual}
              className="text-decision-manual"
            />
          </section>

          <section className="mb-8 rounded-lg border border-stone-200 bg-white p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-medium">門檻設定 — {stores[0].name}</h2>
              {!editingPolicy ? (
                <button
                  type="button"
                  onClick={() => setEditingPolicy(true)}
                  className="text-sm text-stone-600 hover:underline"
                >
                  編輯
                </button>
              ) : null}
            </div>
            {policy && !editingPolicy && (
              <dl className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <dt className="text-stone-500">法定年齡</dt>
                  <dd className="mt-1 text-xl font-mono">
                    {policy.threshold_age}
                  </dd>
                </div>
                <div>
                  <dt className="text-stone-500">安全緩衝</dt>
                  <dd className="mt-1 text-xl font-mono">
                    +{policy.buffer_years}
                  </dd>
                </div>
                <div>
                  <dt className="text-stone-500">辨識信心下限</dt>
                  <dd className="mt-1 text-xl font-mono">
                    {(policy.min_face_confidence * 100).toFixed(0)}%
                  </dd>
                </div>
              </dl>
            )}
            {policy && editingPolicy && (
              <PolicyEditor
                policy={policy}
                onSaved={(p) => {
                  setPolicy(p);
                  setEditingPolicy(false);
                }}
                onCancel={() => setEditingPolicy(false)}
              />
            )}
          </section>

          <section className="rounded-lg border border-stone-200 bg-white p-6">
            <h2 className="mb-4 text-lg font-medium">最近稽核紀錄</h2>
            {auditRows.length === 0 ? (
              <p className="text-sm text-stone-500">尚無紀錄。</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="text-left text-stone-500">
                    <tr>
                      <th className="py-2 pr-4">時間</th>
                      <th className="py-2 pr-4">判定</th>
                      <th className="py-2 pr-4">區間</th>
                      <th className="py-2 pr-4">信心</th>
                      <th className="py-2 pr-4">操作員覆寫</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditRows.slice(0, 20).map((r) => (
                      <tr key={r.id} className="border-t border-stone-100">
                        <td className="py-2 pr-4 font-mono text-xs text-stone-600">
                          {new Date(r.timestamp).toLocaleString("zh-TW", {
                            hour12: false,
                          })}
                        </td>
                        <td className="py-2 pr-4">
                          <DecisionBadge decision={r.decision} />
                        </td>
                        <td className="py-2 pr-4 font-mono">
                          {r.age_low > 0
                            ? `${r.age_low}–${r.age_high}`
                            : "—"}
                        </td>
                        <td className="py-2 pr-4 font-mono">
                          {r.face_confidence > 0
                            ? `${(r.face_confidence * 100).toFixed(0)}%`
                            : "—"}
                        </td>
                        <td className="py-2 pr-4 text-stone-600">
                          {r.operator_override ?? "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}

function StatCard({
  label,
  value,
  className = "",
}: {
  label: string;
  value: number;
  className?: string;
}) {
  return (
    <div className="rounded-lg border border-stone-200 bg-white p-4">
      <div className="text-xs text-stone-500">{label}</div>
      <div className={`mt-1 text-2xl font-mono ${className}`}>{value}</div>
    </div>
  );
}

function DecisionBadge({
  decision,
}: {
  decision: "pass" | "reject" | "manual_check";
}) {
  const styles =
    decision === "pass"
      ? "bg-green-100 text-green-800"
      : decision === "reject"
        ? "bg-red-100 text-red-800"
        : "bg-amber-100 text-amber-800";
  const label =
    decision === "pass"
      ? "通過"
      : decision === "reject"
        ? "拒絕"
        : "人工複核";
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs ${styles}`}>
      {label}
    </span>
  );
}

function PolicyEditor({
  policy,
  onSaved,
  onCancel,
}: {
  policy: Policy;
  onSaved: (p: Policy) => void;
  onCancel: () => void;
}) {
  const [threshold, setThreshold] = useState(policy.threshold_age);
  const [buffer, setBuffer] = useState(policy.buffer_years);
  const [minConf, setMinConf] = useState(policy.min_face_confidence);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const { data, error: err } = await supabase()
        .from("policies")
        .upsert(
          {
            store_id: policy.store_id,
            threshold_age: threshold,
            buffer_years: buffer,
            min_face_confidence: minConf,
          },
          { onConflict: "store_id" },
        )
        .select()
        .single();
      if (err) throw err;
      onSaved(data as Policy);
    } catch (e) {
      setError(e instanceof Error ? e.message : "儲存失敗");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-4">
        <Field
          label="法定年齡 (0–100)"
          value={threshold}
          onChange={setThreshold}
          min={0}
          max={100}
        />
        <Field
          label="安全緩衝 (0–20)"
          value={buffer}
          onChange={setBuffer}
          min={0}
          max={20}
        />
        <Field
          label="辨識信心下限 (0.0–1.0)"
          value={minConf}
          onChange={setMinConf}
          step={0.05}
          min={0}
          max={1}
        />
      </div>
      {error && (
        <div className="rounded border border-red-300 bg-red-50 p-2 text-sm text-red-800">
          {error}
        </div>
      )}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={save}
          disabled={saving}
          className="rounded-md bg-stone-900 px-4 py-2 text-white text-sm disabled:opacity-40 enabled:hover:bg-stone-800"
        >
          {saving ? "儲存中⋯" : "儲存"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-stone-300 px-4 py-2 text-sm hover:bg-stone-50"
        >
          取消
        </button>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step?: number;
}) {
  return (
    <label className="block">
      <span className="text-xs text-stone-500">{label}</span>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-1 block w-full rounded-md border border-stone-300 px-2 py-1 font-mono"
      />
    </label>
  );
}
