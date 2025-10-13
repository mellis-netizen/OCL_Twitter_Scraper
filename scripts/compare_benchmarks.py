#!/usr/bin/env python3
"""
Performance Benchmark Comparison Tool
Compares current benchmark results against a baseline to detect regressions
"""

import json
import sys
from typing import Dict, List, Tuple
from pathlib import Path


class BenchmarkComparator:
    """Compare performance benchmarks and detect regressions"""

    # Regression thresholds
    REGRESSION_THRESHOLD = 1.2  # 20% slower is a regression
    WARNING_THRESHOLD = 1.1     # 10% slower is a warning

    def __init__(self, baseline_path: str, current_path: str):
        self.baseline_path = Path(baseline_path)
        self.current_path = Path(current_path)

        if not self.baseline_path.exists():
            raise FileNotFoundError(f"Baseline file not found: {baseline_path}")

        if not self.current_path.exists():
            raise FileNotFoundError(f"Current benchmark file not found: {current_path}")

        with open(self.baseline_path) as f:
            self.baseline = json.load(f)

        with open(self.current_path) as f:
            self.current = json.load(f)

    def extract_benchmarks(self, data: Dict) -> Dict[str, float]:
        """Extract benchmark names and median times"""
        benchmarks = {}

        if 'benchmarks' in data:
            for bench in data['benchmarks']:
                name = bench.get('name', bench.get('fullname', 'unknown'))
                stats = bench.get('stats', {})
                # Use median time as the comparison metric
                median = stats.get('median', stats.get('mean', 0))
                benchmarks[name] = median

        return benchmarks

    def compare(self) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Compare benchmarks and categorize results

        Returns:
            Tuple of (regressions, warnings, improvements)
        """
        baseline_benchmarks = self.extract_benchmarks(self.baseline)
        current_benchmarks = self.extract_benchmarks(self.current)

        regressions = []
        warnings = []
        improvements = []

        for name, baseline_time in baseline_benchmarks.items():
            if name not in current_benchmarks:
                continue

            current_time = current_benchmarks[name]

            if baseline_time == 0:
                continue

            ratio = current_time / baseline_time
            change_pct = (ratio - 1) * 100

            result = {
                'name': name,
                'baseline': baseline_time,
                'current': current_time,
                'ratio': ratio,
                'change_pct': change_pct
            }

            if ratio >= self.REGRESSION_THRESHOLD:
                regressions.append(result)
            elif ratio >= self.WARNING_THRESHOLD:
                warnings.append(result)
            elif ratio < 1.0:
                improvements.append(result)

        return regressions, warnings, improvements

    def print_report(self):
        """Print comparison report"""
        regressions, warnings, improvements = self.compare()

        print("\n" + "="*80)
        print(" PERFORMANCE BENCHMARK COMPARISON REPORT")
        print("="*80)

        # Regressions
        if regressions:
            print("\n❌ REGRESSIONS DETECTED (≥20% slower):")
            print("-" * 80)
            for r in regressions:
                print(f"  {r['name']}")
                print(f"    Baseline: {r['baseline']*1000:.2f}ms")
                print(f"    Current:  {r['current']*1000:.2f}ms")
                print(f"    Change:   +{r['change_pct']:.1f}% slower ({r['ratio']:.2f}x)")

        # Warnings
        if warnings:
            print("\n⚠️  WARNINGS (10-20% slower):")
            print("-" * 80)
            for w in warnings:
                print(f"  {w['name']}")
                print(f"    Baseline: {w['baseline']*1000:.2f}ms")
                print(f"    Current:  {w['current']*1000:.2f}ms")
                print(f"    Change:   +{w['change_pct']:.1f}% slower ({w['ratio']:.2f}x)")

        # Improvements
        if improvements:
            print("\n✅ IMPROVEMENTS:")
            print("-" * 80)
            for i in improvements:
                print(f"  {i['name']}")
                print(f"    Baseline: {i['baseline']*1000:.2f}ms")
                print(f"    Current:  {i['current']*1000:.2f}ms")
                print(f"    Change:   {i['change_pct']:.1f}% faster ({i['ratio']:.2f}x)")

        # Summary
        print("\n" + "="*80)
        print(" SUMMARY")
        print("="*80)
        print(f"  Regressions: {len(regressions)}")
        print(f"  Warnings:    {len(warnings)}")
        print(f"  Improvements: {len(improvements)}")
        print(f"  Total:       {len(regressions) + len(warnings) + len(improvements)}")
        print("="*80 + "\n")

        # Exit with error code if regressions found
        if regressions:
            print("⛔ Performance regressions detected!")
            return 1
        elif warnings:
            print("⚠️  Performance warnings detected")
            return 0  # Don't fail CI on warnings
        else:
            print("✅ No performance regressions detected")
            return 0


def main():
    """Main entry point"""
    if len(sys.argv) != 3:
        print("Usage: python compare_benchmarks.py <baseline.json> <current.json>")
        sys.exit(1)

    baseline_path = sys.argv[1]
    current_path = sys.argv[2]

    try:
        comparator = BenchmarkComparator(baseline_path, current_path)
        exit_code = comparator.print_report()
        sys.exit(exit_code)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
