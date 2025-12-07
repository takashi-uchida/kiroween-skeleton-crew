"""Worktree内でKiroを実行"""
import subprocess
from pathlib import Path
from typing import Dict, Optional


class KiroInvoker:
    """Worktree内でKiroを実行"""
    
    def __init__(self, kiro_command: str = "kiro-cli"):
        self.kiro_command = kiro_command
    
    def invoke(self, worktree_path: Path, task: Dict, mode: str = "auto") -> Dict:
        """Kiroを呼び出してタスクを実行
        
        Args:
            worktree_path: Worktreeのパス
            task: タスク情報
            mode: 実行モード ('auto', 'manual', 'api')
        """
        if mode == "auto":
            return self._invoke_auto(worktree_path, task)
        elif mode == "manual":
            return self._invoke_manual(worktree_path, task)
        elif mode == "api":
            return self._invoke_api(worktree_path, task)
        else:
            raise ValueError(f"Unknown mode: {mode}")
    
    def _invoke_auto(self, worktree_path: Path, task: Dict) -> Dict:
        """自動モード: Kiro CLIを呼び出し"""
        context_file = worktree_path / ".kiro/current-task.md"
        
        if not context_file.exists():
            raise FileNotFoundError(f"Task context not found: {context_file}")
        
        # Kiro CLIを呼び出し
        result = subprocess.run([
            self.kiro_command, "chat",
            "--message", f"現在のタスク({context_file})を実装してください",
            "--non-interactive"
        ], cwd=worktree_path, capture_output=True, text=True, timeout=300)
        
        return {
            "mode": "auto",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "success": result.returncode == 0
        }
    
    def _invoke_manual(self, worktree_path: Path, task: Dict) -> Dict:
        """手動モード: ユーザーに指示を表示"""
        context_file = worktree_path / ".kiro/current-task.md"
        
        print(f"\n{'='*60}")
        print(f"Task {task['id']}: {task['title']}")
        print(f"{'='*60}")
        print(f"\nWorktree: {worktree_path}")
        print(f"Context: {context_file}")
        print(f"\n次のコマンドを実行してください:")
        print(f"  cd {worktree_path}")
        print(f"  kiro-cli chat")
        print(f"\n実装が完了したら、このスクリプトを続行してください。")
        
        input("\nEnterキーを押して続行...")
        
        return {
            "mode": "manual",
            "success": True,
            "message": "Manual execution completed"
        }
    
    def _invoke_api(self, worktree_path: Path, task: Dict) -> Dict:
        """APIモード: Kiro APIを呼び出し（将来の実装）"""
        # TODO: Kiro APIが利用可能になったら実装
        raise NotImplementedError("API mode not yet implemented")
