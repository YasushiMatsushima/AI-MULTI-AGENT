"""Todoリストを管理するモジュール"""

import threading
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum


class Priority(str, Enum):
    """優先度を表す列挙型（str継承により文字列比較が可能）"""

    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


@dataclass(frozen=True)
class TodoItem:
    """Todoアイテムを表すイミュータブルなデータクラス"""

    id: int
    title: str
    completed: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    category: str = ""
    priority: Priority = Priority.MEDIUM


class TodoList:
    """Todoリストを管理するクラス（スレッドセーフ）"""

    def __init__(self) -> None:
        self._items: dict[int, TodoItem] = {}  # O(1)アクセスのためdictで管理
        self._next_id: int = 1
        self._lock = threading.Lock()

    def add(self, title: str, category: str = "", priority: str = "中") -> TodoItem:
        """新しいTodoアイテムを追加する"""
        if not title or not title.strip():
            raise ValueError("タイトルは空にできません")
        try:
            p = Priority(priority)
        except ValueError:
            raise ValueError(f"優先度は '高', '中', '低' のいずれかを指定してください: {priority!r}")
        with self._lock:
            now = datetime.now()
            item = TodoItem(
                id=self._next_id,
                title=title,
                created_at=now,
                updated_at=now,
                category=category,
                priority=p,
            )
            self._items[self._next_id] = item
            self._next_id += 1
        return item

    def list_all(self) -> list[TodoItem]:
        """全Todoアイテムの一覧を返す"""
        with self._lock:
            return list(self._items.values())

    def mark_completed(self, item_id: int) -> TodoItem | None:
        """指定IDのアイテムを完了状態にする。見つからない場合はNoneを返す。既に完了済みの場合は変更しない"""
        with self._lock:
            item = self._items.get(item_id)
            if item is None or item.completed:
                return item
            updated = replace(item, completed=True, updated_at=datetime.now())
            self._items[item_id] = updated
            return updated

    def delete(self, item_id: int) -> bool:
        """指定IDのアイテムを削除する。削除できた場合はTrueを返す"""
        with self._lock:
            if item_id not in self._items:
                return False
            del self._items[item_id]
        return True

    def list_by_category(self, category: str) -> list[TodoItem]:
        """指定カテゴリのアイテムを返す"""
        with self._lock:
            return [item for item in self._items.values() if item.category == category]

    def list_by_priority(self, priority: str) -> list[TodoItem]:
        """指定優先度のアイテムを返す"""
        try:
            p = Priority(priority)
        except ValueError:
            raise ValueError(f"優先度は '高', '中', '低' のいずれかを指定してください: {priority!r}")
        with self._lock:
            return [item for item in self._items.values() if item.priority == p]

    def __str__(self) -> str:
        """TodoListの中身を文字列で返す"""
        with self._lock:
            items = list(self._items.values())
        if not items:
            return "TodoList: (空)"
        lines = [f"TodoList ({len(items)}件):"]
        for item in items:
            mark = "[✓]" if item.completed else "[ ]"
            category = f"[{item.category}]" if item.category else ""
            priority = f"[{item.priority.value}]"
            lines.append(f"  {mark} {item.id}. {category}{priority} {item.title}")
        return "\n".join(lines)
