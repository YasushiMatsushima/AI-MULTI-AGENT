"""Aggregate: イベントをリプレイして現状を構築し、不変条件を保つ。

Event Sourcing では Aggregate の状態は「過去のイベントの集合」から導出される。
本モジュールでは TodoAggregate が単一の Todo アイテムを表す Aggregate である。
"""

from dataclasses import dataclass
from typing import Any

from src.cqrs.events import Event, TodoAdded, TodoCompleted, TodoDeleted


class AggregateError(Exception):
    """ビジネスルール違反（例: 存在しないアイテムを完了しようとした）。"""


@dataclass
class TodoAggregate:
    """単一の Todo を表す Aggregate。

    Attributes:
        aggregate_id: Aggregate ID。
        version: 適用済みイベント数。0 は未生成（イベントが一度も発行されていない）。
        title, category, priority, completed, deleted: 現在の状態。
    """

    aggregate_id: str
    version: int = 0
    title: str = ""
    category: str = ""
    priority: str = "中"
    completed: bool = False
    deleted: bool = False

    @classmethod
    def from_events(
        cls,
        aggregate_id: str,
        events: list[Event],
        snapshot: dict[str, Any] | None = None,
        snapshot_version: int = 0,
    ) -> "TodoAggregate":
        """スナップショットと差分イベントから Aggregate を組み立てる。

        Args:
            aggregate_id: 対象 Aggregate の ID。
            events: スナップショット以降のイベント（version 昇順）。
            snapshot: スナップショットの状態辞書。None なら最初から組み立て。
            snapshot_version: スナップショット時点の version。
        """
        if snapshot is not None:
            agg = cls(aggregate_id=aggregate_id, version=snapshot_version, **snapshot)
        else:
            agg = cls(aggregate_id=aggregate_id)
        for event in events:
            agg.apply(event)
        return agg

    def apply(self, event: Event) -> None:
        """イベントを適用して状態を更新する。

        Raises:
            AggregateError: 未知のイベントタイプが渡された場合（リプレイ時の壊れ検出）。
        """
        if isinstance(event, TodoAdded):
            self.title = event.title
            self.category = event.category
            self.priority = event.priority
        elif isinstance(event, TodoCompleted):
            self.completed = True
        elif isinstance(event, TodoDeleted):
            self.deleted = True
        else:
            raise AggregateError(
                f"apply: 未知のイベントタイプ {type(event).__name__!r}"
            )
        self.version = event.version

    def to_snapshot(self) -> dict[str, Any]:
        """スナップショットとして保存する状態辞書を返す。"""
        return {
            "title": self.title,
            "category": self.category,
            "priority": self.priority,
            "completed": self.completed,
            "deleted": self.deleted,
        }

    @property
    def exists(self) -> bool:
        """Aggregate が生成済み（TodoAdded が適用済み）であるか。"""
        return self.version > 0
