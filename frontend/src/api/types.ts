/**
 * Types mirroring the backend Pydantic schemas
 * (backend/app/features/*\/schemas.py). Keep in sync with the API.
 */

export type SourceType = "postgres" | "clickhouse";
export type DestinationType = "bitrix24" | "amocrm";
export type SyncStatus = "active" | "paused" | "inactive";

export interface Source {
  id: number;
  name: string;
  type: SourceType;
  host: string;
  port: number;
  database: string;
  username: string;
  created_at: string;
  updated_at: string;
}

export interface SourceInput {
  name: string;
  type: SourceType;
  host: string;
  port: number;
  database: string;
  username: string;
  password?: string;
}

export interface Destination {
  id: number;
  name: string;
  type: DestinationType;
  api_url: string;
  created_at: string;
  updated_at: string;
}

export interface DestinationInput {
  name: string;
  type: DestinationType;
  api_url: string;
  auth_token?: string;
}

export interface FieldMapping {
  source_field: string;
  destination_field: string;
  transformation?: string | null;
}

export interface Mapping {
  id: number;
  name: string;
  source_id: number;
  source_table: string;
  destination_entity: string;
  field_mappings: FieldMapping[];
  created_at: string;
  updated_at: string;
}

export interface MappingInput {
  name: string;
  source_id: number;
  source_table: string;
  destination_entity: string;
  field_mappings: FieldMapping[];
}

export interface Sync {
  id: number;
  name: string;
  source_id: number;
  destination_id: number;
  mapping_id: number;
  schedule: string;
  incremental_field: string | null;
  last_run: string | null;
  next_run: string | null;
  status: SyncStatus;
  created_at: string;
  updated_at: string;
  source?: Source | null;
  destination?: Destination | null;
  mapping?: Mapping | null;
}

export interface SyncInput {
  name: string;
  source_id: number;
  destination_id: number;
  mapping_id: number;
  schedule: string;
  incremental_field?: string | null;
  status?: SyncStatus;
}

export interface TableInfo {
  name: string;
  schema: string;
  kind: "table" | "view";
}

export interface ColumnInfo {
  name: string;
  data_type: string;
  nullable: boolean;
  is_primary_key: boolean;
}

export interface ConnectionTestResult {
  success: boolean;
  message: string;
}

export interface TablePreview {
  columns: string[];
  rows: Record<string, unknown>[];
}

export interface ListResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export interface ListParams {
  skip?: number;
  limit?: number;
  search?: string;
  // Lets ListParams (and types that extend it, e.g. `ListParams & { status?: string }`)
  // satisfy buildQuery's `Record<string, string | number | undefined>` parameter type.
  [key: string]: string | number | undefined;
}
