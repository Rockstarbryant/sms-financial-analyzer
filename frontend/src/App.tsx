import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { DashboardPage } from "./pages/DashboardPage";
import { TransactionsPage } from "./pages/TransactionsPage";
import { CounterpartiesPage } from "./pages/CounterpartiesPage";
import { SettingsPage } from "./pages/SettingsPage";
import { LoginPage } from "./pages/LoginPage";
import { Onboarding } from "./components/Onboarding";
import { useApiData } from "./hooks/useApiData";
import { api } from "./services/api";
import { ErrorState, LoadingState } from "./components/StateViews";
import { useAuth } from "./context/AuthContext";

// Analytics pulls in recharts, the heaviest dependency in the app, and is
// only needed on one route -- lazy-load it so the initial bundle (and
// first paint on a phone) stays lean.
const AnalyticsPage = lazy(() =>
  import("./pages/AnalyticsPage").then((m) => ({ default: m.AnalyticsPage })),
);

function MainApp() {
  const { data, loading, error, refetch } = useApiData(() =>
    api.listTransactions({ limit: 1 }),
  );

  if (loading) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-paper">
        <LoadingState label="Opening your ledger…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-paper px-5">
        <ErrorState message={error} onRetry={refetch} />
      </div>
    );
  }

  const hasData = (data?.total ?? 0) > 0;

  if (!hasData) {
    return (
      <div className="mx-auto min-h-dvh max-w-lg bg-paper px-5 sm:max-w-2xl">
        <Onboarding onImported={refetch} />
      </div>
    );
  }

  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/transactions" element={<TransactionsPage />} />
        <Route
          path="/analytics"
          element={
            <Suspense fallback={<LoadingState label="Loading analytics…" />}>
              <AnalyticsPage />
            </Suspense>
          }
        />
        <Route path="/counterparties" element={<CounterpartiesPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AppShell>
  );
}

export default function App() {
  const { loading: authLoading } = useAuth();

  if (authLoading) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-paper">
        <LoadingState label="Checking session…" />
      </div>
    );
  }

  // Auth is optional:
  // - Signed in  → cloud-scoped data (JWT sent automatically)
  // - Signed out → local/demo data (Termux or sample fixtures)
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/*" element={<MainApp />} />
    </Routes>
  );
}
