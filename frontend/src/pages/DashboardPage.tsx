import { Cable, CheckCircle2, Server, Workflow } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { RunHistoryTable } from "@/components/dashboard/RunHistoryTable";
import { SchedulerPanel } from "@/components/dashboard/SchedulerPanel";
import { StatsCharts } from "@/components/dashboard/StatsCharts";
import { Skeleton } from "@/components/ui/Skeleton";
import { StatCard } from "@/components/ui/StatCard";
import { useDestinations } from "@/hooks/useDestinations";
import { useSources } from "@/hooks/useSources";
import { useAllSyncRuns, useSyncs } from "@/hooks/useSyncs";

export function DashboardPage() {
  const sourcesQuery = useSources();
  const destinationsQuery = useDestinations();
  const syncsQuery = useSyncs();
  const runsQuery = useAllSyncRuns();

  const syncs = syncsQuery.data?.items ?? [];
  const runs = runsQuery.data?.items ?? [];
  const activeSyncs = syncs.filter((sync) => sync.status === "active").length;
  const isLoadingStats =
    sourcesQuery.isLoading || destinationsQuery.isLoading || syncsQuery.isLoading;

  return (
    <AppShell
      title="Dashboard"
      description="Overview of your connections, schedules, and pipeline activity."
    >
      {isLoadingStats ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-24 w-full" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Data sources"
            value={sourcesQuery.data?.total ?? 0}
            icon={Cable}
            hint="Connected databases"
          />
          <StatCard
            label="CRM destinations"
            value={destinationsQuery.data?.total ?? 0}
            icon={Server}
            hint="Connected CRMs"
          />
          <StatCard
            label="Sync pipelines"
            value={syncsQuery.data?.total ?? 0}
            icon={Workflow}
            hint="Configured pipelines"
          />
          <StatCard
            label="Active schedules"
            value={activeSyncs}
            icon={CheckCircle2}
            tone="success"
            hint={`out of ${syncs.length} pipeline${syncs.length === 1 ? "" : "s"}`}
          />
        </div>
      )}

      <div className="mt-4">
        <StatsCharts syncs={syncs} runs={runs} />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <SchedulerPanel syncs={syncs} />
        <RunHistoryTable runs={runs} isLoading={runsQuery.isLoading} />
      </div>
    </AppShell>
  );
}
