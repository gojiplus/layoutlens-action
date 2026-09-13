# LayoutLens Action

[![CI](https://github.com/gojiplus/layoutlens-action/actions/workflows/ci.yml/badge.svg)](https://github.com/gojiplus/layoutlens-action/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Deterministic accessibility and layout checks on your rendered pages —
**no API key, no secrets, safe on every fork's pull requests.**

The action runs [layoutlens](https://github.com/gojiplus/layoutlens)'s keyless
engines against your pages:

- **axe-core WCAG A/AA** accessibility audit (`axe/color-contrast`,
  `axe/image-alt`, …)
- **geometry/contrast layout scan**: text contrast below WCAG thresholds,
  overlapping siblings, clipped content, elements past the viewport,
  page-level horizontal overflow, ellipsis-truncated text, tap targets under
  24×24px

Every finding carries a measured receipt (the contrast ratio, the overflow
pixels, the selector) — these are facts from the browser's layout engine, not
model opinions. Results land in four places: the **job summary**, **PR
annotations**, an optional **sticky PR comment**, and optional **SARIF for
GitHub Code Scanning** (which then tracks new-vs-existing findings per PR for
you).

## Minimal usage

```yaml
name: UI checks
on: [pull_request]

jobs:
  ui:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write   # for the sticky comment (optional)
    steps:
      - uses: actions/checkout@v7
      - uses: gojiplus/layoutlens-action@v2
        with:
          sources: "dist/index.html dist/pricing.html"
          sarif-upload: "false"
```

Unqualified layout findings warn by default. Incomplete evidence fails the job.

## With GitHub Code Scanning

```yaml
    permissions:
      contents: read
      security-events: write   # required for SARIF upload
      pull-requests: write
    steps:
      - uses: actions/checkout@v7
      - uses: gojiplus/layoutlens-action@v2
        with:
          sources: "dist/*.html"
```

Findings appear in **Security → Code scanning** with stable rule ids and
over-time tracking; on PRs, GitHub flags which findings are *new*.

## As a required gate

```yaml
      - uses: gojiplus/layoutlens-action@v2
        with:
          sources: "dist/*.html"
          fail-on: findings      # any measured finding fails the step
          viewport: mobile
```

Browser measurements are reproducible observations. A finding that matches a
layout predicate is a candidate for review; intentional overlaps and rule
exceptions can still apply. Default blocking requires independent precision
evidence. `fail-on: findings` is an explicit strict policy, not a claim that
every finding is a verified defect.

## Inputs

| Input | Default | Description |
|---|---|---|
| `sources` | empty | Whitespace-separated HTML file paths, globs, or URLs; required in scan mode |
| `baseline` | empty | Baseline artifact directory, HTML file, or URL; requires `candidate` and replaces `sources` |
| `candidate` | empty | Candidate artifact directory, HTML file, or URL; requires `baseline` |
| `checks` | `both` | `a11y`, `layout`, or `both` |
| `viewport` | `desktop` | `desktop`, `mobile`, or `tablet` |
| `fail-on` | `qualified` | `qualified`, `nothing` (report only), or `findings` (strict) |
| `sarif-upload` | `true` | Upload SARIF to Code Scanning (needs `security-events: write`) |
| `pr-comment` | `true` | Sticky results comment on PRs (needs `pull-requests: write`; degrades gracefully on forks) |
| `layoutlens-version` | pinned per release | layoutlens version to run |
| `python-version` | `3.12` | Python for the tool install |

## Outputs

| Output | Description |
|---|---|
| `findings` | Total deterministic findings across all sources |
| `blocking` | Number of findings selected for blocking by the policy |
| `incomplete` | Whether capture or comparison evidence is incomplete |
| `sarif-file` | Path to the merged SARIF 2.1.0 file |

## Notes

- URL sources work too (`sources: "https://staging.example.com"`), including
  against a preview deployment started earlier in the job.
- The LLM tier of layoutlens (natural-language checks) is deliberately not in
  this action yet — it needs API-key handling; run the
  [`layoutlens` CLI](https://github.com/gojiplus/layoutlens#cli-usage)
  directly for that.
- Passing axe-core is **not** WCAG conformance; automated rules cover a
  subset. See layoutlens's
  [Limitations](https://github.com/gojiplus/layoutlens#limitations).


## Structured regression comparison (v2)

This breaking Action release targets LayoutLens 3 and Python 3.12+.
Capture and save render states with `layoutlens capture SOURCE --save DIRECTORY`.
Provide the baseline and candidate artifacts together:

```yaml
- uses: gojiplus/layoutlens-action@v2
  with:
    baseline: artifacts/baseline
    candidate: artifacts/candidate
    fail-on: qualified
    pr-comment: "false"
```

`baseline` and `candidate` replace `sources` in comparison mode. URLs and HTML
files are also accepted. Existing and resolved findings remain in SARIF but
do not fail a regression gate. Missing coverage or incompatible captures yield
an incomplete result. `blocking` and `incomplete` are exposed as outputs.
No LayoutLens rule ships with independent gate qualification yet; candidate
findings remain warnings unless strict policy is selected.

`layoutlens-package` accepts a locally built wheel for release-contract tests.
