## Task: {{task_id}} - {{title}}

### 📋 Description

{{description}}

{% if acceptance_criteria %}
### ✅ Acceptance Criteria

{% for criterion in acceptance_criteria %}
- [ ] {{criterion}}
{% endfor %}
{% endif %}

{% if test_results %}
### 🧪 Test Results

{{test_results}}
{% endif %}

{% if artifact_links %}
### 📦 Artifacts

{{artifact_links}}
{% endif %}

{% if execution_logs %}
### 📝 Execution Logs

{{execution_logs}}
{% endif %}

{% if execution_time %}
### ⏱️ Execution Time

Total execution time: **{{execution_time}}s**
{% endif %}

{% if custom_sections %}
{% for section_title, section_content in custom_sections.items() %}
### {{section_title}}

{{section_content}}
{% endfor %}
{% endif %}

---

<details>
<summary>📚 Template Information</summary>

This PR was automatically created by **NecroCode Review & PR Service**.

**Template Variables Available:**
- `task_id`: Task identifier
- `title`: Task title
- `description`: Task description
- `acceptance_criteria`: List of acceptance criteria
- `test_results`: Test execution results
- `artifact_links`: Links to artifacts (diffs, logs, reports)
- `execution_logs`: Execution log details
- `execution_time`: Total execution time in seconds
- `custom_sections`: Custom sections added via API

**Customization:**
You can customize this template by:
1. Editing `templates/pr-template.md`
2. Adding custom sections via `PRTemplateEngine.set_custom_section()`
3. Passing custom data via `create_pr(custom_data={...})`

</details>
