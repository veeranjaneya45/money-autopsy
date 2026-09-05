import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Set


VALIDATOR_VERSION = "1.1"


# Financial exception types that the Truth Engine can produce.
KNOWN_EXCEPTION_TYPES = {
    "DUPLICATE_REFUND",
    "MISSING_SETTLEMENT",
    "PARTIAL_SETTLEMENT",
    "FEE_MISMATCH",
    "BANK_REFERENCE_MISMATCH",
    "TIMING_MISMATCH",
    "ORPHAN_TRANSACTION",
    "UNRESOLVED",
    "NORMAL",
}


ALLOWED_CONFIDENCES = {
    "HIGH",
    "MEDIUM",
    "LOW",
    "UNRESOLVED",
}


CONFIDENCE_RANK = {
    "UNRESOLVED": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
}


DANGEROUS_ACTION_PHRASES = [
    "EXECUTE PAYMENT",
    "SEND PAYMENT",
    "TRANSFER MONEY",
    "REFUND CUSTOMER",
    "RECOVER MONEY AUTOMATICALLY",
    "AUTOMATICALLY RECOVER",
    "WRITE OFF",
    "CLOSE THE CASE",
]


# ------------------------------------------------------------
# BASIC HELPERS
# ------------------------------------------------------------

def _to_decimal(value: Any) -> Decimal | None:
    """
    Safely convert a value to Decimal.
    """
    if value is None:
        return None

    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _normalise(value: Any) -> str:
    """
    Normalise text for deterministic comparison.
    """
    if value is None:
        return ""

    return str(value).strip().upper()


# ------------------------------------------------------------
# EVIDENCE
# ------------------------------------------------------------

def _collect_evidence_ids(
    investigation: Dict[str, Any]
) -> Set[str]:
    """
    Collect every legitimate evidence ID supplied by the
    deterministic investigation.
    """

    evidence_ids: Set[str] = set()

    evidence = investigation.get("evidence", [])

    if isinstance(evidence, list):
        for item in evidence:
            if not isinstance(item, dict):
                continue

            record_id = item.get("record_id")

            if record_id:
                evidence_ids.add(str(record_id))

            evidence_id = item.get("evidence_id")

            if evidence_id:
                evidence_ids.add(str(evidence_id))

    proof_chain = investigation.get("proof_chain", [])

    if isinstance(proof_chain, list):
        for step in proof_chain:
            if not isinstance(step, dict):
                continue

            step_evidence = step.get("evidence", [])

            if isinstance(step_evidence, list):
                for item in step_evidence:
                    if item:
                        evidence_ids.add(str(item))

            record_id = step.get("record_id")

            if record_id:
                evidence_ids.add(str(record_id))

    return evidence_ids


def _extract_evidence_ids(
    ai_report: Dict[str, Any]
) -> List[str]:
    """
    Extract evidence IDs referenced by the AI report.
    """

    result: List[str] = []

    evidence = ai_report.get("evidence", [])

    if not isinstance(evidence, list):
        return result

    for item in evidence:

        if not isinstance(item, dict):
            continue

        evidence_id = item.get("evidence_id")

        if evidence_id:
            result.append(str(evidence_id))

    return result


# ------------------------------------------------------------
# FINANCIAL AMOUNT GROUNDING
# ------------------------------------------------------------

def _extract_financial_numbers(
    text: str
) -> List[Decimal]:
    """
    Extract decimal financial-looking numbers from AI-generated
    financial text.

    We intentionally inspect decimal values rather than every
    integer because integers may be case IDs, evidence IDs, etc.
    """

    if not text:
        return []

    pattern = (
        r"(?<![A-Za-z0-9_])"
        r"(?:₹|\$|USD|INR)?\s*"
        r"(\d+\.\d{1,2})"
        r"(?![A-Za-z0-9_])"
    )

    matches = re.findall(pattern, text)

    values: List[Decimal] = []

    for match in matches:
        try:
            values.append(Decimal(match))
        except InvalidOperation:
            continue

    return values


def _allowed_financial_values(
    investigation: Dict[str, Any]
) -> Set[Decimal]:
    """
    Build the set of financial values that are already established
    by the deterministic investigation.

    AI may explain these values, but may not introduce a new
    financial amount.
    """

    allowed: Set[Decimal] = set()

    case = investigation.get("case", {})
    financial_trace = investigation.get(
        "financial_trace",
        {},
    )

    candidate_fields = [
        "expected_amount",
        "observed_amount",
        "discrepancy_amount",
        "potential_recovery_amount",
        "payment_amount",
        "refund_total",
        "fee_total",
        "expected_settlement",
        "observed_settlement",
        "discrepancy",
    ]

    for field in candidate_fields:

        value = case.get(field)

        decimal_value = _to_decimal(value)

        if decimal_value is not None:
            allowed.add(decimal_value)

        value = financial_trace.get(field)

        decimal_value = _to_decimal(value)

        if decimal_value is not None:
            allowed.add(decimal_value)

    return allowed


# ------------------------------------------------------------
# EXCEPTION CONSISTENCY
# ------------------------------------------------------------

def _contains_conflicting_exception(
    ai_report: Dict[str, Any],
    truth_case: Dict[str, Any],
) -> str | None:
    """
    Detect explicit mentions of a different exception type.

    Example:

    Truth Engine:
        FEE_MISMATCH

    AI:
        "This is a missing settlement."

    Result:
        validation failure
    """

    truth_exception = _normalise(
        truth_case.get("exception_type")
    )

    if not truth_exception:
        return None

    combined_text = " ".join(
        [
            str(ai_report.get("executive_summary", "")),
            str(ai_report.get("root_cause", "")),
            str(ai_report.get("financial_impact", "")),
            str(ai_report.get("recommended_action", "")),
            str(ai_report.get("unresolved_reason", "")),
        ]
    ).upper()

    for exception_type in KNOWN_EXCEPTION_TYPES:

        if exception_type == truth_exception:
            continue

        if exception_type in combined_text:
            return (
                "AI report explicitly mentions conflicting "
                f"exception type: {exception_type}"
            )

    return None


# ------------------------------------------------------------
# REQUIRED STRUCTURE
# ------------------------------------------------------------

def _validate_required_fields(
    ai_report: Dict[str, Any]
) -> List[str]:
    """
    Validate required top-level AI fields and their basic types.
    """

    required = {
        "executive_summary",
        "root_cause",
        "financial_impact",
        "evidence",
        "recommended_action",
        "confidence",
        "human_review_required",
        "unresolved_reason",
    }

    missing = sorted(
        required - set(ai_report.keys())
    )

    if missing:
        return [
            "Missing required AI report fields: "
            f"{missing}"
        ]

    failures: List[str] = []

    string_fields = [
        "executive_summary",
        "root_cause",
        "financial_impact",
        "recommended_action",
        "confidence",
        "unresolved_reason",
    ]

    for field in string_fields:

        if not isinstance(ai_report.get(field), str):
            failures.append(
                f"AI report field '{field}' must be a string."
            )

    if not isinstance(
        ai_report.get("evidence"),
        list,
    ):
        failures.append(
            "AI report field 'evidence' must be a list."
        )

    if not isinstance(
        ai_report.get("human_review_required"),
        bool,
    ):
        failures.append(
            "AI report field 'human_review_required' "
            "must be a boolean."
        )

    return failures


# ------------------------------------------------------------
# MAIN VALIDATOR
# ------------------------------------------------------------

def validate_ai_report(
    investigation: Dict[str, Any],
    ai_report: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Deterministically validate the AI Investigator report
    against the authoritative Truth Engine investigation.

    The validator never uses an LLM.

    Validation philosophy:

        Truth Engine
              ↓
        authoritative truth
              ↓
        AI explanation
              ↓
        deterministic validation
              ↓
        SUPPORTED / UNRESOLVED
    """

    checks: List[Dict[str, Any]] = []
    failures: List[str] = []

    # --------------------------------------------------------
    # INPUT SAFETY
    # --------------------------------------------------------

    if not isinstance(investigation, dict):
        return {
            "status": "UNRESOLVED",
            "checks": [],
            "checks_passed": 0,
            "checks_failed": 1,
            "failures": [
                "Investigation must be a dictionary."
            ],
            "validator": {
                "version": VALIDATOR_VERSION,
                "deterministic": True,
                "llm_used": False,
                "truth_source": "truth_engine",
            },
        }

    if not isinstance(ai_report, dict):
        return {
            "status": "UNRESOLVED",
            "checks": [],
            "checks_passed": 0,
            "checks_failed": 1,
            "failures": [
                "AI report must be a dictionary."
            ],
            "validator": {
                "version": VALIDATOR_VERSION,
                "deterministic": True,
                "llm_used": False,
                "truth_source": "truth_engine",
            },
        }

    truth_case = investigation.get(
    "case",
    investigation,
)
    if not isinstance(truth_case, dict):
        truth_case = {}

    truth_status = _normalise(
        truth_case.get("status")
    )

    truth_exception = _normalise(
        truth_case.get("exception_type")
    )

    truth_confidence = _normalise(
        truth_case.get("confidence")
    )

    truth_resolution = _normalise(
        truth_case.get("resolution")
    )

    def add_check(
        name: str,
        passed: bool,
        detail: str,
    ):

        check = {
            "name": name,
            "status": (
                "PASSED"
                if passed
                else "FAILED"
            ),
            "detail": detail,
        }

        checks.append(check)

        if not passed:
            failures.append(detail)

    # --------------------------------------------------------
    # CHECK 1 — REQUIRED FIELDS + TYPES
    # --------------------------------------------------------

    required_failures = _validate_required_fields(
        ai_report
    )

    add_check(
        "required_fields",
        len(required_failures) == 0,
        (
            "All required AI report fields are present "
            "and have valid basic types."
            if not required_failures
            else required_failures[0]
        ),
    )

    if required_failures:
        return {
            "status": "UNRESOLVED",
            "checks": checks,
            "checks_passed": 0,
            "checks_failed": len(required_failures),
            "failures": required_failures,
            "validator": {
                "version": VALIDATOR_VERSION,
                "deterministic": True,
                "llm_used": False,
                "truth_source": "truth_engine",
            },
        }

    # --------------------------------------------------------
    # CHECK 2 — AI CONFIDENCE VALUE
    # --------------------------------------------------------

    ai_confidence = _normalise(
        ai_report.get("confidence")
    )

    confidence_ok = (
        ai_confidence in ALLOWED_CONFIDENCES
    )

    add_check(
        "confidence_value",
        confidence_ok,
        (
            "AI confidence is a valid value."
            if confidence_ok
            else (
                f"Invalid AI confidence: "
                f"{ai_confidence}"
            )
        ),
    )

    # --------------------------------------------------------
    # CHECK 3 — AI CONFIDENCE CANNOT EXCEED TRUTH
    # --------------------------------------------------------

    if truth_status == "UNRESOLVED":

        confidence_ok = (
            ai_confidence == "UNRESOLVED"
        )

        detail = (
            "UNRESOLVED case correctly remains "
            "UNRESOLVED."
            if confidence_ok
            else (
                "AI confidence must be UNRESOLVED "
                "when Truth Engine status is UNRESOLVED."
            )
        )

    else:

        confidence_ok = (
            ai_confidence in CONFIDENCE_RANK
            and truth_confidence in CONFIDENCE_RANK
            and ai_confidence != "UNRESOLVED"
            and CONFIDENCE_RANK[ai_confidence]
            <= CONFIDENCE_RANK[truth_confidence]
        )

        detail = (
            "AI confidence does not exceed "
            "deterministic Truth Engine confidence."
            if confidence_ok
            else (
                f"AI confidence {ai_confidence} is "
                f"invalid relative to Truth Engine "
                f"confidence {truth_confidence}."
            )
        )

    add_check(
        "confidence_bound",
        confidence_ok,
        detail,
    )

    # --------------------------------------------------------
    # CHECK 4 — UNRESOLVED PRESERVATION
    # --------------------------------------------------------

    unresolved_ok = True

    if truth_status == "UNRESOLVED":

        unresolved_ok = (
            ai_confidence == "UNRESOLVED"
            and _normalise(
                ai_report.get("root_cause")
            ) == "UNRESOLVED"
            and bool(
                ai_report.get(
                    "unresolved_reason"
                )
            )
            and ai_report.get(
                "human_review_required"
            ) is True
        )

    add_check(
        "unresolved_preservation",
        unresolved_ok,
        (
            "UNRESOLVED state was preserved and "
            "missing evidence was acknowledged."
            if unresolved_ok
            else (
                "AI failed to preserve the deterministic "
                "UNRESOLVED state."
            )
        ),
    )

    # --------------------------------------------------------
    # CHECK 5 — HUMAN REVIEW
    # --------------------------------------------------------

    human_review = ai_report.get(
        "human_review_required"
    )

    review_required = (
        truth_resolution != "NO_ACTION"
        or truth_status == "UNRESOLVED"
    )

    if review_required:

        human_review_ok = (
            human_review is True
        )

    else:

        human_review_ok = (
            human_review is False
        )

    add_check(
        "human_review",
        human_review_ok,
        (
            "Human review requirement is correctly "
            "preserved."
            if human_review_ok
            else (
                "Human review flag does not match "
                "the deterministic case resolution."
            )
        ),
    )

    # --------------------------------------------------------
    # CHECK 6 — EVIDENCE STRUCTURE
    # --------------------------------------------------------

    ai_evidence = ai_report.get(
        "evidence"
    )

    evidence_structure_ok = True

    if not isinstance(ai_evidence, list):
        evidence_structure_ok = False

    elif len(ai_evidence) == 0:
        evidence_structure_ok = False

    else:

        for item in ai_evidence:

            if not isinstance(item, dict):
                evidence_structure_ok = False
                break

            if not item.get("evidence_id"):
                evidence_structure_ok = False
                break

            if not isinstance(
                item.get("evidence_id"),
                str,
            ):
                evidence_structure_ok = False
                break

            if not item.get("reason"):
                evidence_structure_ok = False
                break

    add_check(
        "evidence_structure",
        evidence_structure_ok,
        (
            "AI evidence contains valid evidence IDs "
            "and explanations."
            if evidence_structure_ok
            else (
                "AI evidence must contain at least one "
                "evidence item with evidence_id and reason."
            )
        ),
    )

    # --------------------------------------------------------
    # CHECK 7 — EVIDENCE IDs
    # --------------------------------------------------------

    valid_evidence_ids = _collect_evidence_ids(
        investigation
    )

    ai_evidence_ids = _extract_evidence_ids(
        ai_report
    )

    invalid_evidence_ids = [
        evidence_id
        for evidence_id in ai_evidence_ids
        if evidence_id not in valid_evidence_ids
    ]

    evidence_ok = (
        len(ai_evidence_ids) > 0
        and len(invalid_evidence_ids) == 0
    )

    add_check(
        "evidence_grounding",
        evidence_ok,
        (
            f"All {len(ai_evidence_ids)} AI evidence "
            "references exist in the supplied investigation."
            if evidence_ok
            else (
                "AI referenced invalid or missing "
                f"evidence IDs: {invalid_evidence_ids}"
            )
        ),
    )

    # --------------------------------------------------------
    # CHECK 8 — EXCEPTION CONSISTENCY
    # --------------------------------------------------------

    conflict = _contains_conflicting_exception(
        ai_report,
        truth_case,
    )

    exception_ok = (
        conflict is None
    )

    add_check(
        "exception_consistency",
        exception_ok,
        (
            "AI explanation does not contradict the "
            "Truth Engine exception type."
            if exception_ok
            else conflict
        ),
    )

    # --------------------------------------------------------
    # CHECK 9 — FINANCIAL AMOUNT GROUNDING
    # --------------------------------------------------------

    allowed_amounts = _allowed_financial_values(
        investigation
    )

    ai_text = " ".join(
        [
            str(
                ai_report.get(
                    "executive_summary",
                    "",
                )
            ),
            str(
                ai_report.get(
                    "root_cause",
                    "",
                )
            ),
            str(
                ai_report.get(
                    "financial_impact",
                    "",
                )
            ),
            str(
                ai_report.get(
                    "recommended_action",
                    "",
                )
            ),
            str(
                ai_report.get(
                    "unresolved_reason",
                    "",
                )
            ),
        ]
    )

    mentioned_amounts = _extract_financial_numbers(
        ai_text
    )

    unsupported_amounts = [
        amount
        for amount in mentioned_amounts
        if amount not in allowed_amounts
    ]

    amounts_ok = (
        len(unsupported_amounts) == 0
    )

    add_check(
        "financial_grounding",
        amounts_ok,
        (
            "All financial amounts mentioned by AI "
            "are grounded in deterministic investigation data."
            if amounts_ok
            else (
                "AI introduced unsupported financial "
                f"amounts: {unsupported_amounts}"
            )
        ),
    )

    # --------------------------------------------------------
    # CHECK 10 — RECOMMENDATION SAFETY
    # --------------------------------------------------------

    recommendation = _normalise(
        ai_report.get(
            "recommended_action"
        )
    )

    dangerous_phrase = next(
        (
            phrase
            for phrase in DANGEROUS_ACTION_PHRASES
            if phrase in recommendation
        ),
        None,
    )

    recommendation_ok = (
        dangerous_phrase is None
    )

    add_check(
        "recommendation_safety",
        recommendation_ok,
        (
            "AI recommendation remains an operational "
            "recommendation requiring human control."
            if recommendation_ok
            else (
                "AI recommendation contains a potentially "
                f"irreversible action: {dangerous_phrase}"
            )
        ),
    )

    # --------------------------------------------------------
    # CHECK 11 — UNRESOLVED ROOT CAUSE CONSISTENCY
    # --------------------------------------------------------

    unresolved_root_ok = True

    if truth_status == "UNRESOLVED":

        unresolved_root_ok = (
            _normalise(
                ai_report.get("root_cause")
            ) == "UNRESOLVED"
        )

    add_check(
        "unresolved_root_cause",
        unresolved_root_ok,
        (
            "UNRESOLVED root cause is correctly preserved."
            if unresolved_root_ok
            else (
                "AI changed the deterministic UNRESOLVED "
                "root cause."
            )
        ),
    )

    # --------------------------------------------------------
    # FINAL STATUS
    # --------------------------------------------------------

    passed_count = sum(
        1
        for check in checks
        if check["status"] == "PASSED"
    )

    failed_count = len(checks) - passed_count

    validation_status = (
        "SUPPORTED"
        if failed_count == 0
        else "UNRESOLVED"
    )

    return {
        "status": validation_status,
        "checks": checks,
        "checks_passed": passed_count,
        "checks_failed": failed_count,
        "failures": failures,
        "validator": {
            "version": VALIDATOR_VERSION,
            "deterministic": True,
            "llm_used": False,
            "truth_source": "truth_engine",
        },
    }