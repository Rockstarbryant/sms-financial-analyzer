import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../services/api";

type Mode = "login" | "register";

export function LoginPage() {
  const { login, register, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/dashboard", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  if (isAuthenticated) {
    return null;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login({ email: email.trim(), password });
      } else {
        await register({
          email: email.trim(),
          password,
          full_name: fullName.trim() || undefined,
        });
      }
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-dvh max-w-lg flex-col justify-center bg-paper px-5 sm:max-w-md">
      <div className="receipt-card px-6 py-8">
        <p className="font-display text-xl font-semibold text-ink">
          {mode === "login" ? "Welcome back" : "Create your account"}
        </p>
        <p className="mt-2 text-sm text-ink-soft">
          {mode === "login"
            ? "Sign in to see your M-Pesa & Airtel Money ledger in the cloud."
            : "One account for the web dashboard and the Android SMS companion."}
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          {mode === "register" && (
            <Field label="Full name (optional)">
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                autoComplete="name"
                className="field-input"
                placeholder="Jane Doe"
              />
            </Field>
          )}

          <Field label="Email">
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              className="field-input"
              placeholder="you@example.com"
            />
          </Field>

          <Field label="Password">
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              className="field-input"
              placeholder="At least 8 characters"
            />
          </Field>

          {error && (
            <p className="rounded-xl bg-airtel/10 px-3 py-2 text-xs text-airtel">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-full bg-mpesa px-4 py-3 text-sm font-semibold text-white transition-opacity active:opacity-80 disabled:opacity-50"
          >
            {submitting
              ? mode === "login"
                ? "Signing in…"
                : "Creating account…"
              : mode === "login"
                ? "Sign in"
                : "Create account"}
          </button>
        </form>

        <p className="mt-5 text-center text-xs text-ink-soft">
          {mode === "login" ? (
            <>
              No account yet?{" "}
              <button
                type="button"
                onClick={() => {
                  setMode("register");
                  setError(null);
                }}
                className="font-medium text-mpesa"
              >
                Create one
              </button>
            </>
          ) : (
            <>
              Already have an account?{" "}
              <button
                type="button"
                onClick={() => {
                  setMode("login");
                  setError(null);
                }}
                className="font-medium text-mpesa"
              >
                Sign in
              </button>
            </>
          )}
        </p>
      </div>

      <p className="mt-6 text-center text-xs text-ink-faint">
        Prefer local-only on this phone?{" "}
        <Link to="/" className="font-medium text-ink-soft underline">
          Continue without an account
        </Link>
      </p>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block text-left">
      <span className="text-xs font-medium text-ink-soft">{label}</span>
      <div className="mt-1">{children}</div>
    </label>
  );
}
