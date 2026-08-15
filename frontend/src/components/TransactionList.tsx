import type { Transaction } from "../types";
import {
  formatCategory,
  formatDate,
  formatProvider,
  formatSignedMoney,
} from "../services/format";

const PROVIDER_DOT: Record<string, string> = {
  mpesa: "bg-mpesa",
  airtel_money: "bg-airtel",
  unknown: "bg-ink-faint",
};

const CONFIDENCE_LABEL: Record<string, string> = {
  HIGH: "High confidence",
  MEDIUM: "Medium confidence",
  UNKNOWN: "Unverified",
};

interface TransactionRowProps {
  transaction: Transaction;
  onClick?: () => void;
}

export function TransactionRow({ transaction, onClick }: TransactionRowProps) {
  const positive = transaction.direction === "IN";
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center justify-between gap-3 border-b border-line/70 px-1 py-3 text-left last:border-b-0"
    >
      <div className="flex min-w-0 items-center gap-3">
        <span
          className={`h-2 w-2 shrink-0 rounded-full ${PROVIDER_DOT[transaction.provider]}`}
          aria-hidden
        />
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-ink">
            {transaction.counterparty ?? formatTransactionTypeFallback(transaction)}
          </p>
          <p className="truncate text-xs text-ink-faint">
            {formatDate(transaction.timestamp)} · {formatProvider(transaction.provider)} ·{" "}
            {formatCategory(transaction.category)}
          </p>
        </div>
      </div>
      <div className="shrink-0 text-right">
        <p
          className={`ledger-amount text-sm font-semibold ${
            positive ? "text-mpesa" : "text-ink"
          }`}
        >
          {formatSignedMoney(transaction.amount ?? 0, transaction.direction, transaction.currency)}
        </p>
        {transaction.confidence !== "HIGH" && (
          <p className="text-[10px] text-ink-faint">
            {CONFIDENCE_LABEL[transaction.confidence]}
          </p>
        )}
      </div>
    </button>
  );
}

function formatTransactionTypeFallback(transaction: Transaction): string {
  return formatCategory(transaction.category);
}

interface TransactionListProps {
  transactions: Transaction[];
  onSelect?: (transaction: Transaction) => void;
}

export function TransactionList({ transactions, onSelect }: TransactionListProps) {
  return (
    <div className="rounded-2xl border border-line bg-paper-raised px-3">
      {transactions.map((t) => (
        <TransactionRow key={t.id} transaction={t} onClick={() => onSelect?.(t)} />
      ))}
    </div>
  );
}
