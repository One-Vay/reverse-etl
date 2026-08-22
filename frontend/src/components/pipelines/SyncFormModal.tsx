import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";

import type { Destination, Mapping, Source, Sync } from "@/api/types";
import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { useCreateSync, useUpdateSync } from "@/hooks/useSyncs";
import { type SyncFormValues, syncSchema } from "@/lib/schemas";

interface SyncFormModalProps {
  open: boolean;
  onClose: () => void;
  sync?: Sync | null;
  sources: Source[];
  destinations: Destination[];
  mappings: Mapping[];
}

function defaultValues(
  sources: Source[],
  destinations: Destination[],
  mappings: Mapping[],
): SyncFormValues {
  return {
    name: "",
    source_id: sources[0]?.id ?? 0,
    destination_id: destinations[0]?.id ?? 0,
    mapping_id: mappings[0]?.id ?? 0,
    interval_value: 1,
    interval_unit: "hours",
    run_at_time: null,
    incremental_field: "",
    status: "active",
  };
}

export function SyncFormModal({
  open,
  onClose,
  sync,
  sources,
  destinations,
  mappings,
}: SyncFormModalProps) {
  const isEditing = Boolean(sync);
  const createSync = useCreateSync();
  const updateSync = useUpdateSync();

  const canSubmit = sources.length > 0 && destinations.length > 0 && mappings.length > 0;

  const {
    register,
    watch,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<SyncFormValues>({
    resolver: zodResolver(syncSchema),
    defaultValues: defaultValues(sources, destinations, mappings),
  });

  useEffect(() => {
    if (!open) return;
    reset(
      sync
        ? {
            name: sync.name,
            source_id: sync.source_id,
            destination_id: sync.destination_id,
            mapping_id: sync.mapping_id,
            interval_value: sync.interval_value,
            interval_unit: sync.interval_unit,
            run_at_time: sync.run_at_time,
            incremental_field: sync.incremental_field ?? "",
            status: sync.status,
          }
        : defaultValues(sources, destinations, mappings),
    );
  }, [open, sync, sources, destinations, mappings, reset]);

  const intervalUnit = watch("interval_unit");

  const isSaving = createSync.isPending || updateSync.isPending;

  const onSubmit = async (values: SyncFormValues) => {
    const payload = {
      ...values,
      incremental_field: values.incremental_field || null,
    };
    try {
      if (isEditing && sync) {
        await updateSync.mutateAsync({ id: sync.id, input: payload });
      } else {
        await createSync.mutateAsync(payload);
      }
      onClose();
    } catch {
      // Already surfaced to the user via the mutation's onError toast.
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEditing ? "Edit pipeline" : "New sync pipeline"}
      description="Link a source, destination and mapping, then choose a schedule."
    >
      {!canSubmit && !isEditing && (
        <p className="mb-4 rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-xs text-warning">
          You need at least one source, destination and mapping before creating a
          pipeline.
        </p>
      )}
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
        <FormField label="Name" htmlFor="sync-name" error={errors.name?.message} required>
          <Input
            id="sync-name"
            placeholder="Contacts hourly sync"
            {...register("name")}
          />
        </FormField>

        <FormField
          label="Source"
          htmlFor="sync-source"
          error={errors.source_id?.message}
          required
        >
          <Select
            id="sync-source"
            {...register("source_id")}
            disabled={sources.length === 0}
          >
            {sources.length === 0 && <option value={0}>No sources available</option>}
            {sources.map((source) => (
              <option key={source.id} value={source.id}>
                {source.name}
              </option>
            ))}
          </Select>
        </FormField>

        <FormField
          label="Destination"
          htmlFor="sync-destination"
          error={errors.destination_id?.message}
          required
        >
          <Select
            id="sync-destination"
            {...register("destination_id")}
            disabled={destinations.length === 0}
          >
            {destinations.length === 0 && (
              <option value={0}>No destinations available</option>
            )}
            {destinations.map((destination) => (
              <option key={destination.id} value={destination.id}>
                {destination.name}
              </option>
            ))}
          </Select>
        </FormField>

        <FormField
          label="Mapping"
          htmlFor="sync-mapping"
          error={errors.mapping_id?.message}
          required
        >
          <Select
            id="sync-mapping"
            {...register("mapping_id")}
            disabled={mappings.length === 0}
          >
            {mappings.length === 0 && <option value={0}>No mappings available</option>}
            {mappings.map((mapping) => (
              <option key={mapping.id} value={mapping.id}>
                {mapping.name}
              </option>
            ))}
          </Select>
        </FormField>

        <div className="rounded-md border border-border p-3">
          <p className="mb-3 text-xs font-medium text-muted-foreground">How often should this run?</p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <FormField
              label="Every"
              htmlFor="sync-interval-value"
              error={errors.interval_value?.message}
              required
            >
              <Input
                id="sync-interval-value"
                type="number"
                min={1}
                max={intervalUnit === "days" ? 90 : 168}
                {...register("interval_value")}
              />
            </FormField>
            <FormField label="Unit" htmlFor="sync-interval-unit" required>
              <Select id="sync-interval-unit" {...register("interval_unit")}>
                <option value="hours">Hours</option>
                <option value="days">Days</option>
              </Select>
            </FormField>
            {intervalUnit === "days" && (
              <FormField
                label="At time"
                htmlFor="sync-run-at-time"
                error={errors.run_at_time?.message}
                hint="24h, e.g. 09:00"
              >
                <Input id="sync-run-at-time" type="time" {...register("run_at_time")} />
              </FormField>
            )}
          </div>
        </div>

        <FormField
          label="Incremental field"
          htmlFor="sync-incremental-field"
          hint="Optional, e.g. updated_at"
        >
          <Input id="sync-incremental-field" {...register("incremental_field")} />
        </FormField>

        <FormField label="Status" htmlFor="sync-status">
          <Select id="sync-status" {...register("status")}>
            <option value="active">Active</option>
            <option value="paused">Paused</option>
            <option value="inactive">Inactive</option>
          </Select>
        </FormField>

        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={isSaving} disabled={!canSubmit && !isEditing}>
            {isEditing ? "Save changes" : "Create pipeline"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
