import "@testing-library/jest-dom";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import userEvent from "@testing-library/user-event";
import type { ComparisonStatus, Device } from "@/lib/api";
import { DeviceCard } from "./device-card";

const mockCheckDeviceMutate = vi.fn();
vi.mock("@/hooks/use-devices", () => ({
  useCheckDevice: () => ({
    mutate: mockCheckDeviceMutate,
    isPending: false,
  }),
}));

describe("DeviceCard", () => {
  beforeEach(() => vi.clearAllMocks());
  const mockDevice = {
    id: 1,
    name: "My Camera",
    model: "ILCE-7M4",
    module_id: 1,
    module_name: "Sony Alpha Module",
    device_type: "camera",
    current_version: "1.0.0",
    has_update: false,
    latest_detected_version: null,
    last_checked: null,
    last_notified_version: null,
    created_at: "",
    updated_at: "",
  };

  it("renders device name and model, but does not render the device_type badge", () => {
    render(
      <DeviceCard
        device={mockDevice}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        onConfirm={vi.fn()}
      />
    );

    expect(screen.getByText("My Camera")).toBeInTheDocument();
    expect(screen.getByText("ILCE-7M4")).toBeInTheDocument();
    
    // The device_type badge should not be in the document
    expect(screen.queryByText("camera")).not.toBeInTheDocument();
  });

  it("calls handleCheck when the refresh button is clicked", () => {
    render(
      <DeviceCard
        device={mockDevice}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        onConfirm={vi.fn()}
      />
    );

    const checkBtn = screen.getByTitle("Check for update");
    fireEvent.click(checkBtn);

    expect(mockCheckDeviceMutate).toHaveBeenCalledWith(mockDevice.id, expect.any(Object));
  });

  it("renders update confirm button when an update is available", () => {
    const deviceWithUpdate = {
      ...mockDevice,
      has_update: true,
      latest_detected_version: "1.1.0",
    };

    const mockConfirm = vi.fn();

    render(
      <DeviceCard
        device={deviceWithUpdate}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        onConfirm={mockConfirm}
      />
    );

    const confirmBtn = screen.getByRole("button", { name: /confirm update/i });
    expect(confirmBtn).toBeInTheDocument();

    fireEvent.click(confirmBtn);
    expect(mockConfirm).toHaveBeenCalledWith(deviceWithUpdate);
  });

  it.each<[ComparisonStatus, string]>([
    ["unknown", "Installed version unknown"],
    ["comparison_unknown", "Versions cannot be compared"],
    ["unverified", "Not verified"],
    ["no_firmware", "No firmware available"],
    ["stale", "Verification stale"],
    ["failed", "Verification failed"],
  ])("renders %s explicitly, retaining latest only as reference", (status, label) => {
    render(<DeviceCard device={{ ...mockDevice, comparison_status: status, latest_detected_version: "2.0", has_update: true }} onEdit={vi.fn()} onDelete={vi.fn()} onConfirm={vi.fn()} />);
    expect(screen.getByRole("status", { name: "Firmware status" })).toHaveTextContent(label);
    expect(screen.getByText("Last detected version (reference only): 2.0")).toBeInTheDocument();
    expect(screen.queryByText("Latest", { exact: true })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Confirm Update/ })).not.toBeInTheDocument();
  });

  it.each<Partial<Device>>([
    { current_version: "" },
    { current_version: "  " },
    { installed_unknown: true, comparison_status: "current" },
    { installed_unknown: true, has_update: true, latest_detected_version: "2.0" },
  ])("unknown installed state overrides inconsistent flags: %j", overrides => {
    render(<DeviceCard device={{ ...mockDevice, ...overrides }} onEdit={vi.fn()} onDelete={vi.fn()} onConfirm={vi.fn()} />);
    expect(screen.getByRole("status")).toHaveTextContent("Installed version unknown");
    expect(screen.queryByText("Latest", { exact: true })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Confirm Update/ })).not.toBeInTheDocument();
  });

  it.each([false, true])("keeps persisted failure visible after remount (unknown=%s)", unknown => {
    const device: Device = {
      ...mockDevice, current_version: "2.0", latest_detected_version: "2.0",
      installed_unknown: unknown, comparison_status: "failed", has_update: false,
      last_checked: "2026-10-29T10:00:00Z", last_check_attempt_at: "2026-10-30T10:00:00Z",
    };
    const props = { device, onEdit: vi.fn(), onDelete: vi.fn(), onConfirm: vi.fn() };
    const first = render(<DeviceCard {...props} />);
    first.unmount();
    render(<DeviceCard {...props} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Last verification failed");
    expect(screen.queryByText("Latest", { exact: true })).not.toBeInTheDocument();
    expect(screen.getByText(/Last successfully checked:/)).toBeInTheDocument();
    expect(screen.getByText(/Last check attempt:/)).toBeInTheDocument();
    expect(screen.getByText("Last detected version (reference only): 2.0")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Confirm Update/ })).not.toBeInTheDocument();
  });

  it("shows verified current and the legacy manual-entry label without implying catalog support", () => {
    render(<DeviceCard device={{ ...mockDevice, comparison_status: "current", catalog_link_state: "legacy" }} onEdit={vi.fn()} onDelete={vi.fn()} onConfirm={vi.fn()} />);
    expect(screen.getByRole("status")).toHaveTextContent("Latest");
    expect(screen.getByText("Legacy manual entry · per-model checks")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Confirm Update/ })).not.toBeInTheDocument();
  });

  it("does not infer current from a false update flag and exposes unresolved linking", () => {
    render(<DeviceCard device={{ ...mockDevice, catalog_link_state: "unresolved" }} onEdit={vi.fn()} onDelete={vi.fn()} onConfirm={vi.fn()} />);
    expect(screen.getByRole("status")).toHaveTextContent("Not verified");
    expect(screen.getByText("Catalog link unresolved")).toBeInTheDocument();
    expect(screen.queryByText("Latest", { exact: true })).not.toBeInTheDocument();
  });

  it.each([false, true])("announces check errors and does not leave a Latest badge (%s)", networkFailure => {
    render(<DeviceCard device={{ ...mockDevice, comparison_status: "current", latest_detected_version: "1.0.0" }} onEdit={vi.fn()} onDelete={vi.fn()} onConfirm={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Check for update" }));
    const callbacks = mockCheckDeviceMutate.mock.calls[0][1];
    act(() => {
      if (networkFailure) callbacks.onError(new Error("Network unavailable"));
      else callbacks.onSuccess({ success: false, error_message: "Source failed" });
    });
    expect(screen.getByRole("alert")).toHaveTextContent(networkFailure ? "Network unavailable" : "Source failed");
    expect(screen.getByRole("status")).toHaveTextContent("Verification failed");
    expect(screen.queryByText("Latest", { exact: true })).not.toBeInTheDocument();
    expect(screen.getByText(/Last detected version \(reference only\)/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Check for update" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("supports keyboard activation of labeled edit/delete and explicit update confirmation", async () => {
    const user = userEvent.setup();
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    const onConfirm = vi.fn();
    const device = { ...mockDevice, comparison_status: "update_available" as const, has_update: true, latest_detected_version: "2.0" };
    render(<DeviceCard device={device} onEdit={onEdit} onDelete={onDelete} onConfirm={onConfirm} />);
    await user.tab();
    expect(screen.getByRole("button", { name: "Check for update" })).toHaveFocus();
    await user.tab();
    await user.keyboard("{Enter}");
    expect(onEdit).toHaveBeenCalledWith(device);
    await user.tab();
    await user.keyboard(" ");
    expect(onDelete).toHaveBeenCalledWith(device);
    await user.tab();
    await user.keyboard("{Enter}");
    expect(onConfirm).toHaveBeenCalledWith(device);
  });
});
