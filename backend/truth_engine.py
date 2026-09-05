from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

from backend.database import fetch_all, fetch_one


# ============================================================
# MONEY AUTOPSY
# TRUTH ENGINE
# ============================================================
#
# PURPOSE
# -------
# The Truth Engine establishes deterministic financial truth
# from operational financial records.
#
# IMPORTANT PRINCIPLES
# --------------------
# 1. NEVER reads ground_truth.
# 2. NEVER asks an LLM to calculate financial truth.
# 3. NEVER invents missing evidence.
# 4. UNRESOLVED is a first-class outcome.
# 5. Every conclusion is based on database evidence.
# 6. Same input data must produce the same result.
#
# The AI Investigator will come AFTER this layer.
#
# Pipeline:
#
# FIND → TRACE → PROVE → EXPLAIN
#
# ============================================================


TRUTH_ENGINE_VERSION = "1.2"


# ============================================================
# MONEY HELPERS
# ============================================================

def money(value: Any) -> Decimal:
    """
    Convert a value to a 2-decimal Decimal.
    """

    if value is None:
        return Decimal("0.00")

    return Decimal(str(value)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


# ============================================================
# SAFE RECORD HELPERS
# ============================================================

def record_id(
    record: Optional[Dict[str, Any]],
    evidence_type: Optional[str] = None,
) -> Optional[str]:
    """
    Return the correct human-readable business identifier for a database record.

    Evidence types are mapped explicitly to their corresponding business IDs
    so foreign-key fields such as payment_id or settlement_id are never
    mistaken for the record's own identifier.
    """

    if not record:
        return None

    evidence_id_map = {
        "PAYMENT": "payment_id",
        "ORDER": "order_id",
        "REFUND": "refund_id",
        "FEE": "fee_id",
        "SETTLEMENT": "settlement_id",
        "LEDGER": "ledger_entry_id",
        "BANK_TRANSACTION": "bank_transaction_id",
        "ORPHAN_BANK_TRANSACTION": "bank_transaction_id",
    }

    if evidence_type:
        key = evidence_id_map.get(evidence_type)

        if key and record.get(key):
            return str(record[key])

    # Safe fallback for records where the evidence type is not supplied.
    possible_keys = [
        "payment_id",
        "order_id",
        "refund_id",
        "fee_id",
        "settlement_id",
        "bank_transaction_id",
        "ledger_entry_id",
        "case_id",
    ]

    for key in possible_keys:
        if record.get(key):
            return str(record[key])

    return None


# ============================================================
# LOAD CASE
# ============================================================

def load_case(case_id: str) -> Optional[Dict[str, Any]]:
    """
    Load the reconciliation case and its primary relationships.
    """

    query = """
        SELECT
            rc.id AS case_uuid,
            rc.case_id,
            rc.merchant_id,
            rc.payment_id,
            rc.settlement_id,
            rc.case_status,
            rc.exception_type,
            rc.expected_amount,
            rc.observed_amount,
            rc.discrepancy_amount,
            rc.potential_recovery_amount,
            rc.priority,
            rc.created_at,
            rc.updated_at,

            m.merchant_id AS merchant_code,
            m.name AS merchant_name,
            m.currency AS merchant_currency

        FROM reconciliation_cases rc

        JOIN merchants m
            ON m.id = rc.merchant_id

        WHERE rc.case_id = %s;
    """

    return fetch_one(query, (case_id,))


# ============================================================
# LOAD PAYMENT
# ============================================================

def load_payment(payment_uuid: Any) -> Optional[Dict[str, Any]]:
    """
    Load the payment belonging to the case.
    """

    if not payment_uuid:
        return None

    query = """
        SELECT
            id,
            payment_id,
            order_id,
            merchant_id,
            amount,
            currency,
            status,
            payment_reference,
            captured_at,
            created_at

        FROM payments

        WHERE id = %s;
    """

    return fetch_one(query, (payment_uuid,))


# ============================================================
# LOAD ORDER
# ============================================================

def load_order(order_uuid: Any) -> Optional[Dict[str, Any]]:
    """
    Load the order belonging to the payment.
    """

    if not order_uuid:
        return None

    query = """
        SELECT
            id,
            order_id,
            merchant_id,
            order_amount,
            currency,
            status,
            created_at

        FROM orders

        WHERE id = %s;
    """

    return fetch_one(query, (order_uuid,))


# ============================================================
# LOAD REFUNDS
# ============================================================

def load_refunds(payment_uuid: Any) -> List[Dict[str, Any]]:
    """
    Load all refunds for the payment.
    """

    if not payment_uuid:
        return []

    query = """
        SELECT
            id,
            refund_id,
            payment_id,
            order_id,
            merchant_id,
            amount,
            currency,
            status,
            refund_reference,
            created_at

        FROM refunds

        WHERE payment_id = %s

        ORDER BY created_at ASC, refund_id ASC;
    """

    return list(fetch_all(query, (payment_uuid,)))


# ============================================================
# LOAD FEES
# ============================================================

def load_fees(payment_uuid: Any) -> List[Dict[str, Any]]:
    """
    Load all fees for the payment.
    """

    if not payment_uuid:
        return []

    query = """
        SELECT
            id,
            fee_id,
            payment_id,
            merchant_id,
            amount,
            currency,
            fee_type,
            created_at

        FROM fees

        WHERE payment_id = %s

        ORDER BY created_at ASC, fee_id ASC;
    """

    return list(fetch_all(query, (payment_uuid,)))


# ============================================================
# LOAD SETTLEMENT
# ============================================================

def load_settlement(settlement_uuid: Any) -> Optional[Dict[str, Any]]:
    """
    Load the settlement linked to the reconciliation case.
    """

    if not settlement_uuid:
        return None

    query = """
        SELECT
            id,
            settlement_id,
            merchant_id,
            payment_id,
            expected_amount,
            settled_amount,
            currency,
            status,
            settlement_reference,
            settlement_date,
            created_at

        FROM settlements

        WHERE id = %s;
    """

    return fetch_one(query, (settlement_uuid,))


# ============================================================
# LOAD BANK TRANSACTION
# ============================================================

def load_linked_bank_transaction(
    merchant_uuid: Any,
    settlement_uuid: Any,
) -> Optional[Dict[str, Any]]:
    """
    Load the bank transaction explicitly linked to the settlement.

    This is intentionally different from orphan detection.

    A linked transaction is evidence about a settlement.

    An orphan transaction has settlement_id = NULL and is handled
    separately.
    """

    if not merchant_uuid or not settlement_uuid:
        return None

    query = """
        SELECT
            id,
            bank_transaction_id,
            merchant_id,
            settlement_id,
            amount,
            currency,
            bank_reference,
            status,
            transaction_date,
            created_at

        FROM bank_transactions

        WHERE merchant_id = %s
          AND settlement_id = %s

        ORDER BY created_at ASC, bank_transaction_id ASC
        LIMIT 1;
    """

    return fetch_one(
        query,
        (
            merchant_uuid,
            settlement_uuid,
        ),
    )


# ============================================================
# FIND EXACT ORPHAN TRANSACTION
# ============================================================

def load_exact_orphan_transaction(
    merchant_uuid: Any,
    case_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Find the orphan transaction belonging to this exact case.

    Example:

        CASE_000276

    must map to:

        ORPHANREF_00000276

    We do NOT search merely by merchant or amount because multiple
    orphan transactions can belong to the same merchant.
    """

    if not merchant_uuid:
        return None

    try:
        case_number = int(case_id.split("_")[-1])
    except (ValueError, AttributeError):
        return None

    expected_orphan_reference = (
        f"ORPHANREF_{case_number:08d}"
    )

    query = """
        SELECT
            id,
            bank_transaction_id,
            merchant_id,
            settlement_id,
            amount,
            currency,
            bank_reference,
            status,
            transaction_date,
            created_at

        FROM bank_transactions

        WHERE merchant_id = %s
          AND settlement_id IS NULL
          AND bank_reference = %s

        LIMIT 1;
    """

    return fetch_one(
        query,
        (
            merchant_uuid,
            expected_orphan_reference,
        ),
    )


# ============================================================
# LOAD LEDGER ENTRY
# ============================================================

def load_ledger_entry(
    payment_uuid: Any,
    settlement_uuid: Any,
) -> Optional[Dict[str, Any]]:
    """
    Load the ledger entry supporting the settlement.
    """

    if not payment_uuid and not settlement_uuid:
        return None

    query = """
        SELECT
            id,
            ledger_entry_id,
            merchant_id,
            payment_id,
            settlement_id,
            debit,
            credit,
            currency,
            entry_type,
            created_at

        FROM ledger_entries

        WHERE (
            payment_id = %s
            OR settlement_id = %s
        )

        ORDER BY created_at ASC, ledger_entry_id ASC

        LIMIT 1;
    """

    return fetch_one(
        query,
        (
            payment_uuid,
            settlement_uuid,
        ),
    )


# ============================================================
# BUILD EVIDENCE
# ============================================================

def evidence_item(
    evidence_type: str,
    record: Optional[Dict[str, Any]],
    reason: str,
) -> Optional[Dict[str, Any]]:
    """
    Convert a database record into an evidence object.
    """

    if not record:
        return None

    return {
        "evidence_type": evidence_type,
        "record_id": record_id(record, evidence_type),
        "reason": reason,
    }


# ============================================================
# INVESTIGATE ONE CASE
# ============================================================

def investigate_case(case_id: str) -> Dict[str, Any]:
    """
    Deterministically investigate one reconciliation case.

    Returns a structured investigation result.
    """

    case = load_case(case_id)

    if not case:
        raise ValueError(
            f"Case not found: {case_id}"
        )

    payment = load_payment(
        case["payment_id"]
    )

    order = None

    if payment:
        order = load_order(
            payment["order_id"]
        )

    refunds = load_refunds(
        case["payment_id"]
    )

    fees = load_fees(
        case["payment_id"]
    )

    settlement = load_settlement(
        case["settlement_id"]
    )

    bank_transaction = load_linked_bank_transaction(
        case["merchant_id"],
        case["settlement_id"],
    )

    orphan_transaction = load_exact_orphan_transaction(
        case["merchant_id"],
        case["case_id"],
    )

    ledger_entry = load_ledger_entry(
        case["payment_id"],
        case["settlement_id"],
    )

    # ========================================================
    # FINANCIAL CALCULATION
    # ========================================================

    payment_amount = money(
        payment["amount"]
        if payment
        else Decimal("0.00")
    )

    refund_total = sum(
        (
            money(refund["amount"])
            for refund in refunds
        ),
        Decimal("0.00"),
    )

    fee_total = sum(
        (
            money(fee["amount"])
            for fee in fees
        ),
        Decimal("0.00"),
    )

    # --------------------------------------------------------
    # Financial truth
    # --------------------------------------------------------
    #
    # Expected settlement =
    #
    # payment
    # - refunds
    # - fees
    #
    # It can never be negative.
    #

    expected_settlement = money(
        max(
            Decimal("0.00"),
            payment_amount
            - refund_total
            - fee_total,
        )
    )

    observed_settlement = money(
        settlement["settled_amount"]
        if settlement
        else Decimal("0.00")
    )

    discrepancy = money(
        abs(
            expected_settlement
            - observed_settlement
        )
    )

    # ========================================================
    # ANOMALY COLLECTION
    # ========================================================

    detected_exceptions: List[str] = []
    anomaly_reasons: List[str] = []

    evidence: List[Dict[str, Any]] = []

    # ========================================================
    # CORE EVIDENCE
    # ========================================================

    item = evidence_item(
        "PAYMENT",
        payment,
        "Payment amount establishes the original financial obligation.",
    )

    if item:
        evidence.append(item)

    item = evidence_item(
        "ORDER",
        order,
        "Order establishes the originating transaction.",
    )

    if item:
        evidence.append(item)

    item = evidence_item(
        "SETTLEMENT",
        settlement,
        "Settlement establishes the expected and observed payout.",
    )

    if item:
        evidence.append(item)

    item = evidence_item(
        "LEDGER",
        ledger_entry,
        "Ledger entry provides accounting evidence for the settlement.",
    )

    if item:
        evidence.append(item)

    # ========================================================
    # REFUND EVIDENCE
    # ========================================================

    for refund in refunds:

        item = evidence_item(
            "REFUND",
            refund,
            "Refund record contributes to settlement calculation.",
        )

        if item:
            evidence.append(item)

    # ========================================================
    # FEE EVIDENCE
    # ========================================================

    for fee in fees:

        item = evidence_item(
            "FEE",
            fee,
            "Fee record contributes to settlement calculation.",
        )

        if item:
            evidence.append(item)

    # ========================================================
    # BANK EVIDENCE
    # ========================================================

    item = evidence_item(
        "BANK_TRANSACTION",
        bank_transaction,
        "Linked bank transaction provides settlement-bank evidence.",
    )

    if item:
        evidence.append(item)

    item = evidence_item(
        "ORPHAN_BANK_TRANSACTION",
        orphan_transaction,
        "Case-specific orphan bank transaction has no settlement linkage.",
    )

    if item:
        evidence.append(item)

    # ========================================================
    # 1. DUPLICATE REFUND
    # ========================================================

    if len(refunds) > 1:

        refund_references = [
            refund.get("refund_reference")
            for refund in refunds
        ]

        detected_exceptions.append(
            "DUPLICATE_REFUND"
        )

        anomaly_reasons.append(
            "Multiple completed refunds exist for the same payment."
        )

        # The duplicate refund is the additional refund.
        #
        # Because refunds are ordered by creation time, the second
        # refund represents the duplicate exposure in the synthetic
        # dataset.

    # ========================================================
    # 2. FEE MISMATCH
    # ========================================================

    if fees:

        actual_fee = fee_total

        possible_rates = [
            Decimal("0.015"),
            Decimal("0.020"),
            Decimal("0.025"),
        ]

        expected_fee_candidates = [
            money(
                payment_amount * rate
            )
            for rate in possible_rates
        ]

        if not any(
            actual_fee == candidate
            for candidate in expected_fee_candidates
        ):

            detected_exceptions.append(
                "FEE_MISMATCH"
            )

            anomaly_reasons.append(
                "Recorded processing fee does not match "
                "the supported fee-rate rules."
            )

    # ========================================================
    # 3. MISSING SETTLEMENT
    # ========================================================

    if (
        settlement is None
        or settlement.get("status") == "MISSING"
    ):

        detected_exceptions.append(
            "MISSING_SETTLEMENT"
        )

        anomaly_reasons.append(
            "Expected settlement is missing."
        )

    # ========================================================
    # 4. PARTIAL SETTLEMENT
    # ========================================================

    if (
        settlement is not None
        and settlement.get("status") == "PARTIAL"
        and observed_settlement < expected_settlement
    ):

        detected_exceptions.append(
            "PARTIAL_SETTLEMENT"
        )

        anomaly_reasons.append(
            "Settlement amount is lower than the "
            "deterministically expected amount."
        )

    # ========================================================
    # 5. BANK REFERENCE / EVIDENCE ANALYSIS
    # ========================================================

    #
    # IMPORTANT:
    #
    # Missing reference ≠ reference mismatch.
    #
    # A mismatch means we have enough evidence to prove that
    # two references disagree.
    #
    # A missing reference means we cannot establish the cause.
    #
    # Therefore:
    #
    # missing reference → UNRESOLVED
    #
    # wrong reference → BANK_REFERENCE_MISMATCH
    #

    if bank_transaction:

        actual_reference = (
            bank_transaction.get(
                "bank_reference"
            )
        )

        expected_reference = None

        if settlement:

            settlement_reference = (
                settlement.get(
                    "settlement_reference"
                )
            )

            if settlement_reference:
                if settlement_reference.startswith(
                    "SETREF_"
                ):
                    expected_reference = (
                        settlement_reference.replace(
                            "SETREF_",
                            "BANKREF_",
                            1,
                        )
                    )

        # ----------------------------------------------------
        # Missing evidence
        # ----------------------------------------------------

        if not actual_reference:

            detected_exceptions.append(
                "UNRESOLVED"
            )

            anomaly_reasons.append(
                "Bank settlement reference is missing; "
                "root cause cannot be established from "
                "the available evidence."
            )

        # ----------------------------------------------------
        # Proven mismatch
        # ----------------------------------------------------

        elif (
            expected_reference
            and actual_reference != expected_reference
        ):

            detected_exceptions.append(
                "BANK_REFERENCE_MISMATCH"
            )

            anomaly_reasons.append(
                "Bank reference does not match the "
                "reference expected from the settlement."
            )

    # ========================================================
    # 6. TIMING MISMATCH
    # ========================================================

    if (
        payment
        and payment.get("captured_at")
        and settlement
        and settlement.get("settlement_date")
    ):

        capture_time = payment["captured_at"]
        settlement_time = settlement["settlement_date"]

        elapsed = (
            settlement_time
            - capture_time
        )

        elapsed_hours = (
            elapsed.total_seconds()
            / 3600
        )

        if elapsed_hours > 48:

            detected_exceptions.append(
                "TIMING_MISMATCH"
            )

            anomaly_reasons.append(
                "Settlement occurred more than "
                "48 hours after payment capture."
            )

    # ========================================================
    # 7. ORPHAN TRANSACTION
    # ========================================================

    #
    # CRITICAL:
    #
    # We match the orphan using the exact case-specific
    # ORPHANREF identifier.
    #
    # This prevents one case's orphan transaction from being
    # accidentally attributed to another case belonging to
    # the same merchant.
    #

    if orphan_transaction:

        detected_exceptions.append(
            "ORPHAN_TRANSACTION"
        )

        anomaly_reasons.append(
            "A case-specific bank transaction exists "
            "without settlement linkage."
        )

    # ========================================================
    # DEDUPLICATE EXCEPTIONS
    # ========================================================

    detected_exceptions = list(
        dict.fromkeys(
            detected_exceptions
        )
    )

    anomaly_reasons = list(
        dict.fromkeys(
            anomaly_reasons
        )
    )

    # ========================================================
    # DETERMINE FINAL STATUS
    # ========================================================

    #
    # UNRESOLVED has priority.
    #
    # If evidence is insufficient, the engine must not pretend
    # that it knows the root cause.
    #

    if "UNRESOLVED" in detected_exceptions:

        final_status = "UNRESOLVED"

        resolution = "REQUEST_EVIDENCE"

        confidence = "LOW"

        potential_recovery_amount = Decimal(
            "0.00"
        )

    # --------------------------------------------------------
    # Multiple proven anomalies
    # --------------------------------------------------------

    elif len(detected_exceptions) > 1:

        final_status = "UNRESOLVED"

        resolution = "REQUEST_EVIDENCE"

        confidence = "LOW"

        potential_recovery_amount = Decimal(
            "0.00"
        )

        anomaly_reasons.append(
            "Multiple independent anomalies were detected; "
            "the available evidence does not support a single "
            "root-cause conclusion."
        )

    # --------------------------------------------------------
    # No anomaly
    # --------------------------------------------------------

    elif len(detected_exceptions) == 0:

        final_status = "NORMAL"

        resolution = "NO_ACTION"

        confidence = "HIGH"

        potential_recovery_amount = Decimal(
            "0.00"
        )

    # --------------------------------------------------------
    # One proven anomaly
    # --------------------------------------------------------

    else:

        final_status = detected_exceptions[0]

        resolution = "REVIEW"

        confidence = "HIGH"

        # ----------------------------------------------------
        # Recovery calculations
        # ----------------------------------------------------

        if final_status == "DUPLICATE_REFUND":

            if len(refunds) > 1:

                potential_recovery_amount = max(
                    money(
                        refunds[1]["amount"]
                    ),
                    Decimal("0.00"),
                )

            else:

                potential_recovery_amount = max(
                    refund_total
                    - payment_amount,
                    Decimal("0.00"),
                )

        elif final_status == "MISSING_SETTLEMENT":

            potential_recovery_amount = max(
                expected_settlement,
                Decimal("0.00"),
            )

        elif final_status == "PARTIAL_SETTLEMENT":

            potential_recovery_amount = max(
                discrepancy,
                Decimal("0.00"),
            )

        elif final_status == "FEE_MISMATCH":

            potential_recovery_amount = max(
                fee_total,
                Decimal("0.00"),
            )

        elif final_status == "BANK_REFERENCE_MISMATCH":

            potential_recovery_amount = max(
                observed_settlement,
                Decimal("0.00"),
            )

        elif final_status == "ORPHAN_TRANSACTION":

            if orphan_transaction:

                potential_recovery_amount = money(
                    orphan_transaction["amount"]
                )

            else:

                potential_recovery_amount = Decimal(
                    "0.00"
                )

        else:

            potential_recovery_amount = Decimal(
                "0.00"
            )

    # ========================================================
    # BUILD RESULT
    # ========================================================

    result = {
        "case_id": case["case_id"],

        "status": final_status,

        "exception_type": (
            final_status
            if final_status != "NORMAL"
            else None
        ),

        "resolution": resolution,

        "confidence": confidence,

        "expected_amount": expected_settlement,

        "observed_amount": observed_settlement,

        "discrepancy_amount": discrepancy,

        "potential_recovery_amount": (
            money(
                potential_recovery_amount
            )
        ),

        "anomaly_reasons": anomaly_reasons,

        "detected_exceptions": detected_exceptions,

        "evidence": evidence,

        "evidence_count": len(evidence),

        "financial_trace": {
            "payment_amount": payment_amount,
            "refund_total": refund_total,
            "fee_total": fee_total,
            "expected_settlement": expected_settlement,
            "observed_settlement": observed_settlement,
            "discrepancy": discrepancy,
        },

        "records": {
            "payment_id": (
                payment.get("payment_id")
                if payment
                else None
            ),

            "order_id": (
                order.get("order_id")
                if order
                else None
            ),

            "settlement_id": (
                settlement.get("settlement_id")
                if settlement
                else None
            ),

            "bank_transaction_id": (
                bank_transaction.get(
                    "bank_transaction_id"
                )
                if bank_transaction
                else None
            ),

            "orphan_transaction_id": (
                orphan_transaction.get(
                    "bank_transaction_id"
                )
                if orphan_transaction
                else None
            ),
        },

        # ====================================================
        # TRUST METADATA
        # ====================================================

        "truth_engine": {
            "version": TRUTH_ENGINE_VERSION,
            "deterministic": True,
            "used_ground_truth": False,
        },
    }

    return result


# ============================================================
# INVESTIGATE ALL CASES
# ============================================================

def investigate_all_cases(
    limit: int = 300,
) -> List[Dict[str, Any]]:
    """
    Investigate multiple reconciliation cases.

    Cases are processed in deterministic case-id order.
    """

    if limit < 1:
        return []

    if limit > 500:
        limit = 500

    query = """
        SELECT
            case_id

        FROM reconciliation_cases

        ORDER BY created_at ASC, case_id ASC

        LIMIT %s;
    """

    cases = fetch_all(
        query,
        (limit,),
    )

    results: List[Dict[str, Any]] = []

    for case in cases:

        result = investigate_case(
            case["case_id"]
        )

        results.append(result)

    return results


# ============================================================
# SIMPLE CLI TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("MONEY AUTOPSY — TRUTH ENGINE TEST")
    print("=" * 60)

    results = investigate_all_cases(10)

    for result in results:

        print()
        print(
            f"Case:       {result['case_id']}"
        )

        print(
            f"Status:     {result['status']}"
        )

        print(
            f"Confidence: {result['confidence']}"
        )

        print(
            f"Expected:   "
            f"₹{result['expected_amount']}"
        )

        print(
            f"Observed:   "
            f"₹{result['observed_amount']}"
        )

        print(
            f"Recovery:   "
            f"₹{result['potential_recovery_amount']}"
        )

        print(
            f"Evidence:   "
            f"{result['evidence_count']}"
        )

    print()
    print("=" * 60)
    print(
        "Truth Engine test complete."
    )
    print("=" * 60)