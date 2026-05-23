"""FastAPI アプリケーションのエントリポイント。

このモジュールは基本的なエンドポイントに加え、CQRS + Event Sourcing 版の
Todo API を提供する。Event Store はプロセス内で 1 インスタンス保持し、
コマンド側（書き込み）とクエリ側（読み取り）でこれを共有する。
"""

import os
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from scalar_fastapi import get_scalar_api_reference

from src.cqrs.aggregates import AggregateError
from src.cqrs.command_handler import CommandHandler
from src.cqrs.commands import (
    AddTodoCommand,
    CompleteTodoCommand,
    DeleteTodoCommand,
)
from src.cqrs.event_store import EventStore
from src.cqrs.projections import TodoReadModel

app = FastAPI()


@app.get("/shipment")
def get_shipment():
    """配送状況を返すサンプルエンドポイント。"""
    return {
        "Content": "wooden table",
        "status": "in transit",
    }


@app.get("/")
def read_root():
    """ルートエンドポイント。"""
    return {"message": "Hello, FastAPI!"}


@app.get("/health")
def health_check():
    """ヘルスチェック用エンドポイント。"""
    return {"status": "ok"}


@app.get("/scalar", include_in_schema=False)
def get_scalar_docs():
    """Scalar UI 形式の API ドキュメント。"""
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title="Scalar API",
    )


# ----- CQRS + Event Sourcing 用の依存セットアップ -----
# 環境変数 TODO_DB_PATH で DB パスを上書き可能（テスト時に :memory: などを指定する想定）。
_DB_PATH = os.getenv("TODO_DB_PATH", "todos.db")
_event_store = EventStore(_DB_PATH)
_command_handler = CommandHandler(_event_store)
_read_model = TodoReadModel(_event_store)


class AddTodoRequest(BaseModel):
    """POST /todos のリクエストボディ。"""

    title: str
    category: str = ""
    priority: str = "中"


@app.post("/todos", status_code=201)
def create_todo(req: AddTodoRequest):
    """新規 Todo を作成する（Command 側）。"""
    aggregate_id = str(uuid.uuid4())
    try:
        event = _command_handler.handle_add(
            AddTodoCommand(
                aggregate_id=aggregate_id,
                title=req.title,
                category=req.category,
                priority=req.priority,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": aggregate_id, "event_id": event.event_id, "version": event.version}


@app.post("/todos/{todo_id}/complete")
def complete_todo(todo_id: str):
    """Todo を完了状態にする（Command 側）。"""
    try:
        event = _command_handler.handle_complete(
            CompleteTodoCommand(aggregate_id=todo_id)
        )
    except AggregateError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"id": todo_id, "event_id": event.event_id, "version": event.version}


@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: str):
    """Todo を削除する（Command 側、論理削除イベントを発行）。"""
    try:
        event = _command_handler.handle_delete(DeleteTodoCommand(aggregate_id=todo_id))
    except AggregateError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"id": todo_id, "event_id": event.event_id, "version": event.version}


@app.get("/todos")
def list_todos(category: str | None = None, priority: str | None = None):
    """Todo 一覧を取得する（Query 側）。category / priority でフィルタ可能。"""
    if category is not None:
        items = _read_model.list_by_category(category)
    elif priority is not None:
        items = _read_model.list_by_priority(priority)
    else:
        items = _read_model.list_all()
    return [item.__dict__ for item in items]


@app.get("/todos/{todo_id}")
def get_todo(todo_id: str):
    """指定 ID の Todo を取得する（Query 側）。"""
    item = _read_model.get(todo_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Not Found")
    return item.__dict__


@app.get("/todos/{todo_id}/events")
def get_todo_events(todo_id: str):
    """指定 Todo のイベント履歴を返す（Event Sourcing の監査ログ機能）。"""
    events = _read_model.get_events(todo_id)
    if not events:
        raise HTTPException(status_code=404, detail="Not Found")
    return [
        {
            "event_id": e.event_id,
            "event_type": type(e).event_type,
            "version": e.version,
            "occurred_at": e.occurred_at.isoformat(),
            "payload": {
                k: v
                for k, v in e.__dict__.items()
                if k not in {"aggregate_id", "version", "occurred_at", "event_id"}
            },
        }
        for e in events
    ]
