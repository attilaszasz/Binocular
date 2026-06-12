---
adr_id: ADR-0011
status: accepted
date: 2026-06-12
tags: [modules, validation, upload, streaming, ux]
supersedes: []
superseded_by: ""
related_artifacts: [specs/prd.md, specs/sad.md]
---

# ADR-0011: Real-Time Module Validation and Upload Progress Streaming

## Status
accepted

## Context
Uploading and validating a custom module in Binocular involves two distinct phases: Phase 1 (AST-based static structure analysis) and Phase 2 (Runtime execution proof). Phase 2 can take several seconds to execute because it runs the module's `check_firmware` function with mock inputs, which may involve external network requests or slow CPU parsing.

Currently, the POST `/api/v1/modules` upload endpoint blocks and returns a single JSON response once validation is completely finished. In the UI, the upload button simply shows a static "Validating & Uploading..." text. During long-running Phase 2 checks, this lack of updates makes it unclear if the server has crashed or is still processing. We need a way to stream step-by-step progress from the backend during validation to improve user feedback.

## Decision Drivers
- Visual feedback: Users must see what the validation pipeline is doing in real-time (especially during Phase 2).
- Architectural simplicity: Avoid adding heavy infrastructure (like Redis, WebSockets, or a separate task worker process) just to support upload progress.
- API compatibility: Keep file upload and validation tied to a single unified operation, without requiring multiple polling endpoints.

## Considered Options
### Option A: Blocking REST Request (Current)
- Pros: Simple to implement; fits standard OpenAPI code generators.
- Cons: No progress updates; browser requests might time out; users feel like the app is hung.

### Option B: Background Task Queue with Polling
- Pros: Completely non-blocking; returns a task ID immediately so client can query status periodically.
- Cons: Increases architectural complexity; requires task status storage (in SQLite/memory) and polling state management on both backend and frontend.

### Option C: Streaming Chunked Response (Newline-Delimited JSON)
- Pros: Allows the frontend to perform a single `multipart/form-data` upload POST request and read validation progress chunks in real-time. No extra database tables or background tasks are needed. Simple to implement using standard HTTP chunked transfer coding and Python generators.
- Cons: The client must process the response body stream using `ReadableStream` rather than simply waiting for a JSON parse, and the backend must yield individual JSON lines.

## Decision Outcome
Chosen option: **Option C: Streaming Chunked Response (Newline-Delimited JSON)** — It achieves the UX goals of real-time visual progress without adding the complexity of task managers, extra endpoints, or WebSockets, fitting perfectly into the self-contained monolith architecture.

## Consequences
### Positive
- The frontend can show the user exactly which step is running (e.g. AST parsing, runtime mock execution, registering, saving) and display a clear step-by-step checklist.
- Immediate response initialization keeps connection active and avoids gateway/browser timeouts.
- Monolith remains light and does not require task persistence/workers.

### Negative
- The REST API endpoint POST `/api/v1/modules` changes its return type from a flat JSON object to a chunked stream of newline-delimited JSON objects. The frontend client (React/TanStack Query) must be adapted to read from the stream.

## Links
- PRD capability: CAP-003 (Module Lifecycle Management)
- SAD sections: Key Runtime Flows and Failure Paths, Integration Strategy
