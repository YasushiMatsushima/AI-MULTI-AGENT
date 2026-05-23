"""Read Model（TodoReadModel）のテスト。

スコープ:
- list_all がイベントを再生して現在状態を返す
- 削除済みアイテムは list から除外される
- get / list_by_category / list_by_priority のフィルタ
- get_events でイベント履歴を取得できる（監査ログ機能）
"""

import uuid

import pytest

from src.cqrs.command_handler import CommandHandler
from src.cqrs.commands import (
    AddTodoCommand,
    CompleteTodoCommand,
    DeleteTodoCommand,
)
from src.cqrs.event_store import EventStore
from src.cqrs.projections import TodoReadItem, TodoReadModel


@pytest.fixture
def setup():
    store = EventStore(":memory:")
    handler = CommandHandler(store)
    read_model = TodoReadModel(store)
    return store, handler, read_model


def test_list_all_empty(setup) -> None:
    """イベントが何もない状態では空リスト。"""
    _, _, rm = setup
    assert rm.list_all() == []


def test_list_all_reflects_added_events(setup) -> None:
    """Add したアイテムが list_all に現れる。"""
    _, handler, rm = setup
    a1, a2 = str(uuid.uuid4()), str(uuid.uuid4())
    handler.handle_add(AddTodoCommand(aggregate_id=a1, title="A", category="X", priority="高"))
    handler.handle_add(AddTodoCommand(aggregate_id=a2, title="B", category="Y", priority="低"))

    items = rm.list_all()
    assert len(items) == 2
    assert {i.title for i in items} == {"A", "B"}


def test_completed_event_reflects_in_read_model(setup) -> None:
    """Complete イベントで completed=True、updated_at が変化する。"""
    _, handler, rm = setup
    aid = str(uuid.uuid4())
    handler.handle_add(AddTodoCommand(aggregate_id=aid, title="A"))
    item_before = rm.get(aid)
    assert item_before is not None
    assert item_before.completed is False

    handler.handle_complete(CompleteTodoCommand(aggregate_id=aid))
    item_after = rm.get(aid)
    assert item_after is not None
    assert item_after.completed is True
    assert item_after.updated_at >= item_before.updated_at


def test_deleted_items_excluded_from_list(setup) -> None:
    """Delete されたアイテムは list_all/get に出てこない。"""
    _, handler, rm = setup
    aid = str(uuid.uuid4())
    handler.handle_add(AddTodoCommand(aggregate_id=aid, title="A"))
    handler.handle_delete(DeleteTodoCommand(aggregate_id=aid))

    assert rm.list_all() == []
    assert rm.get(aid) is None


def test_list_by_category(setup) -> None:
    """カテゴリでフィルタできる。"""
    _, handler, rm = setup
    a1, a2 = str(uuid.uuid4()), str(uuid.uuid4())
    handler.handle_add(AddTodoCommand(aggregate_id=a1, title="A", category="食料"))
    handler.handle_add(AddTodoCommand(aggregate_id=a2, title="B", category="仕事"))

    items = rm.list_by_category("食料")
    assert len(items) == 1
    assert items[0].title == "A"


def test_list_by_priority(setup) -> None:
    """優先度でフィルタできる。"""
    _, handler, rm = setup
    a1, a2 = str(uuid.uuid4()), str(uuid.uuid4())
    handler.handle_add(AddTodoCommand(aggregate_id=a1, title="A", priority="高"))
    handler.handle_add(AddTodoCommand(aggregate_id=a2, title="B", priority="低"))

    items = rm.list_by_priority("高")
    assert len(items) == 1
    assert items[0].title == "A"


def test_get_events_returns_full_history(setup) -> None:
    """get_events で Aggregate のイベント履歴を取得できる（監査ログ機能）。"""
    _, handler, rm = setup
    aid = str(uuid.uuid4())
    handler.handle_add(AddTodoCommand(aggregate_id=aid, title="A"))
    handler.handle_complete(CompleteTodoCommand(aggregate_id=aid))
    handler.handle_delete(DeleteTodoCommand(aggregate_id=aid))

    events = rm.get_events(aid)
    assert len(events) == 3
    assert [e.version for e in events] == [1, 2, 3]


def test_read_item_is_frozen_dataclass(setup) -> None:
    """TodoReadItem はイミュータブルである。"""
    _, handler, rm = setup
    aid = str(uuid.uuid4())
    handler.handle_add(AddTodoCommand(aggregate_id=aid, title="A"))
    item = rm.get(aid)
    assert isinstance(item, TodoReadItem)
    with pytest.raises(Exception):
        item.title = "変更"  # type: ignore[misc]
