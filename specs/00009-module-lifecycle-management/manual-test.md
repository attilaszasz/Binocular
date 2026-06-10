# Manual Test Runbook: Module Lifecycle Management

This runbook outlines how to manually verify the frontend UI features for E009.

## Prerequisites
1. Start the backend app server:
   ```bash
   cd backend
   .venv/bin/uvicorn binocular.app:create_app --factory --reload
   ```
2. Start the frontend development server:
   ```bash
   cd frontend
   npm run dev
   ```
3. Open the browser to the local frontend port (typically `http://localhost:5173`) and navigate to the **Modules** page in the sidebar.

## Test Scenarios

### Scenario 1: Verify Initial Module Grid
1. Navigate to the **Modules** page.
2. Confirm the page displays three stats cards at the top:
   - Total Modules
   - Official Modules
   - Active Modules
3. Verify that the grid displays the default seeded official modules (e.g., Sony Alpha, Panasonic Lumix, Godox Flashes) with "Official" badges and green "active" status badges.

### Scenario 2: Upload a Valid Extension Module
1. Click the **Upload Module** button.
2. Verify that the Upload form appears and contains a trust boundary warning banner.
3. Drag and drop a valid custom module Python file (e.g., `my_lens.py` containing `MODULE_VERSION`, `SUPPORTED_DEVICE_TYPE`, and `check_firmware`) into the upload zone (or click to select it).
4. Select **Run Phase 2 (Runtime Verification)** to enable verification execution.
5. Click **Upload Module**.
6. Verify that:
   - The upload succeeds.
   - An emerald success message is displayed.
   - The new module `my_lens` appears in the grid with status `active` and version matching your file.

### Scenario 3: Upload an Invalid Module
1. Click **Upload Module** again.
2. Drag and drop a python file with syntax errors or missing required constants (e.g., missing `MODULE_VERSION`).
3. Click **Upload Module**.
4. Verify that:
   - The upload is rejected.
   - A red validation error card appears listing the failed checks.
   - A **Copy for AI** button is available.
5. Click **Copy for AI** and paste the contents into a text editor to confirm they are formatted as a clear Markdown block.

### Scenario 4: Delete Module Restriction
1. Find the new custom module `my_lens` in the grid.
2. Click the red garbage icon. Confirm the browser dialog.
3. Confirm that the module is successfully deleted from the grid.
4. Try to delete any **Official** module (e.g., Godox Flashes).
5. Verify that the delete button is disabled and displays a tooltip: "Cannot delete official built-in modules".
