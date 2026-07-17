const crypto = require("node:crypto");

const REVIEW_MARKER_PREFIX = "codex-action-review";
const FINDING_MARKER_PREFIX = "codex-action-fingerprint";
const REVIEW_KEYS = ["summary", "findings", "validation", "coverage", "uncertainty"];
const FINDING_KEYS = [
  "severity",
  "confidence",
  "path",
  "line",
  "side",
  "title",
  "problem",
  "evidence",
  "correction",
];

function cleanText(value) {
  return String(value).replace(/<!--\s*codex-action-[\s\S]*?-->/gi, "").trim();
}

function assertOnlyKeys(value, allowedKeys, label) {
  const unexpected = Object.keys(value).filter((key) => !allowedKeys.includes(key));
  if (unexpected.length) {
    throw new Error(`${label} contains unexpected field(s): ${unexpected.join(", ")}.`);
  }
}

function validateReview(review) {
  if (!review || typeof review !== "object" || Array.isArray(review)) {
    throw new Error("Codex review output must be a JSON object.");
  }

  assertOnlyKeys(review, REVIEW_KEYS, "Codex review output");
  for (const key of REVIEW_KEYS) {
    if (!(key in review)) {
      throw new Error(`Codex review output is missing '${key}'.`);
    }
  }

  if (typeof review.summary !== "string" || !review.summary.trim()) {
    throw new Error("Codex review summary must be a non-empty string.");
  }

  for (const key of ["findings", "validation", "coverage", "uncertainty"]) {
    if (!Array.isArray(review[key])) {
      throw new Error(`Codex review '${key}' must be an array.`);
    }
  }

  for (const key of ["validation", "coverage", "uncertainty"]) {
    if (review[key].some((item) => typeof item !== "string")) {
      throw new Error(`Codex review '${key}' entries must be strings.`);
    }
  }

  if (review.findings.length > 25) {
    throw new Error("Codex review output exceeds the 25-finding publication limit.");
  }

  for (const finding of review.findings) {
    if (!finding || typeof finding !== "object" || Array.isArray(finding)) {
      throw new Error("Each Codex finding must be a JSON object.");
    }
    assertOnlyKeys(finding, FINDING_KEYS, "Codex finding");
    for (const key of FINDING_KEYS) {
      if (!(key in finding)) {
        throw new Error(`Codex finding is missing '${key}'.`);
      }
    }
    if (!["P0", "P1", "P2"].includes(finding.severity)) {
      throw new Error(`Invalid finding severity '${finding.severity}'.`);
    }
    if (!["high", "medium", "low"].includes(finding.confidence)) {
      throw new Error(`Invalid finding confidence '${finding.confidence}'.`);
    }
    if (!["LEFT", "RIGHT"].includes(finding.side)) {
      throw new Error(`Invalid diff side '${finding.side}'.`);
    }
    if (!Number.isInteger(finding.line) || finding.line < 1) {
      throw new Error("Finding line must be a positive integer.");
    }
    for (const key of ["path", "title", "problem", "evidence", "correction"]) {
      if (typeof finding[key] !== "string" || !finding[key].trim()) {
        throw new Error(`Finding '${key}' must be a non-empty string.`);
      }
    }
  }
}

function collectDiffAnchors(files) {
  const anchors = new Set();

  for (const file of files) {
    if (!file.patch) continue;

    let oldLine = 0;
    let newLine = 0;

    for (const patchLine of file.patch.split("\n")) {
      const hunk = patchLine.match(/^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
      if (hunk) {
        oldLine = Number(hunk[1]);
        newLine = Number(hunk[2]);
        continue;
      }

      if (patchLine.startsWith("\\")) continue;

      if (patchLine.startsWith("+")) {
        anchors.add(`${file.filename}:RIGHT:${newLine}`);
        newLine += 1;
      } else if (patchLine.startsWith("-")) {
        anchors.add(`${file.filename}:LEFT:${oldLine}`);
        oldLine += 1;
      } else if (oldLine > 0 || newLine > 0) {
        anchors.add(`${file.filename}:LEFT:${oldLine}`);
        anchors.add(`${file.filename}:RIGHT:${newLine}`);
        oldLine += 1;
        newLine += 1;
      }
    }
  }

  return anchors;
}

function fingerprintFinding(headSha, finding) {
  const normalizedTitle = cleanText(finding.title).toLowerCase().replace(/\s+/g, " ");
  const identity = [
    headSha,
    finding.path,
    finding.side,
    finding.line,
    normalizedTitle,
  ].join("\u0000");

  return crypto.createHash("sha256").update(identity).digest("hex").slice(0, 20);
}

function formatFinding(finding, fingerprint) {
  return [
    `<!-- ${FINDING_MARKER_PREFIX}:${fingerprint} -->`,
    `**${finding.severity} · ${finding.confidence} confidence — ${cleanText(finding.title)}**`,
    "",
    cleanText(finding.problem),
    "",
    `**Evidence:** ${cleanText(finding.evidence)}`,
    "",
    `**Smallest correction:** ${cleanText(finding.correction)}`,
  ].join("\n");
}

function renderList(items) {
  if (!items.length) return "- None reported.";
  return items.map((item) => `- ${cleanText(item)}`).join("\n");
}

function buildReviewPayload(review, headSha, anchors, existingFingerprints = new Set()) {
  validateReview(review);

  const comments = [];
  const fallbackFindings = [];

  for (const finding of review.findings) {
    const fingerprint = fingerprintFinding(headSha, finding);
    if (existingFingerprints.has(fingerprint)) continue;

    const anchor = `${finding.path}:${finding.side}:${finding.line}`;
    if (!anchors.has(anchor)) {
      fallbackFindings.push(finding);
      continue;
    }

    comments.push({
      path: finding.path,
      line: finding.line,
      side: finding.side,
      body: formatFinding(finding, fingerprint),
    });
  }

  const body = [
    `<!-- ${REVIEW_MARKER_PREFIX}:${headSha} -->`,
    "## Codex Action review",
    "",
    cleanText(review.summary),
    "",
    "### Validation",
    "",
    renderList(review.validation),
    "",
    "### Coverage",
    "",
    renderList(review.coverage),
    "",
    "### Uncertainty",
    "",
    renderList(review.uncertainty),
  ];

  if (fallbackFindings.length) {
    body.push("", "### Findings not attached to a changed line", "");
    for (const finding of fallbackFindings) {
      body.push(
        `- **${finding.severity} · ${finding.confidence} — ${cleanText(finding.title)}** ` +
          `(${finding.path}:${finding.line}): ${cleanText(finding.problem)} ` +
          `Correction: ${cleanText(finding.correction)}`
      );
    }
  }

  if (!review.findings.length) {
    body.push("", "No actionable findings.");
  }

  return { body: body.join("\n"), comments, fallbackFindings };
}

function extractFingerprints(comments) {
  const fingerprints = new Set();
  const pattern = new RegExp(`<!--\\s*${FINDING_MARKER_PREFIX}:([a-f0-9]+)\\s*-->`, "g");

  for (const comment of comments) {
    for (const match of String(comment.body || "").matchAll(pattern)) {
      fingerprints.add(match[1]);
    }
  }

  return fingerprints;
}

async function publishReview({ github, context, core, reviewJson }) {
  const pullRequest = context.payload.pull_request;
  if (!pullRequest) throw new Error("Inline review publication requires a pull_request event.");

  const owner = context.repo.owner;
  const repo = context.repo.repo;
  const pullNumber = pullRequest.number;
  const headSha = pullRequest.head.sha;
  const review = typeof reviewJson === "string" ? JSON.parse(reviewJson) : reviewJson;
  validateReview(review);

  const existingReviews = await github.paginate(github.rest.pulls.listReviews, {
    owner,
    repo,
    pull_number: pullNumber,
    per_page: 100,
  });
  const reviewMarker = `<!-- ${REVIEW_MARKER_PREFIX}:${headSha} -->`;
  if (existingReviews.some((item) => String(item.body || "").includes(reviewMarker))) {
    core.info(`Codex Action review already exists for ${headSha}; skipping duplicate publication.`);
    return { skipped: true, reason: "review-exists" };
  }

  const [files, existingComments] = await Promise.all([
    github.paginate(github.rest.pulls.listFiles, {
      owner,
      repo,
      pull_number: pullNumber,
      per_page: 100,
    }),
    github.paginate(github.rest.pulls.listReviewComments, {
      owner,
      repo,
      pull_number: pullNumber,
      per_page: 100,
    }),
  ]);

  const payload = buildReviewPayload(
    review,
    headSha,
    collectDiffAnchors(files),
    extractFingerprints(existingComments)
  );

  await github.rest.pulls.createReview({
    owner,
    repo,
    pull_number: pullNumber,
    commit_id: headSha,
    event: "COMMENT",
    body: payload.body,
    comments: payload.comments,
  });

  core.info(
    `Published ${payload.comments.length} inline finding(s) and ` +
      `${payload.fallbackFindings.length} summary-only finding(s).`
  );
  return { skipped: false, ...payload };
}

module.exports = {
  buildReviewPayload,
  collectDiffAnchors,
  extractFingerprints,
  fingerprintFinding,
  publishReview,
  validateReview,
};
