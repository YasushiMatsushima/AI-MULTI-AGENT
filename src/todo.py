"""Todoリストを管理するモジュール"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TodoItem:
    """Todoアイテムを表すデータクラス"""

    id: int # アイテムの一意なID
    title: str # アイテムのタイトル
    completed: bool = False # アイテムの完了状態（デフォルトはFalse）
    craeted_at: str = "" # アイテムの作成日時（オプション）
    updated_at: str = "" # アイテムの更新日時（オプション）


class TodoList:
    """Todoリストを管理するクラス"""

    def __init__(self) -> None:
        self._items: list[TodoItem] = []
        self._next_id: int = 1

    def add(self, title: str) -> TodoItem:
        """新しいTodoアイテムを追加する"""
        now = datetime.now().isoformat()
        item = TodoItem(id=self._next_id, title=title, craeted_at=now, updated_at=now)
        self._items.append(item)
        self._next_id += 1
        return item

    def list_all(self) -> list[TodoItem]:
        """全Todoアイテムの一覧を返す"""
        return list(self._items)

    def mark_completed(self, item_id: int) -> Optional[TodoItem]:
        """指定IDのアイテムを完了状態にする。見つからない場合はNoneを返す"""
        item = self._find(item_id)
        if item is not None:
            item.completed = True
            item.updated_at = datetime.now().isoformat()
        return item

    def delete(self, item_id: int) -> bool:
        """指定IDのアイテムを削除する。削除できた場合はTrueを返す"""
        item = self._find(item_id)
        if item is None:
            return False
        self._items.remove(item)
        return True

    def _find(self, item_id: int) -> Optional[TodoItem]:
        """IDでアイテムを検索する"""
        return next((i for i in self._items if i.id == item_id), None)
