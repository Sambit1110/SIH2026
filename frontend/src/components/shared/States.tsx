import { AlertTriangle, Inbox, Loader2 } from "lucide-react";

export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-[var(--text-muted)]">
      <Loader2 className="animate-spin text-[var(--accent)]" size={22} />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function ErrorState({ message = "Something went wrong.", onRetry }: { message?: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
      <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--critical-soft)] text-[var(--critical)]">
        <AlertTriangle size={20} />
      </div>
      <p className="text-sm text-[var(--text)] max-w-sm">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="text-xs text-[var(--accent)] hover:underline">
          Try again
        </button>
      )}
    </div>
  );
}

export function EmptyState({
  title = "Nothing here yet",
  description,
  icon: Icon = Inbox,
  action,
}: {
  title?: string;
  description?: string;
  icon?: React.ComponentType<{ size?: number; className?: string }>;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
      <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--surface-active)] text-[var(--text-faint)]">
        <Icon size={20} />
      </div>
      <div>
        <p className="text-sm font-medium text-[var(--text)]">{title}</p>
        {description && <p className="text-xs text-[var(--text-muted)] mt-1 max-w-sm">{description}</p>}
      </div>
      {action}
    </div>
  );
}
