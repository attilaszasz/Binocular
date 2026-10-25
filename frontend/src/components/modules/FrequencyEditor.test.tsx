import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { it, vi, expect } from "vitest";
import { FrequencyEditor } from "./FrequencyEditor";
import type { Module } from "@/lib/api";

const mocks = vi.hoisted(() => ({ query: vi.fn(), mutation: vi.fn() }));
vi.mock("@/hooks/use-schedules", () => ({ useSchedules: () => mocks.query(), useUpdateSchedule: () => mocks.mutation() }));

it.each(["loading", "error", "missing", "active", "inactive"])("frequency state %s is truthful", state => {
  mocks.query.mockReturnValue({ isLoading: state === "loading", isError: state === "error", data: state === "missing" ? [] : [{ module_id: 1, interval_hours: 6, next_run: "2026-10-08T00:00:00Z" }] });
  mocks.mutation.mockReturnValue({ isPending: false, isError: true, error: new Error("write failed") });
  render(<FrequencyEditor module={{ id: 1, name: "source", status: state } as Module} />);
  if (state === "loading") expect(screen.getByText("Loading frequency...")).toBeInTheDocument();
  else if (state === "error" || state === "missing") expect(screen.getByRole("alert")).toHaveTextContent("unavailable");
  else {
    expect(screen.getByRole("alert")).toHaveTextContent("not saved");
    if (state === "inactive") expect(screen.queryByText(/Next check:/)).not.toBeInTheDocument();
    else expect(screen.getByText(/Next check:/)).toBeInTheDocument();
  }
});
