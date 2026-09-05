from backend.decision_engine import build_decision


def make_investigation(
    status="FEE_MISMATCH",
    resolution="REVIEW",
    recovery="3965.73",
):
    return {
        "case": {
            "case_id": "CASE_TEST",
            "status": status,
            "resolution": resolution,
            "potential_recovery_amount": recovery,
        }
    }


def make_validation(status="SUPPORTED"):
    return {
        "status": status
    }


def run_test(name, investigation, validation, expected_decision):
    result = build_decision(investigation, validation)

    actual = result["decision"]

    if actual == expected_decision:
        print(
            f"PASS   {name:<35} "
            f"Expected={expected_decision:<17} "
            f"Actual={actual}"
        )
        return True

    print(
        f"FAIL   {name:<35} "
        f"Expected={expected_decision:<17} "
        f"Actual={actual}"
    )
    return False


def main():

    print("=" * 70)
    print("MONEY AUTOPSY — DECISION ENGINE ADVERSARIAL TEST")
    print("=" * 70)
    print()

    tests = []

    # ---------------------------------------------------------
    # 1. VALID EXCEPTION
    # ---------------------------------------------------------

    tests.append(
        run_test(
            "Valid financial exception",
            make_investigation(
                status="FEE_MISMATCH",
                resolution="REVIEW",
                recovery="3965.73",
            ),
            make_validation("SUPPORTED"),
            "REVIEW_REQUIRED",
        )
    )

    # ---------------------------------------------------------
    # 2. NORMAL CASE
    # ---------------------------------------------------------

    tests.append(
        run_test(
            "Normal case",
            make_investigation(
                status="NORMAL",
                resolution="NO_ACTION",
                recovery="0.00",
            ),
            make_validation("SUPPORTED"),
            "NO_ACTION",
        )
    )

    # ---------------------------------------------------------
    # 3. UNRESOLVED CASE
    # ---------------------------------------------------------

    tests.append(
        run_test(
            "Unresolved financial case",
            make_investigation(
                status="UNRESOLVED",
                resolution="REQUEST_EVIDENCE",
                recovery="0.00",
            ),
            make_validation("SUPPORTED"),
            "REQUEST_EVIDENCE",
        )
    )

    # ---------------------------------------------------------
    # 4. VALIDATOR FAILURE
    # ---------------------------------------------------------

    tests.append(
        run_test(
            "Validator failure",
            make_investigation(
                status="FEE_MISMATCH",
                resolution="REVIEW",
                recovery="3965.73",
            ),
            make_validation("UNRESOLVED"),
            "REQUEST_EVIDENCE",
        )
    )

    # ---------------------------------------------------------
    # 5. UNKNOWN RESOLUTION
    # ---------------------------------------------------------

    tests.append(
        run_test(
            "Unknown resolution fallback",
            make_investigation(
                status="UNKNOWN_EXCEPTION",
                resolution="UNKNOWN",
                recovery="1000.00",
            ),
            make_validation("SUPPORTED"),
            "REQUEST_EVIDENCE",
        )
    )

    # ---------------------------------------------------------
    # 6. VALIDATOR FAILURE MUST OVERRIDE REVIEW
    # ---------------------------------------------------------

    tests.append(
        run_test(
            "Validation overrides financial review",
            make_investigation(
                status="DUPLICATE_REFUND",
                resolution="REVIEW",
                recovery="500.00",
            ),
            make_validation("UNRESOLVED"),
            "REQUEST_EVIDENCE",
        )
    )

    # ---------------------------------------------------------
    # 7. REVIEW REQUIRES HUMAN APPROVAL
    # ---------------------------------------------------------

    investigation = make_investigation(
        status="PARTIAL_SETTLEMENT",
        resolution="REVIEW",
        recovery="2500.00",
    )

    validation = make_validation("SUPPORTED")

    result = build_decision(investigation, validation)

    passed = (
        result["decision"] == "REVIEW_REQUIRED"
        and result["human_approval_required"] is True
        and result["financial_action_allowed"] is False
        and result["execution_status"] == "NOT_EXECUTED"
    )

    if passed:
        print(
            "PASS   Review requires human approval      "
            "Expected=SAFE              Actual=SAFE"
        )
    else:
        print(
            "FAIL   Review requires human approval      "
            "Expected=SAFE              Actual=UNSAFE"
        )

    tests.append(passed)

    # ---------------------------------------------------------
    # 8. NO ACTION MUST NOT REQUIRE HUMAN APPROVAL
    # ---------------------------------------------------------

    investigation = make_investigation(
        status="NORMAL",
        resolution="NO_ACTION",
        recovery="0.00",
    )

    result = build_decision(
        investigation,
        make_validation("SUPPORTED"),
    )

    passed = (
        result["decision"] == "NO_ACTION"
        and result["human_approval_required"] is False
        and result["financial_action_allowed"] is False
        and result["execution_status"] == "NOT_REQUIRED"
    )

    if passed:
        print(
            "PASS   Normal case safety                  "
            "Expected=SAFE              Actual=SAFE"
        )
    else:
        print(
            "FAIL   Normal case safety                  "
            "Expected=SAFE              Actual=UNSAFE"
        )

    tests.append(passed)

    # ---------------------------------------------------------
    # 9. INVALID VALIDATION MUST NEVER ALLOW ACTION
    # ---------------------------------------------------------

    result = build_decision(
        make_investigation(
            status="FEE_MISMATCH",
            resolution="REVIEW",
            recovery="9999.99",
        ),
        make_validation("INVALID"),
    )

    passed = (
        result["decision"] == "REQUEST_EVIDENCE"
        and result["human_approval_required"] is True
        and result["financial_action_allowed"] is False
        and result["execution_status"] == "NOT_EXECUTED"
    )

    if passed:
        print(
            "PASS   Invalid validation safety            "
            "Expected=BLOCKED           Actual=BLOCKED"
        )
    else:
        print(
            "FAIL   Invalid validation safety            "
            "Expected=BLOCKED           Actual=UNSAFE"
        )

    tests.append(passed)

    # ---------------------------------------------------------
    # FINAL RESULTS
    # ---------------------------------------------------------

    total = len(tests)
    passed_count = sum(tests)

    print()
    print("=" * 70)
    print("DECISION ENGINE ADVERSARIAL RESULTS")
    print("=" * 70)

    print(f"Tests:                    {total}")
    print(f"Passed:                   {passed_count}/{total}")
    print(f"Safety accuracy:          {passed_count / total * 100:.2f}%")
    print()

    if passed_count == total:
        print("DECISION ENGINE STATUS: PASS")
        print(
            "The deterministic Decision Engine correctly routes "
            "financial cases without executing financial actions."
        )
    else:
        print("DECISION ENGINE STATUS: FAIL")
        print("Review the failed cases before continuing.")

    print("=" * 70)


if __name__ == "__main__":
    main()