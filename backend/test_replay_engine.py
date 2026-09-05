import copy

from backend.replay_engine import (
    save_replay,
    replay_investigation,
)
from backend.truth_engine import investigate_case
from backend.proof_chain import build_investigation
from backend.validator import validate_ai_report
from backend.decision_engine import build_decision


CASE_ID = "CASE_000234"


def build_test_state():
    """
    Build a complete deterministic investigation state
    without calling Gemini.
    """

    truth_result = investigate_case(CASE_ID)

    investigation = build_investigation(
        truth_result
    )

    # Valid deterministic mock AI report.
    # This test does not depend on Gemini quota.
    evidence = investigation.get("evidence", [])

    ai_report = {
        "status": investigation["case"]["status"],
        "exception_type": investigation["case"]["exception_type"],
        "root_cause": (
            "The recorded processing fee does not "
            "match the supported fee-rate rules."
        ),
        "explanation": (
            "The deterministic financial trace establishes "
            "a fee mismatch."
        ),
        "confidence": investigation["case"]["confidence"],
        "evidence": [
            {
                "evidence_id": item["record_id"],
                "reason": "Supports the deterministic finding.",
            }
            for item in evidence
        ],
        "recommended_action": (
            "Route the case to an authorized human "
            "operator for review."
        ),
        "unresolved_reason": None,
        "human_review_required": True,
    }

    validation = validate_ai_report(
        investigation,
        ai_report,
    )

    decision = build_decision(
        investigation,
        validation,
    )

    return (
        investigation,
        ai_report,
        validation,
        decision,
    )


def main():

    print("=" * 70)
    print("MONEY AUTOPSY — REPLAY ENGINE ADVERSARIAL TEST")
    print("=" * 70)
    print()

    investigation, ai_report, validation, decision = (
        build_test_state()
    )

    tests = []

    # ---------------------------------------------------------
    # 1. SAVE REPLAY
    # ---------------------------------------------------------

    try:
        saved = save_replay(
            investigation,
            ai_report,
            validation,
            decision,
        )

        replay_id = saved["replay_id"]

        print(
            f"PASS   Save persistent replay              "
            f"Expected=CREATED           Actual=CREATED"
        )

        tests.append(True)

    except Exception as exc:

        print(
            f"FAIL   Save persistent replay              "
            f"Unexpected error: {exc}"
        )

        return

    # ---------------------------------------------------------
    # 2. REPLAY EXISTS
    # ---------------------------------------------------------

    try:
        replayed = replay_investigation(
            replay_id
        )

        print(
            f"PASS   Load replay snapshot                "
            f"Expected=FOUND             Actual=FOUND"
        )

        tests.append(True)

    except Exception as exc:

        print(
            f"FAIL   Load replay snapshot                "
            f"Unexpected error: {exc}"
        )

        return

    # ---------------------------------------------------------
    # 3. FINGERPRINT MUST MATCH
    # ---------------------------------------------------------

    passed = (
        replayed["fingerprint_match"] is True
    )

    if passed:
        print(
            f"PASS   Fingerprint integrity               "
            f"Expected=MATCH             Actual=MATCH"
        )
    else:
        print(
            f"FAIL   Fingerprint integrity               "
            f"Expected=MATCH             Actual=MISMATCH"
        )

    tests.append(passed)

    # ---------------------------------------------------------
    # 4. TRUTH SNAPSHOT PRESERVED
    # ---------------------------------------------------------

    passed = (
        replayed["investigation"] == investigation
    )

    if passed:
        print(
            f"PASS   Truth snapshot preservation         "
            f"Expected=IDENTICAL         Actual=IDENTICAL"
        )
    else:
        print(
            f"FAIL   Truth snapshot preservation         "
            f"Expected=IDENTICAL         Actual=DIFFERENT"
        )

    tests.append(passed)

    # ---------------------------------------------------------
    # 5. AI SNAPSHOT PRESERVED
    # ---------------------------------------------------------

    passed = (
        replayed["ai_report"] == ai_report
    )

    if passed:
        print(
            f"PASS   AI report preservation              "
            f"Expected=IDENTICAL         Actual=IDENTICAL"
        )
    else:
        print(
            f"FAIL   AI report preservation              "
            f"Expected=IDENTICAL         Actual=DIFFERENT"
        )

    tests.append(passed)

    # ---------------------------------------------------------
    # 6. VALIDATION SNAPSHOT PRESERVED
    # ---------------------------------------------------------

    passed = (
        replayed["validation"] == validation
    )

    if passed:
        print(
            f"PASS   Validation preservation             "
            f"Expected=IDENTICAL         Actual=IDENTICAL"
        )
    else:
        print(
            f"FAIL   Validation preservation             "
            f"Expected=IDENTICAL         Actual=DIFFERENT"
        )

    tests.append(passed)

    # ---------------------------------------------------------
    # 7. DECISION SNAPSHOT PRESERVED
    # ---------------------------------------------------------

    passed = (
        replayed["decision"] == decision
    )

    if passed:
        print(
            f"PASS   Decision preservation               "
            f"Expected=IDENTICAL         Actual=IDENTICAL"
        )
    else:
        print(
            f"FAIL   Decision preservation               "
            f"Expected=IDENTICAL         Actual=DIFFERENT"
        )

    tests.append(passed)

    # ---------------------------------------------------------
    # 8. REPLAY MUST NOT USE LLM
    # ---------------------------------------------------------

    passed = (
        replayed["replay_engine"]["llm_used"]
        is False
        and replayed["replay_engine"]["source"]
        == "postgresql_snapshot"
    )

    if passed:
        print(
            f"PASS   Replay LLM bypass                   "
            f"Expected=NO_LLM            Actual=NO_LLM"
        )
    else:
        print(
            f"FAIL   Replay LLM bypass                   "
            f"Expected=NO_LLM            Actual=LLM_USED"
        )

    tests.append(passed)

    # ---------------------------------------------------------
    # 9. REPLAY RESULT IS DETERMINISTIC
    # ---------------------------------------------------------

    replayed_again = replay_investigation(
        replay_id
    )

    passed = (
        replayed_again["fingerprint"]
        == replayed["fingerprint"]
        and replayed_again["recalculated_fingerprint"]
        == replayed["recalculated_fingerprint"]
        and replayed_again["fingerprint_match"]
        is True
    )

    if passed:
        print(
            f"PASS   Repeated replay consistency         "
            f"Expected=IDENTICAL         Actual=IDENTICAL"
        )
    else:
        print(
            f"FAIL   Repeated replay consistency         "
            f"Expected=IDENTICAL         Actual=DIFFERENT"
        )

    tests.append(passed)

    # ---------------------------------------------------------
    # 10. NONEXISTENT REPLAY MUST FAIL
    # ---------------------------------------------------------

    try:

        replay_investigation(
            "REPLAY_DOES_NOT_EXIST"
        )

        print(
            f"FAIL   Missing replay protection            "
            f"Expected=REJECTED           Actual=ACCEPTED"
        )

        tests.append(False)

    except ValueError:

        print(
            f"PASS   Missing replay protection            "
            f"Expected=REJECTED           Actual=REJECTED"
        )

        tests.append(True)

    # ---------------------------------------------------------
    # FINAL RESULTS
    # ---------------------------------------------------------

    total = len(tests)
    passed_count = sum(tests)

    print()
    print("=" * 70)
    print("REPLAY ENGINE ADVERSARIAL RESULTS")
    print("=" * 70)

    print(f"Tests:                    {total}")
    print(f"Passed:                   {passed_count}/{total}")
    print(
        f"Replay integrity:         "
        f"{passed_count / total * 100:.2f}%"
    )
    print()

    if passed_count == total:

        print("REPLAY ENGINE STATUS: PASS")

        print(
            "The Replay Engine reconstructs the stored "
            "investigation deterministically without "
            "rerunning the LLM."
        )

    else:

        print("REPLAY ENGINE STATUS: FAIL")

        print(
            "Review the failed replay integrity tests."
        )

    print("=" * 70)


if __name__ == "__main__":
    main()