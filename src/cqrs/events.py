"""ドメインイベントの定義。

全イベントは frozen=True のイミュータブルなデータクラスで、一度発行されたら変更できない。
Event Sourcing の原則「過去は変えられない」を型レベルで表現している。
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar


@dataclass(frozen=True, kw_only=True)
class Event:
    """全ドメインイベントの基底クラス。

    Attributes:
        aggregate_id: イベントが属する Aggregate の ID（UUID 文字列）。
        version: Aggregate 内でのイベント順序。1 から始まる単調増加。
        occurred_at: イベント発生時刻。
        event_id: イベント自体の一意な ID。
    """

    aggregate_id: str
    version: int
    occurred_at: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    event_type: ClassVar[str] = "Event"


@dataclass(frozen=True, kw_only=True)
class TodoAdded(Event):
    """Todo アイテムが追加されたイベント。"""

    title: str
    category: str = ""
    priority: str = "中"

    event_type: ClassVar[str] = "TodoAdded"


@dataclass(frozen=True, kw_only=True)
class TodoCompleted(Event):
    """Todo アイテムが完了状態になったイベント。"""

    event_type: ClassVar[str] = "TodoCompleted"


@dataclass(frozen=True, kw_only=True)
class TodoDeleted(Event):
    """Todo アイテムが削除されたイベント。"""

    event_type: ClassVar[str] = "TodoDeleted"


EVENT_TYPES: dict[str, type[Event]] = {
    "TodoAdded": TodoAdded,
    "TodoCompleted": TodoCompleted,
    "TodoDeleted": TodoDeleted,
}
