"use client";

export const dynamic = 'force-dynamic';

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { signUp } from "@/lib/auth";

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const { error: authError } = await signUp(email, password);
    setLoading(false);
    if (authError) {
      setError(authError);
    } else {
      // Local auth signs in immediately — no email confirmation step.
      router.replace("/upload");
    }
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-mesh px-4">
      <div className="w-full max-w-sm animate-fade-up">
        <div className="text-center mb-8">
          <div className="inline-flex items-end gap-1 mb-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <span key={i} className="waveform-bar" style={{ height: `${12 + i * 5}px` }} />
            ))}
          </div>
          <h1 className="text-2xl font-bold text-white">Harmonia AI</h1>
          <p className="text-sm text-slate-500 mt-1">Create your free account</p>
        </div>

        <div className="glass p-8">
            <form onSubmit={handleSubmit} className="flex flex-col gap-5">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                  Email
                </label>
                <input
                  id="signup-email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="input-field"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                  Password
                </label>
                <input
                  id="signup-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="min. 8 characters"
                  className="input-field"
                />
              </div>

              {error && (
                <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
                  {error}
                </div>
              )}

              <button
                id="signup-submit"
                type="submit"
                disabled={loading}
                className="btn-primary w-full mt-1"
              >
                {loading ? "Creating account…" : "Create account"}
              </button>
            </form>

            <p className="text-center text-sm text-slate-500 mt-6">
              Already have an account?{" "}
              <Link href="/login" className="text-violet-400 hover:text-violet-300 font-medium transition-colors">
                Sign in
              </Link>
            </p>
        </div>
      </div>
    </div>
  );
}
