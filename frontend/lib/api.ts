/**
 * Thin API client. Centralises the backend URL and request shape so
 * components don't sprinkle fetch() calls everywhere.
 */
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface VerifyResult {
  request_id: string;
  decision: "pass" | "reject" | "manual_check";
  reason: string;
  age_low: number;
  age_high: number;
  threshold_used: number;
  buffer_used: number;
  face_confidence: number;
  multiple_faces_detected: boolean;
}

export async function verifyImage(
  image: string | string[],
  storeId: string,
): Promise<VerifyResult> {
  const body: Record<string, unknown> = { store_id: storeId };
  if (Array.isArray(image)) {
    body.image_base64_frames = image;
  } else {
    body.image_base64 = image;
  }
  const res = await fetch(`${API_URL}/api/v1/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Verify failed (${res.status}): ${detail}`);
  }
  return res.json();
}

export async function recordOverride(
  requestId: string,
  finalDecision: "pass" | "reject",
  note?: string,
): Promise<void> {
  const res = await fetch(`${API_URL}/api/v1/audit/override`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      request_id: requestId,
      final_decision: finalDecision,
      operator_note: note,
    }),
  });
  if (!res.ok) throw new Error(`Override failed: ${res.status}`);
}
