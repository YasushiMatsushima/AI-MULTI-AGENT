"""Read Model（Projection）: 全イベントを再生して現在状態のビューを構築する。

CQRS の Q 側を担当。Read Model は Event Store の全イベントを順に適用し、
クエリしやすい形に整形する。書き込み側（Command）と分離されている点が CQRS の本質。
"""

from dataclasses import dataclass
from typing import Any

from src.cqrs.event_store import EventStore
from src.cqrs.events import Event, TodoAdded, TodoCompleted, TodoDeleted


@dataclass(frozen=True)
class TodoReadItem:
    """Read Model 側の Todo データ表現（API レスポンスにそのまま使える）。"""

    id: str
    title: str
    category: str
    priority: str
    completed: bool
    created_at: str
    updated_at: str


class TodoReadModel:
    """全イベントを再生して Todo 一覧のビューを提供する Read Model。

    本実装はキャッシュを持たず毎回イベントを全件再生する。学習目的としては
    Event Sourcing の本質（状態はイベントから導出される）を理解しやすい。
    本番ではキャッシュ + 増分更新（イベントサブスクライブ）で高速化する。
    """

    def __init__(self, event_store: EventStore) -> None:
        self._store = event_store

    def list_all(self) -> list[TodoReadItem]:
        """削除されていない全 Todo のリストを返す。"""
        items = self._build_state()
        return [TodoReadItem(**data) for data in items.values()]

    def get(self, aggregate_id: str) -> TodoReadItem | None:
        """指定 ID の Todo を返す。削除済み・存在しない場合は None。"""
        items = self._build_state()
        data = items.get(aggregate_id)
        return TodoReadItem(**data) if data is not None else None

    def list_by_category(self, category: str) -> list[TodoReadItem]:
        """指定カテゴリの Todo のみを返す。"""
        return [item for item in self.list_all() if item.category == category]

    def list_by_priority(self, priority: str) -> list[TodoReadItem]:
        """指定優先度の Todo のみを返す。"""
        return [item for item in self.list_all() if item.priority == priority]

    def get_events(self, aggregate_id: str) -> list[Event]:
        """指定 Aggregate のイベント履歴を返す（Event Sourcing の真価: 監査ログ）。"""
        return self._store.load_events(aggregate_id, from_version=0)

    def _build_state(self) -> dict[str, dict[str, Any]]:
        """全イベントを再生して、削除済みを除いた現在状態の辞書を組み立てる。"""
        items: dict[str, dict[str, Any]] = {}
        for event in self._store.load_all_events():
            if isinstance(event, TodoAdded):
                items[event.aggregate_id] = {
                    "id": event.aggregate_id,
                    "title": event.title,
                    "category": event.category,
                    "priority": event.priority,
                    "completed": False,
                    "created_at": event.occurred_at.isoformat(),
                    "updated_at": event.occurred_at.isoformat(),
                }
            elif isinstance(event, TodoCompleted):
                if event.aggregate_id in items:
                    items[event.aggregate_id]["completed"] = True
                    items[event.aggregate_id]["updated_at"] = event.occurred_at.isoformat()
            elif isinstance(event, TodoDeleted):
                items.pop(event.aggregate_id, None)
        return items
