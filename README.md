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
      - uses: actions/checkout@v6
      - uses: gojiplus/layoutlens-action@v1
        with:
          sources: "dist/index.html dist/pricing.html"
          sarif-upload: "false"
```

Non-blocking by default: findings are reported, the job stays green.

## With GitHub Code Scanning

```yaml
    permissions:
      contents: read
      security-events: write   # required for SARIF upload
      pull-requests: write
    steps:
      - uses: actions/checkout@v6
      - uses: gojiplus/layoutlens-action@v1
        with:
          sources: "dist/*.html"
```

Findings appear in **Security → Code scanning** with stable rule ids and
over-time tracking; on PRs, GitHub flags which findings are *new*.

## As a required gate

```yaml
      - uses: gojiplus/layoutlens-action@v1
        with:
          sources: "dist/*.html"
          fail-on: findings      # any measured finding fails the step
          viewport: mobile
```

Because the checks are deterministic, a red gate is a measured defect, never
model noise — reasonable to make a required status check.

## Inputs

| Input | Default | Description |
|---|---|---|
| `sources` | *(required)* | Whitespace-separated HTML file paths, globs, or URLs |
| `checks` | `both` | `a11y`, `layout`, or `both` |
| `viewport` | `desktop` | `desktop`, `mobile`, or `tablet` |
| `fail-on` | `nothing` | `nothing` (report only) or `findings` |
| `sarif-upload` | `true` | Upload SARIF to Code Scanning (needs `security-events: write`) |
| `pr-comment` | `true` | Sticky results comment on PRs (needs `pull-requests: write`; degrades gracefully on forks) |
| `layoutlens-version` | pinned per release | layoutlens version to run |
| `python-version` | `3.12` | Python for the tool install |

## Outputs

| Output | Description |
|---|---|
| `findings` | Total deterministic findings across all sources |
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

<!-- demo: exercises the PR comment path -->
