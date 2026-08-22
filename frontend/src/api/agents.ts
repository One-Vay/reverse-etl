import { api, buildQuery } from "@/api/client";
import type {
  AgentPreview,
  AgentRun,
  ChatMessage,
  ChatResponse,
  DataAgent,
  DataAgentInput,
  LLMModelStatus,
  ListParams,
  ListResponse,
} from "@/api/types";

export const agentsApi = {
  list: (params: ListParams = {}) =>
    api.get<ListResponse<DataAgent>>(`/agents/${buildQuery(params)}`),
  get: (id: number) => api.get<DataAgent>(`/agents/${id}`),
  create: (input: DataAgentInput) => api.post<DataAgent>("/agents/", input),
  update: (id: number, input: Partial<DataAgentInput>) =>
    api.put<DataAgent>(`/agents/${id}`, input),
  remove: (id: number) => api.delete<void>(`/agents/${id}`),
  generatePlan: (id: number) => api.post<DataAgent>(`/agents/${id}/plan`),
  /** Runs synchronously and returns the resulting AgentRun — check
   * `.status`/`.error_message` for whether the run itself succeeded. */
  runNow: (id: number) => api.post<AgentRun>(`/agents/${id}/run`),
  /** Dry-runs the selection step — scores due rows and shows what would
   * be written, without touching the destination or recording a run. */
  preview: (id: number) => api.post<AgentPreview>(`/agents/${id}/preview`),
  listRuns: (id: number, params: ListParams = {}) =>
    api.get<ListResponse<AgentRun>>(`/agents/${id}/runs${buildQuery(params)}`),
  listModels: () => api.get<string[]>("/agents/models"),
  getModelStatus: (model: string) =>
    api.get<LLMModelStatus>(`/agents/models/${encodeURIComponent(model)}/status`),
  pullModel: (model: string) =>
    api.post<{ message: string }>("/agents/models/pull", { model }),
  listMessages: (id: number) => api.get<ChatMessage[]>(`/agents/${id}/messages`),
  sendMessage: (id: number, message: string) =>
    api.post<ChatResponse>(`/agents/${id}/messages`, { message }),
};
