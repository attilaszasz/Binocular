import "@testing-library/jest-dom"
import { render, screen } from "@testing-library/react"
import { describe, it, expect, vi, afterEach } from "vitest"
import { VersionDisplay } from "./version-display"

describe("VersionDisplay", () => {
  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it("prepends 'v' when version does not start with 'v'", () => {
    vi.stubEnv("VITE_APP_VERSION", "0.1.6")
    render(<VersionDisplay />)
    expect(screen.getByText("v0.1.6")).toBeInTheDocument()
  })

  it("does not prepend 'v' when version already starts with 'v'", () => {
    vi.stubEnv("VITE_APP_VERSION", "v0.1.6")
    render(<VersionDisplay />)
    expect(screen.getByText("v0.1.6")).toBeInTheDocument()
  })

  it("defaults to 'vdev' when VITE_APP_VERSION is not defined", () => {
    render(<VersionDisplay />)
    expect(screen.getByText("vdev")).toBeInTheDocument()
  })

  it("handles non-semver version strings correctly", () => {
    vi.stubEnv("VITE_APP_VERSION", "custom-build")
    render(<VersionDisplay />)
    expect(screen.getByText("vcustom-build")).toBeInTheDocument()
  })
})
