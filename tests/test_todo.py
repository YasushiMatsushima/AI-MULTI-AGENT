"""TodoListクラスのテスト"""

import dataclasses

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
    assert item.completed is False


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
    result = todo_list.mark_completed(1)
    assert result is not None
    assert result.completed is True


def test_mark_done_not_found(todo_list: TodoList) -> None:
    """存在しないIDを完了にしようとするとNoneを返すこと"""
    result = todo_list.mark_completed(999)
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


def test_add_item_with_category(todo_list: TodoList) -> None:
    """カテゴリ付きでアイテムを追加できること"""
    item = todo_list.add("企画書を作成する", category="仕事")
    assert item.category == "仕事"


def test_add_item_default_category(todo_list: TodoList) -> None:
    """カテゴリ省略時は空文字になること"""
    item = todo_list.add("買い物をする")
    assert item.category == ""


def test_list_by_category(todo_list: TodoList) -> None:
    """指定カテゴリのアイテムのみ返ること"""
    todo_list.add("企画書を作成する", category="仕事")
    todo_list.add("映画を観る", category="プライベート")
    todo_list.add("報告書を提出する", category="仕事")
    items = todo_list.list_by_category("仕事")
    assert len(items) == 2
    assert all(item.category == "仕事" for item in items)


def test_list_by_category_no_match(todo_list: TodoList) -> None:
    """存在しないカテゴリは空リストを返すこと"""
    todo_list.add("タスク", category="仕事")
    result = todo_list.list_by_category("趣味")
    assert result == []


def test_add_item_with_priority(todo_list: TodoList) -> None:
    """優先度付きでアイテムを追加できること"""
    item = todo_list.add("緊急対応", priority="高")
    assert item.priority == "高"


def test_add_item_default_priority(todo_list: TodoList) -> None:
    """優先度省略時は「中」になること"""
    item = todo_list.add("通常タスク")
    assert item.priority == "中"


def test_list_by_priority(todo_list: TodoList) -> None:
    """指定優先度のアイテムのみ返ること"""
    todo_list.add("緊急対応", priority="高")
    todo_list.add("通常タスク", priority="中")
    todo_list.add("重要会議の準備", priority="高")
    items = todo_list.list_by_priority("高")
    assert len(items) == 2
    assert all(item.priority == "高" for item in items)


def test_list_by_priority_no_match(todo_list: TodoList) -> None:
    """存在しない優先度は空リストを返すこと"""
    todo_list.add("タスク", priority="高")
    result = todo_list.list_by_priority("低")
    assert result == []


def test_add_empty_title_raises(todo_list: TodoList) -> None:
    """空タイトルはValueErrorを送出すること"""
    with pytest.raises(ValueError, match="空にできません"):
        todo_list.add("")


def test_add_whitespace_title_raises(todo_list: TodoList) -> None:
    """空白のみのタイトルはValueErrorを送出すること"""
    with pytest.raises(ValueError, match="空にできません"):
        todo_list.add("   ")


def test_add_invalid_priority_raises(todo_list: TodoList) -> None:
    """不正な優先度はValueErrorを送出すること"""
    with pytest.raises(ValueError, match="優先度は"):
        todo_list.add("タスク", priority="極高")


def test_list_by_priority_invalid_raises(todo_list: TodoList) -> None:
    """不正な優先度でlist_by_priorityを呼ぶとValueErrorを送出すること"""
    with pytest.raises(ValueError, match="優先度は"):
        todo_list.list_by_priority("極高")


def test_mark_completed_already_done_no_update(todo_list: TodoList) -> None:
    """既に完了済みのアイテムはupdated_atが変更されないこと"""
    todo_list.add("タスク")
    first = todo_list.mark_completed(1)
    assert first is not None
    second = todo_list.mark_completed(1)
    assert second is not None
    assert second.updated_at == first.updated_at


def test_todo_item_is_immutable(todo_list: TodoList) -> None:
    """TodoItemはイミュータブルで直接変更できないこと"""
    item = todo_list.add("タスク")
    with pytest.raises(dataclasses.FrozenInstanceError):
        item.completed = True  # type: ignore[misc]


def test_list_all_items_are_immutable(todo_list: TodoList) -> None:
    """list_allで取得したアイテムを直接変更できないこと"""
    todo_list.add("タスク")
    items = todo_list.list_all()
    with pytest.raises(dataclasses.FrozenInstanceError):
        items[0].completed = True  # type: ignore[misc]
