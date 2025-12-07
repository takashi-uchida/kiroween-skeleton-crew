# NecroCode ドキュメント翻訳用語集

## 概要

このドキュメントは、NecroCodeプロジェクトのドキュメント翻訳で使用される用語の統一された日本語訳を提供します。翻訳作業を行う際は、必ずこの用語集を参照し、一貫性のある翻訳を心がけてください。

**バージョン**: 1.0.0  
**最終更新**: 2025-12-06

## 目次

- [技術用語](#技術用語)
- [プロジェクト固有用語](#プロジェクト固有用語)
- [そのまま英語を使用する用語](#そのまま英語を使用する用語)
- [英語併記が推奨される用語](#英語併記が推奨される用語)
- [状態・ステータス用語](#状態ステータス用語)
- [動詞の翻訳](#動詞の翻訳)
- [よく使われるフレーズ](#よく使われるフレーズ)
- [翻訳時の注意事項](#翻訳時の注意事項)

---

## 技術用語

### コア概念

| 英語 | 日本語 | 使用例 |
|------|--------|--------|
| Task | タスク | Task Registry → タスクレジストリ |
| Workspace | ワークスペース | workspace management → ワークスペース管理 |
| Registry | レジストリ | Task Registry → タスクレジストリ |
| Artifact | アーティファクト | artifact store → アーティファクトストア |
| Pool | プール | Repo Pool → リポジトリプール |
| Slot | スロット | slot allocation → スロット割り当て |
| Specification / Spec | 仕様 / スペック | spec document → 仕様ドキュメント |
| Repository / Repo | リポジトリ | git repository → gitリポジトリ |
| Instance | インスタンス | agent instance → エージェントインスタンス |
| Dependency | 依存関係 | task dependencies → タスクの依存関係 |
| Lifecycle | ライフサイクル | workspace lifecycle → ワークスペースライフサイクル |

### サービス・コンポーネント

| 英語 | 日本語 | 使用例 |
|------|--------|--------|
| Dispatcher | ディスパッチャー | Task Dispatcher → タスクディスパッチャー |
| Orchestrator | オーケストレーター | Task Orchestrator → タスクオーケストレーター |
| Runner | ランナー | Agent Runner → エージェントランナー |
| Service | サービス | Review PR Service → レビューPRサービス |
| Component | コンポーネント | system component → システムコンポーネント |
| Module | モジュール | Python module → Pythonモジュール |
| Interface | インターフェース | API interface → APIインターフェース |
| Client | クライアント | HTTP client → HTTPクライアント |
| Server | サーバー | web server → Webサーバー |
| Middleware | ミドルウェア | authentication middleware → 認証ミドルウェア |

### アーキテクチャ

| 英語 | 日本語 | 使用例 |
|------|--------|--------|
| Backend | バックエンド | backend service → バックエンドサービス |
| Frontend | フロントエンド | frontend application → フロントエンドアプリケーション |
| Endpoint | エンドポイント | API endpoint → APIエンドポイント |
| Request | リクエスト | HTTP request → HTTPリクエスト |
| Response | レスポンス | API response → APIレスポンス |
| Payload | ペイロード | request payload → リクエストペイロード |

### データ管理

| 英語 | 日本語 | 使用例 |
|------|--------|--------|
| Schema | スキーマ | database schema → データベーススキーマ |
| Model | モデル | data model → データモデル |
| Query | クエリ | database query → データベースクエリ |
| Index | インデックス | search index → 検索インデックス |
| Storage | ストレージ | artifact storage → アーティファクトストレージ |
| Persistence | 永続化 | data persistence → データ永続化 |

### Git関連

| 英語 | 日本語 | 使用例 |
|------|--------|--------|
| Worktree | ワークツリー | git worktree → gitワークツリー |
| Branch | ブランチ | feature branch → フィーチャーブランチ |
| Commit | コミット | git commit → gitコミット |
| Merge | マージ | branch merge → ブランチマージ |
| Push | プッシュ | git push → gitプッシュ |
| Clone | クローン | repository clone → リポジトリクローン |
| Pull Request / PR | プルリクエスト / PR | create PR → PRを作成 |

### 運用・操作

| 英語 | 日本語 | 使用例 |
|------|--------|--------|
| Monitoring | 監視 / モニタリング | system monitoring → システム監視 |
| Metrics | メトリクス | performance metrics → パフォーマンスメトリクス |
| Logging | ロギング / ログ記録 | error logging → エラーロギング |
| Allocation | 割り当て | resource allocation → リソース割り当て |
| Cleanup | クリーンアップ | workspace cleanup → ワークスペースクリーンアップ |
| Retry | リトライ | retry logic → リトライロジック |
| Timeout | タイムアウト | connection timeout → 接続タイムアウト |
| Deadlock | デッドロック | deadlock detection → デッドロック検出 |
| Lock | ロック | file lock → ファイルロック |
| Concurrency | 並行性 / 同時実行 | concurrency control → 並行性制御 |
| Parallel | 並列 | parallel execution → 並列実行 |
| Synchronization | 同期 | data synchronization → データ同期 |

### パフォーマンス

| 英語 | 日本語 | 使用例 |
|------|--------|--------|
| Cache | キャッシュ | memory cache → メモリキャッシュ |
| Optimization | 最適化 | performance optimization → パフォーマンス最適化 |
| Performance | パフォーマンス | system performance → システムパフォーマンス |
| Throughput | スループット | request throughput → リクエストスループット |
| Latency | レイテンシ | network latency → ネットワークレイテンシ |

---

## プロジェクト固有用語

NecroCodeプロジェクト特有の概念と用語です。

| 英語 | 日本語 | 説明 | 使用例 |
|------|--------|------|--------|
| Spirit | スピリット | AIエージェントの呼称 | Architect Spirit → アーキテクトスピリット |
| Necromancer | ネクロマンサー | オーケストレーションの中心コンポーネント | Necromancer orchestrates spirits |
| Spirit Protocol | スピリットプロトコル | スピリット間の通信規約 | follow Spirit Protocol |
| Summoning | 召喚 | スピリットの起動 | summon spirits → スピリットを召喚 |
| Spell | スペル | コミットメッセージ内の操作 | cast spell → スペルを唱える |
| Taskset | タスクセット | タスクのグループ | taskset creation → タスクセット作成 |
| Job Description | ジョブ記述 | ユーザーからの入力 | parse job description |
| Playbook | プレイブック | 実行手順の定義 | execution playbook |
| Scrum Master | スクラムマスター | タスク管理スピリット | Scrum Master Spirit |
| Architect | アーキテクト | 設計スピリット | Architect Spirit |
| Issue Router | イシュールーター | タスク振り分けコンポーネント | Issue Router assigns tasks |
| Workload Monitor | ワークロードモニター | 負荷監視コンポーネント | Workload Monitor tracks load |

**注意**: 初出時は英語併記を推奨します。
- 例: Spirit（スピリット）、Necromancer（ネクロマンサー）

---

## そのまま英語を使用する用語

以下の用語は、技術業界で広く使われているため、英語のまま使用します。

### 略語・頭字語

- **API** - Application Programming Interface
- **CLI** - Command Line Interface
- **LLM** - Large Language Model
- **PR** - Pull Request
- **GPT** - Generative Pre-trained Transformer

### データフォーマット

- **JSON** - JavaScript Object Notation
- **YAML** - YAML Ain't Markup Language

### 固有名詞

- **Git** - バージョン管理システム
- **GitHub** - Gitホスティングサービス
- **GitLab** - Gitホスティングサービス
- **Bitbucket** - Gitホスティングサービス
- **Docker** - コンテナプラットフォーム
- **Kubernetes** - コンテナオーケストレーション
- **OpenAI** - AI研究組織

### その他

- **Webhook** - 「Webhook」または「ウェブフック」

---

## 英語併記が推奨される用語

初出時は英語併記、以降は日本語のみで使用します。

| 英語 | 日本語 | 初出時の表記 |
|------|--------|-------------|
| Hook | フック | Hook（フック） |
| Agent | エージェント | Agent（エージェント） |
| Event | イベント | Event（イベント） |
| Queue | キュー | Queue（キュー） |

**例**:
```
初出: "Hook（フック）を使用してタスクを自動実行します。"
以降: "フックが正常に動作しています。"
```

---

## 状態・ステータス用語

タスクやシステムの状態を表す用語です。

| 英語 | 日本語 | 文脈 |
|------|--------|------|
| Ready | 準備完了 | タスク状態 |
| Running | 実行中 | タスク状態 |
| Blocked | ブロック中 | タスク状態 |
| Done | 完了 | タスク状態 |
| Failed | 失敗 | タスク状態 |
| Pending | 保留中 | タスク状態 |
| In Progress | 進行中 | 一般的な状態 |
| Completed | 完了 | 一般的な状態 |

---

## 動詞の翻訳

よく使われる動詞の標準的な翻訳です。

| 英語 | 日本語 |
|------|--------|
| create | 作成する |
| update | 更新する |
| delete | 削除する |
| execute | 実行する |
| implement | 実装する |
| deploy | デプロイする |
| monitor | 監視する |
| validate | 検証する |
| configure | 設定する |
| initialize | 初期化する |
| allocate | 割り当てる |
| release | 解放する |
| schedule | スケジュールする |
| dispatch | ディスパッチする |

---

## よく使われるフレーズ

ドキュメントで頻出するフレーズの翻訳です。

| 英語 | 日本語 |
|------|--------|
| Quick Start | クイックスタート |
| Getting Started | はじめに |
| Installation | インストール |
| Configuration | 設定 |
| Usage | 使用方法 |
| Examples | 使用例 |
| API Reference | APIリファレンス |
| Troubleshooting | トラブルシューティング |
| Best Practices | ベストプラクティス |
| Architecture | アーキテクチャ |
| Design | 設計 |
| Requirements | 要件 |
| Overview | 概要 |
| Table of Contents | 目次 |
| See Also | 関連ドキュメント |
| Note | 注意 |
| Warning | 警告 |
| Tip | ヒント |

---

## 翻訳時の注意事項

### 1. コードブロック内の扱い

**変数名・関数名は英語のまま**
```python
# ❌ 間違い
def タスクを作成():
    pass

# ✅ 正しい
def create_task():
    pass
```

**コメントは日本語化**
```python
# ❌ 間違い
# Create a new task
task = Task()

# ✅ 正しい
# 新しいタスクを作成
task = Task()
```

### 2. コマンド例の説明

```bash
# ❌ 間違い
# Install dependencies
pip install -r requirements.txt

# ✅ 正しい
# 依存関係をインストール
pip install -r requirements.txt
```

### 3. ファイル名・パス

**変更しない**
```
❌ README.md → 読んでください.md
✅ README.md → README.md
```

### 4. 環境変数名

**変更しない**
```
❌ GITHUB_TOKEN → ギットハブトークン
✅ GITHUB_TOKEN → GITHUB_TOKEN
```

### 5. 技術用語の統一

**統一された訳語を使用**
```
❌ Task → 「課題」「作業」「仕事」
✅ Task → 常に「タスク」
```

### 6. 文体の使い分け

| ドキュメントタイプ | 文体 | スタイル |
|------------------|------|---------|
| README | 敬体（です・ます調） | 親しみやすく、わかりやすい |
| 仕様書 | 常体（だ・である調） | 正確で、技術的に詳細 |
| ガイド | 敬体（です・ます調） | 手順を明確に、実用的 |
| リファレンス | 常体（だ・である調） | 簡潔で、網羅的 |

---

## 用語集の更新

この用語集は継続的に更新されます。新しい用語や翻訳の改善案がある場合は、以下の手順で提案してください：

1. `.kiro/specs/documentation-i18n-japanese/glossary.yaml` を確認
2. 新しい用語を適切なカテゴリに追加
3. 使用例と注意事項を記載
4. このドキュメント（GLOSSARY.md）も更新

---

## 関連ドキュメント

- [requirements.md](requirements.md) - 翻訳プロジェクトの要件定義
- [design.md](design.md) - 翻訳システムの設計
- [tasks.md](tasks.md) - 翻訳タスクリスト
- [glossary.yaml](glossary.yaml) - 機械可読な用語集データ

---

**最終更新**: 2025-12-06  
**バージョン**: 1.0.0
