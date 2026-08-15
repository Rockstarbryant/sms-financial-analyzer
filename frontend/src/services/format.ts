export function formatMoney(amount: number | null, currency = "KES"): string {
  if (amount === null || amount === undefined) return "—";
  const formatted = Math.abs(amount).toLocaleString("en-KE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${currency === "KES" ? "Ksh" : currency} ${formatted}`;
}

export function formatSignedMoney(
  amount: number,
  direction: "IN" | "OUT",
  currency = "KES",
): string {
  const sign = direction === "IN" ? "+" : "-";
  return `${sign}${formatMoney(amount, currency)}`;
}

export function formatDate(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleDateString("en-KE", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function formatDateTime(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString("en-KE", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatMonthLabel(monthKey: string): string {
  // monthKey is "YYYY-MM"
  const [year, month] = monthKey.split("-");
  const date = new Date(Number(year), Number(month) - 1, 1);
  return date.toLocaleDateString("en-KE", { month: "short", year: "numeric" });
}

const CATEGORY_LABELS: Record<string, string> = {
  transfer: "Transfers",
  bundle: "Bundles",
  airtime: "Airtime",
  payment: "Payments",
  withdrawal: "Withdrawals",
  deposit: "Deposits",
  other: "Other",
};

export function formatCategory(category: string): string {
  return CATEGORY_LABELS[category] ?? category;
}

const PROVIDER_LABELS: Record<string, string> = {
  mpesa: "M-Pesa",
  airtel_money: "Airtel Money",
  unknown: "Unknown",
};

export function formatProvider(provider: string): string {
  return PROVIDER_LABELS[provider] ?? provider;
}

const TYPE_LABELS: Record<string, string> = {
  received: "Received",
  sent: "Sent",
  payment: "Payment",
  bundle: "Bundle",
  airtime: "Airtime",
  withdrawal: "Withdrawal",
  deposit: "Deposit",
  reversal: "Reversal",
  other: "Other",
};

export function formatTransactionType(type: string): string {
  return TYPE_LABELS[type] ?? type;
}
