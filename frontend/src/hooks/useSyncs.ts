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

/** Runs a sync immediately and reports its *actual* outcome — the request
 * only rejects for an app-level error (sync not found); a connector
 * failure (bad credentials, unreachable host, ...) still resolves, just
 * with `status: "failed"` on the returned SyncRun, so it's surfaced here
 * as an error toast rather than a false "success". */
export function useRunSyncNow() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: (id: number) => syncsApi.runNow(id),
    onSuccess: (run) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.syncs });
      queryClient.invalidateQueries({ queryKey: queryKeys.allSyncRuns });
      queryClient.invalidateQueries({ queryKey: queryKeys.syncRuns(run.sync_id) });
      if (run.status === "success") {
        showToast({
          variant: "success",
          title: "Pipeline ran successfully",
          description: `${run.records_written} of ${run.records_read} record${
            run.records_read === 1 ? "" : "s"
          } written.`,
        });
      } else {
        showToast({
          variant: "error",
          title: "Pipeline run failed",
          description: run.error_message ?? "Unknown error.",
        });
      }
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

/** Run history for one pipeline, for its detail view. */
export function useSyncRuns(syncId: number | undefined) {
  return useQuery({
    queryKey: queryKeys.syncRuns(syncId ?? 0),
    queryFn: () => syncsApi.listRuns(syncId as number, { limit: 50 }),
    enabled: syncId != null && syncId > 0,
  });
}

/** Run history across every pipeline, for the dashboard. */
export function useAllSyncRuns() {
  return useQuery({
    queryKey: queryKeys.allSyncRuns,
    queryFn: () => syncsApi.listAllRuns({ limit: 100 }),
  });
}
