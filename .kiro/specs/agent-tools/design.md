# Agent Tools Design Document

## Overview

Agent Toolsは、Orchestrator Agent（Kiro）がタスク実行時に使用する専門化されたツール群です。各ツールはMCP (Model Context Protocol)を通じて提供され、特定の機能（実装、レビュー、テスト等）を実行します。

## Architecture

### System Context

```
┌─────────────────────────────────────────────────────────────┐
│                  NecroCode System                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Orchestrator Agent (Kiro)                    │  │
│  │                                                      │  │
│  │  ┌────────────────────────────────────────────────┐ │  │
│  │  │  Task Execution Logic                          │ │  │
│  │  │  - Read task from Task Registry                │ │  │
│  │  │  - Plan tool invocations                       │ │  │
│  │  │  - Chain tool calls                            │ │  │
│  │  │  - Handle errors and retries                   │ │  │
│  │  └────────────────────────────────────────────────┘ │  │
│  │                        │                            │  │
│  │         ┌──────────────┼──────────────┐             │  │
│  │         │              │              │             │  │
│  │    ┌────▼────┐   ┌────▼────┐   ┌────▼────┐        │  │
│  │    │Implement│   │ Review  │   │  Test   │        │  │
│  │    │  Tool   │   │  Tool   │   │  Tool   │        │  │
│  │    └─────────┘   └─────────┘   └─────────┘        │  │
│  │         │              │              │             │  │
│  └─────────┼──────────────┼──────────────┼─────────────┘  │
│            │              │              │                 │
│            │    MCP Protocol (JSON-RPC)  │                 │
│            │              │              │                 │
│  ┌─────────▼──────────────▼──────────────▼─────────────┐  │
│  │              MCP Tool Server                         │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │  │
│  │  │Implement │  │ Review   │  │  Test    │          │  │
│  │  │ Handler  │  │ Handler  │  │ Handler  │          │  │
│  │  └──────────┘  └──────────┘  └──────────┘          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Tools                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         MCP Tool Server                              │  │
│  │  - Tool registration                                 │  │
│  │  - Request routing                                   │  │
│  │  - Response formatting                               │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│         ┌─────────────────┼─────────────────┐               │
│         │                 │                 │               │
│  ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐      │
│  │Implementation│   │   Review    │   │    Test     │      │
│  │    Tool      │   │    Tool     │   │    Tool     │      │
│  └──────────────┘   └──────────────┘   └──────────────┘      │
│         │                 │                 │               │
│  ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐      │
│  │Refactoring  │   │Documentation│   │   Debug     │      │
│  │    Tool     │   │    Tool     │   │    Tool     │      │
│  └──────────────┘   └──────────────┘   └──────────────┘      │
│         │                 │                 │               │
│  ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐      │
│  │ Dependency  │   │ Performance │   │  Security   │      │
│  │    Tool     │   │    Tool     │   │    Tool     │      │
│  └──────────────┘   └──────────────┘   └──────────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Tools and Interfaces

### 1. Implementation Tool

コードを生成・実装するツール。

```python
class ImplementationTool:
    """コード実装ツール"""
    
    name = "implement_code"
    description = "Generate code based on task requirements"
    
    input_schema = {
        "type": "object",
        "properties": {
            "task_description": {
                "type": "string",
                "description": "Detailed task description"
            },
            "acceptance_criteria": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of acceptance criteria"
            },
            "workspace_path": {
                "type": "string",
                "description": "Path to workspace"
            },
            "context_files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Relevant context files"
            }
        },
        "required": ["task_description", "workspace_path"]
    }
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """ツールを実行"""
        try:
            # 1. タスクを分析
            analysis = self._analyze_task(
                params["task_description"],
                params.get("acceptance_criteria", [])
            )
            
            # 2. コンテキストを読み込み
            context = self._load_context(
                params["workspace_path"],
                params.get("context_files", [])
            )
            
            # 3. コードを生成
            implementation = await self._generate_code(
                analysis,
                context
            )
            
            # 4. ファイルに書き込み
            files_changed = self._write_files(
                params["workspace_path"],
                implementation.files
            )
            
            # 5. diffを生成
            diff = self._generate_diff(
                params["workspace_path"],
                files_changed
            )
            
            return ToolResult(
                success=True,
                data={
                    "files_changed": files_changed,
                    "diff": diff,
                    "implementation_notes": implementation.notes,
                    "duration_seconds": implementation.duration
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                suggestions=self._get_error_suggestions(e)
            )

### 2. Review Tool

コードレビューを実行するツール。

```python
class ReviewTool:
    """コードレビューツール"""
    
    name = "review_code"
    description = "Analyze code quality and provide feedback"
    
    input_schema = {
        "type": "object",
        "properties": {
            "diff": {
                "type": "string",
                "description": "Git diff to review"
            },
            "files_changed": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of changed files"
            },
            "coding_standards": {
                "type": "object",
                "description": "Coding standards to enforce"
            },
            "review_focus": {
                "type": "array",
                "items": {
                    "enum": ["style", "security", "performance", "logic"]
                },
                "description": "Areas to focus on"
            }
        },
        "required": ["diff", "files_changed"]
    }
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """ツールを実行"""
        try:
            # 1. diffを解析
            changes = self._parse_diff(params["diff"])
            
            # 2. 各ファイルをレビュー
            reviews = []
            for file_path in params["files_changed"]:
                file_review = await self._review_file(
                    file_path,
                    changes.get(file_path),
                    params.get("coding_standards"),
                    params.get("review_focus", ["style", "security", "logic"])
                )
                reviews.append(file_review)
            
            # 3. レビュー結果を集約
            aggregated = self._aggregate_reviews(reviews)
            
            return ToolResult(
                success=True,
                data={
                    "approved": aggregated.approved,
                    "comments": aggregated.comments,
                    "suggestions": aggregated.suggestions,
                    "severity": aggregated.severity,
                    "metrics": {
                        "issues_found": len(aggregated.comments),
                        "critical_issues": aggregated.critical_count,
                        "code_quality_score": aggregated.quality_score
                    }
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e)
            )

### 3. Test Tool

テストを実行するツール。

```python
class TestTool:
    """テスト実行ツール"""
    
    name = "run_tests"
    description = "Execute tests and report results"
    
    input_schema = {
        "type": "object",
        "properties": {
            "workspace_path": {
                "type": "string",
                "description": "Path to workspace"
            },
            "test_commands": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Test commands to execute"
            },
            "test_scope": {
                "type": "string",
                "enum": ["all", "unit", "integration", "e2e"],
                "description": "Scope of tests to run"
            },
            "coverage_required": {
                "type": "boolean",
                "description": "Whether to collect coverage"
            }
        },
        "required": ["workspace_path"]
    }
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """ツールを実行"""
        try:
            # 1. テストコマンドを決定
            commands = params.get("test_commands") or self._detect_test_commands(
                params["workspace_path"],
                params.get("test_scope", "all")
            )
            
            # 2. テストを実行
            results = []
            for command in commands:
                result = await self._run_test_command(
                    params["workspace_path"],
                    command,
                    params.get("coverage_required", False)
                )
                results.append(result)
            
            # 3. 結果を集約
            aggregated = self._aggregate_test_results(results)
            
            return ToolResult(
                success=aggregated.all_passed,
                data={
                    "success": aggregated.all_passed,
                    "test_results": aggregated.results,
                    "coverage_percentage": aggregated.coverage,
                    "duration_seconds": aggregated.duration,
                    "summary": {
                        "total": aggregated.total_tests,
                        "passed": aggregated.passed_tests,
                        "failed": aggregated.failed_tests,
                        "skipped": aggregated.skipped_tests
                    }
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e)
            )

### 4. Refactoring Tool

コードをリファクタリングするツール。

```python
class RefactoringTool:
    """リファクタリングツール"""
    
    name = "refactor_code"
    description = "Refactor code while preserving behavior"
    
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "File to refactor"
            },
            "refactoring_type": {
                "type": "string",
                "enum": [
                    "extract_function",
                    "rename_variable",
                    "simplify_logic",
                    "remove_duplication"
                ],
                "description": "Type of refactoring"
            },
            "target_scope": {
                "type": "object",
                "description": "Scope to refactor (line numbers, function name, etc.)"
            }
        },
        "required": ["file_path", "refactoring_type"]
    }
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """ツールを実行"""
        try:
            # 1. 元のコードを読み込み
            original_code = self._read_file(params["file_path"])
            
            # 2. テストを実行（リファクタリング前）
            tests_before = await self._run_tests(params["file_path"])
            
            # 3. リファクタリングを実行
            refactored_code = await self._apply_refactoring(
                original_code,
                params["refactoring_type"],
                params.get("target_scope")
            )
            
            # 4. リファクタリング後のコードを書き込み
            self._write_file(params["file_path"], refactored_code)
            
            # 5. テストを実行（リファクタリング後）
            tests_after = await self._run_tests(params["file_path"])
            
            # 6. テスト結果を比較
            tests_still_pass = tests_before.passed == tests_after.passed
            
            if not tests_still_pass:
                # ロールバック
                self._write_file(params["file_path"], original_code)
                raise RefactoringError("Tests failed after refactoring")
            
            return ToolResult(
                success=True,
                data={
                    "refactored_code": refactored_code,
                    "changes_summary": self._summarize_changes(original_code, refactored_code),
                    "tests_still_pass": tests_still_pass
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e)
            )

### 5. Documentation Tool

ドキュメントを生成するツール。

```python
class DocumentationTool:
    """ドキュメント生成ツール"""
    
    name = "generate_documentation"
    description = "Generate documentation from code"
    
    input_schema = {
        "type": "object",
        "properties": {
            "code_files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Files to document"
            },
            "doc_type": {
                "type": "string",
                "enum": ["api", "readme", "inline", "architecture"],
                "description": "Type of documentation"
            },
            "output_format": {
                "type": "string",
                "enum": ["markdown", "html", "rst"],
                "description": "Output format"
            }
        },
        "required": ["code_files", "doc_type"]
    }
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """ツールを実行"""
        try:
            # 1. コードを解析
            analysis = await self._analyze_code(params["code_files"])
            
            # 2. ドキュメントを生成
            documentation = await self._generate_docs(
                analysis,
                params["doc_type"],
                params.get("output_format", "markdown")
            )
            
            # 3. ドキュメントを書き込み
            files_created = self._write_documentation(documentation)
            
            # 4. 完全性をチェック
            completeness = self._check_completeness(analysis, documentation)
            
            return ToolResult(
                success=True,
                data={
                    "documentation_content": documentation.content,
                    "files_created": files_created,
                    "completeness_score": completeness.score,
                    "missing_items": completeness.missing
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e)
            )

## Orchestrator Integration

### Tool Invocation Pattern

```python
class OrchestratorAgent:
    """Orchestrator Agent (Kiro)"""
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp = mcp_client
        self.tools = self._discover_tools()
    
    async def execute_task(self, task: Task) -> TaskResult:
        """タスクを実行"""
        try:
            # 1. 実装ツールを呼び出し
            impl_result = await self.mcp.call_tool(
                "implement_code",
                {
                    "task_description": task.description,
                    "acceptance_criteria": task.acceptance_criteria,
                    "workspace_path": task.workspace_path
                }
            )
            
            if not impl_result.success:
                return TaskResult(success=False, error=impl_result.error)
            
            # 2. レビューツールを呼び出し
            review_result = await self.mcp.call_tool(
                "review_code",
                {
                    "diff": impl_result.data["diff"],
                    "files_changed": impl_result.data["files_changed"]
                }
            )
            
            # 3. レビューが承認されなかった場合は修正
            if not review_result.data["approved"]:
                # レビューコメントを元に修正
                fix_result = await self._fix_review_issues(
                    task,
                    review_result.data["comments"]
                )
                if not fix_result.success:
                    return fix_result
            
            # 4. テストツールを呼び出し
            test_result = await self.mcp.call_tool(
                "run_tests",
                {
                    "workspace_path": task.workspace_path,
                    "test_scope": "all"
                }
            )
            
            if not test_result.data["success"]:
                return TaskResult(
                    success=False,
                    error="Tests failed",
                    details=test_result.data
                )
            
            # 5. 成功
            return TaskResult(
                success=True,
                implementation=impl_result.data,
                review=review_result.data,
                tests=test_result.data
            )
            
        except Exception as e:
            return TaskResult(success=False, error=str(e))
    
    async def _fix_review_issues(
        self,
        task: Task,
        comments: List[ReviewComment]
    ) -> TaskResult:
        """レビュー指摘を修正"""
        # レビューコメントを元に修正プロンプトを作成
        fix_description = self._build_fix_description(task, comments)
        
        # 実装ツールを再度呼び出し
        return await self.mcp.call_tool(
            "implement_code",
            {
                "task_description": fix_description,
                "workspace_path": task.workspace_path
            }
        )

## Data Models

### ToolResult

```python
@dataclass
class ToolResult:
    """ツール実行結果"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

### Tool Configuration

```python
@dataclass
class ToolConfig:
    """ツール設定"""
    name: str
    enabled: bool = True
    timeout_seconds: int = 300
    retry_count: int = 3
    retry_delay_seconds: float = 1.0
    custom_config: Dict[str, Any] = field(default_factory=dict)

## MCP Server Implementation

```python
class AgentToolsServer:
    """MCP Tool Server"""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self.tools = self._register_tools()
    
    def _register_tools(self) -> Dict[str, Tool]:
        """ツールを登録"""
        return {
            "implement_code": ImplementationTool(),
            "review_code": ReviewTool(),
            "run_tests": TestTool(),
            "refactor_code": RefactoringTool(),
            "generate_documentation": DocumentationTool(),
            "debug_code": DebugTool(),
            "manage_dependencies": DependencyTool(),
            "analyze_performance": PerformanceTool(),
            "scan_security": SecurityTool(),
            "migrate_code": MigrationTool()
        }
    
    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """リクエストを処理"""
        tool = self.tools.get(request.tool_name)
        
        if not tool:
            return MCPResponse(
                success=False,
                error=f"Tool not found: {request.tool_name}"
            )
        
        # ツールを実行
        result = await tool.execute(request.params)
        
        return MCPResponse(
            success=result.success,
            data=result.data,
            error=result.error
        )

## Configuration

### mcp.json

```json
{
  "mcpServers": {
    "necrocode-agent-tools": {
      "command": "python",
      "args": ["-m", "necrocode.agent_tools.server"],
      "env": {
        "TOOL_CONFIG_PATH": ".necrocode/tools-config.json"
      }
    }
  }
}
```

### tools-config.json

```json
{
  "tools": {
    "implement_code": {
      "enabled": true,
      "timeout_seconds": 300,
      "model": "claude-3-5-sonnet-20241022"
    },
    "review_code": {
      "enabled": true,
      "timeout_seconds": 120,
      "coding_standards": {
        "max_line_length": 100,
        "require_docstrings": true
      }
    },
    "run_tests": {
      "enabled": true,
      "timeout_seconds": 600,
      "coverage_threshold": 80
    }
  }
}
```

## Testing Strategy

### Unit Tests
- `test_implementation_tool.py`: Implementation Toolの機能
- `test_review_tool.py`: Review Toolの機能
- `test_test_tool.py`: Test Toolの機能

### Integration Tests
- `test_orchestrator_integration.py`: Orchestratorとツールの統合
- `test_tool_chaining.py`: ツールチェーンの動作

### Performance Tests
- `test_tool_performance.py`: ツールのパフォーマンス

## Dependencies

```python
# requirements.txt
anthropic>=0.18.0  # Claude API
mcp>=1.0.0  # Model Context Protocol
```

## Future Enhancements

1. **ツールキャッシング**: 頻繁に使用されるツール結果のキャッシュ
2. **並列実行**: 独立したツールの並列実行
3. **ツールマーケットプレイス**: カスタムツールの共有
4. **学習機能**: ツール使用パターンの学習と最適化
