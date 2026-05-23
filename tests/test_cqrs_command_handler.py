"""Command Handler のテスト。

スコープ:
- AddTodoCommand（title/category の strip、不正 priority、重複 ID）
- CompleteTodoCommand（未存在、既完了、削除済み）
- DeleteTodoCommand（未存在、既削除）
- スナップショット間隔到達時に自動保存される
"""

import uuid

import pytest

from src.cqrs.aggregates import AggregateError
from src.cqrs.command_handler import CommandHandler
from src.cqrs.commands import (
    AddTodoCommand,
    CompleteTodoCommand,
    DeleteTodoCommand,
)
from src.cqrs.event_store import EventStore
from src.cqrs.events import TodoAdded, TodoCompleted, TodoDeleted


@pytest.fixture
def handler() -> CommandHandler:
    return CommandHandler(EventStore(":memory:"), snapshot_interval=3)


@pytest.fixture
def aid() -> str:
    return str(uuid.uuid4())


# ----- AddTodoCommand -----


def test_handle_add_strips_title_and_category(handler: CommandHandler, aid: str) -> None:
    """title と category の前後空白は除去されて保存される。"""
    event = handler.handle_add(
        AddTodoCommand(aggregate_id=aid, title="  買い物  ", category="  食料  ", priority="高")
    )
    assert isinstance(event, TodoAdded)
    assert event.title == "買い物"
    assert event.category == "食料"
    assert event.priority == "高"
    assert event.version == 1


def test_handle_add_blank_title_raises(handler: CommandHandler, aid: str) -> None:
    """空白のみの title は ValueError。"""
    with pytest.raises(ValueError, match="タイトルは空にできません"):
        handler.handle_add(AddTodoCommand(aggregate_id=aid, title="   "))


def test_handle_add_invalid_priority_raises(handler: CommandHandler, aid: str) -> None:
    """不正な priority は ValueError。"""
    with pytest.raises(ValueError, match="優先度は"):
        handler.handle_add(AddTodoCommand(aggregate_id=aid, title="A", priority="緊急"))


def test_handle_add_duplicate_id_raises(handler: CommandHandler, aid: str) -> None:
    """同じ aggregate_id への再 Add は AggregateError。"""
    handler.handle_add(AddTodoCommand(aggregate_id=aid, title="A"))
    with pytest.raises(AggregateError, match="既に存在"):
        handler.handle_add(AddTodoCommand(aggregate_id=aid, title="B"))


# ----- CompleteTodoCommand -----


def test_handle_complete_after_add(handler: CommandHandler, aid: str) -> None:
    """Add 後の Complete は version=2 の TodoCompleted を発行する。"""
    handler.handle_add(AddTodoCommand(aggregate_id=aid, title="A"))
    event = handler.handle_complete(CompleteTodoCommand(aggregate_id=aid))
    assert isinstance(event, TodoCompleted)
    assert event.version == 2


def test_handle_complete_unknown_id_raises(handler: CommandHandler, aid: str) -> None:
    """存在しない ID への Complete は AggregateError。"""
    with pytest.raises(AggregateError, match="存在しない"):
        handler.handle_complete(CompleteTodoCommand(aggregate_id=aid))


def test_handle_complete_already_completed_raises(
    handler: CommandHandler, aid: str
) -> None:
    """既に完了済みへの再 Complete は AggregateError。"""
    handler.handle_add(AddTodoCommand(aggregate_id=aid, title="A"))
    handler.handle_complete(CompleteTodoCommand(aggregate_id=aid))
    with pytest.raises(AggregateError, match="既に完了済み"):
        handler.handle_complete(CompleteTodoCommand(aggregate_id=aid))


def test_handle_complete_deleted_raises(handler: CommandHandler, aid: str) -> None:
    """削除済みへの Complete は AggregateError。"""
    handler.handle_add(AddTodoCommand(aggregate_id=aid, title="A"))
    handler.handle_delete(DeleteTodoCommand(aggregate_id=aid))
    with pytest.raises(AggregateError, match="削除済み"):
        handler.handle_complete(CompleteTodoCommand(aggregate_id=aid))


# ----- DeleteTodoCommand -----


def test_handle_delete_after_add(handler: CommandHandler, aid: str) -> None:
    """Add 後の Delete は version=2 の TodoDeleted を発行する。"""
    handler.handle_add(AddTodoCommand(aggregate_id=aid, title="A"))
    event = handler.handle_delete(DeleteTodoCommand(aggregate_id=aid))
    assert isinstance(event, TodoDeleted)
    assert event.version == 2


def test_handle_delete_unknown_id_raises(handler: CommandHandler, aid: str) -> None:
    """存在しない ID への Delete は AggregateError。"""
    with pytest.raises(AggregateError, match="存在しない"):
        handler.handle_delete(DeleteTodoCommand(aggregate_id=aid))


def test_handle_delete_twice_raises(handler: CommandHandler, aid: str) -> None:
    """二度目の Delete は AggregateError。"""
    handler.handle_add(AddTodoCommand(aggregate_id=aid, title="A"))
    handler.handle_delete(DeleteTodoCommand(aggregate_id=aid))
    with pytest.raises(AggregateError, match="既に削除済み"):
        handler.handle_delete(DeleteTodoCommand(aggregate_id=aid))


# ----- Snapshot -----


def test_snapshot_taken_at_interval() -> None:
    """snapshot_interval イベントごとにスナップショットが保存される。"""
    store = EventStore(":memory:")
    handler = CommandHandler(store, snapshot_interval=2)
    aid = str(uuid.uuid4())

    # version 1: 保存されない
    handler.handle_add(AddTodoCommand(aggregate_id=aid, title="A"))
    assert store.load_snapshot(aid) is None

    # version 2: 保存される
    handler.handle_complete(CompleteTodoCommand(aggregate_id=aid))
    snap = store.load_snapshot(aid)
    assert snap is not None
    state, version = snap
    assert version == 2
    assert state["completed"] is True


def test_replay_with_snapshot_yields_same_state() -> None:
    """スナップショット経由でロードしても、最終状態は同じ。"""
    store = EventStore(":memory:")
    handler = CommandHandler(store, snapshot_interval=2)
    aid = str(uuid.uuid4())

    handler.handle_add(AddTodoCommand(aggregate_id=aid, title="A", priority="高"))
    handler.handle_complete(CompleteTodoCommand(aggregate_id=aid))

    # スナップショット経由で load されることを確認
    loaded = handler._load(aid)
    assert loaded.title == "A"
    assert loaded.priority == "高"
    assert loaded.completed is True
    assert loaded.version == 2
