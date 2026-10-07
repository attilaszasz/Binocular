---
description: Take next issue from GitHub
subagent: false
---

Review the repository’s open GitHub issues and choose one that is actionable, well-scoped, and not already being addressed. Briefly explain your choice.

Follow the repository’s instructions and required development workflow. Implement the fix, add or update tests, and run the relevant checks. Continue through completion unless blocked by missing access, material ambiguity, or a destructive action requiring approval.

When local validation passes, commit and push the changes to GitHub. Do not create a release or release tag. Monitor the CI pipelines triggered by the push until they finish. Investigate and fix failures caused by your changes, then push again and monitor the new runs.

Close the issue only after the fix is complete and all required checks pass. Include a concise explanation, links to the relevant commits and successful pipeline runs, and concrete validation evidence. If implementation or validation remains incomplete, leave the issue open and report the blocker.