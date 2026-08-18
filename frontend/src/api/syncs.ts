import { api, buildQuery } from "@/api/client";
import type { ListParams, ListResponse, Sync, SyncInput } from "@/api/types";

export const syncsApi = {
  list: (params: ListParams & { status?: string } = {}) =>
    api.get<ListResponse<Sync>>(`/syncs/${buildQuery(params)}`),
  get: (id: number) => api.get<Sync>(`/syncs/${id}`),
  create: (input: SyncInput) => api.post<Sync>("/syncs/", input),
  update: (id: number, input: Partial<SyncInput>) => api.put<Sync>(`/syncs/${id}`, input),
  remove: (id: number) => api.delete<void>(`/syncs/${id}`),
  runNow: (id: number) => api.post<{ message: string }>(`/syncs/${id}/run`),
};
