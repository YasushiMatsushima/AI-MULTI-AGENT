FastAPI + Docker のクラウドデプロイ戦略をまとめます。

---

# FastAPI + Docker クラウドデプロイ戦略

## 1. クラウドサービス比較表

| 比較項目 | Render | Railway | Fly.io |
|---|---|---|---|
| **無料枠** | あり（15分非活動でスリープ） | $5クレジット/月 | あり（256MB VM×3台） |
| **無料枠の制限** | スリープあり、月750時間 | クレジット消費後は有料 | メモリ制限、低速ディスク |
| **有料最安値** | $7/月（スリープなし） | $5/月（Hobbyプラン） | $1.94/月〜（従量課金） |
| **デプロイ難易度** | ★☆☆（最も簡単） | ★☆☆（簡単） | ★★☆（CLIが必要） |
| **初心者向け** | 最適 | 適している | やや上級者向け |
| **Docker対応** | ✅ Dockerfile直接対応 | ✅ Dockerfile対応 | ✅ ネイティブ対応 |
| **GitHub連携** | ✅ 自動デプロイ | ✅ 自動デプロイ | ✅ GitHub Actions推奨 |
| **PostgreSQL** | ✅ 無料枠は90日のみ | ✅ 従量課金 | ✅ Fly Postgres |
| **PG無料枠** | 90日後 $7/月 | クレジット内で使用 | なし（最低$1.94/月） |
| **カスタムドメイン** | ✅ 無料SSL付き | ✅ 無料SSL付き | ✅ 無料SSL付き |
| **CI/CD連携** | GitHub連携で自動 | GitHub連携で自動 | Actions設定が必要 |
| **リージョン** | 米国・欧州 | 米国・欧州・アジア | 世界30+リージョン |
| **コールドスタート** | あり（無料枠） | なし | なし |

---

## 2. FastAPI 最小 Dockerfile

```dockerfile
# ---- ビルドステージ ----
FROM python:3.12-slim AS builder

WORKDIR /app

# uvをインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 依存関係ファイルをコピー
COPY pyproject.toml uv.lock ./

# 依存関係のみインストール（開発依存除く）
RUN uv sync --frozen --no-dev --no-install-project

# ---- 実行ステージ ----
FROM python:3.12-slim AS runner

WORKDIR /app

# 非rootユーザーを作成
RUN addgroup --system app && adduser --system --ingroup app app

# ビルドステージから仮想環境をコピー
COPY --from=builder /app/.venv /app/.venv

# アプリケーションコードをコピー
COPY src/ ./src/

# 実行ユーザーを切り替え
USER app

# PATHに仮想環境を追加
ENV PATH="/app/.venv/bin:$PATH"

# ポート公開
EXPOSE 8000

# Gunicorn + Uvicorn で本番起動
CMD ["gunicorn", "src.main:app", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-"]
```

---

## 3. docker-compose.yml（app + PostgreSQL）

```yaml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      target: runner
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://appuser:apppass@db:5432/appdb
      ENV: development
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - app-net

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD: apppass
      POSTGRES_DB: appdb
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U appuser -d appdb"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - app-net

volumes:
  postgres_data:

networks:
  app-net:
    driver: bridge
```

---

## 4. GitHub Actions 自動デプロイワークフロー

### Render 向け（最もシンプル）

```yaml
# .github/workflows/deploy.yml
name: Deploy to Render

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: uvをセットアップ
        uses: astral-sh/setup-uv@v3
        with:
          version: "latest"

      - name: テスト実行
        run: uv run pytest --tb=short

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Renderへデプロイをトリガー
        run: |
          curl -X POST "${{ secrets.RENDER_DEPLOY_HOOK_URL }}"
        # RENDER_DEPLOY_HOOK_URL は Render の Settings > Deploy Hook から取得
```

### Fly.io 向け（フル制御）

```yaml
# .github/workflows/deploy-fly.yml
name: Deploy to Fly.io

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
      - uses: actions/checkout@v4

      - uses: superfly/flyctl-actions/setup-flyctl@master

      - name: Fly.ioへデプロイ
        run: flyctl deploy --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

---

## 5. 最終推奨サービスと理由

### 推奨: **Render**（初〜中級者）/ **Fly.io**（中〜上級者）

```
用途別推奨：

個人学習・PoC → Render
  理由: GitHub連携→自動デプロイが最も簡単。
        Dockerfileを置くだけで動く。
        無料枠のスリープを許容できれば費用ゼロ。

本番・チーム開発 → Fly.io
  理由: アジアリージョン選択可（低レイテンシ）。
        スリープなし。従量課金で無駄がない。
        Fly Postgresで本番グレードのDB運用が可能。

学習コスト重視 → Railway
  理由: 操作感がHerokuに近く直感的。
        月$5クレジット内なら無料で試せる。
        ただし無料枠はRenderより制約が大きい。
```

### Dockerfile設計の重要ポイント

| ポイント | 理由 |
|---|---|
| マルチステージビルド | イメージサイズを1/3〜1/2に削減 |
| `python:3.12-slim` ベース | Alpine比でライブラリ互換性が高い |
| 非rootユーザー実行 | セキュリティベストプラクティス |
| Gunicorn + Uvicornワーカー | マルチプロセスで本番負荷に対応 |
| `uv sync --frozen` | 再現性のある依存関係インストール |

---

このプロジェクト（`/home/yasushi/udemy/ai-multi-agent`）の技術スタック（Python 3.12 + uv）に合わせた構成になっています。実際に使用する場合は `src.main:app` のパスをプロジェクトの構成に合わせて変更してください。
