import { describe, expect, it } from "vitest";

import {
  agentSchema,
  destinationSchema,
  mappingSchema,
  sourceSchema,
  syncSchema,
} from "./schemas";

const validSource = {
  name: "Production Postgres",
  type: "postgres",
  host: "db.internal",
  port: 5432,
  database: "analytics",
  username: "etl_user",
  password: "secret",
};

describe("sourceSchema", () => {
  it("accepts a fully-populated source", () => {
    expect(sourceSchema.safeParse(validSource).success).toBe(true);
  });

  it("rejects a blank name", () => {
    const result = sourceSchema.safeParse({ ...validSource, name: "" });
    expect(result.success).toBe(false);
  });

  it("rejects a port outside the valid TCP range", () => {
    expect(sourceSchema.safeParse({ ...validSource, port: 0 }).success).toBe(false);
    expect(sourceSchema.safeParse({ ...validSource, port: 70000 }).success).toBe(false);
  });

  it("coerces a string port from a form input into a number", () => {
    const result = sourceSchema.safeParse({ ...validSource, port: "5432" });
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.port).toBe(5432);
  });

  it("rejects a type outside the known enum", () => {
    const result = sourceSchema.safeParse({ ...validSource, type: "mysql" });
    expect(result.success).toBe(false);
  });

  it("allows an empty password (edit flow: blank means 'keep current')", () => {
    const result = sourceSchema.safeParse({ ...validSource, password: "" });
    expect(result.success).toBe(true);
  });
});

describe("destinationSchema", () => {
  const validDestination = {
    name: "Sales Bitrix24",
    type: "bitrix24",
    api_url: "https://example.bitrix24.ru/rest/",
    auth_token: "token",
  };

  it("accepts a fully-populated destination", () => {
    expect(destinationSchema.safeParse(validDestination).success).toBe(true);
  });

  it("rejects a non-URL api_url", () => {
    const result = destinationSchema.safeParse({
      ...validDestination,
      api_url: "not-a-url",
    });
    expect(result.success).toBe(false);
  });
});

describe("mappingSchema", () => {
  const validMapping = {
    name: "Contacts to leads",
    source_id: 1,
    source_table: "contacts",
    destination_entity: "leads",
    field_mappings: [{ source_field: "email", destination_field: "EMAIL" }],
  };

  it("accepts a mapping with at least one field mapping", () => {
    expect(mappingSchema.safeParse(validMapping).success).toBe(true);
  });

  it("rejects a mapping with zero field mappings", () => {
    // Regression check for a real bug: the backend rejects an empty
    // field_mappings list with a raw 422, so the client must catch this
    // before ever sending the request.
    const result = mappingSchema.safeParse({ ...validMapping, field_mappings: [] });
    expect(result.success).toBe(false);
  });

  it("rejects a field mapping missing a destination field", () => {
    const result = mappingSchema.safeParse({
      ...validMapping,
      field_mappings: [{ source_field: "email", destination_field: "" }],
    });
    expect(result.success).toBe(false);
  });

  it("rejects source_id of 0 (the 'no source selected' sentinel)", () => {
    const result = mappingSchema.safeParse({ ...validMapping, source_id: 0 });
    expect(result.success).toBe(false);
  });
});

describe("syncSchema", () => {
  const validSync = {
    name: "Hourly contacts sync",
    source_id: 1,
    destination_id: 1,
    mapping_id: 1,
    interval_value: 1,
    interval_unit: "hours",
  };

  it("accepts a valid sync and defaults status to active", () => {
    const result = syncSchema.safeParse(validSync);
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.status).toBe("active");
  });

  it("rejects an interval value of 0", () => {
    const result = syncSchema.safeParse({ ...validSync, interval_value: 0 });
    expect(result.success).toBe(false);
  });

  it("rejects an hours interval above 168", () => {
    const result = syncSchema.safeParse({ ...validSync, interval_value: 200 });
    expect(result.success).toBe(false);
  });

  it("accepts a days interval with a valid run_at_time", () => {
    const result = syncSchema.safeParse({
      ...validSync,
      interval_unit: "days",
      interval_value: 1,
      run_at_time: "09:00",
    });
    expect(result.success).toBe(true);
  });

  it("rejects a malformed run_at_time", () => {
    const result = syncSchema.safeParse({
      ...validSync,
      interval_unit: "days",
      run_at_time: "not-a-time",
    });
    expect(result.success).toBe(false);
  });

  it("rejects a status outside the known enum", () => {
    const result = syncSchema.safeParse({ ...validSync, status: "archived" });
    expect(result.success).toBe(false);
  });
});

describe("agentSchema", () => {
  const validAgent = {
    name: "Conversion booster",
    destination_id: 1,
    mapping_id: 1,
    goal: "Increase conversion",
    actions: "Direct calls",
    llm_model: "qwen2.5:0.5b",
    selection_strategy: "scoring",
    selection_threshold: 0.6,
  };

  it("accepts a valid agent and defaults feature_notes to an empty array", () => {
    const result = agentSchema.safeParse(validAgent);
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.feature_notes).toEqual([]);
  });

  it("rejects a blank goal", () => {
    const result = agentSchema.safeParse({ ...validAgent, goal: "" });
    expect(result.success).toBe(false);
  });

  it("rejects a blank llm_model", () => {
    const result = agentSchema.safeParse({ ...validAgent, llm_model: "" });
    expect(result.success).toBe(false);
  });

  it("rejects a threshold outside 0-1", () => {
    const result = agentSchema.safeParse({ ...validAgent, selection_threshold: 1.5 });
    expect(result.success).toBe(false);
  });

  it("rejects an unknown selection strategy", () => {
    const result = agentSchema.safeParse({
      ...validAgent,
      selection_strategy: "guessing",
    });
    expect(result.success).toBe(false);
  });

  it("accepts feature notes with column and description", () => {
    const result = agentSchema.safeParse({
      ...validAgent,
      feature_notes: [{ column: "last_purchase_at", description: "recency matters" }],
    });
    expect(result.success).toBe(true);
  });

  it("rejects a feature note missing a description", () => {
    const result = agentSchema.safeParse({
      ...validAgent,
      feature_notes: [{ column: "last_purchase_at", description: "" }],
    });
    expect(result.success).toBe(false);
  });
});
