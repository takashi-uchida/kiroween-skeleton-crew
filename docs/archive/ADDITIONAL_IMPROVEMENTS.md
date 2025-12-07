# NecroCode 追加改善提案

## 現状分析

### ✅ 完了している項目
- Kiroネイティブアーキテクチャ
- Git Worktreeベースの並列実行
- LLMベースのTask Planner
- 進捗表示機能
- statusコマンド
- ディレクトリ構成の整理

### 🔍 改善が必要な領域

## 1. 未使用/未統合のコンポーネント

### 問題
以下のコンポーネントが実装されているが、新アーキテクチャと統合されていない：

```
necrocode/
├── artifact_store/      # 12ファイル - 未統合
├── review_pr_service/   # 12ファイル - 部分的に統合
├── dispatcher/          # 15ファイル - 旧アーキテクチャ
├── agent_runner/        # 20ファイル - 旧アーキテクチャ
└── orchestration/       # 3ファイル - 未統合
```

### 提案

#### Option A: 統合する
新アーキテクチャに必要なコンポーネントのみを統合：
- `review_pr_service` → GitHub PR自動作成に活用
- `artifact_store` → ビルド成果物の管理に活用

#### Option B: 削除する
使用されていないコンポーネントを削除：
- `dispatcher/` - 旧アーキテクチャ
- `agent_runner/` - 旧アーキテクチャ
- `orchestration/` - 未使用

#### 推奨: Option B（削除）
理由：
- 新アーキテクチャはシンプルさを重視
- 未使用コードは保守コストが高い
- 必要になったら再実装する方が効率的

## 2. インストールとセットアップの改善

### 問題
- `pip install -e .` が必要だが、setup.pyやpyproject.tomlがない
- 依存関係が明確でない
- インストール手順が不完全

### 提案

#### setup.pyの作成
```python
from setuptools import setup, find_packages

setup(
    name="necrocode",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "strandsagents>=0.1.0",
    ],
    entry_points={
        "console_scripts": [
            "necrocode=necrocode.cli:cli",
        ],
    },
)
```

#### 利点
- `necrocode` コマンドが直接使える
- 依存関係が自動インストール
- 配布が容易

## 3. エラーハンドリングの強化

### 問題
- タスク失敗時のエラーメッセージが不十分
- リトライ機能がない
- ログが保存されない

### 提案

#### エラーハンドリングモジュール
```python
# necrocode/error_handler.py
class ErrorHandler:
    def handle_task_error(self, task_id, error):
        # エラーログを保存
        # リトライを試行
        # ユーザーに詳細を表示
```

#### 実装内容
- タスク失敗時の詳細ログ
- 自動リトライ（--retry オプション）
- エラーログの保存（.kiro/logs/）
- リカバリー手順の提案

## 4. ドキュメントの改善

### 問題
- 実際の使用例が少ない
- トラブルシューティングガイドがない
- API仕様が不明確

### 提案

#### 追加ドキュメント
1. **TUTORIAL.md** - ステップバイステップのチュートリアル
2. **TROUBLESHOOTING.md** - よくある問題と解決方法
3. **API.md** - 各モジュールのAPI仕様
4. **CONTRIBUTING.md** - 貢献ガイドライン

## 5. テストカバレッジの向上

### 問題
- テストが4ファイルのみ
- 統合テストが不足
- CI/CDパイプラインがない

### 提案

#### テスト追加
```
tests/
├── unit/
│   ├── test_task_planner.py
│   ├── test_progress_monitor.py
│   └── test_cli.py
├── integration/
│   ├── test_end_to_end.py
│   └── test_parallel_execution.py
└── fixtures/
    └── sample_projects/
```

#### CI/CD
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: pytest tests/
```

## 6. パフォーマンスの最適化

### 問題
- 大量のタスクでのスケーラビリティが未検証
- メモリ使用量が不明
- 並列度の最適化が手動

### 提案

#### パフォーマンス監視
```python
# necrocode/performance_monitor.py
class PerformanceMonitor:
    def track_memory_usage(self):
        # メモリ使用量を追跡
    
    def optimize_workers(self, task_count):
        # 最適なワーカー数を自動計算
```

#### ベンチマーク
- 10タスク、50タスク、100タスクでのベンチマーク
- メモリ使用量の測定
- 最適なワーカー数の推奨

## 7. セキュリティの強化

### 問題
- タスクコンテキストに機密情報が含まれる可能性
- Worktreeのクリーンアップが不完全な場合がある
- LLM APIキーの管理が不明確

### 提案

#### セキュリティ機能
```python
# necrocode/security.py
class SecurityManager:
    def sanitize_context(self, context):
        # 機密情報をマスク
    
    def secure_cleanup(self, worktree_path):
        # 確実にクリーンアップ
```

## 優先度付き実装計画

### 🔥 最高優先度（即座に実施）

1. **未使用コンポーネントの削除**
   - dispatcher/, agent_runner/, orchestration/を削除
   - 理由: コードベースの簡素化、保守性向上

2. **setup.pyの作成**
   - インストールプロセスの改善
   - 理由: ユーザビリティ向上

3. **TUTORIAL.mdの作成**
   - 実際の使用例を追加
   - 理由: 新規ユーザーの学習曲線を緩和

### ⚡ 高優先度（1-2週間以内）

4. **エラーハンドリングの強化**
   - リトライ機能
   - エラーログの保存

5. **テストカバレッジの向上**
   - ユニットテスト追加
   - CI/CD設定

6. **TROUBLESHOOTING.mdの作成**
   - よくある問題の文書化

### 🎯 中優先度（1ヶ月以内）

7. **review_pr_serviceの統合**
   - GitHub PR自動作成機能

8. **パフォーマンス最適化**
   - ベンチマーク実施
   - 最適化

9. **API.mdの作成**
   - API仕様の文書化

### 📋 低優先度（将来的に）

10. **セキュリティ強化**
    - 機密情報のマスキング
    - セキュアなクリーンアップ

11. **Web UIの追加**
    - ブラウザベースのインターフェース

12. **プラグインシステム**
    - 拡張可能なアーキテクチャ

## 具体的な次のアクション

### 今すぐ実施可能

```bash
# 1. 未使用コンポーネントを削除
rm -rf necrocode/dispatcher necrocode/agent_runner necrocode/orchestration

# 2. setup.pyを作成
cat > setup.py << 'EOF'
from setuptools import setup, find_packages

setup(
    name="necrocode",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "necrocode=necrocode.cli:cli",
        ],
    },
)
EOF

# 3. インストール
pip install -e .

# 4. テスト
necrocode --help
```

### 今週中に実施

1. TUTORIAL.mdの作成
2. エラーハンドリングの実装
3. テストの追加

## まとめ

現在のNecroCodeは**基本機能は完成**していますが、以下の改善により**プロダクションレディ**になります：

- ✅ コードベースの簡素化（未使用コンポーネント削除）
- ✅ インストールプロセスの改善（setup.py）
- ✅ ドキュメントの充実（TUTORIAL.md等）
- ✅ エラーハンドリングの強化
- ✅ テストカバレッジの向上

これらの改善により、NecroCodeは**実用的で信頼性の高い**フレームワークになります！
