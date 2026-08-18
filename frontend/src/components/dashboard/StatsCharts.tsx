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

import type { Sync } from "@/api/types";
import { DemoDataBadge } from "@/components/dashboard/DemoDataBadge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { useChartColors } from "@/lib/chartTheme";
import { generateMockDailyStats } from "@/lib/mockRunHistory";

interface StatsChartsProps {
  syncs: Sync[];
}

const TOOLTIP_WRAPPER_STYLE = { outline: "none" };

export function StatsCharts({ syncs }: StatsChartsProps) {
  const colors = useChartColors();
  const dailyStats = useMemo(() => generateMockDailyStats(14), []);

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
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <div className="flex items-center gap-2">
            <CardTitle>Runs over the last 14 days</CardTitle>
            <DemoDataBadge />
          </div>
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
