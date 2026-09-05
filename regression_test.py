from backend.truth_engine import investigate_case
from backend.proof_chain import build_proof_chain
from backend.validator import validate_ai_report
from backend.decision_engine import build_decision


TESTS = [
    ("CASE_000001", "NORMAL"),
    ("CASE_000151", "DUPLICATE_REFUND"),
    ("CASE_000181", "MISSING_SETTLEMENT"),
    ("CASE_000206", "PARTIAL_SETTLEMENT"),
    ("CASE_000226", "FEE_MISMATCH"),
    ("CASE_000246", "BANK_REFERENCE_MISMATCH"),
    ("CASE_000261", "TIMING_MISMATCH"),
    ("CASE_000276", "ORPHAN_TRANSACTION"),
    ("CASE_000286", "UNRESOLVED"),
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
            "reason": "This evidence supports the deterministic investigation finding.",
        }
        for item in investigation.get("evidence", [])
        if item.get("record_id")
    ]

    return {
        "executive_summary": (
            "The deterministic investigation identified the reported "
            "financial condition."
        ),
        "root_cause": root_cause,
        "financial_impact": (
            "The financial impact is based only on the deterministic "
            "investigation data."
        ),
        "evidence": evidence,
        "recommended_action": (
            "Review the deterministic findings and supporting evidence "
            "before taking action."
        ),
        "confidence": confidence,
        "human_review_required": status != "NORMAL",
        "unresolved_reason": (
            "Additional evidence is required."
            if status == "UNRESOLVED"
            else ""
        ),
    }


print("MONEY AUTOPSY — END-TO-END REGRESSION")
print("=" * 70)

passed = 0
failed = 0

for case_id, expected_status in TESTS:
    print(f"\n{case_id} — expected {expected_status}")

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

        actual_status = investigation["status"]

        decision_status = decision.get(
            "decision",
            decision.get("status", "UNKNOWN"),
        )

        print(f"  Truth Engine : {actual_status}")
        print(f"  Proof Chain  : {len(proof_chain)} steps")
        print(f"  Validator    : {validation['status']}")
        print(f"  Decision     : {decision_status}")

        if actual_status != expected_status:
            raise AssertionError(
                f"Expected {expected_status}, got {actual_status}"
            )

        if not proof_chain:
            raise AssertionError("Proof Chain is empty")

        if validation["status"] != "SUPPORTED":
            raise AssertionError(
                f"Validator failed: {validation['failures']}"
            )

        if decision_status in (None, "UNKNOWN"):
            raise AssertionError("Decision Engine returned no decision")

        passed += 1
        print("  RESULT       : PASS")

    except Exception as exc:
        failed += 1
        print("  RESULT       : FAIL")
        print(f"  ERROR        : {exc}")


print("\n" + "=" * 70)
print(f"Total cases : {len(TESTS)}")
print(f"Passed      : {passed}")
print(f"Failed      : {failed}")

if failed == 0:
    print("STATUS      : PASS")
else:
    print("STATUS      : FAIL")