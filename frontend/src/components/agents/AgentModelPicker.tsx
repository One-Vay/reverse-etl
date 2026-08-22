import { Download } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import {
  useAgentModelStatus,
  useAgentModels,
  usePullAgentModel,
} from "@/hooks/useAgents";

interface AgentModelPickerProps {
  value: string;
  onChange: (model: string) => void;
  error?: string;
}

/** Lets an agent pick any Ollama model already installed, or pull a new
 * one by name — independent of the single model Settings configures
 * globally, since each agent can reason with a different one. */
export function AgentModelPicker({ value, onChange, error }: AgentModelPickerProps) {
  const modelsQuery = useAgentModels();
  const [newModelName, setNewModelName] = useState("");
  const pullModel = usePullAgentModel();
  const pullStatusQuery = useAgentModelStatus(newModelName || undefined);

  const installed = modelsQuery.data ?? [];

  const handlePull = async () => {
    const name = newModelName.trim();
    if (!name) return;
    await pullModel.mutateAsync(name);
  };

  return (
    <div className="flex flex-col gap-2">
      <FormField
        label="Model"
        htmlFor="agent-llm-model"
        error={error}
        hint="Runs entirely locally via Ollama — pick one already installed, or pull a new one below."
        required
      >
        <Select
          id="agent-llm-model"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={modelsQuery.isLoading}
        >
          <option value="">
            {modelsQuery.isLoading ? "Loading installed models…" : "Select a model"}
          </option>
          {value && !installed.includes(value) && (
            <option value={value}>{value} (not yet installed)</option>
          )}
          {installed.map((model) => (
            <option key={model} value={model}>
              {model}
            </option>
          ))}
        </Select>
      </FormField>

      <div className="flex items-end gap-2">
        <div className="flex-1">
          <FormField
            label="Pull a new model"
            htmlFor="agent-model-pull-name"
            hint="e.g. llama3:8b, qwen2.5:7b — any name Ollama recognizes"
          >
            <Input
              id="agent-model-pull-name"
              placeholder="llama3:8b"
              value={newModelName}
              onChange={(e) => setNewModelName(e.target.value)}
            />
          </FormField>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          loading={pullModel.isPending || pullStatusQuery.data?.pulling}
          disabled={!newModelName.trim()}
          onClick={handlePull}
        >
          <Download className="h-3.5 w-3.5" /> Pull
        </Button>
      </div>
      {newModelName && pullStatusQuery.data && (
        <p className="text-xs text-muted-foreground">
          {pullStatusQuery.data.pulling
            ? `Downloading ${newModelName}…`
            : pullStatusQuery.data.present
              ? `${newModelName} is ready — select it above.`
              : `${newModelName} isn't installed yet.`}
        </p>
      )}
    </div>
  );
}
