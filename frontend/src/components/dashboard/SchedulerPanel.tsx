import { Play, Workflow } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import type { Sync } from "@/api/types";
import { Button, buttonClasses } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Switch } from "@/components/ui/Switch";
import { useRunSyncNow, useToggleSyncStatus } from "@/hooks/useSyncs";
import { formatRelativeTime, formatSchedule } from "@/lib/utils";

interface SchedulerPanelProps {
  syncs: Sync[];
}

export function SchedulerPanel({ syncs }: SchedulerPanelProps) {
  const toggleStatus = useToggleSyncStatus();
  const runNow = useRunSyncNow();
  const [runningId, setRunningId] = useState<number | null>(null);

  const handleRunNow = async (id: number) => {
    setRunningId(id);
    try {
      await runNow.mutateAsync(id);
    } catch {
      // Already surfaced to the user via the mutation's onError toast.
    } finally {
      setRunningId(null);
    }
  };

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle>Scheduler</CardTitle>
          <p className="text-xs text-muted-foreground">
            Toggle pipelines on or off without deleting their configuration.
          </p>
        </div>
        <Link to="/pipelines" className={buttonClasses("outline", "sm")}>
          Manage pipelines
        </Link>
      </CardHeader>
      <CardContent>
        {syncs.length === 0 ? (
          <EmptyState
            icon={Workflow}
            title="No pipelines configured"
            description="Create a sync pipeline to control its schedule from here."
          />
        ) : (
          <ul className="flex flex-col divide-y divide-border">
            {syncs.map((sync) => {
              const isActive = sync.status === "active";
              return (
                <li
                  key={sync.id}
                  className="flex items-center gap-3 py-3 first:pt-0 last:pb-0"
                >
                  <Switch
                    checked={isActive}
                    onCheckedChange={(checked) =>
                      toggleStatus.mutate({
                        id: sync.id,
                        status: checked ? "active" : "paused",
                      })
                    }
                    label={`Toggle schedule for ${sync.name}`}
                    disabled={sync.status === "inactive"}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{sync.name}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {formatSchedule(sync)} &middot; next run{" "}
                      {formatRelativeTime(sync.next_run)}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Run ${sync.name} now`}
                    onClick={() => handleRunNow(sync.id)}
                    loading={runningId === sync.id}
                  >
                    <Play className="h-4 w-4" />
                  </Button>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
