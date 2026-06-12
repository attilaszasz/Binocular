import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { InventoryPage } from "./inventory";
import { vi, describe, it, expect, beforeEach } from "vitest";

// Mock the hooks
const mockUseDevices = vi.fn();
const mockUseCreateDevice = vi.fn();
const mockUseUpdateDevice = vi.fn();
const mockUseDeleteDevice = vi.fn();
const mockUseConfirmUpdate = vi.fn();
const mockUseCheckBulk = vi.fn();

vi.mock("@/hooks/use-devices", () => ({
  useDevices: () => mockUseDevices(),
  useCreateDevice: () => mockUseCreateDevice(),
  useUpdateDevice: () => mockUseUpdateDevice(),
  useDeleteDevice: () => mockUseDeleteDevice(),
  useConfirmUpdate: () => mockUseConfirmUpdate(),
  useCheckBulk: () => mockUseCheckBulk(),
}));

import type { Device } from "@/lib/api";

// Mock child components that are not critical for layout testing
vi.mock("@/components/inventory/device-card", () => ({
  DeviceCard: ({ device }: { device: Device }) => <div data-testid="device-card">{device.name}</div>,
}));
vi.mock("@/components/inventory/device-form", () => ({
  DeviceForm: () => <div>Device Form</div>,
}));
vi.mock("@/components/inventory/empty-state", () => ({
  EmptyState: () => <div>Empty State</div>,
}));

describe("InventoryPage - Compact Stats Subtitle", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mockUseCreateDevice.mockReturnValue({ mutate: vi.fn(), isPending: false });
    mockUseUpdateDevice.mockReturnValue({ mutate: vi.fn(), isPending: false });
    mockUseDeleteDevice.mockReturnValue({ mutate: vi.fn(), isPending: false });
    mockUseConfirmUpdate.mockReturnValue({ mutate: vi.fn(), isPending: false });
    mockUseCheckBulk.mockReturnValue({ mutate: vi.fn(), isPending: false });
  });

  const renderWithProvider = () => {
    const queryClient = new QueryClient();
    return render(
      <QueryClientProvider client={queryClient}>
        <InventoryPage />
      </QueryClientProvider>
    );
  };

  it("should not render subtitle when loading", () => {
    mockUseDevices.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    renderWithProvider();
    expect(screen.queryByText(/devices/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/updates? available/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/checked/i)).not.toBeInTheDocument();
  });

  it("should not render subtitle when there are no devices", () => {
    mockUseDevices.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });

    renderWithProvider();
    expect(screen.getByText("Empty State")).toBeInTheDocument();
    expect(screen.queryByText(/devices/i)).not.toBeInTheDocument();
  });

  it("should render correct subtitle for a single device with 0 updates and 1 checked", () => {
    mockUseDevices.mockReturnValue({
      data: [
        { id: 1, name: "Device 1", has_update: false, last_checked: "2026-06-11T08:00:00Z" }
      ],
      isLoading: false,
      error: null,
    });

    renderWithProvider();
    expect(screen.getByText("1 device • 0 updates available • 1 of 1 checked")).toBeInTheDocument();
    // Verify StatCard cards are not rendered
    expect(screen.queryByText("Devices")).not.toBeInTheDocument();
  });

  it("should render correct subtitle for multiple devices, updates, and checked counts", () => {
    mockUseDevices.mockReturnValue({
      data: [
        { id: 1, name: "Device 1", has_update: true, last_checked: "2026-06-11T08:00:00Z" },
        { id: 2, name: "Device 2", has_update: true, last_checked: "2026-06-11T08:00:00Z" },
        { id: 3, name: "Device 3", has_update: false, last_checked: "2026-06-11T08:00:00Z" },
        { id: 4, name: "Device 4", has_update: false, last_checked: null },
      ],
      isLoading: false,
      error: null,
    });

    renderWithProvider();
    expect(screen.getByText("4 devices • 2 updates available • 3 of 4 checked")).toBeInTheDocument();
  });

  it("should render single update grammatically correct", () => {
    mockUseDevices.mockReturnValue({
      data: [
        { id: 1, name: "Device 1", has_update: true, last_checked: "2026-06-11T08:00:00Z" },
        { id: 2, name: "Device 2", has_update: false, last_checked: "2026-06-11T08:00:00Z" },
      ],
      isLoading: false,
      error: null,
    });

    renderWithProvider();
    expect(screen.getByText("2 devices • 1 update available • 2 of 2 checked")).toBeInTheDocument();
  });
});
