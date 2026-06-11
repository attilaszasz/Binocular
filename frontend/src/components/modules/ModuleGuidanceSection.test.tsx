import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { ModuleGuidanceSection } from "./ModuleGuidanceSection";

// Mock fetch for kit files API
beforeEach(() => {
  global.fetch = vi.fn().mockResolvedValue({
    json: () =>
      Promise.resolve({
        files: [
          {
            name: "STARTER_TEMPLATE.py",
            description: "Annotated V1 contract skeleton",
            size_bytes: 3456,
            url: "/api/v1/module-kit/STARTER_TEMPLATE.py",
          },
          {
            name: "EXAMPLE_MODULE.py",
            description: "Working example (Sony Alpha)",
            size_bytes: 5678,
            url: "/api/v1/module-kit/EXAMPLE_MODULE.py",
          },
          {
            name: "AI_INSTRUCTIONS.md",
            description: "Structured AI authoring guide",
            size_bytes: 9012,
            url: "/api/v1/module-kit/AI_INSTRUCTIONS.md",
          },
          {
            name: "CONTRACT_REFERENCE.md",
            description: "V1 contract documentation",
            size_bytes: 3456,
            url: "/api/v1/module-kit/CONTRACT_REFERENCE.md",
          },
        ],
      }),
  }) as typeof fetch;
});

describe("ModuleGuidanceSection", () => {
  it("renders the section title", () => {
    render(<ModuleGuidanceSection />);
    expect(screen.getByText("Create a Module")).toBeInTheDocument();
  });

  it("renders all four authoring steps", () => {
    render(<ModuleGuidanceSection />);
    expect(screen.getByText("Get the Kit")).toBeInTheDocument();
    expect(screen.getByText("Write Your Module")).toBeInTheDocument();
    expect(screen.getByText("Test Locally")).toBeInTheDocument();
    expect(screen.getByText("Upload")).toBeInTheDocument();
  });

  it("renders V1 contract quick reference", () => {
    render(<ModuleGuidanceSection />);
    expect(screen.getByText("V1 Contract Requirements")).toBeInTheDocument();
    expect(screen.getByText("MODULE_VERSION")).toBeInTheDocument();
    expect(screen.getByText("SUPPORTED_DEVICE_TYPE")).toBeInTheDocument();
    expect(screen.getByText("check_firmware()")).toBeInTheDocument();
  });

  it("renders AI Module Kit heading", () => {
    render(<ModuleGuidanceSection />);
    expect(screen.getByText("AI Module Kit")).toBeInTheDocument();
  });

  it("fetches kit files on mount", async () => {
    render(<ModuleGuidanceSection />);
    expect(global.fetch).toHaveBeenCalledWith("/api/v1/module-kit/");
  });

  it("renders kit file names after loading", async () => {
    render(<ModuleGuidanceSection />);
    // Wait for async state update
    expect(
      await screen.findByText("STARTER_TEMPLATE.py")
    ).toBeInTheDocument();
    expect(screen.getByText("EXAMPLE_MODULE.py")).toBeInTheDocument();
    expect(screen.getByText("AI_INSTRUCTIONS.md")).toBeInTheDocument();
    expect(screen.getByText("CONTRACT_REFERENCE.md")).toBeInTheDocument();
  });
});
