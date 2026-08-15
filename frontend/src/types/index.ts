export type Direction = "IN" | "OUT";

export type TransactionType =
  | "received"
  | "sent"
  | "payment"
  | "bundle"
  | "airtime"
  | "withdrawal"
  | "deposit"
  | "reversal"
  | "other";

export type Category =
  | "transfer"
  | "bundle"
  | "airtime"
  | "payment"
  | "withdrawal"
  | "deposit"
  | "other";

export type Confidence = "HIGH" | "MEDIUM" | "UNKNOWN";

export type Provider = "mpesa" | "airtel_money" | "unknown";

export interface Transaction {
  id: number;
  provider: Provider;
  direction: Direction;
  transaction_type: TransactionType;
  category: Category;
  amount: number | null;
  fee: number | null;
  balance: number | null;
  counterparty: string | null;
  counterparty_phone: string | null;
  transaction_id: string | null;
  timestamp: string;
  currency: string;
  confidence: Confidence;
  created_at: string;
  updated_at: string;
}

export interface TransactionListResponse {
  items: Transaction[];
  total: number;
  limit: number;
  offset: number;
}

export interface DemoImportResponse {
  scanned: number;
  recognized: number;
  inserted: number;
  duplicates: number;
  unknown: number;
}

export interface ProviderSummary {
  money_in: number;
  money_out: number;
  fees: number;
  net_flow: number;
}

export interface DashboardResponse {
  total_balance: number | null;
  money_in: number;
  money_out: number;
  fees: number;
  net_cash_flow: number;
  providers: Record<string, ProviderSummary>;
}

export interface CategoryBreakdownItem {
  category: Category;
  total_in: number;
  total_out: number;
  count: number;
}

export interface ProviderBreakdownItem {
  provider: Provider;
  total_in: number;
  total_out: number;
  fees: number;
  count: number;
}

export interface MonthlyBreakdownItem {
  month: string;
  income: number;
  spending: number;
  fees: number;
  net: number;
}

export interface CounterpartySummary {
  counterparty: string;
  money_sent: number;
  money_received: number;
  transaction_count: number;
  net_flow: number;
}

export interface CounterpartyDetail extends CounterpartySummary {
  transactions: Transaction[];
}

export interface TransactionFilters {
  provider?: string;
  category?: string;
  direction?: string;
  search?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}

// --- Auth / cloud multi-user ---

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}
