import { CheckCircle2, History, XCircle } from "lucide-react";
import { useMemo } from "react";

import type { Sync } from "@/api/types";
import { DemoDataBadge } from "@/components/dashboard/DemoDataBadge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { generateMockRuns } from "@/lib/mockRunHistory";
import { formatRelativeTime } from "@/lib/utils";

interface RunHistoryTableProps {
  syncs: Sync[];
}

export function RunHistoryTable({ syncs }: RunHistoryTableProps) {
  const runs = useMemo(() => generateMockRuns(syncs, 8), [syncs]);

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div className="flex items-center gap-2">
          <CardTitle>Recent pipeline runs</CardTitle>
          <DemoDataBadge />
        </div>
      </CardHeader>
      <CardContent>
        {runs.length === 0 ? (
          <EmptyState
            icon={History}
            title="No runs to show"
            description="Create a pipeline to see its run history here."
          />
        ) : (
          <div className="overflow-x-auto scrollbar-thin">
            <table className="w-full min-w-[520px] text-left text-sm">
              <thead>
                <tr className="text-xs text-muted-foreground">
                  <th className="pb-2 font-medium">Pipeline</th>
                  <th className="pb-2 font-medium">Status</th>
                  <th className="pb-2 font-medium">Started</th>
                  <th className="pb-2 font-medium">Duration</th>
                  <th className="pb-2 font-medium">Rows</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {runs.map((run) => (
                  <tr key={run.id}>
                    <td className="max-w-[180px] truncate py-2.5 pr-2 font-medium">
                      {run.syncName}
                    </td>
                    <td className="py-2.5 pr-2">
                      {run.outcome === "success" ? (
                        <span className="inline-flex items-center gap-1 text-success">
                          <CheckCircle2 className="h-3.5 w-3.5" /> Success
                        </span>
                      ) : (
                        <span
                          className="inline-flex items-center gap-1 text-destructive"
                          title={run.errorMessage}
                        >
                          <XCircle className="h-3.5 w-3.5" /> Failed
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 pr-2 text-muted-foreground">
                      {formatRelativeTime(run.startedAt)}
                    </td>
                    <td className="py-2.5 pr-2 text-muted-foreground">
                      {run.durationSeconds}s
                    </td>
                    <td className="py-2.5 text-muted-foreground">
                      {run.rowsSynced.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
