import type {
  CategoryBreakdownItem,
  CounterpartyDetail,
  CounterpartySummary,
  DashboardResponse,
  DemoImportResponse,
  LoginPayload,
  MonthlyBreakdownItem,
  ProviderBreakdownItem,
  RegisterPayload,
  TokenResponse,
  Transaction,
  TransactionFilters,
  TransactionListResponse,
  User,
} from "../types";
import { getToken } from "./authStorage";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export class ApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };

  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers,
    });
  } catch {
    throw new ApiError(
      "Can't reach the backend. Make sure it's running at " + BASE_URL,
    );
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      // FastAPI validation errors return detail as an array
      if (Array.isArray(body.detail)) {
        detail = body.detail
          .map((d: { msg?: string }) => d.msg || JSON.stringify(d))
          .join("; ");
      } else {
        detail = body.detail || detail;
      }
    } catch {
      // response wasn't JSON -- fall back to statusText
    }
    throw new ApiError(detail, response.status);
  }

  return response.json() as Promise<T>;
}

function buildQuery(filters: TransactionFilters): string {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== "" && value !== null) {
      params.set(key, String(value));
    }
  });
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export const api = {
  health: () => request<{ status: string }>("/api/health"),

  // Auth
  register: (payload: RegisterPayload) =>
    request<TokenResponse>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  login: (payload: LoginPayload) =>
    request<TokenResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  me: () => request<User>("/api/auth/me"),

  // Data
  importDemoData: () =>
    request<DemoImportResponse>("/api/demo/import", { method: "POST" }),

  syncSms: () => request<DemoImportResponse>("/api/sync", { method: "POST" }),

  getDashboard: () => request<DashboardResponse>("/api/dashboard"),

  listTransactions: (filters: TransactionFilters = {}) =>
    request<TransactionListResponse>(
      `/api/transactions${buildQuery(filters)}`,
    ),

  getTransaction: (id: number) =>
    request<Transaction>(`/api/transactions/${id}`),

  getCategoryBreakdown: () =>
    request<CategoryBreakdownItem[]>("/api/analytics/categories"),

  getProviderBreakdown: () =>
    request<ProviderBreakdownItem[]>("/api/analytics/providers"),

  getMonthlyBreakdown: () =>
    request<MonthlyBreakdownItem[]>("/api/analytics/monthly"),

  getCounterparties: () =>
    request<CounterpartySummary[]>("/api/counterparties"),

  getCounterparty: (name: string) =>
    request<CounterpartyDetail>(
      `/api/counterparties/${encodeURIComponent(name)}`,
    ),
};
