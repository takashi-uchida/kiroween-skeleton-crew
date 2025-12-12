#!/usr/bin/env python3
"""
自動worktreeクリーンアップスクリプト

古いworktreeや孤立したブランチを自動的にクリーンアップします。
"""
import os
import sys
import subprocess
import argparse
from datetime import datetime, timedelta
from pathlib import Path


def run_command(cmd, capture_output=True, check=True):
    """コマンドを実行"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=capture_output, 
            text=True, check=check
        )
        return result.stdout.strip() if capture_output else None
    except subprocess.CalledProcessError as e:
        if check:
            print(f"エラー: {cmd}")
            print(f"出力: {e.stdout}")
            print(f"エラー: {e.stderr}")
            raise
        return None


def get_worktree_info():
    """worktree情報を取得"""
    output = run_command("git worktree list --porcelain")
    worktrees = []
    current = {}
    
    for line in output.split('\n'):
        if line.startswith('worktree '):
            if current:
                worktrees.append(current)
            current = {'path': line.split(' ', 1)[1]}
        elif line.startswith('HEAD '):
            current['head'] = line.split(' ', 1)[1]
        elif line.startswith('branch '):
            current['branch'] = line.split(' ', 1)[1]
        elif line == 'detached':
            current['detached'] = True
    
    if current:
        worktrees.append(current)
    
    return worktrees


def get_old_worktrees(days=7):
    """指定日数より古いworktreeを取得"""
    worktrees = get_worktree_info()
    old_worktrees = []
    cutoff_date = datetime.now() - timedelta(days=days)
    
    for wt in worktrees:
        path = Path(wt['path'])
        if not path.exists():
            old_worktrees.append(wt)
            continue
            
        # メインworktreeはスキップ
        if path.name == '.':
            continue
            
        # 最終更新時間をチェック
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            if mtime < cutoff_date:
                old_worktrees.append(wt)
        except OSError:
            old_worktrees.append(wt)
    
    return old_worktrees


def cleanup_worktree(worktree_path, force=False):
    """worktreeをクリーンアップ"""
    try:
        cmd = f"git worktree remove {worktree_path}"
        if force:
            cmd += " --force"
        
        run_command(cmd)
        print(f"✓ 削除: {worktree_path}")
        return True
    except subprocess.CalledProcessError:
        if not force:
            return cleanup_worktree(worktree_path, force=True)
        print(f"✗ 削除失敗: {worktree_path}")
        return False


def cleanup_orphaned_branches():
    """孤立したブランチを削除"""
    # リモートで削除されたブランチを取得
    try:
        run_command("git remote prune origin")
        
        # マージ済みのfeatureブランチを削除
        merged_branches = run_command(
            "git branch --merged main | grep 'feature/' | grep -v '\\*'"
        )
        
        if merged_branches:
            for branch in merged_branches.split('\n'):
                branch = branch.strip()
                if branch:
                    try:
                        run_command(f"git branch -d {branch}")
                        print(f"✓ ブランチ削除: {branch}")
                    except subprocess.CalledProcessError:
                        print(f"✗ ブランチ削除失敗: {branch}")
    
    except subprocess.CalledProcessError:
        pass


def main():
    parser = argparse.ArgumentParser(description="Worktreeとブランチの自動クリーンアップ")
    parser.add_argument("--days", type=int, default=7, 
                       help="指定日数より古いworktreeを削除 (デフォルト: 7)")
    parser.add_argument("--dry-run", action="store_true",
                       help="実際には削除せず、削除対象を表示")
    parser.add_argument("--force", action="store_true",
                       help="強制削除")
    parser.add_argument("--branches", action="store_true",
                       help="孤立したブランチも削除")
    
    args = parser.parse_args()
    
    # Gitリポジトリかチェック
    try:
        run_command("git rev-parse --git-dir")
    except subprocess.CalledProcessError:
        print("エラー: Gitリポジトリではありません")
        sys.exit(1)
    
    print(f"🧹 Worktreeクリーンアップ開始 ({args.days}日以上前)")
    
    # 古いworktreeを取得
    old_worktrees = get_old_worktrees(args.days)
    
    if not old_worktrees:
        print("✓ クリーンアップ対象のworktreeはありません")
    else:
        print(f"📋 {len(old_worktrees)}個のworktreeが見つかりました:")
        
        for wt in old_worktrees:
            path = wt['path']
            branch = wt.get('branch', 'detached')
            print(f"  - {path} (ブランチ: {branch})")
        
        if args.dry_run:
            print("🔍 ドライラン: 実際の削除は行いません")
        else:
            print("\n🗑️  削除を開始...")
            for wt in old_worktrees:
                cleanup_worktree(wt['path'], args.force)
    
    # ブランチクリーンアップ
    if args.branches:
        print("\n🌿 ブランチクリーンアップ開始")
        if args.dry_run:
            print("🔍 ドライラン: 実際の削除は行いません")
        else:
            cleanup_orphaned_branches()
    
    print("\n✨ クリーンアップ完了")


if __name__ == "__main__":
    main()
