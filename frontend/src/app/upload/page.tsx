"use client";

export const dynamic = 'force-dynamic';

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { isAuthenticated, signOut } from "@/lib/auth";
import UploadFlow from "@/components/UploadFlow";

export default function UploadPage() {
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated()) router.replace("/login");
  }, [router]);

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
          <Link href="/library" className="btn-ghost text-sm py-2 px-4">Library</Link>
          <button onClick={handleSignOut} className="btn-ghost text-sm py-2 px-4">
            Sign out
          </button>
        </div>
      </nav>

      {/* Hero */}
      <div className="max-w-xl mx-auto px-4 pt-16 pb-12">
        <div className="text-center mb-10">
          <h1 className="text-3xl font-bold text-white mb-3">
            Separate any song into stems
          </h1>
          <p className="text-slate-400 text-base">
            Upload a track and AI isolates the vocals and instrumental instantly.
          </p>
        </div>

        <UploadFlow />
      </div>
    </div>
  );
}
