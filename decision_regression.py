from backend.truth_engine import investigate_case
from backend.proof_chain import build_proof_chain
from backend.validator import validate_ai_report
from backend.decision_engine import build_decision


TESTS = [
    ("CASE_000001", "NORMAL", "NO_ACTION"),
    ("CASE_000151", "DUPLICATE_REFUND", "REVIEW_REQUIRED"),
    ("CASE_000181", "MISSING_SETTLEMENT", "REVIEW_REQUIRED"),
    ("CASE_000206", "PARTIAL_SETTLEMENT", "REVIEW_REQUIRED"),
    ("CASE_000226", "FEE_MISMATCH", "REVIEW_REQUIRED"),
    ("CASE_000246", "BANK_REFERENCE_MISMATCH", "REVIEW_REQUIRED"),
    ("CASE_000261", "TIMING_MISMATCH", "REVIEW_REQUIRED"),
    ("CASE_000276", "ORPHAN_TRANSACTION", "REVIEW_REQUIRED"),
    ("CASE_000286", "UNRESOLVED", "REQUEST_EVIDENCE"),
]


def make_mock_ai_report(investigation):
    status = investigation["status"]

    if status == "NORMAL":
        root_cause = "NORMAL"
        confidence = investigation["confidence"]
    elif status == "UNRESOLVED":
        root_cause = "UNRESOLVED"
        confidence = "UNRESOLVED"
    else:
        root_cause = investigation["exception_type"]
        confidence = investigation["confidence"]

    evidence = [
        {
            "evidence_id": item["record_id"],
            "reason": "Evidence supports the deterministic finding.",
        }
        for item in investigation.get("evidence", [])
        if item.get("record_id")
    ]

    return {
        "executive_summary": "Deterministic investigation completed.",
        "root_cause": root_cause,
        "financial_impact": (
            "Impact is based only on deterministic investigation data."
        ),
        "evidence": evidence,
        "recommended_action": (
            "Review the deterministic findings and supporting evidence."
        ),
        "confidence": confidence,
        "human_review_required": status != "NORMAL",
        "unresolved_reason": (
            "Additional evidence is required."
            if status == "UNRESOLVED"
            else ""
        ),
    }


print("MONEY AUTOPSY — DECISION ENGINE REGRESSION")
print("=" * 70)

passed = 0
failed = 0

for case_id, expected_truth, expected_decision in TESTS:

    print(f"\n{case_id}")
    print(f"Expected Truth    : {expected_truth}")
    print(f"Expected Decision : {expected_decision}")

    try:
        investigation = investigate_case(case_id)

        proof_chain = build_proof_chain(investigation)

        ai_report = make_mock_ai_report(investigation)

        validation = validate_ai_report(
            investigation,
            ai_report,
        )

        decision = build_decision(
            investigation,
            validation,
        )

        actual_truth = investigation["status"]

        actual_decision = decision.get(
            "decision",
            decision.get("status"),
        )

        print(f"Actual Truth      : {actual_truth}")
        print(f"Validator         : {validation['status']}")
        print(f"Actual Decision   : {actual_decision}")

        if actual_truth != expected_truth:
            raise AssertionError(
                f"Truth mismatch: expected {expected_truth}, "
                f"got {actual_truth}"
            )

        if validation["status"] != "SUPPORTED":
            raise AssertionError(
                f"Validator failed: {validation['failures']}"
            )

        if actual_decision != expected_decision:
            raise AssertionError(
                f"Decision mismatch: expected {expected_decision}, "
                f"got {actual_decision}"
            )

        passed += 1
        print("RESULT            : PASS")

    except Exception as exc:
        failed += 1
        print("RESULT            : FAIL")
        print(f"ERROR             : {exc}")


print("\n" + "=" * 70)
print(f"Total cases : {len(TESTS)}")
print(f"Passed      : {passed}")
print(f"Failed      : {failed}")

if failed == 0:
    print("STATUS      : PASS")
else:
    print("STATUS      : FAIL")