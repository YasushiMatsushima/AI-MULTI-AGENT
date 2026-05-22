# 開発環境メモ

## 構成

```
/
├── src/
│   ├── __init__.py   # パッケージ化のためのファイル（中身は空でOK）
│   ├── main.py       # FastAPI アプリ本体
│   └── todo.py       # TodoItem / TodoList クラス
├── tests/
│   └── test_todo.py  # テストコード
├── docs/             # ドキュメント
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml    # 依存パッケージ定義（uv 管理）
├── uv.lock
└── .gitignore
```

## Docker で起動する

```bash
# 起動（バックグラウンド）
docker compose up -d

# 停止
docker compose down

# ログ確認
docker compose logs -f

# イメージ再ビルド（依存パッケージを変更したとき）
docker compose up --build -d
```

- アクセス先: http://localhost:8080
- Swagger UI: http://localhost:8080/docs
- `src/` をボリュームマウントしているので、コード編集は即反映（--reload）

## uv（ローカル開発・補完・テスト用）

パッケージ管理には `pip` ではなく `uv` を使う。

```bash
# 依存パッケージのインストール（初回 or uv.lock 変更後）
uv sync

# パッケージを追加する
uv add fastapi

# スクリプト実行
uv run python src/main.py

# テスト実行
uv run pytest
```

> `pip install` は使用しない。依存関係は `pyproject.toml` と `uv.lock` で管理する。

## `__init__.py` について

ディレクトリに置くことで、そのディレクトリを Python パッケージとして認識させるファイル。
中身は空でOK。ルーターやモデルをディレクトリに分けるときに必要になる。

```
src/
├── __init__.py
├── main.py
├── routers/
│   ├── __init__.py
│   └── users.py
└── models/
    ├── __init__.py
    └── user.py
```

## GitHub

- リポジトリ: https://github.com/YasushiMatsushima/AI-MULTI-AGENT
- mainブランチで管理
