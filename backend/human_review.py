from typing import Any, Dict, List

from psycopg2.extras import Json

from backend.database import (
    get_connection,
    fetch_all,
    fetch_one,
)


HUMAN_REVIEW_VERSION = "1.0"

ALLOWED_DECISIONS = {
    "APPROVED",
    "REJECTED",
    "REQUEST_EVIDENCE",
}


def _extract_evidence_ids(
    investigation: Dict[str, Any],
) -> List[str]:

    evidence = investigation.get(
        "evidence",
        [],
    )

    evidence_ids = []

    for item in evidence:
        evidence_id = item.get("record_id")

        if evidence_id is None:
            continue

        evidence_id = str(evidence_id)

        if evidence_id not in evidence_ids:
            evidence_ids.append(evidence_id)

    return evidence_ids


def _extract_model_metadata(
    investigation: Dict[str, Any],
) -> Dict[str, Any]:

    return {
        "truth_engine": investigation.get(
            "truth_engine",
            {},
        ),
        "proof_chain": investigation.get(
            "proof_chain_metadata",
            {},
        ),
        "ai_used_for_review": False,
    }


def _extract_rule_metadata(
    investigation: Dict[str, Any],
) -> Dict[str, Any]:

    case = investigation.get(
        "case",
        {},
    )

    return {
        "truth_status": case.get(
            "status"
        ),
        "exception_type": case.get(
            "exception_type"
        ),
        "confidence": case.get(
            "confidence"
        ),
        "resolution": case.get(
            "resolution"
        ),
        "potential_recovery_amount": case.get(
            "potential_recovery_amount"
        ),
        "human_review_version": HUMAN_REVIEW_VERSION,
        "financial_action_executed": False,
    }


def record_human_decision(
    case_id: str,
    decision: str,
    reason: str,
    reviewer: str,
    investigation: Dict[str, Any],
) -> Dict[str, Any]:

    decision = decision.strip().upper()
    reason = reason.strip()
    reviewer = reviewer.strip()

    if decision not in ALLOWED_DECISIONS:
        raise ValueError(
            "Invalid decision. Allowed values: "
            "APPROVED, REJECTED, REQUEST_EVIDENCE."
        )

    if not reviewer:
        raise ValueError(
            "Reviewer is required."
        )

    if not reason:
        raise ValueError(
            "Decision reason is required."
        )

    investigation_case = investigation.get(
        "case",
        {},
    )

    investigation_case_id = investigation_case.get(
        "case_id"
    )

    if investigation_case_id != case_id:
        raise ValueError(
            "Investigation case_id does not match "
            "the requested case."
        )

    current_status = investigation_case.get(
        "status"
    )

    # An unresolved case cannot be approved
    # or rejected as a proven financial finding.
    if (
        current_status == "UNRESOLVED"
        and decision in {
            "APPROVED",
            "REJECTED",
        }
    ):
        raise ValueError(
            "UNRESOLVED cases require additional "
            "evidence. Use REQUEST_EVIDENCE."
        )

    # Confirm the case exists and retrieve
    # its internal UUID.
    case_row = fetch_one(
        """
        SELECT
            id,
            case_id
        FROM reconciliation_cases
        WHERE case_id = %s;
        """,
        (case_id,),
    )

    if not case_row:
        raise ValueError(
            f"Case not found: {case_id}"
        )

    evidence_ids = _extract_evidence_ids(
        investigation
    )

    model_metadata = _extract_model_metadata(
        investigation
    )

    rule_metadata = _extract_rule_metadata(
        investigation
    )

    connection = get_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO human_decisions (
                    case_id,
                    decision,
                    reason,
                    reviewer,
                    evidence_ids,
                    model_metadata,
                    rule_metadata
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                RETURNING
                    id,
                    decision,
                    reason,
                    reviewer,
                    created_at,
                    evidence_ids,
                    model_metadata,
                    rule_metadata;
                """,
                (
                    case_row["id"],
                    decision,
                    reason,
                    reviewer,
                    Json(evidence_ids),
                    Json(model_metadata),
                    Json(rule_metadata),
                ),
            )

            saved = cursor.fetchone()

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    return {
        "audit_id": str(saved[0]),
        "case_id": case_id,
        "decision": saved[1],
        "reason": saved[2],
        "reviewer": saved[3],
        "created_at": saved[4],
        "evidence_ids": saved[5],
        "model_metadata": saved[6],
        "rule_metadata": saved[7],
        "financial_action": {
            "executed": False,
            "status": "NOT_EXECUTED",
        },
        "human_review": {
            "version": HUMAN_REVIEW_VERSION,
            "deterministic": True,
            "llm_used": False,
        },
    }


def get_human_decisions(
    case_id: str,
) -> List[Dict[str, Any]]:

    rows = fetch_all(
        """
        SELECT
            hd.id,
            rc.case_id,
            hd.decision,
            hd.reason,
            hd.reviewer,
            hd.created_at,
            hd.evidence_ids,
            hd.model_metadata,
            hd.rule_metadata
        FROM human_decisions hd
        JOIN reconciliation_cases rc
            ON rc.id = hd.case_id
        WHERE rc.case_id = %s
        ORDER BY hd.created_at DESC;
        """,
        (case_id,),
    )

    results = []

    for row in rows:
        results.append(
            {
                "audit_id": str(row["id"]),
                "case_id": row["case_id"],
                "decision": row["decision"],
                "reason": row["reason"],
                "reviewer": row["reviewer"],
                "created_at": row["created_at"],
                "evidence_ids": row[
                    "evidence_ids"
                ],
                "model_metadata": row[
                    "model_metadata"
                ],
                "rule_metadata": row[
                    "rule_metadata"
                ],
            }
        )

    return results