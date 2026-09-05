import hashlib
import json
import uuid
from typing import Any, Dict

from psycopg2.extras import Json

from backend.database import execute, fetch_one


REPLAY_ENGINE_VERSION = "1.1"


def _json_dumps(value: Any) -> str:
    """
    Convert investigation data into stable JSON.

    default=str allows Decimal, UUID, datetime,
    and other database values to be serialized safely.
    """
    return json.dumps(
        value,
        default=str,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _fingerprint(
    investigation: Dict[str, Any],
    ai_report: Dict[str, Any],
    validation: Dict[str, Any],
    decision: Dict[str, Any],
) -> str:
    """
    Create a deterministic SHA-256 fingerprint
    of the complete investigation state.
    """

    payload = {
        "investigation": investigation,
        "ai_report": ai_report,
        "validation": validation,
        "decision": decision,
    }

    serialized = _json_dumps(payload)

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


def _replay_id(case_id: str) -> str:
    """
    Generate a human-readable replay identifier.
    """

    return (
        f"REPLAY_{case_id}_"
        f"{uuid.uuid4().hex[:12].upper()}"
    )


def save_replay(
    investigation: Dict[str, Any],
    ai_report: Dict[str, Any],
    validation: Dict[str, Any],
    decision: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Persist the complete investigation state.

    Replay stores snapshots of:
        Truth / Proof
        AI report
        Validation
        Decision

    The LLM is NOT called during replay.
    """

    case_data = investigation.get("case", {})

    case_id = case_data.get("case_id")

    if not case_id:
        raise ValueError(
            "Cannot save replay: case_id is missing."
        )

    replay_id = _replay_id(case_id)

    fingerprint = _fingerprint(
        investigation=investigation,
        ai_report=ai_report,
        validation=validation,
        decision=decision,
    )

    query = """
        INSERT INTO investigation_replays (
            replay_id,
            case_id,
            truth_snapshot,
            ai_report,
            validation_snapshot,
            decision_snapshot,
            fingerprint
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        );
    """

    execute(
        query,
        (
            replay_id,
            case_id,
            Json(
                investigation,
                dumps=_json_dumps,
            ),
            Json(
                ai_report,
                dumps=_json_dumps,
            ),
            Json(
                validation,
                dumps=_json_dumps,
            ),
            Json(
                decision,
                dumps=_json_dumps,
            ),
            fingerprint,
        ),
    )

    # Verify that PostgreSQL actually contains
    # the replay we just inserted.
    saved = fetch_one(
        """
        SELECT
            replay_id,
            case_id,
            fingerprint,
            created_at
        FROM investigation_replays
        WHERE replay_id = %s;
        """,
        (replay_id,),
    )

    if not saved:
        raise RuntimeError(
            "Replay insert completed but the replay "
            "could not be verified in PostgreSQL."
        )

    return {
        "replay_id": saved["replay_id"],
        "case_id": saved["case_id"],
        "fingerprint": saved["fingerprint"],
        "created_at": saved["created_at"],
        "replay_engine": {
            "version": REPLAY_ENGINE_VERSION,
            "llm_used": False,
            "persistent_snapshot": True,
        },
    }


def replay_investigation(
    replay_id: str,
) -> Dict[str, Any]:
    """
    Reconstruct an investigation entirely from
    the persisted database snapshot.

    IMPORTANT:
    Gemini is NOT called here.
    """

    row = fetch_one(
        """
        SELECT
            replay_id,
            case_id,
            truth_snapshot,
            ai_report,
            validation_snapshot,
            decision_snapshot,
            fingerprint,
            created_at
        FROM investigation_replays
        WHERE replay_id = %s;
        """,
        (replay_id,),
    )

    if not row:
        raise ValueError(
            f"Replay not found: {replay_id}"
        )

    investigation = row["truth_snapshot"]
    ai_report = row["ai_report"]
    validation = row["validation_snapshot"]
    decision = row["decision_snapshot"]

    recalculated_fingerprint = _fingerprint(
        investigation=investigation,
        ai_report=ai_report,
        validation=validation,
        decision=decision,
    )

    fingerprint_match = (
        recalculated_fingerprint
        == row["fingerprint"]
    )

    return {
        "replay_id": row["replay_id"],
        "case_id": row["case_id"],
        "created_at": row["created_at"],

        "investigation": investigation,

        "ai_report": ai_report,

        "validation": validation,

        "decision": decision,

        "fingerprint": row["fingerprint"],

        "recalculated_fingerprint":
            recalculated_fingerprint,

        "fingerprint_match":
            fingerprint_match,

        "replay_engine": {
            "version": REPLAY_ENGINE_VERSION,
            "deterministic": True,
            "llm_used": False,
            "source": "postgresql_snapshot",
        },
    }