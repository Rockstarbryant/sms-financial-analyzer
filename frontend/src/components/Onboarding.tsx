import { useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../services/api";
import { useAuth } from "../context/AuthContext";

interface OnboardingProps {
  onImported: () => void;
}

type ProviderChoice = "mpesa" | "airtel_money";

export function Onboarding({ onImported }: OnboardingProps) {
  const { isAuthenticated } = useAuth();
  const [provider, setProvider] = useState<ProviderChoice>("mpesa");
  const [password, setPassword] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Choose a PDF statement file first.");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const stats = await api.uploadStatement(
        file,
        provider,
        password.trim() || undefined,
      );
      setResult(
        `Imported ${stats.inserted} of ${stats.scanned} rows (${stats.duplicates} already stored).`,
      );
      onImported();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-[70dvh] flex-col items-center justify-center px-2 text-center">
      <div className="receipt-card mb-8 w-full max-w-sm px-6 py-8">
        <p className="font-display text-xl font-semibold text-ink">
          {isAuthenticated ? "Your cloud ledger" : "Your ledger"}
        </p>
        <p className="mt-3 text-sm leading-relaxed text-ink-soft">
          Upload an <strong>M-Pesa</strong> or <strong>Airtel Money</strong>{" "}
          PDF statement. SMS is not required — statements are the source of
          truth when you upload them.
        </p>

        {!isAuthenticated && (
          <Link
            to="/login"
            className="mt-5 block w-full rounded-full bg-mpesa px-4 py-3 text-sm font-semibold text-white transition-opacity active:opacity-80"
          >
            Sign in / Create account
          </Link>
        )}

        <form onSubmit={handleUpload} className="mt-5 space-y-3 text-left">
          <div>
            <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-ink-faint">
              Provider
            </p>
            <div className="flex gap-2">
              {(
                [
                  ["mpesa", "M-Pesa"],
                  ["airtel_money", "Airtel Money"],
                ] as const
              ).map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setProvider(id)}
                  className={`flex-1 rounded-full px-3 py-2 text-xs font-medium ${
                    provider === id
                      ? id === "mpesa"
                        ? "bg-mpesa text-white"
                        : "bg-airtel text-white"
                      : "border border-line bg-paper-raised text-ink-soft"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="mb-1.5 block text-[11px] font-medium uppercase tracking-wide text-ink-faint">
              Statement PDF
            </label>
            <input
              type="file"
              accept="application/pdf,.pdf"
              onChange={(ev) => setFile(ev.target.files?.[0] ?? null)}
              className="block w-full text-xs text-ink file:mr-3 file:rounded-full file:border-0 file:bg-paper file:px-3 file:py-2 file:text-xs file:font-medium file:text-ink"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-[11px] font-medium uppercase tracking-wide text-ink-faint">
              PDF password {provider === "mpesa" ? "(required for most M-Pesa files)" : "(if any)"}
            </label>
            <input
              type="password"
              value={password}
              onChange={(ev) => setPassword(ev.target.value)}
              placeholder={
                provider === "mpesa"
                  ? "ID number or SMS access code"
                  : "Leave blank if unlocked"
              }
              className="w-full rounded-xl border border-line bg-paper-raised px-3 py-2.5 text-sm text-ink outline-none focus:border-mpesa"
              autoComplete="off"
            />
            <p className="mt-1 text-[10px] text-ink-faint">
              M-Pesa: usually your national ID, or the code Safaricom texts you.
            </p>
          </div>

          <button
            type="submit"
            disabled={loading || !file}
            className="w-full rounded-full bg-mpesa px-4 py-3 text-sm font-semibold text-white transition-opacity active:opacity-80 disabled:opacity-50"
          >
            {loading ? "Parsing statement…" : "Upload & import"}
          </button>
        </form>

        {result && <p className="mt-4 text-xs text-mpesa">{result}</p>}
        {error && <p className="mt-4 text-xs text-airtel">{error}</p>}
      </div>

      <p className="max-w-xs text-xs text-ink-faint">
        You can upload both M-Pesa and Airtel statements (one at a time). Re-upload
        is safe — duplicates are skipped. Manage more uploads anytime in Settings.
      </p>
    </div>
  );
}
