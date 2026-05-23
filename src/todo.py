"""Todoリストを管理するモジュール。

このモジュールは TodoItem データクラスと TodoList 管理クラスを提供する。
スレッドセーフな設計になっており、並行環境でも安全に使用できる。
"""

import threading
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum


class Priority(str, Enum):
    """優先度を表す列挙型。

    str を継承しているため、文字列との直接比較が可能。

    Attributes:
        HIGH: 高優先度（"高"）
        MEDIUM: 中優先度（"中"）
        LOW: 低優先度（"低"）

    Example:
        >>> Priority("高") == "高"
        True
        >>> Priority.MEDIUM
        <Priority.MEDIUM: '中'>
    """

    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


@dataclass(frozen=True)
class TodoItem:
    """Todoアイテムを表すイミュータブルなデータクラス。

    frozen=True により、インスタンス生成後の属性変更は FrozenInstanceError となる。
    変更が必要な場合は dataclasses.replace() を使って新しいインスタンスを生成する。

    Attributes:
        id (int): アイテムの一意な識別子。TodoList が 1 から順に採番する。
        title (str): タスクのタイトル。前後の空白は除去済みの状態で保存される。
        completed (bool): 完了フラグ。デフォルトは False（未完了）。
        created_at (datetime): アイテムの作成日時。
        updated_at (datetime): アイテムの最終更新日時。
        category (str): カテゴリ名。前後の空白は除去済みの状態で保存される。省略時は空文字。
        priority (Priority): 優先度。省略時は Priority.MEDIUM（"中"）。

    Example:
        >>> from datetime import datetime
        >>> item = TodoItem(id=1, title="買い物")
        >>> item.completed
        False
        >>> item.priority
        <Priority.MEDIUM: '中'>
        >>> item.completed = True  # FrozenInstanceError が発生する
        Traceback (most recent call last):
            ...
        dataclasses.FrozenInstanceError: cannot assign to field 'completed'
    """

    id: int
    title: str
    completed: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    category: str = ""
    priority: Priority = Priority.MEDIUM


class TodoList:
    """Todoリストを管理するクラス。

    スレッドセーフな実装になっており、複数スレッドから同時にアクセスしても
    データ整合性が保たれる。内部は dict で管理するため O(1) のアクセスが可能。

    Example:
        >>> tl = TodoList()
        >>> item = tl.add("買い物をする", category="プライベート", priority="高")
        >>> item.title
        '買い物をする'
        >>> item.category
        'プライベート'
        >>> item.priority
        <Priority.HIGH: '高'>
        >>> tl.mark_completed(item.id).completed
        True
    """

    def __init__(self) -> None:
        """TodoList を初期化する。アイテムは空の状態で始まる。"""
        self._items: dict[int, TodoItem] = {}  # O(1)アクセスのためdictで管理
        self._next_id: int = 1
        self._lock = threading.Lock()

    def add(self, title: str, category: str = "", priority: str = "中") -> TodoItem:
        """新しい TodoItem を追加する。

        title と category の前後空白は自動的に除去して保存する。
        空白除去後に title が空文字になる場合は ValueError を送出する。

        Args:
            title (str): タスクのタイトル。前後の空白は除去される。
                空文字・空白のみ・タブのみ・改行のみは不可。
            category (str): カテゴリ名。前後の空白は除去される。省略時は空文字。
            priority (str): 優先度。"高" / "中" / "低" のいずれかを指定する。
                省略時は "中"。

        Returns:
            TodoItem: 追加されたアイテム。id は 1 から始まり追加順に採番される。

        Raises:
            ValueError: title が空文字、または空白・タブ・改行のみの場合。
            ValueError: priority が "高" / "中" / "低" 以外の場合。

        Example:
            >>> tl = TodoList()
            >>> item = tl.add("買い物をする")
            >>> item.id
            1
            >>> item.title
            '買い物をする'
            >>> item.completed
            False
            >>> item.priority
            <Priority.MEDIUM: '中'>

            前後の空白は自動的に除去される：

            >>> item2 = tl.add("  タスク  ", category="  仕事  ")
            >>> item2.title
            'タスク'
            >>> item2.category
            '仕事'

            不正な入力は ValueError になる：

            >>> tl.add("")
            Traceback (most recent call last):
                ...
            ValueError: タイトルは空にできません
            >>> tl.add("   ")
            Traceback (most recent call last):
                ...
            ValueError: タイトルは空にできません
            >>> tl.add("タスク", priority="極高")
            Traceback (most recent call last):
                ...
            ValueError: 優先度は '高', '中', '低' のいずれかを指定してください: '極高'
        """
        title = title.strip() if title else ""
        if not title:
            raise ValueError("タイトルは空にできません")
        category = category.strip()
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
        """全 TodoItem の一覧を返す。

        戻り値は内部状態のコピーであり、変更しても TodoList の内容には影響しない。
        各 TodoItem 自体は frozen=True のイミュータブルなオブジェクトである。

        Returns:
            list[TodoItem]: 全アイテムのリスト。アイテムがない場合は空リスト。

        Example:
            >>> tl = TodoList()
            >>> tl.list_all()
            []
            >>> tl.add("タスクA")
            TodoItem(...)
            >>> tl.add("タスクB")
            TodoItem(...)
            >>> items = tl.list_all()
            >>> len(items)
            2
            >>> items[0].title
            'タスクA'

            戻り値を変更しても内部状態には影響しない：

            >>> items.clear()
            >>> len(tl.list_all())
            2
        """
        with self._lock:
            return list(self._items.values())

    def mark_completed(self, item_id: int) -> TodoItem | None:
        """指定 ID のアイテムを完了状態にする。

        - 指定 ID が存在しない場合は None を返す。
        - 既に完了済みの場合は、そのアイテムをそのまま返す（updated_at は変更されない）。
        - 未完了から完了に変更した場合は、completed=True かつ updated_at が現在時刻に更新された
          新しい TodoItem を返す。

        Args:
            item_id (int): 完了にするアイテムの ID。

        Returns:
            TodoItem | None: 完了状態のアイテム。指定 ID が存在しない場合は None。

        Example:
            >>> tl = TodoList()
            >>> tl.add("タスク")
            TodoItem(...)
            >>> result = tl.mark_completed(1)
            >>> result.completed
            True

            存在しない ID は None を返す：

            >>> tl.mark_completed(999) is None
            True

            既に完了済みのアイテムは updated_at が変化しない：

            >>> first = tl.mark_completed(1)
            >>> second = tl.mark_completed(1)
            >>> second.updated_at == first.updated_at
            True
        """
        with self._lock:
            item = self._items.get(item_id)
            if item is None or item.completed:
                return item
            updated = replace(item, completed=True, updated_at=datetime.now())
            self._items[item_id] = updated
            return updated

    def delete(self, item_id: int) -> bool:
        """指定 ID のアイテムを削除する。

        Args:
            item_id (int): 削除するアイテムの ID。

        Returns:
            bool: 削除に成功した場合は True、指定 ID が存在しなかった場合は False。

        Example:
            >>> tl = TodoList()
            >>> tl.add("削除対象")
            TodoItem(...)
            >>> tl.delete(1)
            True
            >>> tl.list_all()
            []

            存在しない ID は False を返す：

            >>> tl.delete(999)
            False
        """
        with self._lock:
            if item_id not in self._items:
                return False
            del self._items[item_id]
        return True

    def list_by_category(self, category: str) -> list[TodoItem]:
        """指定カテゴリのアイテム一覧を返す。

        戻り値は新規リストであり、変更しても TodoList の内部状態には影響しない。

        Args:
            category (str): 絞り込むカテゴリ名。

        Returns:
            list[TodoItem]: 指定カテゴリに一致するアイテムのリスト。
                一致するアイテムがない場合は空リスト。

        Example:
            >>> tl = TodoList()
            >>> tl.add("企画書を作成する", category="仕事")
            TodoItem(...)
            >>> tl.add("映画を観る", category="プライベート")
            TodoItem(...)
            >>> tl.add("報告書を提出する", category="仕事")
            TodoItem(...)
            >>> items = tl.list_by_category("仕事")
            >>> len(items)
            2

            存在しないカテゴリは空リストを返す：

            >>> tl.list_by_category("趣味")
            []

            戻り値を変更しても内部状態には影響しない：

            >>> items.clear()
            >>> len(tl.list_by_category("仕事"))
            2
        """
        with self._lock:
            return [item for item in self._items.values() if item.category == category]

    def list_by_priority(self, priority: str) -> list[TodoItem]:
        """指定優先度のアイテム一覧を返す。

        戻り値は新規リストであり、変更しても TodoList の内部状態には影響しない。

        Args:
            priority (str): 絞り込む優先度。"高" / "中" / "低" のいずれかを指定する。

        Returns:
            list[TodoItem]: 指定優先度に一致するアイテムのリスト。
                一致するアイテムがない場合は空リスト。

        Raises:
            ValueError: priority が "高" / "中" / "低" 以外の場合。

        Example:
            >>> tl = TodoList()
            >>> tl.add("緊急対応", priority="高")
            TodoItem(...)
            >>> tl.add("通常タスク", priority="中")
            TodoItem(...)
            >>> tl.add("重要会議の準備", priority="高")
            TodoItem(...)
            >>> items = tl.list_by_priority("高")
            >>> len(items)
            2

            存在しない優先度のアイテムがない場合は空リストを返す：

            >>> tl.list_by_priority("低")
            []

            不正な優先度は ValueError になる：

            >>> tl.list_by_priority("極高")
            Traceback (most recent call last):
                ...
            ValueError: 優先度は '高', '中', '低' のいずれかを指定してください: '極高'

            戻り値を変更しても内部状態には影響しない：

            >>> result = tl.list_by_priority("高")
            >>> result.clear()
            >>> len(tl.list_by_priority("高"))
            2
        """
        try:
            p = Priority(priority)
        except ValueError:
            raise ValueError(f"優先度は '高', '中', '低' のいずれかを指定してください: {priority!r}")
        with self._lock:
            return [item for item in self._items.values() if item.priority == p]

    def __str__(self) -> str:
        """TodoList の内容を人間が読みやすい文字列で返す。

        アイテムがない場合は "TodoList: (空)" を返す。
        各アイテムは完了マーク・カテゴリ・優先度・タイトルの順に表示される。

        Returns:
            str: TodoList の文字列表現。

        Example:
            >>> tl = TodoList()
            >>> str(tl)
            'TodoList: (空)'
            >>> tl.add("買い物", category="プライベート", priority="低")
            TodoItem(...)
            >>> print(str(tl))
            TodoList (1件):
              [ ] 1. [プライベート][低] 買い物
        """
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
