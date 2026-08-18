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

const SCHEDULE_PRESETS = [
  { label: "Every 15 minutes", value: "*/15 * * * *" },
  { label: "Every 30 minutes", value: "*/30 * * * *" },
  { label: "Hourly", value: "0 * * * *" },
  { label: "Every 6 hours", value: "0 */6 * * *" },
  { label: "Daily at 03:00", value: "0 3 * * *" },
];

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
    schedule: SCHEDULE_PRESETS[1].value,
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
            schedule: sync.schedule,
            incremental_field: sync.incremental_field ?? "",
            status: sync.status,
          }
        : defaultValues(sources, destinations, mappings),
    );
  }, [open, sync, sources, destinations, mappings, reset]);

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

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField
            label="Schedule"
            htmlFor="sync-schedule"
            error={errors.schedule?.message}
            hint="Cron expression"
            required
          >
            <Input
              id="sync-schedule"
              list="schedule-presets"
              placeholder="*/30 * * * *"
              {...register("schedule")}
            />
            <datalist id="schedule-presets">
              {SCHEDULE_PRESETS.map((preset) => (
                <option key={preset.value} value={preset.value}>
                  {preset.label}
                </option>
              ))}
            </datalist>
          </FormField>
          <FormField
            label="Incremental field"
            htmlFor="sync-incremental-field"
            hint="Optional, e.g. updated_at"
          >
            <Input id="sync-incremental-field" {...register("incremental_field")} />
          </FormField>
        </div>

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
