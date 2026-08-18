import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { syncsApi } from "@/api/syncs";
import type { SyncInput, SyncStatus } from "@/api/types";
import { useToast } from "@/context/ToastContext";
import { queryKeys } from "@/lib/queryClient";
import { getErrorMessage } from "@/lib/utils";

export function useSyncs() {
  return useQuery({
    queryKey: queryKeys.syncs,
    queryFn: () => syncsApi.list({ limit: 200 }),
  });
}

export function useCreateSync() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: (input: SyncInput) => syncsApi.create(input),
    onSuccess: (sync) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.syncs });
      showToast({
        variant: "success",
        title: "Pipeline created",
        description: `"${sync.name}" scheduled: ${sync.schedule}.`,
      });
    },
    onError: (error) => {
      showToast({
        variant: "error",
        title: "Couldn't create pipeline",
        description: getErrorMessage(error),
      });
    },
  });
}

export function useUpdateSync() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: Partial<SyncInput> }) =>
      syncsApi.update(id, input),
    onSuccess: (sync) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.syncs });
      showToast({
        variant: "success",
        title: "Pipeline updated",
        description: `"${sync.name}" saved.`,
      });
    },
    onError: (error) => {
      showToast({
        variant: "error",
        title: "Couldn't update pipeline",
        description: getErrorMessage(error),
      });
    },
  });
}

/** Toggle a sync between active/paused without a success toast — used for the
 * dashboard scheduler switch, which already gives its own visual feedback. */
export function useToggleSyncStatus() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: SyncStatus }) =>
      syncsApi.update(id, { status }),
    onMutate: async ({ id, status }) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.syncs });
      const previous = queryClient.getQueryData(queryKeys.syncs);
      queryClient.setQueryData<Awaited<ReturnType<typeof syncsApi.list>> | undefined>(
        queryKeys.syncs,
        (current) => {
          if (!current) return current;
          return {
            ...current,
            items: current.items.map((sync) =>
              sync.id === id ? { ...sync, status } : sync,
            ),
          };
        },
      );
      return { previous };
    },
    onError: (error, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.syncs, context.previous);
      }
      showToast({
        variant: "error",
        title: "Couldn't change schedule state",
        description: getErrorMessage(error),
      });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.syncs });
    },
  });
}

export function useDeleteSync() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: (id: number) => syncsApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.syncs });
      showToast({ variant: "success", title: "Pipeline deleted" });
    },
    onError: (error) => {
      showToast({
        variant: "error",
        title: "Couldn't delete pipeline",
        description: getErrorMessage(error),
      });
    },
  });
}

export function useRunSyncNow() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: (id: number) => syncsApi.runNow(id),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.syncs });
      showToast({
        variant: "success",
        title: "Pipeline triggered",
        description: result.message,
      });
    },
    onError: (error) => {
      showToast({
        variant: "error",
        title: "Couldn't trigger pipeline",
        description: getErrorMessage(error),
      });
    },
  });
}
