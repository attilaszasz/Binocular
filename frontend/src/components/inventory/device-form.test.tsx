import "@testing-library/jest-dom";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { DeviceForm } from "./device-form";

// Mock useModules hook
const mockModules = [
  { id: 1, name: "Sony Alpha Module", device_type: "camera", source_url: "https://example.com/sony" },
  { id: 2, name: "Panasonic Lumix Module", device_type: "camera", source_url: "" },
];
const mockUseModules = vi.fn().mockReturnValue({
  data: mockModules,
  isLoading: false,
});

vi.mock("@/hooks/use-modules", () => ({
  useModules: () => mockUseModules(),
}));

// Mock checksApi.searchVersion
const mockSearchVersion = vi.fn();
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    checksApi: {
      ...actual.checksApi,
      searchVersion: (...args: unknown[]) => mockSearchVersion(...args),
    },
  };
});

describe("DeviceForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseModules.mockReturnValue({
      data: mockModules,
      isLoading: false,
    });
  });

  it("renders the device form fields", () => {
    render(
      <DeviceForm
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
      />
    );

    expect(screen.getByLabelText("Name")).toBeInTheDocument();
    expect(screen.getByLabelText("Model")).toBeInTheDocument();
    expect(screen.getByLabelText("Module")).toBeInTheDocument();
    expect(screen.getByLabelText("Current Version")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Search Version" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add Device" })).toBeInTheDocument();
  });

  it("disables the Search Version button when Module or Model is not provided", () => {
    render(
      <DeviceForm
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
      />
    );

    const searchBtn = screen.getByRole("button", { name: "Search Version" });
    expect(searchBtn).toBeDisabled();

    // Fill model but no module
    fireEvent.change(screen.getByLabelText("Model"), { target: { value: "ILCE-7M4" } });
    expect(searchBtn).toBeDisabled();
  });

  it("renders a source link only for the selected module with a URL", () => {
    render(
      <DeviceForm
        device={{
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
        }}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    const link = screen.getByRole("link", { name: "View module source page" });
    expect(link).toHaveAttribute("href", "https://example.com/sony");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noreferrer");
  });

  it("does not render a source link when the selected module has no URL", () => {
    render(
      <DeviceForm
        device={{
          id: 2,
          name: "My Lens",
          model: "Lumix",
          module_id: 2,
          module_name: "Panasonic Lumix Module",
          device_type: "camera",
          current_version: "1.0.0",
          has_update: false,
          latest_detected_version: null,
          last_checked: null,
          last_notified_version: null,
          created_at: "",
          updated_at: "",
        }}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.queryByRole("link", { name: "View module source page" })).not.toBeInTheDocument();
  });

  it("enables Search Version button when initial device has model and module", () => {
    const mockDevice = {
      id: 123,
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

    render(
      <DeviceForm
        device={mockDevice}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
      />
    );

    const searchBtn = screen.getByRole("button", { name: "Search Version" });
    expect(searchBtn).not.toBeDisabled();
  });

  it("calls checksApi.searchVersion when Search Version is clicked and updates current version", async () => {
    mockSearchVersion.mockResolvedValue({ version: "2.0.1" });

    const mockDevice = {
      id: 123,
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

    render(
      <DeviceForm
        device={mockDevice}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
      />
    );

    const searchBtn = screen.getByRole("button", { name: "Search Version" });
    fireEvent.click(searchBtn);

    expect(searchBtn).toBeDisabled(); // disables during search
    expect(screen.getByRole("button", { name: "Searching..." })).toBeInTheDocument();

    await waitFor(() => {
      expect(mockSearchVersion).toHaveBeenCalledWith(1, "ILCE-7M4");
    });

    await waitFor(() => {
      const versionInput = screen.getByLabelText("Current Version") as HTMLInputElement;
      expect(versionInput.value).toBe("2.0.1");
    });
  });

  it("shows an error message if checksApi.searchVersion fails", async () => {
    mockSearchVersion.mockRejectedValue(new Error("Device scraper error"));

    const mockDevice = {
      id: 123,
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

    render(
      <DeviceForm
        device={mockDevice}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
      />
    );

    const searchBtn = screen.getByRole("button", { name: "Search Version" });
    fireEvent.click(searchBtn);

    await waitFor(() => {
      expect(screen.getByText("Device scraper error")).toBeInTheDocument();
    });
  });

  it("validates empty name on submit", async () => {
    const mockSubmit = vi.fn();
    const { container } = render(
      <DeviceForm
        onSubmit={mockSubmit}
        onCancel={vi.fn()}
      />
    );

    const form = container.querySelector("form")!;
    fireEvent.submit(form);

    expect(screen.getByText("Device name is required.")).toBeInTheDocument();
    expect(mockSubmit).not.toHaveBeenCalled();
  });
});
