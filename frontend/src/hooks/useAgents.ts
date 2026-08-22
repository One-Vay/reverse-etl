import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { agentsApi } from "@/api/agents";
import type { ChatMessage, DataAgentInput } from "@/api/types";
import { useToast } from "@/context/ToastContext";
import { queryKeys } from "@/lib/queryClient";
import { getErrorMessage } from "@/lib/utils";

export function useAgents() {
  return useQuery({
    queryKey: queryKeys.agents,
    queryFn: () => agentsApi.list({ limit: 200 }),
  });
}

export function useCreateAgent() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: (input: DataAgentInput) => agentsApi.create(input),
    onSuccess: (agent) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents });
      showToast({
        variant: "success",
        title: "Agent created",
        description: `"${agent.name}" is a draft — generate a plan before running it.`,
      });
    },
    onError: (error) => {
      showToast({
        variant: "error",
        title: "Couldn't create agent",
        description: getErrorMessage(error),
      });
    },
  });
}

export function useUpdateAgent() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: Partial<DataAgentInput> }) =>
      agentsApi.update(id, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents });
      showToast({ variant: "success", title: "Agent updated" });
    },
    onError: (error) => {
      showToast({
        variant: "error",
        title: "Couldn't update agent",
        description: getErrorMessage(error),
      });
    },
  });
}

export function useDeleteAgent() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: (id: number) => agentsApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents });
      showToast({ variant: "success", title: "Agent deleted" });
    },
    onError: (error) => {
      showToast({
        variant: "error",
        title: "Couldn't delete agent",
        description: getErrorMessage(error),
      });
    },
  });
}

/** Asks the agent's configured LLM to analyze its goal against the source
 * table and propose a plan. Failures are usually LLM-side (unreachable,
 * bad response) rather than a form-validation problem, so they're
 * reported with the model name for context. */
export function useGeneratePlan() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: (id: number) => agentsApi.generatePlan(id),
    onSuccess: (agent) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents });
      showToast({
        variant: "success",
        title: "Plan generated",
        description: `"${agent.name}" is ready to run.`,
      });
    },
    onError: (error) => {
      showToast({
        variant: "error",
        title: "Couldn't generate a plan",
        description: getErrorMessage(error),
      });
    },
  });
}

/** Runs an agent immediately and reports its *actual* outcome — the
 * request only rejects for an app-level error (agent not found, no
 * plan yet); a connector/LLM failure during the run still resolves, just
 * with `status: "failed"` on the returned AgentRun. */
export function useRunAgentNow() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: (id: number) => agentsApi.runNow(id),
    onSuccess: (run) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents });
      queryClient.invalidateQueries({ queryKey: queryKeys.agentRuns(run.agent_id) });
      if (run.status === "success") {
        showToast({
          variant: "success",
          title: "Agent run complete",
          description: `${run.rows_written} of ${run.rows_selected} selected record${
            run.rows_selected === 1 ? "" : "s"
          } written (${run.rows_considered} considered).`,
        });
      } else {
        showToast({
          variant: "error",
          title: "Agent run failed",
          description: run.error_message ?? "Unknown error.",
        });
      }
    },
    onError: (error) => {
      showToast({
        variant: "error",
        title: "Couldn't trigger agent run",
        description: getErrorMessage(error),
      });
    },
  });
}

/** Dry-runs the agent's selection step: scores due rows and shows exactly
 * what would be written, without touching the destination or recording a
 * run. Not a query — it's a side-effect-free action the user explicitly
 * triggers each time, so a mutation (not cached) is the right shape. */
export function usePreviewAgent() {
  const { showToast } = useToast();

  return useMutation({
    mutationFn: (id: number) => agentsApi.preview(id),
    onError: (error) => {
      showToast({
        variant: "error",
        title: "Couldn't preview this agent",
        description: getErrorMessage(error),
      });
    },
  });
}

export function useAgentRuns(agentId: number | undefined) {
  return useQuery({
    queryKey: queryKeys.agentRuns(agentId ?? 0),
    queryFn: () => agentsApi.listRuns(agentId as number, { limit: 50 }),
    enabled: agentId != null && agentId > 0,
  });
}

/** Models already pulled onto the configured Ollama server — for the
 * agent form's model picker, independent of the one Settings configures
 * globally. */
export function useAgentModels() {
  return useQuery({
    queryKey: queryKeys.agentModels,
    queryFn: () => agentsApi.listModels(),
  });
}

/** Polls while a model pull might be in progress. */
export function useAgentModelStatus(model: string | undefined) {
  return useQuery({
    queryKey: queryKeys.agentModelStatus(model ?? ""),
    queryFn: () => agentsApi.getModelStatus(model as string),
    enabled: Boolean(model),
    refetchInterval: (query) => (query.state.data?.pulling ? 3000 : false),
  });
}

export function usePullAgentModel() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: (model: string) => agentsApi.pullModel(model),
    onSuccess: (_result, model) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agentModels });
      queryClient.invalidateQueries({ queryKey: queryKeys.agentModelStatus(model) });
      showToast({ variant: "success", title: `Pulling ${model}` });
    },
    onError: (error) => {
      showToast({
        variant: "error",
        title: "Couldn't start model pull",
        description: getErrorMessage(error),
      });
    },
  });
}

/** An agent's chat thread, oldest first. */
export function useAgentMessages(agentId: number | undefined) {
  return useQuery({
    queryKey: queryKeys.agentMessages(agentId ?? 0),
    queryFn: () => agentsApi.listMessages(agentId as number),
    enabled: agentId != null && agentId > 0,
  });
}

/** Sends a chat message to the agent and appends both sides of the
 * exchange to the cached thread — the assistant only ever answers, it
 * never changes the agent's own configuration. */
export function useSendAgentMessage(agentId: number) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: (message: string) => agentsApi.sendMessage(agentId, message),
    onSuccess: (result) => {
      queryClient.setQueryData<ChatMessage[] | undefined>(
        queryKeys.agentMessages(agentId),
        (current) => [...(current ?? []), result.user_message, result.assistant_message],
      );
    },
    onError: (error) => {
      showToast({
        variant: "error",
        title: "Couldn't reach the agent",
        description: getErrorMessage(error),
      });
    },
  });
}
