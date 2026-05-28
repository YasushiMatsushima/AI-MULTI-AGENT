# Todo API 使用ガイド

Todo REST API の各エンドポイントについて、リクエスト・レスポンス例を示す。

## ベース URL

```
http://localhost:8000
```

## データモデル

Todo リソースは以下のフィールドを持つ。

| フィールド | 型 | 説明 |
|---|---|---|
| `id` | int | 自動採番される一意な識別子 |
| `title` | str | タイトル（必須） |
| `description` | str \| null | 説明（省略可、デフォルト: null） |
| `completed` | bool | 完了フラグ（デフォルト: false） |

---

## GET /todos

Todo の一覧を取得する。

### リクエスト

```bash
curl http://localhost:8000/todos
```

### レスポンス（200 OK）

```json
[
  {
    "id": 1,
    "title": "買い物",
    "description": "牛乳と卵を買う",
    "completed": false
  },
  {
    "id": 2,
    "title": "報告書を提出する",
    "description": null,
    "completed": true
  }
]
```

> Todo が 0 件の場合は空配列 `[]` を返す。

---

## POST /todos

新しい Todo を作成する。

### リクエスト

```bash
curl -X POST http://localhost:8000/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "買い物", "description": "牛乳を買う"}'
```

#### リクエストボディ

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `title` | str | 必須 | タイトル |
| `description` | str | 任意 | 説明（省略時は null） |
| `completed` | bool | 任意 | 完了フラグ（省略時は false） |

### レスポンス（201 Created）

```json
{
  "id": 1,
  "title": "買い物",
  "description": "牛乳を買う",
  "completed": false
}
```

### 異常系

説明フィールドを省略した場合:

```bash
curl -X POST http://localhost:8000/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "シンプルなタスク"}'
```

```json
{
  "id": 2,
  "title": "シンプルなタスク",
  "description": null,
  "completed": false
}
```

---

## PUT /todos/{id}

指定 ID の Todo を更新する。

### リクエスト

```bash
curl -X PUT http://localhost:8000/todos/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "買い物（更新済み）", "description": "牛乳・卵・パンを買う", "completed": true}'
```

#### リクエストボディ

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `title` | str | 必須 | 更新後のタイトル |
| `description` | str | 任意 | 更新後の説明 |
| `completed` | bool | 任意 | 更新後の完了フラグ |

### レスポンス（200 OK）

```json
{
  "id": 1,
  "title": "買い物（更新済み）",
  "description": "牛乳・卵・パンを買う",
  "completed": true
}
```

### 異常系（404 Not Found）

存在しない ID を指定した場合:

```bash
curl -X PUT http://localhost:8000/todos/999 \
  -H "Content-Type: application/json" \
  -d '{"title": "存在しない"}'
```

```json
{
  "detail": "Not Found"
}
```

ステータスコード: **404**

---

## DELETE /todos/{id}

指定 ID の Todo を削除する。

### リクエスト

```bash
curl -X DELETE http://localhost:8000/todos/1
```

### レスポンス（200 OK）

```json
{
  "ok": true
}
```

### 異常系（404 Not Found）

存在しない ID を指定した場合:

```bash
curl -X DELETE http://localhost:8000/todos/999
```

```json
{
  "detail": "Not Found"
}
```

ステータスコード: **404**

---

## エラーレスポンス一覧

| ステータスコード | 説明 | 発生するケース |
|---|---|---|
| `404 Not Found` | 指定した ID の Todo が存在しない | PUT / DELETE で無効な ID を指定 |
| `422 Unprocessable Entity` | リクエストボディのバリデーションエラー | 必須フィールド欠落、型不一致など |
