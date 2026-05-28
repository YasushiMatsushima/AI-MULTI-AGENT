# マルチエージェントコース Todo API

Claude Code のマルチエージェント機能を学習する実習プロジェクト。
FastAPI + CQRS + Event Sourcing で構築したシンプルな Todo 管理 REST API。

## 技術スタック

| 技術 | バージョン・詳細 |
|---|---|
| Python | 3.12 |
| Web フレームワーク | FastAPI |
| アーキテクチャ | CQRS + Event Sourcing |
| イベントストア | SQLite（開発環境） |
| パッケージ管理 | uv |
| テスト | pytest / httpx |

## セットアップ

```bash
# 依存パッケージのインストール
uv sync
```

## 起動

```bash
uv run uvicorn src.main:app --reload
```

起動後、以下の URL で確認できる。

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Scalar UI**: http://localhost:8000/scalar

## エンドポイント一覧

| メソッド | パス | 説明 | 成功時ステータス |
|---|---|---|---|
| `POST` | `/todos` | Todo 新規作成 | 201 |
| `GET` | `/todos` | Todo 一覧取得（`category` / `priority` フィルタ対応） | 200 |
| `GET` | `/todos/{id}` | 指定 ID の Todo 取得 | 200 |
| `POST` | `/todos/{id}/complete` | Todo を完了状態にする | 200 |
| `DELETE` | `/todos/{id}` | Todo を削除する | 200 |
| `GET` | `/todos/{id}/events` | Todo のイベント履歴を取得 | 200 |

> 詳細なリクエスト・レスポンス例は [docs/api-guide.md](docs/api-guide.md) を参照。

## テスト実行

```bash
uv run pytest -v
```

## プロジェクト構成

```
src/
  main.py               # FastAPI エントリポイント・エンドポイント定義
  cqrs/
    commands.py         # コマンド定義（AddTodoCommand など）
    command_handler.py  # コマンドハンドラー（書き込み側）
    events.py           # ドメインイベント定義（TodoAdded など）
    event_store.py      # SQLite 永続化・イベントストア
    projections.py      # Read Model（イベント再生でビューを構築）
    aggregates.py       # Aggregate ロジック（バリデーション・状態管理）
tests/
  test_cqrs_api.py          # API 統合テスト（全エンドポイント 正常系・異常系）
  test_cqrs_event_store.py  # EventStore 単体テスト
  test_cqrs_command_handler.py  # CommandHandler 単体テスト
  test_cqrs_projections.py  # Read Model 単体テスト
docs/
  api-guide.md          # API 使用ガイド（curl 例・レスポンス例）
```

## アーキテクチャ概要

本プロジェクトは **CQRS（Command Query Responsibility Segregation）** と **Event Sourcing** パターンを採用している。

- **Command 側（書き込み）**: `POST /todos`, `POST /todos/{id}/complete`, `DELETE /todos/{id}` はコマンドを発行し、イベントを Event Store に永続化する。
- **Query 側（読み取り）**: `GET /todos`, `GET /todos/{id}` は Event Store のイベントを全件再生して現在状態を組み立てて返す。
- **イベント履歴**: `GET /todos/{id}/events` で Todo ごとの変更履歴を取得できる（監査ログ）。
