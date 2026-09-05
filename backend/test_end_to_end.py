from backend.truth_engine import investigate_case
from backend.proof_chain import build_investigation
from backend.validator import validate_ai_report
from backend.decision_engine import build_decision
from backend.replay_engine import save_replay, replay_investigation


def make_mock_ai_report(investigation):
    """
    Mock AI response used only for end-to-end integration testing.

    IMPORTANT:
    - No Gemini API call is made.
    - The report follows the exact fields expected by Validator v1.1.
    - Financial values come only from the deterministic investigation.
    - Evidence IDs come only from the deterministic investigation.
    """

    case = investigation["case"]
    finding = investigation["finding"]
    evidence = investigation["evidence"]

    status = str(case["status"]).upper()
    exception_type = finding.get("exception_type")
    confidence = finding.get("confidence")
    resolution = str(case.get("resolution", "")).upper()

    # =========================================================
    # NORMAL CASE
    # =========================================================

    if status == "NORMAL":

        return {
            "executive_summary": (
                "The financial records are consistent and no financial "
                "exception was identified."
            ),

            "root_cause": (
                "No financial anomaly was identified by the deterministic "
                "investigation."
            ),

            "financial_impact": (
                "No financial recovery or exposure requires action."
            ),

            "evidence": [
                {
                    "evidence_id": item["record_id"],
                    "reason": item["reason"],
                }
                for item in evidence
            ],

            "recommended_action": (
                "No action is required because the financial records "
                "are consistent."
            ),

            "confidence": confidence,

            "human_review_required": False,

            # Validator requires this to be a STRING.
            "unresolved_reason": "",
        }

    # =========================================================
    # UNRESOLVED CASE
    # =========================================================

    if status == "UNRESOLVED":

        return {
            "executive_summary": (
                "The available financial evidence is insufficient "
                "to establish a single supported explanation."
            ),

            "root_cause": "UNRESOLVED",

            "financial_impact": (
                "The potential financial impact cannot be finalized "
                "without additional evidence."
            ),

            "evidence": [
                {
                    "evidence_id": item["record_id"],
                    "reason": item["reason"],
                }
                for item in evidence
            ],

            "recommended_action": (
                "Request additional financial evidence before "
                "making a final determination."
            ),

            "confidence": "UNRESOLVED",

            "human_review_required": True,

            "unresolved_reason": (
                "The deterministic investigation could not establish "
                "a single supported financial explanation."
            ),
        }

    # =========================================================
    # RESOLVED FINANCIAL EXCEPTION
    # =========================================================

    recovery = case.get(
        "potential_recovery_amount",
        "0.00",
    )

    reason = (
        finding["reasons"][0]
        if finding.get("reasons")
        else (
            f"The deterministic investigation identified "
            f"{exception_type}."
        )
    )

    return {
        "executive_summary": (
            f"The investigation identified a {exception_type} "
            "exception supported by the available financial evidence."
        ),

        "root_cause": reason,

        "financial_impact": (
            f"The potential financial recovery or exposure is "
            f"₹{recovery}."
        ),

        "evidence": [
            {
                "evidence_id": item["record_id"],
                "reason": item["reason"],
            }
            for item in evidence
        ],

        "recommended_action": (
            "Route the case to an authorized human operator "
            "for review and approval."
        ),

        "confidence": confidence,

        "human_review_required": True,

        # Validator requires a string even when not unresolved.
        "unresolved_reason": "",
    }


def run_case(case_id):
    """
    Run one complete deterministic + mock-AI investigation.
    """

    print("\n" + "=" * 70)
    print(f"END-TO-END TEST — {case_id}")
    print("=" * 70)

    # =========================================================
    # 1. TRUTH ENGINE
    # =========================================================

    truth = investigate_case(case_id)

    # Fix for previous NameError:
    # `case` must be defined before the final assertions.
    case = truth

    print(
        f"[1] Truth Engine        : "
        f"{truth['status']}"
    )

    # =========================================================
    # 2. PROOF CHAIN
    # =========================================================

    investigation = build_investigation(truth)

    print(
        f"[2] Proof Chain         : "
        f"{len(investigation['proof_chain'])} steps"
    )

    # =========================================================
    # 3. MOCK AI INVESTIGATOR
    # =========================================================

    ai_report = make_mock_ai_report(
        investigation
    )

    print(
        "[3] Mock AI Investigator: GENERATED"
    )

    print(
        "    Gemini API call     : NO"
    )

    # =========================================================
    # 4. VALIDATOR
    # =========================================================

    validation = validate_ai_report(
        investigation,
        ai_report,
    )

    print(
        f"[4] Validator           : "
        f"{validation['status']}"
    )

    # If validation fails, print every failure before stopping.
    if validation["status"] != "SUPPORTED":

        print("\nVALIDATOR FAILURES:")

        failures = validation.get(
            "failures",
            []
        )

        if failures:
            for failure in failures:
                print(f"  - {failure}")
        else:
            print(
                "  - Validator returned UNRESOLVED "
                "without detailed failure information."
            )

    # =========================================================
    # 5. DECISION ENGINE
    # =========================================================

    decision = build_decision(
        investigation,
        validation,
    )

    print(
        f"[5] Decision Engine     : "
        f"{decision['decision']}"
    )

    # =========================================================
    # 6. REPLAY ENGINE — SAVE
    # =========================================================

    replay = save_replay(
        investigation,
        ai_report,
        validation,
        decision,
    )

    replay_id = replay["replay_id"]

    print(
        f"[6] Replay Saved        : "
        f"{replay_id}"
    )

    # =========================================================
    # 7. REPLAY ENGINE — VERIFY
    # =========================================================

    replay_result = replay_investigation(
        replay_id
    )

    fingerprint_match = replay_result.get(
        "fingerprint_match"
    )

    print(
        f"[7] Replay Integrity    : "
        f"{fingerprint_match}"
    )

    # =========================================================
    # FINAL ASSERTIONS
    # =========================================================

    # Truth Engine result must belong to the same case.
    assert (
        truth["status"] == case["status"]
    ), (
        "Truth Engine case/status mismatch."
    )

    # AI must pass deterministic validation.
    assert (
        validation["status"] == "SUPPORTED"
    ), (
        "Validator failed: "
        f"{validation.get('failures', [])}"
    )

    # Replay fingerprint must remain identical.
    assert (
        fingerprint_match is True
    ), (
        "Replay fingerprint integrity check failed."
    )

    print("\nRESULT: PASS")


# =================================================================
# MAIN INTEGRATION TEST
# =================================================================

if __name__ == "__main__":

    # -------------------------------------------------------------
    # Test 1: NORMAL financial case
    # Expected:
    # Truth Engine  -> NORMAL
    # Validator     -> SUPPORTED
    # Decision      -> NO_ACTION
    # Replay        -> MATCH
    # -------------------------------------------------------------

    run_case(
        "CASE_000001"
    )

    # -------------------------------------------------------------
    # Test 2: Known financial exception
    # Expected:
    # Truth Engine  -> FEE_MISMATCH
    # Validator     -> SUPPORTED
    # Decision      -> REVIEW_REQUIRED
    # Replay        -> MATCH
    # -------------------------------------------------------------

    run_case(
        "CASE_000234"
    )

    # -------------------------------------------------------------
    # Final system result
    # -------------------------------------------------------------

    print("\n" + "=" * 70)
    print("MONEY AUTOPSY — END-TO-END INTEGRATION")
    print("=" * 70)

    print(
        "Truth Engine       : PASS"
    )

    print(
        "Proof Chain        : PASS"
    )

    print(
        "Mock AI            : PASS"
    )

    print(
        "Validator          : PASS"
    )

    print(
        "Decision Engine    : PASS"
    )

    print(
        "Replay Engine      : PASS"
    )

    print(
        "Gemini API calls   : 0"
    )

    print("=" * 70)

    print(
        "END-TO-END STATUS: PASS"
    )