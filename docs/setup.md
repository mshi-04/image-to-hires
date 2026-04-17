# セットアップ

## 1. 目的

この文書は、開発を始める前に必要なローカル準備と、`models/`、`artifacts/`、`outputs/` の扱いを整理するものです。

## 2. 現時点の前提

- Windows 環境を前提にする
- Python 実行は `python` コマンドを前提にする
- NVIDIA GPU と CUDA が使える環境を前提にする
- 学習済みモデルはリポジトリへコミットしない

## 3. ディレクトリ用途

- `models/`: 推論に使う学習済み重みを置く
- `artifacts/`: 変換中の検証用成果物や一時的な比較出力を置く
- `outputs/`: 手動確認で保存した出力画像を置く

これらは大きなバイナリを含みやすいため、`.gitignore` で除外している。

## 4. モデル取得方針

現在は Real-CUGAN (ncnn-vulkan) を採用している。以下の手順でバイナリとモデルを取得して配置する。

1. [Real-CUGAN の GitHub Releases](https://github.com/nihui/realcugan-ncnn-vulkan/releases) から Windows 版バイナリ（例: `realcugan-ncnn-vulkan-...-windows.zip`）をダウンロードする。
2. ZIP を解凍し、以下のディレクトリ構成になるように配置する。

## 5. 配置ルール

- 推論用バイナリは `bin/` 配下へ置く。
  - 例: `bin/realcugan/realcugan-ncnn-vulkan.exe`
- 学習済み重みは `models/` 配下へ置く。
  - 例: `models/realcugan/models-se/` 等 (解凍したモデル構成をそのまま配置)
- 検証用の生成物は `artifacts/` 配下へ置く
- 手動保存した出力例は `outputs/` 配下へ置く
- 生成物の命名規則やサブディレクトリ構成を決めたら、この文書へ追記する

## 6. 文書更新ルール

モデルの取得元、配置ルール、必要な認証情報、成果物の扱いを変えた場合は、この文書と `AGENTS.md` を一緒に更新する。
