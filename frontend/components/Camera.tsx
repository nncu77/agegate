"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface CameraProps {
  /** Receives either one frame (legacy) or a burst of frames (multi-frame mode). */
  onCapture: (image: string | string[]) => void;
  disabled?: boolean;
  /** Number of frames to capture per shot. 5 by default (~0.5s burst). */
  burstFrames?: number;
  /** Milliseconds between consecutive captures in the burst. 100ms default. */
  burstIntervalMs?: number;
}

/**
 * Camera component — webcam capture for the operator UI.
 *
 * Notes:
 *   - We do NOT stream video to the backend. We capture single frames
 *     on demand and send them as base64 JPEG. This keeps bandwidth low
 *     and minimizes the surface area for accidental data retention.
 *   - The video element is mirrored visually but the captured frame is
 *     NOT mirrored — the model should see the real orientation.
 *   - Stream cleanup on unmount is important; the camera light staying
 *     on after navigation is a real UX problem.
 */
export function Camera({
  onCapture,
  disabled = false,
  burstFrames = 5,
  burstIntervalMs = 100,
}: CameraProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [capturing, setCapturing] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function start() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: "user",
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
          audio: false,
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
          setReady(true);
        }
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof Error
              ? `無法存取攝影機：${e.message}`
              : "無法存取攝影機",
          );
        }
      }
    }

    start();

    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    };
  }, []);

  const captureOne = useCallback((): string | null => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !ready) return null;

    // Resize to MAX_DIM on the long edge before encoding. InsightFace
    // internally resizes detection input to 640×640 anyway, so sending
    // a 1280×720 webcam frame is pure waste of bandwidth + cold-start
    // inference time on free-tier hosts. Cuts ~5x payload size with
    // zero detection-accuracy cost.
    const MAX_DIM = 640;
    const vw = video.videoWidth;
    const vh = video.videoHeight;
    const scale = Math.min(1, MAX_DIM / Math.max(vw, vh));
    const w = Math.round(vw * scale);
    const h = Math.round(vh * scale);
    canvas.width = w;
    canvas.height = h;

    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    // Note: do NOT mirror here. We mirror for display only.
    ctx.drawImage(video, 0, 0, w, h);
    return canvas.toDataURL("image/jpeg", 0.8);
  }, [ready]);

  const capture = useCallback(async () => {
    if (!ready || capturing) return;
    setCapturing(true);
    try {
      if (burstFrames <= 1) {
        const single = captureOne();
        if (single) onCapture(single);
        return;
      }
      const frames: string[] = [];
      for (let i = 0; i < burstFrames; i++) {
        const f = captureOne();
        if (f) frames.push(f);
        if (i < burstFrames - 1) {
          await new Promise((r) => setTimeout(r, burstIntervalMs));
        }
      }
      if (frames.length > 0) onCapture(frames);
    } finally {
      setCapturing(false);
    }
  }, [burstFrames, burstIntervalMs, captureOne, capturing, onCapture, ready]);

  if (error) {
    return (
      <div className="rounded-lg border border-red-300 bg-red-50 p-6 text-red-800">
        <p className="font-medium">攝影機存取失敗</p>
        <p className="mt-1 text-sm">{error}</p>
        <p className="mt-3 text-xs">
          請確認瀏覽器已授予攝影機權限，並使用 HTTPS 或 localhost 開啟。
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="relative aspect-video overflow-hidden rounded-lg bg-stone-900">
        <video
          ref={videoRef}
          playsInline
          muted
          // Mirror for display — feels natural to the operator
          className="absolute inset-0 h-full w-full scale-x-[-1] object-cover"
        />
        {!ready && (
          <div className="absolute inset-0 flex items-center justify-center text-stone-400">
            正在啟動攝影機⋯
          </div>
        )}
      </div>
      <canvas ref={canvasRef} className="hidden" />
      <button
        type="button"
        onClick={capture}
        disabled={!ready || disabled || capturing}
        className="w-full rounded-lg bg-stone-900 px-6 py-3 text-white font-medium transition disabled:opacity-40 enabled:hover:bg-stone-800"
      >
        {capturing ? `擷取中⋯ (${burstFrames} 幀)` : "擷取並驗證"}
      </button>
    </div>
  );
}
