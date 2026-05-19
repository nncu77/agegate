"use client";

import { clsx } from "clsx";

export interface DecisionData {
  decision: "pass" | "reject" | "manual_check";
  reason: string;
  age_low: number;
  age_high: number;
  threshold_used: number;
  buffer_used: number;
  face_confidence: number;
  multiple_faces_detected: boolean;
  request_id: string;
}

const REASON_LABELS: Record<string, string> = {
  clearly_over_threshold: "估測年齡明確高於門檻",
  clearly_under_threshold: "估測年齡明確低於門檻",
  range_straddles_threshold: "估測年齡橫跨門檻,需人工確認",
  face_detection_confidence_too_low: "人臉辨識信心過低,請重新擷取或人工確認",
  no_face_detected: "未偵測到人臉",
  multiple_faces_no_target_selected: "偵測到多張人臉,請選擇目標或請顧客單獨入鏡",
};

interface Props {
  data: DecisionData;
  onOverride?: (decision: "pass" | "reject") => void;
}

export function DecisionDisplay({ data, onOverride }: Props) {
  const isManual = data.decision === "manual_check";

  return (
    <div className="space-y-4">
      <div
        className={clsx(
          "rounded-lg border-2 p-6",
          data.decision === "pass" && "border-decision-pass bg-green-50",
          data.decision === "reject" && "border-decision-reject bg-red-50",
          data.decision === "manual_check" && "border-decision-manual bg-amber-50",
        )}
      >
        <div className="flex items-center gap-3">
          <span
            className={clsx(
              "inline-block h-4 w-4 rounded-full",
              data.decision === "pass" && "bg-decision-pass",
              data.decision === "reject" && "bg-decision-reject",
              data.decision === "manual_check" && "bg-decision-manual",
            )}
            aria-hidden
          />
          <h2 className="text-xl font-semibold">
            {data.decision === "pass" && "通過"}
            {data.decision === "reject" && "拒絕"}
            {data.decision === "manual_check" && "請查驗證件"}
          </h2>
        </div>
        <p className="mt-2 text-sm text-stone-700">
          {REASON_LABELS[data.reason] ?? data.reason}
        </p>
      </div>

      <dl className="grid grid-cols-2 gap-4 rounded-lg bg-white border border-stone-200 p-4 text-sm">
        <div>
          <dt className="text-stone-500">估測年齡區間</dt>
          <dd className="font-mono">
            {data.age_low > 0
              ? `${data.age_low} – ${data.age_high} 歲`
              : "—"}
          </dd>
        </div>
        <div>
          <dt className="text-stone-500">辨識信心</dt>
          <dd className="font-mono">
            {data.face_confidence > 0
              ? `${(data.face_confidence * 100).toFixed(1)}%`
              : "—"}
          </dd>
        </div>
        <div>
          <dt className="text-stone-500">門檻年齡</dt>
          <dd className="font-mono">{data.threshold_used} 歲</dd>
        </div>
        <div>
          <dt className="text-stone-500">安全緩衝</dt>
          <dd className="font-mono">+{data.buffer_used} 歲</dd>
        </div>
      </dl>

      {isManual && onOverride && (
        <div className="rounded-lg bg-stone-50 border border-stone-200 p-4">
          <p className="text-sm font-medium text-stone-700">
            完成證件查驗後,請記錄最終結果:
          </p>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              onClick={() => onOverride("pass")}
              className="flex-1 rounded-md bg-decision-pass px-4 py-2 text-white text-sm font-medium hover:opacity-90"
            >
              證件查驗通過
            </button>
            <button
              type="button"
              onClick={() => onOverride("reject")}
              className="flex-1 rounded-md bg-decision-reject px-4 py-2 text-white text-sm font-medium hover:opacity-90"
            >
              證件查驗拒絕
            </button>
          </div>
        </div>
      )}

      <p className="text-xs text-stone-400 font-mono">
        request_id: {data.request_id}
      </p>
    </div>
  );
}
