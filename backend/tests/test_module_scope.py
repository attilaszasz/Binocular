"""Scope snapshots and explicit pause HTTP boundaries on isolated SQLite."""

import json
from pathlib import Path
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient

from binocular.app import create_app
from binocular.config import Settings
from binocular.extensions.repository import ModuleRepository


async def test_replacement_omission_and_failed_write(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path, modules_dir=tmp_path / "modules", seed_modules=False
    )
    app = create_app(settings=settings)
    async with app.router.lifespan_context(app):
        db = app.state.db
        repo = ModuleRepository(db)
        settings.modules_dir.mkdir(exist_ok=True)
        path = settings.modules_dir / "sony_alpha.py"
        path.write_text("# original protected bytes")
        mid = await repo.create(
            name="sony_alpha",
            device_type="camera",
            file_path=str(path),
            status="inactive",
            is_official=True,
            display_name="Old official label",
            registration_origin="bundled",
            official_content_hash="a" * 64,
        )
        await db.execute(
            "UPDATE schedules SET interval_hours=6 WHERE module_id=?", (mid,)
        )
        await db.commit()
        code = (
            b'MODULE_VERSION="1"\nSUPPORTED_DEVICE_TYPE="lens"\n'
            b'def check_firmware(a,b,c): return {"latest_version":"1"}\n'
        )
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/modules", files={"file": ("sony_alpha.py", code)}
            )
            last = json.loads(response.text.splitlines()[-1])
            assert last["status"] == "success"
            assert last["module"]["status"] == "inactive"
            assert last["module"]["guidance_provenance"] == "custom"
            assert not last["module"]["is_official"]
            stored = await repo.get_by_id(mid)
            assert stored is not None
            row = dict(stored)
            assert row["display_name"] == ""
            assert row["official_content_hash"] == ""
            assert app.state.scheduler.admission.ticket(mid) is None
            with patch.object(
                ModuleRepository, "update", side_effect=RuntimeError("write failed")
            ):
                response = await client.post(
                    "/api/v1/modules",
                    files={"file": ("sony_alpha.py", code + b"# new bytes")},
                )
            assert json.loads(response.text.splitlines()[-1])["status"] == "failed"
            assert path.read_bytes() == code


async def test_scope_zero_one_many_relink_delete(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            data_dir=tmp_path, modules_dir=tmp_path / "modules", seed_modules=False
        )
    )
    async with app.router.lifespan_context(app):
        db = app.state.db
        await db.execute("INSERT INTO modules (name) VALUES ('a'), ('b')")
        await db.commit()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:

            async def scope(count: int) -> None:
                response = await client.get("/api/v1/modules/1/devices")
                assert response.status_code == 200
                data = response.json()
                assert data["linked_device_count"] == len(data["devices"]) == count
                modules = (await client.get("/api/v1/modules")).json()
                assert modules[0]["linked_device_count"] == count

            await scope(0)
            first = (
                await client.post(
                    "/api/v1/devices", json={"name": "first", "module_id": 1}
                )
            ).json()
            await scope(1)
            second = (
                await client.post(
                    "/api/v1/devices", json={"name": "second", "module_id": 1}
                )
            ).json()
            await scope(2)
            await client.put(f"/api/v1/devices/{first['id']}", json={"module_id": 2})
            await scope(1)
            await client.delete(f"/api/v1/devices/{second['id']}")
            await scope(0)
            assert (await client.get("/api/v1/modules/999/devices")).status_code == 404
            pause = await client.put("/api/v1/modules/1", json={"status": "inactive"})
            assert pause.status_code == 200
            assert app.state.scheduler.admission.ticket(1) is None
            assert (
                await client.put("/api/v1/modules/1", json={"status": "bogus"})
            ).status_code == 422
