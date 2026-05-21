# 開発環境メモ

## 構成

```
docker-python-backend/
├── app/
│   ├── __init__.py   # パッケージ化のためのファイル（中身は空でOK）
│   └── main.py       # FastAPI アプリ本体
├── Dockerfile
├── compose.yaml
├── requirements.txt
├── .dockerignore
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

# イメージ再ビルド（requirements.txt を変更したとき）
docker compose up --build -d
```

- アクセス先: http://localhost:8080
- Swagger UI: http://localhost:8080/docs
- `app/` をボリュームマウントしているので、コード編集は即反映（--reload）

## venv（ローカルの補完・型チェック用）

```bash
# 作成
python -m venv .venv

# 有効化（Linux/Mac）
source venv/bin/activate

# 有効化（Windows）
venv\Scripts\activate

# パッケージインストール
# # 1つだけインストール
# pip install fastapi
# ファイルに書かれた全パッケージを一括インストール
# pip install -r requirements.txt
pip install -r requirements.txt

pip install fastapi[all]
# freeze は「その時点でインストールされているパッケージとバージョンを一覧で出力する」コマンド
pip freeze > requirements.txt
#イメージ
# requirements.txt の中身：
#  fastapi==0.136.1
#  uvicorn==0.47.0
#  pydantic==2.13.4
#  ...

# pip install -r で1行ずつ読んで順番にインストール

# pip install fastapi==0.136.1
# pip install uvicorn==0.47.0
# pip install pydantic==2.13.4
# -r は --requirement の省略形

# 無効化
deactivate
```

> 実際の起動は Docker で行う。venv はVSCodeの補完を効かせるために使う。

## `__init__.py` について

ディレクトリに置くことで、そのディレクトリを Python パッケージとして認識させるファイル。
中身は空でOK。ルーターやモデルをディレクトリに分けるときに必要になる。

```
app/
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
