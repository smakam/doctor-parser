# Codex review experiment

This repository supports two deliberately separate Codex review paths. The
repository-owned GitHub Action is the primary scalable direction because it can
be coordinated with static analysis, security, testing, evidence aggregation,
and merge gates. Hosted review remains useful as a low-setup comparison and an
optional additional review pass.

## Shared review policy

`AGENTS.md` is the entrypoint for every agent. Its pull-request review contract
routes both integrations to `.github/review/code-review.md`, which contains the
provider-neutral review policy. Integration prompts should contain execution
details only and must not duplicate that policy.

## Hosted Codex review

1. Connect the repository to Codex Cloud.
2. Enable Code Review in Codex settings.
3. On an experiment pull request, comment:

   ```text
   @codex review
   ```

Codex Cloud owns execution, reads `AGENTS.md`, follows its review-policy route,
and posts a standard GitHub review. No repository workflow runs for this path.

## Repository-owned Codex Action review

1. Add an `OPENAI_API_KEY` repository secret.
2. Add the `codex-action-review` label to the experiment pull request.
3. The `Codex action PR review` workflow runs in GitHub Actions and posts one
   native GitHub review containing inline, resolvable findings.

Codex emits structured JSON governed by
`.github/codex/schemas/pr-review.schema.json`. The publisher validates each
finding against the current diff before attaching it to a line. Findings that
cannot be attached safely remain visible in the review summary.

Each inline comment contains a hidden fingerprint derived from the head commit,
path, line, side, and normalized title. A retry on the same commit therefore
does not duplicate the review. A new commit receives new fingerprints so
remaining findings can be reported at their current locations. The automation
does not resolve threads; resolution remains a human decision.

The write-enabled publisher is always loaded from the pull request's trusted
base commit, not from the proposed changes. Consequently, the pull request that
first introduces this publisher should be merged without applying the
`codex-action-review` label; exercise the inline flow on the next pull request.

## Multi-repository direction

After the experiment, move the stable orchestration into a versioned reusable
workflow owned by a central CI repository. Each application repository should
retain only its `AGENTS.md`, repository-specific review policy or overrides, and
a thin caller workflow. Model-specific actions then become replaceable adapters
behind the reusable workflow rather than being copied across every project.

## Safe experiment sequence

1. Merge the setup pull request containing these files.
2. Configure the Codex Cloud repository connection and the GitHub secret.
3. Open a separate draft experiment pull request containing known temporary
   defects.
4. Trigger both review paths on that same commit.
5. Compare finding accuracy, evidence, noise, latency, and presentation.
6. Close the experiment pull request without merging it.
