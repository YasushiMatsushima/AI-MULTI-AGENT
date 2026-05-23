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

- `Priority` — 優先度を表す列挙型（"高" / "中" / "低"）
- `TodoItem` — id / title / completed / created_at / updated_at / category / priority を持つイミュータブルなデータクラス
- `TodoList` — add / list_all / mark_completed / delete / list_by_category / list_by_priority メソッドを持つスレッドセーフな管理クラス

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
| `test_add_item_with_category` | カテゴリ付きでアイテムを追加できること |
| `test_add_item_default_category` | カテゴリ省略時は空文字になること |
| `test_list_by_category` | 指定カテゴリのアイテムのみ返ること |
| `test_list_by_category_no_match` | 存在しないカテゴリは空リストを返すこと |
| `test_add_item_with_priority` | 優先度付きでアイテムを追加できること |
| `test_add_item_default_priority` | 優先度省略時は「中」になること |
| `test_list_by_priority` | 指定優先度のアイテムのみ返ること |
| `test_list_by_priority_no_match` | 存在しない優先度のアイテムがない場合は空リストを返すこと |
| `test_add_empty_title_raises` | 空タイトルはValueErrorを送出すること |
| `test_add_whitespace_title_raises` | 空白のみのタイトルはValueErrorを送出すること |
| `test_add_invalid_priority_raises` | 不正な優先度はValueErrorを送出すること |
| `test_list_by_priority_invalid_raises` | 不正な優先度でlist_by_priorityを呼ぶとValueErrorを送出すること |
| `test_mark_completed_already_done_no_update` | 既に完了済みのアイテムはupdated_atが変更されないこと |
| `test_todo_item_is_immutable` | TodoItemはイミュータブルで直接変更できないこと |
| `test_list_all_items_are_immutable` | list_allで取得したアイテムを直接変更できないこと |
| `test_add_title_with_surrounding_spaces_is_stripped` | title の前後空白が strip されて保存されること |
| `test_add_category_with_surrounding_spaces_is_stripped` | category の前後空白が strip されて保存されること |
| `test_add_title_and_category_both_stripped` | title と category の両方が同時に strip されること |
| `test_add_blank_title_raises_value_error` | 空白・タブ・改行のみの title は ValueError になること（パラメータ化） |
| `test_mark_completed_with_unknown_id_returns_none` | 存在しない ID を指定すると None を返すこと |
| `test_mark_completed_transitions_to_done` | 未完了アイテムを完了にすると completed=True かつ updated_at が更新されること |
| `test_mark_completed_already_done_returns_same_item` | 既に完了済みのアイテムをもう一度完了にすると同じ TodoItem がそのまま返ること |
| `test_list_by_category_returns_new_list` | list_by_category の戻り値を変更しても内部状態に影響しないこと |
| `test_list_by_priority_returns_new_list` | list_by_priority の戻り値を変更しても内部状態に影響しないこと |
