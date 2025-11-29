# LLM Task Planner - Design

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Job Submitter                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              LLM Task Planner                           │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Analyzer   │→ │  Generator   │→ │  Validator   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│         │                  │                  │         │
│         ▼                  ▼                  ▼         │
│  ┌──────────────────────────────────────────────────┐  │
│  │            LLM Client (OpenAI)                   │  │
│  └──────────────────────────────────────────────────┘  │
│         │                                               │
│         ▼                                               │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Prompt Template Manager                  │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                 Task Registry                           │
└─────────────────────────────────────────────────────────┘
```

## Components

### 1. LLMTaskPlanner
メインコンポーネント。タスク分解のオーケストレーション。

```python
class LLMTaskPlanner:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.analyzer = JobAnalyzer(llm_client)
        self.generator = TaskGenerator(llm_client)
        self.validator = TaskValidator()
        self.cache = TaskCache()
    
    def plan(
        self,
        job_description: str,
        project_name: str,
        options: PlanningOptions = None
    ) -> TaskPlan:
        """ジョブ記述からタスクプランを生成"""
        
        # 1. キャッシュチェック
        cached = self.cache.get(job_description)
        if cached:
            return cached
        
        # 2. ジョブ分析
        analysis = self.analyzer.analyze(job_description, options)
        
        # 3. タスク生成
        tasks = self.generator.generate(analysis)
        
        # 4. 検証
        validated_tasks = self.validator.validate(tasks)
        
        # 5. キャッシュ保存
        plan = TaskPlan(tasks=validated_tasks, analysis=analysis)
        self.cache.set(job_description, plan)
        
        return plan
```

### 2. JobAnalyzer
ジョブ記述を分析し、プロジェクトタイプや技術スタックを推論。

```python
class JobAnalyzer:
    def analyze(
        self,
        job_description: str,
        options: PlanningOptions
    ) -> JobAnalysis:
        """ジョブ記述を分析"""
        
        prompt = self._build_analysis_prompt(job_description, options)
        response = self.llm_client.complete(prompt)
        
        return JobAnalysis(
            project_type=response['project_type'],
            tech_stack=response['tech_stack'],
            complexity=response['complexity'],
            estimated_tasks=response['estimated_tasks'],
            key_features=response['key_features']
        )
    
    def _build_analysis_prompt(self, description: str, options) -> str:
        """分析用プロンプト構築"""
        return f"""
        以下のプロジェクト要件を分析してください：
        
        {description}
        
        以下の情報を抽出してください：
        1. プロジェクトタイプ（REST API, SPA, CLI, etc.）
        2. 推奨技術スタック
        3. 複雑度（Low/Medium/High）
        4. 推定タスク数
        5. 主要機能リスト
        
        JSON形式で回答してください。
        """
```

### 3. TaskGenerator
分析結果から具体的なタスクを生成。

```python
class TaskGenerator:
    def generate(self, analysis: JobAnalysis) -> List[Task]:
        """タスク生成"""
        
        # プロジェクトタイプに応じたテンプレート選択
        template = self.template_manager.get_template(
            analysis.project_type
        )
        
        # LLMでタスク生成
        prompt = self._build_generation_prompt(analysis, template)
        response = self.llm_client.complete(prompt)
        
        # タスクオブジェクトに変換
        tasks = self._parse_tasks(response)
        
        # 依存関係解決
        tasks = self._resolve_dependencies(tasks)
        
        return tasks
    
    def _build_generation_prompt(
        self,
        analysis: JobAnalysis,
        template: PromptTemplate
    ) -> str:
        """タスク生成プロンプト構築"""
        return template.render(
            project_type=analysis.project_type,
            tech_stack=analysis.tech_stack,
            features=analysis.key_features,
            complexity=analysis.complexity
        )
```

### 4. TaskValidator
生成されたタスクの妥当性を検証。

```python
class TaskValidator:
    def validate(self, tasks: List[Task]) -> List[Task]:
        """タスク検証"""
        
        # 1. 循環依存チェック
        self._check_circular_dependencies(tasks)
        
        # 2. タスク粒度チェック
        tasks = self._optimize_granularity(tasks)
        
        # 3. 完全性チェック
        self._check_completeness(tasks)
        
        # 4. 実装可能性チェック
        self._check_feasibility(tasks)
        
        return tasks
    
    def _check_circular_dependencies(self, tasks: List[Task]):
        """循環依存検出"""
        graph = self._build_dependency_graph(tasks)
        cycles = self._detect_cycles(graph)
        
        if cycles:
            raise CircularDependencyError(cycles)
    
    def _optimize_granularity(self, tasks: List[Task]) -> List[Task]:
        """タスク粒度最適化"""
        optimized = []
        
        for task in tasks:
            # 大きすぎるタスクを分割
            if self._is_too_large(task):
                subtasks = self._split_task(task)
                optimized.extend(subtasks)
            # 小さすぎるタスクを統合
            elif self._is_too_small(task):
                # 次のタスクと統合可能かチェック
                continue
            else:
                optimized.append(task)
        
        return optimized
```

### 5. PromptTemplateManager
プロジェクトタイプ別のプロンプトテンプレート管理。

```python
class PromptTemplateManager:
    def __init__(self):
        self.templates = self._load_templates()
    
    def get_template(self, project_type: str) -> PromptTemplate:
        """テンプレート取得"""
        return self.templates.get(
            project_type,
            self.templates['default']
        )
    
    def _load_templates(self) -> Dict[str, PromptTemplate]:
        """テンプレート読み込み"""
        return {
            'rest-api': RestAPITemplate(),
            'spa': SPATemplate(),
            'cli': CLITemplate(),
            'microservices': MicroservicesTemplate(),
            'default': DefaultTemplate()
        }
```

## Data Models

### TaskPlan
```python
@dataclass
class TaskPlan:
    tasks: List[Task]
    analysis: JobAnalysis
    metadata: Dict[str, Any]
    created_at: datetime
    
    def to_dict(self) -> dict:
        """辞書に変換"""
        return {
            'tasks': [task.to_dict() for task in self.tasks],
            'analysis': self.analysis.to_dict(),
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat()
        }
```

### JobAnalysis
```python
@dataclass
class JobAnalysis:
    project_type: str
    tech_stack: List[str]
    complexity: str  # Low/Medium/High
    estimated_tasks: int
    key_features: List[str]
    recommendations: List[str]
```

### PlanningOptions
```python
@dataclass
class PlanningOptions:
    tech_stack: Optional[List[str]] = None
    granularity: str = 'medium'  # fine/medium/coarse
    max_tasks: int = 20
    include_tests: bool = True
    include_docs: bool = True
```

## Prompt Templates

### REST API Template
```python
REST_API_TEMPLATE = """
以下のREST API要件からタスクを生成してください：

プロジェクト: {project_name}
技術スタック: {tech_stack}
主要機能: {features}

以下の構造でタスクを生成してください：

1. プロジェクトセットアップ
   - 依存関係のインストール
   - プロジェクト構造の作成
   - 設定ファイルの作成

2. データベース設計
   - スキーマ設計
   - マイグレーション作成
   - シードデータ作成

3. 認証・認可
   - ユーザーモデル作成
   - JWT実装
   - ミドルウェア作成

4. APIエンドポイント
   - CRUD操作実装
   - バリデーション
   - エラーハンドリング

5. テストとドキュメント
   - ユニットテスト
   - 統合テスト
   - API ドキュメント

各タスクについて以下を含めてください：
- タスクID（階層的）
- タイトル
- 詳細な説明
- 受け入れ基準
- 依存関係
- 必要なスキル
- 推定工数（時間）

JSON形式で出力してください。
"""
```

## Integration

### Job Submitter統合
```python
# necrocode/orchestration/job_submitter.py

class JobSubmitter:
    def __init__(self):
        self.llm_planner = LLMTaskPlanner(
            llm_client=OpenAIClient()
        )
    
    def submit_job(
        self,
        description: str,
        project_name: str,
        options: PlanningOptions = None
    ) -> str:
        """ジョブ投稿（LLM統合版）"""
        
        # LLMでタスク生成
        plan = self.llm_planner.plan(
            description,
            project_name,
            options
        )
        
        # Task Registryに登録
        spec_name = f"{project_name}-{job_id[:8]}"
        self._create_spec(spec_name, plan.tasks)
        
        return job_id
```

## Configuration

```yaml
# .necrocode/llm_planner.yaml
llm:
  provider: openai
  model: gpt-4
  temperature: 0.7
  max_tokens: 2000
  
cache:
  enabled: true
  ttl: 3600  # 1 hour
  
validation:
  max_task_size: 8  # hours
  min_task_size: 1  # hours
  max_dependencies: 5
  
templates:
  directory: templates/prompts
  custom_templates:
    - my-custom-template.txt
```

## Testing Strategy

### Unit Tests
- LLM Client のモック
- プロンプト生成のテスト
- タスク検証ロジックのテスト

### Integration Tests
- 実際のLLM APIを使用
- エンドツーエンドのタスク生成
- 様々なプロジェクトタイプでのテスト

### Performance Tests
- レスポンス時間測定
- トークン使用量測定
- キャッシュ効果の検証
