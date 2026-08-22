import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AgentFormModal } from "@/components/agents/AgentFormModal";
import { ToastProvider } from "@/context/ToastContext";

vi.mock("@/api/agents", () => ({
  agentsApi: {
    create: vi.fn(),
    update: vi.fn(),
    listModels: vi.fn(),
    getModelStatus: vi.fn(),
    pullModel: vi.fn(),
  },
}));

import { agentsApi } from "@/api/agents";

const mockedCreate = vi.mocked(agentsApi.create);
const mockedListModels = vi.mocked(agentsApi.listModels);
const mockedGetModelStatus = vi.mocked(agentsApi.getModelStatus);

const DESTINATIONS = [{ id: 1, name: "Bitrix24" }] as never[];
const MAPPINGS = [{ id: 1, name: "Contacts -> Leads" }] as never[];

function renderModal(props: Partial<React.ComponentProps<typeof AgentFormModal>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>{children}</ToastProvider>
    </QueryClientProvider>
  );
  return render(
    <AgentFormModal
      open
      onClose={vi.fn()}
      destinations={DESTINATIONS as never}
      mappings={MAPPINGS as never}
      {...props}
    />,
    { wrapper },
  );
}

describe("AgentFormModal", () => {
  beforeEach(() => {
    mockedCreate.mockReset().mockResolvedValue({ id: 1, name: "Test agent" } as never);
    mockedListModels.mockReset().mockResolvedValue(["qwen2.5:0.5b", "llama3:8b"]);
    mockedGetModelStatus
      .mockReset()
      .mockResolvedValue({ model: "", present: false, pulling: false });
  });

  it("lists installed models in the picker", async () => {
    renderModal();

    const select = await screen.findByLabelText(/^model/i);
    await waitFor(() => {
      expect(select).toHaveTextContent("qwen2.5:0.5b");
      expect(select).toHaveTextContent("llama3:8b");
    });
  });

  it("adds and removes a column note", async () => {
    const user = userEvent.setup();
    renderModal();

    await user.click(await screen.findByRole("button", { name: /add note/i }));
    expect(screen.getByPlaceholderText("column_name")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /remove column note/i }));
    expect(screen.queryByPlaceholderText("column_name")).not.toBeInTheDocument();
  });

  it("submits the form with goal, actions, and selected model", async () => {
    const user = userEvent.setup();
    renderModal();

    await user.type(await screen.findByLabelText(/^name/i), "Conversion booster");
    await user.type(screen.getByLabelText(/^goal/i), "Increase conversion");
    await user.type(screen.getByLabelText(/planned actions/i), "Direct calls");
    await user.selectOptions(screen.getByLabelText(/^model/i), "qwen2.5:0.5b");
    await user.click(screen.getByRole("button", { name: /create agent/i }));

    await waitFor(() => {
      expect(mockedCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "Conversion booster",
          goal: "Increase conversion",
          actions: "Direct calls",
          llm_model: "qwen2.5:0.5b",
        }),
      );
    });
  });
});
