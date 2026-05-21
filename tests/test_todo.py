"""TodoListクラスのテスト"""

import pytest
from src.todo import TodoList


@pytest.fixture
def todo_list() -> TodoList:
    return TodoList()


def test_add_item(todo_list: TodoList) -> None:
    """アイテムを追加できること"""
    item = todo_list.add("買い物をする")
    assert item.id == 1
    assert item.title == "買い物をする"
    assert item.done is False


def test_add_multiple_items_increments_id(todo_list: TodoList) -> None:
    """複数追加時にIDが連番になること"""
    item1 = todo_list.add("タスク1")
    item2 = todo_list.add("タスク2")
    assert item1.id == 1
    assert item2.id == 2


def test_list_all_empty(todo_list: TodoList) -> None:
    """空のリストは空のリストを返すこと"""
    assert todo_list.list_all() == []


def test_list_all_returns_all_items(todo_list: TodoList) -> None:
    """追加したアイテムが一覧に含まれること"""
    todo_list.add("タスクA")
    todo_list.add("タスクB")
    items = todo_list.list_all()
    assert len(items) == 2
    assert items[0].title == "タスクA"
    assert items[1].title == "タスクB"


def test_mark_done(todo_list: TodoList) -> None:
    """アイテムを完了状態にできること"""
    todo_list.add("完了テスト")
    result = todo_list.mark_done(1)
    assert result is not None
    assert result.done is True


def test_mark_done_not_found(todo_list: TodoList) -> None:
    """存在しないIDを完了にしようとするとNoneを返すこと"""
    result = todo_list.mark_done(999)
    assert result is None


def test_delete_item(todo_list: TodoList) -> None:
    """アイテムを削除できること"""
    todo_list.add("削除対象")
    result = todo_list.delete(1)
    assert result is True
    assert todo_list.list_all() == []


def test_delete_not_found(todo_list: TodoList) -> None:
    """存在しないIDを削除しようとするとFalseを返すこと"""
    result = todo_list.delete(999)
    assert result is False


def test_list_all_is_copy(todo_list: TodoList) -> None:
    """list_allの戻り値を変更しても内部状態に影響しないこと"""
    todo_list.add("タスク")
    items = todo_list.list_all()
    items.clear()
    assert len(todo_list.list_all()) == 1
