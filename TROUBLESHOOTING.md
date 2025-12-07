# トラブルシューティングガイド

## よくある問題と解決方法

### インストール関連

#### Q1: `necrocode: command not found`

**原因**: setup.pyでインストールされていない

**解決方法**:
```bash
cd kiroween-skeleton-crew
pip install -e .

# 確認
necrocode --help
```

#### Q2: `ModuleNotFoundError: No module named 'click'`

**原因**: 依存関係がインストールされていない

**解決方法**:
```bash
pip install click
# または
pip install -e .
```

### 実行関連

#### Q3: `エラー: プロジェクト 'xxx' が見つかりません`

**原因**: タスク定義ファイルが存在しない

**解決方法**:
```bash
# プロジェクト一覧を確認
necrocode status

# タスク定義ファイルを確認
ls -la .kiro/tasks/

# 新規作成
necrocode plan "プロジェクト説明" --project xxx --no-llm
```

#### Q4: Worktreeが作成できない

**エラー**:
```
fatal: 'worktrees/task-1' already exists
```

**原因**: 以前のworktreeが残っている

**解決方法**:
```bash
# 全worktreeをクリーンアップ
necrocode cleanup --force

# または手動で削除
git worktree remove worktrees/task-1 --force
```

#### Q5: タスクが実行されない（手動モード）

**症状**: Enterキーを押しても次に進まない

**原因**: 非対話的な環境で実行している

**解決方法**:
```bash
# 自動モードを使用（実験的）
necrocode execute project --mode auto

# または、手動で各worktreeで作業
cd worktrees/task-1
# 実装
git add .
git commit -m "feat: task 1"
cd ../..
```

### Git関連

#### Q6: ブランチが残っている

**症状**: 古いfeature/task-*ブランチが大量にある

**解決方法**:
```bash
# ローカルブランチを確認
git branch | grep "feature/task-"

# 削除
git branch -D feature/task-1-*

# 一括削除
git branch | grep "feature/task-" | xargs git branch -D
```

#### Q7: Worktreeのブランチが競合

**エラー**:
```
fatal: 'feature/task-1-xxx' is already checked out at 'worktrees/task-1'
```

**解決方法**:
```bash
# worktreeを削除
git worktree remove worktrees/task-1 --force

# ブランチを削除
git branch -D feature/task-1-xxx

# 再実行
necrocode execute project
```

### パフォーマンス関連

#### Q8: 実行が遅い

**原因**: ワーカー数が多すぎる、またはタスクが重い

**解決方法**:
```bash
# ワーカー数を減らす
necrocode execute project --workers 1

# 進捗表示を無効化
necrocode execute project --no-progress
```

#### Q9: メモリ不足

**症状**: プロセスが強制終了される

**解決方法**:
```bash
# ワーカー数を減らす
necrocode execute project --workers 2

# タスクを分割して実行
# （大きなタスクを小さく分ける）
```

### タスク定義関連

#### Q10: タスクの依存関係が解決されない

**症状**: 依存タスクが完了していないのに実行される

**原因**: tasks.jsonの依存関係が正しくない

**解決方法**:
```json
{
  "tasks": [
    {
      "id": "1",
      "dependencies": []  // 依存なし
    },
    {
      "id": "2",
      "dependencies": ["1"]  // Task 1に依存（文字列の配列）
    }
  ]
}
```

#### Q11: LLMでタスク生成が失敗

**エラー**:
```
エラー: LLMでのタスク生成に失敗しました
```

**解決方法**:
```bash
# フォールバックを使用
necrocode plan "説明" --project xxx --no-llm

# または手動でtasks.jsonを作成
mkdir -p .kiro/tasks/xxx
vi .kiro/tasks/xxx/tasks.json
```

### Kiro統合関連

#### Q12: Kiroが見つからない

**エラー**:
```
kiro-cli: command not found
```

**解決方法**:
```bash
# Kiroがインストールされているか確認
which kiro-cli

# インストール（Kiroのドキュメントに従う）
# ...

# 手動モードを使用
necrocode execute project --mode manual
```

#### Q13: Kiroの実行が失敗

**症状**: タスクが常に失敗する

**解決方法**:
```bash
# ログを確認
cat .kiro/logs/task-*.log

# 手動でworktreeに移動して確認
cd worktrees/task-1
kiro-cli chat
# エラーメッセージを確認
```

## デバッグ方法

### 詳細ログを有効化

```bash
# 環境変数を設定
export NECROCODE_DEBUG=1

# 実行
necrocode execute project
```

### Worktreeの状態を確認

```bash
# アクティブなworktreeを確認
git worktree list

# 特定worktreeの状態
cd worktrees/task-1
git status
git log --oneline -5
```

### タスクレジストリを確認

```bash
# レジストリファイルを確認
cat .kiro/registry/tasks.jsonl
cat .kiro/registry/events.jsonl
```

## エラーメッセージ一覧

### `fatal: Not a git repository`

**解決**: Gitリポジトリ内で実行してください

```bash
cd kiroween-skeleton-crew
necrocode execute project
```

### `PermissionError: [Errno 13] Permission denied`

**解決**: 書き込み権限を確認

```bash
chmod -R u+w .kiro/
chmod -R u+w worktrees/
```

### `JSONDecodeError: Expecting value`

**解決**: tasks.jsonの構文を確認

```bash
# JSONの検証
python3 -m json.tool .kiro/tasks/project/tasks.json
```

## サポート

### 問題が解決しない場合

1. **GitHubでIssueを作成**:
   https://github.com/takashi-uchida/kiroween-skeleton-crew/issues

2. **情報を含める**:
   - エラーメッセージ
   - 実行したコマンド
   - 環境情報（OS、Pythonバージョン）
   - tasks.jsonの内容

3. **ログを添付**:
   ```bash
   # ログを収集
   tar czf necrocode-logs.tar.gz .kiro/logs/ .kiro/registry/
   ```

## 予防策

### 定期的なクリーンアップ

```bash
# 週に1回実行
necrocode cleanup --force
git branch | grep "feature/task-" | xargs git branch -D
```

### バックアップ

```bash
# タスク定義をバックアップ
cp -r .kiro/tasks/ .kiro/tasks.backup/
```

### テスト実行

```bash
# 小さなプロジェクトでテスト
necrocode plan "テスト" --project test --no-llm
necrocode execute test --workers 1
necrocode cleanup
```

## 関連ドキュメント

- [TUTORIAL.md](TUTORIAL.md) - 基本的な使い方
- [QUICKSTART.md](QUICKSTART.md) - クイックスタート
- [README.md](README.md) - プロジェクト概要
