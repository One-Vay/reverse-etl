import { Database, Plus, Server } from "lucide-react";
import { useState } from "react";

import type { Destination, Source } from "@/api/types";
import { AppShell } from "@/components/layout/AppShell";
import { ConnectionCard } from "@/components/connections/ConnectionCard";
import { DestinationFormModal } from "@/components/connections/DestinationFormModal";
import { SourceFormModal } from "@/components/connections/SourceFormModal";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { Tabs } from "@/components/ui/Tabs";
import { useDeleteDestination, useDestinations } from "@/hooks/useDestinations";
import { useDeleteSource, useSources } from "@/hooks/useSources";
import { titleCase } from "@/lib/utils";

type Tab = "sources" | "destinations";

export function ConnectionsPage() {
  const [tab, setTab] = useState<Tab>("sources");

  const sourcesQuery = useSources();
  const destinationsQuery = useDestinations();
  const deleteSource = useDeleteSource();
  const deleteDestination = useDeleteDestination();

  const [sourceModal, setSourceModal] = useState<{
    open: boolean;
    source?: Source | null;
  }>({
    open: false,
  });
  const [destinationModal, setDestinationModal] = useState<{
    open: boolean;
    destination?: Destination | null;
  }>({ open: false });
  const [deleteTarget, setDeleteTarget] = useState<{
    kind: "source" | "destination";
    id: number;
    name: string;
  } | null>(null);

  const sources = sourcesQuery.data?.items ?? [];
  const destinations = destinationsQuery.data?.items ?? [];

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    if (deleteTarget.kind === "source") {
      await deleteSource.mutateAsync(deleteTarget.id);
    } else {
      await deleteDestination.mutateAsync(deleteTarget.id);
    }
  };

  return (
    <AppShell
      title="Connections"
      description="Data sources and CRM destinations available to your pipelines."
      actions={
        <Button
          onClick={() =>
            tab === "sources"
              ? setSourceModal({ open: true, source: null })
              : setDestinationModal({ open: true, destination: null })
          }
        >
          <Plus className="h-4 w-4" />
          {tab === "sources" ? "Add source" : "Add destination"}
        </Button>
      }
    >
      <Tabs
        value={tab}
        onChange={(value) => setTab(value as Tab)}
        items={[
          { value: "sources", label: "Sources", count: sources.length },
          { value: "destinations", label: "Destinations", count: destinations.length },
        ]}
      />

      <div className="mt-5">
        {tab === "sources" ? (
          sourcesQuery.isLoading ? (
            <CardGridSkeleton />
          ) : sources.length === 0 ? (
            <EmptyState
              icon={Database}
              title="No data sources yet"
              description="Connect a PostgreSQL or ClickHouse database to start building mappings and pipelines."
              action={
                <Button onClick={() => setSourceModal({ open: true, source: null })}>
                  <Plus className="h-4 w-4" /> Add source
                </Button>
              }
            />
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {sources.map((source) => (
                <ConnectionCard
                  key={source.id}
                  icon="database"
                  name={source.name}
                  typeLabel={titleCase(source.type)}
                  subtitle={`${source.host}:${source.port}/${source.database}`}
                  meta={`User ${source.username}`}
                  onEdit={() => setSourceModal({ open: true, source })}
                  onDelete={() =>
                    setDeleteTarget({ kind: "source", id: source.id, name: source.name })
                  }
                />
              ))}
            </div>
          )
        ) : destinationsQuery.isLoading ? (
          <CardGridSkeleton />
        ) : destinations.length === 0 ? (
          <EmptyState
            icon={Server}
            title="No CRM destinations yet"
            description="Connect Bitrix24 or AmoCRM so synced records have somewhere to land."
            action={
              <Button
                onClick={() => setDestinationModal({ open: true, destination: null })}
              >
                <Plus className="h-4 w-4" /> Add destination
              </Button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {destinations.map((destination) => (
              <ConnectionCard
                key={destination.id}
                icon="server"
                name={destination.name}
                typeLabel={titleCase(destination.type)}
                subtitle={destination.api_url}
                meta="API credentials stored securely"
                onEdit={() => setDestinationModal({ open: true, destination })}
                onDelete={() =>
                  setDeleteTarget({
                    kind: "destination",
                    id: destination.id,
                    name: destination.name,
                  })
                }
              />
            ))}
          </div>
        )}
      </div>

      <SourceFormModal
        open={sourceModal.open}
        onClose={() => setSourceModal({ open: false })}
        source={sourceModal.source}
      />
      <DestinationFormModal
        open={destinationModal.open}
        onClose={() => setDestinationModal({ open: false })}
        destination={destinationModal.destination}
      />
      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleConfirmDelete}
        title={`Delete "${deleteTarget?.name}"?`}
        description="This cannot be undone. Pipelines using this connection will stop working."
        confirmLabel="Delete"
      />
    </AppShell>
  );
}

function CardGridSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 3 }).map((_, index) => (
        <Skeleton key={index} className="h-24 w-full" />
      ))}
    </div>
  );
}
