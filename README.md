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

## 設計上の堅牢化（コードレビュー反映）

コードレビューで指摘された以下の修正が取り込まれています。

- **未知イベントの例外化**: `TodoAggregate.apply()` は既知の 3 種以外のイベントを受け取ると `AggregateError` を送出する。`EventStore._deserialize()` は `EVENT_TYPES` に登録されていない `event_type` を読み込むと `UnknownEventTypeError` を送出する。どちらもリプレイ時のデータ破損を即座に検出するための仕組み。
- **ペイロードインジェクション対策**: `EventStore._deserialize()` は payload をイベントクラスの固有フィールド集合でフィルタする。`aggregate_id` / `version` 等の共通フィールドは payload の値を無視し、DB カラムの値を使用する。
- **WAL モード**: ファイルパスを指定して `EventStore` を初期化すると `PRAGMA journal_mode=WAL` が有効になり、並行読み書き性能と耐障害性が向上する（`:memory:` は対象外）。
- **DB 接続の確実なクローズ**: FastAPI の `lifespan` コンテキストマネージャの `finally` 節で `_event_store.close()` を呼び出す。アプリシャットダウン時に接続が確実に解放される。
- **スナップショット時の二重ロード排除**: `CommandHandler._maybe_snapshot()` は引数で受け取った `agg` と `event` から最新状態を組み立てるため、Event Store への追加ロードが発生しない。

これらの堅牢化は `tests/test_review_fixes.py` の 11 件のテスト（`test_apply_unknown_event_raises_aggregate_error`、`test_maybe_snapshot_no_double_load_at_interval`、`test_deserialize_filters_unknown_payload_keys`、`test_event_store_enables_wal_mode_for_file_db`、`test_lifespan_closes_event_store_on_shutdown` ほか）によって仕様が保証されている。

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
