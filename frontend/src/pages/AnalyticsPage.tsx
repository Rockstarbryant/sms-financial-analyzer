import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useApiData } from "../hooks/useApiData";
import { api } from "../services/api";
import { ErrorState, LoadingState, EmptyState } from "../components/StateViews";
import {
  formatCategory,
  formatMonthLabel,
  formatMoney,
  formatProvider,
} from "../services/format";

const INK = "#191B1D";
const MPESA = "#0B6E3C";
const AIRTEL = "#B21E24";
const CATEGORY_PALETTE = ["#0B6E3C", "#B21E24", "#C99A3B", "#5A5F66", "#3E7CB1", "#9A9E9E", "#7B4B94"];

export function AnalyticsPage() {
  const categories = useApiData(() => api.getCategoryBreakdown());
  const providers = useApiData(() => api.getProviderBreakdown());
  const monthly = useApiData(() => api.getMonthlyBreakdown());

  const anyLoading = categories.loading || providers.loading || monthly.loading;
  const firstError = categories.error || providers.error || monthly.error;

  if (anyLoading) return <LoadingState label="Crunching your numbers…" />;
  if (firstError)
    return (
      <ErrorState
        message={firstError}
        onRetry={() => {
          categories.refetch();
          providers.refetch();
          monthly.refetch();
        }}
      />
    );

  const hasAnyData =
    (categories.data?.length ?? 0) > 0 ||
    (providers.data?.length ?? 0) > 0 ||
    (monthly.data?.length ?? 0) > 0;

  if (!hasAnyData) {
    return (
      <EmptyState
        title="Nothing to analyze yet"
        description="Import data from the Dashboard or Settings tab to see charts here."
      />
    );
  }

  const categoryChartData = (categories.data ?? [])
    .map((c) => ({
      name: formatCategory(c.category),
      spent: c.total_out,
    }))
    .filter((c) => c.spent > 0);

  const providerChartData = (providers.data ?? []).map((p) => ({
    name: formatProvider(p.provider),
    "Money in": p.total_in,
    "Money out": p.total_out,
    fill: p.provider === "mpesa" ? MPESA : AIRTEL,
  }));

  const monthlyChartData = (monthly.data ?? []).map((m) => ({
    name: formatMonthLabel(m.month),
    Income: m.income,
    Spending: m.spending,
    Fees: m.fees,
  }));

  return (
    <div className="space-y-6">
      <Section title="Spending by category">
        {categoryChartData.length === 0 ? (
          <NoData />
        ) : (
          <div className="rounded-2xl border border-line bg-paper-raised p-3">
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={categoryChartData}
                  dataKey="spent"
                  nameKey="name"
                  innerRadius={45}
                  outerRadius={80}
                  paddingAngle={2}
                >
                  {categoryChartData.map((_, i) => (
                    <Cell key={i} fill={CATEGORY_PALETTE[i % CATEGORY_PALETTE.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => formatMoney(Number(v))} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </Section>

      <Section title="Money in vs out, by provider">
        {providerChartData.length === 0 ? (
          <NoData />
        ) : (
          <div className="rounded-2xl border border-line bg-paper-raised p-3">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={providerChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#DFDACC" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: INK }} />
                <YAxis tick={{ fontSize: 10, fill: "#9A9E9E" }} width={40} />
                <Tooltip formatter={(v) => formatMoney(Number(v))} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="Money in" fill={MPESA} radius={[4, 4, 0, 0]} />
                <Bar dataKey="Money out" fill={AIRTEL} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </Section>

      <Section title="Monthly income, spending & fees">
        {monthlyChartData.length === 0 ? (
          <NoData />
        ) : (
          <div className="rounded-2xl border border-line bg-paper-raised p-3">
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={monthlyChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#DFDACC" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: INK }} />
                <YAxis tick={{ fontSize: 10, fill: "#9A9E9E" }} width={40} />
                <Tooltip formatter={(v) => formatMoney(Number(v))} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="Income" fill={MPESA} radius={[4, 4, 0, 0]} />
                <Bar dataKey="Spending" fill={AIRTEL} radius={[4, 4, 0, 0]} />
                <Bar dataKey="Fees" fill="#C99A3B" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-ink-faint">
        {title}
      </p>
      {children}
    </section>
  );
}

function NoData() {
  return (
    <div className="rounded-2xl border border-dashed border-line px-4 py-6 text-center text-xs text-ink-faint">
      Not enough data yet.
    </div>
  );
}
