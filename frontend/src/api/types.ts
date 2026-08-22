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
  connect_timeout: number | null;
  command_timeout: number | null;
  min_pool_size: number | null;
  max_pool_size: number | null;
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
  connect_timeout?: number | null;
  command_timeout?: number | null;
  min_pool_size?: number | null;
  max_pool_size?: number | null;
}

export interface Destination {
  id: number;
  name: string;
  type: DestinationType;
  api_url: string;
  request_timeout: number | null;
  created_at: string;
  updated_at: string;
}

export interface DestinationInput {
  name: string;
  type: DestinationType;
  api_url: string;
  auth_token?: string;
  request_timeout?: number | null;
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

export type IntervalUnit = "hours" | "days";

export interface Sync {
  id: number;
  name: string;
  source_id: number;
  destination_id: number;
  mapping_id: number;
  interval_value: number;
  interval_unit: IntervalUnit;
  run_at_time: string | null;
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
  interval_value: number;
  interval_unit: IntervalUnit;
  run_at_time?: string | null;
  incremental_field?: string | null;
  status?: SyncStatus;
}

export interface UpcomingSyncRuns {
  sync_id: number;
  sync_name: string;
  occurrences: string[];
}

export type SyncRunStatus = "running" | "success" | "failed";
export type SyncRunTrigger = "manual" | "scheduled";

export interface SyncRun {
  id: number;
  sync_id: number;
  status: SyncRunStatus;
  trigger: SyncRunTrigger;
  started_at: string;
  finished_at: string | null;
  records_read: number;
  records_written: number;
  error_message: string | null;
  sync_name: string | null;
}

export interface AppSettings {
  scheduler_enabled: boolean;
  scheduler_poll_interval_seconds: number;
  llm_enabled: boolean;
  llm_base_url: string;
  llm_model: string;
  telegram_enabled: boolean;
  telegram_bot_token: string;
  telegram_chat_id: string;
  default_connect_timeout_seconds: number;
  default_request_timeout_seconds: number;
  updated_at: string;
}

export type AppSettingsInput = Partial<Omit<AppSettings, "updated_at">>;

export interface LLMStatus {
  model_present: boolean;
  pulling: boolean;
  detail: string | null;
}

export interface TelegramTestResult {
  success: boolean;
  detail: string | null;
}

export interface SuggestFieldInfo {
  name: string;
  data_type: string;
}

export interface SuggestedFieldPair {
  source_field: string;
  destination_field: string;
  confidence: number;
}

export interface SuggestMappingsResponse {
  pairs: SuggestedFieldPair[];
  message: string | null;
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

export type AgentStatus = "draft" | "ready" | "archived";
export type SelectionStrategy = "scoring" | "clustering" | "rule_based";
export type AgentRunStatus = "running" | "success" | "failed";

export interface FeatureNote {
  column: string;
  description: string;
}

export interface AgentPlan {
  strategy: SelectionStrategy;
  reasoning: string;
  selection_rule: string;
  recommended_threshold: number | null;
  next_actions: string[];
  model: string;
  generated_at: string;
}

export interface DataAgent {
  id: number;
  name: string;
  destination_id: number;
  mapping_id: number;
  goal: string;
  actions: string;
  feature_notes: FeatureNote[];
  llm_model: string;
  selection_strategy: SelectionStrategy;
  selection_threshold: number;
  incremental_field: string | null;
  annotation_field: string | null;
  status: AgentStatus;
  plan: AgentPlan | null;
  plan_generated_at: string | null;
  last_run_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DataAgentInput {
  name: string;
  destination_id: number;
  mapping_id: number;
  goal: string;
  actions: string;
  feature_notes: FeatureNote[];
  llm_model: string;
  selection_strategy: SelectionStrategy;
  selection_threshold: number;
  incremental_field?: string | null;
  annotation_field?: string | null;
}

export interface RowDetail {
  index: number;
  score: number;
  reason: string;
  selected: boolean;
  record: Record<string, unknown> | null;
}

export interface AgentRun {
  id: number;
  agent_id: number;
  agent_name: string | null;
  status: AgentRunStatus;
  started_at: string;
  finished_at: string | null;
  rows_considered: number;
  rows_selected: number;
  rows_written: number;
  selection_summary: string | null;
  row_details: RowDetail[];
  error_message: string | null;
}

export interface AgentPreview {
  rows_considered: number;
  rows_selected: number;
  row_details: RowDetail[];
}

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  id: number;
  agent_id: number;
  role: ChatRole;
  content: string;
  created_at: string;
}

export interface ChatResponse {
  user_message: ChatMessage;
  assistant_message: ChatMessage;
}

export interface LLMModelStatus {
  model: string;
  present: boolean;
  pulling: boolean;
}
