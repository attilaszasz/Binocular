"""Scale oracles measure bounded SQL/results, not machine-dependent wall time."""

from __future__ import annotations

import socket
from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import aiosqlite
import httpx
import pytest
from tests.db import test_catalog_reevaluation as reevaluation
from tests.db.test_catalog_work import reopened

from binocular.db import catalog_repository
from binocular.db.catalog_repository import CatalogPageCursor, CatalogRepository
from binocular.db.catalog_types import (
    CatalogModelRecord,
    Claim,
    Claimed,
    Conflict,
    Exhausted,
    ReevaluationWorkRecord,
    RefreshRunRecord,
    canonical_variant_v1,
)
from binocular.db.repository import RepositoryBase
from binocular.db.unit_of_work import WriteConnection, WriteUnit
from binocular.db.work_repository import (
    ModelReevaluation,
    ReevaluationTarget,
    RefreshItemAdmission,
    RefreshRequestReservation,
    WorkRepository,
    refresh_fence,
)
from binocular.scraping.client import ScrapeClient

SCALE = 10_000


@pytest.fixture(autouse=True)
def no_vendor_or_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: object, **kwargs: object) -> None:
        raise AssertionError("local catalog work attempted vendor/network access")

    for target, name in (
        (socket, "create_connection"), (socket, "getaddrinfo"),
        (socket.socket, "connect"), (ScrapeClient, "get"),
        (httpx.AsyncClient, "request"), (httpx.Client, "request"),
    ):
        monkeypatch.setattr(target, name, denied)


@pytest.fixture
async def large_catalog(migrated_db: aiosqlite.Connection) -> reevaluation.Fixture:
    """One real attested observation, plus one bulk unit under shipped guards.

    Thousands of product families have EU/US variants, duplicate names and
    searchable historical aliases/secondary IDs. 10,000 physical devices link
    to the observed model; fixture setup never opens one unit per row.
    """
    fixture = await reevaluation.setup(migrated_db, count=0)
    variants = tuple(canonical_variant_v1(
        region=region, mount=None, hardware_revision=None,
    ).key for region in ("EU", "US"))
    ids = [fixture.model.id, *(str(UUID(int=i, version=4)) for i in range(1, SCALE))]
    async with WriteUnit(migrated_db) as unit:
        await unit.connection.executemany(
            """INSERT INTO catalog_models
               (id,module_id,source_model_key,variant_key,display_name,
                last_seen_at,last_seen_generation) VALUES (?,7,?,?,?,20,1)""",
            [(ids[i], f"product-{i // 2:05}", variants[i % 2],
              f"Camera {i // 2:05}") for i in range(1, SCALE)],
        )
        await unit.connection.executemany(
            """INSERT INTO catalog_model_aliases(model_id,alias,search_key)
               VALUES (?,?,?)""",
            [(model_id, f"Historical {i:05}", f"historical {i:05}")
             for i, model_id in enumerate(ids)],
        )
        await unit.connection.executemany(
            """INSERT INTO catalog_model_source_ids(model_id,namespace,value)
               VALUES (?,'sku',?)""",
            [(model_id, f"SKU-{i:05}") for i, model_id in enumerate(ids)],
        )
        await unit.connection.executemany(
            """INSERT INTO devices(id,name,model,module_id,current_version,
               installed_unknown,catalog_model_id,catalog_link_state)
               VALUES (?,'owned','camera',7,'1',0,?,'linked')""",
            [(i, fixture.model.id) for i in range(1, SCALE + 1)],
        )
    row = await CatalogRepository(migrated_db).fetch_one(
        """SELECT (SELECT count(*) FROM catalog_models) AS models,
           (SELECT count(*) FROM devices) AS devices""",
    )
    assert row is not None
    assert (row["models"], row["devices"]) == (SCALE, SCALE)
    async with migrated_db.execute("PRAGMA foreign_key_check") as cursor:
        assert await cursor.fetchall() == []
    return fixture


@dataclass
class Queries:
    calls: int = 0
    batches: list[tuple[str, tuple[object, ...], int]] = field(default_factory=list)


@pytest.fixture
def queries(monkeypatch: pytest.MonkeyPatch) -> Queries:
    """Observe before Python materialization; every multirow read needs a bound."""
    result = Queries()
    fetch_all = RepositoryBase.fetch_all
    fetch_one = RepositoryBase.fetch_one
    execute = RepositoryBase.execute

    async def all_rows(
        self: RepositoryBase, sql: str, parameters: Sequence[object] = (),
    ) -> list[aiosqlite.Row]:
        result.calls += 1
        assert "LIMIT" in sql.upper()
        assert "OFFSET" not in sql.upper()
        rows = await fetch_all(self, sql, parameters)
        assert len(rows) <= 100
        result.batches.append((sql, tuple(parameters), len(rows)))
        return rows

    async def one_row(
        self: RepositoryBase, sql: str, parameters: Sequence[object] = (),
    ) -> aiosqlite.Row | None:
        result.calls += 1
        return await fetch_one(self, sql, parameters)

    async def statement(
        self: RepositoryBase, sql: str, parameters: Sequence[object] = (),
    ) -> aiosqlite.Cursor:
        result.calls += 1
        return await execute(self, sql, parameters)

    monkeypatch.setattr(RepositoryBase, "fetch_all", all_rows)
    monkeypatch.setattr(RepositoryBase, "fetch_one", one_row)
    monkeypatch.setattr(RepositoryBase, "execute", statement)
    return result


async def test_local_pages_search_and_full_cursor_walk_are_bounded(
    large_catalog: reevaluation.Fixture, queries: Queries,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = CatalogRepository(large_catalog.db)
    materialized = 0
    original = catalog_repository._model

    def model(row: aiosqlite.Row) -> CatalogModelRecord:
        nonlocal materialized
        materialized += 1
        return original(row)

    monkeypatch.setattr(catalog_repository, "_model", model)
    default = await repo.list_models(7)
    assert len(default.models) == materialized == 50
    assert queries.calls == 1
    assert queries.batches[-1][1][-1] == len(default.models)
    for query, namespace in (
        ("HiStOrIcAl 099", None), ("SKU-099", "sku"), ("product-049", None),
    ):
        before, calls = materialized, queries.calls
        page = await repo.list_models(
            7, query=query, source_namespace=namespace, limit=100,
        )
        assert len(page.models) == 100
        assert materialized - before == 100
        assert queries.calls - calls == 1
        assert queries.batches[-1][1][-1] == 100
        first = await repo.list_models(7, query=query, source_namespace=namespace)
        second = await repo.list_models(
            7, query=query, source_namespace=namespace, after=first.next_cursor,
        )
        assert (*first.models, *second.models) == page.models
        cursor: CatalogPageCursor | None = second.next_cursor
        if query == "product-049":
            tail = await repo.list_models(
                7, query=query, after=cursor, limit=100,
            )
            assert len(tail.models) == 100
            assert {m.id for m in tail.models}.isdisjoint(m.id for m in page.models)
            cursor = tail.next_cursor
        empty = await repo.list_models(
            7, query=query, source_namespace=namespace, after=cursor,
        )
        assert empty.models == ()
        assert empty.next_cursor is None
    cursor = None
    seen: set[str] = set()
    previous: tuple[str, str] | None = None
    for _ in range(SCALE // 100 + 1):
        before, calls = materialized, queries.calls
        page = await repo.list_models(7, after=cursor, limit=100)
        assert materialized - before == len(page.models) <= 100
        assert queries.calls - calls == 1
        for item in page.models:
            key = (item.display_name, item.id)
            assert previous is None or key > previous
            assert item.id not in seen
            seen.add(item.id)
            previous = key
        cursor = page.next_cursor
        if cursor is None:
            break
    assert len(seen) == SCALE
    assert cursor is None
    calls = queries.calls
    with pytest.raises(ValueError, match="invalid catalog page"):
        await repo.list_models(7, limit=101)
    assert queries.calls == calls


@pytest.mark.parametrize("limit", [50, 100])
async def test_large_fanout_atomic_chunks_wal_snapshot_and_exhausted_restart(
    large_catalog: reevaluation.Fixture, queries: Queries, limit: int,
) -> None:
    fixture = large_catalog
    repo = WorkRepository(fixture.db)
    options = {} if limit == 50 else {"chunk_limit": limit}
    work = await repo.enqueue_reevaluation(
        ModelReevaluation(fixture.model.id, 1), now=40, deadline_at=500,
        max_chunks=2, **options,
    )
    assert isinstance(work, ReevaluationWorkRecord)
    assert work.chunk_limit == limit
    owned = await reevaluation.claim(fixture.db, work)
    async with fixture.db.execute("PRAGMA journal_mode") as cursor:
        row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "wal"
    fail = True
    calls = 0

    async def effects(
        conn: WriteConnection, targets: tuple[ReevaluationTarget, ...],
    ) -> None:
        nonlocal calls
        calls += 1
        assert len(targets) == limit
        assert [t.snapshot.id for t in targets] == list(range(1, limit + 1))
        await conn.executemany(
            "UPDATE devices SET name='local effect' WHERE id=?",
            [(target.snapshot.id,) for target in targets],
        )
        # This independent WAL reader completes while the write unit is open.
        # It must see neither effects nor cursor, including on eventual rollback.
        saved = await WorkRepository(fixture.db).get_reevaluation(work.id)
        assert saved == owned.record
        row = await CatalogRepository(fixture.db).fetch_one(
            """SELECT count(*) AS n FROM devices
               WHERE has_update=1 OR name='local effect'""",
        )
        assert row is not None
        assert row["n"] == 0
        assert len((await CatalogRepository(fixture.db).list_models(7)).models) == 50
        if fail:
            raise RuntimeError("injected after bounded local effects")

    before = queries.calls
    with pytest.raises(RuntimeError, match="injected"):
        await repo.commit_reevaluation_chunk(
            owned, expected_cursor=0, expected_chunks_used=0,
            clock=reevaluation.Clock(), local_effects=effects,
        )
    assert queries.calls - before <= 12 * limit + 20
    assert await repo.get_reevaluation(work.id) == owned.record
    fail = False
    before = queries.calls
    first = await repo.commit_reevaluation_chunk(
        owned, expected_cursor=0, expected_chunks_used=0,
        clock=reevaluation.Clock(), local_effects=effects,
    )
    assert queries.calls - before <= 12 * limit + 20
    assert calls == 2
    assert isinstance(first, ReevaluationWorkRecord)
    assert (first.cursor_device_id, first.chunks_used, first.state) == (
        limit, 1, "running",
    )
    row = await repo.fetch_one(
        """SELECT count(*) AS n FROM devices
           WHERE has_update=1 AND name='local effect'""",
    )
    assert row is not None
    assert row["n"] == limit
    async with reopened(fixture.db) as db:
        repo = WorkRepository(db)
        assert await repo.get_reevaluation(work.id) == first
        current = await reevaluation.claim(db, first, now=100, lease=1000)
        assert current.claim.lease_until == 500
        before = queries.calls
        final = await repo.commit_reevaluation_chunk(
            current, expected_cursor=limit, expected_chunks_used=1,
            clock=reevaluation.Clock(101),
        )
        assert queries.calls - before <= 12 * limit + 20
        assert isinstance(final, ReevaluationWorkRecord)
        assert (final.cursor_device_id, final.chunks_used, final.state,
                final.error_code) == (2 * limit, 2, "failed", "budget")
        scans = [batch for batch in queries.batches
                 if "SELECT id FROM devices" in batch[0]]
        assert len(scans) == 3
        assert all(params[-1] == count == limit for _, params, count in scans)
        async with reopened(db) as restarted:
            repo = WorkRepository(restarted)
            assert await repo.get_reevaluation(work.id) == final
            assert await repo.enqueue_reevaluation(
                ModelReevaluation(fixture.model.id, 1), now=200, deadline_at=5000,
                max_chunks=1000, chunk_limit=100,
            ) == final
            assert isinstance(await repo.claim_reevaluation(
                work.id, owner_instance=str(uuid4()), now=500, lease_until=600,
            ), Conflict)
            row = await repo.fetch_one(
                "SELECT count(*) AS n FROM devices WHERE has_update=1",
            )
            assert row is not None
            assert row["n"] == 2 * limit


async def test_large_fanout_deadline_survives_restart_without_local_effects(
    large_catalog: reevaluation.Fixture, queries: Queries,
) -> None:
    fixture = large_catalog
    target = ModelReevaluation(fixture.model.id, 1)
    work = await WorkRepository(fixture.db).enqueue_reevaluation(
        target, now=40, deadline_at=50, max_chunks=200,
    )
    assert isinstance(work, ReevaluationWorkRecord)
    owned = await reevaluation.claim(fixture.db, work, lease=1000)
    assert owned.claim.lease_until == 50
    async with reopened(fixture.db) as db:
        repo = WorkRepository(db)
        assert await repo.get_reevaluation(work.id) == owned.record
        before = len(queries.batches)
        assert isinstance(await repo.commit_reevaluation_chunk(
            owned, expected_cursor=0, expected_chunks_used=0,
            clock=reevaluation.Clock(50),
        ), Conflict)
        assert len(queries.batches) == before
        assert await repo.expire_reevaluation(work.id, now=50) == Exhausted("deadline")
        failed = await repo.get_reevaluation(work.id)
        assert failed is not None
        assert (failed.state, failed.error_code, failed.chunks_used,
                failed.cursor_device_id, failed.deadline_at) == (
                    "failed", "deadline", 0, 0, 50,
                )
        async with reopened(db) as restarted:
            repo = WorkRepository(restarted)
            assert await repo.enqueue_reevaluation(
                target, now=60, deadline_at=5000, max_chunks=1000, chunk_limit=100,
            ) == failed
            assert isinstance(await repo.claim_reevaluation(
                work.id, owner_instance=str(uuid4()), now=60, lease_until=500,
            ), Conflict)
            row = await repo.fetch_one(
                "SELECT count(*) AS n FROM devices WHERE has_update=1",
            )
            assert row is not None
            assert row["n"] == 0


@pytest.mark.parametrize("budget", ["requests", "models", "deadline"])
async def test_large_catalog_refresh_bounds_survive_restart(
    large_catalog: reevaluation.Fixture, budget: str,
) -> None:
    fixture = large_catalog
    repo = WorkRepository(fixture.db)
    state = await CatalogRepository(fixture.db).module_state(7)
    assert state is not None
    assert state.enumeration_last_attempt_id is not None
    initial = await repo.get_refresh(state.enumeration_last_attempt_id)
    assert initial is not None
    assert initial.claim_token is not None
    assert initial.owner_instance is not None
    assert initial.lease_until is not None
    initial_fence = refresh_fence(Claimed(initial, Claim(
        initial.claim_token, initial.claim_generation, initial.owner_instance,
        initial.lease_until,
    )))
    assert await CatalogRepository(fixture.db).finish_enumeration(
        initial_fence, now=40, outcome="cancelled",
    ) is True
    assert isinstance(await repo.finish_refresh(
        initial_fence, now=40, outcome="cancelled", expected_cursor=None,
        expected_requests_used=0, expected_models_used=0,
    ), RefreshRunRecord)
    run = await repo.create_refresh(
        module_id=7, now=40, deadline_at=200,
        max_requests=1, max_models=1,
    )
    assert isinstance(run, RefreshRunRecord)
    owned = await repo.claim_refresh(
        run.id, generation=run.generation, config_generation=1,
        owner_instance=str(uuid4()), now=40, lease_until=100,
    )
    assert isinstance(owned, Claimed)
    fence = refresh_fence(owned)
    items = await repo.admit_items(
        fence, (RefreshItemAdmission(fixture.model.id, 150, 1),), now=41,
        expected_cursor=None, next_cursor="00001",
    )
    assert isinstance(items, tuple)
    if budget == "requests":
        assert isinstance(await repo.reserve_request(
            fence, now=42, expected_requests_used=0,
            model_id=fixture.model.id, expected_item_requests_used=0,
        ), RefreshRequestReservation)
    before = await repo.get_refresh(run.id)
    assert before is not None
    async with reopened(fixture.db) as db:
        repo = WorkRepository(db)
        assert await repo.get_refresh(run.id) == before
        assert await repo.create_refresh(
            module_id=7, now=99, deadline_at=5000,
            max_requests=1000, max_models=SCALE,
        ) == before
        result = await repo.claim_refresh(
            run.id, generation=run.generation, config_generation=1,
            owner_instance=str(uuid4()), now=200 if budget == "deadline" else 100,
            lease_until=1000,
        )
        if budget == "models":
            assert isinstance(result, Claimed)
            assert result.record.models_used == result.record.max_models == 1
            assert result.claim.lease_until == 200
            other = (await CatalogRepository(db).list_models(7)).models[1]
            assert await repo.admit_items(
                refresh_fence(result), (RefreshItemAdmission(other.id, 150, 1),),
                now=101, expected_cursor="00001", next_cursor="00002",
            ) == Exhausted("models")
        else:
            assert result == Exhausted(
                "requests" if budget == "requests" else "deadline",
            )
        saved = await repo.get_refresh(run.id)
        assert saved is not None
        assert (saved.deadline_at, saved.max_models, saved.models_used,
                saved.max_requests, saved.requests_used, saved.cursor) == (
                    200, 1, 1, 1, int(budget == "requests"), "00001",
                )
        item = await repo.get_item(run.id, fixture.model.id)
        assert item is not None
        assert (item.deadline_at, item.max_requests, item.requests_used) == (
            150, 1, int(budget == "requests"),
        )
