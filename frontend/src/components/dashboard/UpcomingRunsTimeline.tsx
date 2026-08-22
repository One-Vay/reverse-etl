import { CalendarClock } from "lucide-react";
import { Link } from "react-router-dom";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { useUpcomingRuns } from "@/hooks/useSyncs";
import { cn } from "@/lib/utils";

const DAYS_AHEAD = 7;

interface DayChip {
  time: string;
  syncId: number;
  syncName: string;
  timestamp: Date;
}

interface DayColumn {
  date: Date;
  isToday: boolean;
  chips: DayChip[];
}

function buildColumns(
  upcoming: { sync_id: number; sync_name: string; occurrences: string[] }[],
): DayColumn[] {
  const now = new Date();
  const columns: DayColumn[] = Array.from({ length: DAYS_AHEAD }, (_, offset) => {
    const date = new Date(now);
    date.setDate(date.getDate() + offset);
    return { date, isToday: offset === 0, chips: [] };
  });

  for (const sync of upcoming) {
    for (const iso of sync.occurrences) {
      const timestamp = new Date(iso);
      if (Number.isNaN(timestamp.getTime())) continue;
      const dayOffset = Math.floor(
        (startOfDay(timestamp).getTime() - startOfDay(now).getTime()) / 86_400_000,
      );
      if (dayOffset < 0 || dayOffset >= DAYS_AHEAD) continue;
      columns[dayOffset].chips.push({
        time: timestamp.toLocaleTimeString(undefined, {
          hour: "2-digit",
          minute: "2-digit",
        }),
        syncId: sync.sync_id,
        syncName: sync.sync_name,
        timestamp,
      });
    }
  }

  for (const column of columns) {
    column.chips.sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
  }
  return columns;
}

function startOfDay(date: Date): Date {
  const copy = new Date(date);
  copy.setHours(0, 0, 0, 0);
  return copy;
}

/** Interactive 7-day calendar strip showing every active pipeline's
 * projected fire times, so a UI-only user can see what's about to run
 * without reading a cron expression or checking each pipeline one by one. */
export function UpcomingRunsTimeline() {
  const upcomingQuery = useUpcomingRuns(DAYS_AHEAD);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-1.5">
          <CalendarClock className="h-4 w-4" /> Upcoming runs
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          Every active pipeline's scheduled fires over the next {DAYS_AHEAD} days.
        </p>
      </CardHeader>
      <CardContent>
        {upcomingQuery.isLoading ? (
          <Skeleton className="h-40 w-full" />
        ) : !upcomingQuery.data || upcomingQuery.data.length === 0 ? (
          <EmptyState
            icon={CalendarClock}
            title="Nothing scheduled"
            description="Active pipelines will show their upcoming runs here."
          />
        ) : (
          <UpcomingGrid upcoming={upcomingQuery.data} />
        )}
      </CardContent>
    </Card>
  );
}

function UpcomingGrid({
  upcoming,
}: {
  upcoming: { sync_id: number; sync_name: string; occurrences: string[] }[];
}) {
  const columns = buildColumns(upcoming);

  return (
    <div className="grid grid-cols-1 gap-2 overflow-x-auto sm:grid-cols-7">
      {columns.map((column) => (
        <div
          key={column.date.toDateString()}
          className={cn(
            "flex min-h-[7rem] flex-col gap-1.5 rounded-md border p-2",
            column.isToday ? "border-primary/40 bg-primary/5" : "border-border",
          )}
        >
          <p
            className={cn(
              "text-[11px] font-medium",
              column.isToday ? "text-primary" : "text-muted-foreground",
            )}
          >
            {column.isToday
              ? "Today"
              : column.date.toLocaleDateString(undefined, {
                  weekday: "short",
                  day: "numeric",
                })}
          </p>
          <div className="flex flex-col gap-1">
            {column.chips.length === 0 ? (
              <p className="text-[11px] text-muted-foreground/60">—</p>
            ) : (
              column.chips.map((chip, index) => (
                <Link
                  key={`${chip.syncId}-${index}`}
                  to="/pipelines"
                  title={chip.timestamp.toLocaleString()}
                  className="truncate rounded border border-border bg-background px-1.5 py-0.5 text-[11px] transition-colors hover:border-primary/40 hover:bg-accent"
                >
                  <span className="font-mono text-muted-foreground">{chip.time}</span>{" "}
                  <span className="text-foreground">{chip.syncName}</span>
                </Link>
              ))
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
