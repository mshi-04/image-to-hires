# AGENTS.md

## 役割

このファイルは、このリポジトリで AI エージェントや実装者が最初に見る文書の入口です。

詳細な方針や仕様は個別文書に分けて記載します。ここには要点と文書の地図だけを書きます。

## 最初に確認すること

このプロジェクトの現時点の前提は次の通りです。

- Windows 向け GUI アプリを作る
- NVIDIA GPU 前提で進める
- Python は 3 系を使う
- MVP は画像 1 枚の 2 倍、3 倍、4 倍拡大に対応する
- 入力はファイル選択、ドラッグアンドドロップ、起動引数に対応する
- アーキテクチャは `ui / domain / infrastructure` を基本にする
- ユースケースは `domain/usecase` に置く
- 将来の複数画像対応を見据えて実装する

前提を変える場合は、対応する詳細文書も更新すること。

## 文書マップ

### 全体像

- `docs/overview.md`
- プロジェクトの目的、MVP 範囲、現在の大方針をまとめる文書

### 要件

- `docs/requirements.md`
- 機能要件、非機能要件、入出力要件、受け入れ条件を定義する文書

### 技術方針

- `docs/technical-design.md`
- 言語、GUI、推論方式、GPU 前提、モデル利用方針を定義する文書

### アーキテクチャ

- `docs/architecture.md`
- ディレクトリ構成、責務分離、データの流れ、将来拡張の見通しを記載する文書

### 実装計画

- `docs/implementation-plan.md`
- 実装フェーズ、優先順位、判断基準、将来タスクを整理する文書

### サブエージェント運用

- `docs/subagent-guide.md`
- サブエージェントをいつ使うか、どう分担するか、どう統合するかを定義する文書

### コーディング規約

- `docs/coding-standards.md`
- 命名、責務分離、例外処理、状態管理、コメント方針などの実装ルールを定義する文書

### UnitTest 方針

- `docs/unit-test-guidelines.md`
- ユニットテストの対象範囲、モック方針、GPU 依存コードの扱い、命名規則を定義する文書

### レビューガイド

- `docs/review-guide.md`
- PR レビュー時の観点、優先順位、確認手順を定義する文書

## 読み方

- 何を作るかを確認したいときは `docs/overview.md` と `docs/requirements.md` を読む
- 技術選定や外部モデルの扱いを確認したいときは `docs/technical-design.md` を読む
- ファイル構成や責務の切り方を確認したいときは `docs/architecture.md` を読む
- 着手順や実装順序を確認したいときは `docs/implementation-plan.md` を読む
- サブエージェントをどう使うか確認したいときは `docs/subagent-guide.md` を読む
- コードの書き方を確認したいときは `docs/coding-standards.md` を読む
- UnitTest の書き方を確認したいときは `docs/unit-test-guidelines.md` を読む
- レビュー観点を確認したいときは `docs/review-guide.md` を読む

## 変更ルール

- 仕様を変えたら `docs/requirements.md` を更新する
- 技術選定を変えたら `docs/technical-design.md` を更新する
- 構造を変えたら `docs/architecture.md` を更新する
- 進め方を変えたら `docs/implementation-plan.md` を更新する
- サブエージェント運用を変えたら `docs/subagent-guide.md` を更新する
- コーディング規約を変えたら `docs/coding-standards.md` を更新する
- UnitTest 方針を変えたら `docs/unit-test-guidelines.md` を更新する
- レビュー方針を変えたら `docs/review-guide.md` を更新する
- 文書同士の内容がずれたら放置せず、その場で整合を取る

## 実装時の基本ルール

- MVP の範囲を勝手に広げない
- UI と推論ロジックを混ぜない
- 画像の読み込み経路を分岐させすぎない
- ガード節を積極的に使う
- まず動く最小構成を作り、その上で整える
- ただし将来の複数画像対応を壊す近道は避ける
- 並列化できる作業は、サブエージェントの利用を優先的に検討する
