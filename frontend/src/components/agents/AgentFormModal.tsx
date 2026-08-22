import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, Trash2 } from "lucide-react";
import { useEffect } from "react";
import { useFieldArray, useForm } from "react-hook-form";

import type { DataAgent, Destination, Mapping } from "@/api/types";
import { AgentModelPicker } from "@/components/agents/AgentModelPicker";
import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { useCreateAgent, useUpdateAgent } from "@/hooks/useAgents";
import { type AgentFormValues, agentSchema } from "@/lib/schemas";

interface AgentFormModalProps {
  open: boolean;
  onClose: () => void;
  agent?: DataAgent | null;
  destinations: Destination[];
  mappings: Mapping[];
}

function defaultValues(
  destinations: Destination[],
  mappings: Mapping[],
): AgentFormValues {
  return {
    name: "",
    destination_id: destinations[0]?.id ?? 0,
    mapping_id: mappings[0]?.id ?? 0,
    goal: "",
    actions: "",
    feature_notes: [],
    llm_model: "",
    selection_strategy: "scoring",
    selection_threshold: 0.6,
    incremental_field: "",
    annotation_field: "",
  };
}

export function AgentFormModal({
  open,
  onClose,
  agent,
  destinations,
  mappings,
}: AgentFormModalProps) {
  const isEditing = Boolean(agent);
  const createAgent = useCreateAgent();
  const updateAgent = useUpdateAgent();

  const canSubmit = destinations.length > 0 && mappings.length > 0;

  const {
    register,
    control,
    watch,
    setValue,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<AgentFormValues>({
    resolver: zodResolver(agentSchema),
    defaultValues: defaultValues(destinations, mappings),
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: "feature_notes",
  });

  useEffect(() => {
    if (!open) return;
    reset(
      agent
        ? {
            name: agent.name,
            destination_id: agent.destination_id,
            mapping_id: agent.mapping_id,
            goal: agent.goal,
            actions: agent.actions,
            feature_notes: agent.feature_notes,
            llm_model: agent.llm_model,
            selection_strategy: agent.selection_strategy,
            selection_threshold: agent.selection_threshold,
            incremental_field: agent.incremental_field ?? "",
            annotation_field: agent.annotation_field ?? "",
          }
        : defaultValues(destinations, mappings),
    );
  }, [open, agent, destinations, mappings, reset]);

  const isSaving = createAgent.isPending || updateAgent.isPending;
  const llmModel = watch("llm_model");

  const onSubmit = async (values: AgentFormValues) => {
    const payload = {
      ...values,
      incremental_field: values.incremental_field || null,
      annotation_field: values.annotation_field || null,
    };
    try {
      if (isEditing && agent) {
        await updateAgent.mutateAsync({ id: agent.id, input: payload });
      } else {
        await createAgent.mutateAsync(payload);
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
      title={isEditing ? "Edit agent" : "New data agent"}
      description="Describe the goal, and the agent will plan how to select only the data that matters for it."
      size="lg"
    >
      {!canSubmit && !isEditing && (
        <p className="mb-4 rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-xs text-warning">
          You need at least one destination and mapping before creating an agent.
        </p>
      )}
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
        <FormField label="Name" htmlFor="agent-name" error={errors.name?.message} required>
          <Input
            id="agent-name"
            placeholder="B2B conversion booster"
            {...register("name")}
          />
        </FormField>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField
            label="Mapping (source table + destination fields)"
            htmlFor="agent-mapping"
            error={errors.mapping_id?.message}
            required
          >
            <Select
              id="agent-mapping"
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
          <FormField
            label="Destination"
            htmlFor="agent-destination"
            error={errors.destination_id?.message}
            required
          >
            <Select
              id="agent-destination"
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
        </div>

        <FormField
          label="Goal"
          htmlFor="agent-goal"
          error={errors.goal?.message}
          hint='What are you trying to achieve? e.g. "Increase conversion rate" or "Move from B2C to B2B segment"'
          required
        >
          <Textarea
            id="agent-goal"
            placeholder="Increase conversion by targeting customers most likely to purchase again"
            {...register("goal")}
          />
        </FormField>

        <FormField
          label="Planned actions"
          htmlFor="agent-actions"
          error={errors.actions?.message}
          hint="How do you plan to act on the selected records? e.g. direct calls, an email campaign"
          required
        >
          <Textarea
            id="agent-actions"
            placeholder="Sales team will call the top candidates directly"
            {...register("actions")}
          />
        </FormField>

        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium">Column notes (optional)</label>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => append({ column: "", description: "" })}
            >
              <Plus className="h-3.5 w-3.5" /> Add note
            </Button>
          </div>
          {fields.length === 0 ? (
            <p className="rounded-md border border-dashed border-border px-3 py-3 text-center text-xs text-muted-foreground">
              Tell the agent why specific columns matter, e.g. "last_purchase_at —
              recency matters for conversion likelihood".
            </p>
          ) : (
            <div className="flex flex-col gap-2">
              {fields.map((field, index) => (
                <div key={field.id} className="flex items-start gap-2">
                  <Input
                    placeholder="column_name"
                    className="w-40 shrink-0"
                    {...register(`feature_notes.${index}.column` as const)}
                  />
                  <Input
                    placeholder="Why this column matters for the goal"
                    {...register(`feature_notes.${index}.description` as const)}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => remove(index)}
                    aria-label="Remove column note"
                    className="shrink-0 text-destructive hover:bg-destructive/10"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>

        <AgentModelPicker
          value={llmModel}
          onChange={(model) =>
            setValue("llm_model", model, { shouldValidate: true, shouldDirty: true })
          }
          error={errors.llm_model?.message}
        />

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <FormField label="Selection strategy" htmlFor="agent-strategy">
            <Select id="agent-strategy" {...register("selection_strategy")}>
              <option value="scoring">Scoring (e.g. purchase probability)</option>
              <option value="clustering">Clustering (segment match)</option>
              <option value="rule_based">Rule-based (explicit criteria)</option>
            </Select>
          </FormField>
          <FormField
            label="Threshold"
            htmlFor="agent-threshold"
            error={errors.selection_threshold?.message}
            hint="0-1, only rows scoring at or above this are loaded"
          >
            <Input
              id="agent-threshold"
              type="number"
              min={0}
              max={1}
              step={0.05}
              {...register("selection_threshold")}
            />
          </FormField>
          <FormField
            label="Incremental field"
            htmlFor="agent-incremental-field"
            hint="Optional, e.g. created_at — only new rows are considered"
          >
            <Input id="agent-incremental-field" {...register("incremental_field")} />
          </FormField>
        </div>

        <FormField
          label="Annotation field"
          htmlFor="agent-annotation-field"
          hint='Optional destination field (e.g. "COMMENTS") to receive a note with the selection score and reason on every record — without this, nothing on the loaded record explains why it was chosen.'
        >
          <Input
            id="agent-annotation-field"
            placeholder="COMMENTS"
            {...register("annotation_field")}
          />
        </FormField>

        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={isSaving} disabled={!canSubmit && !isEditing}>
            {isEditing ? "Save changes" : "Create agent"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
