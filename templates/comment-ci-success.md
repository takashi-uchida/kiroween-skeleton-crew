## ✅ CI Checks Passed

{{message | default("All continuous integration checks have passed successfully!")}}

---

### 🎉 Build Status

| Check | Status | Duration |
|-------|--------|----------|
{% if ci_checks %}
{% for check in ci_checks %}
| {{check.name}} | ✅ Passed | {{check.duration}}s |
{% endfor %}
{% else %}
| All Checks | ✅ Passed | {{duration | default("N/A")}} |
{% endif %}

---

{% if test_results %}
### 🧪 Test Results

- **Total Tests:** {{test_results.total}}
- **Passed:** ✅ {{test_results.passed}} (100%)
- **Failed:** ❌ 0
- **Duration:** ⏱️ {{test_results.duration}}s

{% if test_coverage %}
### 📊 Code Coverage

- **Line Coverage:** {{test_coverage.line}}%
- **Branch Coverage:** {{test_coverage.branch}}%
- **Function Coverage:** {{test_coverage.function}}%

{% if test_coverage.line >= 80 %}
✅ Coverage meets the minimum threshold (80%)
{% else %}
⚠️ Coverage is below the minimum threshold (80%)
{% endif %}
{% endif %}
{% endif %}

---

### 🚀 Next Steps

{% if auto_merge_enabled %}
- ✅ This PR is eligible for auto-merge
- 🔄 Waiting for required approvals ({{approvals_received}}/{{approvals_required}})
{% if approvals_received >= approvals_required %}
- 🎯 **Ready to merge!** This PR will be automatically merged soon.
{% endif %}
{% else %}
- ✅ This PR is ready for review
- 👀 Waiting for reviewer approval
- 🔀 Manual merge required after approval
{% endif %}

---

{% if draft_pr %}
### 📝 Draft Status

This PR is currently in **draft** mode.

{% if convert_draft_on_success %}
✅ **Converting to ready for review** since all CI checks passed.
{% else %}
💡 Mark as "Ready for review" when you're done with changes.
{% endif %}
{% endif %}

---

### 🔗 Links

{% if ci_url %}
- [View CI Build Details]({{ci_url}})
{% endif %}
{% if artifact_links %}
{% for name, url in artifact_links.items() %}
- [{{name}}]({{url}})
{% endfor %}
{% endif %}

---

### 📋 Pre-Merge Checklist

- [x] All CI checks passed
- [x] All tests passed
{% if test_coverage %}
- [{{  "x" if test_coverage.line >= 80 else " " }}] Code coverage meets threshold
{% endif %}
- [{{  "x" if approvals_received >= approvals_required else " " }}] Required approvals received ({{approvals_received}}/{{approvals_required}})
- [ ] Final review completed
- [ ] Ready to merge

---

<sub>🤖 Posted by **NecroCode Review & PR Service** | CI completed at: {{timestamp}}</sub>
