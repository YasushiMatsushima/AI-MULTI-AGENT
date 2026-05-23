"""Command Handler: コマンドを受けて Aggregate を介してイベントを発行する。

各コマンドハンドラは以下の流れで動作する：
  1. Event Store から Aggregate をロード（スナップショット + 差分イベント）
  2. ビジネスルールを検証
  3. 新しいイベントを Event Store に追記
  4. スナップショット間隔に達していればスナップショットを保存
"""

from src.cqrs.aggregates import AggregateError, TodoAggregate
from src.cqrs.commands import (
    AddTodoCommand,
    CompleteTodoCommand,
    DeleteTodoCommand,
)
from src.cqrs.event_store import EventStore
from src.cqrs.events import Event, TodoAdded, TodoCompleted, TodoDeleted

# スナップショット間隔（このイベント数ごとにスナップショット保存）
SNAPSHOT_INTERVAL = 10

_VALID_PRIORITIES = frozenset({"高", "中", "低"})


class CommandHandler:
    """コマンドを処理してイベントを発行するハンドラ。"""

    def __init__(
        self, event_store: EventStore, snapshot_interval: int = SNAPSHOT_INTERVAL
    ) -> None:
        self._store = event_store
        self._snapshot_interval = snapshot_interval

    def handle_add(self, cmd: AddTodoCommand) -> Event:
        """新規 Todo を追加する。

        Raises:
            ValueError: title が空白のみ、または priority が不正な場合。
            AggregateError: 同じ aggregate_id が既に存在する場合。
        """
        title = cmd.title.strip() if cmd.title else ""
        if not title:
            raise ValueError("タイトルは空にできません")
        if cmd.priority not in _VALID_PRIORITIES:
            raise ValueError(
                f"優先度は '高', '中', '低' のいずれかを指定してください: {cmd.priority!r}"
            )

        agg = self._load(cmd.aggregate_id)
        if agg.exists:
            raise AggregateError(f"既に存在するアイテム: {cmd.aggregate_id}")

        event = TodoAdded(
            aggregate_id=cmd.aggregate_id,
            version=agg.version + 1,
            title=title,
            category=cmd.category.strip(),
            priority=cmd.priority,
        )
        self._store.append(event)
        self._maybe_snapshot(cmd.aggregate_id, agg, event)
        return event

    def handle_complete(self, cmd: CompleteTodoCommand) -> Event:
        """Todo を完了状態にする。

        Raises:
            AggregateError: 存在しない、削除済み、または既に完了済みの場合。
        """
        agg = self._load(cmd.aggregate_id)
        if not agg.exists:
            raise AggregateError(f"存在しないアイテム: {cmd.aggregate_id}")
        if agg.deleted:
            raise AggregateError(f"削除済みのアイテム: {cmd.aggregate_id}")
        if agg.completed:
            raise AggregateError(f"既に完了済み: {cmd.aggregate_id}")

        event = TodoCompleted(
            aggregate_id=cmd.aggregate_id,
            version=agg.version + 1,
        )
        self._store.append(event)
        self._maybe_snapshot(cmd.aggregate_id, agg, event)
        return event

    def handle_delete(self, cmd: DeleteTodoCommand) -> Event:
        """Todo を削除する（論理削除イベントを発行）。

        Raises:
            AggregateError: 存在しない、または既に削除済みの場合。
        """
        agg = self._load(cmd.aggregate_id)
        if not agg.exists:
            raise AggregateError(f"存在しないアイテム: {cmd.aggregate_id}")
        if agg.deleted:
            raise AggregateError(f"既に削除済み: {cmd.aggregate_id}")

        event = TodoDeleted(
            aggregate_id=cmd.aggregate_id,
            version=agg.version + 1,
        )
        self._store.append(event)
        self._maybe_snapshot(cmd.aggregate_id, agg, event)
        return event

    def _load(self, aggregate_id: str) -> TodoAggregate:
        """スナップショット + 差分イベントで Aggregate を復元する。"""
        snap = self._store.load_snapshot(aggregate_id)
        if snap is None:
            events = self._store.load_events(aggregate_id, from_version=0)
            return TodoAggregate.from_events(aggregate_id, events)
        state, snap_version = snap
        events = self._store.load_events(aggregate_id, from_version=snap_version)
        return TodoAggregate.from_events(
            aggregate_id, events, snapshot=state, snapshot_version=snap_version
        )

    def _maybe_snapshot(
        self, aggregate_id: str, agg: TodoAggregate, event: Event
    ) -> None:
        """version が snapshot_interval の倍数に達していたらスナップショットを保存。

        既に手元にある Aggregate と直近の Event から最新状態を組み立てるため、
        Event Store からの再ロードは行わない（TOCTOU 回避とパフォーマンス改善）。
        """
        if event.version <= 0 or event.version % self._snapshot_interval != 0:
            return
        agg.apply(event)
        self._store.save_snapshot(aggregate_id, agg.to_snapshot(), agg.version)
