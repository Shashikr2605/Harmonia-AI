import { getToken } from "./auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Auth helper
// ---------------------------------------------------------------------------

function getAuthHeaders(): HeadersInit {
  const token = getToken();
  if (!token) throw new Error("Not authenticated");
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
}

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

export interface Song {
  id: string;
  title: string;
  original_filename: string;
  status: "uploaded" | "processing" | "complete" | "failed";
  created_at: string;
  duration_seconds: number | null;
}

export interface JobStatus {
  status: "queued" | "running" | "complete" | "failed";
  progress: number;
  error_message: string | null;
}

export interface Stem {
  id: string;
  stem_type: "vocals" | "instrumental" | "drums" | "bass" | "other";
  format: string;
  file_size: number;
  download_url: string;
}

export interface Config {
  max_upload_size_mb: number;
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

/** GET /health — no auth, used to check reachability */
export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/health`, { signal: AbortSignal.timeout(5000) });
    return res.ok;
  } catch {
    return false;
  }
}

/** GET /api/v1/config — no auth */
export async function getConfig(): Promise<Config> {
  const res = await fetch(`${API_URL}/api/v1/config`);
  if (!res.ok) throw new Error("Failed to fetch config");
  return res.json();
}

/**
 * Step 1 of upload flow.
 * POST /api/v1/songs → {song_id, r2_original_key}
 */
export async function createSong(
  title: string,
  originalFilename: string
): Promise<{ song_id: string; r2_original_key: string }> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/songs`, {
    method: "POST",
    headers,
    body: JSON.stringify({ title, original_filename: originalFilename }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Create song failed (${res.status})`);
  }
  return res.json();
}

/**
 * Step 2a of upload flow.
 * POST /api/v1/songs/{song_id}/upload-url → {url}
 */
export async function getUploadUrl(
  songId: string,
  contentType: string
): Promise<string> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_URL}/api/v1/songs/${songId}/upload-url?content_type=${encodeURIComponent(contentType)}`,
    { method: "POST", headers }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Get upload URL failed (${res.status})`);
  }
  const data = await res.json();
  return data.url;
}

/**
 * Step 2b of upload flow.
 * PUT directly to R2 presigned URL — audio never touches our API.
 * Throws on network error or non-2xx from R2.
 * This function is intentionally separate so the caller can retry the PUT
 * without re-creating the song record.
 */
export async function uploadToR2(
  presignedUrl: string,
  file: File,
  onProgress?: (pct: number) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", presignedUrl);
    // Must match the Content-Type the presigned URL was signed with (see
    // getUploadUrl in UploadFlow, which uses the same `|| "audio/mpeg"` fallback).
    // A mismatch makes S3/R2/MinIO reject the PUT with SignatureDoesNotMatch.
    xhr.setRequestHeader("Content-Type", file.type || "audio/mpeg");

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
      } else {
        reject(
          new Error(
            `R2 upload failed: HTTP ${xhr.status}. ` +
              `Check the R2 bucket CORS policy allows PUT from this origin.`
          )
        );
      }
    });

    xhr.addEventListener("error", () =>
      reject(new Error("R2 upload network error. Check your connection and the R2 CORS policy."))
    );
    xhr.addEventListener("abort", () => reject(new Error("Upload cancelled")));

    xhr.send(file);
  });
}

/**
 * Step 3 of upload flow.
 * POST /api/v1/songs/{song_id}/process → {job_id}
 */
export async function startProcessing(songId: string): Promise<string> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/songs/${songId}/process`, {
    method: "POST",
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Start processing failed (${res.status})`);
  }
  const data = await res.json();
  return data.job_id;
}

/** GET /api/v1/jobs/{job_id} — poll this every 3s */
export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/jobs/${jobId}`, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Get job status failed (${res.status})`);
  }
  return res.json();
}

/** GET /api/v1/songs/{song_id}/stems */
export async function getStems(songId: string): Promise<Stem[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/songs/${songId}/stems`, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Get stems failed (${res.status})`);
  }
  return res.json();
}

/** GET /api/v1/songs — paginated library */
export async function listSongs(page = 1, pageSize = 20): Promise<Song[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_URL}/api/v1/songs?page=${page}&page_size=${pageSize}`,
    { headers }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `List songs failed (${res.status})`);
  }
  return res.json();
}
