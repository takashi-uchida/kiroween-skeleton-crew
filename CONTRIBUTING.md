# コントリビューションガイド

NecroCodeへのコントリビューションをありがとうございます！

## 開発環境のセットアップ

### 1. リポジトリをフォーク

GitHubでリポジトリをフォークしてください。

### 2. クローンとセットアップ

```bash
git clone https://github.com/YOUR_USERNAME/kiroween-skeleton-crew.git
cd kiroween-skeleton-crew

# 開発用依存関係をインストール
pip install -e .
pip install -r requirements-dev.txt
```

### 3. ブランチを作成

```bash
git checkout -b feature/your-feature-name
```

## コーディング規約

### Pythonスタイル

- PEP 8に従う
- Black でフォーマット
- Flake8 でリント

```bash
# フォーマット
black necrocode/

# リント
flake8 necrocode/
```

### 命名規則

- **関数/変数**: `snake_case`
- **クラス**: `PascalCase`
- **定数**: `UPPER_CASE`
- **プライベート**: `_leading_underscore`

### ドキュメント

- 全ての公開関数にdocstringを追加
- 日本語コメントOK（コード内）
- ドキュメントは日本語優先

```python
def execute_task(task_id: str) -> Dict:
    """タスクを実行
    
    Args:
        task_id: タスクID
    
    Returns:
        実行結果の辞書
    """
    pass
```

## テスト

### テストの実行

```bash
# 全テスト
pytest tests/

# カバレッジ付き
pytest tests/ --cov=necrocode --cov-report=html

# 特定のテスト
pytest tests/test_worktree_manager.py
```

### テストの書き方

```python
def test_worktree_creation():
    """Worktree作成のテスト"""
    mgr = WorktreeManager(Path("."))
    worktree = mgr.create_worktree("1", "feature/test")
    
    assert worktree.exists()
    assert worktree.name == "task-1"
```

## プルリクエスト

### 1. 変更をコミット

```bash
git add .
git commit -m "feat: 新機能の追加"
```

コミットメッセージの形式:
- `feat:` - 新機能
- `fix:` - バグ修正
- `docs:` - ドキュメント
- `test:` - テスト追加
- `refactor:` - リファクタリング
- `chore:` - その他

### 2. プッシュ

```bash
git push origin feature/your-feature-name
```

### 3. PRを作成

GitHubでPRを作成してください。

### PRのチェックリスト

- [ ] テストが通る
- [ ] ドキュメントを更新
- [ ] コーディング規約に従っている
- [ ] 破壊的変更がある場合は明記
- [ ] 関連するIssueをリンク

## Git Worktreeを使った開発

NecroCode自身を使って開発できます！

```bash
# 改善タスクを作成
necrocode plan "新機能を追加" --project my-feature

# Worktreeで並列開発
necrocode execute my-feature --workers 2 --mode manual
```

## 質問・サポート

- **Issue**: バグ報告や機能リクエスト
- **Discussion**: 質問や議論
- **PR**: コード貢献

## ライセンス

コントリビューションはMITライセンスの下で公開されます。

## 行動規範

- 敬意を持って接する
- 建設的なフィードバック
- 多様性を尊重

---

貢献をお待ちしています！🚀
