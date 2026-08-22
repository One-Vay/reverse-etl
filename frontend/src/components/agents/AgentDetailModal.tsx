import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Eye,
  History,
  Loader2,
  Play,
  Sparkles,
  XCircle,
} from "lucide-react";
import { Fragment, useState } from "react";

import type { DataAgent } from "@/api/types";
import { AgentChatPanel } from "@/components/agents/AgentChatPanel";
import { AgentStatusBadge } from "@/components/agents/AgentStatusBadge";
import { RowDetailsTable } from "@/components/agents/RowDetailsTable";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Modal } from "@/components/ui/Modal";
import { Tabs } from "@/components/ui/Tabs";
import {
  useAgentRuns,
  useGeneratePlan,
  usePreviewAgent,
  useRunAgentNow,
} from "@/hooks/useAgents";
import { formatDateTime, formatRelativeTime } from "@/lib/utils";

interface AgentDetailModalProps {
  open: boolean;
  onClose: () => void;
  agent: DataAgent | null;
}

export function AgentDetailModal({ open, onClose, agent }: AgentDetailModalProps) {
  const [tab, setTab] = useState<"overview" | "chat">("overview");
  const [expandedRunId, setExpandedRunId] = useState<number | null>(null);

  const generatePlan = useGeneratePlan();
  const runNow = useRunAgentNow();
  const preview = usePreviewAgent();
  const runsQuery = useAgentRuns(agent?.id);

  if (!agent) return null;

  const runs = runsQuery.data?.items ?? [];
  const hasPlan = Boolean(agent.plan);

  const handleRunNow = async () => {
    await runNow.mutateAsync(agent.id);
    preview.reset();
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={agent.name}
      description="Goal-driven selection: only rows matching the plan below get loaded."
      size="lg"
    >
      <div className="flex flex-col gap-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <AgentStatusBadge status={agent.status} />
            <span className="text-xs text-muted-foreground">
              Last run {formatRelativeTime(agent.last_run_at)}
            </span>
          </div>
          <Tabs
            value={tab}
            onChange={(value) => setTab(value as "overview" | "chat")}
            items={[
              { value: "overview", label: "Overview" },
              { value: "chat", label: "Chat" },
            ]}
          />
        </div>

        {tab === "chat" ? (
          <AgentChatPanel agentId={agent.id} />
        ) : (
          <>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <p className="text-xs font-medium text-muted-foreground">Goal</p>
                <p className="text-sm">{agent.goal}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-muted-foreground">
                  Planned actions
                </p>
                <p className="text-sm">{agent.actions}</p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                loading={generatePlan.isPending}
                onClick={() => generatePlan.mutate(agent.id)}
              >
                <Sparkles className="h-3.5 w-3.5" />{" "}
                {hasPlan ? "Regenerate plan" : "Generate plan"}
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                loading={preview.isPending}
                disabled={!hasPlan}
                title={hasPlan ? undefined : "Generate a plan first"}
                onClick={() => preview.mutate(agent.id)}
              >
                <Eye className="h-3.5 w-3.5" /> Preview selection
              </Button>
              <Button
                type="button"
                size="sm"
                loading={runNow.isPending}
                disabled={!hasPlan}
                title={hasPlan ? undefined : "Generate a plan first"}
                onClick={handleRunNow}
              >
                <Play className="h-3.5 w-3.5" /> Run now
              </Button>
            </div>

            {preview.data && (
              <div className="flex flex-col gap-2 rounded-md border border-primary/30 bg-primary/5 p-3">
                <p className="text-xs font-medium text-primary">
                  Preview — nothing has been written yet
                </p>
                <RowDetailsTable
                  rows={preview.data.row_details}
                  caption={`${preview.data.rows_selected} of ${preview.data.rows_considered} rows would be selected. Review below, then click "Run now" to actually load them.`}
                />
              </div>
            )}

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
                  <p className="text-xs font-medium text-muted-foreground">
                    Selection rule
                  </p>
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
                <div className="flex flex-col gap-1">
                  <div className="overflow-x-auto scrollbar-thin">
                    <table className="w-full min-w-[520px] text-left text-sm">
                      <thead>
                        <tr className="text-xs text-muted-foreground">
                          <th className="w-6 pb-2" />
                          <th className="pb-2 font-medium">Status</th>
                          <th className="pb-2 font-medium">Started</th>
                          <th className="pb-2 font-medium">Considered</th>
                          <th className="pb-2 font-medium">Selected</th>
                          <th className="pb-2 font-medium">Written</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {runs.map((run) => {
                          const expanded = expandedRunId === run.id;
                          return (
                            <Fragment key={run.id}>
                              <tr
                                className="cursor-pointer hover:bg-accent/50"
                                onClick={() =>
                                  setExpandedRunId(expanded ? null : run.id)
                                }
                              >
                                <td className="py-2.5 pl-1 text-muted-foreground">
                                  {expanded ? (
                                    <ChevronDown className="h-3.5 w-3.5" />
                                  ) : (
                                    <ChevronRight className="h-3.5 w-3.5" />
                                  )}
                                </td>
                                <td className="py-2.5 pr-2">
                                  {run.status === "success" ? (
                                    <span className="inline-flex items-center gap-1 text-success">
                                      <CheckCircle2 className="h-3.5 w-3.5" /> Success
                                    </span>
                                  ) : run.status === "running" ? (
                                    <span className="inline-flex items-center gap-1 text-muted-foreground">
                                      <Loader2 className="h-3.5 w-3.5 animate-spin" />{" "}
                                      Running
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
                              {expanded && (
                                <tr>
                                  <td colSpan={6} className="bg-muted/20 p-3">
                                    {run.error_message && (
                                      <p className="mb-2 text-xs text-destructive">
                                        {run.error_message}
                                      </p>
                                    )}
                                    <RowDetailsTable rows={run.row_details} />
                                  </td>
                                </tr>
                              )}
                            </Fragment>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </>
        )}

        <div className="flex justify-end">
          <Button type="button" variant="outline" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Modal>
  );
}
