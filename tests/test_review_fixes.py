"""コードレビュー指摘事項に対するテスト。

各テストは「修正後のあるべき動作（仕様）」を表現している。
現状のコードに対しては Red になるものが含まれており、それはバグを示す正しいシグナルである。

指摘事項（初回レビュー）:
1. [Critical]  event_store._deserialize で未知 event_type が KeyError → UnknownEventTypeError を送出すべき
2. [Major]     command_handler.handle_add の version=1 ハードコード → agg.version + 1 に統一すべき
3. [Major]     main.py の todo_id パスパラメータが UUID バリデーションされない → 不正 UUID で HTTP 422
4. [Major]     main.py の list_by_priority が不正値で空リスト → HTTP 422 を返すべき
5. [Major]     projections._build_state が list_by_category / list_by_priority で 2 回呼ばれる → 1 回のみ

追加修正（第二回レビュー）:
6. aggregates.apply() に未知イベント分岐を追加 → AggregateError を送出
7. command_handler._maybe_snapshot() シグネチャ変更 → Event Store の二重ロードを排除
8. event_store._deserialize() でペイロードインジェクション対策 → 未知キーと共通フィールドを除外
9. event_store.__init__() でファイル DB の場合のみ WAL モードを有効化
10. main.py で lifespan 導入 → シャットダウン時に _event_store.close() を呼ぶ
"""

import importlib
import os
import sqlite3
import tempfile
import uuid
from unittest.mock import MagicMock, patch

import pytest

from src.cqrs.event_store import EventStore
from src.cqrs.events import TodoAdded


# ---------------------------------------------------------------------------
# 指摘 1: _deserialize で未知 event_type が KeyError → UnknownEventTypeError
# ---------------------------------------------------------------------------


class TestDeserializeUnknownEventType:
    """_deserialize に未知の event_type が渡されたとき UnknownEventTypeError を送出する。"""

    @pytest.fixture
    def store_with_unknown_event(self) -> EventStore:
        """未知の event_type を持つレコードを DB に直接書き込んだ EventStore を返す。"""
        store = EventStore(":memory:")
        # 内部の SQLite 接続に直接アクセスして不正レコードを挿入する
        aggregate_id = str(uuid.uuid4())
        with store._lock:
            store._conn.execute(
                "INSERT INTO events "
                "(aggregate_id, event_type, version, payload, occurred_at, event_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    aggregate_id,
                    "NonExistentEventType",  # EVENT_TYPES に存在しない型
                    1,
                    "{}",
                    "2024-01-01T00:00:00",
                    str(uuid.uuid4()),
                ),
            )
            store._conn.commit()
        # aggregate_id を store に記憶させる
        store._test_aggregate_id = aggregate_id  # type: ignore[attr-defined]
        return store

    def test_deserialize_unknown_event_type_raises_unknown_event_type_error(
        self, store_with_unknown_event: EventStore
    ) -> None:
        """未知の event_type を含むイベントを load すると UnknownEventTypeError が送出される。

        あるべき動作: KeyError ではなく専用例外 UnknownEventTypeError を送出し、
        エラーメッセージに event_type 名 'NonExistentEventType' を含める。
        """
        from src.cqrs.event_store import UnknownEventTypeError  # type: ignore[attr-defined]

        aggregate_id = store_with_unknown_event._test_aggregate_id  # type: ignore[attr-defined]
        with pytest.raises(UnknownEventTypeError, match="NonExistentEventType"):
            store_with_unknown_event.load_events(aggregate_id)

    def test_deserialize_unknown_event_type_error_message_contains_type_name(
        self, store_with_unknown_event: EventStore
    ) -> None:
        """UnknownEventTypeError のメッセージには不明な event_type 名が含まれる。

        あるべき動作: 開発者がデバッグできるよう、どの event_type が未知なのかを
        エラーメッセージから特定できること。
        """
        from src.cqrs.event_store import UnknownEventTypeError  # type: ignore[attr-defined]

        aggregate_id = store_with_unknown_event._test_aggregate_id  # type: ignore[attr-defined]
        with pytest.raises(UnknownEventTypeError) as exc_info:
            store_with_unknown_event.load_events(aggregate_id)
        assert "NonExistentEventType" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 指摘 2: handle_add の version=1 ハードコード → agg.version + 1 に統一
# ---------------------------------------------------------------------------


class TestHandleAddVersionConsistency:
    """handle_add が発行する TodoAdded の version は agg.version + 1 で計算される。"""

    def test_handle_add_new_todo_version_equals_agg_version_plus_one(self) -> None:
        """新規 Todo 追加時の version は agg.version（=0）+ 1 = 1 になる。

        あるべき動作: version=1 というハードコード値ではなく、
        agg.version + 1 という表現で算出される。結果は同じく 1 だが、
        コードの意図が明確になる（一貫性の確保）。
        ここでは add 後の version が実際に 1 であることを確認する。
        """
        from src.cqrs.command_handler import CommandHandler
        from src.cqrs.commands import AddTodoCommand

        store = EventStore(":memory:")
        handler = CommandHandler(store)
        aid = str(uuid.uuid4())

        event = handler.handle_add(AddTodoCommand(aggregate_id=aid, title="テスト"))

        # 新規作成時 agg.version=0 なので agg.version + 1 = 1
        assert event.version == 1

    def test_handle_add_version_is_derived_from_aggregate_state(self) -> None:
        """handle_add の version 計算が agg.version を参照している（コードレベルの一貫性）。

        あるべき動作: handle_complete / handle_delete と同様に
        `agg.version + 1` という形で version を計算する。
        現在のコードは version=1 とハードコードしているため、
        将来の Aggregate リファクタリング時に矛盾が生じる可能性がある。

        このテストはソースコードを直接検査して、ハードコードされた version=1 が
        存在しないことを確認する。
        """
        import ast
        import pathlib

        source = pathlib.Path("/workspace/src/cqrs/command_handler.py").read_text()
        tree = ast.parse(source)

        # handle_add 関数内の TodoAdded コンストラクタ呼び出しを探す
        hardcoded_version_found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "handle_add":
                for child in ast.walk(node):
                    # keyword(arg='version', value=Constant(value=1)) を探す
                    if isinstance(child, ast.keyword):
                        if child.arg == "version" and isinstance(child.value, ast.Constant):
                            if child.value.value == 1:
                                hardcoded_version_found = True

        assert not hardcoded_version_found, (
            "handle_add 内に version=1 のハードコードが見つかりました。"
            "agg.version + 1 に統一してください。"
        )


# ---------------------------------------------------------------------------
# 指摘 3: todo_id パスパラメータが UUID バリデーションされない → HTTP 422
# ---------------------------------------------------------------------------


@pytest.fixture
def api_client():
    """テストごとに一時 DB ファイルを使う FastAPI クライアントを返す。"""
    from fastapi.testclient import TestClient

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    os.environ["TODO_DB_PATH"] = tmp.name

    import src.main

    importlib.reload(src.main)
    with TestClient(src.main.app) as c:
        yield c

    src.main._event_store.close()
    os.unlink(tmp.name)
    os.environ.pop("TODO_DB_PATH", None)


class TestTodoIdUUIDValidation:
    """todo_id パスパラメータに不正な UUID 形式が渡された場合 HTTP 422 を返す。"""

    INVALID_IDS = [
        "not-a-uuid",
        "12345",
        "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "../../etc/passwd",
        "",
    ]

    def test_complete_todo_with_invalid_uuid_returns_422(self, api_client) -> None:
        """POST /todos/{todo_id}/complete に不正 UUID を渡すと HTTP 422。

        あるべき動作: FastAPI の uuid.UUID 型バリデーションにより、
        UUID 形式でない文字列はリクエストが Handler に到達する前に 422 で拒否される。
        """
        resp = api_client.post("/todos/not-a-valid-uuid/complete")
        assert resp.status_code == 422, (
            f"不正 UUID に対して 422 を期待しましたが {resp.status_code} が返りました。"
            "パスパラメータを uuid.UUID 型でバリデーションしてください。"
        )

    def test_delete_todo_with_invalid_uuid_returns_422(self, api_client) -> None:
        """DELETE /todos/{todo_id} に不正 UUID を渡すと HTTP 422。

        あるべき動作: FastAPI の uuid.UUID 型バリデーションにより、
        UUID 形式でない文字列は 422 で拒否される。
        """
        resp = api_client.delete("/todos/not-a-valid-uuid")
        assert resp.status_code == 422, (
            f"不正 UUID に対して 422 を期待しましたが {resp.status_code} が返りました。"
        )

    def test_get_todo_with_invalid_uuid_returns_422(self, api_client) -> None:
        """GET /todos/{todo_id} に不正 UUID を渡すと HTTP 422。

        あるべき動作: FastAPI の uuid.UUID 型バリデーションにより、
        UUID 形式でない文字列は 422 で拒否される。
        """
        resp = api_client.get("/todos/not-a-valid-uuid")
        assert resp.status_code == 422, (
            f"不正 UUID に対して 422 を期待しましたが {resp.status_code} が返りました。"
        )

    def test_get_todo_events_with_invalid_uuid_returns_422(self, api_client) -> None:
        """GET /todos/{todo_id}/events に不正 UUID を渡すと HTTP 422。

        あるべき動作: FastAPI の uuid.UUID 型バリデーションにより、
        UUID 形式でない文字列は 422 で拒否される。
        """
        resp = api_client.get("/todos/not-a-valid-uuid/events")
        assert resp.status_code == 422, (
            f"不正 UUID に対して 422 を期待しましたが {resp.status_code} が返りました。"
        )

    def test_complete_todo_with_valid_uuid_format_proceeds_to_handler(
        self, api_client
    ) -> None:
        """正しい UUID 形式であれば Handler まで到達し、存在チェックで 409 が返る。

        あるべき動作: UUID 形式が正しければバリデーションは通過し、
        存在しない ID に対しては 409 Conflict が返る（現状と同じ動作を維持）。
        """
        valid_uuid = str(uuid.uuid4())
        resp = api_client.post(f"/todos/{valid_uuid}/complete")
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# 指摘 4: list_by_priority の不正値で空リスト → HTTP 422
# ---------------------------------------------------------------------------


class TestListByPriorityValidation:
    """GET /todos?priority= に高/中/低 以外の値を指定すると HTTP 422 を返す。"""

    def test_list_todos_with_invalid_priority_returns_422(self, api_client) -> None:
        """priority クエリに '高/中/低' 以外を指定すると HTTP 422。

        あるべき動作: 不正な priority 値はクエリバリデーションで弾かれ、
        空リストを返すのではなく HTTP 422 Unprocessable Entity を返す。
        クライアントが誤った priority を指定したことを明示的にエラーで通知する。
        """
        resp = api_client.get("/todos", params={"priority": "緊急"})
        assert resp.status_code == 422, (
            f"不正 priority に対して 422 を期待しましたが {resp.status_code} が返りました。"
            "priority クエリパラメータを Enum 型等でバリデーションしてください。"
        )

    def test_list_todos_with_invalid_priority_english_returns_422(
        self, api_client
    ) -> None:
        """priority クエリに英語値 'high' を指定すると HTTP 422。

        あるべき動作: 日本語('高/中/低')以外の値は全て 422 で拒否される。
        """
        resp = api_client.get("/todos", params={"priority": "high"})
        assert resp.status_code == 422, (
            f"不正 priority 'high' に対して 422 を期待しましたが {resp.status_code} が返りました。"
        )

    def test_list_todos_with_valid_priority_returns_200(self, api_client) -> None:
        """priority クエリに '高' を指定すると正常に 200 を返す。

        あるべき動作: 有効な priority 値では既存どおりフィルタ結果を返す。
        """
        resp = api_client.get("/todos", params={"priority": "高"})
        assert resp.status_code == 200

    @pytest.mark.parametrize("valid_priority", ["高", "中", "低"])
    def test_list_todos_with_all_valid_priorities_returns_200(
        self, api_client, valid_priority: str
    ) -> None:
        """priority クエリに '高/中/低' を指定すると 200 を返す。

        あるべき動作: 有効な値はいずれも受け入れられる。
        """
        resp = api_client.get("/todos", params={"priority": valid_priority})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 指摘 5: _build_state が list_by_category / list_by_priority で 2 回呼ばれる
# ---------------------------------------------------------------------------


class TestBuildStateCalledOnce:
    """list_by_category / list_by_priority は load_all_events を 1 回だけ呼ぶ。"""

    def test_list_by_category_calls_load_all_events_once(self) -> None:
        """list_by_category は load_all_events を 1 回しか呼ばない。

        あるべき動作: list_by_category は内部で _build_state を 1 回呼び、
        load_all_events の呼び出しも 1 回に留まる。
        現状は list_all() → _build_state() → load_all_events() が呼ばれた後、
        さらに内部でもう一度 _build_state() が呼ばれるため計 2 回になっている。
        """
        from src.cqrs.projections import TodoReadModel

        mock_store = MagicMock()
        mock_store.load_all_events.return_value = [
            TodoAdded(
                aggregate_id="test-id",
                version=1,
                title="仕事タスク",
                category="仕事",
                priority="高",
            )
        ]
        rm = TodoReadModel(mock_store)

        rm.list_by_category("仕事")

        assert mock_store.load_all_events.call_count == 1, (
            f"load_all_events が {mock_store.load_all_events.call_count} 回呼ばれました。"
            "1 回のみ呼ばれるべきです。_build_state の重複呼び出しを修正してください。"
        )

    def test_list_by_priority_calls_load_all_events_once(self) -> None:
        """list_by_priority は load_all_events を 1 回しか呼ばない。

        あるべき動作: list_by_priority は内部で _build_state を 1 回呼び、
        load_all_events の呼び出しも 1 回に留まる。
        """
        from src.cqrs.projections import TodoReadModel

        mock_store = MagicMock()
        mock_store.load_all_events.return_value = [
            TodoAdded(
                aggregate_id="test-id-2",
                version=1,
                title="高優先タスク",
                category="",
                priority="高",
            )
        ]
        rm = TodoReadModel(mock_store)

        rm.list_by_priority("高")

        assert mock_store.load_all_events.call_count == 1, (
            f"load_all_events が {mock_store.load_all_events.call_count} 回呼ばれました。"
            "1 回のみ呼ばれるべきです。_build_state の重複呼び出しを修正してください。"
        )

    def test_list_by_category_returns_correct_items(self) -> None:
        """list_by_category は正しいカテゴリのアイテムのみを返す（機能正確性も担保）。

        あるべき動作: カテゴリフィルタが正しく動作し、かつ load_all_events は 1 回のみ。
        """
        from src.cqrs.projections import TodoReadModel

        a1, a2 = str(uuid.uuid4()), str(uuid.uuid4())
        mock_store = MagicMock()
        mock_store.load_all_events.return_value = [
            TodoAdded(
                aggregate_id=a1,
                version=1,
                title="仕事タスク",
                category="仕事",
                priority="高",
            ),
            TodoAdded(
                aggregate_id=a2,
                version=1,
                title="買い物タスク",
                category="買い物",
                priority="中",
            ),
        ]
        rm = TodoReadModel(mock_store)

        items = rm.list_by_category("仕事")

        assert len(items) == 1
        assert items[0].title == "仕事タスク"
        assert mock_store.load_all_events.call_count == 1

    def test_list_by_priority_returns_correct_items(self) -> None:
        """list_by_priority は正しい優先度のアイテムのみを返す（機能正確性も担保）。

        あるべき動作: 優先度フィルタが正しく動作し、かつ load_all_events は 1 回のみ。
        """
        from src.cqrs.projections import TodoReadModel

        a1, a2 = str(uuid.uuid4()), str(uuid.uuid4())
        mock_store = MagicMock()
        mock_store.load_all_events.return_value = [
            TodoAdded(
                aggregate_id=a1,
                version=1,
                title="高優先タスク",
                category="",
                priority="高",
            ),
            TodoAdded(
                aggregate_id=a2,
                version=1,
                title="低優先タスク",
                category="",
                priority="低",
            ),
        ]
        rm = TodoReadModel(mock_store)

        items = rm.list_by_priority("低")

        assert len(items) == 1
        assert items[0].title == "低優先タスク"
        assert mock_store.load_all_events.call_count == 1


# ---------------------------------------------------------------------------
# 修正 6: aggregates.apply() に未知イベント分岐 → AggregateError を送出
# ---------------------------------------------------------------------------


class TestApplyUnknownEvent:
    """apply() に未知のイベントタイプを渡すと AggregateError が送出される。"""

    def test_apply_unknown_event_raises_aggregate_error(self) -> None:
        """apply() に未知イベントを渡すと AggregateError が送出される。

        あるべき動作: 既知の TodoAdded / TodoCompleted / TodoDeleted 以外のイベントが
        apply() に渡されたとき、AggregateError を送出し、リプレイの壊れを即座に検出できる。
        """
        from src.cqrs.aggregates import AggregateError, TodoAggregate
        from src.cqrs.events import Event

        # 未知のイベントクラスをインラインで定義する
        @dataclass_like_event
        class UnknownEvent(Event):
            event_type = "UnknownEvent"  # type: ignore[assignment]

        agg = TodoAggregate(aggregate_id=str(uuid.uuid4()))
        unknown = UnknownEvent(aggregate_id=agg.aggregate_id, version=1)

        with pytest.raises(AggregateError, match="UnknownEvent"):
            agg.apply(unknown)

    def test_apply_unknown_event_error_message_contains_type_name(self) -> None:
        """AggregateError のメッセージには未知のイベントタイプ名が含まれる。

        あるべき動作: エラーメッセージから「どのイベントタイプが未知だったか」を
        開発者がすぐ特定できること。
        """
        from src.cqrs.aggregates import AggregateError, TodoAggregate
        from src.cqrs.events import Event

        @dataclass_like_event
        class AnotherUnknown(Event):
            event_type = "AnotherUnknown"  # type: ignore[assignment]

        agg = TodoAggregate(aggregate_id=str(uuid.uuid4()))
        unknown = AnotherUnknown(aggregate_id=agg.aggregate_id, version=1)

        with pytest.raises(AggregateError) as exc_info:
            agg.apply(unknown)
        assert "AnotherUnknown" in str(exc_info.value)

    def test_apply_known_events_do_not_raise(self) -> None:
        """既知のイベント (TodoAdded, TodoCompleted, TodoDeleted) は正常に適用される。

        あるべき動作: 未知イベント検出のガード追加後も、既知イベントには影響しない。
        """
        from src.cqrs.aggregates import TodoAggregate
        from src.cqrs.events import TodoAdded, TodoCompleted, TodoDeleted

        aid = str(uuid.uuid4())
        agg = TodoAggregate(aggregate_id=aid)
        agg.apply(TodoAdded(aggregate_id=aid, version=1, title="テスト", category="", priority="中"))
        agg.apply(TodoCompleted(aggregate_id=aid, version=2))
        agg.apply(TodoDeleted(aggregate_id=aid, version=3))

        assert agg.version == 3
        assert agg.completed is True
        assert agg.deleted is True


def dataclass_like_event(cls):
    """Event サブクラスに frozen dataclass デコレータを適用するヘルパー。"""
    import dataclasses
    return dataclasses.dataclass(frozen=True, kw_only=True)(cls)


# ---------------------------------------------------------------------------
# 修正 7: _maybe_snapshot の二重ロード排除
# ---------------------------------------------------------------------------


class TestMaybeSnapshotNoDoubleLoad:
    """_maybe_snapshot がスナップショット保存時に Event Store を再ロードしない。"""

    def test_maybe_snapshot_no_double_load_at_interval(self) -> None:
        """snapshot_interval=1 で 1 件追加したとき load_events は 1 回だけ呼ばれる。

        あるべき動作: _maybe_snapshot は既に手元にある agg と event から最新状態を
        組み立てるため、Event Store への追加ロードは発生しない。
        修正前は _maybe_snapshot 内で load_events / load_snapshot を再呼び出しして
        二重ロードが発生していた。
        """
        from src.cqrs.command_handler import CommandHandler
        from src.cqrs.commands import AddTodoCommand

        store = MagicMock(spec=EventStore)
        # load_snapshot は None（スナップショットなし）を返す
        store.load_snapshot.return_value = None
        # load_events は空リストを返す（新規 Aggregate）
        store.load_events.return_value = []
        # append は副作用なし
        store.append.return_value = None
        # save_snapshot は副作用なし
        store.save_snapshot.return_value = None

        # snapshot_interval=1 にすることで最初のイベントでスナップショットが走る
        handler = CommandHandler(store, snapshot_interval=1)
        aid = str(uuid.uuid4())

        handler.handle_add(AddTodoCommand(aggregate_id=aid, title="テスト"))

        # load_events は _load() の中で 1 回だけ呼ばれるべき
        # _maybe_snapshot 内で追加ロードが走ると 2 回以上になる
        assert store.load_events.call_count == 1, (
            f"load_events が {store.load_events.call_count} 回呼ばれました。"
            "_maybe_snapshot 内での二重ロードが修正されていない可能性があります。"
        )
        # load_snapshot も 1 回だけ（_load() の中のみ）
        assert store.load_snapshot.call_count == 1, (
            f"load_snapshot が {store.load_snapshot.call_count} 回呼ばれました。"
            "_maybe_snapshot 内での二重ロードが修正されていない可能性があります。"
        )
        # スナップショットは保存されるべき（interval=1 なので version=1 でトリガー）
        assert store.save_snapshot.call_count == 1

    def test_maybe_snapshot_not_triggered_below_interval(self) -> None:
        """snapshot_interval=10 で 1 件追加してもスナップショットは保存されない。

        あるべき動作: version が snapshot_interval の倍数でなければ
        save_snapshot は呼ばれない（追加ロードも発生しない）。
        """
        from src.cqrs.command_handler import CommandHandler
        from src.cqrs.commands import AddTodoCommand

        store = MagicMock(spec=EventStore)
        store.load_snapshot.return_value = None
        store.load_events.return_value = []
        store.append.return_value = None

        handler = CommandHandler(store, snapshot_interval=10)
        aid = str(uuid.uuid4())

        handler.handle_add(AddTodoCommand(aggregate_id=aid, title="テスト"))

        # interval に達していないのでスナップショットは保存されない
        assert store.save_snapshot.call_count == 0
        # ロードは _load() の中で 1 回だけ
        assert store.load_events.call_count == 1
        assert store.load_snapshot.call_count == 1


# ---------------------------------------------------------------------------
# 修正 8: _deserialize でペイロードインジェクション対策
# ---------------------------------------------------------------------------


class TestDeserializeFiltersPayloadKeys:
    """_deserialize が payload の未知キーと共通フィールドを安全に無視する。"""

    def _insert_raw_event(
        self, store: EventStore, aggregate_id: str, payload_str: str
    ) -> None:
        """テスト用に細工した payload を直接 SQLite に INSERT する。"""
        with store._lock:
            store._conn.execute(
                "INSERT INTO events "
                "(aggregate_id, event_type, version, payload, occurred_at, event_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    aggregate_id,
                    "TodoAdded",
                    1,
                    payload_str,
                    "2024-01-01T00:00:00",
                    str(uuid.uuid4()),
                ),
            )
            store._conn.commit()

    def test_deserialize_filters_unknown_payload_keys(self) -> None:
        """payload に未知キーが含まれていても正常にデシリアライズできる。

        あるべき動作: payload に TodoAdded のフィールドに存在しない任意のキーが
        含まれていてもエラーにならず、既知フィールドだけが使われる。
        """
        store = EventStore(":memory:")
        aid = str(uuid.uuid4())
        # unknown_key は TodoAdded に存在しないフィールド
        payload = '{"title": "テスト", "category": "仕事", "priority": "高", "unknown_key": "malicious"}'
        self._insert_raw_event(store, aid, payload)

        events = store.load_events(aid)

        assert len(events) == 1
        event = events[0]
        assert event.title == "テスト"
        assert event.category == "仕事"
        assert event.priority == "高"
        # unknown_key は無視されること（TodoAdded には属性として存在しない）
        assert not hasattr(event, "unknown_key")

    def test_deserialize_ignores_payload_overrides_for_reserved_fields(self) -> None:
        """payload に aggregate_id / version 等の共通フィールドが含まれていても上書きされない。

        あるべき動作: payload 内の 'aggregate_id', 'version', 'occurred_at', 'event_id'
        は無視され、DB カラムの値が使われる。攻撃者が payload を細工して
        Aggregate ID を偽装しようとしても防げること。
        """
        store = EventStore(":memory:")
        aid = str(uuid.uuid4())
        injected_id = str(uuid.uuid4())  # 偽の aggregate_id
        # 共通フィールドを payload に含めてインジェクションを試みる
        payload = (
            f'{{"title": "テスト", "category": "", "priority": "中", '
            f'"aggregate_id": "{injected_id}", "version": 999}}'
        )
        self._insert_raw_event(store, aid, payload)

        events = store.load_events(aid)

        assert len(events) == 1
        event = events[0]
        # DB カラムの値が使われること（payload の偽値で上書きされないこと）
        assert event.aggregate_id == aid, (
            f"aggregate_id が payload の値 {injected_id!r} で上書きされました。"
            "ペイロードインジェクション対策が機能していません。"
        )
        assert event.version == 1, (
            f"version が payload の偽値 999 で上書きされました。"
            "ペイロードインジェクション対策が機能していません。"
        )


# ---------------------------------------------------------------------------
# 修正 9: EventStore.__init__ でファイル DB 限定の WAL モード有効化
# ---------------------------------------------------------------------------


class TestEventStoreWALMode:
    """ファイル DB では WAL モードが有効になり、:memory: では有効にならない。"""

    def test_event_store_enables_wal_mode_for_file_db(self, tmp_path) -> None:
        """ファイル DB で EventStore を初期化すると journal_mode が WAL になる。

        あるべき動作: ファイルベースの SQLite DB では `PRAGMA journal_mode=WAL` が
        実行され、並行読み書き性能と耐障害性が向上する。
        """
        db_file = str(tmp_path / "test.db")
        store = EventStore(db_file)

        try:
            with store._lock:
                row = store._conn.execute("PRAGMA journal_mode").fetchone()
            journal_mode = row[0]
        finally:
            store.close()

        assert journal_mode == "wal", (
            f"ファイル DB の journal_mode は 'wal' であるべきですが '{journal_mode}' でした。"
        )

    def test_event_store_memory_db_does_not_enable_wal_mode(self) -> None:
        """:memory: DB では WAL モードは有効にならない（適用不可のため）。

        あるべき動作: :memory: は PRAGMA journal_mode=WAL が適用できないため
        スキップされ、エラーも発生しない。journal_mode は 'memory' のまま。
        """
        store = EventStore(":memory:")

        try:
            with store._lock:
                row = store._conn.execute("PRAGMA journal_mode").fetchone()
            journal_mode = row[0]
        finally:
            store.close()

        # :memory: の journal_mode は 'memory' であること
        assert journal_mode == "memory", (
            f":memory: の journal_mode は 'memory' であるべきですが '{journal_mode}' でした。"
        )


# ---------------------------------------------------------------------------
# 修正 10: lifespan で close() が呼ばれる
# ---------------------------------------------------------------------------


class TestLifespanClosesEventStore:
    """lifespan コンテキスト終了時に _event_store.close() が呼ばれる。"""

    def test_lifespan_closes_event_store_on_shutdown(self) -> None:
        """TestClient の with ブロック終了（アプリシャットダウン）時に close() が呼ばれる。

        あるべき動作: lifespan の finally 節で _event_store.close() が実行され、
        DB 接続が確実に閉じられる。
        """
        from fastapi.testclient import TestClient

        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        os.environ["TODO_DB_PATH"] = tmp.name

        import src.main

        importlib.reload(src.main)

        close_called = []

        original_close = src.main._event_store.close

        def spy_close():
            close_called.append(True)
            original_close()

        src.main._event_store.close = spy_close  # type: ignore[method-assign]

        with TestClient(src.main.app):
            pass  # アプリのシャットダウンは with ブロック終了時に走る

        os.unlink(tmp.name)
        os.environ.pop("TODO_DB_PATH", None)

        assert len(close_called) == 1, (
            "lifespan の shutdown 時に _event_store.close() が呼ばれていません。"
            "lifespan の finally 節を確認してください。"
        )

    def test_lifespan_event_store_connection_closed_after_shutdown(self) -> None:
        """アプリシャットダウン後に _event_store._conn は閉じられている。

        あるべき動作: lifespan 終了後は DB 接続が閉じられており、
        接続を使った操作は ProgrammingError を送出する。
        """
        from fastapi.testclient import TestClient

        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        os.environ["TODO_DB_PATH"] = tmp.name

        import src.main

        importlib.reload(src.main)
        event_store_ref = src.main._event_store

        with TestClient(src.main.app):
            pass  # シャットダウン実行

        os.unlink(tmp.name)
        os.environ.pop("TODO_DB_PATH", None)

        # 接続が閉じられているため execute は ProgrammingError を送出するべき
        with pytest.raises(sqlite3.ProgrammingError):
            event_store_ref._conn.execute("SELECT 1")
