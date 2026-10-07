import { expect, it, vi } from "vitest";
import { formatErrorsForAI, copyErrorsForAI } from "./copy-errors-for-ai";

it("formats actionable failed checks but omits passed checks", async () => {
  const errors = { phases: [
    { phase: "ast", passed: false, checks: [
      { name: "metadata", passed: false, message: "Too long", line: 12, fix_suggestion: "Use 120 characters" },
      { name: "syntax", passed: true, message: "ok", line: null, fix_suggestion: null },
      { name: "missing", passed: false, message: "missing", line: null, fix_suggestion: null },
    ] },
    { phase: "runtime", passed: true, checks: [] },
  ] };
  const text = formatErrorsForAI(errors, "custom.py");
  expect(text).toContain("Use 120 characters");
  expect(text).toContain("Line**: 12");
  expect(text).not.toContain("syntax");
  expect(formatErrorsForAI({})).toContain("Unknown error");
  expect(formatErrorsForAI({ detail: "error" })).toContain("error");
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
  await copyErrorsForAI(errors, "custom.py");
  expect(writeText).toHaveBeenCalledWith(text);
});
