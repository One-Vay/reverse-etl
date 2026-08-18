import { api, buildQuery } from "@/api/client";
import type {
  ColumnInfo,
  ConnectionTestResult,
  ListParams,
  ListResponse,
  Source,
  SourceInput,
  TableInfo,
  TablePreview,
} from "@/api/types";

export const sourcesApi = {
  list: (params: ListParams = {}) =>
    api.get<ListResponse<Source>>(`/sources/${buildQuery(params)}`),
  get: (id: number) => api.get<Source>(`/sources/${id}`),
  create: (input: SourceInput) => api.post<Source>("/sources/", input),
  update: (id: number, input: Partial<SourceInput>) =>
    api.put<Source>(`/sources/${id}`, input),
  remove: (id: number) => api.delete<void>(`/sources/${id}`),

  /** Try connecting with a source's stored credentials. Never rejects on a
   * bad connection — inspect `.success` instead, so the UI can show an
   * inline result rather than treating it as an app error. */
  testConnection: (id: number) =>
    api.post<ConnectionTestResult>(`/sources/${id}/test-connection`),

  listTables: (id: number) => api.get<TableInfo[]>(`/sources/${id}/tables`),

  getTableSchema: (id: number, tableName: string, schema = "public") =>
    api.get<ColumnInfo[]>(
      `/sources/${id}/tables/${encodeURIComponent(tableName)}/schema${buildQuery({ schema })}`,
    ),

  previewTable: (
    id: number,
    tableName: string,
    params: { schema?: string; columns?: string[]; limit?: number } = {},
  ) =>
    api.get<TablePreview>(
      `/sources/${id}/tables/${encodeURIComponent(tableName)}/preview${buildQuery({
        schema: params.schema ?? "public",
        columns: params.columns?.join(","),
        limit: params.limit,
      })}`,
    ),
};
