"""FastAPI エンドポイントの結合テスト。

各テストごとに新しい EventStore に差し替えてテスト間の分離を保つ。
"""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """テストごとに一時 DB ファイルを使う FastAPI クライアントを返す。"""
    # 一時ファイルパスを環境変数で渡して、main 内の EventStore がそれを使う
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    os.environ["TODO_DB_PATH"] = tmp.name

    # 既に import 済みのモジュールを差し替えるためリロード
    import importlib

    import src.main

    importlib.reload(src.main)
    with TestClient(src.main.app) as c:
        yield c

    # クリーンアップ
    src.main._event_store.close()
    os.unlink(tmp.name)
    os.environ.pop("TODO_DB_PATH", None)


def test_create_todo_returns_201_with_id(client) -> None:
    """POST /todos は 201 と id/version を返す。"""
    resp = client.post("/todos", json={"title": "買い物", "category": "食料", "priority": "高"})
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["version"] == 1


def test_create_todo_with_blank_title_returns_400(client) -> None:
    """空タイトルは 400 BadRequest。"""
    resp = client.post("/todos", json={"title": "   "})
    assert resp.status_code == 400
    assert "タイトルは空にできません" in resp.json()["detail"]


def test_create_todo_with_invalid_priority_returns_400(client) -> None:
    """不正 priority は 400 BadRequest。"""
    resp = client.post("/todos", json={"title": "A", "priority": "緊急"})
    assert resp.status_code == 400


def test_list_todos_returns_added(client) -> None:
    """作成した Todo が GET /todos で取得できる。"""
    client.post("/todos", json={"title": "A"})
    client.post("/todos", json={"title": "B"})
    resp = client.get("/todos")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    assert {i["title"] for i in items} == {"A", "B"}


def test_get_todo_by_id(client) -> None:
    """GET /todos/{id} で個別取得できる。"""
    created = client.post("/todos", json={"title": "A"}).json()
    resp = client.get(f"/todos/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "A"


def test_get_unknown_todo_returns_404(client) -> None:
    """存在しない ID は 404。"""
    resp = client.get("/todos/non-existent-id")
    assert resp.status_code == 404


def test_complete_todo_changes_state(client) -> None:
    """POST /todos/{id}/complete で completed=True になる。"""
    created = client.post("/todos", json={"title": "A"}).json()
    resp = client.post(f"/todos/{created['id']}/complete")
    assert resp.status_code == 200

    got = client.get(f"/todos/{created['id']}").json()
    assert got["completed"] is True


def test_complete_unknown_id_returns_409(client) -> None:
    """存在しない ID への complete は 409 Conflict。"""
    resp = client.post("/todos/non-existent-id/complete")
    assert resp.status_code == 409


def test_complete_already_completed_returns_409(client) -> None:
    """既に完了済みへの再 complete は 409 Conflict。"""
    created = client.post("/todos", json={"title": "A"}).json()
    client.post(f"/todos/{created['id']}/complete")
    resp = client.post(f"/todos/{created['id']}/complete")
    assert resp.status_code == 409


def test_delete_todo_removes_from_list(client) -> None:
    """DELETE /todos/{id} 後は list_all から消える。"""
    created = client.post("/todos", json={"title": "A"}).json()
    resp = client.delete(f"/todos/{created['id']}")
    assert resp.status_code == 200

    items = client.get("/todos").json()
    assert items == []


def test_list_todos_filter_by_category(client) -> None:
    """?category= でフィルタできる。"""
    client.post("/todos", json={"title": "A", "category": "食料"})
    client.post("/todos", json={"title": "B", "category": "仕事"})
    resp = client.get("/todos", params={"category": "食料"})
    items = resp.json()
    assert len(items) == 1
    assert items[0]["title"] == "A"


def test_list_todos_filter_by_priority(client) -> None:
    """?priority= でフィルタできる。"""
    client.post("/todos", json={"title": "A", "priority": "高"})
    client.post("/todos", json={"title": "B", "priority": "低"})
    resp = client.get("/todos", params={"priority": "高"})
    items = resp.json()
    assert len(items) == 1
    assert items[0]["title"] == "A"


def test_get_todo_events_returns_full_history(client) -> None:
    """GET /todos/{id}/events でイベント履歴が取得できる（Event Sourcing の特徴）。"""
    created = client.post("/todos", json={"title": "A"}).json()
    client.post(f"/todos/{created['id']}/complete")
    resp = client.get(f"/todos/{created['id']}/events")
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) == 2
    assert events[0]["event_type"] == "TodoAdded"
    assert events[0]["version"] == 1
    assert events[1]["event_type"] == "TodoCompleted"
    assert events[1]["version"] == 2


def test_get_events_unknown_id_returns_404(client) -> None:
    """存在しない ID の events は 404。"""
    resp = client.get("/todos/non-existent/events")
    assert resp.status_code == 404


def test_events_persist_across_reload(client) -> None:
    """イベントは DB に永続化されているので、Read Model 経由でも再現できる。"""
    created = client.post("/todos", json={"title": "永続化テスト", "priority": "高"}).json()
    client.post(f"/todos/{created['id']}/complete")

    # 同じ DB を使う Read Model を直接作って読めることを確認
    from src.cqrs.event_store import EventStore
    from src.cqrs.projections import TodoReadModel

    db_path = os.environ["TODO_DB_PATH"]
    fresh_store = EventStore(db_path)
    fresh_rm = TodoReadModel(fresh_store)
    item = fresh_rm.get(created["id"])
    assert item is not None
    assert item.title == "永続化テスト"
    assert item.completed is True
    fresh_store.close()
