"use client";

import { useState, useRef, DragEvent, ChangeEvent } from "react";
import { useRouter } from "next/navigation";
import {
  createSong,
  getUploadUrl,
  uploadToR2,
  startProcessing,
  getJobStatus,
  getConfig,
} from "@/lib/api";

// ── State machine ──────────────────────────────────────────────────────────

type UploadState =
  | { phase: "idle" }
  | { phase: "validating" }
  | { phase: "creating" }
  | { phase: "uploading"; pct: number; retryPayload?: RetryPayload }
  | { phase: "upload_failed"; error: string; retryPayload: RetryPayload }
  | { phase: "processing"; progress: number }
  | { phase: "polling_error"; lastStatus: string }  // API unreachable mid-poll
  | { phase: "complete"; songId: string }
  | { phase: "failed"; error: string };

interface RetryPayload {
  songId: string;
  presignedUrl: string;
  file: File;
}

const POLL_INTERVAL_MS = 3000;
const ACCEPTED_TYPES = ["audio/mpeg", "audio/wav", "audio/flac", "audio/mp4", "audio/x-m4a"];
const ACCEPTED_EXT = ".mp3,.wav,.flac,.m4a";

// ── Component ──────────────────────────────────────────────────────────────

export default function UploadFlow() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [state, setState] = useState<UploadState>({ phase: "idle" });
  const [dragOver, setDragOver] = useState(false);
  const [title, setTitle] = useState("");

  function stopPolling() {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }

  async function startFlow(file: File) {
    // ── Validate ──────────────────────────────────────────────────────────
    setState({ phase: "validating" });

    let maxMb = 100;
    try {
      const cfg = await getConfig();
      maxMb = cfg.max_upload_size_mb;
    } catch {
      // config fetch failing is non-fatal
    }

    if (!ACCEPTED_TYPES.includes(file.type) && !file.name.match(/\.(mp3|wav|flac|m4a)$/i)) {
      setState({ phase: "failed", error: "Unsupported file type. Please upload MP3, WAV, FLAC, or M4A." });
      return;
    }
    if (file.size > maxMb * 1024 * 1024) {
      setState({ phase: "failed", error: `File is too large (max ${maxMb} MB).` });
      return;
    }

    const songTitle = title.trim() || file.name.replace(/\.[^.]+$/, "");

    try {
      // ── Step 1: Create song record ────────────────────────────────────
      setState({ phase: "creating" });
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { song_id, r2_original_key: _ } = await createSong(songTitle, file.name);

      // ── Step 2a: Get presigned URL ────────────────────────────────────
      const contentType = file.type || "audio/mpeg";
      const presignedUrl = await getUploadUrl(song_id, contentType);

      // ── Step 2b: Upload directly to R2 ───────────────────────────────
      setState({ phase: "uploading", pct: 0 });
      await doUpload(file, presignedUrl, song_id);

    } catch (err) {
      setState({ phase: "failed", error: String(err instanceof Error ? err.message : err) });
    }
  }

  async function doUpload(file: File, presignedUrl: string, songId: string) {
    try {
      await uploadToR2(presignedUrl, file, (pct) => {
        setState({ phase: "uploading", pct });
      });

      // ── Step 3: Trigger processing ─────────────────────────────────────
      const jobId = await startProcessing(songId);
      setState({ phase: "processing", progress: 0 });
      startPolling(jobId, songId);

    } catch (err) {
      // Upload failed — expose retry without re-creating the song
      setState({
        phase: "upload_failed",
        error: String(err instanceof Error ? err.message : err),
        retryPayload: { songId, presignedUrl, file },
      });
    }
  }

  function startPolling(jobId: string, songId: string) {
    stopPolling();
    let consecutiveErrors = 0;

    pollTimerRef.current = setInterval(async () => {
      try {
        const job = await getJobStatus(jobId);
        consecutiveErrors = 0;

        if (job.status === "complete") {
          stopPolling();
          setState({ phase: "complete", songId });
        } else if (job.status === "failed") {
          stopPolling();
          setState({
            phase: "failed",
            error: job.error_message ?? "Processing failed — no details available.",
          });
        } else {
          // queued or running
          setState({ phase: "processing", progress: job.progress });
        }
      } catch {
        consecutiveErrors++;
        if (consecutiveErrors >= 3) {
          // 3 consecutive failures = API is likely down, not just a hiccup
          setState({
            phase: "polling_error",
            lastStatus: "The API appears to be unreachable — the server may be restarting. " +
              "Your job is still queued and will continue when it comes back.",
          });
        }
      }
    }, POLL_INTERVAL_MS);
  }

  function handleFileSelect(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) startFlow(file);
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) startFlow(file);
  }

  // ── Render ──────────────────────────────────────────────────────────────

  if (state.phase === "complete") {
    return (
      <div className="glass p-10 text-center animate-fade-up">
        <div className="text-5xl mb-4">🎵</div>
        <h2 className="text-xl font-bold text-white mb-2">Separation complete!</h2>
        <p className="text-slate-400 text-sm mb-6">Your vocals and instrumental are ready.</p>
        <div className="flex gap-3 justify-center flex-wrap">
          <button
            id="view-stems-btn"
            className="btn-primary"
            onClick={() => router.push(`/songs/${state.songId}`)}
          >
            Listen to stems →
          </button>
          <button
            id="upload-another-btn"
            className="btn-ghost"
            onClick={() => { setState({ phase: "idle" }); setTitle(""); }}
          >
            Upload another
          </button>
        </div>
      </div>
    );
  }

  if (state.phase === "upload_failed") {
    return (
      <div className="glass p-8 animate-fade-up">
        <div className="flex items-start gap-3 mb-5">
          <span className="text-2xl">⚠️</span>
          <div>
            <h3 className="font-semibold text-white mb-1">Upload failed</h3>
            <p className="text-sm text-red-400">{state.error}</p>
          </div>
        </div>
        <div className="text-xs text-slate-500 mb-5 p-3 bg-white/5 rounded-lg">
          The song record was already created. You can retry the upload without starting over.
        </div>
        <div className="flex gap-3">
          <button
            id="retry-upload-btn"
            className="btn-primary"
            onClick={() => doUpload(
              state.retryPayload.file,
              state.retryPayload.presignedUrl,
              state.retryPayload.songId
            )}
          >
            Retry upload
          </button>
          <button
            id="cancel-upload-btn"
            className="btn-ghost"
            onClick={() => setState({ phase: "idle" })}
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  if (state.phase === "failed") {
    return (
      <div className="glass p-8 animate-fade-up">
        <div className="flex items-start gap-3 mb-6">
          <span className="text-2xl">❌</span>
          <div>
            <h3 className="font-semibold text-white mb-1">Something went wrong</h3>
            <p className="text-sm text-red-400">{state.error}</p>
          </div>
        </div>
        <button id="try-again-btn" className="btn-primary" onClick={() => setState({ phase: "idle" })}>
          Try again
        </button>
      </div>
    );
  }

  if (state.phase === "polling_error") {
    return (
      <div className="glass p-8 animate-fade-up">
        <div className="flex items-start gap-3">
          <span className="text-2xl">🔌</span>
          <div>
            <h3 className="font-semibold text-amber-400 mb-1">API unreachable</h3>
            <p className="text-sm text-slate-400">{state.lastStatus}</p>
            <p className="text-xs text-slate-500 mt-3">
              This is different from a processing failure — the server is likely restarting.
              Check back in a few minutes.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Use explicit phase narrowing to avoid 'as any' casts
  const uploadPct    = state.phase === "uploading"   ? state.pct      : 0;
  const processPct   = state.phase === "processing"  ? state.progress : 0;
  const isProcessing = ["creating", "uploading", "processing", "validating"].includes(state.phase);

  if (isProcessing) {
    const label =
      state.phase === "validating" ? "Validating…" :
      state.phase === "creating"   ? "Creating record…" :
      state.phase === "uploading"  ? `Uploading… ${uploadPct}%` :
                                     `Processing… ${processPct}%`;

    const pct =
      state.phase === "uploading"   ? uploadPct  :
      state.phase === "processing"  ? processPct :
      state.phase === "creating"    ? 5 :
      state.phase === "validating"  ? 2 : 0;

    const phaseLabel =
      state.phase === "uploading"   ? "Uploading to cloud storage" :
      state.phase === "processing" && processPct < 30 ? "Queued for processing" :
      state.phase === "processing" && processPct < 80 ? "Separating stems with Demucs…" :
      state.phase === "processing" ? "Saving results…" :
      "Preparing…";

    return (
      <div className="glass p-10 text-center animate-fade-up">
        {/* Waveform animation */}
        <div className="flex gap-1.5 items-end justify-center h-12 mb-6">
          {[16, 28, 40, 32, 20, 36, 24].map((h, i) => (
            <span
              key={i}
              className="waveform-bar"
              style={{ height: `${h}px`, animationDelay: `${i * 0.08}s` }}
            />
          ))}
        </div>

        <p className="text-white font-semibold text-lg mb-1">{phaseLabel}</p>
        <p className="text-slate-500 text-xs mb-6">{label}</p>

        <div className="progress-track mb-2">
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>
        <p className="text-right text-xs text-slate-600">{pct}%</p>

        {state.phase === "processing" && (
          <p className="text-xs text-slate-600 mt-4">
            Demucs on CPU takes a few minutes for a full song — this is normal ☕
          </p>
        )}
      </div>
    );
  }

  // ── Idle drop zone ───────────────────────────────────────────────────────
  return (
    <div className="flex flex-col gap-5 animate-fade-up">
      <div>
        <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
          Song title (optional)
        </label>
        <input
          id="song-title-input"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Leave blank to use filename"
          className="input-field"
        />
      </div>

      {/* Drop zone */}
      <div
        id="drop-zone"
        role="button"
        tabIndex={0}
        aria-label="Drop audio file here or click to browse"
        className={`relative flex flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed
          transition-all duration-200 cursor-pointer py-14 px-8 text-center
          ${dragOver
            ? "border-violet-500 bg-violet-500/10 scale-[1.01]"
            : "border-white/10 hover:border-violet-500/50 hover:bg-white/[0.02]"
          }`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        onKeyDown={(e) => e.key === "Enter" && fileInputRef.current?.click()}
      >
        <div className="text-4xl">🎧</div>
        <div>
          <p className="text-white font-semibold text-base">Drop your audio file here</p>
          <p className="text-slate-500 text-sm mt-1">or <span className="text-violet-400">browse files</span></p>
        </div>
        <p className="text-xs text-slate-600">MP3 · WAV · FLAC · M4A · up to 100 MB</p>

        <input
          ref={fileInputRef}
          type="file"
          id="file-input"
          accept={ACCEPTED_EXT}
          className="hidden"
          onChange={handleFileSelect}
        />
      </div>
    </div>
  );
}
