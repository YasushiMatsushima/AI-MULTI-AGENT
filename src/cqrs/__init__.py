"""CQRS + Event Sourcing 実装パッケージ。

このパッケージは以下のモジュールから構成される：
- events: ドメインイベントの定義（TodoAdded, TodoCompleted, TodoDeleted）
- event_store: SQLite ベースの追記専用イベントストア + スナップショット
- commands: コマンド定義（AddTodoCommand 等）
- aggregates: TodoAggregate（イベントリプレイ + 状態保持）
- command_handler: コマンドを受けて検証しイベントを発行する
- projections: Read Model（全イベントから現在状態を組み立てる）
"""
