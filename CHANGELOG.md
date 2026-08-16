# Changelog

## [Unreleased]

_Nothing yet._

## [1.0.0] - 2026-08-15

### Added

- Composite action running layoutlens 2.0.0's keyless deterministic checks
  (axe-core WCAG A/AA + geometry/contrast layout scan) on file, glob, or URL
  sources.
- Four output channels: job summary table, `::warning` annotations
  (file-anchored for workspace sources), sticky PR comment
  (`pull-requests: write`, fork-safe degradation), and merged SARIF 2.1.0
  upload to Code Scanning (`security-events: write`).
- `fail-on: nothing|findings` (non-blocking by default), `checks`,
  `viewport`, `layoutlens-version` inputs; `findings` and `sarif-file`
  outputs.
