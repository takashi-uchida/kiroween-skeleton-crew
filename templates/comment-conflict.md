## ⚠️ Merge Conflicts Detected

{{message | default("This pull request has merge conflicts that must be resolved before it can be merged.")}}

---

### 🔀 Conflict Details

{% if conflict_details %}
{{conflict_details}}
{% endif %}

{% if conflicting_files %}
### 📁 Conflicting Files

{% for file in conflicting_files %}
- `{{file}}`
{% endfor %}
{% endif %}

---

### 🛠️ How to Resolve

#### Option 1: Using Git Command Line

```bash
# Update your local branch
git checkout {{source_branch}}
git fetch origin
git merge origin/{{target_branch}}

# Resolve conflicts in your editor
# After resolving, stage the changes
git add .

# Complete the merge
git commit -m "Resolve merge conflicts with {{target_branch}}"

# Push the changes
git push origin {{source_branch}}
```

#### Option 2: Using GitHub Web Interface

1. Click the "Resolve conflicts" button below
2. Edit the conflicting files in the web editor
3. Mark each conflict as resolved
4. Click "Commit merge" when done

#### Option 3: Using Your IDE

Most modern IDEs (VS Code, IntelliJ, etc.) have built-in merge conflict resolution tools:

1. Pull the latest changes from `{{target_branch}}`
2. Merge `{{target_branch}}` into your branch
3. Use your IDE's conflict resolution tool
4. Commit and push the resolved changes

---

### 📋 Conflict Resolution Checklist

- [ ] Pull latest changes from `{{target_branch}}`
- [ ] Resolve all conflicts in affected files
- [ ] Test the code after resolution
- [ ] Ensure all tests still pass
- [ ] Commit and push the resolved changes
- [ ] Verify conflicts are resolved in this PR

---

### 💡 Tips

- **Don't panic!** Merge conflicts are normal in collaborative development
- **Communicate:** If you're unsure about a conflict, ask the author of the conflicting code
- **Test thoroughly:** After resolving conflicts, make sure everything still works
- **Keep it clean:** Remove conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) from your code

---

### 🔗 Resources

- [GitHub: Resolving Merge Conflicts](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/addressing-merge-conflicts)
- [Git Documentation: Merge Conflicts](https://git-scm.com/docs/git-merge#_how_conflicts_are_presented)

---

{% if recheck_info %}
### 🔄 Automatic Re-check

This PR will be automatically re-checked for conflicts:
- After you push new commits
- Periodically every {{recheck_interval}} minutes
- When the target branch is updated

{% endif %}

---

<sub>🤖 Posted by **NecroCode Review & PR Service** | Detected at: {{timestamp}}</sub>
