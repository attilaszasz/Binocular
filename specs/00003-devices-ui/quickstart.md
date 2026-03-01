# Quickstart: Core Frontend (UI/UX)

**Feature**: `00003-devices-ui` | **Plan**: [plan.md](plan.md)

---

## Prerequisites

- Node.js 18+ (LTS) and npm
- Python 3.11+ with Feature 00001 + 00002 fully implemented
- `pyproject.toml` dependencies installed: `pip install -e ".[dev]"`
- Backend runs on `http://localhost:8000`

## Initial Setup

```bash
# From the repository root
cd frontend

# Install dependencies (creates node_modules from lock file)
npm ci

# Start the Vite dev server (port 5173, proxies /api → localhost:8000)
npm run dev
```

Open `http://localhost:5173` in your browser. The dev server proxies all `/api/*` requests to the FastAPI backend.

## Running the Backend (separate terminal)

```bash
# From the repository root
uvicorn backend.src.main:app --reload --host 0.0.0.0 --port 8000
```

Or use VS Code's **"Binocular: Debug API"** launch configuration (F5).

## Running Both (F5 — Full Stack)

1. Open the workspace in VS Code.
2. Select the **"Binocular: Full Stack"** compound launch configuration.
3. Press **F5** — both the FastAPI backend (port 8000) and Vite dev server (port 5173) start simultaneously.
4. Set breakpoints in both Python (`backend/src/`) and TypeScript (`frontend/src/`) files.
5. Open `http://localhost:5173` — API requests proxy to the backend with debugpy attached.

The `.vscode/launch.json` compound configuration:

```jsonc
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Binocular: Debug API",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "backend.src.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
      ],
      "cwd": "${workspaceFolder}",
      "env": {
        "BINOCULAR_DB_PATH": "${workspaceFolder}/data/binocular.db"
      },
      "console": "integratedTerminal"
    },
    {
      "name": "Binocular: Debug Frontend",
      "type": "node",
      "request": "launch",
      "cwd": "${workspaceFolder}/frontend",
      "runtimeExecutable": "npm",
      "runtimeArgs": ["run", "dev"],
      "console": "integratedTerminal",
      "serverReadyAction": {
        "pattern": "Local:.+(https?://\\S+)",
        "uriFormat": "%s",
        "action": "openExternally"
      }
    }
  ],
  "compounds": [
    {
      "name": "Binocular: Full Stack",
      "configurations": [
        "Binocular: Debug API",
        "Binocular: Debug Frontend"
      ]
    }
  ]
}
```

## Quality Gate Commands

```bash
cd frontend

# Type checking (equivalent of mypy --strict)
npx tsc --noEmit

# Linting + formatting check (equivalent of ruff + ruff format)
npx biome check .
npx biome format --check .

# Run all component tests
npx vitest run

# Run Playwright smoke test (requires browsers installed)
npx playwright test
```

## Production Build

```bash
cd frontend
npm run build
# Output: frontend/dist/
```

In production, FastAPI serves `frontend/dist/` via `StaticFiles`:

```python
# backend/src/main.py (updated)
from fastapi.staticfiles import StaticFiles

# Mount API routes first (higher priority)
# ... existing route registration ...

# SPA fallback: serve index.html for all non-API routes
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
```

## Integration Scenarios

### Scenario 1: Dashboard — View Grouped Inventory

1. Start both backend and frontend.
2. Open `http://localhost:5173`.
3. The dashboard loads with skeleton placeholders, then shows:
   - Stats row: Total Devices, Updates Available, Up to Date
   - Device cards grouped by device type
   - Each card shows: name, local version, latest version, status indicator, last-checked time

### Scenario 2: Add a Device via the UI

1. On the dashboard, click **"Add Device"**.
2. The slide-over panel opens on the right.
3. Fill in: Name ("Sony A7IV"), Device Type (select from dropdown), Current Version ("2.00").
4. Click **Submit** — the panel closes, the new device appears in the correct group, stats update.

### Scenario 3: Confirm a Firmware Update

1. Find a device card showing "Update Available" (rose/red highlight, arrow between versions).
2. Click **"Sync Local"** on the card.
3. The button disables, the card immediately updates (optimistic), and the stats bar decrements "Updates Available" by 1.

### Scenario 4: Dark Mode Toggle

1. Click the Sun/Moon icon in the top header.
2. The entire interface switches themes immediately.
3. Refresh the page — the theme persists (stored in `localStorage`).
4. Clear `localStorage` and refresh — the theme follows your OS preference.

### Scenario 5: Mobile Responsive Layout

1. Open the browser's device toolbar (responsive mode).
2. Set width to 375px (iPhone size).
3. Verify: sidebar hidden, hamburger menu visible, stats stacked vertically, cards single column.
4. Tap the hamburger — sidebar slides in from the left with an overlay.

### Scenario 6: Empty Inventory State

1. Start with an empty database (no device types or devices).
2. Open the dashboard — see the welcome empty state with guidance text and a "Get Started" button.
3. Click the CTA — it opens the device type creation form.

### Scenario 7: Delete Device Type with Cascade

1. Navigate to the Modules tab.
2. Click "Delete" on a device type that has child devices.
3. A confirmation dialog appears: "Delete {name}? This will also delete {N} devices."
4. Click "Delete All" — the type and all its devices are removed, dashboard updates.

## Running Tests

```bash
cd frontend

# Component tests (Vitest + RTL)
npx vitest run

# Component tests in watch mode (during development)
npx vitest

# Playwright smoke test
npx playwright install --with-deps chromium  # first time only
npx playwright test

# All quality gates in sequence
npx tsc --noEmit && npx biome check . && npx vitest run
```

## Key Development Patterns

### Adding a New API Call

1. Add the TypeScript interface to `src/api/types.ts`.
2. Add the fetch function to `src/api/client.ts`.
3. Create a TanStack Query hook in the relevant `features/*/hooks.ts`.
4. Use the hook in your component — loading/error states are built in.

### Adding a New Form

1. Create a form component in `src/features/forms/`.
2. Use `useForm()` from React Hook Form with inline validation rules.
3. On submit, call a TanStack Query mutation.
4. On backend error, map `error_code` + `field` to `setError()`.
5. Wrap the form in `<SlideOverPanel>`.

### Theming a New Component

- Use Tailwind's `dark:` prefix for all color/background/border utilities.
- Light mode class first, then `dark:` variant: `bg-white dark:bg-slate-900`.
- Test both modes before committing.
