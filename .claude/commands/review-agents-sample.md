$ARGUMENTS がある場合、https://github.com/YasushiMatsushima/AI-MULTI-AGENT
の該当番号のPRの品質を改善してください。
$ARGUMENTS がない場合、現在のコードの品質を改善してください。

事前準備: Shift+Tab で acceptEdits モードに切り替えてから実行することを推奨。

以下の3ステップを順番に実行してください。

  1. python-code-reviewer サブエージェントでコードレビューを行う
  2. test-engineer サブエージェントでテストを作成・実行する（レビュー結果を踏まえる）
  3. doc-writer サブエージェントで docstring と README.md を生成する（レビュー結果とテスト結果を踏まえる）
