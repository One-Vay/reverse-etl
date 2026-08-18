import { ArrowRight, Plus, Trash2 } from "lucide-react";
import {
  useFieldArray,
  type Control,
  type FieldErrors,
  type UseFormRegister,
} from "react-hook-form";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import type { MappingFormValues } from "@/lib/schemas";

interface FieldMappingsEditorProps {
  control: Control<MappingFormValues>;
  register: UseFormRegister<MappingFormValues>;
  error?: FieldErrors<MappingFormValues>["field_mappings"];
}

export function FieldMappingsEditor({
  control,
  register,
  error,
}: FieldMappingsEditorProps) {
  const { fields, append, remove } = useFieldArray({
    control,
    name: "field_mappings",
  });

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium">Field mappings</label>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() =>
            append({ source_field: "", destination_field: "", transformation: "" })
          }
        >
          <Plus className="h-3.5 w-3.5" /> Add field
        </Button>
      </div>

      {fields.length === 0 ? (
        <p className="rounded-md border border-dashed border-border px-3 py-4 text-center text-xs text-muted-foreground">
          No field mappings yet. Add at least one to define how source columns map to
          destination fields.
        </p>
      ) : (
        <div className="flex flex-col gap-2">
          <div className="hidden grid-cols-[1fr_auto_1fr_1fr_auto] gap-2 px-1 text-xs font-medium text-muted-foreground sm:grid">
            <span>Source field</span>
            <span />
            <span>Destination field</span>
            <span>Transformation (optional)</span>
            <span />
          </div>
          {fields.map((field, index) => (
            <div
              key={field.id}
              className="grid grid-cols-1 items-center gap-2 rounded-md border border-border p-2 sm:grid-cols-[1fr_auto_1fr_1fr_auto] sm:border-none sm:p-0"
            >
              <Input
                placeholder="raw_email"
                {...register(`field_mappings.${index}.source_field` as const)}
              />
              <ArrowRight className="hidden h-4 w-4 shrink-0 text-muted-foreground sm:block" />
              <Input
                placeholder="EMAIL"
                {...register(`field_mappings.${index}.destination_field` as const)}
              />
              <Input
                placeholder="lowercase, trim…"
                {...register(`field_mappings.${index}.transformation` as const)}
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => remove(index)}
                aria-label="Remove field mapping"
                className="text-destructive hover:bg-destructive/10"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      )}
      {error?.message && <p className="text-xs text-destructive">{error.message}</p>}
    </div>
  );
}
