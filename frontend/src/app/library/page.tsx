"use client";

export const dynamic = 'force-dynamic';

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { isAuthenticated, signOut } from "@/lib/auth";
import { listSongs, Song } from "@/lib/api";

function StatusBadge({ status }: { status: Song["status"] }) {
  const map: Record<Song["status"], string> = {
    uploaded: "badge badge-uploaded",
    processing: "badge badge-processing",
    complete: "badge badge-complete",
    failed: "badge badge-failed",
  };
  return <span className={map[status]}>{status}</span>;
}

export default function LibraryPage() {
  const router = useRouter();
  const [songs, setSongs] = useState<Song[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  useEffect(() => {
    if (!isAuthenticated()) { router.replace("/login"); return; }
    fetchSongs(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function fetchSongs(p: number) {
    setLoading(true);
    setError(null);
    try {
      const data = await listSongs(p, 20);
      setSongs(data);
      setPage(p);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load songs");
    } finally {
      setLoading(false);
    }
  }

  function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short", day: "numeric", year: "numeric",
    });
  }

  function handleSignOut() {
    signOut();
    router.replace("/login");
  }

  return (
    <div className="min-h-dvh bg-mesh">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-4 border-b border-white/5">
        <div className="flex items-center gap-2">
          <div className="flex items-end gap-0.5">
            {[1,2,3,4,5].map((i) => (
              <span key={i} className="waveform-bar" style={{ height: `${8 + i*3}px` }} />
            ))}
          </div>
          <span className="font-bold text-white ml-2">Harmonia AI</span>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/upload" className="btn-primary text-sm py-2 px-4">+ Upload</Link>
          <button onClick={handleSignOut} className="btn-ghost text-sm py-2 px-4">Sign out</button>
        </div>
      </nav>

      <div className="max-w-3xl mx-auto px-4 pt-12 pb-16">
        <h1 className="text-2xl font-bold text-white mb-2">Your Library</h1>
        <p className="text-slate-500 text-sm mb-8">All your separated tracks, newest first.</p>

        {loading && (
          <div className="flex justify-center py-20">
            <div className="flex gap-1 items-end h-10">
              {[1,2,3,4,5].map((i) => (
                <span key={i} className="waveform-bar" style={{ height: `${16 + i*6}px` }} />
              ))}
            </div>
          </div>
        )}

        {error && (
          <div className="glass p-6 text-center">
            <p className="text-red-400 text-sm mb-3">{error}</p>
            <button className="btn-ghost text-sm" onClick={() => fetchSongs(page)}>Retry</button>
          </div>
        )}

        {!loading && !error && songs.length === 0 && (
          <div className="glass p-12 text-center">
            <div className="text-4xl mb-4">🎵</div>
            <p className="text-white font-semibold mb-2">No songs yet</p>
            <p className="text-slate-500 text-sm mb-6">Upload your first track to get started.</p>
            <Link href="/upload" className="btn-primary">Upload a track</Link>
          </div>
        )}

        {!loading && !error && songs.length > 0 && (
          <div className="flex flex-col gap-3">
            {songs.map((song) => (
              <Link
                key={song.id}
                href={song.status === "complete" ? `/songs/${song.id}` : "#"}
                id={`song-card-${song.id}`}
                className={`glass p-5 flex items-center gap-4 transition-all duration-150
                  ${song.status === "complete"
                    ? "hover:border-violet-500/40 hover:-translate-y-0.5 cursor-pointer"
                    : "cursor-default opacity-80"}`}
              >
                {/* Icon */}
                <div className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
                  style={{ background: "rgba(124,58,237,0.15)" }}>
                  <span className="text-lg">
                    {song.status === "complete" ? "🎧" :
                     song.status === "processing" ? "⚙️" :
                     song.status === "failed" ? "❌" : "📁"}
                  </span>
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-white truncate">{song.title}</p>
                  <p className="text-xs text-slate-500 mt-0.5 truncate">{song.original_filename}</p>
                </div>

                {/* Meta */}
                <div className="flex flex-col items-end gap-1.5 shrink-0">
                  <StatusBadge status={song.status} />
                  <span className="text-xs text-slate-600">{formatDate(song.created_at)}</span>
                </div>
              </Link>
            ))}
          </div>
        )}

        {/* Pagination */}
        {!loading && songs.length === 20 && (
          <div className="flex justify-center mt-8">
            <button
              className="btn-ghost text-sm"
              onClick={() => fetchSongs(page + 1)}
            >
              Load more
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
