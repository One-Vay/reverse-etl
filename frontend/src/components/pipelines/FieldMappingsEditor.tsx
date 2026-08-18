import { ArrowRight, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import type {
  Control,
  FieldArrayWithId,
  FieldErrors,
  UseFieldArrayAppend,
  UseFieldArrayRemove,
  UseFormRegister,
  UseFormSetValue,
  UseFormWatch,
} from "react-hook-form";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import type { MappingFormValues } from "@/lib/schemas";
import { CUSTOM_TRANSFORMATION, TRANSFORMATION_PRESETS } from "@/lib/transformations";

interface FieldMappingsEditorProps {
  control: Control<MappingFormValues>;
  register: UseFormRegister<MappingFormValues>;
  watch: UseFormWatch<MappingFormValues>;
  setValue: UseFormSetValue<MappingFormValues>;
  fields: FieldArrayWithId<MappingFormValues, "field_mappings", "id">[];
  append: UseFieldArrayAppend<MappingFormValues, "field_mappings">;
  remove: UseFieldArrayRemove;
  error?: FieldErrors<MappingFormValues>["field_mappings"];
}

export function FieldMappingsEditor({
  register,
  watch,
  setValue,
  fields,
  append,
  remove,
  error,
}: FieldMappingsEditorProps) {
  // Rows whose transformation preset is "Custom…" render a free-text input
  // instead of the preset <select>. This is purely local UI state — the
  // underlying form field still just holds a string.
  const [customRows, setCustomRows] = useState<Set<number>>(new Set());

  const setRowCustomMode = (index: number, isCustom: boolean) => {
    setCustomRows((prev) => {
      const next = new Set(prev);
      if (isCustom) next.add(index);
      else next.delete(index);
      return next;
    });
  };

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
          No field mappings yet. Click a column below, or "Add field", to define how
          source columns map to destination fields.
        </p>
      ) : (
        <div className="flex flex-col gap-2">
          <div className="hidden grid-cols-[1fr_auto_1fr_1fr_auto] gap-2 px-1 text-xs font-medium text-muted-foreground sm:grid">
            <span>Source field</span>
            <span />
            <span>Destination field</span>
            <span>Transformation</span>
            <span />
          </div>
          {fields.map((field, index) => {
            const transformationValue = watch(`field_mappings.${index}.transformation`);
            const isCustom = customRows.has(index);

            return (
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
                {isCustom ? (
                  <div className="flex items-center gap-1">
                    <Input
                      placeholder="e.g. concat(first, last)"
                      autoFocus
                      {...register(`field_mappings.${index}.transformation` as const)}
                    />
                    <button
                      type="button"
                      onClick={() => setRowCustomMode(index, false)}
                      className="shrink-0 text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
                    >
                      Presets
                    </button>
                  </div>
                ) : (
                  <Select
                    value={transformationValue || ""}
                    onChange={(e) => {
                      if (e.target.value === CUSTOM_TRANSFORMATION) {
                        setRowCustomMode(index, true);
                        setValue(`field_mappings.${index}.transformation`, "", {
                          shouldDirty: true,
                        });
                      } else {
                        setValue(
                          `field_mappings.${index}.transformation`,
                          e.target.value,
                          {
                            shouldDirty: true,
                          },
                        );
                      }
                    }}
                  >
                    {TRANSFORMATION_PRESETS.map((preset) => (
                      <option key={preset.label} value={preset.value}>
                        {preset.label}
                      </option>
                    ))}
                  </Select>
                )}
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    remove(index);
                    setRowCustomMode(index, false);
                  }}
                  aria-label="Remove field mapping"
                  className="text-destructive hover:bg-destructive/10"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            );
          })}
        </div>
      )}
      {error?.message && <p className="text-xs text-destructive">{error.message}</p>}
    </div>
  );
}
