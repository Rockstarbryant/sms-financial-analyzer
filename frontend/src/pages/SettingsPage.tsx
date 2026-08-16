import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useApiData } from "../hooks/useApiData";
import { api, ApiError } from "../services/api";
import { LoadingState } from "../components/StateViews";
import { useAuth } from "../context/AuthContext";

type Tone = "success" | "error";
type ProviderChoice = "mpesa" | "airtel_money";

export function SettingsPage() {
  const { data, loading, refetch } = useApiData(() =>
    api.listTransactions({ limit: 1 }),
  );
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const [provider, setProvider] = useState<ProviderChoice>("mpesa");
  const [password, setPassword] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [uploadTone, setUploadTone] = useState<Tone>("success");

  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [syncTone, setSyncTone] = useState<Tone>("success");

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setUploadMessage("Choose a PDF first.");
      setUploadTone("error");
      return;
    }
    setUploading(true);
    setUploadMessage(null);
    try {
      const stats = await api.uploadStatement(
        file,
        provider,
        password.trim() || undefined,
      );
      setUploadMessage(
        `Scanned ${stats.scanned} · inserted ${stats.inserted} · duplicates ${stats.duplicates}`,
      );
      setUploadTone("success");
      setFile(null);
      refetch();
    } catch (err) {
      setUploadMessage(err instanceof ApiError ? err.message : "Upload failed.");
      setUploadTone("error");
    } finally {
      setUploading(false);
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
      setSyncMessage(err instanceof ApiError ? err.message : "Sync failed.");
      setSyncTone("error");
    } finally {
      setSyncing(false);
    }
  }

  if (loading && !data) return <LoadingState label="Loading settings…" />;

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-line bg-paper-raised px-4 py-4">
        <p className="text-sm font-medium text-ink">Account</p>
        {isAuthenticated && user ? (
          <div className="mt-2 space-y-2">
            <p className="text-sm text-ink-soft">{user.email}</p>
            <button
              type="button"
              onClick={() => {
                logout();
                navigate("/");
              }}
              className="text-sm font-medium text-airtel"
            >
              Sign out
            </button>
          </div>
        ) : (
          <p className="mt-2 text-sm text-ink-soft">
            <Link to="/login" className="font-medium text-mpesa">
              Sign in
            </Link>{" "}
            to keep your ledger in the cloud.
          </p>
        )}
      </section>

      <section className="rounded-2xl border border-line bg-paper-raised px-4 py-4">
        <p className="text-sm font-medium text-ink">Upload statement PDF</p>
        <p className="mt-1 text-xs text-ink-faint">
          M-Pesa or Airtel Money official PDF. Statements are the primary import
          path; SMS is optional for local testing.
        </p>

        <form onSubmit={handleUpload} className="mt-4 space-y-3">
          <div className="flex gap-2">
            {(
              [
                ["mpesa", "M-Pesa"],
                ["airtel_money", "Airtel"],
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
                    : "border border-line text-ink-soft"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <input
            type="file"
            accept="application/pdf,.pdf"
            onChange={(ev) => setFile(ev.target.files?.[0] ?? null)}
            className="block w-full text-xs text-ink file:mr-3 file:rounded-full file:border-0 file:bg-paper file:px-3 file:py-2 file:text-xs file:font-medium"
          />

          <input
            type="password"
            value={password}
            onChange={(ev) => setPassword(ev.target.value)}
            placeholder="PDF password (ID or SMS code for M-Pesa)"
            className="w-full rounded-xl border border-line bg-paper px-3 py-2.5 text-sm outline-none focus:border-mpesa"
            autoComplete="off"
          />

          <button
            type="submit"
            disabled={uploading || !file}
            className="w-full rounded-full bg-mpesa px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
          >
            {uploading ? "Parsing…" : "Upload & import"}
          </button>
        </form>

        {uploadMessage && (
          <p
            className={`mt-3 text-xs ${
              uploadTone === "success" ? "text-mpesa" : "text-airtel"
            }`}
          >
            {uploadMessage}
          </p>
        )}
      </section>

      <section className="rounded-2xl border border-line bg-paper-raised px-4 py-4">
        <p className="text-sm font-medium text-ink">Sync SMS (local / Termux)</p>
        <p className="mt-1 text-xs text-ink-faint">
          Optional. Pull new M-Pesa / Airtel SMS via Termux:API on this phone.
          Requires the Termux:API app and SMS permission.
        </p>
        <button
          type="button"
          onClick={handleSync}
          disabled={syncing}
          className="mt-3 w-full rounded-full border border-line px-4 py-2.5 text-sm font-medium text-ink disabled:opacity-50"
        >
          {syncing ? "Syncing…" : "Sync SMS now"}
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
      </section>

      <section className="rounded-2xl border border-line bg-paper-raised px-4 py-4">
        <p className="text-sm font-medium text-ink">Data</p>
        <p className="mt-1 text-xs text-ink-faint">
          {data?.total
            ? `${data.total} transaction${data.total === 1 ? "" : "s"} in your ledger.`
            : "No transactions yet — upload a statement to begin."}
        </p>
      </section>
    </div>
  );
}
