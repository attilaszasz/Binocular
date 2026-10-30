import "@testing-library/jest-dom";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import userEvent from "@testing-library/user-event";
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
  it("requires a source and preserves free-text values on add", () => {
    const submit = vi.fn();
    const view = render(<DeviceForm onSubmit={submit} onCancel={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "new" } });
    fireEvent.submit(view.container.querySelector("form")!);
    expect(screen.getByRole("alert")).toHaveTextContent("Please select a module");
    expect(submit).not.toHaveBeenCalled();
  });

  it("submits only changed edit fields and retains manually entered version", () => {
    const submit = vi.fn();
    const view = render(<DeviceForm device={device} onSubmit={submit} onCancel={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "renamed" } });
    fireEvent.change(screen.getByLabelText("Current Version"), { target: { value: "manual" } });
    fireEvent.change(screen.getByLabelText("Model"), { target: { value: "free text" } });
    fireEvent.submit(view.container.querySelector("form")!);
    expect(submit).toHaveBeenCalledWith({ name: "renamed", model: "free text", current_version: "manual" });
  });
  const device = { id: 1, name: "Camera", model: "old", module_id: 1, module_name: "Sony", device_type: "camera", current_version: "typed", has_update: false, latest_detected_version: null, last_checked: null, last_notified_version: null, created_at: "", updated_at: "" };
  it.each([false, true])("discards stale success/error and finally after model edit (%s)", async (reject) => {
    let resolve!: (value: { version: string }) => void;
    let fail!: (error: Error) => void;
    mockSearchVersion.mockImplementationOnce(() => new Promise((yes, no) => { resolve = yes; fail = no; }));
    render(<DeviceForm device={device} onSubmit={vi.fn()} onCancel={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Search Version" }));
    fireEvent.change(screen.getByLabelText("Model"), { target: { value: "new" } });
    await act(async () => { if (reject) fail(new Error("stale error")); else resolve({ version: "stale" }); });
    expect(screen.getByLabelText("Current Version")).toHaveValue("typed");
    expect(screen.queryByText("stale error")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Search Version" })).toBeEnabled();
  });
  it("invalidates requests on unmount and clears only search references", async () => {
    mockSearchVersion.mockResolvedValueOnce({ version: "derived" });
    const view = render(<DeviceForm device={device} onSubmit={vi.fn()} onCancel={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Search Version" }));
    await waitFor(() => expect(screen.getByRole("status", { name: "Version search reference" })).toHaveTextContent("Latest found version (reference only): derived"));
    expect(screen.getByLabelText("Current Version")).toHaveValue("typed");
    fireEvent.change(screen.getByLabelText("Model"), { target: { value: "new" } });
    expect(screen.getByLabelText("Current Version")).toHaveValue("typed");
    expect(screen.queryByRole("status", { name: "Version search reference" })).not.toBeInTheDocument();
    let resolve!: (value: { version: string }) => void;
    mockSearchVersion.mockImplementationOnce(() => new Promise(yes => { resolve = yes; }));
    fireEvent.click(screen.getByRole("button", { name: "Search Version" }));
    view.unmount();
    await act(async () => resolve({ version: "ignored" }));
  });
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
    expect(screen.getByLabelText("Source")).toBeInTheDocument();
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

    const link = screen.getByRole("link", { name: /View module source page/ });
    expect(link).toHaveAttribute("href", "https://example.com/sony");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
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

    expect(screen.queryByRole("link", { name: /View module source page/ })).not.toBeInTheDocument();
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

  it("calls checksApi.searchVersion and displays a reference without changing installed version", async () => {
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
      expect(screen.getByRole("status", { name: "Version search reference" })).toHaveTextContent("Latest found version (reference only): 2.0.1");
      expect(versionInput.value).toBe("1.0.0");
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

  it("supports labeled unknown control via keyboard, preserves text and submits edit revision", async () => {
    const submit = vi.fn();
    const user = userEvent.setup();
    render(<DeviceForm device={{ ...device, installed_unknown: false, revision: 7 }} onSubmit={submit} onCancel={vi.fn()} />);
    const unknown = screen.getByRole("checkbox", { name: "Installed version unknown" });
    screen.getByLabelText("Current Version").focus();
    await user.tab();
    expect(unknown).toHaveFocus();
    await user.keyboard(" ");
    expect(unknown).toBeChecked();
    expect(screen.getByLabelText("Current Version")).toHaveValue("typed");
    expect(unknown).toHaveAccessibleDescription(/Unknown preserves any entered version/);
    await user.tab();
    expect(screen.getByRole("button", { name: "Save Changes" })).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(submit).toHaveBeenCalledWith({ installed_unknown: true, expected_revision: 7 });
  });

  it("nonblank installed edits clear unknown and blank edits restore it", () => {
    const submit = vi.fn();
    const view = render(<DeviceForm device={{ ...device, installed_unknown: true, revision: 3 }} onSubmit={submit} onCancel={vi.fn()} />);
    const unknown = screen.getByRole("checkbox", { name: "Installed version unknown" });
    expect(unknown).toBeChecked();
    fireEvent.change(screen.getByLabelText("Current Version"), { target: { value: "2.0" } });
    expect(unknown).not.toBeChecked();
    fireEvent.submit(view.container.querySelector("form")!);
    expect(submit).toHaveBeenLastCalledWith({ current_version: "2.0", installed_unknown: false, expected_revision: 3 });
    fireEvent.change(screen.getByLabelText("Current Version"), { target: { value: "  " } });
    expect(unknown).toBeChecked();
    fireEvent.click(unknown);
    expect(unknown).toBeChecked();
    fireEvent.submit(view.container.querySelector("form")!);
    expect(submit).toHaveBeenLastCalledWith({ current_version: "  ", expected_revision: 3 });
  });

  it("creates an explicitly unknown device without discarding the entered reference", async () => {
    const submit = vi.fn();
    const user = userEvent.setup();
    const view = render(<DeviceForm onSubmit={submit} onCancel={vi.fn()} />);
    await user.type(screen.getByLabelText("Name"), "Camera");
    fireEvent.change(view.container.querySelector("select")!, { target: { value: "1" } });
    await user.type(screen.getByLabelText("Current Version"), "last known");
    expect(screen.getByRole("checkbox")).not.toBeChecked();
    await user.click(screen.getByRole("checkbox", { name: "Installed version unknown" }));
    await user.click(screen.getByRole("button", { name: "Add Device" }));
    expect(submit).toHaveBeenCalledWith({ name: "Camera", model: "", module_id: 1, current_version: "last known", installed_unknown: true });
    expect(mockSearchVersion).not.toHaveBeenCalled();
  });

  it.each(["", "   "])("rejects empty search result %j without changing installed state", async version => {
    mockSearchVersion.mockResolvedValueOnce({ version });
    render(<DeviceForm device={{ ...device, installed_unknown: true }} onSubmit={vi.fn()} onCancel={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Search Version" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("No version returned by module");
    expect(screen.getByLabelText("Current Version")).toHaveValue("typed");
    expect(screen.getByRole("checkbox")).toBeChecked();
    expect(screen.queryByRole("status", { name: "Version search reference" })).not.toBeInTheDocument();
  });

  it("keeps unknown installed state after a successful reference search", async () => {
    mockSearchVersion.mockResolvedValueOnce({ version: "9.0" });
    render(<DeviceForm device={{ ...device, current_version: "", installed_unknown: true, latest_detected_version: "8.0" }} onSubmit={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByLabelText("Current Version")).toHaveValue("");
    fireEvent.click(screen.getByRole("button", { name: "Search Version" }));
    expect(await screen.findByRole("status", { name: "Version search reference" })).toHaveTextContent("9.0");
    expect(screen.getByLabelText("Current Version")).toHaveValue("");
    expect(screen.getByRole("checkbox")).toBeChecked();
  });
});
