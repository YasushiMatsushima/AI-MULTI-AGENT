# マルチエージェントコース Todo API

Claude Code のマルチエージェント機能を学習する実習プロジェクト。
FastAPI + SQLModel + SQLite で構築したシンプルな Todo 管理 REST API。

## 技術スタック

| 技術 | バージョン・詳細 |
|---|---|
| Python | 3.12 |
| Web フレームワーク | FastAPI |
| ORM | SQLModel |
| データベース | SQLite（開発環境） |
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

## エンドポイント一覧

| メソッド | パス | 説明 | 成功時ステータス |
|---|---|---|---|
| `GET` | `/todos` | Todo 一覧取得 | 200 |
| `POST` | `/todos` | Todo 新規作成 | 201 |
| `PUT` | `/todos/{id}` | Todo 更新 | 200 |
| `DELETE` | `/todos/{id}` | Todo 削除 | 200 |

> 詳細なリクエスト・レスポンス例は [docs/api-guide.md](docs/api-guide.md) を参照。

## テスト実行

```bash
uv run pytest -v
```

## プロジェクト構成

```
src/
  main.py         # FastAPI エントリポイント・エンドポイント定義
  models.py       # SQLModel データモデル（Todo）
  database.py     # SQLite データベース接続・初期化処理
tests/
  conftest.py     # テスト用フィクスチャ（テスト用 DB セットアップ等）
  test_api.py     # API 統合テスト（全エンドポイント 正常系・異常系）
docs/
  api-guide.md    # API 使用ガイド（curl 例・レスポンス例）
```
