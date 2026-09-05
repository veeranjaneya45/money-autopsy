from typing import Any, Dict, List


# ============================================================
# MONEY AUTOPSY — PROOF CHAIN
# ============================================================
#
# PURPOSE
# -------
# Converts the deterministic Truth Engine result into a
# structured chain of financial evidence.
#
# The Proof Chain answers:
#
#   WHAT happened?
#   WHICH records prove it?
#   HOW was the amount calculated?
#   WHY was the case classified this way?
#   WHAT is the financial impact?
#
# IMPORTANT
# ---------
# This module does NOT calculate financial truth itself.
#
# The Truth Engine remains the source of deterministic truth.
#
# Pipeline:
#
# FIND → TRACE → PROVE → EXPLAIN
#
# ============================================================


PROOF_CHAIN_VERSION = "1.0"


# ============================================================
# HELPERS
# ============================================================

def decimal_to_string(value: Any) -> str:
    """
    Convert Decimal/numeric values into stable string values.

    Financial amounts are represented as strings in the proof
    chain to avoid floating-point ambiguity in JSON.
    """

    if value is None:
        return "0.00"

    return f"{value:.2f}"


def add_step(
    steps: List[Dict[str, Any]],
    step_number: int,
    step_type: str,
    title: str,
    description: str,
    evidence: List[str] | None = None,
    calculation: str | None = None,
) -> None:
    """
    Add one deterministic proof-chain step.
    """

    step = {
        "step": step_number,
        "type": step_type,
        "title": title,
        "description": description,
    }

    if evidence:
        step["evidence"] = evidence

    if calculation:
        step["calculation"] = calculation

    steps.append(step)


# ============================================================
# CASE SUMMARY
# ============================================================

def build_case_summary(
    investigation: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build the high-level financial summary.
    """

    return {
        "case_id": investigation["case_id"],
        "status": investigation["status"],
        "exception_type": investigation.get(
            "exception_type"
        ),
        "confidence": investigation["confidence"],
        "resolution": investigation["resolution"],
        "expected_amount": decimal_to_string(
            investigation["expected_amount"]
        ),
        "observed_amount": decimal_to_string(
            investigation["observed_amount"]
        ),
        "discrepancy_amount": decimal_to_string(
            investigation["discrepancy_amount"]
        ),
        "potential_recovery_amount": decimal_to_string(
            investigation["potential_recovery_amount"]
        ),
    }


# ============================================================
# FINANCIAL TRACE
# ============================================================

def build_financial_trace(
    investigation: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Expose the deterministic financial calculation behind
    the investigation.
    """

    trace = investigation.get(
        "financial_trace",
        {},
    )

    return {
        "payment_amount": decimal_to_string(
            trace.get("payment_amount")
        ),
        "refund_total": decimal_to_string(
            trace.get("refund_total")
        ),
        "fee_total": decimal_to_string(
            trace.get("fee_total")
        ),
        "expected_settlement": decimal_to_string(
            trace.get("expected_settlement")
        ),
        "observed_settlement": decimal_to_string(
            trace.get("observed_settlement")
        ),
        "discrepancy": decimal_to_string(
            trace.get("discrepancy")
        ),
        "formula": (
            "Expected Settlement = "
            "Payment - Refunds - Fees"
        ),
    }


# ============================================================
# BUILD PROOF CHAIN
# ============================================================

def build_proof_chain(
    investigation: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Build a human-readable but machine-verifiable proof chain.

    The chain is generated only from the Truth Engine result.
    """

    steps: List[Dict[str, Any]] = []

    case_id = investigation["case_id"]

    records = investigation.get(
        "records",
        {},
    )

    evidence = investigation.get(
        "evidence",
        [],
    )

    trace = investigation.get(
        "financial_trace",
        {},
    )

    status = investigation["status"]

    # ========================================================
    # STEP 1 — CASE
    # ========================================================

    add_step(
        steps,
        1,
        "CASE",
        "Investigation opened",
        (
            f"Financial investigation opened for "
            f"{case_id}."
        ),
    )

    # ========================================================
    # STEP 2 — PAYMENT
    # ========================================================

    payment_id = records.get(
        "payment_id"
    )

    if payment_id:

        add_step(
            steps,
            2,
            "PAYMENT",
            "Payment identified",
            (
                "The payment establishes the original "
                "financial transaction amount."
            ),
            evidence=[
                payment_id
            ],
        )

    # ========================================================
    # STEP 3 — REFUNDS
    # ========================================================

    refund_evidence = [
        item["record_id"]
        for item in evidence
        if item.get("evidence_type") == "REFUND"
        and item.get("record_id")
    ]

    if refund_evidence:

        add_step(
            steps,
            len(steps) + 1,
            "REFUNDS",
            "Refund activity traced",
            (
                "Refund records were traced against the "
                "payment and included in the settlement "
                "calculation."
            ),
            evidence=refund_evidence,
            calculation=(
                "Refund Total = sum(all payment refunds)"
            ),
        )

    # ========================================================
    # STEP 4 — FEES
    # ========================================================

    fee_evidence = [
        item["record_id"]
        for item in evidence
        if item.get("evidence_type") == "FEE"
        and item.get("record_id")
    ]

    if fee_evidence:

        add_step(
            steps,
            len(steps) + 1,
            "FEES",
            "Fee activity traced",
            (
                "Fee records were traced against the "
                "payment and included in the settlement "
                "calculation."
            ),
            evidence=fee_evidence,
            calculation=(
                "Fee Total = sum(all payment fees)"
            ),
        )

    # ========================================================
    # STEP 5 — SETTLEMENT
    # ========================================================

    settlement_id = records.get(
        "settlement_id"
    )

    if settlement_id:

        add_step(
            steps,
            len(steps) + 1,
            "SETTLEMENT",
            "Settlement traced",
            (
                "The settlement record provides the observed "
                "payout amount used for reconciliation."
            ),
            evidence=[
                settlement_id
            ],
        )

    else:

        add_step(
            steps,
            len(steps) + 1,
            "SETTLEMENT",
            "Settlement record missing",
            (
                "No linked settlement record was available "
                "for this case."
            ),
        )

    # ========================================================
    # STEP 6 — BANK
    # ========================================================

    bank_transaction_id = records.get(
        "bank_transaction_id"
    )

    if bank_transaction_id:

        add_step(
            steps,
            len(steps) + 1,
            "BANK_TRANSACTION",
            "Bank transaction traced",
            (
                "The linked bank transaction was examined "
                "as settlement evidence."
            ),
            evidence=[
                bank_transaction_id
            ],
        )

    # ========================================================
    # STEP 7 — ORPHAN BANK TRANSACTION
    # ========================================================

    orphan_transaction_id = records.get(
        "orphan_transaction_id"
    )

    if orphan_transaction_id:

        add_step(
            steps,
            len(steps) + 1,
            "ORPHAN_TRANSACTION",
            "Unlinked bank transaction discovered",
            (
                "A case-specific bank transaction exists "
                "without settlement linkage."
            ),
            evidence=[
                orphan_transaction_id
            ],
        )

    # ========================================================
    # STEP 8 — FINANCIAL CALCULATION
    # ========================================================

    payment_amount = decimal_to_string(
        trace.get("payment_amount")
    )

    refund_total = decimal_to_string(
        trace.get("refund_total")
    )

    fee_total = decimal_to_string(
        trace.get("fee_total")
    )

    expected_settlement = decimal_to_string(
        trace.get("expected_settlement")
    )

    observed_settlement = decimal_to_string(
        trace.get("observed_settlement")
    )

    discrepancy = decimal_to_string(
        trace.get("discrepancy")
    )

    add_step(
        steps,
        len(steps) + 1,
        "CALCULATION",
        "Settlement reconstructed",
        (
            "The Truth Engine reconstructed the expected "
            "settlement from payment, refunds and fees."
        ),
        calculation=(
            f"{payment_amount} - "
            f"{refund_total} - "
            f"{fee_total} = "
            f"{expected_settlement}"
        ),
    )

    # ========================================================
    # STEP 9 — OBSERVED VS EXPECTED
    # ========================================================

    add_step(
        steps,
        len(steps) + 1,
        "COMPARISON",
        "Expected and observed settlement compared",
        (
            "The reconstructed expected settlement was "
            "compared with the observed settlement amount."
        ),
        calculation=(
            f"Expected ₹{expected_settlement} | "
            f"Observed ₹{observed_settlement} | "
            f"Difference ₹{discrepancy}"
        ),
    )

    # ========================================================
    # STEP 10 — CONCLUSION
    # ========================================================

    if status == "NORMAL":

        title = "No financial exception detected"

        description = (
            "Available payment, refund, fee and settlement "
            "evidence is consistent with the deterministic "
            "financial rules."
        )

    elif status == "UNRESOLVED":

        title = "Investigation unresolved"

        description = (
            "The available evidence does not support a "
            "single reliable root-cause conclusion. "
            "Additional evidence is required."
        )

    else:

        title = (
            f"Exception identified: {status}"
        )

        description = (
            "The Truth Engine identified a specific "
            "financial exception supported by the "
            "available operational evidence."
        )

    add_step(
        steps,
        len(steps) + 1,
        "CONCLUSION",
        title,
        description,
        evidence=[
            item["record_id"]
            for item in evidence
            if item.get("record_id")
        ],
    )

    # ========================================================
    # STEP 11 — IMPACT
    # ========================================================

    recovery = decimal_to_string(
        investigation[
            "potential_recovery_amount"
        ]
    )

    add_step(
        steps,
        len(steps) + 1,
        "IMPACT",
        "Financial impact calculated",
        (
            f"Potential financial recovery or exposure "
            f"identified by the Truth Engine: "
            f"₹{recovery}."
        ),
        calculation=(
            f"Potential Recovery = ₹{recovery}"
        ),
    )

    # ========================================================
    # STEP 12 — RESOLUTION
    # ========================================================

    resolution = investigation[
        "resolution"
    ]

    if resolution == "REQUEST_EVIDENCE":

        description = (
            "Human review should request additional "
            "evidence before reaching a consequential "
            "financial decision."
        )

    elif resolution == "REVIEW":

        description = (
            "The identified exception should be reviewed "
            "by an authorized human operator."
        )

    else:

        description = (
            "No corrective financial action is required "
            "based on the available evidence."
        )

    add_step(
        steps,
        len(steps) + 1,
        "RESOLUTION",
        f"Recommended resolution: {resolution}",
        description,
    )

    return steps


# ============================================================
# BUILD COMPLETE INVESTIGATION
# ============================================================

def build_investigation(
    investigation: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Combine Truth Engine output with the Proof Chain.

    This becomes the structured object consumed later by
    the AI Investigator and API.
    """

    proof_chain = build_proof_chain(
        investigation
    )

    return {
        "case": build_case_summary(
            investigation
        ),

        "finding": {
            "status": investigation["status"],
            "exception_type": investigation.get(
                "exception_type"
            ),
            "confidence": investigation[
                "confidence"
            ],
            "reasons": investigation.get(
                "anomaly_reasons",
                [],
            ),
        },

        "financial_trace": build_financial_trace(
            investigation
        ),

        "proof_chain": proof_chain,

        "evidence": investigation.get(
            "evidence",
            [],
        ),

        "evidence_count": investigation.get(
            "evidence_count",
            0,
        ),

        "truth_engine": investigation.get(
            "truth_engine",
            {},
        ),

        "proof_chain_metadata": {
            "version": PROOF_CHAIN_VERSION,
            "deterministic": True,
            "source": "truth_engine",
            "llm_used": False,
        },
    }