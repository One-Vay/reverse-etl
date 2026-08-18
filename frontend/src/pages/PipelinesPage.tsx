import { Plus, Waypoints, Workflow } from "lucide-react";
import { useState } from "react";

import type { Mapping, Sync } from "@/api/types";
import { AppShell } from "@/components/layout/AppShell";
import { Card } from "@/components/ui/Card";
import { MappingCard } from "@/components/pipelines/MappingCard";
import { MappingFormModal } from "@/components/pipelines/MappingFormModal";
import { SyncFormModal } from "@/components/pipelines/SyncFormModal";
import { SyncRow } from "@/components/pipelines/SyncRow";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { Tabs } from "@/components/ui/Tabs";
import { useDestinations } from "@/hooks/useDestinations";
import { useDeleteMapping, useMappings } from "@/hooks/useMappings";
import { useSources } from "@/hooks/useSources";
import { useDeleteSync, useRunSyncNow, useSyncs } from "@/hooks/useSyncs";

type Tab = "mappings" | "syncs";

export function PipelinesPage() {
  const [tab, setTab] = useState<Tab>("syncs");

  const sourcesQuery = useSources();
  const destinationsQuery = useDestinations();
  const mappingsQuery = useMappings();
  const syncsQuery = useSyncs();

  const deleteMapping = useDeleteMapping();
  const deleteSync = useDeleteSync();
  const runSyncNow = useRunSyncNow();

  const sources = sourcesQuery.data?.items ?? [];
  const destinations = destinationsQuery.data?.items ?? [];
  const mappings = mappingsQuery.data?.items ?? [];
  const syncs = syncsQuery.data?.items ?? [];

  const sourceById = new Map(sources.map((s) => [s.id, s]));
  const destinationById = new Map(destinations.map((d) => [d.id, d]));
  const mappingById = new Map(mappings.map((m) => [m.id, m]));

  const [mappingModal, setMappingModal] = useState<{
    open: boolean;
    mapping?: Mapping | null;
  }>({ open: false });
  const [syncModal, setSyncModal] = useState<{ open: boolean; sync?: Sync | null }>({
    open: false,
  });
  const [deleteMappingTarget, setDeleteMappingTarget] = useState<Mapping | null>(null);
  const [deleteSyncTarget, setDeleteSyncTarget] = useState<Sync | null>(null);
  const [runningId, setRunningId] = useState<number | null>(null);

  const handleRunNow = async (id: number) => {
    setRunningId(id);
    try {
      await runSyncNow.mutateAsync(id);
    } catch {
      // Already surfaced to the user via the mutation's onError toast.
    } finally {
      setRunningId(null);
    }
  };

  return (
    <AppShell
      title="Pipelines"
      description="Configure field mappings and sync jobs that connect your sources to destinations."
      actions={
        <Button
          onClick={() =>
            tab === "mappings"
              ? setMappingModal({ open: true, mapping: null })
              : setSyncModal({ open: true, sync: null })
          }
        >
          <Plus className="h-4 w-4" />
          {tab === "mappings" ? "Add mapping" : "Add pipeline"}
        </Button>
      }
    >
      <Tabs
        value={tab}
        onChange={(value) => setTab(value as Tab)}
        items={[
          { value: "syncs", label: "Sync pipelines", count: syncs.length },
          { value: "mappings", label: "Field mappings", count: mappings.length },
        ]}
      />

      <div className="mt-5">
        {tab === "syncs" ? (
          syncsQuery.isLoading ? (
            <Skeleton className="h-64 w-full" />
          ) : syncs.length === 0 ? (
            <EmptyState
              icon={Workflow}
              title="No sync pipelines yet"
              description="Create a pipeline to link a source, destination and mapping on a schedule."
              action={
                <Button onClick={() => setSyncModal({ open: true, sync: null })}>
                  <Plus className="h-4 w-4" /> Add pipeline
                </Button>
              }
            />
          ) : (
            <Card className="overflow-hidden p-0">
              {syncs.map((sync) => (
                <SyncRow
                  key={sync.id}
                  sync={sync}
                  source={sourceById.get(sync.source_id)}
                  destination={destinationById.get(sync.destination_id)}
                  mapping={mappingById.get(sync.mapping_id)}
                  onEdit={() => setSyncModal({ open: true, sync })}
                  onDelete={() => setDeleteSyncTarget(sync)}
                  onRunNow={() => handleRunNow(sync.id)}
                  isRunning={runningId === sync.id}
                />
              ))}
            </Card>
          )
        ) : mappingsQuery.isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : mappings.length === 0 ? (
          <EmptyState
            icon={Waypoints}
            title="No field mappings yet"
            description="Define how columns in a source table transform into destination fields before creating a pipeline."
            action={
              <Button
                onClick={() => setMappingModal({ open: true, mapping: null })}
                disabled={sources.length === 0}
              >
                <Plus className="h-4 w-4" /> Add mapping
              </Button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {mappings.map((mapping) => (
              <MappingCard
                key={mapping.id}
                mapping={mapping}
                source={sourceById.get(mapping.source_id)}
                onEdit={() => setMappingModal({ open: true, mapping })}
                onDelete={() => setDeleteMappingTarget(mapping)}
              />
            ))}
          </div>
        )}
      </div>

      <MappingFormModal
        open={mappingModal.open}
        onClose={() => setMappingModal({ open: false })}
        mapping={mappingModal.mapping}
        sources={sources}
      />
      <SyncFormModal
        open={syncModal.open}
        onClose={() => setSyncModal({ open: false })}
        sync={syncModal.sync}
        sources={sources}
        destinations={destinations}
        mappings={mappings}
      />
      <ConfirmDialog
        open={Boolean(deleteMappingTarget)}
        onClose={() => setDeleteMappingTarget(null)}
        onConfirm={async () => {
          if (deleteMappingTarget)
            await deleteMapping.mutateAsync(deleteMappingTarget.id);
        }}
        title={`Delete "${deleteMappingTarget?.name}"?`}
        description="Pipelines using this mapping will need a replacement before they can run."
        confirmLabel="Delete"
      />
      <ConfirmDialog
        open={Boolean(deleteSyncTarget)}
        onClose={() => setDeleteSyncTarget(null)}
        onConfirm={async () => {
          if (deleteSyncTarget) await deleteSync.mutateAsync(deleteSyncTarget.id);
        }}
        title={`Delete "${deleteSyncTarget?.name}"?`}
        description="This stops the schedule and removes its run history from the console."
        confirmLabel="Delete"
      />
    </AppShell>
  );
}
