# AGENTS.md

## 役割

このファイルは、このリポジトリで AI エージェントや実装者が最初に見る文書の入口です。

詳細な方針や仕様は個別文書に分けて記載します。ここには前提と文書の地図だけを書きます。

## 前提

このプロジェクトの現時点の前提は次の通りです。

- Windows 向け GUI アプリを作る
- NVIDIA GPU 前提で進める
- Python は 3 系を使う
- MVP は画像の 2 倍、3 倍、4 倍拡大と複数ファイルの順次処理に対応する
- 入力はファイル選択のみ対応する（ドラッグアンドドロップは対応しない）
- 出力は既定で入力と同じ拡張子を使い、`webp_lossless` 選択時は `.webp` で、同じフォルダに `-denoiseXx-upYx` を付けて保存する
- アーキテクチャは `ui / domain / infrastructure` を基本にする
- ユースケースは `domain/usecase` に置く
- 複数ファイルはキュー方式で順次処理する
- GPU 都合で複数画像の並列生成は採用しない
- 高速化は順次処理の範囲で行う（Real-CUGAN 実行設定、一時ファイル再利用、保存オーバーヘッド削減）

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

## Rules 文書

- `docs/rules/requirements.md`: 要件定義時の判断基準
- `docs/rules/coding-standards.md`: 実装時の判断基準
- `docs/rules/unit-test-guidelines.md`: UnitTest 作成時の判断基準
- `docs/rules/review-guide.md`: レビュー時の判断基準
- `docs/rules/git-guidelines.md`: Git と CodeRabbit 対応時の判断基準
