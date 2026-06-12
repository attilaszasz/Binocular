# API Contract: Streaming Module Upload Validation

Updates the `POST /api/v1/modules` endpoint to return a chunked, newline-delimited JSON stream detailing the validation progress and final resolution.

## Endpoints

### 1. Upload Module (Streaming)
* **Method**: `POST`
* **Path**: `/api/v1/modules`
* **Query Parameters**:
  * `run_phase2` (boolean, optional, default: `false`)
* **Request Body**:
  * `Content-Type`: `multipart/form-data`
  * `file`: UploadFile (the `.py` module file)
* **Success Response Headers**:
  * **Code**: `200 OK` (HTTP 200 is used for streaming rather than 201 to support chunked transport)
  * **Content-Type**: `application/x-ndjson`
  * **X-Accel-Buffering**: `no` (tells Nginx and other proxies not to buffer chunks)
* **Stream Events (NDJSON)**:
  * Each event is yielded on its own line followed by `\n`.

#### Example Success Stream
```json
{"status": "running", "step": "ast", "message": "Running Phase 1: Static AST validation..."}
{"status": "running", "step": "runtime", "message": "Running Phase 2: Runtime verification..."}
{"status": "running", "step": "saving", "message": "Registering and saving module..."}
{"status": "success", "module": {"id": 5, "name": "custom_module", "device_type": "camera", "version": "1.0.0", "author": "Operator", "file_path": "/app/modules/custom_module.py", "is_official": false, "status": "active", "created_at": "2026-06-12T14:00:00Z"}}
```

#### Example Failure Stream (AST Validation Fails)
```json
{"status": "running", "step": "ast", "message": "Running Phase 1: Static AST validation..."}
{"status": "failed", "step": "ast", "message": "Module validation failed", "validation_result": {"valid": false, "phases": [{"phase": "ast", "passed": false, "checks": [{"name": "has_module_version", "passed": false, "message": "Missing required constant 'MODULE_VERSION'", "line": null, "fix_suggestion": "Add at module level: MODULE_VERSION = \"1.0.0\""}]}]}}
```

#### Example Failure Stream (Runtime Validation Fails)
```json
{"status": "running", "step": "ast", "message": "Running Phase 1: Static AST validation..."}
{"status": "running", "step": "runtime", "message": "Running Phase 2: Runtime verification..."}
{"status": "failed", "step": "runtime", "message": "Module validation failed", "validation_result": {"valid": false, "phases": [{"phase": "ast", "passed": true, "checks": [...]}, {"phase": "runtime", "passed": false, "checks": [{"name": "execution", "passed": false, "message": "Execution failed: ValueError: Host not allowed"}]}]}}
```
