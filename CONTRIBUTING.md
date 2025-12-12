# Contributing to NecroCode

NecroCodeへの貢献をありがとうございます！

## 開発環境のセットアップ

### 1. リポジトリをクローン

```bash
git clone https://github.com/takashi-uchida/kiroween-skeleton-crew.git
cd kiroween-skeleton-crew
```

### 2. 開発環境をセットアップ

```bash
make setup-dev
```

これにより以下が実行されます：
- 依存関係のインストール
- pre-commitフックの設定
- 開発ツールのセットアップ

### 3. 動作確認

```bash
make test
python -m necrocode.cli --help
```

## 開発ワークフロー

### ブランチ作成

```bash
git checkout -b feature/your-feature-name
```

### コード変更

1. コードを変更
2. テストを追加/更新
3. フォーマットとリント

```bash
make format
make lint
make test
```

### コミット

```bash
git add .
git commit -m "feat: 新機能の説明"
```

pre-commitフックが自動的に実行されます。

### プルリクエスト

```bash
git push origin feature/your-feature-name
gh pr create --title "feat: 新機能" --body "詳細な説明"
```

## 開発コマンド

```bash
make help              # 利用可能なコマンドを表示
make test              # テスト実行
make test-watch        # テスト監視モード
make lint              # リント実行
make format            # コードフォーマット
make format-check      # フォーマットチェック
make clean             # 一時ファイル削除
make cleanup-worktrees # 古いworktree削除
make ci                # CI/CDチェック
```

## コーディング規約

### Python

- **フォーマット**: Black（自動）
- **リント**: flake8
- **型チェック**: mypy
- **インポート順序**: isort（自動）

### コミットメッセージ

```
type: 簡潔な説明

詳細な説明（必要に応じて）

- 変更点1
- 変更点2
```

**Type:**
- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメント
- `style`: フォーマット
- `refactor`: リファクタリング
- `test`: テスト
- `chore`: その他

## テスト

### テスト実行

```bash
# 全テスト
make test

# 特定のテスト
pytest tests/test_cli.py -v

# カバレッジ付き
pytest tests/ --cov=necrocode --cov-report=html
```

### テスト作成

- `tests/` ディレクトリにテストファイルを作成
- ファイル名は `test_*.py`
- 関数名は `test_*`

## Worktree管理

### 自動クリーンアップ

```bash
# ドライラン（確認のみ）
make cleanup-worktrees-dry

# 実際にクリーンアップ
make cleanup-worktrees

# ブランチも含めて全クリーンアップ
make cleanup-all
```

### 手動クリーンアップ

```bash
# 特定のworktreeを削除
git worktree remove worktrees/task-name

# 強制削除
git worktree remove worktrees/task-name --force

# ブランチも削除
git branch -D feature/task-name
```

## CI/CD

### GitHub Actions

- **テスト**: プッシュ時に自動実行
- **リント**: 別ジョブで実行
- **クリーンアップ**: 毎日自動実行

### ローカルでCI確認

```bash
make ci
```

## トラブルシューティング

### よくある問題

1. **pre-commitエラー**
   ```bash
   pre-commit run --all-files
   ```

2. **worktreeエラー**
   ```bash
   make cleanup-worktrees
   ```

3. **テストエラー**
   ```bash
   make clean
   make test
   ```

## 質問・サポート

- Issues: GitHub Issues
- ディスカッション: GitHub Discussions
- ドキュメント: `.kiro/steering/`
