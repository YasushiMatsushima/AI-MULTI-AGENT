# guidance.md — アプリ設計・環境構築・テスト実行ガイド

## アプリ設計

### 概要

Claude Code のマルチエージェント機能を学習する実習プロジェクト。
FastAPI をベースにした REST API サーバーと、Todoリスト管理機能を提供する。

### ディレクトリ構成

```
/workspace
├── src/
│   ├── __init__.py       # パッケージ定義
│   ├── main.py           # FastAPI アプリ本体（エンドポイント定義）
│   └── todo.py           # Todoリスト管理クラス（TodoItem / TodoList）
├── tests/
│   └── test_todo.py      # TodoList のユニットテスト
├── docs/
│   └── guidance.md       # 本ドキュメント
├── pyproject.toml        # プロジェクト設定・依存パッケージ定義
├── uv.lock               # 依存パッケージのロックファイル
└── .venv/                # 仮想環境（uv が自動生成）
```

### 主要モジュール

#### `src/main.py` — FastAPI エンドポイント

| メソッド | パス | 説明 |
|--------|------|------|
| GET | `/` | 疎通確認 |
| GET | `/health` | ヘルスチェック |
| GET | `/shipment` | 出荷情報のサンプルレスポンス |
| GET | `/scalar` | Scalar API ドキュメント UI |

#### `src/todo.py` — Todoリスト管理

- `TodoItem` — id / title / done を持つデータクラス
- `TodoList` — add / list_all / mark_done / delete メソッドを持つ管理クラス

### 依存パッケージ

| パッケージ | 用途 |
|-----------|------|
| fastapi | Web フレームワーク |
| uvicorn | ASGI サーバー |
| scalar-fastapi | API ドキュメント UI |
| python-dotenv | 環境変数の読み込み |
| pytest | テストフレームワーク |

---

## ローカル環境の立ち上げ

### 前提

- Python 3.12 以上
- [uv](https://docs.astral.sh/uv/) がインストール済みであること

### セットアップ

```bash
# 依存パッケージのインストール（.venv を自動生成）
uv sync
```

### 開発サーバーの起動

```bash
uv run uvicorn src.main:app --reload
```

起動後、以下の URL でアクセスできる。

| URL | 内容 |
|-----|------|
| http://localhost:8000/ | ルートエンドポイント |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/scalar | Scalar API ドキュメント |

### パッケージの追加

```bash
# pip install は使わず uv add を使う
uv add <パッケージ名>
```

---

## テストの実行

### 全テストを実行

```bash
uv run pytest
```

### 特定ファイルのみ実行

```bash
uv run pytest tests/test_todo.py
```

### 詳細出力（各テスト名を表示）

```bash
uv run pytest -v
```

### インポートの動作確認

```bash
uv run python -c "import src.main"
```

### テスト一覧（`tests/test_todo.py`）

| テスト名 | 内容 |
|---------|------|
| `test_add_item` | アイテムを追加できること |
| `test_add_multiple_items_increments_id` | IDが連番になること |
| `test_list_all_empty` | 空リストは空を返すこと |
| `test_list_all_returns_all_items` | 追加したアイテムが一覧に含まれること |
| `test_mark_done` | アイテムを完了状態にできること |
| `test_mark_done_not_found` | 存在しないIDはNoneを返すこと |
| `test_delete_item` | アイテムを削除できること |
| `test_delete_not_found` | 存在しないIDの削除はFalseを返すこと |
| `test_list_all_is_copy` | list_all の戻り値は内部状態のコピーであること |
