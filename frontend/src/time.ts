/**
 * The API stores UTC timestamps in SQLite, which drops the timezone, so they
 * arrive without a "Z" suffix. Browsers would parse those as local time, so
 * zone-less timestamps are treated as UTC here.
 */
export function parseApiTime(iso: string): Date {
  const hasZone = /([zZ]|[+-]\d{2}:?\d{2})$/.test(iso);
  return new Date(hasZone ? iso : `${iso}Z`);
}

export function formatApiTime(iso: string): string {
  const date = parseApiTime(iso);
  return Number.isNaN(date.getTime())
    ? ""
    : date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}
