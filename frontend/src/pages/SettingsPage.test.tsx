import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ThemeProvider } from "@/context/ThemeContext";
import { ToastProvider } from "@/context/ToastContext";
import { SettingsPage } from "@/pages/SettingsPage";

vi.mock("@/api/settings", () => ({
  settingsApi: {
    get: vi.fn(),
    update: vi.fn(),
    getLLMStatus: vi.fn(),
    pullLLMModel: vi.fn(),
    sendTelegramTestMessage: vi.fn(),
  },
}));

import { settingsApi } from "@/api/settings";

const mockedGet = vi.mocked(settingsApi.get);
const mockedUpdate = vi.mocked(settingsApi.update);
const mockedGetLLMStatus = vi.mocked(settingsApi.getLLMStatus);
const mockedSendTelegramTest = vi.mocked(settingsApi.sendTelegramTestMessage);

const BASE_SETTINGS = {
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
};

function renderPage(ui: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <MemoryRouter>{ui}</MemoryRouter>
        </ToastProvider>
      </QueryClientProvider>
    </ThemeProvider>,
  );
}

describe("SettingsPage", () => {
  beforeEach(() => {
    mockedGet.mockReset().mockResolvedValue(BASE_SETTINGS);
    mockedUpdate.mockReset().mockResolvedValue(BASE_SETTINGS);
    mockedGetLLMStatus.mockReset().mockResolvedValue({
      model_present: false,
      pulling: false,
      detail: null,
    });
    mockedSendTelegramTest.mockReset().mockResolvedValue({
      success: true,
      detail: "Test message sent.",
    });
  });

  it("loads and displays the current settings", async () => {
    renderPage(<SettingsPage />);

    expect(await screen.findByLabelText(/poll interval/i)).toHaveValue(30);
  });

  it("disables LLM fields until AI suggestions are enabled", async () => {
    renderPage(<SettingsPage />);

    await screen.findByLabelText(/poll interval/i);
    expect(screen.getByLabelText(/ollama base url/i)).toBeDisabled();
  });

  it("saves changes to the scheduler poll interval", async () => {
    const user = userEvent.setup();
    renderPage(<SettingsPage />);

    const input = await screen.findByLabelText(/poll interval/i);
    await user.clear(input);
    await user.type(input, "60");
    await user.click(screen.getByRole("button", { name: /save settings/i }));

    await waitFor(() => {
      expect(mockedUpdate).toHaveBeenCalledWith(
        expect.objectContaining({ scheduler_poll_interval_seconds: 60 }),
      );
    });
  });

  it("enables the LLM fields when the AI switch is toggled on", async () => {
    const user = userEvent.setup();
    renderPage(<SettingsPage />);

    await screen.findByLabelText(/poll interval/i);
    await user.click(screen.getByLabelText(/ai mapping suggestions enabled/i));

    expect(screen.getByLabelText(/ollama base url/i)).toBeEnabled();
  });

  it("enables the Telegram fields and a test-message button when the switch is on", async () => {
    const user = userEvent.setup();
    renderPage(<SettingsPage />);

    await screen.findByLabelText(/poll interval/i);
    await user.click(screen.getByLabelText(/telegram notifications enabled/i));

    expect(screen.getByLabelText(/bot token/i)).toBeEnabled();
    expect(
      screen.getByRole("button", { name: /send test message/i }),
    ).toBeInTheDocument();
  });

  it("sends a Telegram test message and reports success", async () => {
    const user = userEvent.setup();
    renderPage(<SettingsPage />);

    await screen.findByLabelText(/poll interval/i);
    await user.click(screen.getByLabelText(/telegram notifications enabled/i));
    await user.click(screen.getByRole("button", { name: /send test message/i }));

    await waitFor(() => {
      expect(mockedSendTelegramTest).toHaveBeenCalled();
    });
    expect(await screen.findByText("Test message sent")).toBeInTheDocument();
  });
});
