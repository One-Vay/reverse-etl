import { api, buildQuery } from "@/api/client";
import type { ListParams, ListResponse, Sync, SyncInput, SyncRun } from "@/api/types";

export const syncsApi = {
  list: (params: ListParams & { status?: string } = {}) =>
    api.get<ListResponse<Sync>>(`/syncs/${buildQuery(params)}`),
  get: (id: number) => api.get<Sync>(`/syncs/${id}`),
  create: (input: SyncInput) => api.post<Sync>("/syncs/", input),
  update: (id: number, input: Partial<SyncInput>) => api.put<Sync>(`/syncs/${id}`, input),
  remove: (id: number) => api.delete<void>(`/syncs/${id}`),
  /** Runs synchronously and returns the resulting SyncRun — check
   * `.status`/`.error_message` for whether the sync itself succeeded. */
  runNow: (id: number) => api.post<SyncRun>(`/syncs/${id}/run`),
  listRuns: (id: number, params: ListParams = {}) =>
    api.get<ListResponse<SyncRun>>(`/syncs/${id}/runs${buildQuery(params)}`),
  listAllRuns: (params: ListParams = {}) =>
    api.get<ListResponse<SyncRun>>(`/syncs/runs${buildQuery(params)}`),
};
