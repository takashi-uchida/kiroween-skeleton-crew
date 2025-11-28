{{message}}

{% if details %}
### 📋 Details

{% for key, value in details.items() %}
- **{{key}}:** {{value}}
{% endfor %}
{% endif %}

{% if test_results %}
### 🧪 Test Results Summary

- **Total Tests:** {{test_results.total}}
- **Passed:** ✅ {{test_results.passed}}
- **Failed:** ❌ {{test_results.failed}}
- **Skipped:** ⏭️ {{test_results.skipped}}
{% if test_results.duration %}
- **Duration:** {{test_results.duration}}s
{% endif %}

{% if test_results.failed_tests %}
#### Failed Tests

{% for test in test_results.failed_tests[:10] %}
- **{{test.name}}**
  ```
  {{test.error}}
  ```
{% endfor %}

{% if test_results.failed_tests|length > 10 %}
*... and {{test_results.failed_tests|length - 10}} more failed tests*
{% endif %}
{% endif %}
{% endif %}

{% if error_log_url %}
### 🔗 Links

- [View Full Error Log]({{error_log_url}})
{% if artifact_links %}
{% for name, url in artifact_links.items() %}
- [{{name}}]({{url}})
{% endfor %}
{% endif %}
{% endif %}

{% if next_steps %}
### 🎯 Next Steps

{% for step in next_steps %}
- {{step}}
{% endfor %}
{% endif %}

---

<sub>🤖 Posted by **NecroCode Review & PR Service** | [Documentation](https://github.com/necrocode/docs)</sub>
