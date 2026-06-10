# Research: Module Engine & Contract
> Feature E006 | 2026-05-31 | Inform architecture, validation, and QC choices

## Importlib Loading And Contract Shape
- **Decision**: Load module files with `importlib.util.spec_from_file_location`, then validate required metadata and async entrypoint via typed models/protocols.
- **Rationale**: Direct path loading fits a local modules volume while a narrow contract keeps downstream lifecycle and checking stable.
- **Rejected**: `load_module()` and reload-driven hot swapping because they are deprecated or hard to synchronize.
- **Pitfalls**: Do not assume annotations or `Protocol` enforce runtime behavior.
- **Sources**: https://docs.python.org/3/library/importlib.html, https://docs.python.org/3/library/typing.html

## Async Invocation Boundary
- **Decision**: Wrap each module run in `asyncio.wait_for`, map timeout/`Exception`/`SystemExit` to structured failures, and preserve host cancellation.
- **Rationale**: A broken module must be visible without crashing or stalling the app.
- **Rejected**: Catching broad `BaseException` as a generic module failure because it can swallow cancellation/interrupt semantics.
- **Pitfalls**: Timeout cancellation can take longer than the configured timeout while cleanup completes.
- **Sources**: https://docs.python.org/3/library/asyncio-task.html, https://docs.python.org/3/library/exceptions.html

## Static Validation And Trust Boundary
- **Decision**: Use AST/compile/import checks as contract lint only, with explicit documentation that modules are unsandboxed trusted code.
- **Rationale**: AST checks improve feedback but do not provide security isolation.
- **Rejected**: Marketing validation as malware prevention or sandboxing.
- **Pitfalls**: Parsing can still fail at compile/import time; annotation evaluation may execute code.
- **Sources**: https://docs.python.org/3/library/ast.html, https://docs.python.org/3/library/typing.html

## Structured Validation Results
- **Decision**: Model validation as phase-labeled Pydantic results with status, findings, duration, error type/message, and optional runtime proof output.
- **Rationale**: E008 needs actionable rejection feedback and E009 needs stable runtime failure shape.
- **Rejected**: Raising raw plugin exceptions across the core boundary.
- **Pitfalls**: Do not mix static and runtime failures without phase labels.
- **Sources**: https://pydantic.dev/docs/validation/latest/concepts/models/, https://docs.python.org/3/library/exceptions.html

## Summary
| Topic | Decision | Rationale |
|-------|----------|-----------|
| Loading | importlib path load + contract validation | Local module files need explicit loading and stable shape. |
| Runtime | wait_for boundary + structured failures | Broken modules must not crash/stall the core. |
| Validation | AST/import + optional runtime proof | Phase-specific feedback catches shape and runtime defects. |
| Trust | explicit unsandboxed docs | Validation is not isolation. |

## Sources Index
| URL | Topic | Fetched |
|-----|-------|---------|
| https://docs.python.org/3/library/importlib.html | Loading | 2026-05-31 |
| https://docs.python.org/3/library/typing.html | Contract/AST | 2026-05-31 |
| https://docs.python.org/3/library/asyncio-task.html | Runtime | 2026-05-31 |
| https://docs.python.org/3/library/exceptions.html | Runtime/Results | 2026-05-31 |
| https://docs.python.org/3/library/ast.html | Validation | 2026-05-31 |
| https://pydantic.dev/docs/validation/latest/concepts/models/ | Results | 2026-05-31 |
