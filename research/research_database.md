TodoアプリのDB設計調査結果をMarkdownで出力します。

# TodoアプリDB設計調査レポート

## SQLite vs PostgreSQL 比較表

| 観点 | SQLite | PostgreSQL |
|------|--------|------------|
| **セットアップ** | ファイル1つで即起動、依存なし | サーバープロセス必要、Docker推奨 |
| **スケーラビリティ** | 単一ライター制約あり（WALモードで緩和可）、〜数GB/数千RPSが上限 | 水平・垂直スケール両対応、コネクションプーリング可 |
| **Python統合** | 標準ライブラリ`sqlite3`付属、SQLAlchemy/SQLModel完全対応 | `psycopg2`/`asyncpg`必要、SQLAlchemy/SQLModel完全対応 |
| **移行コスト** | スキーマ差異あり（BOOLEAN型等）、Alembicで吸収可能 | 移行先のため追加コストなし |
| **コスト（無料枠）** | 無料（ローカルファイル）、Fly.io等でホスト可 | Supabase/Neon/Render が無料枠提供 |
| **JSONサポート** | JSON1拡張（限定的） | JSONB型（インデックス・クエリ強力） |
| **同時接続** | 実質シングルプロセス向き | 数百〜数千コネクション対応 |
| **型安全性** | 型強制なし（動的型付け） | 厳格な型チェック |

---

## 推奨スキーマ DDL（SQLite互換）

```sql
-- ユーザーテーブル（認証連携を見据えた設計）
CREATE TABLE users (
    id       TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    email    TEXT NOT NULL UNIQUE,
    name     TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- Todoテーブル
CREATE TABLE todos (
    id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 200),
    description TEXT,
    status      TEXT NOT NULL DEFAULT 'todo'
                    CHECK(status IN ('todo', 'in_progress', 'done')),
    due_date    DATE,
    created_at  DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at  DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- 更新日時の自動更新トリガー（SQLite用）
CREATE TRIGGER todos_updated_at
    AFTER UPDATE ON todos
    FOR EACH ROW
BEGIN
    UPDATE todos SET updated_at = datetime('now') WHERE id = OLD.id;
END;

-- 検索用インデックス
CREATE INDEX idx_todos_user_id ON todos(user_id);
CREATE INDEX idx_todos_status   ON todos(status);
CREATE INDEX idx_todos_due_date ON todos(due_date);
```

### PostgreSQL向け差分（本番）

```sql
-- UUIDはgen_random_uuid()を使用
-- BOOLEAN型を使用（SQLiteはINTEGER 0/1）
-- TIMESTAMPTZで timezone-aware に

CREATE TABLE todos (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT NOT NULL CHECK(char_length(title) BETWEEN 1 AND 200),
    description TEXT,
    status      TEXT NOT NULL DEFAULT 'todo'
                    CHECK(status IN ('todo', 'in_progress', 'done')),
    due_date    DATE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 更新日時の自動更新（PostgreSQL用トリガー）
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER todos_updated_at
    BEFORE UPDATE ON todos
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

---

## SQLModel定義（Python）

```python
from datetime import datetime, date
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field
import uuid

class TodoStatus(str, Enum):
    todo        = "todo"
    in_progress = "in_progress"
    done        = "done"

class Todo(SQLModel, table=True):
    __tablename__ = "todos"

    id:          str          = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id:     str          = Field(foreign_key="users.id", index=True)
    title:       str          = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None)
    status:      TodoStatus   = Field(default=TodoStatus.todo, index=True)
    due_date:    Optional[date] = Field(default=None)
    created_at:  datetime     = Field(default_factory=datetime.utcnow)
    updated_at:  datetime     = Field(default_factory=datetime.utcnow)
```

---

## マイグレーション戦略（Alembic）

### 初期セットアップ

```bash
uv add alembic sqlalchemy sqlmodel
uv run alembic init alembic
```

### `alembic/env.py` の設定

```python
from sqlmodel import SQLModel
from src.models import Todo, User  # noqa: F401（自動検出のため必要）
from src.config import settings

target_metadata = SQLModel.metadata

def get_url():
    return settings.DATABASE_URL  # 環境変数から取得
```

### `src/config.py`（環境切り替え）

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./dev.db"  # 開発デフォルト

    class Config:
        env_file = ".env"

settings = Settings()
```

### `.env`（開発）

```
DATABASE_URL=sqlite:///./dev.db
```

### `.env`（本番 例: Supabase）

```
DATABASE_URL=postgresql+asyncpg://user:pass@db.xxx.supabase.co:5432/postgres
```

### マイグレーションコマンド

```bash
# マイグレーションファイル自動生成
uv run alembic revision --autogenerate -m "add todos table"

# 本番/開発共通で適用
uv run alembic upgrade head

# ロールバック
uv run alembic downgrade -1
```

---

## 開発・本番 推奨構成

### 開発環境

```
SQLite (WALモード有効)
  ├── ファイル: dev.db
  ├── 接続: sqlite+aiosqlite:///./dev.db
  └── Alembicでスキーマ管理
```

```python
# WALモード有効化（FastAPI startup）
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine("sqlite+aiosqlite:///./dev.db")

@event.listens_for(engine.sync_engine, "connect")
def set_wal_mode(conn, _):
    conn.execute("PRAGMA journal_mode=WAL")
```

### 本番環境（推奨: Supabase 無料枠）

```
PostgreSQL (Supabase / Neon / Render)
  ├── 接続: postgresql+asyncpg://...
  ├── コネクションプーリング: PgBouncer（Supabase付属）
  ├── マイグレーション: GitHub Actions + alembic upgrade head
  └── バックアップ: Supabase自動バックアップ（無料枠7日）
```

| サービス | 無料枠DB容量 | 接続数上限 | 備考 |
|---------|------------|-----------|------|
| Supabase | 500MB | 200 | Postgrest/Auth付属 |
| Neon | 512MB | 100 | サーバーレス・自動スリープ |
| Render | 1GB | 97 | 90日後削除注意 |

---

## 最終推奨と理由

**開発: SQLite + aiosqlite、本番: PostgreSQL (Supabase)**

### 推奨理由

1. **開発体験**: SQLiteはゼロセットアップ。`uv add aiosqlite` だけで即起動できる
2. **本番信頼性**: PostgreSQLは同時書き込み・トランザクション分離が堅牢。Todoアプリがスケールしても対応可能
3. **移行コスト最小化**: SQLModel + Alembic により `DATABASE_URL` の1行変更で開発→本番を切り替えられる。スキーマ差異（UUIDなど）はAlembicの`render_as_batch`オプションで吸収
4. **コスト**: Supabaseの無料枠（500MB）でTodoアプリは数年単位で運用可能
5. **エコシステム**: SQLModelはFastAPIと同一作者製で、PydanticバリデーションとDB定義を1クラスで管理できる

### 採用しない選択肢の理由

- **MongoDB**: Todoのような関係データにドキュメントDBは過剰
- **MySQL**: PostgreSQLに比べJSON/型サポートが劣り、Supabase等の無料PaaSでの優位性なし
- **本番SQLite**: 単一ライター制限とバックアップ運用が複雑になるため非推奨
