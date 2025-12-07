# Notification System - Requirements

## Overview
タスク完了やエラー時の通知システム。

## Functional Requirements

### 1.1 通知チャネル
- Slack
- Email
- Discord
- Webhook
- SMS (オプション)

### 1.2 通知イベント
- ジョブ開始
- ジョブ完了
- ジョブ失敗
- タスク完了
- タスク失敗
- PR作成
- PR マージ

### 1.3 通知設定
- チャネル別の有効/無効
- イベント別の通知設定
- 通知フィルター
- 通知テンプレート

### 1.4 通知内容
- ジョブ/タスク情報
- ステータス
- エラーメッセージ
- 実行時間
- リンク（ダッシュボード、PR）

## Configuration
```yaml
notifications:
  slack:
    enabled: true
    webhook_url: https://hooks.slack.com/...
    channel: "#necrocode"
    events:
      - job_completed
      - job_failed
      - pr_created
  
  email:
    enabled: true
    smtp_server: smtp.gmail.com
    from: necrocode@example.com
    to:
      - team@example.com
    events:
      - job_failed
```

## Message Templates
- Slack: リッチフォーマット（Blocks API）
- Email: HTML + Plain text
- Discord: Embed形式
