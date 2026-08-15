import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useApiData } from "../hooks/useApiData";
import { api, ApiError } from "../services/api";
import { LoadingState } from "../components/StateViews";
import { useAuth } from "../context/AuthContext";

type Tone = "success" | "error";

export function SettingsPage() {
  const { data, loading, refetch } = useApiData(() =>
    api.listTransactions({ limit: 1 }),
  );
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const [importing, setImporting] = useState(false);
  const [importMessage, setImportMessage] = useState<string | null>(null);
  const [importTone, setImportTone] = useState<Tone>("success");

  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [syncTone, setSyncTone] = useState<Tone>("success");

  async function handleImport() {
    setImporting(true);
    setImportMessage(null);
    try {
      const stats = await api.importDemoData();
      setImportMessage(
        `Scanned ${stats.scanned} · inserted ${stats.inserted} · duplicates ${stats.duplicates} · unrecognized ${stats.unknown}`,
      );
      setImportTone("success");
      refetch();
    } catch (err) {
      setImportMessage(err instanceof ApiError ? err.message : "Import failed.");
      setImportTone("error");
    } finally {
      setImporting(false);
    }
  }

  async function handleSync() {
    setSyncing(true);
    setSyncMessage(null);
    try {
      const stats = await api.syncSms();
      setSyncMessage(
        `Scanned ${stats.scanned} · inserted ${stats.inserted} · duplicates ${stats.duplicates} · unrecognized ${stats.unknown}`,
      );
      setSyncTone("success");
      refetch();
    } catch (err) {
      if (err instanceof ApiError) {
        setSyncMessage(err.message);
      } else {
        setSyncMessage("Sync failed.");
      }
      setSyncTone("error");
    } finally {
      setSyncing(false);
    }
  }

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="space-y-6">
      <section>
        <SectionTitle>Account</SectionTitle>
        <div className="rounded-2xl border border-line bg-paper-raised px-4 py-4">
          {isAuthenticated && user ? (
            <>
              <p className="text-sm font-medium text-ink">
                {user.full_name || "Signed in"}
              </p>
              <p className="mt-0.5 text-xs text-ink-soft">{user.email}</p>
              <p className="mt-2 text-xs text-ink-faint">
                Cloud mode — data is stored on the server and synced from the
                Android companion app.
              </p>
              <button
                onClick={handleLogout}
                className="mt-3 rounded-full border border-line bg-paper px-4 py-2 text-sm font-medium text-ink active:opacity-80"
              >
                Sign out
              </button>
            </>
          ) : (
            <>
              <p className="text-sm font-medium text-ink">Local mode</p>
              <p className="mt-1 text-xs text-ink-soft">
                You're using this app without an account. Data stays on this
                device. Sign in to use the cloud dashboard with the Android
                companion app.
              </p>
              <Link
                to="/login"
                className="mt-3 inline-block rounded-full bg-mpesa px-4 py-2 text-sm font-medium text-white active:opacity-80"
              >
                Sign in / Create account
              </Link>
            </>
          )}
        </div>
      </section>

      <section>
        <SectionTitle>Data</SectionTitle>
        <div className="rounded-2xl border border-line bg-paper-raised px-4 py-4">
          <p className="text-sm font-medium text-ink">Database</p>
          {loading ? (
            <LoadingState label="Checking…" />
          ) : (
            <p className="mt-1 text-sm text-ink-soft">
              {data?.total ?? 0} transaction{data?.total === 1 ? "" : "s"}{" "}
              {isAuthenticated ? "in your cloud account" : "stored on this device"}.
            </p>
          )}
        </div>
      </section>

      {!isAuthenticated && (
        <section>
          <SectionTitle>Sync SMS (local)</SectionTitle>
          <div className="rounded-2xl border border-line bg-paper-raised px-4 py-4">
            <p className="text-sm font-medium text-ink">
              Sync from this phone's SMS
            </p>
            <p className="mt-1 text-xs text-ink-soft">
              Reads M-Pesa and Airtel Money messages via Termux:API and
              imports recognized transactions. Safe to run repeatedly — it
              never creates duplicates.
            </p>
            <button
              onClick={handleSync}
              disabled={syncing}
              className="mt-3 rounded-full bg-mpesa px-4 py-2 text-sm font-medium text-white active:opacity-80 disabled:opacity-50"
            >
              {syncing ? "Syncing…" : "Sync SMS"}
            </button>
            {syncMessage && (
              <p
                className={`mt-3 text-xs ${
                  syncTone === "success" ? "text-mpesa" : "text-airtel"
                }`}
              >
                {syncMessage}
              </p>
            )}
          </div>
        </section>
      )}

      {isAuthenticated && (
        <section>
          <SectionTitle>SMS sync</SectionTitle>
          <div className="rounded-2xl border border-line bg-paper-raised px-4 py-4">
            <p className="text-sm font-medium text-ink">
              Use the Android companion app
            </p>
            <p className="mt-1 text-xs text-ink-soft">
              Install the companion app on your phone, sign in with the same
              account, and grant SMS permission. It will upload M-Pesa and
              Airtel Money messages to this dashboard automatically.
            </p>
          </div>
        </section>
      )}

      <section>
        <SectionTitle>Demo data</SectionTitle>
        <div className="rounded-2xl border border-line bg-paper-raised px-4 py-4">
          <p className="text-sm font-medium text-ink">Import demo data</p>
          <p className="mt-1 text-xs text-ink-soft">
            Loads synthetic M-Pesa and Airtel Money messages through the
            same parser real SMS uses. Useful for trying the app without
            SMS access.
          </p>
          <button
            onClick={handleImport}
            disabled={importing}
            className="mt-3 rounded-full bg-ink px-4 py-2 text-sm font-medium text-paper active:opacity-80 disabled:opacity-50"
          >
            {importing ? "Importing…" : "Import demo data"}
          </button>
          {importMessage && (
            <p
              className={`mt-3 text-xs ${
                importTone === "success" ? "text-mpesa" : "text-airtel"
              }`}
            >
              {importMessage}
            </p>
          )}
        </div>
      </section>

      <section>
        <SectionTitle>Supported providers</SectionTitle>
        <div className="flex gap-3">
          <ProviderChip label="M-Pesa" accent="mpesa" />
          <ProviderChip label="Airtel Money" accent="airtel" />
        </div>
      </section>

      <section>
        <SectionTitle>Privacy</SectionTitle>
        <div className="rounded-2xl border border-line bg-paper-raised px-4 py-4 text-xs leading-relaxed text-ink-soft">
          {isAuthenticated ? (
            <>
              <p>
                In cloud mode, parsed transactions are stored on the server
                under your account. The Android companion app only uploads
                SMS from known M-Pesa and Airtel Money senders.
              </p>
              <p className="mt-2">
                Raw SMS bodies are never returned by the API or shown in this
                dashboard. You can sign out at any time from this page.
              </p>
            </>
          ) : (
            <>
              <p>
                This app is local-first. Your SMS content and parsed
                transactions are stored only in a SQLite database on this
                device, and the backend only listens on 127.0.0.1 — it's never
                exposed to the network.
              </p>
              <p className="mt-2">
                No SMS content or transaction data is ever sent to external
                AI services. Raw SMS bodies are never returned by the API or
                shown in this app.
              </p>
            </>
          )}
        </div>
      </section>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-ink-faint">
      {children}
    </p>
  );
}

function ProviderChip({
  label,
  accent,
}: {
  label: string;
  accent: "mpesa" | "airtel";
}) {
  const classes =
    accent === "mpesa"
      ? "bg-mpesa-soft text-mpesa"
      : "bg-airtel-soft text-airtel";
  return (
    <span className={`rounded-full px-3 py-1.5 text-xs font-medium ${classes}`}>
      {label}
    </span>
  );
}
