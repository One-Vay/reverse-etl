import { ArrowRight, Bot, Pencil, Play, Sparkles, Trash2 } from "lucide-react";

import type { DataAgent, Destination, Mapping } from "@/api/types";
import { AgentStatusBadge } from "@/components/agents/AgentStatusBadge";
import { ActionMenu } from "@/components/ui/ActionMenu";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useGeneratePlan, useRunAgentNow } from "@/hooks/useAgents";
import { formatRelativeTime } from "@/lib/utils";

interface AgentCardProps {
  agent: DataAgent;
  destination?: Destination;
  mapping?: Mapping;
  onOpen: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

export function AgentCard({
  agent,
  destination,
  mapping,
  onOpen,
  onEdit,
  onDelete,
}: AgentCardProps) {
  const generatePlan = useGeneratePlan();
  const runNow = useRunAgentNow();
  const hasPlan = Boolean(agent.plan);

  return (
    <Card className="p-4">
      <div className="flex items-start gap-3">
        <button
          type="button"
          onClick={onOpen}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"
        >
          <Bot className="h-5 w-5" />
        </button>
        <div className="min-w-0 flex-1">
          <button
            type="button"
            onClick={onOpen}
            className="truncate text-left text-sm font-semibold hover:underline"
          >
            {agent.name}
          </button>
          <div className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className="truncate">
              {mapping?.name ?? `Mapping #${agent.mapping_id}`}
            </span>
            <ArrowRight className="h-3 w-3 shrink-0" />
            <span className="truncate">
              {destination?.name ?? `Destination #${agent.destination_id}`}
            </span>
          </div>
          <p className="mt-1.5 line-clamp-2 text-xs text-muted-foreground">{agent.goal}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <AgentStatusBadge status={agent.status} />
            <span className="text-[11px] text-muted-foreground">
              Last run {formatRelativeTime(agent.last_run_at)}
            </span>
          </div>
        </div>
        <ActionMenu
          ariaLabel="Open agent menu"
          items={[
            { label: "Edit", icon: Pencil, onClick: onEdit },
            { label: "Delete", icon: Trash2, onClick: onDelete, destructive: true },
          ]}
        />
      </div>
      <div className="mt-3 flex items-center gap-2">
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
    </Card>
  );
}
