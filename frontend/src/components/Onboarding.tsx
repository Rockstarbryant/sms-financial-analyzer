import { useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../services/api";
import { useAuth } from "../context/AuthContext";

interface OnboardingProps {
  onImported: () => void;
}

type Mode = "demo" | "sync";

export function Onboarding({ onImported }: OnboardingProps) {
  const { isAuthenticated } = useAuth();
  const [loadingMode, setLoadingMode] = useState<Mode | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  async function run(mode: Mode) {
    setLoadingMode(mode);
    setError(null);
    setResult(null);
    try {
      const stats =
        mode === "demo" ? await api.importDemoData() : await api.syncSms();
      setResult(
        `Imported ${stats.inserted} transactions from ${stats.scanned} messages (${stats.duplicates} already there, ${stats.unknown} unrecognized).`,
      );
      onImported();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Import failed.");
    } finally {
      setLoadingMode(null);
    }
  }

  return (
    <div className="flex min-h-[70dvh] flex-col items-center justify-center px-2 text-center">
      <div className="receipt-card mb-8 w-full max-w-sm px-6 py-8">
        <p className="font-display text-xl font-semibold text-ink">
          {isAuthenticated ? "Your cloud ledger" : "Your ledger, on your device"}
        </p>
        <p className="mt-3 text-sm leading-relaxed text-ink-soft">
          {isAuthenticated
            ? "Import demo data to explore the dashboard, or sync real SMS from the Android companion app."
            : "This app can run fully locally, or you can sign in to use the cloud dashboard with the Android companion app."}
        </p>

        {!isAuthenticated && (
          <>
            <Link
              to="/login"
              className="mt-6 block w-full rounded-full bg-mpesa px-4 py-3 text-sm font-semibold text-white transition-opacity active:opacity-80"
            >
              Sign in / Create account
            </Link>
            <p className="mt-3 text-xs text-ink-faint">
              Best for non-technical use — pair with the Android app for SMS.
            </p>
          </>
        )}

        {!isAuthenticated && (
          <button
            onClick={() => run("sync")}
            disabled={loadingMode !== null}
            className="mt-4 w-full rounded-full border border-line bg-paper-raised px-4 py-3 text-sm font-medium text-ink transition-opacity active:opacity-80 disabled:opacity-50"
          >
            {loadingMode === "sync" ? "Syncing…" : "Sync my SMS (Termux)"}
          </button>
        )}

        <div className="mt-4 rounded-xl bg-paper px-4 py-3 text-left text-xs text-ink-soft">
          <p className="font-medium text-ink">Or try sample data first</p>
          <p className="mt-1">
            See how the dashboard, transactions, and analytics work using
            synthetic M-Pesa and Airtel Money messages — no SMS permission
            needed.
          </p>
          <button
            onClick={() => run("demo")}
            disabled={loadingMode !== null}
            className="mt-3 w-full rounded-full border border-line bg-paper-raised px-4 py-2 text-sm font-medium text-ink active:opacity-80 disabled:opacity-50"
          >
            {loadingMode === "demo" ? "Importing…" : "Import demo data"}
          </button>
        </div>

        {result && <p className="mt-4 text-xs text-mpesa">{result}</p>}
        {error && <p className="mt-4 text-xs text-airtel">{error}</p>}
      </div>

      <p className="max-w-xs text-xs text-ink-faint">
        You can sync SMS or import demo data again any time from Settings.
      </p>
    </div>
  );
}
