/**
 * The backend does not yet persist individual pipeline run history (only the
 * latest `last_run`/`next_run` timestamps on a Sync). Everything in this file
 * is placeholder/demo data for the dashboard's run-history table and trend
 * chart, clearly labelled as such in the UI. Replace with real API calls once
 * a run-history endpoint exists (e.g. GET /api/v1/syncs/{id}/runs).
 */

import type { Sync } from "@/api/types";

export type RunOutcome = "success" | "failed";

export interface MockRun {
  id: string;
  syncName: string;
  outcome: RunOutcome;
  startedAt: string;
  durationSeconds: number;
  rowsSynced: number;
  errorMessage?: string;
}

const MOCK_ERRORS = [
  "Connection to destination API timed out",
  "Rate limit exceeded (429) from CRM API",
  "Source column 'phone' violated NOT NULL constraint",
  "Authentication token expired",
];

/** Deterministic pseudo-random generator so the demo looks stable across renders. */
function seededRandom(seed: number) {
  let value = seed;
  return () => {
    value = (value * 9301 + 49297) % 233280;
    return value / 233280;
  };
}

export function generateMockRuns(syncs: Sync[], count = 24): MockRun[] {
  if (syncs.length === 0) return [];
  const random = seededRandom(42);
  const runs: MockRun[] = [];

  for (let i = 0; i < count; i++) {
    const sync = syncs[Math.floor(random() * syncs.length)];
    const outcome: RunOutcome = random() > 0.82 ? "failed" : "success";
    const hoursAgo = i * (random() * 2 + 1);
    const startedAt = new Date(Date.now() - hoursAgo * 60 * 60 * 1000).toISOString();

    runs.push({
      id: `demo-${sync.id}-${i}`,
      syncName: sync.name,
      outcome,
      startedAt,
      durationSeconds: Math.round(8 + random() * 240),
      rowsSynced: outcome === "success" ? Math.round(random() * 5000) : 0,
      errorMessage:
        outcome === "failed"
          ? MOCK_ERRORS[Math.floor(random() * MOCK_ERRORS.length)]
          : undefined,
    });
  }

  return runs.sort(
    (a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime(),
  );
}

export interface DailyRunStats {
  date: string;
  success: number;
  failed: number;
}

export function generateMockDailyStats(days = 14): DailyRunStats[] {
  const random = seededRandom(7);
  const stats: DailyRunStats[] = [];

  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(Date.now() - i * 24 * 60 * 60 * 1000);
    stats.push({
      date: date.toLocaleDateString("en-GB", { day: "2-digit", month: "short" }),
      success: Math.round(6 + random() * 18),
      failed: Math.round(random() * 3),
    });
  }

  return stats;
}
