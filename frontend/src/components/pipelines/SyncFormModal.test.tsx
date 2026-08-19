import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SyncFormModal } from "@/components/pipelines/SyncFormModal";
import { ToastProvider } from "@/context/ToastContext";

vi.mock("@/api/syncs", () => ({
  syncsApi: {
    create: vi.fn(),
    update: vi.fn(),
  },
}));

import { syncsApi } from "@/api/syncs";

const mockedCreate = vi.mocked(syncsApi.create);
const mockedUpdate = vi.mocked(syncsApi.update);

const SOURCES = [{ id: 1, name: "Postgres" }] as never[];
const DESTINATIONS = [{ id: 1, name: "Bitrix24" }] as never[];
const MAPPINGS = [{ id: 1, name: "Contacts -> Leads" }] as never[];

function renderModal(props: Partial<React.ComponentProps<typeof SyncFormModal>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>{children}</ToastProvider>
    </QueryClientProvider>
  );
  return render(
    <SyncFormModal
      open
      onClose={vi.fn()}
      sources={SOURCES as never}
      destinations={DESTINATIONS as never}
      mappings={MAPPINGS as never}
      {...props}
    />,
    { wrapper },
  );
}

describe("SyncFormModal", () => {
  beforeEach(() => {
    mockedCreate.mockReset().mockResolvedValue({
      id: 1,
      name: "Test sync",
      source_id: 1,
      destination_id: 1,
      mapping_id: 1,
      interval_value: 1,
      interval_unit: "hours",
      run_at_time: null,
      incremental_field: null,
      last_run: null,
      next_run: null,
      status: "active",
      created_at: "",
      updated_at: "",
    } as never);
    mockedUpdate.mockReset().mockResolvedValue({} as never);
  });

  it("defaults to an hourly interval with no time field shown", async () => {
    renderModal();

    expect(await screen.findByLabelText(/unit/i)).toHaveValue("hours");
    expect(screen.queryByLabelText(/at time/i)).not.toBeInTheDocument();
  });

  it("shows the time-of-day field only when the unit is days", async () => {
    const user = userEvent.setup();
    renderModal();

    await user.selectOptions(await screen.findByLabelText(/unit/i), "days");

    expect(screen.getByLabelText(/at time/i)).toBeInTheDocument();
  });

  it("submits the interval fields on create", async () => {
    const user = userEvent.setup();
    renderModal();

    await user.type(await screen.findByLabelText(/^name/i), "Nightly sync");
    await user.selectOptions(screen.getByLabelText(/unit/i), "days");
    await user.clear(screen.getByLabelText(/at time/i));
    await user.type(screen.getByLabelText(/at time/i), "02:30");
    await user.click(screen.getByRole("button", { name: /create pipeline/i }));

    await waitFor(() => {
      expect(mockedCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          interval_value: 1,
          interval_unit: "days",
          run_at_time: "02:30",
        }),
      );
    });
  });
});
