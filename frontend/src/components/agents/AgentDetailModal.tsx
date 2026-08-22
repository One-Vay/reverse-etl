import {
  CheckCircle2,
  History,
  Loader2,
  Play,
  Sparkles,
  XCircle,
} from "lucide-react";

import type { DataAgent } from "@/api/types";
import { AgentStatusBadge } from "@/components/agents/AgentStatusBadge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Modal } from "@/components/ui/Modal";
import { useAgentRuns, useGeneratePlan, useRunAgentNow } from "@/hooks/useAgents";
import { formatDateTime, formatRelativeTime } from "@/lib/utils";

interface AgentDetailModalProps {
  open: boolean;
  onClose: () => void;
  agent: DataAgent | null;
}

export function AgentDetailModal({ open, onClose, agent }: AgentDetailModalProps) {
  const generatePlan = useGeneratePlan();
  const runNow = useRunAgentNow();
  const runsQuery = useAgentRuns(agent?.id);

  if (!agent) return null;

  const runs = runsQuery.data?.items ?? [];
  const hasPlan = Boolean(agent.plan);

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={agent.name}
      description="Goal-driven selection: only rows matching the plan below get loaded."
      size="lg"
    >
      <div className="flex flex-col gap-5">
        <div className="flex flex-wrap items-center gap-2">
          <AgentStatusBadge status={agent.status} />
          <span className="text-xs text-muted-foreground">
            Last run {formatRelativeTime(agent.last_run_at)}
          </span>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <p className="text-xs font-medium text-muted-foreground">Goal</p>
            <p className="text-sm">{agent.goal}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground">Planned actions</p>
            <p className="text-sm">{agent.actions}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            loading={generatePlan.isPending}
            onClick={() => generatePlan.mutate(agent.id)}
          >
            <Sparkles className="h-3.5 w-3.5" /> {hasPlan ? "Regenerate plan" : "Generate plan"}
          </Button>
          <Button
            type="button"
            size="sm"
            loading={runNow.isPending}
            disabled={!hasPlan}
            title={hasPlan ? undefined : "Generate a plan first"}
            onClick={() => runNow.mutate(agent.id)}
          >
            <Play className="h-3.5 w-3.5" /> Run now
          </Button>
        </div>

        {agent.plan ? (
          <div className="flex flex-col gap-3 rounded-md border border-border bg-muted/30 p-3">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>
                Plan from <span className="font-mono">{agent.plan.model}</span>
              </span>
              <span>{formatDateTime(agent.plan_generated_at)}</span>
            </div>
            <div>
              <p className="text-xs font-medium text-muted-foreground">
                Strategy: {agent.plan.strategy}
              </p>
            </div>
            <div>
              <p className="text-xs font-medium text-muted-foreground">Selection rule</p>
              <p className="text-sm">{agent.plan.selection_rule}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-muted-foreground">Reasoning</p>
              <p className="whitespace-pre-wrap text-sm text-foreground/90">
                {agent.plan.reasoning}
              </p>
            </div>
            {agent.plan.next_actions.length > 0 && (
              <div>
                <p className="text-xs font-medium text-muted-foreground">
                  Recommended next actions
                </p>
                <ul className="ml-4 list-disc text-sm">
                  {agent.plan.next_actions.map((action, index) => (
                    <li key={index}>{action}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <p className="rounded-md border border-dashed border-border px-3 py-4 text-center text-xs text-muted-foreground">
            No plan yet — click "Generate plan" to have the agent analyze the goal
            against the source data.
          </p>
        )}

        <div>
          <p className="mb-2 text-sm font-medium">Run history</p>
          {runsQuery.isLoading ? (
            <p className="text-xs text-muted-foreground">Loading…</p>
          ) : runs.length === 0 ? (
            <EmptyState
              icon={History}
              title="No runs yet"
              description="Run this agent to see its selection history here."
            />
          ) : (
            <div className="overflow-x-auto scrollbar-thin">
              <table className="w-full min-w-[480px] text-left text-sm">
                <thead>
                  <tr className="text-xs text-muted-foreground">
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium">Started</th>
                    <th className="pb-2 font-medium">Considered</th>
                    <th className="pb-2 font-medium">Selected</th>
                    <th className="pb-2 font-medium">Written</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {runs.map((run) => (
                    <tr key={run.id}>
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
                        {run.rows_considered.toLocaleString()}
                      </td>
                      <td className="py-2.5 pr-2 text-muted-foreground">
                        {run.rows_selected.toLocaleString()}
                      </td>
                      <td className="py-2.5 text-muted-foreground">
                        {run.rows_written.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="flex justify-end">
          <Button type="button" variant="outline" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Modal>
  );
}
