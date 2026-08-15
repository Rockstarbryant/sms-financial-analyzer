import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: HomeIcon },
  { to: "/transactions", label: "Transactions", icon: ListIcon },
  { to: "/analytics", label: "Analytics", icon: ChartIcon },
  { to: "/counterparties", label: "People", icon: PeopleIcon },
  { to: "/settings", label: "Settings", icon: GearIcon },
];

export function AppShell({ children }: { children: ReactNode }) {
  const { isAuthenticated, user } = useAuth();

  return (
    <div className="mx-auto flex min-h-dvh max-w-lg flex-col bg-paper pb-20 sm:max-w-2xl">
      <header className="sticky top-0 z-10 flex items-center justify-between border-b border-line bg-paper/95 px-5 py-4 backdrop-blur">
        <div>
          <p className="font-display text-lg font-semibold tracking-tight text-ink">
            Ledger
          </p>
          <p className="text-xs text-ink-faint">
            {isAuthenticated
              ? user?.email ?? "Cloud account"
              : "Local M-Pesa & Airtel Money tracker"}
          </p>
        </div>
        <span className="rounded-full border border-line bg-paper-raised px-3 py-1 text-[11px] font-medium text-ink-soft">
          {isAuthenticated ? "Cloud" : "On this device"}
        </span>
      </header>

      <main className="flex-1 px-5 py-5">{children}</main>

      <nav className="fixed inset-x-0 bottom-0 z-20 mx-auto flex max-w-lg justify-around border-t border-line bg-paper-raised/95 px-2 py-2 backdrop-blur sm:max-w-2xl">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex flex-col items-center gap-1 rounded-xl px-3 py-1.5 text-[11px] font-medium transition-colors ${
                isActive
                  ? "text-mpesa"
                  : "text-ink-faint hover:text-ink-soft"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon active={isActive} />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

type IconProps = { active?: boolean };

function iconStroke(active?: boolean) {
  return active ? "#0B6E3C" : "#9A9E9E";
}

function HomeIcon({ active }: IconProps) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <path
        d="M4 11.5 12 4l8 7.5M6 10v9a1 1 0 0 0 1 1h3v-5h4v5h3a1 1 0 0 0 1-1v-9"
        stroke={iconStroke(active)}
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ListIcon({ active }: IconProps) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <path
        d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01"
        stroke={iconStroke(active)}
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

function ChartIcon({ active }: IconProps) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <path
        d="M4 19V5M4 19h16M8 16v-5M12 16V8M16 16v-3"
        stroke={iconStroke(active)}
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function PeopleIcon({ active }: IconProps) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <path
        d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"
        stroke={iconStroke(active)}
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function GearIcon({ active }: IconProps) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <path
        d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"
        stroke={iconStroke(active)}
        strokeWidth="1.8"
      />
      <path
        d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9c.2.6.7 1 1.5 1.1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z"
        stroke={iconStroke(active)}
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
