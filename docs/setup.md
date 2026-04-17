# セットアップ

## 1. 目的

この文書は、開発を始める前に必要なローカル準備と、`models/`、`artifacts/`、`outputs/` の扱いを整理するものです。

## 2. 現時点の前提

- Windows 環境を前提にする
- Python 実行は `python` コマンドを前提にする
- NVIDIA GPU と CUDA が使える環境を前提にする
- 学習済みモデルはリポジトリへコミットしない
- ローカル起動は `.exe` を主導線にする

## 3. ディレクトリ用途

- `models/`: 推論に使う学習済み重みを置く
- `artifacts/`: 変換中の検証用成果物や一時的な比較出力を置く
- `outputs/`: 手動確認で保存した出力画像を置く

これらは大きなバイナリを含みやすいため、`.gitignore` で除外している。

## 4. モデル取得方針

現時点では採用モデルを最終確定していないため、固定のダウンロード URL や取得コマンドはまだ定義しない。

- MVP 候補は `docs/technical-design.md` にあるとおり Real-ESRGAN 系を中心に検討する
- 採用モデルを確定したら、入手元 URL、ライセンス、配置先、必要なら検証手順をこの文書へ追記する
- 認証が必要な配布元を使う場合は、必要な環境変数やログイン手順もこの文書へ追記する

## 5. 配置ルール

- 学習済み重みは `models/` 配下へ置く
- 検証用の生成物は `artifacts/` 配下へ置く
- 手動保存した出力例は `outputs/` 配下へ置く
- 生成物の命名規則やサブディレクトリ構成を決めたら、この文書へ追記する

## 6. 文書更新ルール

モデルの取得元、配置ルール、必要な認証情報、成果物の扱いを変えた場合は、この文書と `AGENTS.md` を一緒に更新する。

## 7. Windows exe ビルド手順

### 7.1 方針

- ローカル PC に Python が入っていない利用者でも起動できるように、`PyInstaller` の `onedir` でランタイムを同梱する
- 現時点ではインストーラー作成や配布自動化は対象外

### 7.2 ビルド

リポジトリ直下で次を実行する。

```powershell
python -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```

### 7.3 起動確認

ビルド後は次の exe を起動する。

```powershell
.\dist\image-to-hires\image-to-hires.exe
```

### 7.4 成果物

- `build/`: PyInstaller 作業ディレクトリ（中間生成物）
- `dist/image-to-hires/`: 配布前確認用の exe 一式
