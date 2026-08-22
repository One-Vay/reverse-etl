import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { UpcomingRunsTimeline } from "@/components/dashboard/UpcomingRunsTimeline";

vi.mock("@/api/syncs", () => ({
  syncsApi: {
    upcoming: vi.fn(),
  },
}));

import { syncsApi } from "@/api/syncs";

const mockedUpcoming = vi.mocked(syncsApi.upcoming);

function renderWithProviders(ui: ReactNode) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("UpcomingRunsTimeline", () => {
  beforeEach(() => {
    mockedUpcoming.mockReset();
  });

  it("shows an empty state when nothing is scheduled", async () => {
    mockedUpcoming.mockResolvedValue([]);
    renderWithProviders(<UpcomingRunsTimeline />);

    expect(await screen.findByText(/nothing scheduled/i)).toBeInTheDocument();
  });

  it("places a today's occurrence in the Today column", async () => {
    const inOneHour = new Date(Date.now() + 60 * 60 * 1000).toISOString();
    mockedUpcoming.mockResolvedValue([
      { sync_id: 1, sync_name: "Contacts sync", occurrences: [inOneHour] },
    ]);
    renderWithProviders(<UpcomingRunsTimeline />);

    expect(await screen.findByText("Today")).toBeInTheDocument();
    expect(screen.getByText("Contacts sync")).toBeInTheDocument();
  });
});
