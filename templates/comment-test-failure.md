## ⚠️ Test Failure Detected

{{message | default("Automated tests have failed for this pull request.")}}

---

### 🧪 Test Results Summary

| Metric | Value |
|--------|-------|
| **Total Tests** | {{test_results.total}} |
| **Passed** | ✅ {{test_results.passed}} ({{(test_results.passed / test_results.total * 100) | round(1)}}%) |
| **Failed** | ❌ {{test_results.failed}} ({{(test_results.failed / test_results.total * 100) | round(1)}}%) |
| **Skipped** | ⏭️ {{test_results.skipped}} |
{% if test_results.duration %}
| **Duration** | ⏱️ {{test_results.duration}}s |
{% endif %}

---

{% if test_results.failed_tests %}
### ❌ Failed Tests

{% for test in test_results.failed_tests[:10] %}
#### {{loop.index}}. `{{test.name}}`

{% if test.error %}
```
{{test.error}}
```
{% endif %}

{% if test.stack_trace %}
<details>
<summary>Stack Trace</summary>

```
{{test.stack_trace}}
```

</details>
{% endif %}

{% endfor %}

{% if test_results.failed_tests|length > 10 %}
<details>
<summary>Show {{test_results.failed_tests|length - 10}} more failed tests</summary>

{% for test in test_results.failed_tests[10:] %}
- **{{test.name}}**: {{test.error | truncate(100)}}
{% endfor %}

</details>
{% endif %}
{% endif %}

---

### 🔗 Resources

{% if error_log_url %}
- 📄 [View Full Error Log]({{error_log_url}})
{% endif %}
{% if ci_url %}
- 🔄 [View CI Build]({{ci_url}})
{% endif %}
{% if artifact_links %}
{% for name, url in artifact_links.items() %}
- 📦 [{{name}}]({{url}})
{% endfor %}
{% endif %}

---

### 🎯 Next Steps

{% if next_steps %}
{% for step in next_steps %}
{{loop.index}}. {{step}}
{% endfor %}
{% else %}
1. Review the failed tests above
2. Fix the issues in your code
3. Push your changes to trigger a new CI run
4. Verify all tests pass
{% endif %}

---

### 💡 Tips

- Run tests locally before pushing: `npm test` or `pytest`
- Check the error logs for detailed information
- If you need help, mention `@team-lead` or `@qa-team`

---

<sub>🤖 Posted by **NecroCode Review & PR Service** | Last updated: {{timestamp}}</sub>
