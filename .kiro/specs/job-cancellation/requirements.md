# Job Cancellation - Requirements

## Overview
実行中のジョブをキャンセルする機能。

## Functional Requirements

### 1.1 ジョブキャンセル
- 実行中のジョブを停止
- キュー内のタスクを削除
- 実行中のRunnerを停止
- リソースのクリーンアップ

### 1.2 部分キャンセル
- 特定のタスクのみキャンセル
- 完了済みタスクは保持
- 依存タスクの処理

### 1.3 ステータス管理
- キャンセル状態の記録
- キャンセル理由の記録
- ロールバック情報

## CLI Commands
```bash
# ジョブ全体をキャンセル
necrocode job cancel <job-id>

# 特定タスクをキャンセル
necrocode job cancel <job-id> --task <task-id>

# 強制キャンセル
necrocode job cancel <job-id> --force
```

## API Endpoints
- POST /api/jobs/{job_id}/cancel
- POST /api/tasks/{task_id}/cancel
- GET /api/jobs/{job_id}/cancellation-status
