"""Kiro用のタスクコンテキスト生成"""
from pathlib import Path
from typing import Dict, List


class TaskContextGenerator:
    """Kiro用のタスクコンテキストを生成"""
    
    def generate(self, worktree_path: Path, task: Dict):
        """current-task.mdを生成"""
        context_file = worktree_path / ".kiro/current-task.md"
        context_file.parent.mkdir(parents=True, exist_ok=True)
        
        content = self._build_context(task)
        context_file.write_text(content, encoding="utf-8")
    
    def _build_context(self, task: Dict) -> str:
        """タスクコンテキストを構築"""
        return f"""# Task: {task['title']}

## Task ID
{task['id']}

## Description
{task['description']}

## Dependencies Completed
{self._format_dependencies(task.get('dependencies', []))}

## Files to Create/Modify
{self._format_files(task.get('files_to_create', []))}

## Acceptance Criteria
{self._format_criteria(task.get('acceptance_criteria', []))}

## Technical Context
- Type: {task.get('type', 'general')}
- Estimated Complexity: {task.get('complexity', 'medium')}

## Instructions for Kiro
このタスクを実装してください。受け入れ基準を全て満たすコードを作成し、
適切なテストを含めてください。
"""
    
    def _format_dependencies(self, deps: List[str]) -> str:
        """依存関係をフォーマット"""
        if not deps:
            return "なし"
        return "\n".join(f"- Task {dep}" for dep in deps)
    
    def _format_files(self, files: List[str]) -> str:
        """ファイルリストをフォーマット"""
        if not files:
            return "なし"
        return "\n".join(f"- `{f}`" for f in files)
    
    def _format_criteria(self, criteria: List[str]) -> str:
        """受け入れ基準をフォーマット"""
        if not criteria:
            return "なし"
        return "\n".join(f"- [ ] {c}" for c in criteria)
