import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { Sync, SyncRun } from "@/api/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { useChartColors } from "@/lib/chartTheme";

interface StatsChartsProps {
  syncs: Sync[];
  runs: SyncRun[];
}

const TOOLTIP_WRAPPER_STYLE = { outline: "none" };
const DAYS_SHOWN = 14;

function dayKey(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
}

/** Buckets recent runs into one success/failed count per day, for the last
 * `DAYS_SHOWN` days — including days with zero runs, so the chart's x-axis
 * stays a continuous timeline rather than skipping quiet days. */
function bucketRunsByDay(runs: SyncRun[]): { date: string; success: number; failed: number }[] {
  const buckets = new Map<string, { success: number; failed: number }>();
  for (let i = DAYS_SHOWN - 1; i >= 0; i--) {
    const date = new Date();
    date.setDate(date.getDate() - i);
    buckets.set(dayKey(date.toISOString()), { success: 0, failed: 0 });
  }
  for (const run of runs) {
    const bucket = buckets.get(dayKey(run.started_at));
    if (!bucket) continue; // outside the shown window
    if (run.status === "success") bucket.success += 1;
    else if (run.status === "failed") bucket.failed += 1;
  }
  return [...buckets.entries()].map(([date, counts]) => ({ date, ...counts }));
}

export function StatsCharts({ syncs, runs }: StatsChartsProps) {
  const colors = useChartColors();
  const dailyStats = useMemo(() => bucketRunsByDay(runs), [runs]);

  const statusDistribution = useMemo(() => {
    const counts = { active: 0, paused: 0, inactive: 0 };
    for (const sync of syncs) counts[sync.status] += 1;
    return [
      { name: "Active", value: counts.active, color: colors.success },
      { name: "Paused", value: counts.paused, color: colors.warning },
      { name: "Inactive", value: counts.inactive, color: colors.muted },
    ].filter((entry) => entry.value > 0);
  }, [syncs, colors]);

  const tooltipContentStyle = {
    background: "hsl(var(--popover))",
    border: `1px solid hsl(var(--border))`,
    borderRadius: 8,
    fontSize: 12,
  };

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle>Runs over the last 14 days</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dailyStats} barCategoryGap={4}>
                <CartesianGrid vertical={false} stroke={colors.border} />
                <XAxis
                  dataKey="date"
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 11, fill: colors.muted }}
                  interval="preserveStartEnd"
                />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 11, fill: colors.muted }}
                  width={28}
                  allowDecimals={false}
                />
                <Tooltip
                  cursor={{ fill: "hsl(var(--accent))" }}
                  contentStyle={tooltipContentStyle}
                  wrapperStyle={TOOLTIP_WRAPPER_STYLE}
                />
                <Legend
                  iconType="circle"
                  iconSize={8}
                  wrapperStyle={{ fontSize: 12, color: colors.muted }}
                />
                <Bar
                  dataKey="success"
                  name="Succeeded"
                  stackId="runs"
                  fill={colors.success}
                  radius={[0, 0, 0, 0]}
                />
                <Bar
                  dataKey="failed"
                  name="Failed"
                  stackId="runs"
                  fill={colors.destructive}
                  radius={[3, 3, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Pipeline status</CardTitle>
        </CardHeader>
        <CardContent>
          {statusDistribution.length === 0 ? (
            <p className="flex h-64 items-center justify-center text-center text-sm text-muted-foreground">
              No pipelines yet.
            </p>
          ) : (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={statusDistribution}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={55}
                    outerRadius={80}
                    paddingAngle={3}
                  >
                    {statusDistribution.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} stroke="none" />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={tooltipContentStyle}
                    wrapperStyle={TOOLTIP_WRAPPER_STYLE}
                  />
                  <Legend
                    iconType="circle"
                    iconSize={8}
                    wrapperStyle={{ fontSize: 12, color: colors.muted }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
