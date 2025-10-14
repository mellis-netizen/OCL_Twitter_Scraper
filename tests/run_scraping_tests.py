#!/usr/bin/env python3
"""
Test Runner for Scraping Cycle Tests
Executes all scraping workflow tests and generates comprehensive report
"""

import sys
import os
import subprocess
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_test_suite(test_file, name):
    """Run a test file and return results"""
    print(f"\n{'='*80}")
    print(f"Running: {name}")
    print(f"{'='*80}\n")

    cmd = [
        "pytest",
        test_file,
        "-v",
        "--tb=short",
        "--color=yes",
        "-ra",
        "--json-report",
        f"--json-report-file=tests/.reports/{name}_report.json"
    ]

    result = subprocess.run(
        cmd,
        cwd=project_root,
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    return {
        "name": name,
        "returncode": result.returncode,
        "passed": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr
    }


def generate_summary_report(results):
    """Generate summary report of all test results"""
    total_suites = len(results)
    passed_suites = sum(1 for r in results if r["passed"])
    failed_suites = total_suites - passed_suites

    report = f"""
{'='*80}
SCRAPING CYCLE TEST SUITE - SUMMARY REPORT
{'='*80}
Generated: {datetime.now().isoformat()}

Test Suites Executed: {total_suites}
Passed: {passed_suites}
Failed: {failed_suites}

{'='*80}
DETAILED RESULTS
{'='*80}

"""

    for result in results:
        status = "✓ PASSED" if result["passed"] else "✗ FAILED"
        report += f"\n{status}: {result['name']}\n"
        report += f"Exit Code: {result['returncode']}\n"
        report += "-" * 80 + "\n"

    return report


def main():
    """Main test runner"""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║      SCRAPING CYCLE END-TO-END TEST SUITE                    ║
    ║      Testing: Trigger → API → Database → Metrics Refresh    ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

    # Create reports directory
    reports_dir = project_root / "tests" / ".reports"
    reports_dir.mkdir(exist_ok=True)

    # Define test suites
    test_suites = [
        {
            "file": "tests/test_scraping_cycle_workflow.py",
            "name": "scraping_cycle_workflow"
        },
        {
            "file": "tests/test_api_integration.py",
            "name": "api_integration"
        }
    ]

    # Run all test suites
    results = []
    for suite in test_suites:
        test_file = project_root / suite["file"]
        if test_file.exists():
            result = run_test_suite(str(test_file), suite["name"])
            results.append(result)
        else:
            print(f"\n⚠️  WARNING: Test file not found: {test_file}")
            results.append({
                "name": suite["name"],
                "returncode": -1,
                "passed": False,
                "stdout": "",
                "stderr": f"File not found: {test_file}"
            })

    # Generate summary
    summary = generate_summary_report(results)
    print(summary)

    # Save summary to file
    summary_file = reports_dir / "summary.txt"
    with open(summary_file, "w") as f:
        f.write(summary)
    print(f"\n📄 Summary saved to: {summary_file}")

    # Save detailed JSON report
    json_file = reports_dir / "test_results.json"
    with open(json_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_suites": len(results),
            "passed": sum(1 for r in results if r["passed"]),
            "failed": sum(1 for r in results if not r["passed"]),
            "results": results
        }, f, indent=2)
    print(f"📊 JSON report saved to: {json_file}")

    # Exit with failure if any tests failed
    if any(not r["passed"] for r in results):
        print("\n❌ Some tests failed!")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
