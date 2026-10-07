import "@testing-library/jest-dom";
import { render, screen, fireEvent } from "@testing-library/react";
import { vi, it, expect } from "vitest";
import { ModuleCard } from "./ModuleCard";
import type { Module } from "@/lib/api";

const mocks = vi.hoisted(() => ({ scope: vi.fn(), update: vi.fn() }));
vi.mock("@/hooks/use-modules", () => ({
  useModuleScope: () => mocks.scope(),
  useUpdateModule: () => ({ mutate: mocks.update }),
  useDeleteModule: () => ({ mutate: vi.fn() }),
}));
vi.mock("./FrequencyEditor", () => ({ FrequencyEditor: () => <p>Frequency</p> }));
const module = { id: 1, name: "internal_name", display_name: "Friendly source", status: "inactive", device_type: "camera", linked_device_count: 2, coverage_notes: "Cameras & lenses", model_examples: ["example"], is_official: false } as Module;

it("shows official healthy metadata and no guessed count while refreshing summary", () => {
  mocks.scope.mockReturnValue({ refetch: vi.fn() });
  render(<ModuleCard module={{ ...module, is_official: true, version: "1", author: "Operator", file_path: "/modules/file.py", consecutive_failures: 0, status: "active" }} countsUpdating />);
  expect(screen.getByText("Official")).toBeInTheDocument();
  expect(screen.getByText("Healthy")).toBeInTheDocument();
  expect(screen.getByText("Linked device count unknown")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Delete Friendly source" })).toBeDisabled();
});

it.each([0, 1, 3])("shows exact %s members and current/future scope", count => {
  mocks.scope.mockReturnValue({ data: { linked_device_count: count, devices: Array.from({ length: count }, (_, id) => ({ id, name: `device ${id}`, model: "model" })) }, refetch: vi.fn() });
  render(<ModuleCard module={module} />);
  fireEvent.click(screen.getByRole("button", { name: "Inspect linked devices" }));
  expect(screen.getByText(`${count} linked devices`)).toBeInTheDocument();
  expect(screen.getByText(/and devices linked later/)).toBeInTheDocument();
  expect(screen.getByText(/Manual single, bulk/)).toBeInTheDocument();
  if (!count) expect(screen.getByText("No linked devices.")).toBeInTheDocument();
  else expect(screen.getAllByRole("listitem")).toHaveLength(count);
});

it("failure is unknown, never zero", () => {
  mocks.scope.mockReturnValue({ isError: true, refetch: vi.fn() });
  render(<ModuleCard module={module} />);
  fireEvent.click(screen.getByRole("button", { name: "Inspect linked devices" }));
  expect(screen.getByRole("alert")).toHaveTextContent("Count unknown");
  expect(screen.queryByText("0 linked devices")).not.toBeInTheDocument();
});

it.each(["active", "error", "unknown"])("keeps health visible and status/delete failures honest (%s)", status => {
  mocks.scope.mockReturnValue({ isFetching: true, refetch: vi.fn() });
  mocks.update.mockImplementation((_data, options) => options.onError(new Error("Not saved")));
  render(<ModuleCard module={{ ...module, status, consecutive_failures: 6, last_success: "2026-10-07T00:00:00Z", guidance_provenance: "legacy" }} />);
  expect(screen.getByText("6 consecutive failures")).toBeInTheDocument();
  expect(screen.getByText("Last Success")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("switch"));
  expect(screen.getByText("Not saved")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Inspect linked devices" }));
  expect(screen.getByText("Refreshing linked devices…")).toBeInTheDocument();
  expect(screen.getByText("Linked device count unknown")).toBeInTheDocument();
});
