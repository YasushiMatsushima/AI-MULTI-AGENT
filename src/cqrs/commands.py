"""コマンドの定義。

コマンドは「ユーザーがやりたいこと」を表すデータクラス。Command Handler が検証し、
成功すればドメインイベントを発行する。コマンド自身は副作用を持たない。
"""

from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class Command:
    """全コマンドの基底クラス。"""


@dataclass(frozen=True, kw_only=True)
class AddTodoCommand(Command):
    """新規 Todo を追加するコマンド。

    Attributes:
        aggregate_id: 追加する Todo の ID（呼び出し側が生成して指定する。通常は UUID）。
        title: タスクのタイトル。前後の空白は Command Handler 側で除去される。
        category: カテゴリ名。前後の空白は除去される。
        priority: 優先度。"高" / "中" / "低" のいずれか。
    """

    aggregate_id: str
    title: str
    category: str = ""
    priority: str = "中"


@dataclass(frozen=True, kw_only=True)
class CompleteTodoCommand(Command):
    """既存 Todo を完了状態にするコマンド。"""

    aggregate_id: str


@dataclass(frozen=True, kw_only=True)
class DeleteTodoCommand(Command):
    """既存 Todo を削除するコマンド。"""

    aggregate_id: str
