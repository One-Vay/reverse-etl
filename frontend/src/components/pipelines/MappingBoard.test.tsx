import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MappingBoard } from "@/components/pipelines/MappingBoard";
import { ToastProvider } from "@/context/ToastContext";

vi.mock("@/api/sources", () => ({
  sourcesApi: {
    getTableSchema: vi.fn(),
  },
}));
vi.mock("@/api/destinations", () => ({
  destinationsApi: {
    getEntityFields: vi.fn(),
  },
}));
vi.mock("@/api/settings", () => ({
  settingsApi: {
    get: vi.fn(),
    getLLMStatus: vi.fn(),
  },
}));
vi.mock("@/api/mappings", () => ({
  mappingsApi: {
    suggest: vi.fn(),
  },
}));

import { sourcesApi } from "@/api/sources";
import { destinationsApi } from "@/api/destinations";
import { settingsApi } from "@/api/settings";

const mockedGetTableSchema = vi.mocked(sourcesApi.getTableSchema);
const mockedGetEntityFields = vi.mocked(destinationsApi.getEntityFields);
const mockedGetSettings = vi.mocked(settingsApi.get);

function makeSettings(overrides: Partial<Awaited<ReturnType<typeof settingsApi.get>>> = {}) {
  return {
    scheduler_enabled: true,
    scheduler_poll_interval_seconds: 30,
    llm_enabled: false,
    llm_base_url: "http://ollama:11434",
    llm_model: "qwen2.5:0.5b",
    telegram_enabled: false,
    telegram_bot_token: "",
    telegram_chat_id: "",
    default_connect_timeout_seconds: 10,
    default_request_timeout_seconds: 30,
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

const SOURCE_COLUMNS = [
  { name: "id", data_type: "integer", nullable: false, is_primary_key: true },
  { name: "email", data_type: "text", nullable: false, is_primary_key: false },
  { name: "full_name", data_type: "text", nullable: true, is_primary_key: false },
];

const DESTINATION_FIELDS = [
  { name: "ID", data_type: "integer", nullable: false, is_primary_key: true },
  { name: "EMAIL", data_type: "string", nullable: false, is_primary_key: false },
  { name: "TITLE", data_type: "string", nullable: true, is_primary_key: false },
];

function renderWithClient(ui: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>{ui}</ToastProvider>
    </QueryClientProvider>,
  );
}

describe("MappingBoard", () => {
  beforeEach(() => {
    mockedGetTableSchema.mockReset().mockResolvedValue(SOURCE_COLUMNS);
    mockedGetEntityFields.mockReset().mockResolvedValue(DESTINATION_FIELDS);
    mockedGetSettings.mockReset().mockResolvedValue(makeSettings());
  });

  const baseProps = {
    sourceId: 1,
    table: "contacts",
    destinationId: 2,
    entity: "lead",
    fieldMappings: [],
    onConnect: vi.fn(),
    onDisconnect: vi.fn(),
  };

  it("renders nothing until a source table and destination entity are both chosen", () => {
    renderWithClient(
      <MappingBoard
        {...baseProps}
        table={undefined}
        onConnect={vi.fn()}
        onDisconnect={vi.fn()}
      />,
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("renders the source columns and destination fields once loaded", async () => {
    renderWithClient(<MappingBoard {...baseProps} />);

    expect(await screen.findByRole("button", { name: /email/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /EMAIL/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /full_name/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /TITLE/ })).toBeInTheDocument();
  });

  it("connects a source column and a destination field via click-to-arm", async () => {
    const user = userEvent.setup();
    const onConnect = vi.fn();
    renderWithClient(<MappingBoard {...baseProps} onConnect={onConnect} />);

    const sourceChip = await screen.findByRole("button", { name: /^email/ });
    await user.click(sourceChip);
    expect(screen.getByText(/"email" selected/)).toBeInTheDocument();

    const destinationChip = screen.getByRole("button", { name: /EMAIL/ });
    await user.click(destinationChip);

    expect(onConnect).toHaveBeenCalledWith("email", "EMAIL");
  });

  it("clicking the armed source column again cancels the selection", async () => {
    const user = userEvent.setup();
    renderWithClient(<MappingBoard {...baseProps} />);

    const sourceChip = await screen.findByRole("button", { name: /^email/ });
    await user.click(sourceChip);
    expect(screen.getByText(/"email" selected/)).toBeInTheDocument();

    await user.click(sourceChip);
    expect(screen.queryByText(/"email" selected/)).not.toBeInTheDocument();
  });

  it("clicking an already-connected source column disconnects it", async () => {
    const user = userEvent.setup();
    const onDisconnect = vi.fn();
    renderWithClient(
      <MappingBoard
        {...baseProps}
        fieldMappings={[{ source_field: "email", destination_field: "EMAIL" }]}
        onDisconnect={onDisconnect}
      />,
    );

    const sourceChip = await screen.findByRole("button", { name: /^email/ });
    await user.click(sourceChip);

    expect(onDisconnect).toHaveBeenCalledWith("email");
  });

  it("clicking an already-connected destination field disconnects its source", async () => {
    const user = userEvent.setup();
    const onDisconnect = vi.fn();
    renderWithClient(
      <MappingBoard
        {...baseProps}
        fieldMappings={[{ source_field: "email", destination_field: "EMAIL" }]}
        onDisconnect={onDisconnect}
      />,
    );

    const destinationChip = await screen.findByRole("button", { name: /EMAIL/ });
    await user.click(destinationChip);

    expect(onDisconnect).toHaveBeenCalledWith("email");
  });

  it("shows a shared pair badge on both sides of a connected mapping", async () => {
    renderWithClient(
      <MappingBoard
        {...baseProps}
        fieldMappings={[{ source_field: "email", destination_field: "EMAIL" }]}
      />,
    );

    const sourceChip = await screen.findByRole("button", { name: /^email/ });
    const destinationChip = screen.getByRole("button", { name: /EMAIL/ });
    expect(sourceChip).toHaveTextContent("1");
    expect(destinationChip).toHaveTextContent("1");
  });

  it("connects fields on drop", async () => {
    const onConnect = vi.fn();
    renderWithClient(<MappingBoard {...baseProps} onConnect={onConnect} />);

    const destinationChip = await screen.findByRole("button", { name: /EMAIL/ });
    const dataTransfer = {
      getData: vi.fn().mockReturnValue("email"),
      setData: vi.fn(),
      dropEffect: "",
    };
    const dropEvent = new Event("drop", { bubbles: true, cancelable: true }) as Event & {
      dataTransfer: typeof dataTransfer;
    };
    Object.defineProperty(dropEvent, "dataTransfer", { value: dataTransfer });
    destinationChip.dispatchEvent(dropEvent);

    await waitFor(() => {
      expect(onConnect).toHaveBeenCalledWith("email", "EMAIL");
    });
  });

  it("shows an error message when either side fails to load", async () => {
    mockedGetTableSchema.mockReset().mockRejectedValue(new Error("boom"));
    renderWithClient(<MappingBoard {...baseProps} />);

    expect(await screen.findByText(/Couldn't load fields/)).toBeInTheDocument();
  });

  describe("AI suggestions", () => {
    it("disables the suggest button when AI suggestions are off", async () => {
      renderWithClient(<MappingBoard {...baseProps} />);

      const button = await screen.findByRole("button", { name: /suggest with ai/i });
      expect(button).toBeDisabled();
    });

    it("applies suggested pairs above the confidence threshold", async () => {
      mockedGetSettings.mockResolvedValue(makeSettings({ llm_enabled: true }));
      const { mappingsApi } = await import("@/api/mappings");
      vi.mocked(mappingsApi.suggest).mockResolvedValue({
        pairs: [
          { source_field: "email", destination_field: "EMAIL", confidence: 0.9 },
          { source_field: "id", destination_field: "ID", confidence: 0.2 },
        ],
        message: null,
      });
      const onConnect = vi.fn();
      const user = userEvent.setup();
      renderWithClient(<MappingBoard {...baseProps} onConnect={onConnect} />);

      const button = await screen.findByRole("button", { name: /suggest with ai/i });
      await waitFor(() => expect(button).not.toBeDisabled());
      await user.click(button);

      await waitFor(() => {
        expect(onConnect).toHaveBeenCalledWith("email", "EMAIL");
      });
      expect(onConnect).not.toHaveBeenCalledWith("id", "ID");
      expect(await screen.findByText(/applied 1 ai suggestion/i)).toBeInTheDocument();
    });

    it("shows an info toast when every suggestion is already mapped", async () => {
      mockedGetSettings.mockResolvedValue(makeSettings({ llm_enabled: true }));
      const { mappingsApi } = await import("@/api/mappings");
      vi.mocked(mappingsApi.suggest).mockResolvedValue({
        pairs: [{ source_field: "email", destination_field: "EMAIL", confidence: 0.9 }],
        message: null,
      });
      const onConnect = vi.fn();
      const user = userEvent.setup();
      renderWithClient(
        <MappingBoard
          {...baseProps}
          fieldMappings={[{ source_field: "email", destination_field: "EMAIL" }]}
          onConnect={onConnect}
        />,
      );

      const button = await screen.findByRole("button", { name: /suggest with ai/i });
      await waitFor(() => expect(button).not.toBeDisabled());
      await user.click(button);

      expect(await screen.findByText(/nothing new to suggest/i)).toBeInTheDocument();
      expect(onConnect).not.toHaveBeenCalled();
    });
  });
});
