import { ArrowLeftRight, KeyRound, Link2, Sparkles, Unlink } from "lucide-react";
import { useState } from "react";

import { useDestinationEntityFields } from "@/hooks/useDestinations";
import { useSuggestMappings } from "@/hooks/useMappings";
import { useSettings } from "@/hooks/useSettings";
import { useSourceTableSchema } from "@/hooks/useSources";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/context/ToastContext";
import { cn } from "@/lib/utils";

// Suggested pairs below this confidence are dropped rather than
// auto-applied — low-confidence guesses are more distracting than useful.
const SUGGESTION_CONFIDENCE_THRESHOLD = 0.5;

interface FieldMappingPair {
  source_field: string;
  destination_field: string;
}

interface MappingBoardProps {
  sourceId: number | undefined;
  table: string | undefined;
  schema?: string;
  destinationId: number | undefined;
  entity: string | undefined;
  fieldMappings: FieldMappingPair[];
  /** Links a source column to a destination field. If the source column is
   * already linked, this re-points it rather than creating a duplicate. */
  onConnect: (sourceField: string, destinationField: string) => void;
  /** Removes whatever mapping currently uses this source column. */
  onDisconnect: (sourceField: string) => void;
}

// A drag payload custom MIME type, so drop targets can tell a mapping-board
// chip apart from any other draggable content dragged over the page.
const DRAG_MIME = "application/x-reverse-etl-source-field";

/** Interactive two-column board for wiring a source table's columns to a
 * destination entity's fields: drag a source chip onto a destination chip,
 * or click one of each to connect them — both update the same
 * `field_mappings` the row-based editor below reads from. Connected pairs
 * share a numbered badge so the link between the two columns is visible at
 * a glance without drawing connector lines across the form. */
export function MappingBoard({
  sourceId,
  table,
  schema = "public",
  destinationId,
  entity,
  fieldMappings,
  onConnect,
  onDisconnect,
}: MappingBoardProps) {
  const [armedSource, setArmedSource] = useState<string | null>(null);
  const [dragOverField, setDragOverField] = useState<string | null>(null);

  const columnsQuery = useSourceTableSchema(sourceId, table, schema);
  const fieldsQuery = useDestinationEntityFields(destinationId, entity);
  const settingsQuery = useSettings();
  const suggestMappings = useSuggestMappings();
  const { showToast } = useToast();

  if (!sourceId || !table || !destinationId || !entity) return null;

  const sourceByField = new Map(
    fieldMappings
      .filter((fm) => fm.source_field)
      .map((fm) => [fm.source_field, fm.destination_field] as const),
  );
  // Order pairs deterministically so a source/destination chip pair keeps
  // the same badge number across re-renders instead of jumping around.
  const pairOrder = new Map(
    [...sourceByField.keys()].sort().map((field, index) => [field, index + 1]),
  );
  const destinationInUse = new Map(
    [...sourceByField.entries()].map(([source, dest]) => [dest, source]),
  );

  const connect = (sourceField: string, destinationField: string) => {
    onConnect(sourceField, destinationField);
    setArmedSource(null);
  };

  const handleSourceClick = (fieldName: string) => {
    if (sourceByField.has(fieldName)) {
      onDisconnect(fieldName);
      if (armedSource === fieldName) setArmedSource(null);
      return;
    }
    setArmedSource((prev) => (prev === fieldName ? null : fieldName));
  };

  const handleDestinationClick = (fieldName: string) => {
    const linkedSource = destinationInUse.get(fieldName);
    if (linkedSource) {
      onDisconnect(linkedSource);
      return;
    }
    if (armedSource) connect(armedSource, fieldName);
  };

  if (columnsQuery.isPending || fieldsQuery.isPending) {
    return <p className="text-xs text-muted-foreground">Loading fields to connect…</p>;
  }

  if (columnsQuery.isError || fieldsQuery.isError) {
    return (
      <p className="text-xs text-destructive">
        Couldn't load fields. Check the source's and destination's connections.
      </p>
    );
  }

  const columns = columnsQuery.data ?? [];
  const fields = fieldsQuery.data ?? [];

  if (columns.length === 0 || fields.length === 0) {
    return (
      <p className="text-xs text-muted-foreground">
        {columns.length === 0
          ? `"${table}" has no columns to map.`
          : `"${entity}" has no fields to map.`}
      </p>
    );
  }

  const llmEnabled = settingsQuery.data?.llm_enabled ?? false;

  const handleSuggest = async () => {
    const result = await suggestMappings.mutateAsync({
      sourceColumns: columns.map((c) => ({ name: c.name, data_type: c.data_type })),
      destinationFields: fields.map((f) => ({ name: f.name, data_type: f.data_type })),
    });
    // A suggestion only counts as "new" if it changes an actual connection —
    // otherwise a click that re-suggests already-mapped fields would look
    // like nothing happened, with no visible change and no feedback.
    let appliedCount = 0;
    for (const pair of result.pairs) {
      if (pair.confidence < SUGGESTION_CONFIDENCE_THRESHOLD) continue;
      if (sourceByField.get(pair.source_field) === pair.destination_field) continue;
      onConnect(pair.source_field, pair.destination_field);
      appliedCount += 1;
    }

    if (appliedCount > 0) {
      showToast({
        variant: "success",
        title: `Applied ${appliedCount} AI suggestion${appliedCount === 1 ? "" : "s"}`,
      });
    } else if (result.pairs.length > 0) {
      showToast({
        variant: "info",
        title: "Nothing new to suggest",
        description: "These fields are already mapped.",
      });
    }
  };

  return (
    <div className="flex flex-col gap-2 rounded-md border border-border p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
          <ArrowLeftRight className="h-3.5 w-3.5" />
          Drag a source column onto a destination field, or click one of each to
          connect them
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          loading={suggestMappings.isPending}
          disabled={!llmEnabled}
          title={llmEnabled ? undefined : "Enable AI mapping suggestions in Settings"}
          onClick={handleSuggest}
        >
          <Sparkles className="h-3.5 w-3.5" /> Suggest with AI
        </Button>
      </div>
      {suggestMappings.data?.pairs.length === 0 && suggestMappings.data.message && (
        <p className="text-xs text-muted-foreground">{suggestMappings.data.message}</p>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <p className="text-xs font-medium text-muted-foreground">{table} (source)</p>
          <div className="flex flex-wrap gap-1.5">
            {columns.map((column) => {
              const pairNumber = pairOrder.get(column.name);
              const isConnected = sourceByField.has(column.name);
              const isArmed = armedSource === column.name;
              return (
                <button
                  key={column.name}
                  type="button"
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData(DRAG_MIME, column.name);
                    e.dataTransfer.effectAllowed = "link";
                  }}
                  onClick={() => handleSourceClick(column.name)}
                  title={`${column.data_type}${column.nullable ? "" : " · not null"}`}
                  className={cn(
                    "inline-flex cursor-grab items-center gap-1 rounded-full border px-2.5 py-1 text-xs transition-colors active:cursor-grabbing",
                    isConnected
                      ? "border-primary/40 bg-primary/10 text-primary"
                      : isArmed
                        ? "border-primary bg-primary/20 text-primary ring-1 ring-primary"
                        : "border-border bg-background text-foreground hover:border-primary/40 hover:bg-accent",
                  )}
                >
                  {column.is_primary_key && <KeyRound className="h-3 w-3 shrink-0" />}
                  {column.name}
                  {isConnected && (
                    <span className="ml-0.5 inline-flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[10px] font-semibold text-primary-foreground">
                      {pairNumber}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <p className="text-xs font-medium text-muted-foreground">
            {entity} (destination)
          </p>
          <div className="flex flex-wrap gap-1.5">
            {fields.map((field) => {
              const linkedSource = destinationInUse.get(field.name);
              const pairNumber = linkedSource ? pairOrder.get(linkedSource) : undefined;
              const isConnected = Boolean(linkedSource);
              const isDragOver = dragOverField === field.name;
              return (
                <button
                  key={field.name}
                  type="button"
                  onClick={() => handleDestinationClick(field.name)}
                  onDragOver={(e) => {
                    e.preventDefault();
                    e.dataTransfer.dropEffect = "link";
                    setDragOverField(field.name);
                  }}
                  onDragLeave={() =>
                    setDragOverField((prev) => (prev === field.name ? null : prev))
                  }
                  onDrop={(e) => {
                    e.preventDefault();
                    setDragOverField(null);
                    const sourceField = e.dataTransfer.getData(DRAG_MIME);
                    if (sourceField) connect(sourceField, field.name);
                  }}
                  title={`${field.data_type}${field.nullable ? "" : " · not null"}`}
                  className={cn(
                    "inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs transition-colors",
                    isConnected
                      ? "border-primary/40 bg-primary/10 text-primary"
                      : isDragOver
                        ? "border-primary bg-primary/20 text-primary ring-1 ring-primary"
                        : armedSource
                          ? "border-primary/40 bg-background text-foreground hover:border-primary hover:bg-primary/10"
                          : "border-border bg-background text-foreground hover:border-primary/40 hover:bg-accent",
                  )}
                >
                  {isConnected ? (
                    <span className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[10px] font-semibold text-primary-foreground">
                      {pairNumber}
                    </span>
                  ) : (
                    <Link2 className="h-3 w-3 shrink-0 opacity-40" />
                  )}
                  {field.is_primary_key && <KeyRound className="h-3 w-3 shrink-0" />}
                  {field.name}
                  {isConnected && <Unlink className="h-3 w-3 shrink-0 opacity-60" />}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {armedSource && (
        <p className="text-xs text-primary">
          "{armedSource}" selected — click a destination field to connect it, or click it
          again to cancel.
        </p>
      )}
    </div>
  );
}
