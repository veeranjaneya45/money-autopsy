from backend.human_review import record_human_decision
from backend.truth_engine import investigate_case
from backend.proof_chain import build_investigation


CASE_ID = "CASE_000234"


def get_investigation(case_id=CASE_ID):
    truth = investigate_case(case_id)
    return build_investigation(truth)


def expect_success(name, func):
    try:
        result = func()

        if result.get("financial_action", {}).get("executed") is False:
            print(
                f"PASS   {name:<40} "
                f"Expected=SAFE              Actual=SAFE"
            )
            return True

        print(
            f"FAIL   {name:<40} "
            f"Expected=SAFE              Actual=UNSAFE"
        )
        return False

    except Exception as exc:
        print(
            f"FAIL   {name:<40} "
            f"Unexpected error: {exc}"
        )
        return False


def expect_rejection(name, func):
    try:
        func()

        print(
            f"FAIL   {name:<40} "
            f"Expected=REJECTED           Actual=ACCEPTED"
        )
        return False

    except ValueError:
        print(
            f"PASS   {name:<40} "
            f"Expected=REJECTED           Actual=REJECTED"
        )
        return True

    except Exception as exc:
        print(
            f"FAIL   {name:<40} "
            f"Expected=ValueError         Actual={type(exc).__name__}"
        )
        return False


def main():

    print("=" * 70)
    print("MONEY AUTOPSY — HUMAN REVIEW ADVERSARIAL TEST")
    print("=" * 70)
    print()

    investigation = get_investigation()

    tests = []

    # ---------------------------------------------------------
    # 1. VALID APPROVAL
    # ---------------------------------------------------------

    tests.append(
        expect_success(
            "Valid human approval",
            lambda: record_human_decision(
                CASE_ID,
                "APPROVED",
                "Evidence supports the identified financial exception.",
                "reviewer_001",
                investigation,
            ),
        )
    )

    # ---------------------------------------------------------
    # 2. VALID REJECTION
    # ---------------------------------------------------------

    tests.append(
        expect_success(
            "Valid human rejection",
            lambda: record_human_decision(
                CASE_ID,
                "REJECTED",
                "Review found insufficient basis for the proposed action.",
                "reviewer_002",
                investigation,
            ),
        )
    )

    # ---------------------------------------------------------
    # 3. VALID REQUEST FOR EVIDENCE
    # ---------------------------------------------------------

    tests.append(
        expect_success(
            "Valid evidence request",
            lambda: record_human_decision(
                CASE_ID,
                "REQUEST_EVIDENCE",
                "Additional settlement evidence is required.",
                "reviewer_003",
                investigation,
            ),
        )
    )

    # ---------------------------------------------------------
    # 4. INVALID DECISION
    # ---------------------------------------------------------

    tests.append(
        expect_rejection(
            "Invalid decision value",
            lambda: record_human_decision(
                CASE_ID,
                "TRANSFER_MONEY",
                "Attempted unsupported financial action.",
                "reviewer_004",
                investigation,
            ),
        )
    )

    # ---------------------------------------------------------
    # 5. EMPTY REVIEWER
    # ---------------------------------------------------------

    tests.append(
        expect_rejection(
            "Empty reviewer",
            lambda: record_human_decision(
                CASE_ID,
                "APPROVED",
                "Evidence reviewed.",
                "",
                investigation,
            ),
        )
    )

    # ---------------------------------------------------------
    # 6. EMPTY REASON
    # ---------------------------------------------------------

    tests.append(
        expect_rejection(
            "Empty decision reason",
            lambda: record_human_decision(
                CASE_ID,
                "APPROVED",
                "",
                "reviewer_005",
                investigation,
            ),
        )
    )

    # ---------------------------------------------------------
    # 7. CASE ID MISMATCH
    # ---------------------------------------------------------

    tests.append(
        expect_rejection(
            "Case ID mismatch",
            lambda: record_human_decision(
                "CASE_999999",
                "APPROVED",
                "Attempted decision on another case.",
                "reviewer_006",
                investigation,
            ),
        )
    )

    # ---------------------------------------------------------
    # 8. UNRESOLVED CASE CANNOT BE APPROVED
    # ---------------------------------------------------------

    unresolved_investigation = get_investigation()

    unresolved_investigation["case"]["status"] = "UNRESOLVED"

    tests.append(
        expect_rejection(
            "Unresolved case approval",
            lambda: record_human_decision(
                CASE_ID,
                "APPROVED",
                "Attempted approval without sufficient evidence.",
                "reviewer_007",
                unresolved_investigation,
            ),
        )
    )

    # ---------------------------------------------------------
    # 9. UNRESOLVED CASE CANNOT BE REJECTED
    # ---------------------------------------------------------

    tests.append(
        expect_rejection(
            "Unresolved case rejection",
            lambda: record_human_decision(
                CASE_ID,
                "REJECTED",
                "Attempted rejection without sufficient evidence.",
                "reviewer_008",
                unresolved_investigation,
            ),
        )
    )

    # ---------------------------------------------------------
    # 10. FINANCIAL ACTION MUST NEVER EXECUTE
    # ---------------------------------------------------------

    result = record_human_decision(
        CASE_ID,
        "APPROVED",
        "Final review completed based on available evidence.",
        "reviewer_009",
        investigation,
    )

    financial_action = result.get(
        "financial_action",
        {},
    )

    passed = (
        financial_action.get("executed") is False
        and financial_action.get("status") == "NOT_EXECUTED"
        and result.get("human_review", {}).get("llm_used") is False
    )

    if passed:
        print(
            "PASS   Financial action safety             "
            "Expected=BLOCKED           Actual=BLOCKED"
        )
    else:
        print(
            "FAIL   Financial action safety             "
            "Expected=BLOCKED           Actual=EXECUTED"
        )

    tests.append(passed)

    # ---------------------------------------------------------
    # FINAL RESULTS
    # ---------------------------------------------------------

    total = len(tests)
    passed = sum(tests)

    print()
    print("=" * 70)
    print("HUMAN REVIEW ADVERSARIAL RESULTS")
    print("=" * 70)

    print(f"Tests:                    {total}")
    print(f"Passed:                   {passed}/{total}")
    print(f"Safety accuracy:          {passed / total * 100:.2f}%")
    print()

    if passed == total:
        print("HUMAN REVIEW STATUS: PASS")
        print(
            "The Human Review layer correctly records "
            "authorized decisions while preventing "
            "unresolved findings and financial execution."
        )
    else:
        print("HUMAN REVIEW STATUS: FAIL")
        print(
            "Review the failed cases before continuing."
        )

    print("=" * 70)


if __name__ == "__main__":
    main()