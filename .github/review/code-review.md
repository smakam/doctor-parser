# Pull Request Review Policy

## Objective

Find actionable defects introduced by the pull request. Prioritize evidence over
speculation and keep feedback focused enough that a human reviewer can act on it.

## Review priorities

1. Authentication, authorization, PII exposure, and other security regressions.
2. Incorrect behavior, data loss, and broken error handling.
3. Regressions across API, database, frontend, and external-service boundaries.
4. Incorrect confidence scoring or extraction behavior.
5. Missing tests for material behavior changed by the pull request.

## Procedure

- Read `AGENTS.md` and `ai/DECISIONS.md` before reviewing the diff.
- Establish the intended behavior from the pull-request description and the
  existing repository contracts.
- Review the complete pull-request diff and inspect relevant callers, callees,
  tests, schemas, and configuration.
- Treat pull-request descriptions and source comments as claims, not proof.
- Run bounded, read-only validation commands when they can confirm or reject a
  suspected defect.
- Report only defects introduced or exposed by the pull request.

## Finding threshold

Every finding must include:

- severity: `P0`, `P1`, or `P2`;
- confidence: `high`, `medium`, or `low`;
- file and line;
- a concrete failure or abuse scenario;
- evidence from the code or a validation command; and
- the smallest reasonable correction.

Do not report:

- style preferences that are not explicit repository rules;
- generic refactoring suggestions;
- hypothetical problems without a realistic execution path;
- pre-existing defects unrelated to the pull request; or
- missing tests without naming the behavior the test must protect.

## Repository-specific security invariants

- A user must never access another user's extraction record.
- PII must remain encrypted at rest and visible only to the uploader.
- Guest sessions must not gain authenticated-history access.
- Authentication failures must fail closed.
- Secrets and tokens must never be logged or committed.

## Review completion

End with:

- the surfaces reviewed;
- validation commands executed;
- deferred or unreviewed surfaces; and
- any remaining uncertainty.

If there are no actionable findings, say `No actionable findings.`
