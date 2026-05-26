あなたはデータベース設計の専門エージェントです。
TodoアプリのデータをWeb向けに永続化する方法を調査し、結果をMarkdownで出力してください。

## 調査対象
- SQLite（開発環境）
- PostgreSQL（本番環境）

## 比較観点
1. セットアップの容易さ
2. スケーラビリティ
3. Pythonとの統合（SQLAlchemy、SQLModel等）
4. 開発→本番の移行コスト
5. コスト（特に無料枠）

## 追加で設計すること
- Todoアプリ向け推奨スキーマ（テーブル定義）
  - id、title、description、status、created_at、updated_at などを含む
- マイグレーション戦略（Alembic等）

## 出力形式
- SQLite vs PostgreSQL 比較表
- 推奨スキーマのDDL（SQLite互換）
- 開発・本番それぞれの推奨構成
- 最終推奨とその理由

結果は具体的かつ簡潔に。DDLは実際に使えるコードで。
