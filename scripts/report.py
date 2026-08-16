"""Turn layoutlens SARIF runs into GitHub Action outputs.

Reads every ``*.sarif`` in the input directory (one per source × check, as
emitted by ``layoutlens --output sarif``), merges them into a single SARIF
log, and produces the action's four report channels:

- the merged SARIF at the given output path (for Code Scanning upload),
- a findings table appended to ``$GITHUB_STEP_SUMMARY``,
- ``::warning`` workflow-command annotations (``file=`` only for sources
  inside the workspace — URLs get file-less warnings),
- a sticky-comment body (``comment.md`` next to the merged SARIF), marked
  with ``<!-- layoutlens-action -->`` so the action can find and update it.

Exit code is always 0: pass/fail is the composite action's separate verdict
step, so the upload and comment steps always run. Standard library only.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

MARKER = "<!-- layoutlens-action -->"


def load_runs(sarif_dir: Path) -> list[dict]:
    """Load every SARIF file in ``sarif_dir`` and return their runs."""
    runs = []
    for path in sorted(sarif_dir.glob("*.sarif")):
        try:
            log = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"::warning::skipping unreadable SARIF {path.name}: {e}")
            continue
        runs.extend(log.get("runs", []))
    return runs


def merge(runs: list[dict]) -> dict:
    """Merge runs into one SARIF log with a single deduplicated run."""
    all_results: list[dict] = []
    rules: dict[str, dict] = {}
    driver_meta: dict = {}
    for run in runs:
        driver = run.get("tool", {}).get("driver", {})
        driver_meta = driver_meta or driver
        for rule in driver.get("rules", []):
            rules.setdefault(rule["id"], rule)
        all_results.extend(run.get("results", []))
    return {
        "$schema": "https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/schemas/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": driver_meta.get("name", "LayoutLens"),
                        "informationUri": driver_meta.get(
                            "informationUri",
                            "https://github.com/gojiplus/layoutlens",
                        ),
                        "version": driver_meta.get("version", "unknown"),
                        "rules": sorted(rules.values(), key=lambda r: r["id"]),
                    }
                },
                "results": all_results,
            }
        ],
    }


def result_row(result: dict) -> tuple[str, str, str, str]:
    """Extract (rule, source, selector, message) from a SARIF result."""
    rule = result.get("ruleId", "?")
    message = result.get("message", {}).get("text", "")
    source, selector = "?", "?"
    for loc in result.get("locations", [])[:1]:
        source = (
            loc.get("physicalLocation", {})
            .get("artifactLocation", {})
            .get("uri", "?")
        )
        logical = loc.get("logicalLocations", [])
        if logical:
            selector = logical[0].get("name", "?")
    return rule, source, selector, message


def workspace_relative(source: str) -> str | None:
    """Return a workspace-relative path for a local source, else None."""
    if source.startswith(("http://", "https://")):
        return None
    workspace = os.environ.get("GITHUB_WORKSPACE", "")
    path = Path(source)
    if workspace and path.is_absolute():
        try:
            return str(path.relative_to(workspace))
        except ValueError:
            return None
    return source if not path.is_absolute() else None


def annotate(results: list[dict]) -> None:
    """Emit one ::warning workflow command per finding."""
    for result in results:
        rule, source, selector, message = result_row(result)
        # Workflow commands treat some characters as delimiters.
        text = f"[{rule}] {selector}: {message}".replace("\n", " ").replace(
            "%", "%25"
        )
        rel = workspace_relative(source)
        if rel:
            print(f"::warning file={rel},title=layoutlens::{text}")
        else:
            print(f"::warning title=layoutlens ({source})::{text}")


def tables(results: list[dict], viewport: str) -> tuple[str, str]:
    """Build (summary_md, comment_md) for the findings."""
    count = len(results)
    if count == 0:
        verdict = f"✅ **LayoutLens: no deterministic findings** ({viewport} viewport)."
    else:
        verdict = (
            f"❌ **LayoutLens measured {count} finding(s)** ({viewport} viewport)."
        )

    lines = [verdict, ""]
    if count:
        lines += [
            "| Rule | Source | Selector | Detail |",
            "|---|---|---|---|",
        ]
        for result in results[:50]:
            rule, source, selector, message = result_row(result)
            detail = message.replace("|", "\\|").replace("\n", " ")
            lines.append(f"| `{rule}` | {source} | `{selector}` | {detail} |")
        if count > 50:
            lines.append(f"| … | | | +{count - 50} more finding(s) |")
    lines += [
        "",
        "_Deterministic axe-core + geometry checks by"
        " [layoutlens](https://github.com/gojiplus/layoutlens) — measured"
        " values, no LLM, no API key._",
    ]
    summary_md = "\n".join(lines)
    comment_md = MARKER + "\n" + summary_md
    return summary_md, comment_md


def set_output(name: str, value: str) -> None:
    """Append a step output (no-op outside Actions)."""
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")


def main() -> int:
    """CLI: report.py SARIF_DIR MERGED_SARIF_PATH."""
    sarif_dir = Path(sys.argv[1])
    merged_path = Path(sys.argv[2])
    viewport = os.environ.get("LL_VIEWPORT", "desktop")

    runs = load_runs(sarif_dir)
    merged = merge(runs)
    results = merged["runs"][0]["results"]

    merged_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")

    summary_md, comment_md = tables(results, viewport)
    comment_path = merged_path.with_name("comment.md")
    comment_path.write_text(comment_md, encoding="utf-8")

    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as f:
            f.write(summary_md + "\n")

    annotate(results)

    set_output("findings", str(len(results)))
    set_output("sarif-file", str(merged_path))
    set_output("comment-file", str(comment_path))
    print(f"findings: {len(results)}; sarif: {merged_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
