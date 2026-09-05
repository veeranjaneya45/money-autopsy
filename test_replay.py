from backend.truth_engine import investigate_case
from backend.proof_chain import build_investigation
from backend.replay_engine import save_replay, replay_investigation


case_id = "CASE_000234"

# Deterministic investigation
truth = investigate_case(case_id)
investigation = build_investigation(truth)

# Mock AI result — NO Gemini call
ai_report = {
    "executive_summary": "Fee mismatch identified from financial evidence.",
    "root_cause": "Fee activity is inconsistent with the expected fee pattern.",
    "financial_impact": 3965.73,
    "evidence": [
        {
            "evidence_id": "PAY_000234",
            "reason": "Payment establishes the original transaction."
        },
        {
            "evidence_id": "FEE_000234",
            "reason": "Fee record supports the fee mismatch finding."
        }
    ],
    "recommended_action": "Review the fee charge for recovery.",
    "confidence": "HIGH",
    "human_review_required": True,
    "unresolved_reason": None,
}

# Minimal validation object for replay storage
validation = {
    "status": "SUPPORTED",
    "failures": [],
}

decision = {
    "decision": "REVIEW_REQUIRED",
    "reason": "Exception requires human review.",
}

# Save replay
saved = save_replay(
    investigation,
    ai_report,
    validation,
    decision,
)

print("\n=== REPLAY SAVED ===")
print(saved)

replay_id = saved["replay_id"]

# Replay WITHOUT Gemini
replayed = replay_investigation(replay_id)

print("\n=== REPLAY RESULT ===")
print(replayed)

print("\n=== REPLAY TEST COMPLETE ===")
print("Replay ID:", replay_id)