# 概要

## 目的

- この PR で何を解決するのか
- なぜ今この変更が必要なのか

## 変更内容

- 主要な変更点を箇条書きで記載
- UI、`domain/usecase`、`infrastructure` のどこに影響があるかも必要に応じて記載

## 変更理由

- どういう判断でこの実装や設計を選んだか
- 代替案があれば、採用しなかった理由も簡潔に記載

# 設計影響

## アーキテクチャへの影響

- [ ] `ui / domain / infrastructure` の責務分離を崩していない
- [ ] ユースケースは `domain/usecase` に集約されている
- [ ] `infrastructure` から `ui` を参照していない
- [ ] 値オブジェクトで閉じ込めるべき不変条件を適切に扱っている
- [ ] ガード節で早期に弾くべき入力検証を実装している

## 文書への影響

- [ ] 文書更新なし
- [ ] `docs/overview.md` を更新した
- [ ] `docs/requirements.md` を更新した
- [ ] `docs/technical-design.md` を更新した
- [ ] `docs/architecture.md` を更新した
- [ ] `docs/implementation-plan.md` を更新した
- [ ] `docs/subagent-guide.md` を更新した
- [ ] `docs/coding-standards.md` を更新した
- [ ] `docs/unit-test-guidelines.md` を更新した
- [ ] `docs/review-guide.md` を更新した
- [ ] `AGENTS.md` を更新した

# 確認項目

## 動作確認

- [ ] 未確認
- [ ] 手動確認済み
- [ ] Windows 上で起動確認済み
- [ ] ファイル選択で確認した
- [ ] ドラッグアンドドロップで確認した
- [ ] 起動引数で確認した

## 変換確認

- [ ] 2x を確認した
- [ ] 3x を確認した
- [ ] 4x を確認した
- [ ] 保存を確認した
- [ ] 異常系を確認した

## GPU 確認

- [ ] GPU 未使用の変更
- [ ] CUDA 利用環境で確認した
- [ ] `torch.cuda.is_available()` 前提の処理に影響なし
- [ ] GPU 依存コードは未確認

# テスト

## UnitTest

- [ ] 追加なし
- [ ] 追加した
- [ ] 既存テストのみ実行した
- [ ] 未実行

### 実行コマンド

```bash
# 例:
python -m pytest
```

### 結果

- 実行結果を記載

## Lint

- [ ] 影響なし
- [ ] 実行した
- [ ] 未実行

### 実行コマンド

```bash
# 例:
python -m ruff check .
```

### 結果

- 実行結果を記載

# リスク

## 想定される影響

- どの機能に影響しうるか
- 特に UI、状態遷移、倍率分岐、保存、GPU 依存部分のリスクを記載

## 未対応事項

- この PR で意図的にやっていないこと
- 後続 PR に回すこと

# レビューで見てほしい点

- 特に見てほしい箇所
- 迷いがあった設計ポイント
- レビュー観点の希望
