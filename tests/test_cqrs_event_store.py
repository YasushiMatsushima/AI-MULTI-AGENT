"""Event Store のテスト。

スコープ:
- イベントの追記とリプレイ
- 楽観ロック（同一 aggregate_id × version で ConcurrencyError）
- スナップショットの保存と取得
"""

import uuid

import pytest

from src.cqrs.event_store import ConcurrencyError, EventStore
from src.cqrs.events import TodoAdded, TodoCompleted, TodoDeleted


@pytest.fixture
def store() -> EventStore:
    return EventStore(":memory:")


def test_append_and_load_events(store: EventStore) -> None:
    """追記したイベントを version 昇順で取り出せる。"""
    aid = str(uuid.uuid4())
    store.append(TodoAdded(aggregate_id=aid, version=1, title="買い物", category="食料", priority="高"))
    store.append(TodoCompleted(aggregate_id=aid, version=2))

    events = store.load_events(aid)
    assert len(events) == 2
    assert isinstance(events[0], TodoAdded)
    assert events[0].title == "買い物"
    assert events[0].category == "食料"
    assert events[0].priority == "高"
    assert isinstance(events[1], TodoCompleted)
    assert events[1].version == 2


def test_load_events_with_from_version_filter(store: EventStore) -> None:
    """from_version より大きい version のイベントだけが返る。"""
    aid = str(uuid.uuid4())
    store.append(TodoAdded(aggregate_id=aid, version=1, title="A"))
    store.append(TodoCompleted(aggregate_id=aid, version=2))
    store.append(TodoDeleted(aggregate_id=aid, version=3))

    events = store.load_events(aid, from_version=1)
    assert [e.version for e in events] == [2, 3]


def test_load_all_events_across_aggregates(store: EventStore) -> None:
    """異なる Aggregate のイベントが発生順に取得できる。"""
    a1, a2 = str(uuid.uuid4()), str(uuid.uuid4())
    store.append(TodoAdded(aggregate_id=a1, version=1, title="A1"))
    store.append(TodoAdded(aggregate_id=a2, version=1, title="A2"))
    store.append(TodoCompleted(aggregate_id=a1, version=2))

    events = store.load_all_events()
    assert len(events) == 3
    assert events[0].aggregate_id == a1
    assert events[1].aggregate_id == a2
    assert events[2].aggregate_id == a1


def test_concurrency_error_on_duplicate_version(store: EventStore) -> None:
    """同じ aggregate_id × version を二度書こうとすると ConcurrencyError。"""
    aid = str(uuid.uuid4())
    store.append(TodoAdded(aggregate_id=aid, version=1, title="A"))
    with pytest.raises(ConcurrencyError):
        store.append(TodoAdded(aggregate_id=aid, version=1, title="A duplicated"))


def test_snapshot_save_and_load(store: EventStore) -> None:
    """スナップショットを保存して同じ内容を取り出せる。"""
    aid = str(uuid.uuid4())
    state = {"title": "A", "category": "", "priority": "中", "completed": True, "deleted": False}
    store.save_snapshot(aid, state, version=5)

    loaded = store.load_snapshot(aid)
    assert loaded is not None
    loaded_state, loaded_version = loaded
    assert loaded_state == state
    assert loaded_version == 5


def test_snapshot_load_none_when_missing(store: EventStore) -> None:
    """存在しないスナップショットは None。"""
    assert store.load_snapshot("non-existent-id") is None


def test_snapshot_save_overwrites(store: EventStore) -> None:
    """同じ aggregate_id のスナップショットは上書きされる。"""
    aid = str(uuid.uuid4())
    store.save_snapshot(aid, {"v": 1}, version=1)
    store.save_snapshot(aid, {"v": 2}, version=2)
    loaded = store.load_snapshot(aid)
    assert loaded == ({"v": 2}, 2)


def test_event_id_uniqueness(store: EventStore) -> None:
    """同じ event_id を持つイベントは insert できない（UNIQUE 制約）。"""
    a1, a2 = str(uuid.uuid4()), str(uuid.uuid4())
    e = TodoAdded(aggregate_id=a1, version=1, title="A")
    store.append(e)
    duplicate = TodoAdded(
        aggregate_id=a2, version=1, title="B", event_id=e.event_id
    )
    with pytest.raises(ConcurrencyError):
        store.append(duplicate)
