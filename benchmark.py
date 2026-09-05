import argparse
import sys
import time
from decimal import Decimal
from typing import Any, Dict, List

from backend.database import fetch_all
from backend.truth_engine import investigate_case
from backend.proof_chain import build_investigation


BENCHMARK_VERSION = "4.0"
DEFAULT_AI_SAMPLE = 20


# ============================================================
# HELPERS
# ============================================================

def normalize_decimal(value: Any) -> str:
    if value is None:
        return "0.00"

    try:
        return format(
            Decimal(str(value)),
            ".2f",
        )
    except Exception:
        return str(value)


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip().upper()


# ============================================================
# LOAD BENCHMARK DATA
# ============================================================

def load_cases() -> List[Dict[str, Any]]:
    """
    Load cases and hidden ground truth.

    IMPORTANT:
    The Truth Engine itself does NOT read this table.
    The benchmark uses it only after investigation
    to measure accuracy.
    """

    rows = fetch_all(
        """
        SELECT
            rc.case_id,
            gt.true_status,
            gt.true_exception_type,
            gt.true_recoverable_amount,
            gt.expected_resolution

        FROM reconciliation_cases rc

        INNER JOIN ground_truth gt
            ON gt.case_id = rc.id

        ORDER BY rc.case_id;
        """
    )

    return [
        dict(row)
        for row in rows
    ]


def normalize_ground_truth(
    row: Dict[str, Any],
) -> Dict[str, str]:

    return {
        "status":
            normalize_text(
                row.get("true_status")
            ),

        "exception_type":
            normalize_text(
                row.get("true_exception_type")
            ),

        "recoverable_amount":
            normalize_decimal(
                row.get(
                    "true_recoverable_amount"
                )
            ),

        "resolution":
            normalize_text(
                row.get("expected_resolution")
            ),
    }


# ============================================================
# TRUTH ENGINE EVALUATION
# ============================================================

def evaluate_truth(
    result: Dict[str, Any],
    ground_truth: Dict[str, str],
) -> Dict[str, bool]:

    expected_status = ground_truth[
        "status"
    ]

    expected_exception = ground_truth[
        "exception_type"
    ]

    expected_recovery = ground_truth[
        "recoverable_amount"
    ]

    expected_resolution = ground_truth[
        "resolution"
    ]

    actual_status = normalize_text(
        result.get("status")
    )

    actual_exception = normalize_text(
        result.get("exception_type")
    )

    actual_recovery = normalize_decimal(
        result.get(
            "potential_recovery_amount"
        )
    )

    actual_resolution = normalize_text(
        result.get("resolution")
    )

    # --------------------------------------------------------
    # CLASSIFICATION
    # --------------------------------------------------------

    if expected_exception == "NORMAL":

        classification_correct = (
            actual_status == "NORMAL"
            and actual_exception == ""
        )

    elif expected_exception == "UNRESOLVED":

        classification_correct = (
            actual_status == "UNRESOLVED"
            and actual_exception
            in {
                "",
                "UNRESOLVED",
            }
        )

    else:

        classification_correct = (
            actual_exception
            == expected_exception
        )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    if expected_exception == "NORMAL":

        status_correct = (
            actual_status == "NORMAL"
        )

    elif expected_exception == "UNRESOLVED":

        status_correct = (
            actual_status == "UNRESOLVED"
        )

    else:

        status_correct = (
            actual_status
            == expected_exception
        )

    # --------------------------------------------------------
    # RECOVERY
    # --------------------------------------------------------

    recovery_correct = (
        actual_recovery
        == expected_recovery
    )

    # --------------------------------------------------------
    # RESOLUTION
    # --------------------------------------------------------

    resolution_correct = (
        actual_resolution
        == expected_resolution
    )

    # --------------------------------------------------------
    # UNRESOLVED PRESERVATION
    # --------------------------------------------------------

    if expected_exception == "UNRESOLVED":

        unresolved_correct = (
            actual_status
            == "UNRESOLVED"
        )

    else:

        unresolved_correct = True

    return {
        "classification":
            classification_correct,

        "status":
            status_correct,

        "recovery":
            recovery_correct,

        "resolution":
            resolution_correct,

        "unresolved":
            unresolved_correct,
    }


# ============================================================
# PROOF CHAIN CHECK
# ============================================================

def evaluate_proof_chain(
    investigation: Dict[str, Any],
) -> bool:

    required_keys = {
        "case",
        "finding",
        "financial_trace",
        "proof_chain",
        "evidence",
        "truth_engine",
    }

    if not required_keys.issubset(
        investigation.keys()
    ):
        return False

    proof_chain = investigation.get(
        "proof_chain"
    )

    if not isinstance(
        proof_chain,
        list,
    ):
        return False

    if not proof_chain:
        return False

    evidence = investigation.get(
        "evidence"
    )

    if not isinstance(
        evidence,
        list,
    ):
        return False

    return True


# ============================================================
# DETERMINISTIC BENCHMARK
# ============================================================

def run_deterministic_benchmark(
    cases: List[Dict[str, Any]],
) -> Dict[str, Any]:

    total = len(cases)

    print()
    print("=" * 60)
    print(
        f"DETERMINISTIC PIPELINE — N={total}"
    )
    print("=" * 60)

    classification_correct = 0
    status_correct = 0
    recovery_correct = 0
    resolution_correct = 0
    unresolved_correct = 0
    proof_correct = 0

    failed_cases = []

    start_time = time.perf_counter()

    for index, row in enumerate(
        cases,
        start=1,
    ):

        case_id = row["case_id"]

        ground_truth = (
            normalize_ground_truth(
                row
            )
        )

        try:

            # Truth Engine
            truth_result = (
                investigate_case(
                    case_id
                )
            )

            # Proof Chain
            investigation = (
                build_investigation(
                    truth_result
                )
            )

            # Evaluation
            metrics = evaluate_truth(
                truth_result,
                ground_truth,
            )

            proof_ok = (
                evaluate_proof_chain(
                    investigation
                )
            )

            if metrics["classification"]:
                classification_correct += 1

            if metrics["status"]:
                status_correct += 1

            if metrics["recovery"]:
                recovery_correct += 1

            if metrics["resolution"]:
                resolution_correct += 1

            if metrics["unresolved"]:
                unresolved_correct += 1

            if proof_ok:
                proof_correct += 1

            if (
                not all(metrics.values())
                or not proof_ok
            ):

                failed_cases.append(
                    {
                        "case_id":
                            case_id,

                        "metrics":
                            metrics,

                        "ground_truth":
                            ground_truth,

                        "actual": {
                            "status":
                                truth_result.get(
                                    "status"
                                ),

                            "exception_type":
                                truth_result.get(
                                    "exception_type"
                                ),

                            "recovery":
                                normalize_decimal(
                                    truth_result.get(
                                        "potential_recovery_amount"
                                    )
                                ),

                            "resolution":
                                truth_result.get(
                                    "resolution"
                                ),
                        },

                        "proof_chain":
                            proof_ok,
                    }
                )

        except Exception as exc:

            failed_cases.append(
                {
                    "case_id":
                        case_id,

                    "error":
                        str(exc),
                }
            )

        if (
            index % 25 == 0
            or index == total
        ):

            print(
                f"Processed "
                f"{index}/{total}"
            )

    elapsed = (
        time.perf_counter()
        - start_time
    )

    throughput = (
        total / elapsed
        if elapsed > 0
        else 0
    )

    print()
    print("=" * 60)
    print(
        "DETERMINISTIC BENCHMARK RESULTS"
    )
    print("=" * 60)

    print(
        f"Total cases:              "
        f"{total}"
    )

    print(
        f"Classification accuracy:  "
        f"{classification_correct}/{total} = "
        f"{classification_correct / total * 100:.2f}%"
    )

    print(
        f"Status accuracy:          "
        f"{status_correct}/{total} = "
        f"{status_correct / total * 100:.2f}%"
    )

    print(
        f"Recovery amount accuracy: "
        f"{recovery_correct}/{total} = "
        f"{recovery_correct / total * 100:.2f}%"
    )

    print(
        f"Resolution accuracy:      "
        f"{resolution_correct}/{total} = "
        f"{resolution_correct / total * 100:.2f}%"
    )

    print(
        f"Unresolved preservation:   "
        f"{unresolved_correct}/{total} = "
        f"{unresolved_correct / total * 100:.2f}%"
    )

    print(
        f"Proof Chain integrity:     "
        f"{proof_correct}/{total} = "
        f"{proof_correct / total * 100:.2f}%"
    )

    print(
        f"Processing time:           "
        f"{elapsed:.3f}s"
    )

    print(
        f"Throughput:                "
        f"{throughput:.2f} cases/sec"
    )

    print(
        f"Failed cases:              "
        f"{len(failed_cases)}"
    )

    if failed_cases:

        print()
        print("=" * 60)
        print(
            "FAILED DETERMINISTIC CASES"
        )
        print("=" * 60)

        for failure in failed_cases[:25]:

            print(failure)

        if len(failed_cases) > 25:

            print(
                f"... and "
                f"{len(failed_cases) - 25} "
                f"more."
            )

    return {
        "total":
            total,

        "classification_correct":
            classification_correct,

        "status_correct":
            status_correct,

        "recovery_correct":
            recovery_correct,

        "resolution_correct":
            resolution_correct,

        "unresolved_correct":
            unresolved_correct,

        "proof_correct":
            proof_correct,

        "failed_cases":
            failed_cases,

        "elapsed":
            elapsed,

        "throughput":
            throughput,
    }


# ============================================================
# AI + VALIDATOR + DECISION ENGINE
# ============================================================

def run_ai_benchmark(
    cases: List[Dict[str, Any]],
    sample_size: int,
):

    # --------------------------------------------------------
    # IMPORTANT:
    # Lazy imports prevent --skip-ai from loading Gemini
    # or other optional AI modules.
    # --------------------------------------------------------

    from backend.ai_investigator import (
        investigate_with_ai,
    )

    from backend.validator import (
        validate_ai_report,
    )

    from backend.decision_engine import (
        build_decision,
    )

    sample = cases[
        :min(
            sample_size,
            len(cases),
        )
    ]

    print()
    print("=" * 60)
    print(
        f"AI RELIABILITY SAMPLE — "
        f"N={len(sample)}"
    )
    print("=" * 60)

    ai_successful = 0
    validator_passed = 0
    decision_consistent = 0

    total_ai_time = 0.0

    failures = []

    for index, row in enumerate(
        sample,
        start=1,
    ):

        case_id = row["case_id"]

        try:

            start_time = (
                time.perf_counter()
            )

            # ------------------------------------------------
            # 1. Truth Engine
            # ------------------------------------------------

            truth_result = (
                investigate_case(
                    case_id
                )
            )

            # ------------------------------------------------
            # 2. Proof Chain / Investigation
            # ------------------------------------------------

            investigation = (
                build_investigation(
                    truth_result
                )
            )

            # ------------------------------------------------
            # 3. Gemini Investigator
            # ------------------------------------------------

            ai_result = (
                investigate_with_ai(
                    investigation
                )
            )

            ai_report = ai_result[
                "report"
            ]

            # ------------------------------------------------
            # 4. Deterministic Validator
            # ------------------------------------------------

            validation = (
                validate_ai_report(
                    investigation,
                    ai_report,
                )
            )

            # ------------------------------------------------
            # 5. Deterministic Decision Engine
            # ------------------------------------------------

            decision = (
                build_decision(
                    investigation,
                    validation,
                )
            )

            elapsed = (
                time.perf_counter()
                - start_time
            )

            total_ai_time += elapsed

            ai_successful += 1

            validation_ok = (
                validation.get("status")
                == "SUPPORTED"
            )

            if validation_ok:

                validator_passed += 1

            # ------------------------------------------------
            # Decision consistency
            # ------------------------------------------------

            truth_case = investigation.get(
                "case",
                {}
            )

            truth_status = normalize_text(
                truth_case.get("status")
            )

            truth_resolution = normalize_text(
                truth_case.get("resolution")
            )

            decision_value = normalize_text(
                decision.get("decision")
            )

            if truth_status == "UNRESOLVED":

                expected_decision = (
                    "REQUEST_EVIDENCE"
                )

            elif truth_resolution == "NO_ACTION":

                expected_decision = (
                    "NO_ACTION"
                )

            elif truth_resolution == "REVIEW":

                expected_decision = (
                    "REVIEW_REQUIRED"
                )

            else:

                expected_decision = (
                    "REQUEST_EVIDENCE"
                )

            decision_ok = (
                decision_value
                == expected_decision
            )

            if decision_ok:

                decision_consistent += 1

            print(
                f"[AI "
                f"{index}/{len(sample)}] "
                f"{case_id} ... "
                f"AI=PASS "
                f"Validator="
                f"{'PASS' if validation_ok else 'FAIL'} "
                f"Decision="
                f"{'PASS' if decision_ok else 'FAIL'} "
                f"({elapsed:.2f}s)"
            )

        except Exception as exc:

            failures.append(
                {
                    "case_id":
                        case_id,

                    "error":
                        str(exc),
                }
            )

            print(
                f"[AI "
                f"{index}/{len(sample)}] "
                f"{case_id} ... "
                f"AI=FAIL"
            )

    average_time = (
        total_ai_time / ai_successful
        if ai_successful
        else 0
    )

    print()
    print("=" * 60)
    print(
        "AI / VALIDATOR / DECISION RESULTS"
    )
    print("=" * 60)

    print(
        f"AI sample N:              "
        f"{len(sample)}"
    )

    print(
        f"AI successful:            "
        f"{ai_successful}/{len(sample)} = "
        f"{ai_successful / len(sample) * 100:.2f}%"
    )

    if ai_successful:

        print(
            f"Validator passed:         "
            f"{validator_passed}/{ai_successful} = "
            f"{validator_passed / ai_successful * 100:.2f}%"
        )

        print(
            f"Decision consistency:     "
            f"{decision_consistent}/{ai_successful} = "
            f"{decision_consistent / ai_successful * 100:.2f}%"
        )

        print(
            f"Average AI time:          "
            f"{average_time:.3f}s"
        )

    else:

        print(
            "Validator passed:         0/0 = N/A"
        )

        print(
            "Decision consistency:     0/0 = N/A"
        )

        print(
            "Average AI time:          N/A"
        )

    if failures:

        print()
        print(
            "AI failures "
            "(not counted as deterministic "
            "financial classification failures):"
        )

        for failure in failures[:10]:

            print(failure)

        if len(failures) > 10:

            print(
                f"... and "
                f"{len(failures) - 10} "
                f"more."
            )

    return {
        "sample_size":
            len(sample),

        "ai_successful":
            ai_successful,

        "validator_passed":
            validator_passed,

        "decision_consistent":
            decision_consistent,

        "average_ai_time":
            average_time,

        "failures":
            failures,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Money Autopsy "
            "full-system benchmark"
        )
    )

    parser.add_argument(
        "--skip-ai",
        action="store_true",
        help=(
            "Run only the deterministic "
            "300-case benchmark."
        ),
    )

    parser.add_argument(
        "--ai-sample",
        type=int,
        default=DEFAULT_AI_SAMPLE,
        help=(
            "Number of cases sampled for "
            "Gemini + Validator + Decision Engine."
        ),
    )

    args = parser.parse_args()

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print(
        "MONEY AUTOPSY — "
        "FULL SYSTEM BENCHMARK"
    )
    print("=" * 60)

    print(
        f"Benchmark version: "
        f"{BENCHMARK_VERSION}"
    )

    # --------------------------------------------------------
    # LOAD
    # --------------------------------------------------------

    cases = load_cases()

    print(
        f"Cases loaded: "
        f"{len(cases)}"
    )

    if not cases:

        print(
            "ERROR: No benchmark cases found."
        )

        sys.exit(1)

    # --------------------------------------------------------
    # DETERMINISTIC
    # --------------------------------------------------------

    deterministic_results = (
        run_deterministic_benchmark(
            cases
        )
    )

    # --------------------------------------------------------
    # AI
    # --------------------------------------------------------

    if not args.skip_ai:

        if args.ai_sample <= 0:

            print(
                "ERROR: --ai-sample "
                "must be greater than 0."
            )

            sys.exit(1)

        run_ai_benchmark(
            cases,
            args.ai_sample,
        )

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print(
        "MONEY AUTOPSY — "
        "BENCHMARK COMPLETE"
    )
    print("=" * 60)

    failed = len(
        deterministic_results[
            "failed_cases"
        ]
    )

    if failed == 0:

        print(
            "DETERMINISTIC PIPELINE: PASS"
        )

    else:

        print(
            "DETERMINISTIC PIPELINE: "
            "REVIEW FAILURES"
        )

    if args.skip_ai:

        print(
            "AI benchmark: SKIPPED"
        )

    print(
        "The deterministic Truth Engine "
        "remains the financial authority."
    )


if __name__ == "__main__":
    main()