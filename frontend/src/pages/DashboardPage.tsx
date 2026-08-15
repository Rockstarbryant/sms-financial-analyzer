import { useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { useApiData } from "../hooks/useApiData";
import { api } from "../services/api";
import { ReceiptHero, ProviderCard } from "../components/SummaryCards";
import { ErrorState, LoadingState } from "../components/StateViews";
import {
  formatCategory,
  formatMoney,
  formatProvider,
} from "../services/format";
import type { Transaction } from "../types";

type Period = "day" | "week" | "month" | "all";

function periodRange(period: Period): { start?: string; end?: string } {
  if (period === "all") return {};
  const end = new Date();
  const start = new Date();
  if (period === "day") {
    start.setHours(0, 0, 0, 0);
  } else if (period === "week") {
    start.setDate(start.getDate() - 7);
  } else if (period === "month") {
    start.setDate(1);
    start.setHours(0, 0, 0, 0);
  }
  return {
    start: start.toISOString(),
    end: end.toISOString(),
  };
}

function aggregateFromTransactions(items: Transaction[]) {
  let moneyIn = 0;
  let moneyOut = 0;
  let fees = 0;
  const byProvider: Record<
    string,
    { money_in: number; money_out: number; fees: number }
  > = {
    mpesa: { money_in: 0, money_out: 0, fees: 0 },
    airtel_money: { money_in: 0, money_out: 0, fees: 0 },
  };
  const byCategory: Record<string, { total_out: number; count: number }> = {};
  const sentTo: Record<
    string,
    { amount: number; count: number }
  > = {};
  const receivedFrom: Record<
    string,
    { amount: number; count: number }
  > = {};

  for (const t of items) {
    const amount = t.amount ?? 0;
    const fee = t.fee ?? 0;
    fees += fee;

    if (t.direction === "IN") moneyIn += amount;
    else moneyOut += amount;

    const p = byProvider[t.provider] ?? {
      money_in: 0,
      money_out: 0,
      fees: 0,
    };
    if (t.direction === "IN") p.money_in += amount;
    else p.money_out += amount;
    p.fees += fee;
    byProvider[t.provider] = p;

    if (t.direction === "OUT") {
      const cat = byCategory[t.category] ?? { total_out: 0, count: 0 };
      cat.total_out += amount;
      cat.count += 1;
      byCategory[t.category] = cat;

      if (t.counterparty) {
        const row = sentTo[t.counterparty] ?? { amount: 0, count: 0 };
        row.amount += amount;
        row.count += 1;
        sentTo[t.counterparty] = row;
      }
    } else if (t.counterparty) {
      const row = receivedFrom[t.counterparty] ?? { amount: 0, count: 0 };
      row.amount += amount;
      row.count += 1;
      receivedFrom[t.counterparty] = row;
    }
  }

  const topSent = Object.entries(sentTo)
    .map(([name, v]) => ({ name, ...v }))
    .sort((a, b) => b.amount - a.amount)
    .slice(0, 8);

  const topReceived = Object.entries(receivedFrom)
    .map(([name, v]) => ({ name, ...v }))
    .sort((a, b) => b.amount - a.amount)
    .slice(0, 8);

  const categories = Object.entries(byCategory)
    .map(([category, v]) => ({ category, ...v }))
    .sort((a, b) => b.total_out - a.total_out);

  return {
    moneyIn,
    moneyOut,
    fees,
    net: moneyIn - moneyOut,
    byProvider,
    topSent,
    topReceived,
    categories,
  };
}

const PERIOD_LABELS: { id: Period; label: string }[] = [
  { id: "day", label: "Today" },
  { id: "week", label: "7 days" },
  { id: "month", label: "This month" },
  { id: "all", label: "All time" },
];

export function DashboardPage() {
  const [period, setPeriod] = useState<Period>("all");
  const range = useMemo(() => periodRange(period), [period]);

  const dashboard = useApiData(() => api.getDashboard());
  const transactions = useApiData(
    () =>
      api.listTransactions({
        limit: 500,
        start_date: range.start,
        end_date: range.end,
      }),
    // re-fetch when period changes
    [period],
  );

  if (dashboard.loading && !dashboard.data) {
    return <LoadingState label="Loading your dashboard…" />;
  }
  if (dashboard.error && !dashboard.data) {
    return (
      <ErrorState message={dashboard.error} onRetry={dashboard.refetch} />
    );
  }
  if (!dashboard.data) return null;

const dashboardData = dashboard.data;

const items = transactions.data?.items ?? [];
  const agg = aggregateFromTransactions(items);
  const usePeriodTotals = period !== "all" && !transactions.loading;

  const moneyIn = usePeriodTotals ? agg.moneyIn : dashboardData.money_in;
const moneyOut = usePeriodTotals ? agg.moneyOut : dashboardData.money_out;
const net = usePeriodTotals ? agg.net : dashboardData.net_cash_flow;
const fees = usePeriodTotals ? agg.fees : dashboardData.fees;
const balance = period === "all" ? dashboardData.total_balance : null;

  const providerOrder = ["mpesa", "airtel_money"] as const;

  return (
    <div className="space-y-6">
      {/* Period filter */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {PERIOD_LABELS.map((p) => (
          <button
            key={p.id}
            type="button"
            onClick={() => setPeriod(p.id)}
            className={`shrink-0 rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
              period === p.id
                ? "bg-mpesa text-white"
                : "border border-line bg-paper-raised text-ink-soft"
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      <ReceiptHero
        balance={balance}
        moneyIn={moneyIn}
        moneyOut={moneyOut}
        netCashFlow={net}
      />
      {period !== "all" && (
        <p className=" -mt-3 text-[11px] text-ink-faint">
          Totals for selected period
          {transactions.loading ? " · updating…" : ""}. Balance is always
          all-time.
        </p>
      )}

      {/* Providers — always show both */}
      <section>
        <SectionTitle>By provider</SectionTitle>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {providerOrder.map((provider) => {
            const fromDash = dashboardData.providers[provider];
            const fromAgg = agg.byProvider[provider];
            const summary = usePeriodTotals
              ? fromAgg
              : fromDash ?? { money_in: 0, money_out: 0, fees: 0 };
            return (
              <ProviderCard
                key={provider}
                name={formatProvider(provider)}
                accent={provider === "mpesa" ? "mpesa" : "airtel"}
                moneyIn={summary.money_in}
                moneyOut={summary.money_out}
                fees={summary.fees}
              />
            );
          })}
        </div>
      </section>

      {/* Spending by service / category */}
      <section>
        <div className="mb-2 flex items-center justify-between">
          <SectionTitle className="mb-0">Spent by service</SectionTitle>
          <Link to="/analytics" className="text-[11px] font-medium text-mpesa">
            Charts
          </Link>
        </div>
        {transactions.loading && items.length === 0 ? (
          <p className="text-sm text-ink-faint">Loading…</p>
        ) : agg.categories.length === 0 ? (
          <EmptyHint text="No outgoing payments in this period." />
        ) : (
          <div className="overflow-hidden rounded-2xl border border-line bg-paper-raised">
            {agg.categories.map((c) => (
              <div
                key={c.category}
                className="flex items-center justify-between border-b border-line/70 px-4 py-3 last:border-b-0"
              >
                <div>
                  <p className="text-sm font-medium text-ink">
                    {formatCategory(c.category)}
                  </p>
                  <p className="text-[11px] text-ink-faint">
                    {c.count} payment{c.count === 1 ? "" : "s"}
                  </p>
                </div>
                <p className="ledger-amount text-sm font-semibold text-ink">
                  {formatMoney(c.total_out)}
                </p>
              </div>
            ))}
          </div>
        )}
        <p className="mt-2 text-[11px] text-ink-faint">
          Categories come from SMS type (airtime, bundles, paybill/till
          payments, transfers, withdrawals). KPLC and other till names appear
          under People when the SMS includes them.
        </p>
      </section>

      {/* Top people sent to */}
      <section>
        <div className="mb-2 flex items-center justify-between">
          <SectionTitle className="mb-0">Sent to</SectionTitle>
          <Link
            to="/counterparties"
            className="text-[11px] font-medium text-mpesa"
          >
            See all
          </Link>
        </div>
        {agg.topSent.length === 0 ? (
          <EmptyHint text="No sends in this period." />
        ) : (
          <PersonList
            rows={agg.topSent}
            tone="out"
          />
        )}
      </section>

      {/* Top people received from */}
      <section>
        <div className="mb-2 flex items-center justify-between">
          <SectionTitle className="mb-0">Received from</SectionTitle>
          <Link
            to="/counterparties"
            className="text-[11px] font-medium text-mpesa"
          >
            See all
          </Link>
        </div>
        {agg.topReceived.length === 0 ? (
          <EmptyHint text="No receipts in this period." />
        ) : (
          <PersonList rows={agg.topReceived} tone="in" />
        )}
      </section>

      {/* Fees */}
      <section>
        <SectionTitle>Fees paid</SectionTitle>
        <div className="rounded-2xl border border-line bg-paper-raised px-4 py-3">
          <p className="ledger-amount text-lg font-semibold text-ink">
            {formatMoney(fees)}{" "}
            <span className="text-sm font-normal text-ink-faint">
              {period === "all" ? "all time" : "this period"}
            </span>
          </p>
        </div>
      </section>
    </div>
  );
}

function SectionTitle({
  children,
  className = "mb-2",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <p
      className={`text-[11px] font-medium uppercase tracking-wide text-ink-faint ${className}`}
    >
      {children}
    </p>
  );
}

function EmptyHint({ text }: { text: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-line px-4 py-4 text-sm text-ink-faint">
      {text}
    </div>
  );
}

function PersonList({
  rows,
  tone,
}: {
  rows: { name: string; amount: number; count: number }[];
  tone: "in" | "out";
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-paper-raised">
      {rows.map((r) => (
        <div
          key={r.name}
          className="flex items-center justify-between gap-3 border-b border-line/70 px-4 py-3 last:border-b-0"
        >
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-ink">{r.name}</p>
            <p className="text-[11px] text-ink-faint">
              {r.count} tx
            </p>
          </div>
          <p
            className={`ledger-amount shrink-0 text-sm font-semibold ${
              tone === "in" ? "text-mpesa" : "text-ink"
            }`}
          >
            {tone === "in" ? "+" : "-"}
            {formatMoney(r.amount)}
          </p>
        </div>
      ))}
    </div>
  );
}
