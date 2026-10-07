import "@testing-library/jest-dom";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { ModuleUploadForm } from "./ModuleUploadForm";

// Mock useUploadModule hook
const mockMutateAsync = vi.fn();
vi.mock("@/hooks/use-modules", () => ({
  useUploadModule: () => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
    isSuccess: false,
  }),
}));

// Mock ResizeObserver for Radix component layout effects in jsdom
globalThis.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

describe("ModuleUploadForm", () => {
  it("offers manual copying when the Clipboard API is absent on HTTP LAN origins", async () => {
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: undefined });
    mockMutateAsync.mockRejectedValueOnce(new Error("metadata invalid"));
    render(<ModuleUploadForm />);
    fireEvent.change(screen.getByLabelText("Python module file", { exact: true }), { target: { files: [new File(["code"], "custom.py")] } });
    fireEvent.click(screen.getByRole("button", { name: "Upload Module" }));
    fireEvent.click(await screen.findByRole("button", { name: "Copy for AI" }));
    expect(await screen.findByText(/Select the displayed errors manually/)).toBeInTheDocument();
  });
  it("copies actual validation errors and surfaces clipboard failure", async () => {
    const copy = vi.fn().mockRejectedValue(new Error("permission denied"));
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: copy } });
    mockMutateAsync.mockRejectedValueOnce(new Error("metadata invalid"));
    render(<ModuleUploadForm />);
    fireEvent.change(screen.getByLabelText("Python module file", { exact: true }), { target: { files: [new File(["code"], "custom.py")] } });
    fireEvent.click(screen.getByRole("button", { name: "Upload Module" }));
    fireEvent.click(await screen.findByRole("button", { name: "Copy for AI" }));
    expect(await screen.findByText(/Unable to copy errors/)).toBeInTheDocument();
    expect(copy).toHaveBeenCalledWith(expect.stringContaining("metadata invalid"));
    copy.mockResolvedValueOnce(undefined);
    fireEvent.click(screen.getByRole("button", { name: "Copy for AI" }));
    await screen.findByText("Copied!");
    fireEvent.click(screen.getByRole("button", { name: "Clear" }));
    expect(screen.queryByText("custom.py")).not.toBeInTheDocument();
  });
  it("warns before import and rejects truncated streams without claiming saved", async () => {
    mockMutateAsync.mockResolvedValueOnce({ body: { getReader: () => ({ read: async () => ({ done: true }) }) } });
    const { container } = render(<ModuleUploadForm />);
    expect(screen.getByText(/unsandboxed, user-vetted code/)).toBeInTheDocument();
    fireEvent.change(container.querySelector('input[type="file"]')!, { target: { files: [new File(["code"], "test.py")] } });
    fireEvent.click(screen.getByRole("button", { name: "Upload Module" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("without confirmed save");
    expect(screen.queryByText("Module Uploaded Successfully")).not.toBeInTheDocument();
  });
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the trust boundary warning and upload button", () => {
    render(<ModuleUploadForm />);
    expect(screen.getByText("Trust Boundary Warning")).toBeInTheDocument();
    expect(screen.getByText("Upload Module")).toBeInTheDocument();
    expect(screen.getByText("Run Phase 2 (Runtime Verification)")).toBeInTheDocument();
  });

  it("updates state when selecting a file", () => {
    const { container } = render(<ModuleUploadForm />);
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).toBeInTheDocument();

    const file = new File(["print('hello')"], "test_module.py", { type: "text/x-python" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText("test_module.py")).toBeInTheDocument();
    expect(screen.getByText("Clear")).toBeInTheDocument();
  });

  it("performs a successful streaming upload", async () => {
    // Setup mock chunks for stream
    const mockEvents = [
      { status: "running", step: "ast", message: "Running Phase 1" },
      { status: "running", step: "saving", message: "Saving" },
      { status: "success", step: "saved", message: "Successfully uploaded", module: { id: 10, name: "test_module" } },
    ];
    const mockChunks = mockEvents.map((evt) => new TextEncoder().encode(JSON.stringify(evt) + "\n"));

    let chunkIdx = 0;
    const mockReader = {
      read: vi.fn().mockImplementation(async () => {
        if (chunkIdx < mockChunks.length) {
          const value = mockChunks[chunkIdx++];
          return { done: false, value };
        }
        return { done: true, value: undefined };
      }),
    };

    const mockResponse = {
      body: {
        getReader: () => mockReader,
      },
    };

    mockMutateAsync.mockResolvedValue(mockResponse);

    const { container } = render(<ModuleUploadForm />);
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;

    const file = new File(["print('hello')"], "test_module.py", { type: "text/x-python" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const submitButton = screen.getByText("Upload Module");
    fireEvent.click(submitButton);

    // Should display the checklist heading
    expect(screen.getByText("Validation & Upload Progress")).toBeInTheDocument();

    // Wait for the upload success alert
    await waitFor(() => {
      expect(screen.getByText("Module Uploaded Successfully")).toBeInTheDocument();
    });

    // Check that we called the mutation
    expect(mockMutateAsync).toHaveBeenCalledWith({ file, runPhase2: false });
  });

  it("handles a failed streaming upload", async () => {
    // Setup mock chunks for failed stream
    const mockEvents = [
      { status: "running", step: "ast", message: "Running Phase 1" },
      {
        status: "failed",
        step: "ast",
        message: "Module validation failed",
        validation_result: {
          valid: false,
          phases: [
            {
              phase: "ast",
              passed: false,
              checks: [
                {
                  name: "syntax_check",
                  passed: false,
                  message: "SyntaxError: invalid syntax",
                  line: 12,
                  fix_suggestion: "Add a colon",
                },
              ],
            },
          ],
        },
      },
    ];
    const mockChunks = mockEvents.map((evt) => new TextEncoder().encode(JSON.stringify(evt) + "\n"));

    let chunkIdx = 0;
    const mockReader = {
      read: vi.fn().mockImplementation(async () => {
        if (chunkIdx < mockChunks.length) {
          const value = mockChunks[chunkIdx++];
          return { done: false, value };
        }
        return { done: true, value: undefined };
      }),
    };

    const mockResponse = {
      body: {
        getReader: () => mockReader,
      },
    };

    mockMutateAsync.mockResolvedValue(mockResponse);

    const { container } = render(<ModuleUploadForm />);
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;

    const file = new File(["print('hello')"], "test_module.py", { type: "text/x-python" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const submitButton = screen.getByText("Upload Module");
    fireEvent.click(submitButton);

    // Wait for the failure message
    await waitFor(() => {
      expect(screen.getByText("Module Validation Failed")).toBeInTheDocument();
    });

    // Verify copy-for-AI button exists
    expect(screen.getByText("Copy for AI")).toBeInTheDocument();
  });
});
