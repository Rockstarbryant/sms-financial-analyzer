import type { ReactNode } from "react";
import { formatMoney } from "../services/format";

interface SummaryCardProps {
  label: string;
  value: number | null;
  currency?: string;
  tone?: "neutral" | "positive" | "negative";
  helper?: string;
}

const TONE_CLASSES: Record<NonNullable<SummaryCardProps["tone"]>, string> = {
  neutral: "text-ink",
  positive: "text-mpesa",
  negative: "text-airtel",
};

export function SummaryCard({
  label,
  value,
  currency = "KES",
  tone = "neutral",
  helper,
}: SummaryCardProps) {
  return (
    <div className="rounded-2xl border border-line bg-paper-raised px-4 py-3">
      <p className="text-[11px] font-medium uppercase tracking-wide text-ink-faint">
        {label}
      </p>
      <p
        className={`ledger-amount mt-1 text-lg font-semibold ${TONE_CLASSES[tone]}`}
      >
        {formatMoney(value, currency)}
      </p>
      {helper && <p className="mt-0.5 text-[11px] text-ink-faint">{helper}</p>}
    </div>
  );
}

interface ReceiptHeroProps {
  balance: number | null;
  moneyIn: number;
  moneyOut: number;
  netCashFlow: number;
  currency?: string;
}

/**
 * The signature element: the top dashboard card rendered as a torn
 * receipt stub, with the running balance printed large in tabular
 * ledger digits and a perforated edge tying it to every other card
 * in the app.
 */
export function ReceiptHero({
  balance,
  moneyIn,
  moneyOut,
  netCashFlow,
  currency = "KES",
}: ReceiptHeroProps) {
  const netPositive = netCashFlow >= 0;
  return (
    <div className="receipt-card mb-4 px-5 pb-7 pt-5">
      <p className="text-[11px] font-medium uppercase tracking-wide text-ink-faint">
        Total balance
      </p>
      <p className="ledger-amount mt-1 text-3xl font-semibold text-ink">
        {formatMoney(balance, currency)}
      </p>

      <div className="mt-5 grid grid-cols-3 gap-3 border-t border-dashed border-line pt-4">
        <div>
          <p className="text-[10px] uppercase tracking-wide text-ink-faint">
            Money in
          </p>
          <p className="ledger-amount mt-0.5 text-sm font-medium text-mpesa">
            {formatMoney(moneyIn, currency)}
          </p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wide text-ink-faint">
            Money out
          </p>
          <p className="ledger-amount mt-0.5 text-sm font-medium text-ink">
            {formatMoney(moneyOut, currency)}
          </p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wide text-ink-faint">
            Net flow
          </p>
          <p
            className={`ledger-amount mt-0.5 text-sm font-medium ${
              netPositive ? "text-mpesa" : "text-airtel"
            }`}
          >
            {netPositive ? "+" : "-"}
            {formatMoney(Math.abs(netCashFlow), currency)}
          </p>
        </div>
      </div>
    </div>
  );
}

interface ProviderCardProps {
  name: string;
  accent: "mpesa" | "airtel";
  moneyIn: number;
  moneyOut: number;
  fees: number;
  currency?: string;
}

export function ProviderCard({
  name,
  accent,
  moneyIn,
  moneyOut,
  fees,
  currency = "KES",
}: ProviderCardProps) {
  const accentClasses =
    accent === "mpesa"
      ? { bar: "bg-mpesa", chip: "bg-mpesa-soft text-mpesa" }
      : { bar: "bg-airtel", chip: "bg-airtel-soft text-airtel" };
  const netFlow = moneyIn - moneyOut;

  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-paper-raised">
      <div className={`h-1 ${accentClasses.bar}`} />
      <div className="px-4 py-3">
        <div className="flex items-center justify-between">
          <p className="font-display text-sm font-semibold text-ink">
            {name}
          </p>
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${accentClasses.chip}`}
          >
            {netFlow >= 0 ? "Net positive" : "Net negative"}
          </span>
        </div>
        <dl className="mt-3 grid grid-cols-3 gap-2 text-xs">
          <Stat label="In" value={formatMoney(moneyIn, currency)} />
          <Stat label="Out" value={formatMoney(moneyOut, currency)} />
          <Stat label="Fees" value={formatMoney(fees, currency)} />
        </dl>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <dt className="text-[10px] uppercase tracking-wide text-ink-faint">
        {label}
      </dt>
      <dd className="ledger-amount mt-0.5 font-medium text-ink">{value}</dd>
    </div>
  );
}
