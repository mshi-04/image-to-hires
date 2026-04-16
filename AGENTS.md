# AGENTS.md

## 役割

このファイルは、このリポジトリで AI エージェントや実装者が最初に見る文書の入口です。

詳細な方針や仕様は個別文書に分けて記載します。ここには前提、文書の地図、最小限の横断ルールだけを書きます。

## 前提

このプロジェクトの現時点の前提は次の通りです。

- Windows 向け GUI アプリを作る
- NVIDIA GPU 前提で進める
- Python は 3 系を使う
- MVP は画像 1 枚の 2 倍、3 倍、4 倍拡大に対応する
- 入力はファイル選択、ドラッグアンドドロップ、起動引数に対応する
- アーキテクチャは `ui / domain / infrastructure` を基本にする
- ユースケースは `domain/usecase` に置く
- 将来の複数画像対応を見据えて実装する

## 文書マップ

- `docs/overview.md`: プロジェクトの目的、MVP 範囲、現在の大方針
- `docs/requirements.md`: 機能要件、非機能要件、入出力要件、受け入れ条件
- `docs/technical-design.md`: 言語、GUI、推論方式、GPU 前提、モデル利用方針
- `docs/architecture.md`: ディレクトリ構成、責務分離、データの流れ、将来拡張の見通し
- `docs/implementation-plan.md`: 実装フェーズ、優先順位、判断基準、将来タスク
- `docs/setup.md`: モデル配置、成果物ディレクトリ、開発開始前の準備手順
- `docs/subagent-guide.md`: サブエージェントの使いどころ、分担、統合方法
- `docs/coding-standards.md`: 命名、責務分離、例外処理、状態管理、コメント方針
- `docs/unit-test-guidelines.md`: UnitTest の対象範囲、モック方針、GPU 依存コードの扱い、命名規則
- `docs/review-guide.md`: PR レビュー時の観点、優先順位、確認手順
- `docs/git-guidelines.md`: コミット、PR、レビュー応答、CodeRabbit 対応の運用

## 横断 Rules

- MVP の範囲を勝手に広げない
- 変更内容に対応する文書を更新する
- 文書同士の内容がずれたら、その場で整合を取る
- 詳細な判断は各文書の `Rules` を優先する
