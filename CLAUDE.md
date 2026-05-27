# マルチエージェントコース

## プロジェクト概要
Claude Codeのマルチエージェント機能を学習する実習プロジェクト

## 技術スタック
- Python 3.12
- パッケージ管理: uv（pipは使用しない）
- テスト: pytest
- フレームワーク: FastAPI

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

## エージェントログ出力（必須）
Agent Teams のチームメイトおよびサブエージェントは、Dev Container 環境で tmux 分割表示が見えないため、ログをファイルに残すことで進捗を可視化する。**ログを残さなかった場合はタスク未完了とみなす。**

### ログ出力ルール
- ログディレクトリ: `/workspace/logs/`
- ファイル名: `agent_<役割名>.log`（例: `agent_database.log`, `agent_framework.log`）
- 役割名はリーダーから割り当てられた名前を使う（小文字スネークケース）

### 起動直後（最優先で実行）
作業を始める前に、必ず最初の Bash で以下を実行する：
```bash
mkdir -p /workspace/logs
echo "[$(date -Iseconds)] START role=<役割名>" >> /workspace/logs/agent_<役割名>.log
```

### 主要ステップごと
ファイル編集・コマンド実行・調査の節目ごとに追記する：
```bash
echo "[$(date -Iseconds)] <ステップの1行要約>" >> /workspace/logs/agent_<役割名>.log
```

### 完了時
作業を完了する直前に必ず以下を実行する：
```bash
echo "[$(date -Iseconds)] DONE summary=<成果の1行要約>" >> /workspace/logs/agent_<役割名>.log
```

### リーダー側の検証義務
リーダー（メイン Claude）はチームメイトの完了報告を受け取った際、以下を必ず確認する：
1. `/workspace/logs/agent_<役割名>.log` が存在すること
2. ログ末尾に `DONE` 行が含まれていること
3. 不足があれば該当チームメイトを再起動してログ補完を要求する

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

## API開発ルール
- WebフレームワークはFastAPIを使用する
- ORMはSQLModelを使用する
- データベースはSQLite（開発環境）
- APIテストにはhttpxのAsyncClientを使用する
- サーバー起動コマンド: uv run uvicorn src.main:app --reload
- テスト実行コマンド: uv run pytest -v