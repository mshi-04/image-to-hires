# アーキテクチャ設計

## Rules

- 層の責務と依存方向はこの文書で固定する
- 入力経路と推論経路は集約し、UI と推論ロジックの混在を許さない
- 構造を変えたら `docs/coding-standards.md` と `docs/unit-test-guidelines.md` も確認する

## 1. 基本方針

最初から責務を分ける。単一画像しか扱わない段階でも、UI と推論を混ぜない。

後で複数画像対応を入れるとき、単一画像処理の流れをジョブキューへ差し替えやすい構造にする。

アーキテクチャの大分類は `ui / domain / infrastructure` とする。

ユースケースは `domain/usecase` に置く。

## 2. 想定ディレクトリ構成

```text
src/
  ui/
    windows/
    widgets/
  domain/
    entities/
    value_objects/
    usecase/
    ports/
    services/
  infrastructure/
    image_io/
    inference/
    model_store/
    persistence/
  main.py
```

## 3. 各層の責務

### ui

- メインウィンドウ
- ドラッグアンドドロップ
- ボタン操作
- プレビュー表示
- 状態表示

### domain

- エンティティ
- 値オブジェクト
- ユースケース
- ポート
- ドメインサービス
- アプリ固有の状態遷移ルール

### infrastructure

- 画像読み込みと保存
- PyTorch + CUDA を使った推論実装
- モデル重みの解決とロード
- 外部ライブラリやファイルシステムとの接続

## 4. データの流れ

1. UI が画像読み込み要求を出す
2. `domain/usecase` が入力を受けて検証する
3. 必要な値オブジェクトを組み立てる
4. usecase が port を通して infrastructure を呼ぶ
5. infrastructure が画像 I/O や推論を実行する
6. usecase が結果をドメインの戻り値へまとめる
7. UI が結果を表示し、保存要求を受ける

## 5. 設計ルール

- UI から直接 PyTorch、モデル、ファイル保存の詳細を触らない
- ファイル選択、ドラッグアンドドロップ、起動引数は同じ読み込み経路へ流す
- 推論や保存の入口は usecase にまとめる
- 不変条件はできるだけ値オブジェクトへ閉じ込める
- 入力検証ではガード節を積極的に使う
- 将来の複数画像対応を見据えて、画像 1 枚の処理を独立した単位として扱う

## 6. 将来拡張の見通し

複数画像対応をするときは、主に `domain/usecase` 側へジョブキューの責務を追加する。

`infrastructure` は、単一画像の処理単位をそのまま流用できる形を保つ。
