"use client";

export const dynamic = 'force-dynamic';

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";

/**
 * Root page — redirects authenticated users to /upload, guests to /login.
 */
export default function RootPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace(isAuthenticated() ? "/upload" : "/login");
  }, [router]);

  return (
    <div className="flex min-h-dvh items-center justify-center bg-mesh">
      <div className="flex flex-col items-center gap-4">
        <div className="flex gap-1 items-end h-8">
          {[1, 2, 3, 4, 5].map((i) => (
            <span
              key={i}
              className="waveform-bar"
              style={{ height: `${20 + i * 8}px` }}
            />
          ))}
        </div>
        <p className="text-sm text-slate-500">Loading…</p>
      </div>
    </div>
  );
}
