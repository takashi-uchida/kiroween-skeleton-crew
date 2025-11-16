# NecroCode: 新アーキテクチャ設計

## ゴール
- Spec受領からPR生成までをフル自動化し、タスク単位で独立したエージェントが開発できるようにする。
- ローカルマシン上で複数のリポジトリ/ワークスペースを並列利用し、さらにコンテナ化したAgent Runnerを水平スケール可能にする。
- 各タスクの状態・成果物・イベントを一元管理し、失敗時の再実行や監査を容易にする。

## コンポーネント

| コンポーネント | 役割 |
| --- | --- |
| Spec Intake | PM/ユーザーから受けたSpecをPlannerが扱える形式に変換（cc-sddは使わず、既存Markdown構造をパース）。 |
| Task Planner | Specをタスクに分解し、依存関係・優先度・必要スキル/ツール情報を付与。成果は`Task Registry`へ保存。 |
| Task Registry | タスクセットのバージョン管理、状態管理（Ready/Running/Blocked/Done）、イベント履歴を保持する永続ストア。 |
| Repo Pool Manager | ローカル上に複数のクローン済みリポジトリスロット（`workspace-{repo}-{slot}`）を準備/割当/クリーンアップ。 |
| Dispatcher | Readyタスクを監視し、必要スキルと利用可能なエージェントプールに基づいて実行予約。Repo Poolからスロットを確保してRunnerに情報を渡す。 |
| Agent Pool | Agent Runnerのプール定義。`local-process`/`docker`/`k8s`/`remote-host`など複数の実行ターゲットを抽象化する。各プールは最大同時実行数とリソースクォータを持つ。 |
| Agent Runner | 受け取ったタスクを実行するワーカー。コンテナベースで起動し、ワークスペースをマウントして`fetch→rebase→branch→実装→テスト→push`を行い、成果物を保存。 |
| Artifact Store | diff/ログ/テスト結果等の成果物を保管するストレージ。Runner終了時にアップロードし、PR作成や監査で参照。 |
| Review & PR Service | Runner成果物をもとにPRを作成、テンプレート（タスクID/要約/テスト結果など）を生成し、CI状態を連携。PRイベントをTask Registryに反映。 |
| Cleanup & Dependency Notifier | マージ後にブランチ削除/ワークスペース返却/依存タスクへのReady通知を行う。 |

## データモデル（例）
```jsonc
{
  "taskset_version": 3,
  "tasks": [
    {
      "id": "A-1",
      "title": "ドキュメント生成基盤",
      "status": "ready",
      "dependencies": [],
      "required_skill": "doc-agent",
      "repo": "workspace-docs",
      "priority": 1,
      "metadata": {
        "acceptance": [
          "README更新",
          "テスト: test_documentation_spirit.py"
        ]
      }
    }
  ]
}
```

Task Registryはタスクごとに以下を保持する。
- `assigned_slot`: Repo Poolで割り当てた`workspace-docs-slot2`など。
- `reserved_branch`: `feature/task-docs-A-1`のようなブランチ名。
- `runner_id`: 実行中Runnerの識別子（再実行時に空になる）。
- `artifacts`: diff/log/test結果のURI一覧。

## ワークスペースとエージェントのスケーリング

### Repo Pool Manager
- ルートディレクトリ例: `~/.kiro/workspaces/{repo}/{slot}`。
- `slot.lock`を用いた排他制御で同一スロットの二重利用を防ぐ。
- Slot取得時: `git fetch --all`で最新化 → `git clean -fdx`で前回の残骸を除去 → Dispatcherへ`slot_path`を返却。
- Runnerから返却されると再度`git clean -fdx`を実行し、即再利用可能にする。

### Agent Pool & Runner
- プール設定例:
```yaml
pools:
  local:
    type: process
    max_concurrency: 2
  docker:
    type: docker
    image: kiro/runner:latest
    max_concurrency: 4
    mount_repo_pool: true
  k8s:
    type: kubernetes
    namespace: kiro-agents
    job_template: manifests/runner-job.yaml
    max_concurrency: 10
```
- Dispatcherはタスクの`required_skill`から対応するプールを選択（例: `frontend-skill`はdocker、`infra-skill`はk8s）。
- Runnerは完全ステートレス。起動時に環境変数 or Secret MountからGitトークンやAPIキーを取得し、終了と同時に破棄される。
- Runner内の処理:
  1. Repo Pool割当パスをマウント。
  2. `git checkout main && git fetch origin && git rebase origin/main`。
  3. `git checkout -b feature/task-{spec}-{task}`（既に存在する場合は`git reset --hard`で更新）。
  4. スキル定義のプレイブックに従い編集/テスト/フォーマット。
  5. `git push origin feature/...`。
  6. テスト結果/ログをArtifact Storeへアップロード。
  7. Runner終了 → Repo Poolへslot返却。

## フロー

```
Spec Intake
   │ 1. Spec受領
   ▼
Task Planner
   │ 2. タスクリスト生成
   ▼
Task Registry
   │ 3. Readyタスクイベント
   ▼
Dispatcher ──┬─► Repo Pool Manager（slot割当）
             │
             └─► Agent Pool（空きRunnerを選択）
   ▼
Agent Runner（コンテナ）
   │ 4. fetch/rebase/branch
   │ 5. 実装・テスト・push
   ▼
Artifact Store（diff/log/test）
   │ 6. 結果通知
   ▼
Review & PR Service
   │ 7. PR作成＋CIトリガ
   ▼
Task Registry（ステータス更新）
   │ 8. Done → 依存タスクReady化
   ▼
Cleanup & Dependency Notifier
```

## イベントと監査
- `TaskCreated`, `TaskUpdated`, `TaskReady`, `TaskAssigned`, `RunnerStarted`, `RunnerFinished`, `PROpened`, `PRMerged`, `TaskCompleted`などのイベントをJSON LinesまたはSQLiteに蓄積。
- 再実行・障害調査に備えてRunnerの標準出力/標準エラーをArtifact Storeに保存。
- Repo Pool状態（slot利用状況、最新コミット）もメトリクス化して監視。

## セキュリティと権限
- 各Runnerに付与するGitトークンは`task-scope`で限定し、PR作成・ブランチpushのみに許可。
+- SecretsはK8s Secret / Docker secrets / 環境変数などで注入し、ログには出力しない。
- Repo Poolのアクセス権はホストユーザー権限で統一し、コンテナからは読み書き専用マウントに制限。

## 今後の実装ステップ
1. Repo Pool ManagerのPoC実装（slot割当・clean・再利用）。
2. タスクリスト生成ツール（Markdown→JSON）の実装とTask Registryスキーマ定義。
3. Dispatcher + Agent Pool制御のサービス化（優先度キュー、max concurrency制御、失敗時リトライ）。
4. コンテナRunnerのベースイメージ作成（依存ツール、テスト実行環境、Artifact uploader）。
5. Review & PR Serviceの自動PRテンプレート生成とGitホストAPI連携。
6. 監査/イベントストアの実装とダッシュボード化。

この設計により、ローカルマシンのリソースを最大限活用しつつ、必要に応じてコンテナRunnerをスケールアウトし、タスクごとの完全自動化されたブランチ/PRフローを実現できる。

