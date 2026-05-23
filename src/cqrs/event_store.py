"""SQLite ベースの Event Store。

追記専用（append-only）でイベントを永続化する。Aggregate ごとに version での楽観ロックを
行い、同時更新による履歴の壊れを防ぐ。スナップショット機能も提供する。
"""

import dataclasses
import json
import sqlite3
import threading
from datetime import datetime
from typing import Any

from src.cqrs.events import EVENT_TYPES, Event


class ConcurrencyError(Exception):
    """楽観ロック失敗（同じ aggregate_id × version が既に存在する）。"""


class UnknownEventTypeError(Exception):
    """イベントストアから未知の event_type を読み込んだときに送出する。"""


_PAYLOAD_RESERVED = frozenset({"aggregate_id", "version", "occurred_at", "event_id"})


class EventStore:
    """SQLite を使った追記専用イベントストア。

    Args:
        db_path: SQLite データベースのパス。`":memory:"` でインメモリ。
            ファイルパスを指定した場合は `PRAGMA journal_mode=WAL` が有効化され、
            並行読み書き性能と耐障害性が向上する。`:memory:` の場合は WAL 非対応のためスキップ。

    Example:
        >>> store = EventStore(":memory:")
        >>> from src.cqrs.events import TodoAdded
        >>> store.append(TodoAdded(aggregate_id="abc", version=1, title="買い物"))
        >>> events = store.load_events("abc")
        >>> len(events)
        1
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._lock = threading.Lock()
        # ファイル DB の場合のみ WAL モードを有効化。
        # :memory: では適用できないためスキップする。
        if db_path != ":memory:":
            with self._lock:
                self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    aggregate_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    event_id TEXT NOT NULL UNIQUE,
                    UNIQUE (aggregate_id, version)
                );
                CREATE INDEX IF NOT EXISTS idx_events_aggregate
                    ON events(aggregate_id, version);

                CREATE TABLE IF NOT EXISTS snapshots (
                    aggregate_id TEXT PRIMARY KEY,
                    version INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    taken_at TEXT NOT NULL
                );
                """
            )
            self._conn.commit()

    def append(self, event: Event) -> None:
        """イベントを追記する。

        Raises:
            ConcurrencyError: 同じ aggregate_id × version が既に存在する場合。
        """
        payload = self._serialize_payload(event)
        with self._lock:
            try:
                self._conn.execute(
                    "INSERT INTO events "
                    "(aggregate_id, event_type, version, payload, occurred_at, event_id) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        event.aggregate_id,
                        type(event).event_type,
                        event.version,
                        json.dumps(payload, ensure_ascii=False),
                        event.occurred_at.isoformat(),
                        event.event_id,
                    ),
                )
                self._conn.commit()
            except sqlite3.IntegrityError as e:
                raise ConcurrencyError(
                    f"バージョン競合: aggregate_id={event.aggregate_id}, version={event.version}"
                ) from e

    def load_events(self, aggregate_id: str, from_version: int = 0) -> list[Event]:
        """指定 Aggregate のイベントを version 昇順で返す。

        Args:
            aggregate_id: 対象の Aggregate ID。
            from_version: この値より大きい version のイベントだけを返す（スナップショット後の差分取得用）。
        """
        with self._lock:
            rows = self._conn.execute(
                "SELECT event_type, version, payload, occurred_at, event_id "
                "FROM events WHERE aggregate_id = ? AND version > ? ORDER BY version",
                (aggregate_id, from_version),
            ).fetchall()
        return [self._deserialize(aggregate_id, *row) for row in rows]

    def load_all_events(self) -> list[Event]:
        """全 Aggregate の全イベントを発生順で返す（Read Model の再構築用）。"""
        with self._lock:
            rows = self._conn.execute(
                "SELECT aggregate_id, event_type, version, payload, occurred_at, event_id "
                "FROM events ORDER BY id"
            ).fetchall()
        return [self._deserialize(*row) for row in rows]

    def save_snapshot(
        self, aggregate_id: str, state: dict[str, Any], version: int
    ) -> None:
        """Aggregate の現状を スナップショットとして保存する（同 ID は上書き）。"""
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO snapshots "
                "(aggregate_id, version, state, taken_at) VALUES (?, ?, ?, ?)",
                (
                    aggregate_id,
                    version,
                    json.dumps(state, ensure_ascii=False),
                    datetime.now().isoformat(),
                ),
            )
            self._conn.commit()

    def load_snapshot(self, aggregate_id: str) -> tuple[dict[str, Any], int] | None:
        """スナップショットを読み込む。

        Returns:
            (state, version) のタプル。存在しない場合は None。
        """
        with self._lock:
            row = self._conn.execute(
                "SELECT state, version FROM snapshots WHERE aggregate_id = ?",
                (aggregate_id,),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row[0]), row[1]

    def close(self) -> None:
        """DB 接続を閉じる。"""
        with self._lock:
            self._conn.close()

    def _serialize_payload(self, event: Event) -> dict[str, Any]:
        """イベント固有のフィールドだけを JSON 化対象にする（共通フィールドは別カラム）。"""
        return {k: v for k, v in event.__dict__.items() if k not in _PAYLOAD_RESERVED}

    def _deserialize(
        self,
        aggregate_id: str,
        event_type: str,
        version: int,
        payload: str,
        occurred_at: str,
        event_id: str,
    ) -> Event:
        """DB レコードをイベントオブジェクトに変換する。

        payload はイベントクラスの固有フィールド集合でフィルタされる。
        `aggregate_id` / `version` / `occurred_at` / `event_id` などの共通フィールドは
        payload からではなく DB カラムの値を使用する（ペイロードインジェクション対策）。
        payload に存在しない既知フィールドは dataclass デフォルト値で補完される。

        Raises:
            UnknownEventTypeError: event_type が EVENT_TYPES に登録されていない場合。
        """
        cls = EVENT_TYPES.get(event_type)
        if cls is None:
            raise UnknownEventTypeError(f"未知のイベントタイプ: {event_type!r}")
        # payload の予期しないキーで共通フィールドを上書きされないよう
        # 当該イベントクラスの固有フィールドだけに絞り込む（インジェクション対策）。
        allowed_keys = {f.name for f in dataclasses.fields(cls)} - _PAYLOAD_RESERVED
        filtered = {
            k: v for k, v in json.loads(payload).items() if k in allowed_keys
        }
        return cls(
            aggregate_id=aggregate_id,
            version=version,
            occurred_at=datetime.fromisoformat(occurred_at),
            event_id=event_id,
            **filtered,
        )
