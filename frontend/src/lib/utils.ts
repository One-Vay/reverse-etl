import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge conditional class names, resolving conflicting Tailwind utilities
 * (e.g. a passed-in "flex-row" correctly overrides a default "flex-col"). */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** Format an ISO date string for display, e.g. "17 Aug 2026, 14:05". */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

/** Format an ISO date string as a relative time, e.g. "3 minutes ago". */
export function formatRelativeTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";

  const diffMs = date.getTime() - Date.now();
  const diffSeconds = Math.round(diffMs / 1000);
  const divisions: [Intl.RelativeTimeFormatUnit, number][] = [
    ["year", 60 * 60 * 24 * 365],
    ["month", 60 * 60 * 24 * 30],
    ["day", 60 * 60 * 24],
    ["hour", 60 * 60],
    ["minute", 60],
    ["second", 1],
  ];
  const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

  for (const [unit, secondsInUnit] of divisions) {
    if (Math.abs(diffSeconds) >= secondsInUnit || unit === "second") {
      return rtf.format(Math.round(diffSeconds / secondsInUnit), unit);
    }
  }
  return "—";
}

/** Extract a human-readable message from an unknown error value. */
export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  return "Something went wrong. Please try again.";
}

/** Describe a sync's interval schedule for display, e.g. "Every 6 hours" or
 * "Daily at 09:00". */
export function formatSchedule(sync: {
  interval_value: number;
  interval_unit: "hours" | "days";
  run_at_time: string | null;
}): string {
  if (sync.interval_unit === "hours") {
    return sync.interval_value === 1 ? "Every hour" : `Every ${sync.interval_value} hours`;
  }
  const time = sync.run_at_time ?? "09:00";
  return sync.interval_value === 1
    ? `Daily at ${time}`
    : `Every ${sync.interval_value} days at ${time}`;
}

/** Title-case a snake_case or lowercase identifier, e.g. "click_house" -> "Click House". */
export function titleCase(value: string): string {
  return value
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(" ");
}
