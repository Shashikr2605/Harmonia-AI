"use client";

export const dynamic = 'force-dynamic';

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { isAuthenticated, signOut } from "@/lib/auth";
import { getStems, Stem } from "@/lib/api";

const STEM_CONFIG: Record<string, { label: string; emoji: string; gradient: string }> = {
  vocals:       { label: "Vocals",       emoji: "🎤", gradient: "from-violet-600/20 to-violet-600/5" },
  instrumental: { label: "Instrumental", emoji: "🎸", gradient: "from-teal-600/20 to-teal-600/5" },
  drums:        { label: "Drums",        emoji: "🥁", gradient: "from-orange-600/20 to-orange-600/5" },
  bass:         { label: "Bass",         emoji: "🎵", gradient: "from-blue-600/20 to-blue-600/5" },
  other:        { label: "Other",        emoji: "✨", gradient: "from-pink-600/20 to-pink-600/5" },
};

function formatBytes(b: number) {
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(0)} KB`;
  return `${(b / (1024 * 1024)).toFixed(1)} MB`;
}

function StemPlayer({ stem }: { stem: Stem }) {
  const cfg = STEM_CONFIG[stem.stem_type] ?? STEM_CONFIG.other;

  return (
    <div className={`glass p-6 bg-gradient-to-br ${cfg.gradient} animate-fade-up`}>
      <div className="flex items-center gap-3 mb-4">
        <span className="text-2xl">{cfg.emoji}</span>
        <div>
          <h3 className="font-bold text-white text-lg">{cfg.label}</h3>
          <p className="text-xs text-slate-500">{stem.format.toUpperCase()} · {formatBytes(stem.file_size)}</p>
        </div>
      </div>

      <audio
        id={`player-${stem.stem_type}`}
        controls
        preload="metadata"
        src={stem.download_url}
        className="w-full"
      >
        Your browser does not support the audio element.
      </audio>

      <a
        id={`download-${stem.stem_type}`}
        href={stem.download_url}
        download={`${stem.stem_type}.${stem.format}`}
        className="inline-flex items-center gap-2 mt-3 text-xs text-slate-500 hover:text-slate-300 transition-colors"
      >
        ↓ Download {cfg.label.toLowerCase()}
      </a>
    </div>
  );
}

export default function SongDetailPage() {
  const params = useParams();
  const router = useRouter();
  const songId = params?.id as string;

  const [stems, setStems] = useState<Stem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) { router.replace("/login"); return; }
    fetchStems();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [songId]);

  async function fetchStems() {
    setLoading(true);
    setError(null);
    try {
      const data = await getStems(songId);
      setStems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load stems");
    } finally {
      setLoading(false);
    }
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
          <Link href="/library" className="btn-ghost text-sm py-2 px-4">← Library</Link>
          <Link href="/upload" className="btn-primary text-sm py-2 px-4">+ Upload</Link>
          <button onClick={handleSignOut} className="btn-ghost text-sm py-2 px-4">Sign out</button>
        </div>
      </nav>

      <div className="max-w-2xl mx-auto px-4 pt-12 pb-20">
        <h1 className="text-2xl font-bold text-white mb-2">Stems</h1>
        <p className="text-slate-500 text-sm mb-8">
          Separated tracks — play each stem independently.
        </p>

        {loading && (
          <div className="flex justify-center py-20">
            <div className="flex gap-1 items-end h-12">
              {[1,2,3,4,5].map((i) => (
                <span key={i} className="waveform-bar" style={{ height: `${18 + i*7}px` }} />
              ))}
            </div>
          </div>
        )}

        {error && (
          <div className="glass p-8 text-center">
            <p className="text-red-400 text-sm mb-3">{error}</p>
            <button className="btn-ghost text-sm" onClick={fetchStems}>Retry</button>
          </div>
        )}

        {!loading && !error && stems.length === 0 && (
          <div className="glass p-10 text-center">
            <p className="text-slate-400 text-sm">No stems found for this song yet.</p>
            <p className="text-slate-600 text-xs mt-2">
              The job may still be processing — check your library for status.
            </p>
          </div>
        )}

        {!loading && !error && stems.length > 0 && (
          <div className="flex flex-col gap-5">
            {/* Recommended order: vocals, then instrumental, then anything else */}
            {["vocals", "instrumental", "drums", "bass", "other"]
              .map((type) => stems.find((s) => s.stem_type === type))
              .filter(Boolean)
              .map((stem) => (
                <StemPlayer key={stem!.id} stem={stem!} />
              ))}
          </div>
        )}
      </div>
    </div>
  );
}
