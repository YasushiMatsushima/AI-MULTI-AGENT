# TodoアプリWebアプリ拡張 統合調査レポート

> 作成日: 2026-05-26  
> 調査方法: tmux 3ペイン並列エージェント（チームメイト1〜3）

---

## エグゼクティブサマリー

| 項目 | 推奨 | 理由 |
|------|------|------|
| **Webフレームワーク** | FastAPI（現状維持） | 既存コードベース活用、Python 3.12最大活用、非同期I/O完全対応 |
| **開発DB** | SQLite + aiosqlite | ゼロセットアップ、WALモードで並列読み取り対応 |
| **本番DB** | PostgreSQL（Supabase無料枠） | 500MB無料、コネクションプーリング付属、7日自動バックアップ |
| **コンテナ化** | Docker（マルチステージビルド + uv） | イメージ最小化、再現性確保、非rootユーザー実行 |
| **デプロイ先** | Render（学習用）/ Fly.io（本番） | 難易度と制御性のバランス |
| **CI/CD** | GitHub Actions | テスト→デプロイを自動化、Renderはdeploy hook一発 |

---

## チームメイト1: Webフレームワーク調査結果

### フレームワーク比較

| 観点 | FastAPI | Flask | Django |
|------|---------|-------|--------|
| 学習コスト | 中（型ヒント前提） | 低 | 高（規約多数） |
| 非同期サポート | ネイティブASGI | 部分的 | 部分的 |
| APIドキュメント | 自動生成 | 別途必要 | DRFで対応可 |
| パフォーマンス | 高（~40K req/s） | 低（~8K req/s） | 中（~10K req/s） |
| Admin画面 | なし | なし | 自動生成 |

### パフォーマンス傾向
```
FastAPI (async)  ██████████████████░░  ~40,000 req/s
Django           ████████░░░░░░░░░░░░  ~10,000 req/s
Flask            ██████░░░░░░░░░░░░░░   ~8,000 req/s
```

### 推奨: **FastAPI（現状維持・強化）**
- 既存コードへの変更ゼロ
- Pydantic v2 + Python 3.12 型ヒントと完全統合
- 非同期DB操作（aiosqlite/asyncpg）が自然に実現
- `uv` の高速依存管理との相性が良い

---

## チームメイト2: データベース設計結果

### SQLite vs PostgreSQL 比較

| 観点 | SQLite | PostgreSQL |
|------|--------|------------|
| セットアップ | ファイル1つで即起動 | サーバープロセス必要 |
| スケーラビリティ | 数千RPS上限 | 水平・垂直スケール対応 |
| Python統合 | 標準ライブラリ付属 | psycopg2/asyncpg必要 |
| コスト | 無料 | Supabase無料枠500MB |

### 推奨スキーマ（SQLite/PostgreSQL共通）

```sql
-- Todoテーブル
CREATE TABLE todos (
    id          TEXT PRIMARY KEY,           -- UUID
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 200),
    description TEXT,
    status      TEXT NOT NULL DEFAULT 'todo'
                    CHECK(status IN ('todo', 'in_progress', 'done')),
    due_date    DATE,
    created_at  DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at  DATETIME NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_todos_user_id ON todos(user_id);
CREATE INDEX idx_todos_status   ON todos(status);
```

### SQLModelによるPython定義

```python
class TodoStatus(str, Enum):
    todo        = "todo"
    in_progress = "in_progress"
    done        = "done"

class Todo(SQLModel, table=True):
    id:          str           = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id:     str           = Field(foreign_key="users.id", index=True)
    title:       str           = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    status:      TodoStatus    = Field(default=TodoStatus.todo)
    due_date:    Optional[date] = None
    created_at:  datetime      = Field(default_factory=datetime.utcnow)
    updated_at:  datetime      = Field(default_factory=datetime.utcnow)
```

### 推奨: **開発=SQLite、本番=PostgreSQL（Supabase）**
- `DATABASE_URL` 1行変更で開発→本番を切り替え
- Alembicでスキーマ差異を吸収
- Supabase無料枠（500MB）でTodoアプリは数年運用可能

---

## チームメイト3: デプロイ戦略結果

### クラウドサービス比較

| 比較項目 | Render | Railway | Fly.io |
|---|---|---|---|
| 無料枠 | あり（15分スリープ） | $5クレジット/月 | あり（256MB VM×3） |
| 最安有料 | $7/月 | $5/月 | $1.94/月〜 |
| デプロイ難易度 | ★☆☆（最簡単） | ★☆☆ | ★★☆ |
| PostgreSQL | 無料枠90日のみ | クレジット内 | $1.94/月〜 |
| アジアリージョン | なし | あり | あり |
| CI/CD連携 | Deploy Hook一発 | 自動 | Actions設定必要 |

### 推奨Dockerfile（マルチステージ + uv）

```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim AS runner
WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app
COPY --from=builder /app/.venv /app/.venv
COPY src/ ./src/
USER app
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["gunicorn", "src.main:app", "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000"]
```

### GitHub Actions（Render向け）

```yaml
name: Deploy to Render
on:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv run pytest --tb=short
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - run: curl -X POST "${{ secrets.RENDER_DEPLOY_HOOK_URL }}"
```

### 推奨: **Render（学習用）→ Fly.io（本番）**

---

## 統合推奨アーキテクチャ

```
┌─────────────────────────────────────────────────┐
│                GitHub Repository                 │
│  push to main → GitHub Actions                  │
│    1. uv run pytest（テスト）                   │
│    2. Deploy Hook → Render/Fly.io               │
└──────────────────────┬──────────────────────────┘
                       │ 自動デプロイ
          ┌────────────▼────────────┐
          │   Render / Fly.io       │
          │  Docker コンテナ        │
          │  FastAPI + Uvicorn      │
          │  (Python 3.12 + uv)     │
          └────────────┬────────────┘
                       │ DATABASE_URL
          ┌────────────▼────────────┐
          │   Supabase PostgreSQL   │
          │   (無料枠 500MB)        │
          │   + PgBouncer pooling   │
          └─────────────────────────┘
```

## 実装ロードマップ

| フェーズ | 作業内容 | コマンド/ファイル |
|---------|----------|--------------|
| **1. DB移行** | SQLModel + Alembic追加 | `uv add sqlmodel alembic aiosqlite` |
| **2. スキーマ** | Todoモデル定義 | `src/models.py` |
| **3. マイグレ** | 初回マイグレーション | `uv run alembic init && uv run alembic revision --autogenerate` |
| **4. Docker** | Dockerfile作成 | 上記雛形を `Dockerfile` に配置 |
| **5. ローカル検証** | docker-compose起動 | `docker-compose up --build` |
| **6. Renderデプロイ** | GitHubリポジトリ連携 | Renderダッシュボードで設定 |
| **7. CI/CD** | GitHub Actions追加 | `.github/workflows/deploy.yml` |

## コスト見積もり（月額）

| 構成 | コスト |
|------|--------|
| Render無料 + Supabase無料 | **$0/月**（スリープあり） |
| Render有料 + Supabase無料 | **$7/月**（スリープなし） |
| Fly.io + Supabase無料 | **~$2-5/月**（アジアリージョン） |

---

*本レポートはtmux 3ペイン並列エージェント（チームメイト1〜3）による調査結果を統合したものです。*
