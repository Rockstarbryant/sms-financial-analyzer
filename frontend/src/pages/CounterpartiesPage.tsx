import { useState } from "react";
import { useApiData } from "../hooks/useApiData";
import { api } from "../services/api";
import { ErrorState, LoadingState, EmptyState } from "../components/StateViews";
import { TransactionList } from "../components/TransactionList";
import { formatMoney } from "../services/format";

export function CounterpartiesPage() {
  const [selectedName, setSelectedName] = useState<string | null>(null);

  if (selectedName) {
    return (
      <CounterpartyDetail
        name={selectedName}
        onBack={() => setSelectedName(null)}
      />
    );
  }

  return <CounterpartyList onSelect={setSelectedName} />;
}

function CounterpartyList({ onSelect }: { onSelect: (name: string) => void }) {
  const { data, loading, error, refetch } = useApiData(() =>
    api.getCounterparties(),
  );

  if (loading) return <LoadingState label="Grouping transactions…" />;
  if (error) return <ErrorState message={error} onRetry={refetch} />;
  if (!data || data.length === 0) {
    return (
      <EmptyState
        title="No people or services yet"
        description="Once you have transactions, they'll be grouped here by who they're with."
      />
    );
  }

  const sorted = [...data].sort(
    (a, b) => b.money_sent + b.money_received - (a.money_sent + a.money_received),
  );

  return (
    <div className="rounded-2xl border border-line bg-paper-raised px-3">
      {sorted.map((c) => (
        <button
          key={c.counterparty}
          onClick={() => onSelect(c.counterparty)}
          className="flex w-full items-center justify-between gap-3 border-b border-line/70 px-1 py-3 text-left last:border-b-0"
        >
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-ink">
              {c.counterparty}
            </p>
            <p className="text-xs text-ink-faint">
              {c.transaction_count} transaction
              {c.transaction_count === 1 ? "" : "s"}
            </p>
          </div>
          <p
            className={`ledger-amount shrink-0 text-sm font-semibold ${
              c.net_flow >= 0 ? "text-mpesa" : "text-ink"
            }`}
          >
            {c.net_flow >= 0 ? "+" : "-"}
            {formatMoney(Math.abs(c.net_flow))}
          </p>
        </button>
      ))}
    </div>
  );
}

function CounterpartyDetail({
  name,
  onBack,
}: {
  name: string;
  onBack: () => void;
}) {
  const { data, loading, error, refetch } = useApiData(
    () => api.getCounterparty(name),
    [name],
  );

  return (
    <div>
      <button
        onClick={onBack}
        className="mb-4 flex items-center gap-1 text-sm font-medium text-ink-soft"
      >
        ← All people &amp; services
      </button>

      {loading && <LoadingState label="Loading…" />}
      {error && <ErrorState message={error} onRetry={refetch} />}

      {data && (
        <>
          <div className="receipt-card mb-6 px-5 pb-7 pt-5">
            <p className="font-display text-lg font-semibold text-ink">
              {data.counterparty}
            </p>
            <div className="mt-4 grid grid-cols-3 gap-3 border-t border-dashed border-line pt-4">
              <Stat label="Sent" value={formatMoney(data.money_sent)} />
              <Stat label="Received" value={formatMoney(data.money_received)} />
              <Stat
                label="Net"
                value={`${data.net_flow >= 0 ? "+" : "-"}${formatMoney(Math.abs(data.net_flow))}`}
                tone={data.net_flow >= 0 ? "positive" : "neutral"}
              />
            </div>
          </div>

          <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-ink-faint">
            History
          </p>
          <TransactionList transactions={data.transactions} />
        </>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: "neutral" | "positive";
}) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wide text-ink-faint">
        {label}
      </p>
      <p
        className={`ledger-amount mt-0.5 text-sm font-medium ${
          tone === "positive" ? "text-mpesa" : "text-ink"
        }`}
      >
        {value}
      </p>
    </div>
  );
}
