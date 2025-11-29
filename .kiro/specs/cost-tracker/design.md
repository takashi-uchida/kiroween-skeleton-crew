# Cost Tracker - Design Document

## Overview

Cost Trackerは、NecroCodeフレームワーク内でLLM API使用量とコストを追跡・管理するシステムです。各タスク実行時のトークン使用量を記録し、リアルタイムでコスト計算を行い、予算管理と最適化提案を提供します。

## Architecture

### High-Level Architecture

```
┌─────────────────┐
│  Agent Runner   │
│  Task Executor  │
└────────┬────────┘
         │ Usage Events
         ▼
┌─────────────────────────────────────────┐
│         Cost Tracker Service            │
│  ┌─────────────┐  ┌─────────────────┐  │
│  │   Usage     │  │  Cost           │  │
│  │   Collector │─▶│  Calculator     │  │
│  └─────────────┘  └─────────────────┘  │
│         │                  │            │
│         ▼                  ▼            │
│  ┌─────────────┐  ┌─────────────────┐  │
│  │   Usage     │  │  Budget         │  │
│  │   Store     │  │  Manager        │  │
│  └─────────────┘  └─────────────────┘  │
│         │                  │            │
│         └──────────┬───────┘            │
│                    ▼                    │
│         ┌─────────────────┐             │
│         │  Report         │             │
│         │  Generator      │             │
│         └─────────────────┘             │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│   CLI / API     │
│   Interface     │
└─────────────────┘
```

### Integration Points

1. **Agent Runner Integration**: `necrocode/agent_runner/llm_client.py`にフックを追加し、各LLM呼び出し後に使用量を記録
2. **Task Registry Integration**: タスクIDとジョブIDを使用して使用量をコンテキスト化
3. **Dispatcher Integration**: ジョブレベルでのコスト集計とレポート生成

## Components and Interfaces

### 1. Usage Collector

**責任**: LLM API呼び出しからトークン使用量を収集

```python
# necrocode/cost_tracker/usage_collector.py

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class UsageRecord:
    """LLM API使用量の記録"""
    timestamp: datetime
    job_id: str
    task_id: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    agent_instance: Optional[str] = None
    operation: Optional[str] = None  # e.g., "task_execution", "planning"

class UsageCollector:
    """LLM使用量を収集してストアに保存"""
    
    def __init__(self, store: 'UsageStore', calculator: 'CostCalculator'):
        self.store = store
        self.calculator = calculator
    
    def record_usage(
        self,
        job_id: str,
        task_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        agent_instance: Optional[str] = None,
        operation: Optional[str] = None
    ) -> UsageRecord:
        """使用量を記録してコストを計算"""
        total_tokens = prompt_tokens + completion_tokens
        cost = self.calculator.calculate_cost(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens
        )
        
        record = UsageRecord(
            timestamp=datetime.utcnow(),
            job_id=job_id,
            task_id=task_id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            agent_instance=agent_instance,
            operation=operation
        )
        
        self.store.save_record(record)
        return record
```

**設計判断**: 
- UsageRecordをimmutableなdataclassとして定義し、監査証跡を保証
- agent_instanceとoperationをオプショナルフィールドとして追加し、詳細な分析を可能に

### 2. Cost Calculator

**責任**: モデル別の料金設定に基づいてコストを計算

```python
# necrocode/cost_tracker/cost_calculator.py

from typing import Dict
from dataclasses import dataclass

@dataclass
class ModelPricing:
    """モデルの料金設定"""
    model: str
    prompt_price_per_1k: float  # USD per 1K tokens
    completion_price_per_1k: float

class CostCalculator:
    """LLM使用コストを計算"""
    
    # デフォルトの料金設定（2025年11月時点）
    DEFAULT_PRICING: Dict[str, ModelPricing] = {
        "gpt-4": ModelPricing("gpt-4", 0.03, 0.06),
        "gpt-4-turbo": ModelPricing("gpt-4-turbo", 0.01, 0.03),
        "gpt-5-codex": ModelPricing("gpt-5-codex", 0.015, 0.045),
        "gpt-3.5-turbo": ModelPricing("gpt-3.5-turbo", 0.0015, 0.002),
    }
    
    def __init__(self, custom_pricing: Optional[Dict[str, ModelPricing]] = None):
        self.pricing = {**self.DEFAULT_PRICING}
        if custom_pricing:
            self.pricing.update(custom_pricing)
    
    def calculate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """トークン数からコストを計算（USD）"""
        if model not in self.pricing:
            raise ValueError(f"Unknown model: {model}")
        
        pricing = self.pricing[model]
        prompt_cost = (prompt_tokens / 1000) * pricing.prompt_price_per_1k
        completion_cost = (completion_tokens / 1000) * pricing.completion_price_per_1k
        
        return prompt_cost + completion_cost
    
    def add_model_pricing(self, pricing: ModelPricing):
        """カスタムモデルの料金設定を追加"""
        self.pricing[pricing.model] = pricing
```

**設計判断**:
- 料金設定を外部から注入可能にし、新しいモデルや価格変更に対応
- 1000トークン単位での計算により、APIプロバイダーの料金体系に準拠

### 3. Usage Store

**責任**: 使用量レコードの永続化と検索

```python
# necrocode/cost_tracker/usage_store.py

import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta

class UsageStore:
    """使用量レコードをJSONL形式で保存"""
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def save_record(self, record: UsageRecord):
        """レコードを日付別ファイルに追記"""
        date_str = record.timestamp.strftime("%Y-%m-%d")
        file_path = self.storage_dir / f"usage_{date_str}.jsonl"
        
        with open(file_path, "a") as f:
            f.write(json.dumps(self._record_to_dict(record)) + "\n")
    
    def get_records_by_job(self, job_id: str) -> List[UsageRecord]:
        """ジョブIDで使用量を検索"""
        records = []
        for file_path in self.storage_dir.glob("usage_*.jsonl"):
            with open(file_path) as f:
                for line in f:
                    record_dict = json.loads(line)
                    if record_dict["job_id"] == job_id:
                        records.append(self._dict_to_record(record_dict))
        return records
    
    def get_records_by_period(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[UsageRecord]:
        """期間で使用量を検索"""
        records = []
        current = start_date
        
        while current <= end_date:
            date_str = current.strftime("%Y-%m-%d")
            file_path = self.storage_dir / f"usage_{date_str}.jsonl"
            
            if file_path.exists():
                with open(file_path) as f:
                    for line in f:
                        record_dict = json.loads(line)
                        timestamp = datetime.fromisoformat(record_dict["timestamp"])
                        if start_date <= timestamp <= end_date:
                            records.append(self._dict_to_record(record_dict))
            
            current += timedelta(days=1)
        
        return records
    
    def _record_to_dict(self, record: UsageRecord) -> dict:
        return {
            "timestamp": record.timestamp.isoformat(),
            "job_id": record.job_id,
            "task_id": record.task_id,
            "model": record.model,
            "prompt_tokens": record.prompt_tokens,
            "completion_tokens": record.completion_tokens,
            "total_tokens": record.total_tokens,
            "cost": record.cost,
            "agent_instance": record.agent_instance,
            "operation": record.operation,
        }
    
    def _dict_to_record(self, data: dict) -> UsageRecord:
        return UsageRecord(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            job_id=data["job_id"],
            task_id=data["task_id"],
            model=data["model"],
            prompt_tokens=data["prompt_tokens"],
            completion_tokens=data["completion_tokens"],
            total_tokens=data["total_tokens"],
            cost=data["cost"],
            agent_instance=data.get("agent_instance"),
            operation=data.get("operation"),
        )
```

**設計判断**:
- JSONL形式を採用し、日付別ファイルで管理することで、大量データでも効率的に検索可能
- Task Registryと同様のファイルベースアプローチで、既存アーキテクチャとの一貫性を保持

### 4. Budget Manager

**責任**: 予算設定、アラート、使用量制限の管理

```python
# necrocode/cost_tracker/budget_manager.py

from dataclasses import dataclass
from typing import Optional, Callable
from datetime import datetime
from enum import Enum

class BudgetPeriod(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

@dataclass
class Budget:
    """予算設定"""
    period: BudgetPeriod
    limit: float  # USD
    alert_threshold: float = 0.8  # 80%でアラート
    hard_limit: bool = False  # Trueの場合、予算超過時に実行を停止

@dataclass
class BudgetStatus:
    """予算の使用状況"""
    budget: Budget
    current_spend: float
    remaining: float
    percentage_used: float
    is_exceeded: bool
    is_alert_triggered: bool

class BudgetManager:
    """予算管理とアラート"""
    
    def __init__(
        self,
        store: UsageStore,
        alert_callback: Optional[Callable[[BudgetStatus], None]] = None
    ):
        self.store = store
        self.alert_callback = alert_callback
        self.budgets: Dict[BudgetPeriod, Budget] = {}
    
    def set_budget(self, budget: Budget):
        """予算を設定"""
        self.budgets[budget.period] = budget
    
    def check_budget(self, period: BudgetPeriod) -> BudgetStatus:
        """現在の予算状況を確認"""
        if period not in self.budgets:
            raise ValueError(f"No budget set for period: {period}")
        
        budget = self.budgets[period]
        start_date, end_date = self._get_period_range(period)
        
        records = self.store.get_records_by_period(start_date, end_date)
        current_spend = sum(r.cost for r in records)
        
        remaining = budget.limit - current_spend
        percentage_used = (current_spend / budget.limit) * 100
        is_exceeded = current_spend > budget.limit
        is_alert_triggered = percentage_used >= (budget.alert_threshold * 100)
        
        status = BudgetStatus(
            budget=budget,
            current_spend=current_spend,
            remaining=remaining,
            percentage_used=percentage_used,
            is_exceeded=is_exceeded,
            is_alert_triggered=is_alert_triggered
        )
        
        if is_alert_triggered and self.alert_callback:
            self.alert_callback(status)
        
        return status
    
    def can_proceed(self, period: BudgetPeriod) -> bool:
        """予算内で実行可能かチェック"""
        if period not in self.budgets:
            return True  # 予算未設定の場合は制限なし
        
        status = self.check_budget(period)
        budget = self.budgets[period]
        
        if budget.hard_limit and status.is_exceeded:
            return False
        
        return True
    
    def _get_period_range(self, period: BudgetPeriod) -> tuple[datetime, datetime]:
        """期間の開始日と終了日を取得"""
        now = datetime.utcnow()
        
        if period == BudgetPeriod.DAILY:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif period == BudgetPeriod.WEEKLY:
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        else:  # MONTHLY
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        
        return start, end
```

**設計判断**:
- hard_limitフラグにより、予算超過時の動作を柔軟に制御
- コールバック機構により、アラート通知方法を外部から注入可能（Slack、メール等）

### 5. Report Generator

**責任**: 使用量とコストのレポート生成

```python
# necrocode/cost_tracker/report_generator.py

from dataclasses import dataclass
from typing import List, Dict
from collections import defaultdict

@dataclass
class CostSummary:
    """コストサマリー"""
    total_cost: float
    total_tokens: int
    total_calls: int
    by_model: Dict[str, float]
    by_job: Dict[str, float]
    by_agent: Dict[str, float]

@dataclass
class UsageTrend:
    """使用量トレンド"""
    date: str
    cost: float
    tokens: int
    calls: int

class ReportGenerator:
    """レポート生成"""
    
    def __init__(self, store: UsageStore):
        self.store = store
    
    def generate_summary(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> CostSummary:
        """期間のコストサマリーを生成"""
        records = self.store.get_records_by_period(start_date, end_date)
        
        total_cost = sum(r.cost for r in records)
        total_tokens = sum(r.total_tokens for r in records)
        total_calls = len(records)
        
        by_model = defaultdict(float)
        by_job = defaultdict(float)
        by_agent = defaultdict(float)
        
        for record in records:
            by_model[record.model] += record.cost
            by_job[record.job_id] += record.cost
            if record.agent_instance:
                by_agent[record.agent_instance] += record.cost
        
        return CostSummary(
            total_cost=total_cost,
            total_tokens=total_tokens,
            total_calls=total_calls,
            by_model=dict(by_model),
            by_job=dict(by_job),
            by_agent=dict(by_agent)
        )
    
    def generate_trend(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[UsageTrend]:
        """日次トレンドを生成"""
        records = self.store.get_records_by_period(start_date, end_date)
        
        daily_data = defaultdict(lambda: {"cost": 0.0, "tokens": 0, "calls": 0})
        
        for record in records:
            date_key = record.timestamp.strftime("%Y-%m-%d")
            daily_data[date_key]["cost"] += record.cost
            daily_data[date_key]["tokens"] += record.total_tokens
            daily_data[date_key]["calls"] += 1
        
        trends = [
            UsageTrend(
                date=date,
                cost=data["cost"],
                tokens=data["tokens"],
                calls=data["calls"]
            )
            for date, data in sorted(daily_data.items())
        ]
        
        return trends
    
    def forecast_monthly_cost(self) -> float:
        """月次コストを予測"""
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        records = self.store.get_records_by_period(month_start, now)
        
        if not records:
            return 0.0
        
        days_elapsed = (now - month_start).days + 1
        days_in_month = (month_start.replace(month=month_start.month + 1) - month_start).days
        
        current_spend = sum(r.cost for r in records)
        daily_average = current_spend / days_elapsed
        
        return daily_average * days_in_month
```

**設計判断**:
- 日次平均から月次コストを予測する単純な線形モデルを採用
- 将来的には機械学習ベースの予測モデルに拡張可能

### 6. Cost Tracker Service

**責任**: 全コンポーネントの統合とAPIの提供

```python
# necrocode/cost_tracker/cost_tracker.py

from pathlib import Path
from typing import Optional

class CostTracker:
    """Cost Trackerサービスのメインクラス"""
    
    def __init__(self, storage_dir: Path, config: Optional[dict] = None):
        self.storage_dir = storage_dir
        self.config = config or {}
        
        # コンポーネント初期化
        self.calculator = CostCalculator()
        self.store = UsageStore(storage_dir)
        self.collector = UsageCollector(self.store, self.calculator)
        self.budget_manager = BudgetManager(self.store)
        self.report_generator = ReportGenerator(self.store)
    
    def record_llm_usage(
        self,
        job_id: str,
        task_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        **kwargs
    ) -> UsageRecord:
        """LLM使用量を記録（Agent Runnerから呼び出される）"""
        return self.collector.record_usage(
            job_id=job_id,
            task_id=task_id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            **kwargs
        )
    
    def get_job_cost(self, job_id: str) -> float:
        """ジョブの総コストを取得"""
        records = self.store.get_records_by_job(job_id)
        return sum(r.cost for r in records)
    
    def get_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> CostSummary:
        """コストサマリーを取得"""
        if not start_date:
            start_date = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = datetime.utcnow()
        
        return self.report_generator.generate_summary(start_date, end_date)
```

## Data Models

すべてのデータモデルは`necrocode/cost_tracker/models.py`に集約:

```python
# necrocode/cost_tracker/models.py

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum

# UsageRecord, ModelPricing, Budget, BudgetStatus, CostSummary, UsageTrend
# (上記で定義したものをここに集約)
```

## Error Handling

```python
# necrocode/cost_tracker/exceptions.py

class CostTrackerError(Exception):
    """Cost Tracker基底例外"""
    pass

class UnknownModelError(CostTrackerError):
    """未知のモデルエラー"""
    pass

class BudgetExceededError(CostTrackerError):
    """予算超過エラー"""
    pass

class StorageError(CostTrackerError):
    """ストレージエラー"""
    pass
```

## Testing Strategy

### Unit Tests
- `test_cost_calculator.py`: 各モデルのコスト計算精度
- `test_usage_store.py`: JSONL読み書き、期間検索
- `test_budget_manager.py`: 予算チェック、アラートトリガー
- `test_report_generator.py`: サマリー生成、トレンド計算

### Integration Tests
- `test_cost_tracker_integration.py`: Agent Runnerとの統合
- `test_budget_enforcement.py`: 予算制限の実行フロー

### Performance Tests
- 大量レコード（10万件以上）での検索性能
- 並行書き込み時のファイルロック動作

## Configuration

```yaml
# config/cost-tracker.yaml

cost_tracker:
  storage_dir: ".necrocode/cost_tracker"
  
  # カスタムモデル料金設定
  custom_pricing:
    - model: "custom-model"
      prompt_price_per_1k: 0.02
      completion_price_per_1k: 0.04
  
  # 予算設定
  budgets:
    - period: "monthly"
      limit: 100.0  # USD
      alert_threshold: 0.8
      hard_limit: false
    
    - period: "daily"
      limit: 5.0
      alert_threshold: 0.9
      hard_limit: true
  
  # アラート設定
  alerts:
    enabled: true
    channels:
      - type: "log"
      - type: "slack"
        webhook_url: "${SLACK_WEBHOOK_URL}"
```

## CLI Interface

```bash
# コストサマリー表示
necrocode cost summary
necrocode cost summary --month 2025-11
necrocode cost summary --start 2025-11-01 --end 2025-11-30

# ジョブ別コスト
necrocode cost by-job <job-id>

# 予算状況確認
necrocode cost budget status
necrocode cost budget set --period monthly --limit 100

# レポート生成
necrocode cost report --format json --output report.json
necrocode cost report --format csv --output report.csv

# コスト予測
necrocode cost forecast --period monthly
```

## API Endpoints

```python
# necrocode/cost_tracker/api.py (将来的な拡張)

from fastapi import FastAPI, Query
from datetime import datetime

app = FastAPI()

@app.get("/api/cost/summary")
async def get_summary(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None)
):
    """コストサマリーを取得"""
    pass

@app.get("/api/cost/by-job/{job_id}")
async def get_job_cost(job_id: str):
    """ジョブ別コストを取得"""
    pass

@app.get("/api/cost/forecast")
async def get_forecast(period: str = "monthly"):
    """コスト予測を取得"""
    pass

@app.get("/api/cost/budget/status")
async def get_budget_status(period: str):
    """予算状況を取得"""
    pass
```

## Integration with Existing Components

### 1. Agent Runner Integration

`necrocode/agent_runner/llm_client.py`を修正:

```python
class OpenAIChatClient:
    def __init__(self, cost_tracker: Optional[CostTracker] = None):
        self.cost_tracker = cost_tracker
        # ... existing code
    
    def chat_completion(self, messages, **kwargs):
        response = self.client.chat.completions.create(...)
        
        # Cost tracking
        if self.cost_tracker and hasattr(self, 'current_job_id'):
            self.cost_tracker.record_llm_usage(
                job_id=self.current_job_id,
                task_id=self.current_task_id,
                model=response.model,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens
            )
        
        return response
```

### 2. Task Registry Integration

タスク完了時にコスト情報を記録:

```python
# Task Registryのイベントにコスト情報を追加
task_registry.add_event(
    spec_id=spec_id,
    task_id=task_id,
    event_type="task_completed",
    data={
        "cost": cost_tracker.get_job_cost(job_id),
        "tokens": total_tokens
    }
)
```

### 3. Dispatcher Integration

ジョブ開始時に予算チェック:

```python
# Dispatcherでジョブ実行前に予算確認
if not cost_tracker.budget_manager.can_proceed(BudgetPeriod.DAILY):
    raise BudgetExceededError("Daily budget exceeded")
```

## Migration Strategy

1. **Phase 1**: コアコンポーネント実装（UsageCollector, CostCalculator, UsageStore）
2. **Phase 2**: Agent Runner統合とデータ収集開始
3. **Phase 3**: Budget Manager実装とアラート機能
4. **Phase 4**: Report Generator実装とCLI追加
5. **Phase 5**: API実装と外部ツール統合

## Future Enhancements

- **機械学習ベースのコスト予測**: 過去のパターンから精度の高い予測
- **リアルタイムダッシュボード**: Web UIでのコスト可視化
- **コスト最適化提案**: 使用パターン分析に基づく最適化アドバイス
- **マルチテナント対応**: プロジェクト/チーム別のコスト管理
- **外部BI連携**: Grafana、Tableauなどへのデータエクスポート
