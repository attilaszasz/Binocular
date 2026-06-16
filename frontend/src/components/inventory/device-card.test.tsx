import "@testing-library/jest-dom";
import { render, screen, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect } from "vitest";
import { DeviceCard } from "./device-card";

const mockCheckDeviceMutate = vi.fn();
vi.mock("@/hooks/use-devices", () => ({
  useCheckDevice: () => ({
    mutate: mockCheckDeviceMutate,
    isPending: false,
  }),
}));

describe("DeviceCard", () => {
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
});
