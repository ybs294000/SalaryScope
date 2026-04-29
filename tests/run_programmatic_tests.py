import io
import importlib.util
import os
import platform
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS_DIR = os.path.join(ROOT_DIR, "tests")
ARTIFACT_DIR = os.path.join(TESTS_DIR, "artifacts")

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

os.makedirs(ARTIFACT_DIR, exist_ok=True)


def build_suite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    for dirpath, _, filenames in os.walk(TESTS_DIR):
        for filename in sorted(filenames):
            if not filename.startswith("test_") or not filename.endswith(".py"):
                continue
            file_path = os.path.join(dirpath, filename)
            module_name = (
                os.path.relpath(file_path, ROOT_DIR)
                .replace(os.sep, ".")
                .rsplit(".", 1)[0]
            )
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            assert spec.loader is not None
            spec.loader.exec_module(module)
            suite.addTests(loader.loadTestsFromModule(module))
    return suite


def write_markdown_report(result, stdout_text, started_at, finished_at):
    report_path = os.path.join(ARTIFACT_DIR, "programmatic_test_report.md")
    duration = (finished_at - started_at).total_seconds()

    lines = [
        "# Tests Report",
        "",
        f"- Generated: `{finished_at.isoformat()}`",
        f"- Python: `{platform.python_version()}`",
        f"- Platform: `{platform.platform()}`",
        f"- Duration: `{duration:.2f}s`",
        "",
        "## Scope",
        "",
        "- Checked-in programmatic tests under `tests/`",
        "- Covers core validation, resume extraction and scoring, resume screening readiness, financial utilities, insights, rate limiting, and Interview Prep core logic",
        "- Programmatic coverage only; this report does not represent browser-driven Streamlit UI testing",
        "",
        "## Summary",
        "",
        f"- Tests run: `{result.testsRun}`",
        f"- Failures: `{len(result.failures)}`",
        f"- Errors: `{len(result.errors)}`",
        f"- Skipped: `{len(getattr(result, 'skipped', []))}`",
        f"- Successful: `{'yes' if result.wasSuccessful() else 'no'}`",
        "",
        "## Covered Areas",
        "",
        "- Password policy validation",
        "- Rate limiter session logic",
        "- Resume analysis helpers and score calculation",
        "- Resume screening readiness signals",
        "- Financial planning utility functions",
        "- Insights engine role and domain logic",
        "- Model Hub schema and bundle validation",
        "- Interview Prep registry validation, scoring, timer formatting, and loader behavior",
        "",
    ]

    if result.failures or result.errors:
        lines.extend(["## Findings", ""])
        for label, entries in [("Failures", result.failures), ("Errors", result.errors)]:
            if entries:
                lines.append(f"### {label}")
                lines.append("")
                for test, traceback in entries:
                    lines.append(f"- `{test.id()}`")
                    lines.append("```text")
                    lines.append(traceback.rstrip())
                    lines.append("```")
                lines.append("")
    else:
        lines.extend(
            [
                "## Findings",
                "",
                "- No failing programmatic tests in this run.",
                "",
            ]
        )

    lines.extend(
        [
            "## Raw Runner Output",
            "",
            "```text",
            stdout_text.rstrip(),
            "```",
            "",
        ]
    )

    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    return report_path


def main():
    suite = build_suite()
    buffer = io.StringIO()
    runner = unittest.TextTestRunner(stream=buffer, verbosity=2)
    started_at = datetime.now(timezone.utc)
    with redirect_stdout(buffer), redirect_stderr(buffer):
        result = runner.run(suite)
    finished_at = datetime.now(timezone.utc)
    stdout_text = buffer.getvalue()

    raw_output_path = os.path.join(ARTIFACT_DIR, "programmatic_test_output.txt")
    with open(raw_output_path, "w", encoding="utf-8") as handle:
        handle.write(stdout_text)

    report_path = write_markdown_report(result, stdout_text, started_at, finished_at)
    print(stdout_text)
    print(f"Artifacts written to: {ARTIFACT_DIR}")
    print(f"Markdown report: {report_path}")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
