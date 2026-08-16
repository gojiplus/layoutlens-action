"""Assert-script tests for report.py (run: python3 scripts/test_report.py)."""

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import report  # noqa: E402

SAMPLE = {
    "$schema": "https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/schemas/sarif-schema-2.1.0.json",
    "version": "2.1.0",
    "runs": [
        {
            "tool": {
                "driver": {
                    "name": "LayoutLens",
                    "informationUri": "https://github.com/gojiplus/layoutlens",
                    "version": "2.0.0",
                    "rules": [
                        {"id": "layout/page-overflow", "shortDescription": {"text": "x"}}
                    ],
                }
            },
            "results": [
                {
                    "ruleId": "layout/page-overflow",
                    "level": "warning",
                    "message": {"text": "page scrolls horizontally (overflow 1088px)"},
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": "fixtures/defect.html"}
                            },
                            "logicalLocations": [{"name": "html", "kind": "element"}],
                        }
                    ],
                }
            ],
        }
    ],
}

AXE = {
    "version": "2.1.0",
    "runs": [
        {
            "tool": {"driver": {"name": "LayoutLens", "version": "2.0.0", "rules": [
                {"id": "axe/image-alt", "shortDescription": {"text": "alt"}}
            ]}},
            "results": [
                {
                    "ruleId": "axe/image-alt",
                    "level": "error",
                    "message": {"text": "Images must have alternative text (selector: img)"},
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": "fixtures/defect.html"}
                            },
                            "logicalLocations": [{"name": "img", "kind": "element"}],
                        }
                    ],
                }
            ],
        }
    ],
}


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        indir = tmpdir / "in"
        indir.mkdir()
        (indir / "layout-1.sarif").write_text(json.dumps(SAMPLE))
        (indir / "a11y-1.sarif").write_text(json.dumps(AXE))
        merged_path = tmpdir / "merged.sarif"
        outputs = tmpdir / "outputs.txt"
        summary = tmpdir / "summary.md"
        os.environ["GITHUB_OUTPUT"] = str(outputs)
        os.environ["GITHUB_STEP_SUMMARY"] = str(summary)
        os.environ["LL_VIEWPORT"] = "mobile"

        sys.argv = ["report.py", str(indir), str(merged_path)]
        assert report.main() == 0

        merged = json.loads(merged_path.read_text())
        assert len(merged["runs"]) == 1, "merged log must have exactly one run"
        rule_ids = [r["id"] for r in merged["runs"][0]["tool"]["driver"]["rules"]]
        assert rule_ids == ["axe/image-alt", "layout/page-overflow"], rule_ids
        assert len(merged["runs"][0]["results"]) == 2

        out = outputs.read_text()
        assert "findings=2" in out, out
        assert f"sarif-file={merged_path}" in out

        md = summary.read_text()
        assert "2 finding(s)" in md
        assert "mobile viewport" in md
        assert "`layout/page-overflow`" in md
        assert "`html`" in md

        comment = (tmpdir / "comment.md").read_text()
        assert comment.startswith(report.MARKER)

        # Empty input dir => zero findings, valid empty SARIF, green verdict.
        empty = tmpdir / "empty"
        empty.mkdir()
        merged2 = tmpdir / "merged2.sarif"
        sys.argv = ["report.py", str(empty), str(merged2)]
        assert report.main() == 0
        assert json.loads(merged2.read_text())["runs"][0]["results"] == []
        assert "no deterministic findings" in summary.read_text()

    # Annotation escaping: newlines/percent/colon/comma must never break the
    # workflow-command syntax, and the file property must be escaped too.
    import contextlib
    import io

    tricky = {
        "ruleId": "layout/contrast",
        "message": {"text": "line1\nline2 100% bad"},
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": "pages/a,b:c.html"}
                },
                "logicalLocations": [{"name": "#x", "kind": "element"}],
            }
        ],
    }
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        report.annotate([tricky])
    line = buf.getvalue().strip()
    assert line.startswith("::warning file=pages/a%2Cb%3Ac.html,title=layoutlens::"), line
    assert "%0A" in line and "100%25" in line, line
    assert "\n" not in line

    print("test_report.py: all assertions passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
