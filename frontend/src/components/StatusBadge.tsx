const STYLES: Record<string, { label: string; className: string }> = {
  pending: { label: "Running", className: "text-steel border-rule" },
  success: { label: "Passed", className: "text-ok border-ok/40" },
  partial: { label: "Partial result", className: "text-partial border-partial/40" },
  error: { label: "Failed", className: "text-fail border-fail/40" },
  rejected: { label: "Rejected", className: "text-partial border-partial/40" },
  cancelled: { label: "Cancelled", className: "text-steel border-rule" },
};

export function StatusBadge({ status }: { status: string }) {
  const style = STYLES[status] ?? { label: status, className: "text-steel border-rule" };
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium ${style.className}`}
    >
      {status === "pending" && (
        <span
          aria-hidden
          className="h-1.5 w-1.5 rounded-full bg-current motion-safe:animate-pulse"
        />
      )}
      {style.label}
    </span>
  );
}
