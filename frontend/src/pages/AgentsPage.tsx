import { Bot, Plus } from "lucide-react";
import { useState } from "react";

import type { DataAgent } from "@/api/types";
import { AgentCard } from "@/components/agents/AgentCard";
import { AgentDetailModal } from "@/components/agents/AgentDetailModal";
import { AgentFormModal } from "@/components/agents/AgentFormModal";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { useAgents, useDeleteAgent } from "@/hooks/useAgents";
import { useDestinations } from "@/hooks/useDestinations";
import { useMappings } from "@/hooks/useMappings";

export function AgentsPage() {
  const agentsQuery = useAgents();
  const destinationsQuery = useDestinations();
  const mappingsQuery = useMappings();
  const deleteAgent = useDeleteAgent();

  const agents = agentsQuery.data?.items ?? [];
  const destinations = destinationsQuery.data?.items ?? [];
  const mappings = mappingsQuery.data?.items ?? [];

  const destinationById = new Map(destinations.map((d) => [d.id, d]));
  const mappingById = new Map(mappings.map((m) => [m.id, m]));

  const [formModal, setFormModal] = useState<{ open: boolean; agent?: DataAgent | null }>(
    { open: false },
  );
  const [detailAgent, setDetailAgent] = useState<DataAgent | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<DataAgent | null>(null);

  const isLoading =
    agentsQuery.isLoading || destinationsQuery.isLoading || mappingsQuery.isLoading;

  return (
    <AppShell
      title="Data agents"
      description="Describe a goal, and a personal agent will plan and select only the data that matters — not the whole table."
      actions={
        <Button onClick={() => setFormModal({ open: true, agent: null })}>
          <Plus className="h-4 w-4" /> New agent
        </Button>
      }
    >
      {isLoading ? (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      ) : agents.length === 0 ? (
        <EmptyState
          icon={Bot}
          title="No data agents yet"
          description="Create an agent, describe your goal and planned actions, and it will analyze your data to load only what matters."
          action={
            <Button onClick={() => setFormModal({ open: true, agent: null })}>
              <Plus className="h-4 w-4" /> New agent
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {agents.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              destination={destinationById.get(agent.destination_id)}
              mapping={mappingById.get(agent.mapping_id)}
              onOpen={() => setDetailAgent(agent)}
              onEdit={() => setFormModal({ open: true, agent })}
              onDelete={() => setDeleteTarget(agent)}
            />
          ))}
        </div>
      )}

      <AgentFormModal
        open={formModal.open}
        onClose={() => setFormModal({ open: false })}
        agent={formModal.agent}
        destinations={destinations}
        mappings={mappings}
      />
      <AgentDetailModal
        open={Boolean(detailAgent)}
        onClose={() => setDetailAgent(null)}
        agent={detailAgent}
      />
      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        onConfirm={async () => {
          if (deleteTarget) await deleteAgent.mutateAsync(deleteTarget.id);
        }}
        title={`Delete "${deleteTarget?.name}"?`}
        description="This removes the agent's plan and run history."
        confirmLabel="Delete"
      />
    </AppShell>
  );
}
