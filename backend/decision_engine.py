from decimal import Decimal, InvalidOperation
from typing import Any, Dict


DECISION_ENGINE_VERSION = "1.1"


def _to_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0.00")


def build_decision(
    investigation: Dict[str, Any],
    validation: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build a deterministic operational decision from the
    authoritative investigation and validator result.

    The Decision Engine does not use an LLM and does not
    execute financial actions.
    """

    # Truth Engine returns the authoritative case fields
    # at the top level. The fallback supports both the
    # current structure and the older nested structure.
    case = investigation.get(
        "case",
        investigation,
    )

    case_id = case.get("case_id")

    status = str(
        case.get("status", "")
    ).upper()

    resolution = str(
        case.get("resolution", "")
    ).upper()

    recovery_amount = _to_decimal(
        case.get(
            "potential_recovery_amount",
            "0.00",
        )
    )

    validation_status = str(
        validation.get(
            "status",
            "UNRESOLVED",
        )
    ).upper()

    # ---------------------------------------------------------
    # VALIDATION FAILURE
    # ---------------------------------------------------------

    if validation_status != "SUPPORTED":

        return {
            "case_id": case_id,
            "decision": "REQUEST_EVIDENCE",
            "potential_recovery_amount": f"{recovery_amount:.2f}",
            "recommended_action": (
                "Obtain additional evidence and resolve "
                "the validation exception before making a "
                "financial decision."
            ),
            "human_approval_required": True,
            "execution_status": "NOT_EXECUTED",
            "decision_reason": (
                "AI output did not pass deterministic validation."
            ),
            "financial_action_allowed": False,
            "decision_engine": {
                "version": DECISION_ENGINE_VERSION,
                "deterministic": True,
                "llm_used": False,
            },
        }

    # ---------------------------------------------------------
    # UNRESOLVED CASE
    # ---------------------------------------------------------

    if status == "UNRESOLVED":

        return {
            "case_id": case_id,
            "decision": "REQUEST_EVIDENCE",
            "potential_recovery_amount": f"{recovery_amount:.2f}",
            "recommended_action": (
                "Request the missing financial evidence "
                "before determining a final resolution."
            ),
            "human_approval_required": True,
            "execution_status": "NOT_EXECUTED",
            "decision_reason": (
                "The Truth Engine could not establish a "
                "single supported financial explanation."
            ),
            "financial_action_allowed": False,
            "decision_engine": {
                "version": DECISION_ENGINE_VERSION,
                "deterministic": True,
                "llm_used": False,
            },
        }

    # ---------------------------------------------------------
    # NORMAL CASE
    # ---------------------------------------------------------

    if status == "NORMAL" or resolution == "NO_ACTION":

        return {
            "case_id": case_id,
            "decision": "NO_ACTION",
            "potential_recovery_amount": "0.00",
            "recommended_action": (
                "No financial exception requires action."
            ),
            "human_approval_required": False,
            "execution_status": "NOT_REQUIRED",
            "decision_reason": (
                "The financial records are consistent."
            ),
            "financial_action_allowed": False,
            "decision_engine": {
                "version": DECISION_ENGINE_VERSION,
                "deterministic": True,
                "llm_used": False,
            },
        }

    # ---------------------------------------------------------
    # FINANCIAL EXCEPTION
    # ---------------------------------------------------------

    if resolution == "REVIEW":

        return {
            "case_id": case_id,
            "decision": "REVIEW_REQUIRED",
            "potential_recovery_amount": f"{recovery_amount:.2f}",
            "recommended_action": (
                "Route the case to an authorized human "
                "operator for review and approval."
            ),
            "human_approval_required": True,
            "execution_status": "NOT_EXECUTED",
            "decision_reason": (
                f"A {status} exception was established by "
                "the deterministic Truth Engine."
            ),
            "financial_action_allowed": False,
            "decision_engine": {
                "version": DECISION_ENGINE_VERSION,
                "deterministic": True,
                "llm_used": False,
            },
        }

    # ---------------------------------------------------------
    # SAFE FALLBACK
    # ---------------------------------------------------------

    return {
        "case_id": case_id,
        "decision": "REQUEST_EVIDENCE",
        "potential_recovery_amount": f"{recovery_amount:.2f}",
        "recommended_action": (
            "Request additional evidence before taking "
            "any financial action."
        ),
        "human_approval_required": True,
        "execution_status": "NOT_EXECUTED",
        "decision_reason": (
            "The case resolution could not be mapped to "
            "a supported operational decision."
        ),
        "financial_action_allowed": False,
        "decision_engine": {
            "version": DECISION_ENGINE_VERSION,
            "deterministic": True,
            "llm_used": False,
        },
    }