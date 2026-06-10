---
adr_id: ADR-0005
status: accepted
date: 2026-05-31
tags: [extension-engine, security, trust-boundary]
supersedes: []
superseded_by: ""
related_artifacts: [specs/prd.md#CAP-002, specs/prd.md#CAP-003]
---

# ADR-0005: Unsandboxed extension module engine with two-phase validation

## Status

Accepted.

## Context

Binocular's differentiator is user-managed extension modules — single `.py` files that know how to scrape a manufacturer page and return the latest firmware version. The engine must define a strict interface contract, load user-dropped modules at runtime, prevent broken modules from crashing the host process, and reject malformed uploads. A key trust decision is whether to execute these user-authored scripts in a sandbox. The product runs on a trusted single-user LAN, where the user is also the operator who chooses which modules to install.

## Decision Drivers

- Enable arbitrary device-type support via user-authored scripts (CAP-002)
- Prevent broken/malicious-by-accident modules from crashing the core loop
- Reject non-conforming modules before they enter the system (CAP-003)
- Keep operational footprint minimal (no separate sandbox runtime/container per module)
- Honest, single-user trust model (operator vets their own modules)

## Considered Options

### Option A: In-process unsandboxed loading with error boundary and two-phase validation

In-process loading via `importlib.util.spec_from_file_location()` (never inserted into `sys.modules`, never `exec`/`eval`), wrapped in an error boundary (catch `Exception` and `SystemExit`, never `KeyboardInterrupt`) with execution timeouts (`asyncio.to_thread` + `asyncio.wait_for`); NO sandbox. A two-phase validation pipeline gates uploads: (1) AST-based static structure analysis without execution, (2) optional runtime execution proof.

- **Pros**: Simple, low-footprint, idiomatic Python; fault-isolated against crashes; pre-save validation blocks malformed modules.
- **Cons**: Modules run with full host privileges — arbitrary code execution by design.

### Option B: Sandboxed execution

Subprocess with seccomp/namespaces, container-per-module, or WASM/RestrictedPython.

- **Pros**: Contains malicious code.
- **Cons**: Large operational and runtime complexity, breaks single-container minimal-footprint model, RestrictedPython is incomplete/unsafe-by-reputation, container-per-module is disproportionate for a single-user LAN tool.

### Option C: No validation, free-form loading

- **Pros**: Simplest.
- **Cons**: Malformed modules silently break checks; no early feedback to authors.

## Decision Outcome

Chosen option: **Option A: in-process unsandboxed loading with an error boundary and two-phase validation**. The product's security model is an explicit trusted-LAN, single-operator boundary (see security model ADR): the user installs only modules they choose to trust, so sandboxing's heavy cost is unjustified. Instead, the engine invests in fault isolation (timeouts + broad exception/SystemExit boundary so a bad module cannot crash the host) and pre-save two-phase validation (static AST check is mandatory; runtime proof runs when test inputs are supplied) to guarantee only conforming, functional modules are accepted. The interface contract is hard-coded V1: top-level `check_firmware(url, model, http_client)` plus module constants `MODULE_VERSION` and `SUPPORTED_DEVICE_TYPE`.

## Consequences

### Positive

- Simple, low-footprint, idiomatic extensibility.
- Broken modules cannot crash the core loop.
- Malformed uploads are rejected with structured per-phase results.

### Negative

- Explicit arbitrary-code-execution trust boundary — imported third-party modules run with host privileges; mitigated only by operator vetting and non-root container, not by isolation.

### Neutral

- Modules live in a single `/app/modules/` volume.
- System-shipped modules use underscore-prefixed protected filenames.
- Modules must use the host-provided HTTP client (separate scraping ADR).

## Links

- [specs/prd.md](../prd.md) — CAP-002 (Extension Module Engine), CAP-003 (Module Lifecycle Management)
- Related: trusted-LAN security model ADR
- Related: centralized scraping client ADR
