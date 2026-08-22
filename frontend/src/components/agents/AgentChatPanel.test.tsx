import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AgentChatPanel } from "@/components/agents/AgentChatPanel";
import { ToastProvider } from "@/context/ToastContext";

vi.mock("@/api/agents", () => ({
  agentsApi: {
    listMessages: vi.fn(),
    sendMessage: vi.fn(),
  },
}));

import { agentsApi } from "@/api/agents";

const mockedListMessages = vi.mocked(agentsApi.listMessages);
const mockedSendMessage = vi.mocked(agentsApi.sendMessage);

function renderPanel() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>{children}</ToastProvider>
    </QueryClientProvider>
  );
  return render(<AgentChatPanel agentId={1} />, { wrapper });
}

describe("AgentChatPanel", () => {
  beforeEach(() => {
    mockedListMessages.mockReset().mockResolvedValue([]);
    mockedSendMessage.mockReset();
  });

  it("shows an empty state with no messages", async () => {
    renderPanel();
    expect(await screen.findByText(/no messages yet/i)).toBeInTheDocument();
  });

  it("renders existing messages", async () => {
    mockedListMessages.mockResolvedValue([
      { id: 1, agent_id: 1, role: "user", content: "Why no name?", created_at: new Date().toISOString() },
      {
        id: 2,
        agent_id: 1,
        role: "assistant",
        content: "Map full_name to NAME too.",
        created_at: new Date().toISOString(),
      },
    ]);
    renderPanel();

    expect(await screen.findByText("Why no name?")).toBeInTheDocument();
    expect(screen.getByText("Map full_name to NAME too.")).toBeInTheDocument();
  });

  it("sends a message and appends the exchange", async () => {
    const user = userEvent.setup();
    const now = new Date().toISOString();
    mockedSendMessage.mockResolvedValue({
      user_message: { id: 1, agent_id: 1, role: "user", content: "hello", created_at: now },
      assistant_message: {
        id: 2,
        agent_id: 1,
        role: "assistant",
        content: "Hi, how can I help?",
        created_at: now,
      },
    });
    renderPanel();

    await screen.findByText(/no messages yet/i);
    const textbox = screen.getByPlaceholderText(/ask a question/i);
    await user.type(textbox, "hello");
    await user.click(screen.getByRole("button", { name: /send message/i }));

    await waitFor(() => {
      expect(mockedSendMessage).toHaveBeenCalledWith(1, "hello");
    });
    expect(await screen.findByText("Hi, how can I help?")).toBeInTheDocument();
  });
});
