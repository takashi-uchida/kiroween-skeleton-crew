## タスク: {{task_id}} - {{title}}

### 📋 説明

{{description}}

{% if acceptance_criteria %}
### ✅ 受け入れ基準

{% for criterion in acceptance_criteria %}
- [ ] {{criterion}}
{% endfor %}
{% endif %}

{% if test_results %}
### 🧪 テスト結果

{{test_results}}
{% endif %}

{% if artifact_links %}
### 📦 アーティファクト

{{artifact_links}}
{% endif %}

{% if execution_logs %}
### 📝 実行ログ

{{execution_logs}}
{% endif %}

{% if execution_time %}
### ⏱️ 実行時間

合計実行時間: **{{execution_time}}秒**
{% endif %}

{% if custom_sections %}
{% for section_title, section_content in custom_sections.items() %}
### {{section_title}}

{{section_content}}
{% endfor %}
{% endif %}

---

<details>
<summary>📚 テンプレート情報</summary>

このPRは**NecroCode Review & PR Service**によって自動的に作成されました。

**利用可能なテンプレート変数:**
- `task_id`: タスク識別子
- `title`: タスクタイトル
- `description`: タスク説明
- `acceptance_criteria`: 受け入れ基準のリスト
- `test_results`: テスト実行結果
- `artifact_links`: アーティファクトへのリンク（差分、ログ、レポート）
- `execution_logs`: 実行ログの詳細
- `execution_time`: 合計実行時間（秒）
- `custom_sections`: API経由で追加されたカスタムセクション

**カスタマイズ:**
このテンプレートは以下の方法でカスタマイズできます：
1. `templates/pr-template.md`を編集
2. `PRTemplateEngine.set_custom_section()`経由でカスタムセクションを追加
3. `create_pr(custom_data={...})`経由でカスタムデータを渡す

</details>
