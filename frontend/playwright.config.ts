import { defineConfig, devices } from "@playwright/test"

export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  use: { baseURL: "http://127.0.0.1:5173" },
  webServer: [
    { command: "uv run --directory ../backend uvicorn tests.e2e_app:create_e2e_app --factory --host 127.0.0.1 --port 8001", url: "http://127.0.0.1:8001/healthz", reuseExistingServer: false },
    { command: "npm run dev -- --host 127.0.0.1", env: { VITE_API_TARGET: "http://127.0.0.1:8001" }, url: "http://127.0.0.1:5173", reuseExistingServer: false },
  ],
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Desktop Chrome"], viewport: { width: 375, height: 812 } } },
  ],
})
