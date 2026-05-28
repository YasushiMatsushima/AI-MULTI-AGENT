# Todo API 使用ガイド

Todo REST API の各エンドポイントについて、リクエスト・レスポンス例を示す。

## ベース URL

```
http://localhost:8000
```

## データモデル

### Todo リソース（読み取り側）

`GET /todos` および `GET /todos/{id}` のレスポンスに含まれるフィールド。

| フィールド | 型 | 説明 |
|---|---|---|
| `id` | str（UUID） | 一意な識別子 |
| `title` | str | タイトル |
| `category` | str | カテゴリ（省略時は空文字） |
| `priority` | str | 優先度（`高` / `中` / `低`、デフォルト: `中`） |
| `completed` | bool | 完了フラグ |
| `created_at` | str（ISO 8601） | 作成日時 |
| `updated_at` | str（ISO 8601） | 最終更新日時 |

---

## POST /todos

新しい Todo を作成する（Command）。

### リクエスト

```bash
curl -X POST http://localhost:8000/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "買い物", "category": "食料", "priority": "高"}'
```

#### リクエストボディ

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `title` | str | 必須 | タイトル（空白のみは不可） |
| `category` | str | 任意 | カテゴリ（省略時は空文字） |
| `priority` | str | 任意 | 優先度（`高` / `中` / `低`、省略時は `中`） |

### レスポンス（201 Created）

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "event_id": "7a8b9c0d-e1f2-3a4b-5c6d-7e8f90a1b2c3",
  "version": 1
}
```

### 異常系

#### 空タイトルの場合（400 Bad Request）

```bash
curl -X POST http://localhost:8000/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "   "}'
```

```json
{
  "detail": "タイトルは空にできません"
}
```

#### 不正な priority の場合（400 Bad Request）

```bash
curl -X POST http://localhost:8000/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "A", "priority": "緊急"}'
```

```json
{
  "detail": "priority は '高/中/低' のいずれかを指定してください"
}
```

---

## GET /todos

Todo の一覧を取得する（Query）。`category` または `priority` でフィルタ可能。

### リクエスト（全件取得）

```bash
curl http://localhost:8000/todos
```

### レスポンス（200 OK）

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "買い物",
    "category": "食料",
    "priority": "高",
    "completed": false,
    "created_at": "2026-05-28T10:00:00",
    "updated_at": "2026-05-28T10:00:00"
  },
  {
    "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "title": "報告書を提出する",
    "category": "仕事",
    "priority": "中",
    "completed": true,
    "created_at": "2026-05-28T09:00:00",
    "updated_at": "2026-05-28T09:30:00"
  }
]
```

> Todo が 0 件の場合は空配列 `[]` を返す。

### カテゴリフィルタ

```bash
curl "http://localhost:8000/todos?category=食料"
```

### 優先度フィルタ

```bash
curl "http://localhost:8000/todos?priority=高"
```

> `priority` クエリパラメータに `高` / `中` / `低` 以外の値を指定すると `422 Unprocessable Entity` が返る。

---

## GET /todos/{id}

指定 ID の Todo を取得する（Query）。

### リクエスト

```bash
curl http://localhost:8000/todos/550e8400-e29b-41d4-a716-446655440000
```

### レスポンス（200 OK）

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "買い物",
  "category": "食料",
  "priority": "高",
  "completed": false,
  "created_at": "2026-05-28T10:00:00",
  "updated_at": "2026-05-28T10:00:00"
}
```

### 異常系（404 Not Found）

存在しない ID または削除済みの ID を指定した場合:

```json
{
  "detail": "Not Found"
}
```

---

## POST /todos/{id}/complete

指定 ID の Todo を完了状態にする（Command）。

### リクエスト

```bash
curl -X POST http://localhost:8000/todos/550e8400-e29b-41d4-a716-446655440000/complete
```

### レスポンス（200 OK）

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "event_id": "9f8e7d6c-5b4a-3210-fedc-ba9876543210",
  "version": 2
}
```

### 異常系（409 Conflict）

存在しない ID、または既に完了済みの Todo に対して complete を実行した場合:

```bash
curl -X POST http://localhost:8000/todos/00000000-0000-0000-0000-000000000000/complete
```

```json
{
  "detail": "..."
}
```

ステータスコード: **409**

---

## DELETE /todos/{id}

指定 ID の Todo を削除する（Command）。

### リクエスト

```bash
curl -X DELETE http://localhost:8000/todos/550e8400-e29b-41d4-a716-446655440000
```

### レスポンス（200 OK）

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "event_id": "1a2b3c4d-5e6f-7890-abcd-ef1234567890",
  "version": 2
}
```

### 異常系（409 Conflict）

存在しない ID を指定した場合:

```bash
curl -X DELETE http://localhost:8000/todos/00000000-0000-0000-0000-000000000000
```

```json
{
  "detail": "..."
}
```

ステータスコード: **409**

---

## GET /todos/{id}/events

指定 ID の Todo のイベント履歴を取得する（Event Sourcing の監査ログ機能）。

### リクエスト

```bash
curl http://localhost:8000/todos/550e8400-e29b-41d4-a716-446655440000/events
```

### レスポンス（200 OK）

```json
[
  {
    "event_id": "7a8b9c0d-e1f2-3a4b-5c6d-7e8f90a1b2c3",
    "event_type": "TodoAdded",
    "version": 1,
    "occurred_at": "2026-05-28T10:00:00",
    "payload": {
      "title": "買い物",
      "category": "食料",
      "priority": "高"
    }
  },
  {
    "event_id": "9f8e7d6c-5b4a-3210-fedc-ba9876543210",
    "event_type": "TodoCompleted",
    "version": 2,
    "occurred_at": "2026-05-28T10:30:00",
    "payload": {}
  }
]
```

### 異常系（404 Not Found）

存在しない ID または削除済みの ID でイベント履歴が空の場合:

```json
{
  "detail": "Not Found"
}
```

---

## エラーレスポンス一覧

| ステータスコード | 説明 | 発生するケース |
|---|---|---|
| `400 Bad Request` | リクエスト内容が不正 | 空タイトル、無効な priority 値 |
| `404 Not Found` | 指定した ID の Todo が存在しない | `GET /todos/{id}` や `GET /todos/{id}/events` で無効な ID を指定 |
| `409 Conflict` | 操作が許可されていない状態 | 存在しない ID への complete / delete、既に完了済みへの再 complete |
| `422 Unprocessable Entity` | クエリパラメータのバリデーションエラー | `priority` フィルタに `高/中/低` 以外の値を指定、パス変数が UUID 形式でない |
