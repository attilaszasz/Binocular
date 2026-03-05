# Quickstart: Module Management (API & UI)

**Feature**: 00007-module-management

## Prerequisites

- Backend running (`uvicorn backend.src.main:app --reload`)
- Frontend dev server running (`cd frontend && npm run dev`)
- Seed data loaded (`python -m backend.scripts.seed_mock_data`)
- A valid test module file (e.g., copy `backend/modules/mock_module.py` and rename to `test_upload.py`)

## Scenario 1: Upload a Valid Module

1. Open `http://localhost:5173/modules`
2. Drag a valid `.py` module file onto the upload area (or click to browse)
3. Leave Test URL and Device Model fields empty
4. Click Upload
5. **Verify**: Module appears in the table as Active with its declared version and supported device type

**API equivalent**:
```bash
curl -X POST http://localhost:8000/api/v1/modules \
  -F "file=@test_upload.py"
```
Expected: HTTP 201 with `ModuleResponse` JSON body.

## Scenario 2: Upload with Runtime Validation

1. Repeat Scenario 1 but fill in Test URL (`https://example.com/firmware`) and Device Model (`TEST-MODEL`)
2. Click Upload
3. **Verify**: If the module's `check_firmware()` succeeds with those inputs, the module is saved. If it fails, the upload is rejected with runtime error details displayed inline.

**API equivalent**:
```bash
curl -X POST http://localhost:8000/api/v1/modules \
  -F "file=@test_upload.py" \
  -F "test_url=https://example.com/firmware" \
  -F "test_model=TEST-MODEL"
```

## Scenario 3: Upload Rejection — Structural Errors

1. Create a file `broken.py` with content: `x = 1` (missing check_firmware function)
2. Upload it
3. **Verify**: HTTP 400 returned. Inline error displays "Missing required function 'check_firmware'" and "Missing required constant 'MODULE_VERSION'" (all errors at once)

## Scenario 4: Upload Rejection — Duplicate Filename

1. Upload a module that already exists (same filename)
2. **Verify**: HTTP 400 with message directing user to delete existing module first

## Scenario 5: Delete a Module

1. From the module table, click the Delete button on a user-uploaded module
2. Confirm in the dialog
3. **Verify**: Module disappears from the list immediately. HTTP 204 returned.

**API equivalent**:
```bash
curl -X DELETE http://localhost:8000/api/v1/modules/test_upload.py -v
```
Expected: HTTP 204 No Content.

## Scenario 6: System Module Protection

1. Verify the built-in mock module (underscore-prefixed) has no Delete button, or attempting delete returns HTTP 400
2. Attempting to upload `_system.py` is rejected with "reserved for system modules" message

## Scenario 7: Empty State

1. Delete all user modules
2. **Verify**: Empty state renders with a prompt to upload the first module

## Scenario 8: Reload

1. Manually place or remove a `.py` file in the modules directory outside the UI
2. Click the Reload button
3. **Verify**: Module list refreshes to reflect filesystem changes
