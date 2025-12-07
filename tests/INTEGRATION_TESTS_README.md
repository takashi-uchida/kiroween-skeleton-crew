# 統合テストガイド

このガイドでは、Agent Runnerの統合テストの実行方法について説明します。

## テストファイル

### 1. 外部サービス統合（`test_external_services_integration.py`）
Task Registry、Repo Pool Manager、Artifact Storeとの統合をテストします。

**要件:**
- 外部サービスが実行されている必要があります
- サービスURLの環境変数を設定

**実行:**
```bash
# サービスURLを設定（オプション、デフォルトはlocalhost）
export TASK_REGISTRY_URL="http://localhost:8080"
export REPO_POOL_URL="http://localhost:8081"
export ARTIFACT_STORE_URL="http://localhost:8082"

# 統合テストを有効化
export SKIP_INTEGRATION_TESTS="false"

# テストを実行
pytest tests/test_external_services_integration.py -v
```

### 2. LLM統合（`test_llm_integration.py`）
LLMサービス（OpenAI）との統合をテストします。

**要件:**
- 有効なOpenAI APIキー
- テストによりAPI料金が発生する可能性があります

**実行:**
```bash
# APIキーを設定
export OPENAI_API_KEY="your-api-key-here"

# LLMテストを有効化
export SKIP_LLM_TESTS="false"

# テストを実行
pytest tests/test_llm_integration.py -v -m llm
```

### 3. エンドツーエンドテスト（`test_runner_e2e.py`）
完全なタスク実行ワークフローをテストします。

**要件:**
- Gitがインストールされ設定されている
- 一時ワークスペース用の十分なディスク容量

**実行:**
```bash
# E2Eテストを有効化
export SKIP_E2E_TESTS="false"

# テストを実行
pytest tests/test_runner_e2e.py -v -m e2e
```

### 4. パフォーマンステスト（更新済み）
LLM呼び出しのオーバーヘッドを含む実行パフォーマンスをテストします。

**実行:**
```bash
# パフォーマンステストを実行
pytest tests/test_runner_performance.py -v -m performance
pytest tests/test_parallel_runners.py -v -m performance
```

## テストマーカー

pytestマーカーを使用して特定のテストカテゴリを実行：

```bash
# 統合テストのみ
pytest -v -m integration

# LLMテストのみ
pytest -v -m llm

# E2Eテストのみ
pytest -v -m e2e

# パフォーマンステストのみ
pytest -v -m performance

# 低速テストのみ
pytest -v -m slow

# 低速テストを除外
pytest -v -m "not slow"
```

## すべてのテストの実行

```bash
# すべてのテストを実行（サービスを有効化）
export SKIP_INTEGRATION_TESTS="false"
export SKIP_LLM_TESTS="false"
export SKIP_E2E_TESTS="false"
export OPENAI_API_KEY="your-api-key"

pytest tests/test_external_services_integration.py \
       tests/test_llm_integration.py \
       tests/test_runner_e2e.py \
       -v
```

## CI/CD設定

### GitHub Actionsの例

```yaml
name: 統合テスト

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    
    services:
      task-registry:
        image: task-registry:latest
        ports:
          - 8080:8080
      
      repo-pool:
        image: repo-pool:latest
        ports:
          - 8081:8081
      
      artifact-store:
        image: artifact-store:latest
        ports:
          - 8082:8082
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Pythonのセットアップ
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: 依存関係のインストール
        run: |
          pip install -r requirements.txt
          pip install pytest
      
      - name: 統合テストの実行
        env:
          SKIP_INTEGRATION_TESTS: "false"
          TASK_REGISTRY_URL: "http://localhost:8080"
          REPO_POOL_URL: "http://localhost:8081"
          ARTIFACT_STORE_URL: "http://localhost:8082"
        run: |
          pytest tests/test_external_services_integration.py -v
      
      - name: E2Eテストの実行
        env:
          SKIP_E2E_TESTS: "false"
        run: |
          pytest tests/test_runner_e2e.py -v
```

## トラブルシューティング

### テストがスキップされる
- 環境変数が正しく設定されているか確認
- `SKIP_*_TESTS`変数が`"false"`（文字列、ブール値ではない）に設定されているか確認

### 外部サービステストが失敗する
- サービスが実行されているか確認: `curl http://localhost:8080/health`
- サービスURLが正しいか確認
- ネットワーク接続を確認

### LLMテストが失敗する
- APIキーが有効か確認
- APIレート制限を確認
- 十分なAPIクレジットがあるか確認

### E2Eテストが失敗する
- Gitがインストールされているか確認: `git --version`
- ディスク容量が利用可能か確認
- ファイルのパーミッションを確認

## テスト統計

- **外部サービス統合**: 23テスト
- **LLM統合**: 20テスト
- **エンドツーエンド**: 18テスト
- **パフォーマンス更新**: 5テスト強化
- **新規テスト合計**: 61

## パフォーマンスベンチマーク

期待されるパフォーマンス範囲（モック実装使用時）：

- 単一タスク実行: < 30秒
- ワークスペース準備: < 5秒
- コミットとプッシュ: < 5秒
- アーティファクトアップロード: < 10秒
- LLM呼び出しオーバーヘッド: 合計時間の30-50%
- 並列高速化: > 1.5倍

## 注意事項

- 統合テストは冪等性を持つように設計されています
- テストは実行後にリソースをクリーンアップします
- 一時ワークスペースはシステムの一時ディレクトリに作成されます
- テストは外部依存関係を減らすために適切な場所でモックを使用します
- パフォーマンステストはリグレッション検出のためのベースラインメトリクスを提供します

## サポート

問題や質問がある場合：
1. 詳細なエラーメッセージについてテスト出力を確認
2. ソースファイル内のテストドキュメントを確認
3. 環境設定を確認
4. 外部サービスの問題についてサービスログを確認
