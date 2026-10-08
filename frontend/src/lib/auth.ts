// Local email/password auth against the FastAPI backend.
//
// Replaces the old Supabase browser client — the app is fully self-contained
// now (no external auth service). The backend (app/api/v1/auth_endpoint.py)
// issues an HS256 JWT which we stash in localStorage; lib/api.ts reads it for
// the Authorization header on every request.

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "harmonia.token";
const USER_KEY = "harmonia.user";

export interface AuthUser {
  id: string;
  email: string;
}

interface AuthResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

/** The current access token, or null when signed out. SSR-safe. */
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

/** The signed-in user, or null. SSR-safe. */
export function getUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(USER_KEY);
  return raw ? (JSON.parse(raw) as AuthUser) : null;
}

/** True when a token is present. Does not check server-side expiry. */
export function isAuthenticated(): boolean {
  return getToken() !== null;
}

function persist(res: AuthResponse): void {
  window.localStorage.setItem(TOKEN_KEY, res.access_token);
  window.localStorage.setItem(USER_KEY, JSON.stringify(res.user));
}

async function authPost(
  path: string,
  email: string,
  password: string
): Promise<{ error: string | null }> {
  try {
    const res = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      // FastAPI returns a string `detail` for our handled errors, but a list
      // for 422 validation errors — coerce anything non-string to a generic msg.
      const detail =
        typeof data.detail === "string" ? data.detail : `Request failed (${res.status})`;
      return { error: detail };
    }
    persist(data as AuthResponse);
    return { error: null };
  } catch {
    return { error: "Cannot reach the server. Is the API running on port 8000?" };
  }
}

/** Create an account and sign in. */
export function signUp(email: string, password: string) {
  return authPost("/api/v1/auth/signup", email, password);
}

/** Sign in to an existing account. */
export function signIn(email: string, password: string) {
  return authPost("/api/v1/auth/login", email, password);
}

/** Clear the local session. */
export function signOut(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}
