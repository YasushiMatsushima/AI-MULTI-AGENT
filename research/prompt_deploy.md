あなたはデプロイ戦略の専門エージェントです。
PythonのFastAPIアプリをDockerでコンテナ化してクラウドにデプロイする方法を調査し、結果をMarkdownで出力してください。

## 調査対象
- Docker化の方法（Dockerfile、docker-compose）
- クラウドサービス：Render、Railway、Fly.io

## 比較観点
1. コスト（無料枠の有無と制限）
2. デプロイの難易度（初心者向けか）
3. CI/CDとの連携（GitHub Actions等）
4. データベース（PostgreSQL）のサポート
5. カスタムドメイン対応

## 追加で設計すること
- FastAPI用の最小Dockerfileの構成例
- docker-compose.ymlの構成例（app + db）
- GitHub Actionsによる自動デプロイのワークフロー概要

## 出力形式
- クラウドサービス比較表
- 推奨Dockerfileの雛形
- 推奨docker-compose.ymlの雛形
- 最終推奨サービスとその理由

結果は具体的かつ簡潔に。設定ファイルは実際に使えるコードで。
