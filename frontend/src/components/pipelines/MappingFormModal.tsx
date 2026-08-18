import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";

import type { Mapping, Source } from "@/api/types";
import { FieldMappingsEditor } from "@/components/pipelines/FieldMappingsEditor";
import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { useCreateMapping, useUpdateMapping } from "@/hooks/useMappings";
import { type MappingFormValues, mappingSchema } from "@/lib/schemas";

interface MappingFormModalProps {
  open: boolean;
  onClose: () => void;
  mapping?: Mapping | null;
  sources: Source[];
}

function defaultValues(sources: Source[]): MappingFormValues {
  return {
    name: "",
    source_id: sources[0]?.id ?? 0,
    source_table: "",
    destination_entity: "",
    field_mappings: [],
  };
}

export function MappingFormModal({
  open,
  onClose,
  mapping,
  sources,
}: MappingFormModalProps) {
  const isEditing = Boolean(mapping);
  const createMapping = useCreateMapping();
  const updateMapping = useUpdateMapping();

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<MappingFormValues>({
    resolver: zodResolver(mappingSchema),
    defaultValues: defaultValues(sources),
  });

  useEffect(() => {
    if (!open) return;
    reset(
      mapping
        ? {
            name: mapping.name,
            source_id: mapping.source_id,
            source_table: mapping.source_table,
            destination_entity: mapping.destination_entity,
            field_mappings: mapping.field_mappings.map((fm) => ({
              source_field: fm.source_field,
              destination_field: fm.destination_field,
              transformation: fm.transformation ?? "",
            })),
          }
        : defaultValues(sources),
    );
  }, [open, mapping, sources, reset]);

  const isSaving = createMapping.isPending || updateMapping.isPending;

  const onSubmit = async (values: MappingFormValues) => {
    const payload = {
      ...values,
      field_mappings: values.field_mappings
        .filter((fm) => fm.source_field && fm.destination_field)
        .map((fm) => ({
          source_field: fm.source_field,
          destination_field: fm.destination_field,
          transformation: fm.transformation || null,
        })),
    };
    try {
      if (isEditing && mapping) {
        await updateMapping.mutateAsync({ id: mapping.id, input: payload });
      } else {
        await createMapping.mutateAsync(payload);
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
      title={isEditing ? "Edit mapping" : "New field mapping"}
      description="Define how a source table's columns transform into destination fields."
      size="lg"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
        <FormField
          label="Name"
          htmlFor="mapping-name"
          error={errors.name?.message}
          required
        >
          <Input id="mapping-name" placeholder="Contacts → Leads" {...register("name")} />
        </FormField>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <FormField
            label="Source"
            htmlFor="mapping-source"
            error={errors.source_id?.message}
            required
          >
            <Select
              id="mapping-source"
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
            label="Source table"
            htmlFor="mapping-source-table"
            error={errors.source_table?.message}
            required
          >
            <Input
              id="mapping-source-table"
              placeholder="contacts"
              {...register("source_table")}
            />
          </FormField>
          <FormField
            label="Destination entity"
            htmlFor="mapping-destination-entity"
            error={errors.destination_entity?.message}
            required
          >
            <Input
              id="mapping-destination-entity"
              placeholder="leads"
              {...register("destination_entity")}
            />
          </FormField>
        </div>

        <FieldMappingsEditor
          control={control}
          register={register}
          error={errors.field_mappings}
        />

        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={isSaving} disabled={sources.length === 0}>
            {isEditing ? "Save changes" : "Create mapping"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
