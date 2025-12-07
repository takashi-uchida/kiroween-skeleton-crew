# Cost Tracker - Requirements

## Overview
LLM API使用量とコストの追跡システム。

## Functional Requirements

### 1.1 使用量追跡
- トークン数の記録
- API呼び出し回数
- モデル別の使用量
- ジョブ別の使用量

### 1.2 コスト計算
- モデル別の料金設定
- リアルタイムコスト計算
- 月次コスト集計
- プロジェクト別コスト

### 1.3 予算管理
- 予算設定
- 予算アラート
- 使用量制限
- コスト予測

### 1.4 レポート
- 日次/週次/月次レポート
- コスト推移グラフ
- 使用量分析
- 最適化提案

## Data Model
```python
@dataclass
class UsageRecord:
    timestamp: datetime
    job_id: str
    task_id: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
```

## API Endpoints
- GET /api/cost/summary
- GET /api/cost/by-job/{job_id}
- GET /api/cost/by-period?start=&end=
- GET /api/cost/forecast

## CLI Commands
```bash
# コストサマリー
necrocode cost summary

# ジョブ別コスト
necrocode cost by-job <job-id>

# 月次レポート
necrocode cost report --month 2025-11
```
