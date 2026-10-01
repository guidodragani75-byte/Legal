"""
E2E Test Runner for legal-bot
Discovers and executes all 4 test tiers, computes statistics, generates e2e_report.json,
and exits with code 0 on all tests passing or 1 on failure.

Usage:
    python tests/run_e2e_tests.py
"""

import os
import sys
import time
import json
import unittest
from datetime import datetime, timezone

# Ensure project root and tests directory are in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS_DIR = os.path.abspath(os.path.dirname(__file__))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

REPORT_PATH = os.path.join(TESTS_DIR, "e2e_report.json")

TIER_MODULES = [
    ("Tier 1: Feature Coverage", "test_tier1_features"),
    ("Tier 2: Boundary & Corner Cases", "test_tier2_boundaries"),
    ("Tier 3: Pairwise Combinations", "test_tier3_pairwise"),
    ("Tier 4: Real-World Scenarios", "test_tier4_scenarios"),
    ("Redesign E2E (R1 - R4 Tiers 1 - 4)", "test_redesign_e2e"),
]


def print_banner(text, width=70, char="="):
    print(char * width)
    print(f" {text}")
    print(char * width)


def run_e2e_suite():
    t_start = time.time()
    start_utc = datetime.now(timezone.utc).isoformat()

    print("\n" + "=" * 70)
    print(" ⚖️   LEGAL-BOT E2E TEST HARNESS (TIERS 1 - 4)")
    print(f" Started: {start_utc}")
    print(f" Working Dir: {PROJECT_ROOT}")
    print("=" * 70 + "\n")

    loader = unittest.TestLoader()
    tier_results = []
    total_run = 0
    total_passed = 0
    total_failed = 0
    total_errors = 0
    total_skipped = 0

    overall_success = True

    for tier_title, module_name in TIER_MODULES:
        print_banner(f"Running {tier_title} [{module_name}.py]", width=70, char="-")
        tier_t0 = time.time()

        try:
            suite = loader.loadTestsFromName(module_name)
        except Exception as e:
            print(f" ❌ Failed to load test module {module_name}: {e}")
            overall_success = False
            tier_results.append({
                "tier": tier_title,
                "module": module_name,
                "status": "LOAD_ERROR",
                "error": str(e),
                "tests_run": 0,
                "passed": 0,
                "failed": 0,
                "errors": 1,
                "skipped": 0,
                "duration_seconds": round(time.time() - tier_t0, 3)
            })
            continue

        runner = unittest.TextTestRunner(verbosity=1, stream=sys.stdout)
        result = runner.run(suite)
        tier_duration = round(time.time() - tier_t0, 3)

        tests_in_tier = result.testsRun
        fails_in_tier = len(result.failures)
        errors_in_tier = len(result.errors)
        skips_in_tier = len(result.skipped)
        passed_in_tier = tests_in_tier - fails_in_tier - errors_in_tier - skips_in_tier

        total_run += tests_in_tier
        total_passed += passed_in_tier
        total_failed += fails_in_tier
        total_errors += errors_in_tier
        total_skipped += skips_in_tier

        tier_status = "PASSED" if (fails_in_tier == 0 and errors_in_tier == 0) else "FAILED"
        if tier_status == "FAILED":
            overall_success = False

        tier_results.append({
            "tier": tier_title,
            "module": module_name,
            "status": tier_status,
            "tests_run": tests_in_tier,
            "passed": passed_in_tier,
            "failed": fails_in_tier,
            "errors": errors_in_tier,
            "skipped": skips_in_tier,
            "duration_seconds": tier_duration
        })

        status_icon = "✅" if tier_status == "PASSED" else "❌"
        print(f"\n {status_icon} {tier_title}: {passed_in_tier} passed, {skips_in_tier} skipped, {fails_in_tier} failed, {errors_in_tier} errors ({tier_duration}s)\n")

    total_duration = round(time.time() - t_start, 3)
    end_utc = datetime.now(timezone.utc).isoformat()

    # Generate Summary Table
    print_banner("E2E EXECUTION SUMMARY", width=70, char="=")
    print(f" Total Tests Run : {total_run}")
    print(f" Passed         : {total_passed}")
    print(f" Skipped        : {total_skipped} (Progressive milestone placeholders)")
    print(f" Failed         : {total_failed}")
    print(f" Errors         : {total_errors}")
    print(f" Elapsed Time   : {total_duration}s")
    print(f" Final Verdict  : {'✅ ALL TESTS PASSED' if overall_success else '❌ TEST SUITE FAILED'}")
    print("=" * 70 + "\n")

    report_payload = {
        "timestamp_start": start_utc,
        "timestamp_end": end_utc,
        "duration_seconds": total_duration,
        "overall_status": "PASSED" if overall_success else "FAILED",
        "summary": {
            "total_run": total_run,
            "passed": total_passed,
            "skipped": total_skipped,
            "failed": total_failed,
            "errors": total_errors,
        },
        "tiers": tier_results
    }

    try:
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(report_payload, f, indent=2, ensure_ascii=False)
        print(f" 📄 Structured JSON report written to: {REPORT_PATH}\n")
    except Exception as ex:
        print(f" ⚠️ Could not write report JSON: {ex}")

    sys.exit(0 if overall_success else 1)


if __name__ == "__main__":
    run_e2e_suite()
