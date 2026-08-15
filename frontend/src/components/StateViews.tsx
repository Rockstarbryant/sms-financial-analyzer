interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="rounded-2xl border border-airtel/20 bg-airtel-soft px-5 py-6 text-center">
      <p className="font-display text-sm font-medium text-airtel">
        Couldn't load this
      </p>
      <p className="mt-1 text-sm text-ink-soft">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 rounded-full bg-ink px-4 py-2 text-sm font-medium text-paper active:opacity-80"
        >
          Try again
        </button>
      )}
    </div>
  );
}

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-ink-faint">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-line border-t-ink" />
      <p className="text-sm">{label}</p>
    </div>
  );
}

interface EmptyStateProps {
  title: string;
  description: string;
  action?: React.ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="rounded-2xl border border-dashed border-line bg-paper-raised px-6 py-10 text-center">
      <p className="font-display text-base font-medium text-ink">{title}</p>
      <p className="mx-auto mt-1 max-w-xs text-sm text-ink-soft">
        {description}
      </p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
