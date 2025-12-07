# PR Service テンプレート

このディレクトリには、NecroCode Review & PR Serviceがプルリクエストの説明とコメントを生成するために使用するJinja2テンプレートが含まれています。

## 利用可能なテンプレート

### プルリクエストテンプレート

#### `pr-template.md` (デフォルト)

プルリクエスト説明のデフォルトテンプレート。以下を含みます：
- タスクIDとタイトル
- 説明
- 受け入れ基準
- テスト結果
- アーティファクト
- 実行ログ
- カスタムセクション

**使用方法:**
```python
config = PRServiceConfig(
    template=TemplateConfig(
        template_path="templates/pr-template.md"
    )
)
```

#### `pr-template-comprehensive.md`

追加セクションを含む包括的なテンプレート：
- 依存関係
- 実装の詳細
- メトリクス（実行時間、変更行数）
- レビューチェックリスト
- デプロイメモ
- スクリーンショット/デモ
- 関連リンク

**使用方法:**
```python
config = PRServiceConfig(
    template=TemplateConfig(
        template_path="templates/pr-template-comprehensive.md"
    )
)
```

### コメントテンプレート

#### `comment-template.md` (デフォルト)

PRコメントのデフォルトテンプレート。以下を含みます：
- メッセージ
- 詳細（キー・バリューペア）
- テスト結果サマリー
- 失敗したテスト
- ログとアーティファクトへのリンク
- 次のステップ

**使用方法:**
```python
config = PRServiceConfig(
    template=TemplateConfig(
        comment_template_path="templates/comment-template.md"
    )
)
```

#### `comment-test-failure.md`

テスト失敗コメント用の専用テンプレート。以下を含みます：
- テスト結果テーブル
- エラー付きの失敗したテストの詳細
- スタックトレース（折りたたみ可能）
- リソースとリンク
- 次のステップ
- 解決のヒント

**使用方法:**
```python
# post_test_failure_comment()によって自動的に使用されます
pr_service.post_test_failure_comment(
    pr_id="123",
    test_results={...}
)
```

#### `comment-conflict.md`

マージコンフリクト通知用のテンプレート。以下を含みます：
- コンフリクトの詳細
- コンフリクトしているファイルのリスト
- 解決手順（CLI、Web、IDE）
- 解決チェックリスト
- ヒントとリソース

**使用方法:**
```python
# コンフリクトが検出された時に自動的に使用されます
pr_service.post_conflict_comment(
    pr_id="123",
    conflict_details="..."
)
```

#### `comment-ci-success.md`

CI成功通知用のテンプレート。以下を含みます：
- ビルドステータステーブル
- テスト結果
- コードカバレッジ
- 次のステップ（自動マージステータス）
- マージ前チェックリスト

**使用方法:**
```python
# CI monitorによって成功時に自動的に使用されます
# または手動で：
pr_service.post_comment(
    pr_id="123",
    message="CI passed!",
    use_template=True
)
```

## テンプレート変数

### 共通変数

全てのテンプレートで利用可能：

- `message`: メインメッセージテキスト
- `timestamp`: 現在のタイムスタンプ
- `details`: キー・バリュー詳細の辞書

### PRテンプレート変数

PRテンプレートで利用可能：

- `task_id`: タスク識別子（例："1.1"）
- `title`: タスクタイトル
- `description`: タスク説明
- `state`: タスク状態（DONE、IN_PROGRESSなど）
- `created_at`: タスク作成タイムスタンプ
- `acceptance_criteria`: 受け入れ基準のリスト
- `dependencies`: タスク依存関係のリスト
- `test_results`: フォーマット済みテスト結果
- `artifact_links`: フォーマット済みアーティファクトリンク
- `execution_logs`: フォーマット済み実行ログ
- `execution_time`: 実行時間（秒）
- `source_branch`: ソースブランチ名
- `target_branch`: ターゲットブランチ名
- `custom_sections`: カスタムセクションの辞書

### コメントテンプレート変数

コメントテンプレートで利用可能：

- `test_results`: テスト統計情報の辞書
  - `total`: テストの総数
  - `passed`: 成功したテストの数
  - `failed`: 失敗したテストの数
  - `skipped`: スキップされたテストの数
  - `duration`: テスト実行時間（秒）
  - `failed_tests`: 失敗したテストの詳細リスト
- `error_log_url`: エラーログへのURL
- `artifact_links`: アーティファクト名からURLへの辞書
- `next_steps`: 次のステップのリスト
- `ci_url`: CIビルドへのURL
- `ci_checks`: CIチェック結果のリスト
- `test_coverage`: コードカバレッジ統計
- `conflicting_files`: コンフリクトしているファイルのリスト
- `conflict_details`: 詳細なコンフリクト情報
- `auto_merge_enabled`: 自動マージが有効かどうか
- `approvals_received`: 受け取った承認の数
- `approvals_required`: 必要な承認の数
- `draft_pr`: PRがドラフトモードかどうか

## カスタムテンプレートの作成

### 基本テンプレート

新しいJinja2テンプレートファイルを作成：

```markdown
## {{title}}

{{description}}

### 結果
{{test_results}}

---
*NecroCodeによって生成*
```

### カスタムテンプレートの使用

```python
config = PRServiceConfig(
    template=TemplateConfig(
        template_path="templates/my-custom-template.md"
    )
)

pr_service = PRService(config)
```

### カスタムデータの追加

```python
pr = pr_service.create_pr(
    task=task,
    branch_name="feature/my-feature",
    custom_data={
        "my_custom_field": "カスタム値",
        "another_field": 123
    }
)
```

テンプレート内でのアクセス：
```markdown
### カスタムデータ
- My Field: {{my_custom_field}}
- Another: {{another_field}}
```

### カスタムセクションの追加

```python
engine = pr_service.template_engine
engine.set_custom_section("Breaking Changes", "なし")
engine.set_custom_section("Migration Guide", "docs/migration.mdを参照")
```

## テンプレートのベストプラクティス

### 1. 条件ブロックの使用

データが利用可能な場合のみセクションを表示：

```jinja2
{% if test_results %}
### テスト結果
{{test_results}}
{% endif %}
```

### 2. デフォルト値の提供

オプション変数にデフォルト値を使用：

```jinja2
{{message | default("メッセージが提供されていません")}}
```

### 3. リストのフォーマット

リストを適切に反復処理：

```jinja2
{% for criterion in acceptance_criteria %}
- [ ] {{criterion}}
{% endfor %}
```

### 4. フィルターの使用

Jinja2は便利なフィルターを提供：

```jinja2
{{description | truncate(100)}}  # 100文字に切り詰め
{{value | round(2)}}              # 小数点以下2桁に丸める
{{text | upper}}                  # 大文字に変換
```

### 5. 折りたたみ可能なセクションの追加

長いコンテンツにはHTML detailsを使用：

```markdown
<details>
<summary>クリックして展開</summary>

{{long_content}}

</details>
```

### 6. リンクの含有

リンクでテンプレートをアクション可能に：

```markdown
- [ログを表示]({{log_url}})
- [CIビルド]({{ci_url}})
- [ドキュメント](https://docs.example.com)
```

## テンプレートのテスト

デプロイ前にテンプレートをテスト：

```python
from necrocode.review_pr_service import PRTemplateEngine, PRServiceConfig

config = PRServiceConfig(
    template=TemplateConfig(
        template_path="templates/my-template.md"
    )
)

engine = PRTemplateEngine(config)

# サンプルデータでテスト
result = engine.generate(
    task=sample_task,
    acceptance_criteria=["基準 1", "基準 2"],
    test_results={"total": 10, "passed": 10}
)

print(result)
```

## 使用例

完全な使用例については`examples/`ディレクトリを参照：

- `examples/pr_template_engine_example.py` - テンプレートエンジンの使用
- `examples/basic_pr_service_usage.py` - 基本的なPR作成
- `examples/github_setup.py` - GitHub設定

## トラブルシューティング

### テンプレートが見つからない

テンプレートパスが正しいことを確認：

```python
import os
template_path = "templates/pr-template.md"
assert os.path.exists(template_path), f"テンプレートが見つかりません: {template_path}"
```

### 変数が定義されていない

条件ブロックまたはデフォルト値を使用：

```jinja2
{% if variable %}
{{variable}}
{% else %}
*利用不可*
{% endif %}
```

または：

```jinja2
{{variable | default("利用不可")}}
```

### 構文エラー

テンプレート構文を検証：

```python
engine = PRTemplateEngine(config)
try:
    engine._load_template()
    print("✅ テンプレート構文は有効です")
except Exception as e:
    print(f"❌ テンプレート構文エラー: {e}")
```

## コントリビューション

新しいテンプレートを追加する際：

1. 命名規則に従う：`{type}-{purpose}.md`
2. 使用する全ての変数を文書化
3. 使用例を追加
4. 実際のデータでテスト
5. このREADMEを更新

## 関連情報

- [PR Service README](../necrocode/review_pr_service/README.md)
- [Jinja2ドキュメント](https://jinja.palletsprojects.com/)
- [Markdownガイド](https://www.markdownguide.org/)
