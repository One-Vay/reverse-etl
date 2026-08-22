import { CheckCircle2, History, Loader2, XCircle } from "lucide-react";

import type { SyncRun } from "@/api/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatRelativeTime } from "@/lib/utils";

interface RunHistoryTableProps {
  runs: SyncRun[];
  isLoading: boolean;
}

function durationSeconds(run: SyncRun): string {
  if (!run.finished_at) return "—";
  const ms = new Date(run.finished_at).getTime() - new Date(run.started_at).getTime();
  return `${Math.max(0, Math.round(ms / 1000))}s`;
}

export function RunHistoryTable({ runs, isLoading }: RunHistoryTableProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent pipeline runs</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <p className="flex h-32 items-center justify-center text-sm text-muted-foreground">
            Loading…
          </p>
        ) : runs.length === 0 ? (
          <EmptyState
            icon={History}
            title="No runs yet"
            description="Run a pipeline (or wait for its schedule) to see its history here."
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
                      {run.sync_name ?? `Pipeline #${run.sync_id}`}
                    </td>
                    <td className="py-2.5 pr-2">
                      {run.status === "success" ? (
                        <span className="inline-flex items-center gap-1 text-success">
                          <CheckCircle2 className="h-3.5 w-3.5" /> Success
                        </span>
                      ) : run.status === "running" ? (
                        <span className="inline-flex items-center gap-1 text-muted-foreground">
                          <Loader2 className="h-3.5 w-3.5 animate-spin" /> Running
                        </span>
                      ) : (
                        <span
                          className="inline-flex items-center gap-1 text-destructive"
                          title={run.error_message ?? undefined}
                        >
                          <XCircle className="h-3.5 w-3.5" /> Failed
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 pr-2 text-muted-foreground">
                      {formatRelativeTime(run.started_at)}
                    </td>
                    <td className="py-2.5 pr-2 text-muted-foreground">
                      {durationSeconds(run)}
                    </td>
                    <td className="py-2.5 text-muted-foreground">
                      {run.records_written.toLocaleString()} / {run.records_read.toLocaleString()}
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
