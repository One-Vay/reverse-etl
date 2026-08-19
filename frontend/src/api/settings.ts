import { api } from "@/api/client";
import type { AppSettings, AppSettingsInput, LLMStatus } from "@/api/types";

export const settingsApi = {
  get: () => api.get<AppSettings>("/settings/"),
  update: (input: AppSettingsInput) => api.put<AppSettings>("/settings/", input),
  getLLMStatus: () => api.get<LLMStatus>("/settings/llm/status"),
  pullLLMModel: () => api.post<{ message: string }>("/settings/llm/pull"),
};
