# マルチエージェントコース Todo API

Claude Code のマルチエージェント機能を学習する実習プロジェクト。
CQRS + Event Sourcing アーキテクチャで実装した Todo 管理 API。

## 技術スタック

- Python 3.12
- FastAPI
- パッケージ管理: uv
- テスト: pytest
- DB: SQLite（Event Store）

## セットアップ

```bash
uv sync
```

## 起動

```bash
uv run uvicorn src.main:app --reload
```

起動後、`http://localhost:8000/scalar` で API ドキュメント（Scalar UI）を確認できる。

## テスト実行

```bash
uv run pytest
```

## API エンドポイント

### Todo の作成

```
POST /todos
```

リクエストボディ:

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| title | string | 必須 | タイトル（空白のみは 400） |
| category | string | 任意 | カテゴリ（デフォルト: 空文字） |
| priority | string | 任意 | 優先度（デフォルト: `中`） |

`priority` の許容値: `高` / `中` / `低`（それ以外は 400）

レスポンス例（201）:

```json
{"id": "550e8400-e29b-41d4-a716-446655440000", "event_id": "...", "version": 1}
```

### Todo 一覧の取得

```
GET /todos
GET /todos?category=食料
GET /todos?priority=高
```

`priority` クエリに `高/中/低` 以外を指定すると 422。

### Todo の個別取得

```
GET /todos/{todo_id}
```

`todo_id` は UUID 形式必須（不正形式は 422、存在しない場合は 404）。

### Todo の完了

```
POST /todos/{todo_id}/complete
```

`todo_id` は UUID 形式必須（不正形式は 422）。存在しない・削除済み・完了済みの場合は 409。

### Todo の削除

```
DELETE /todos/{todo_id}
```

`todo_id` は UUID 形式必須（不正形式は 422）。存在しない・削除済みの場合は 409。論理削除。

### イベント履歴の取得

```
GET /todos/{todo_id}/events
```

Event Sourcing の監査ログ。`todo_id` は UUID 形式必須（不正形式は 422）。存在しない場合は 404。

## アーキテクチャ

CQRS（Command Query Responsibility Segregation）と Event Sourcing を採用。

```
コマンド側（書き込み）          クエリ側（読み取り）
POST/DELETE                    GET
    ↓                              ↓
CommandHandler             TodoReadModel
    ↓                              ↓
EventStore（SQLite）  ────→  イベントを再生して Read Model を構築
```

- **Event Store**: 追記専用（append-only）。`aggregate_id × version` で楽観ロック。
- **Aggregate**: イベントを再生してビジネスルールを適用。
- **Read Model**: 全イベントを再生して現在の状態を返す。スナップショット機能で高速化。

## ディレクトリ構成

```
src/
  main.py               # FastAPI エントリポイント
  cqrs/
    events.py           # ドメインイベント定義
    commands.py         # コマンド定義
    aggregates.py       # Todo Aggregate（ビジネスルール）
    command_handler.py  # コマンドハンドラ
    event_store.py      # SQLite ベース Event Store
    projections.py      # Read Model（クエリ側）
tests/
  test_cqrs_api.py      # FastAPI 結合テスト
  test_review_fixes.py  # レビュー指摘事項のテスト
docs/                   # 追加ドキュメント
```

## 環境変数

| 変数名 | デフォルト | 説明 |
|---|---|---|
| `TODO_DB_PATH` | `todos.db` | SQLite DB のパス。`:memory:` でインメモリ動作（テスト用）。 |
