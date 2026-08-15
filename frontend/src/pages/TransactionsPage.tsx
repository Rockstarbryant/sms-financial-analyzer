import { useState } from "react";
import { useApiData } from "../hooks/useApiData";
import { api } from "../services/api";
import { TransactionList } from "../components/TransactionList";
import { ErrorState, LoadingState, EmptyState } from "../components/StateViews";
import type { Transaction, TransactionFilters } from "../types";
import {
  formatCategory,
  formatDate,
  formatMoney,
  formatProvider,
  formatTransactionType,
} from "../services/format";

const PAGE_SIZE = 20;

const PROVIDER_OPTIONS = [
  { value: "", label: "All providers" },
  { value: "mpesa", label: "M-Pesa" },
  { value: "airtel_money", label: "Airtel Money" },
];

const CATEGORY_OPTIONS = [
  { value: "", label: "All categories" },
  { value: "transfer", label: "Transfers" },
  { value: "bundle", label: "Bundles" },
  { value: "airtime", label: "Airtime" },
  { value: "payment", label: "Payments" },
  { value: "withdrawal", label: "Withdrawals" },
  { value: "deposit", label: "Deposits" },
  { value: "other", label: "Other" },
];

const DIRECTION_OPTIONS = [
  { value: "", label: "In & out" },
  { value: "IN", label: "Money in" },
  { value: "OUT", label: "Money out" },
];

export function TransactionsPage() {
  const [search, setSearch] = useState("");
  const [provider, setProvider] = useState("");
  const [category, setCategory] = useState("");
  const [direction, setDirection] = useState("");
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<Transaction | null>(null);

  const filters: TransactionFilters = {
    search: search || undefined,
    provider: provider || undefined,
    category: category || undefined,
    direction: direction || undefined,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  };

  const { data, loading, error, refetch } = useApiData(
    () => api.listTransactions(filters),
    [search, provider, category, direction, page],
  );

  function resetToFirstPage<T>(setter: (v: T) => void) {
    return (value: T) => {
      setter(value);
      setPage(0);
    };
  }

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div>
      <div className="space-y-2">
        <input
          type="search"
          value={search}
          onChange={(e) => resetToFirstPage(setSearch)(e.target.value)}
          placeholder="Search by counterparty…"
          className="w-full rounded-full border border-line bg-paper-raised px-4 py-2.5 text-sm text-ink placeholder:text-ink-faint focus:border-ink"
        />
        <div className="flex gap-2 overflow-x-auto pb-1">
          <Select
            value={provider}
            onChange={resetToFirstPage(setProvider)}
            options={PROVIDER_OPTIONS}
          />
          <Select
            value={category}
            onChange={resetToFirstPage(setCategory)}
            options={CATEGORY_OPTIONS}
          />
          <Select
            value={direction}
            onChange={resetToFirstPage(setDirection)}
            options={DIRECTION_OPTIONS}
          />
        </div>
      </div>

      <div className="mt-4">
        {loading && <LoadingState label="Loading transactions…" />}
        {error && <ErrorState message={error} onRetry={refetch} />}
        {!loading && !error && data && data.items.length === 0 && (
          <EmptyState
            title="No transactions match"
            description="Try clearing a filter or searching a different name."
          />
        )}
        {!loading && !error && data && data.items.length > 0 && (
          <>
            <TransactionList
              transactions={data.items}
              onSelect={setSelected}
            />
            <div className="mt-4 flex items-center justify-between text-xs text-ink-faint">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="rounded-full border border-line px-3 py-1.5 disabled:opacity-40"
              >
                Previous
              </button>
              <span>
                Page {page + 1} of {Math.max(1, totalPages)} · {data.total}{" "}
                total
              </span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={page + 1 >= totalPages}
                className="rounded-full border border-line px-3 py-1.5 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </>
        )}
      </div>

      {selected && (
        <TransactionDetailSheet
          transaction={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}

function Select({
  value,
  onChange,
  options,
}: {
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="shrink-0 rounded-full border border-line bg-paper-raised px-3 py-1.5 text-xs text-ink-soft"
    >
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}

function TransactionDetailSheet({
  transaction,
  onClose,
}: {
  transaction: Transaction;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-30 flex items-end bg-ink/40 sm:items-center sm:justify-center"
      onClick={onClose}
    >
      <div
        className="w-full max-w-sm rounded-t-2xl bg-paper-raised px-5 pb-8 pt-5 sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mx-auto mb-4 h-1 w-10 rounded-full bg-line sm:hidden" />
        <p className="font-display text-base font-semibold text-ink">
          {transaction.counterparty ?? formatCategory(transaction.category)}
        </p>
        <p className="ledger-amount mt-1 text-2xl font-semibold text-ink">
          {formatMoney(transaction.amount, transaction.currency)}
        </p>

        <dl className="mt-5 space-y-2.5 text-sm">
          <Row label="Date" value={formatDate(transaction.timestamp)} />
          <Row label="Provider" value={formatProvider(transaction.provider)} />
          <Row label="Type" value={formatTransactionType(transaction.transaction_type)} />
          <Row label="Category" value={formatCategory(transaction.category)} />
          <Row
            label="Direction"
            value={transaction.direction === "IN" ? "Money in" : "Money out"}
          />
          {transaction.fee !== null && (
            <Row label="Fee" value={formatMoney(transaction.fee, transaction.currency)} />
          )}
          {transaction.balance !== null && (
            <Row
              label="Balance after"
              value={formatMoney(transaction.balance, transaction.currency)}
            />
          )}
          {transaction.transaction_id && (
            <Row label="Transaction ID" value={transaction.transaction_id} />
          )}
          <Row label="Confidence" value={transaction.confidence} />
        </dl>

        <button
          onClick={onClose}
          className="mt-6 w-full rounded-full border border-line py-2.5 text-sm font-medium text-ink-soft"
        >
          Close
        </button>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-line/60 pb-2.5">
      <dt className="text-ink-faint">{label}</dt>
      <dd className="ledger-amount font-medium text-ink">{value}</dd>
    </div>
  );
}
