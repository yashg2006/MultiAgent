const STYLES: Record<string, { label: string; className: string; dot: string }> = {
  pending: { label: "Queued", className: "bg-sunken text-muted", dot: "bg-faint" },
  running: { label: "Running", className: "bg-accent-soft text-accent-hover", dot: "bg-accent" },
  success: { label: "Passed", className: "bg-ok-soft text-ok", dot: "bg-ok" },
  partial: { label: "Partial result", className: "bg-warn-soft text-warn", dot: "bg-warn" },
  error: { label: "Failed", className: "bg-fail-soft text-fail", dot: "bg-fail" },
  rejected: { label: "Rejected", className: "bg-warn-soft text-warn", dot: "bg-warn" },
  cancelled: { label: "Cancelled", className: "bg-sunken text-muted", dot: "bg-faint" },
};

export function StatusBadge({ status }: { status: string }) {
  const style = STYLES[status] ?? {
    label: status,
    className: "bg-sunken text-muted",
    dot: "bg-faint",
  };
  const live = status === "pending" || status === "running";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-2xs font-medium tracking-tight ${style.className}`}
    >
      <span
        aria-hidden
        className={`h-1.5 w-1.5 rounded-full ${style.dot} ${live ? "motion-safe:animate-pulse" : ""}`}
      />
      {style.label}
    </span>
  );
}
