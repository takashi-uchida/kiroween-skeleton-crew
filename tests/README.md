# Tests

NecroCodeのテストスイートです。

## テスト構成

- `test_worktree_manager.py` - Git Worktree管理のテスト
- `test_worktree_pool_manager.py` - Worktreeプール管理のテスト  
- `test_integration.py` - 統合テスト

## 実行方法

```bash
# 全テスト実行
pytest tests/

# 特定のテスト実行
pytest tests/test_worktree_manager.py

# カバレッジ付き実行
pytest tests/ --cov=necrocode
```

## 検証スクリプト

開発時の詳細な検証は `scripts/verification/` を参照してください。
