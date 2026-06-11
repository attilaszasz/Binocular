"""Extension modules REST API routes."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, UploadFile

from binocular.deps import DBDep
from binocular.devices.models import (
    ModuleResponse,
    ModuleUpdate,
    ScheduleResponse,
    ScheduleUpdate,
)
from binocular.extensions.loader import ModuleLoader
from binocular.extensions.repository import ModuleRepository
from binocular.extensions.validator import validate_module

router = APIRouter(prefix="/api/v1", tags=["modules"])


def _repository(db: DBDep) -> ModuleRepository:
    return ModuleRepository(db)


@router.get("/modules", response_model=list[ModuleResponse])
async def list_modules(db: DBDep) -> list[ModuleResponse]:
    """List all registered modules with full metadata."""
    repo = _repository(db)
    rows = await repo.list_all()
    res = []
    for r in rows:
        d = dict(r)
        d["is_official"] = bool(d["is_official"])
        res.append(ModuleResponse(**d))
    return res


@router.post("/modules", response_model=ModuleResponse, status_code=201)
async def upload_module(
    file: UploadFile,
    db: DBDep,
    request: Request,
    run_phase2: bool = False,
) -> Any:
    """Upload and validate a module file."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    filename = Path(file.filename).name
    if not filename.endswith(".py"):
        raise HTTPException(
            status_code=400, detail="Uploaded file must be a Python (.py) file."
        )

    settings = request.app.state.settings
    modules_dir = settings.modules_dir
    modules_dir.mkdir(parents=True, exist_ok=True)

    contents = await file.read()

    # Run validation in a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir) / filename
        temp_path.write_bytes(contents)

        # Phase 1: AST validation
        validation_result = validate_module(temp_path)

        # Phase 2: Runtime validation (optional)
        if run_phase2 and validation_result.valid:
            loader = ModuleLoader(temp_path.parent)
            load_result = loader.load(temp_path)
            if load_result.success:
                validation_result = validate_module(
                    temp_path,
                    loaded_module=load_result.module,
                    run_phase2=True,
                    test_client=request.app.state.scrape_client,
                )
            else:
                validation_result = validate_module(
                    temp_path,
                    loaded_module=None,
                    run_phase2=False,
                )

        if not validation_result.valid:
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=422,
                content={
                    "detail": "Module validation failed",
                    "validation_result": {
                        "valid": False,
                        "phases": [
                            {
                                "phase": phase.phase,
                                "passed": phase.passed,
                                "checks": [
                                    {
                                        "name": check.name,
                                        "passed": check.passed,
                                        "message": check.message,
                                        "line": check.line,
                                        "fix_suggestion": check.fix_suggestion,
                                    }
                                    for check in phase.checks
                                ],
                            }
                            for phase in validation_result.phases
                        ],
                    },
                },
            )

        # Load the module to extract properties
        loader = ModuleLoader(temp_path.parent)
        load_result = loader.load(temp_path)
        if not load_result.success:
            raise HTTPException(
                status_code=422, detail="Failed to load module properties."
            )

        name = load_result.module_name
        device_type = load_result.device_type
        version = load_result.version
        author = (
            getattr(load_result.module, "MODULE_AUTHOR", "")
            or getattr(load_result.module, "__author__", "")
            or "Operator"
        )

        # Save file to final modules directory
        final_path = modules_dir / filename
        final_path.write_bytes(contents)

        # Register in database
        repo = _repository(db)
        existing = await repo.get_by_name(name)
        if existing:
            await repo.update(
                existing["id"],
                device_type=device_type,
                version=version,
                author=author,
                file_path=str(final_path),
                status="active",
            )
            module_id = existing["id"]
        else:
            module_id = await repo.create(
                name=name,
                device_type=device_type,
                version=version,
                author=author,
                file_path=str(final_path),
                is_official=False,
                status="active",
            )

        row = await repo.get_by_id(module_id)
        if not row:
            raise HTTPException(
                status_code=500, detail="Failed to retrieve registered module."
            )

        # Register/ensure schedule is active in background scheduler
        scheduler = request.app.state.scheduler
        await scheduler.register_new_module(module_id)

        d = dict(row)
        d["is_official"] = bool(d["is_official"])
        return ModuleResponse(**d)


@router.put("/modules/{module_id}", response_model=ModuleResponse)
async def update_module(
    module_id: int,
    body: ModuleUpdate,
    db: DBDep,
    request: Request,
) -> ModuleResponse:
    """Update a module's status."""
    repo = _repository(db)
    existing = await repo.get_by_id(module_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Module not found")

    await repo.update(module_id, status=body.status)

    # Enable or disable background job
    scheduler = request.app.state.scheduler
    if body.status == "active":
        await scheduler.register_new_module(module_id)
    else:
        scheduler.remove_job(module_id)

    updated = await repo.get_by_id(module_id)
    if not updated:
        raise HTTPException(
            status_code=500, detail="Failed to retrieve updated module."
        )

    d = dict(updated)
    d["is_official"] = bool(d["is_official"])
    return ModuleResponse(**d)


@router.delete("/modules/{module_id}", status_code=204)
async def delete_module(
    module_id: int,
    db: DBDep,
    request: Request,
) -> None:
    """Delete a module."""
    repo = _repository(db)
    existing = await repo.get_by_id(module_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Module not found")

    # Check if module is currently linked to devices
    cursor = await db.execute(
        "SELECT COUNT(*) FROM devices WHERE module_id = ?", (module_id,)
    )
    row = await cursor.fetchone()
    count = row[0] if row else 0
    if count > 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot delete module: it is currently referenced"
                f" by {count} active devices."
            ),
        )

    # Remove background job
    scheduler = request.app.state.scheduler
    scheduler.remove_job(module_id)

    file_path_str = dict(existing).get("file_path")
    deleted = await repo.delete(module_id)
    if deleted and file_path_str:
        path = Path(file_path_str)
        path.unlink(missing_ok=True)


@router.get("/schedules", response_model=list[ScheduleResponse])
async def list_schedules(db: DBDep) -> list[ScheduleResponse]:
    """Retrieve all schedules with module details."""
    cursor = await db.execute(
        """
        SELECT s.module_id, m.name AS module_name, m.device_type,
               s.interval_hours, s.last_run, s.next_run
        FROM schedules s
        JOIN modules m ON s.module_id = m.id
        ORDER BY m.name
        """
    )
    rows = await cursor.fetchall()
    return [
        ScheduleResponse(
            module_id=row[0],
            module_name=row[1],
            device_type=row[2],
            interval_hours=row[3],
            last_run=row[4],
            next_run=row[5],
        )
        for row in rows
    ]


@router.put("/schedules", response_model=ScheduleResponse)
async def update_schedule(
    body: ScheduleUpdate,
    db: DBDep,
    request: Request,
) -> ScheduleResponse:
    """Update check interval hours for a specific module."""
    cursor = await db.execute(
        "SELECT name, device_type FROM modules WHERE id = ?", (body.module_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Module not found")

    module_name, device_type = row

    scheduler = request.app.state.scheduler
    await scheduler.reschedule_module(body.module_id, body.interval_hours)

    # Retrieve updated schedule timestamps
    cursor = await db.execute(
        "SELECT last_run, next_run FROM schedules WHERE module_id = ?",
        (body.module_id,),
    )
    sched_row = await cursor.fetchone()
    last_run = sched_row[0] if sched_row else None
    next_run = sched_row[1] if sched_row else None

    return ScheduleResponse(
        module_id=body.module_id,
        module_name=module_name,
        device_type=device_type,
        interval_hours=body.interval_hours,
        last_run=last_run,
        next_run=next_run,
    )
