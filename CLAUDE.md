# マルチエージェントコース

## プロジェクト概要
Claude Codeのマルチエージェント機能を学習する実習プロジェクト

## 技術スタック
- Python 3.12
- パッケージ管理: uv（pipは使用しない）
- テスト: pytest
- フレームワーク: FastAPI（セクション7で使用）

## 開発ルール
- コメントとドキュメントは日本語で記述する
- パッケージの追加は `uv add` を使う
- スクリプト実行は `uv run python` を使う
- テスト実行は `uv run pytest` を使う
- pip install は絶対に使わないこと

## ディレクトリ構成
- src/ : メインのソースコード
- tests/ : テストコード
- docs/ : ドキュメント

## gitへのcommit、push
- claude側で自動でやらない（現状）

## 完了の定義（/goal 評価基準）
以下がすべて満たされた状態を「完了」とする：
- `uv run pytest` がすべてパスしている（終了コード0）
- `uv run python -c "import src.main"` がエラーなく実行できる
- 新規追加した機能にはテストが tests/ に存在する
- コメント・ドキュメントが日本語で記述されている

## 禁止事項
- `pip install` を使用しない（`uv add` を使う）
- `src/.env` をコミットしない
- `.venv/` を直接編集しない
- テストを削除して通過させない

## /goal テンプレート
長時間タスクやマルチエージェント実行には以下の4ブロック構造を使う：

```
/goal [達成したいゴール]

context:
- Python 3.12 / FastAPI / uv プロジェクト
- src/ にソースコード、tests/ にテスト、docs/ にドキュメント
- [今回の作業背景・変更理由]

done when:
- [ログを見て30秒で確認できる具体的な完了条件]
- uv run pytest がすべてパスしている（終了コード0）

do not:
- pip install を使わない
- src/.env を変更しない
- テストを削除して通過させない

progress tracking:
完了したステップを progress.md に随時記録すること
```