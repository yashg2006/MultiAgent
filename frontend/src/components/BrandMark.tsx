/** Three sources converging on one node — the orchestrator coordinating agents. */
export function BrandMark({ className = "h-7 w-7" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 28 28" fill="none" aria-hidden>
      <rect width="28" height="28" rx="8" fill="#14161C" />
      <circle cx="8" cy="8" r="2.1" fill="#8E86F5" />
      <circle cx="8" cy="20" r="2.1" fill="#5AC9A3" />
      <circle cx="8" cy="14" r="2.1" fill="#E8A54B" />
      <circle cx="20" cy="14" r="2.6" fill="#4A3AEC" />
      <path
        d="M10 8.2 17.6 13M10 14h7.4M10 19.8 17.6 15"
        stroke="#6B63E8"
        strokeWidth="1.3"
        strokeLinecap="round"
      />
    </svg>
  );
}
