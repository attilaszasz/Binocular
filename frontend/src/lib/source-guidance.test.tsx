import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { safeSourceUrl } from "./source-guidance";
import { SourceGuidance } from "@/components/inventory/SourceGuidance";
import type { Module } from "./api";

describe("source links", () => {
  it.each([undefined, "", "/relative", "javascript:alert(1)", "data:text/html,x", "https://u:p@host/", "https://host/\n", "https://", "ftp://host/"])("omits unsafe %s", value => expect(safeSourceUrl(value)).toBeUndefined());
  it("renders only local escaped help with distinct human/canonical links", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    render(<SourceGuidance id="help" module={{ help_url: "https://host/index.html", source_url: "https://host/data.xml", coverage_notes: "<script>text</script>", model_examples: ["Z 30"], status: "inactive" } as Module} />);
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(screen.getByText("<script>text</script>")).toBeInTheDocument();
    for (const link of screen.getAllByRole("link")) expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(screen.getByRole("status")).toHaveTextContent("Automatic monitoring is off");
    fetchSpy.mockRestore();
  });
});
