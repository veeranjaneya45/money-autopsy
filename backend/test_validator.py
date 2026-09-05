from copy import deepcopy

from backend.truth_engine import investigate_case
from backend.proof_chain import build_investigation
from backend.validator import validate_ai_report


CASE_ID = "CASE_000234"


def get_investigation():
    """
    Build the authoritative deterministic investigation
    used by every adversarial test.
    """

    truth_result = investigate_case(CASE_ID)

    if not truth_result:
        raise RuntimeError(
            f"Truth Engine returned no result for {CASE_ID}"
        )

    return build_investigation(
        truth_result
    )


def build_valid_ai_report(
    investigation
):
    """
    Build a deliberately valid AI report without
    calling Gemini.

    This allows us to test the Validator even when
    Gemini free-tier quota is exhausted.
    """

    case = investigation["case"]
    evidence = investigation["evidence"]

    evidence_id = str(
        evidence[0]["record_id"]
    )

    recovery = case[
        "potential_recovery_amount"
    ]

    expected = case[
        "expected_amount"
    ]

    observed = case[
        "observed_amount"
    ]

    return {
        "executive_summary": (
            "The deterministic investigation established "
            "a fee mismatch supported by the supplied "
            "financial records."
        ),
        "root_cause": (
            "Recorded processing fee does not match "
            "the supported fee-rate rules."
        ),
        "financial_impact": (
            f"The deterministic investigation identified "
            f"a potential recovery amount of {recovery}."
        ),
        "evidence": [
            {
                "evidence_id": evidence_id,
                "reason": (
                    "This record is part of the deterministic "
                    "investigation evidence."
                ),
            }
        ],
        "recommended_action": (
            "Route the case to an authorized human "
            "operator for review and approval."
        ),
        "confidence": "HIGH",
        "human_review_required": True,
        "unresolved_reason": "",
    }


def run_test(
    name,
    investigation,
    ai_report,
    expected_status,
):
    result = validate_ai_report(
        investigation,
        ai_report,
    )

    passed = (
        result["status"] == expected_status
    )

    status = "PASS" if passed else "FAIL"

    print(
        f"{status:<6} {name:<35} "
        f"Expected={expected_status:<10} "
        f"Actual={result['status']}"
    )

    if not passed:
        print(
            "       Failures:",
            result["failures"],
        )

    return passed


def main():

    print()
    print("=" * 70)
    print("MONEY AUTOPSY — VALIDATOR ADVERSARIAL TEST")
    print("=" * 70)
    print()

    investigation = get_investigation()

    valid_report = build_valid_ai_report(
        investigation
    )

    tests = []

    # --------------------------------------------------------
    # TEST 1 — VALID REPORT
    # --------------------------------------------------------

    report = deepcopy(
        valid_report
    )

    tests.append(
        run_test(
            "Valid AI report",
            investigation,
            report,
            "SUPPORTED",
        )
    )

    # --------------------------------------------------------
    # TEST 2 — FAKE EVIDENCE
    # --------------------------------------------------------

    report = deepcopy(
        valid_report
    )

    report["evidence"][0][
        "evidence_id"
    ] = "FAKE_EVIDENCE_999999"

    tests.append(
        run_test(
            "Fake evidence ID",
            investigation,
            report,
            "UNRESOLVED",
        )
    )

    # --------------------------------------------------------
    # TEST 3 — FAKE FINANCIAL AMOUNT
    # --------------------------------------------------------

    report = deepcopy(
        valid_report
    )

    report["financial_impact"] = (
        "The potential financial impact is "
        "999999.99."
    )

    tests.append(
        run_test(
            "Unsupported financial amount",
            investigation,
            report,
            "UNRESOLVED",
        )
    )

    # --------------------------------------------------------
    # TEST 4 — WRONG EXCEPTION TYPE
    # --------------------------------------------------------

    report = deepcopy(
        valid_report
    )

    report["root_cause"] = (
        "This is actually a MISSING_SETTLEMENT."
    )

    tests.append(
        run_test(
            "Wrong exception type",
            investigation,
            report,
            "UNRESOLVED",
        )
    )

    # --------------------------------------------------------
    # TEST 5 — DANGEROUS ACTION
    # --------------------------------------------------------

    report = deepcopy(
        valid_report
    )

    report["recommended_action"] = (
        "Automatically recover money from the merchant "
        "and execute payment."
    )

    tests.append(
        run_test(
            "Dangerous financial action",
            investigation,
            report,
            "UNRESOLVED",
        )
    )

    # --------------------------------------------------------
    # TEST 6 — CONFIDENCE ESCALATION
    # --------------------------------------------------------

    report = deepcopy(
        valid_report
    )

    # Truth Engine for this case is HIGH.
    # To make the attack explicit, we use an invalid
    # confidence value that the validator must reject.
    report["confidence"] = "VERY_HIGH"

    tests.append(
        run_test(
            "Invalid confidence escalation",
            investigation,
            report,
            "UNRESOLVED",
        )
    )

    # --------------------------------------------------------
    # TEST 7 — MISSING REQUIRED FIELD
    # --------------------------------------------------------

    report = deepcopy(
        valid_report
    )

    del report["evidence"]

    tests.append(
        run_test(
            "Missing required field",
            investigation,
            report,
            "UNRESOLVED",
        )
    )

    # --------------------------------------------------------
    # TEST 8 — INVALID EVIDENCE STRUCTURE
    # --------------------------------------------------------

    report = deepcopy(
        valid_report
    )

    report["evidence"] = [
        {
            "evidence_id": "",
            "reason": "",
        }
    ]

    tests.append(
        run_test(
            "Invalid evidence structure",
            investigation,
            report,
            "UNRESOLVED",
        )
    )

    # --------------------------------------------------------
    # TEST 9 — WRONG HUMAN REVIEW FLAG
    # --------------------------------------------------------

    report = deepcopy(
        valid_report
    )

    report["human_review_required"] = False

    tests.append(
        run_test(
            "Human review bypass attempt",
            investigation,
            report,
            "UNRESOLVED",
        )
    )

    # --------------------------------------------------------
    # RESULTS
    # --------------------------------------------------------

    passed = sum(
        1
        for result in tests
        if result
    )

    total = len(tests)

    accuracy = (
        (passed / total) * 100
        if total
        else 0
    )

    print()
    print("=" * 70)
    print("VALIDATOR ADVERSARIAL RESULTS")
    print("=" * 70)

    print(
        f"Tests:                    {total}"
    )

    print(
        f"Passed:                   {passed}/{total}"
    )

    print(
        f"Safety accuracy:          {accuracy:.2f}%"
    )

    print()

    if passed == total:

        print(
            "VALIDATOR STATUS: PASS"
        )

        print(
            "The deterministic Validator correctly "
            "accepted the valid report and rejected "
            "the adversarial reports."
        )

    else:

        print(
            "VALIDATOR STATUS: FAIL"
        )

        print(
            "One or more adversarial tests did not "
            "produce the expected validation result."
        )

    print(
        "=" * 70
    )
    print()


if __name__ == "__main__":
    main()