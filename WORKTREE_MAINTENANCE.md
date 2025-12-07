# Worktree Maintenance Guide

NecroCodeではタスクごとに `worktrees/` 配下へ Git worktree を切って作業するユースケースが多いため、放置すると手元に大量の worktree が溜まってしまいます。このファイルでは、リポジトリに追加した `scripts/worktree_cleanup.py` を使って簡単に棚卸し＆クリーンアップする手順をまとめます。

## 使い方

```bash
# 概況を表示（デフォルトはドライラン）
python3 scripts/worktree_cleanup.py

# JSONで取得
python3 scripts/worktree_cleanup.py --json

# ブランチが存在しない task-* worktree を削除（確認のみ）
python3 scripts/worktree_cleanup.py --prune-stale

# 実際に削除 (--apply) + 強制削除 (--force)
python3 scripts/worktree_cleanup.py --prune-stale --apply --force

# ブランチが存在していても task-* をすべて片付けたい場合
python3 scripts/worktree_cleanup.py --prune-stale --include-active-task --apply
```

## 出力例

```
Worktree summary for /Users/takashi/Documents/kiroween-skeleton-crew
PATH                                                         BRANCH                        CATEGORY   STALE
/Users/.../kiroween-skeleton-crew                           main                          root       no
/Users/.../worktrees/task-5                                 feature/task-5                task       yes
/Users/.../worktrees/task-7                                 feature/task-7                task       no
```

`STALE` が `yes` の行は参照ブランチが `git show-ref` で見つからないか、ディレクトリ自体が既に消えているworktreeです。`--prune-stale` を指定すると、それら `task-*` worktree が削除対象に選ばれ、`--apply` を付けた場合のみ実際に `git worktree remove` が実行されます。

## 注意事項

- `task-*` 以外の worktree は情報表示のみで、自動削除の対象外です（必要に応じて手動で `git worktree remove <path>` を実行してください）。
- すべての削除操作は `git worktree remove` を内部的に呼び出します。作業途中の変更がある worktree は削除前にコミットまたは退避してください。
- リモート追跡ブランチのみ存在するケースでは `branch` 列が空白になることがあります。その場合は `--include-active-task` を併用すると強制的に削除対象へ含められます。
