import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DashboardPage } from "../../src/features/dashboard/DashboardPage";
import { renderWithProviders } from "../test-utils";

const hookMocks = vi.hoisted(() => ({
  useDevices: vi.fn(),
  useDeviceTypes: vi.fn(),
  useCreateDevice: vi.fn(),
  useUpdateDevice: vi.fn(),
  useDeleteDevice: vi.fn(),
  useConfirmDevice: vi.fn(),
}));

vi.mock("../../src/features/dashboard/hooks", () => hookMocks);

describe("DashboardPage", () => {
  beforeEach(() => {
    hookMocks.useCreateDevice.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
    hookMocks.useUpdateDevice.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
    hookMocks.useDeleteDevice.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
    hookMocks.useConfirmDevice.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
  });

  it("shows skeleton while loading", () => {
    hookMocks.useDevices.mockReturnValue({ isLoading: true, isError: false, data: [] });
    hookMocks.useDeviceTypes.mockReturnValue({ isLoading: false, isError: false, data: [] });

    renderWithProviders(<DashboardPage />);

    expect(screen.getByLabelText("Loading stats")).toBeInTheDocument();
  });

  it("renders grouped device cards and zero-device group headings", () => {
    hookMocks.useDevices.mockReturnValue({
      isLoading: false,
      isError: false,
      data: [
        {
          id: 1,
          device_type_id: 1,
          device_type_name: "Sony Bodies",
          name: "Sony A7IV",
          current_version: "2.0",
          latest_seen_version: "3.0",
          last_checked_at: new Date().toISOString(),
          notes: null,
          status: "update_available",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
    });
    hookMocks.useDeviceTypes.mockReturnValue({
      isLoading: false,
      isError: false,
      data: [
        {
          id: 1,
          name: "Sony Bodies",
          firmware_source_url: "https://example.com/sony",
          extension_module_id: null,
          check_frequency_minutes: 360,
          device_count: 1,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        {
          id: 2,
          name: "Sony Lenses",
          firmware_source_url: "https://example.com/lenses",
          extension_module_id: null,
          check_frequency_minutes: 360,
          device_count: 0,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
    });

    renderWithProviders(<DashboardPage />);

    expect(screen.getByText("Sony Bodies")).toBeInTheDocument();
    expect(screen.getByText("Sony Lenses")).toBeInTheDocument();
    expect(screen.getByText("Sony A7IV")).toBeInTheDocument();
  });

  it("refresh button is visible and clickable", async () => {
    const user = userEvent.setup();
    hookMocks.useDevices.mockReturnValue({ isLoading: false, isError: false, data: [] });
    hookMocks.useDeviceTypes.mockReturnValue({ isLoading: false, isError: false, data: [] });

    renderWithProviders(<DashboardPage />);

    const refreshButton = screen.getByRole("button", { name: "Refresh" });
    await user.click(refreshButton);
    expect(refreshButton).toBeInTheDocument();
  });
});
