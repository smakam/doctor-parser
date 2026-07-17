const test = require("node:test");
const assert = require("node:assert/strict");

const {
  buildReviewPayload,
  collectDiffAnchors,
  extractFingerprints,
  fingerprintFinding,
  publishReview,
  validateReview,
} = require("./publish-inline-review.cjs");

const finding = {
  severity: "P1",
  confidence: "high",
  path: "src/access.py",
  line: 11,
  side: "RIGHT",
  title: "Restore owner-only access",
  problem: "A different user can read the record.",
  evidence: "The changed predicate fails open.",
  correction: "Restore the ownership comparison.",
};

const review = {
  summary: "One authorization regression.",
  findings: [finding],
  validation: ["Inspected the caller."],
  coverage: ["Reviewed the changed access path."],
  uncertainty: [],
};

test("collectDiffAnchors maps added, removed, and context lines", () => {
  const anchors = collectDiffAnchors([
    {
      filename: "src/access.py",
      patch: "@@ -10,3 +10,3 @@\n context\n-old\n+new\n context",
    },
  ]);

  assert.equal(anchors.has("src/access.py:RIGHT:11"), true);
  assert.equal(anchors.has("src/access.py:LEFT:11"), true);
  assert.equal(anchors.has("src/access.py:RIGHT:10"), true);
});

test("fingerprints are stable for one commit and change for a new commit", () => {
  const first = fingerprintFinding("abc123", finding);
  const retry = fingerprintFinding("abc123", { ...finding, title: "  Restore  owner-only access " });
  const nextCommit = fingerprintFinding("def456", finding);

  assert.equal(first, retry);
  assert.notEqual(first, nextCommit);
});

test("buildReviewPayload publishes valid anchors and falls back for invalid ones", () => {
  const inline = buildReviewPayload(
    review,
    "abc123",
    new Set(["src/access.py:RIGHT:11"])
  );
  assert.equal(inline.comments.length, 1);
  assert.equal(inline.fallbackFindings.length, 0);
  assert.match(inline.comments[0].body, /codex-action-fingerprint/);

  const fallback = buildReviewPayload(review, "abc123", new Set());
  assert.equal(fallback.comments.length, 0);
  assert.equal(fallback.fallbackFindings.length, 1);
  assert.match(fallback.body, /Findings not attached to a changed line/);
});

test("an existing fingerprint suppresses a duplicate inline comment", () => {
  const fingerprint = fingerprintFinding("abc123", finding);
  const payload = buildReviewPayload(
    review,
    "abc123",
    new Set(["src/access.py:RIGHT:11"]),
    new Set([fingerprint])
  );
  assert.equal(payload.comments.length, 0);

  const extracted = extractFingerprints([
    { body: `<!-- codex-action-fingerprint:${fingerprint} -->` },
  ]);
  assert.deepEqual([...extracted], [fingerprint]);
});

test("runtime validation enforces the schema's closed objects and string arrays", () => {
  assert.throws(() => validateReview({ ...review, extra: true }), /unexpected field/);
  assert.throws(
    () => validateReview({ ...review, validation: [123] }),
    /entries must be strings/
  );
  assert.throws(
    () => validateReview({
      ...review,
      findings: [{ ...finding, extra: true }],
    }),
    /unexpected field/
  );
});

function publisherFixture(existingReviews = []) {
  const calls = [];
  const pulls = {
    listReviews() {},
    listFiles() {},
    listReviewComments() {},
    async createReview(payload) {
      calls.push(payload);
    },
  };
  const github = {
    rest: { pulls },
    async paginate(method) {
      if (method === pulls.listReviews) return existingReviews;
      if (method === pulls.listFiles) {
        return [{ filename: "src/access.py", patch: "@@ -10 +10,2 @@\n old\n+new" }];
      }
      if (method === pulls.listReviewComments) return [];
      throw new Error("Unexpected paginated method.");
    },
  };
  const context = {
    repo: { owner: "smakam", repo: "doctor-parser" },
    payload: { pull_request: { number: 3, head: { sha: "abc123" } } },
  };
  return { calls, github, context, core: { info() {} } };
}

test("publishReview sends a native review anchored to the PR head", async () => {
  const fixture = publisherFixture();
  const result = await publishReview({
    ...fixture,
    reviewJson: JSON.stringify(review),
  });

  assert.equal(result.skipped, false);
  assert.equal(fixture.calls.length, 1);
  assert.equal(fixture.calls[0].commit_id, "abc123");
  assert.equal(fixture.calls[0].event, "COMMENT");
  assert.deepEqual(
    fixture.calls[0].comments.map(({ path, line, side }) => ({ path, line, side })),
    [{ path: "src/access.py", line: 11, side: "RIGHT" }]
  );
});

test("publishReview skips a review already published for the same head", async () => {
  const fixture = publisherFixture([{ body: "<!-- codex-action-review:abc123 -->" }]);
  const result = await publishReview({
    ...fixture,
    reviewJson: JSON.stringify(review),
  });

  assert.deepEqual(result, { skipped: true, reason: "review-exists" });
  assert.equal(fixture.calls.length, 0);
});
