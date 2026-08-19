import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { settingsApi } from "@/api/settings";
import type { AppSettingsInput } from "@/api/types";
import { useToast } from "@/context/ToastContext";
import { queryKeys } from "@/lib/queryClient";
import { getErrorMessage } from "@/lib/utils";

export function useSettings() {
  return useQuery({
    queryKey: queryKeys.settings,
    queryFn: () => settingsApi.get(),
  });
}

export function useUpdateSettings() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: (input: AppSettingsInput) => settingsApi.update(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.settings });
      queryClient.invalidateQueries({ queryKey: queryKeys.llmStatus });
      showToast({ variant: "success", title: "Settings saved" });
    },
    onError: (error) => {
      showToast({
        variant: "error",
        title: "Couldn't save settings",
        description: getErrorMessage(error),
      });
    },
  });
}

/** Polls while a model pull might be in progress — cheap, local-only
 * request, so a short interval is fine. */
export function useLLMStatus(enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.llmStatus,
    queryFn: () => settingsApi.getLLMStatus(),
    enabled,
    refetchInterval: (query) => (query.state.data?.pulling ? 3000 : false),
  });
}

export function usePullLLMModel() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: () => settingsApi.pullLLMModel(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.llmStatus });
      showToast({ variant: "success", title: "Model pull started" });
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
