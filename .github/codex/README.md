# Codex review experiment

This repository supports two deliberately separate Codex review paths.

## Hosted Codex review

1. Connect the repository to Codex Cloud.
2. Enable Code Review in Codex settings.
3. On an experiment pull request, comment:

   ```text
   @codex review. Also read .github/review/code-review.md.
   ```

Codex Cloud owns execution and posts a standard GitHub review. No repository
workflow runs for this path.

## Repository-owned Codex Action review

1. Add an `OPENAI_API_KEY` repository secret.
2. Add the `codex-action-review` label to the experiment pull request.
3. The `Codex action PR review` workflow runs in GitHub Actions and posts its
   Markdown result as a pull-request conversation comment.

This first version intentionally posts one summary comment. Converting structured
findings into inline comments is deferred so the experiment can make that extra
integration overhead visible rather than hiding it.

## Safe experiment sequence

1. Merge the setup pull request containing these files.
2. Configure the Codex Cloud repository connection and the GitHub secret.
3. Open a separate draft experiment pull request containing known temporary
   defects.
4. Trigger both review paths on that same commit.
5. Compare finding accuracy, evidence, noise, latency, and presentation.
6. Close the experiment pull request without merging it.
