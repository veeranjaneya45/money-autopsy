from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from benchmark import load_cases, run_deterministic_benchmark

from backend.database import (
    fetch_all,
    fetch_one,
)

from backend.models import (
    HealthResponse,
    DatasetStats,
    HumanReviewRequest,
)

from backend.truth_engine import (
    investigate_case,
)

from backend.proof_chain import (
    build_investigation,
)

from backend.ai_investigator import (
    investigate_with_ai,
)

from backend.validator import (
    validate_ai_report,
)

from backend.decision_engine import (
    build_decision,
)

from backend.replay_engine import (
    save_replay,
    replay_investigation,
)

from backend.human_review import (
    record_human_decision,
    get_human_decisions,
)

from benchmark import (
    load_cases,
    run_deterministic_benchmark,
)


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="Money Autopsy",
    description=(
        "Financial investigation and settlement reconciliation engine."
    ),
    version="0.5.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROOT
# ============================================================

@app.get(
    "/",
    tags=["System"],
)
def root():
    return {
        "name": "Money Autopsy",
        "version": "0.5.0",
        "status": "running",
        "architecture": (
            "Truth Engine → Money DNA → Proof Chain → "
            "Evidence → AI Investigator → Validator → "
            "Human Review → Replay → Benchmark"
        ),
    }


# ============================================================
# HEALTH
# ============================================================

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
)
def health():

    try:
        result = fetch_one(
            "SELECT 1 AS value;"
        )

        if result and result["value"] == 1:
            return {
                "status": "healthy",
                "database": "connected",
            }

        raise HTTPException(
            status_code=503,
            detail="Database health check failed.",
        )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Database unavailable: "
                f"{str(exc)}"
            ),
        )


# ============================================================
# DATASET STATISTICS
# ============================================================

@app.get(
    "/api/stats",
    response_model=DatasetStats,
    tags=["Dataset"],
)
def dataset_stats():

    queries = {
        "merchants":
            "SELECT COUNT(*) AS count FROM merchants;",

        "orders":
            "SELECT COUNT(*) AS count FROM orders;",

        "payments":
            "SELECT COUNT(*) AS count FROM payments;",

        "refunds":
            "SELECT COUNT(*) AS count FROM refunds;",

        "fees":
            "SELECT COUNT(*) AS count FROM fees;",

        "settlements":
            "SELECT COUNT(*) AS count FROM settlements;",

        "bank_transactions":
            "SELECT COUNT(*) AS count FROM bank_transactions;",

        "ledger_entries":
            "SELECT COUNT(*) AS count FROM ledger_entries;",

        "cases":
            "SELECT COUNT(*) AS count FROM reconciliation_cases;",

        "ground_truth_cases":
            "SELECT COUNT(*) AS count FROM ground_truth;",
    }

    stats = {}

    for name, query in queries.items():

        result = fetch_one(query)

        stats[name] = result["count"]

    return stats


# ============================================================
# CASE LIST
# ============================================================

@app.get(
    "/api/cases",
    tags=["Cases"],
)
def get_cases(
    limit: int = 50,
):

    if limit < 1 or limit > 500:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 500",
        )

    query = """
        SELECT
            case_id,
            case_status,
            exception_type,
            expected_amount,
            observed_amount,
            discrepancy_amount,
            potential_recovery_amount,
            priority,
            created_at
        FROM reconciliation_cases
        ORDER BY created_at ASC
        LIMIT %s;
    """

    return fetch_all(
        query,
        (limit,),
    )


# ============================================================
# CASE DETAIL
# ============================================================

@app.get(
    "/api/cases/{case_id}",
    tags=["Cases"],
)
def get_case(
    case_id: str,
):

    query = """
        SELECT
            rc.case_id,
            rc.case_status,
            rc.exception_type,
            rc.expected_amount,
            rc.observed_amount,
            rc.discrepancy_amount,
            rc.potential_recovery_amount,
            rc.priority,
            rc.created_at,

            p.payment_id,
            p.amount AS payment_amount,
            p.status AS payment_status,

            o.order_id,
            o.amount AS order_amount,
            o.status AS order_status,

            s.settlement_id,
            s.amount AS settlement_amount,
            s.status AS settlement_status

        FROM reconciliation_cases rc

        LEFT JOIN payments p
            ON rc.payment_id = p.id

        LEFT JOIN orders o
            ON p.order_id = o.id

        LEFT JOIN settlements s
            ON rc.settlement_id = s.id

        WHERE rc.case_id = %s;
    """

    result = fetch_one(
        query,
        (case_id,),
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Case not found: {case_id}",
        )

    return result


# ============================================================
# DETERMINISTIC INVESTIGATION
# ============================================================

@app.get(
    "/api/cases/{case_id}/investigation",
    tags=["Investigation"],
)
def get_investigation(
    case_id: str,
):

    try:

        truth_result = investigate_case(
            case_id
        )

        investigation = build_investigation(
            truth_result
        )

        return investigation

    except ValueError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Investigation failed: "
                f"{str(exc)}"
            ),
        )


# ============================================================
# FULL AI INVESTIGATION REPORT
# ============================================================

@app.get(
    "/api/cases/{case_id}/report",
    tags=["Investigation"],
)
def get_report(
    case_id: str,
):

    try:

        # ----------------------------------------------------
        # 1. DETERMINISTIC TRUTH
        # ----------------------------------------------------

        truth_result = investigate_case(
            case_id
        )

        # ----------------------------------------------------
        # 2. MONEY DNA + PROOF CHAIN
        # ----------------------------------------------------

        investigation = build_investigation(
            truth_result
        )

        # ----------------------------------------------------
        # 3. AI INVESTIGATION
        # ----------------------------------------------------

        ai_result = investigate_with_ai(
            investigation
        )

        ai_report = ai_result.get(
            "report",
            {},
        )

        # ----------------------------------------------------
        # 4. VALIDATE AI OUTPUT
        # ----------------------------------------------------

        validation = validate_ai_report(
            investigation,
            ai_report,
        )

        # ----------------------------------------------------
        # 5. DECISION ENGINE
        # ----------------------------------------------------

        decision = build_decision(
            investigation,
            validation,
        )

        # ----------------------------------------------------
        # 6. SAVE REPLAY
        # ----------------------------------------------------

        replay = save_replay(
            investigation=investigation,
            ai_report=ai_report,
            validation=validation,
            decision=decision,
        )

        return {
            "case_id": case_id,

            "investigation": investigation,

            "ai": ai_result,

            "ai_report": ai_report,

            "validation": validation,

            "decision": decision,

            "replay": replay,
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Report generation failed: "
                f"{str(exc)}"
            ),
        )


# ============================================================
# HUMAN REVIEW
# ============================================================

@app.post(
    "/api/cases/{case_id}/review",
    tags=["Human Review"],
)
def submit_human_review(
    case_id: str,
    request: HumanReviewRequest,
):

    try:

        # ----------------------------------------------------
        # ALWAYS REBUILD DETERMINISTIC INVESTIGATION
        # ----------------------------------------------------

        truth_result = investigate_case(
            case_id
        )

        investigation = build_investigation(
            truth_result
        )

        # ----------------------------------------------------
        # RECORD HUMAN DECISION
        # ----------------------------------------------------

        audit = record_human_decision(
            case_id=case_id,
            decision=request.decision,
            reason=request.reason,
            reviewer=request.reviewer,
            investigation=investigation,
        )

        return {
            "status": "recorded",
            "case_id": case_id,
            "investigation": investigation,
            "audit": audit,
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Human review failed: "
                f"{str(exc)}"
            ),
        )


# ============================================================
# HUMAN REVIEW HISTORY
# ============================================================

@app.get(
    "/api/cases/{case_id}/reviews",
    tags=["Human Review"],
)
def get_reviews(
    case_id: str,
):

    try:

        return {
            "case_id": case_id,
            "reviews": get_human_decisions(
                case_id
            ),
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not retrieve review history: "
                f"{str(exc)}"
            ),
        )


# ============================================================
# DECISION REPLAY
# ============================================================

@app.get(
    "/api/replays/{replay_id}",
    tags=["Decision Replay"],
)
def get_replay(
    replay_id: str,
):

    try:

        replay = replay_investigation(
            replay_id
        )

        if not replay:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Replay not found: {replay_id}"
                ),
            )

        return replay

    except HTTPException:
        raise

    except ValueError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Replay failed: "
                f"{str(exc)}"
            ),
        )


# ============================================================
# BENCHMARK
# ============================================================

@app.get(
    "/api/benchmark",
    tags=["Benchmark"],
)
def get_benchmark():

    """
    Run the deterministic 300-case benchmark.

    This endpoint intentionally does NOT run the AI benchmark.

    Financial truth is evaluated only through:

        Truth Engine
        Proof Chain
        Validator
        Decision Engine

    The AI benchmark is deliberately excluded because:

        1. Financial truth must remain deterministic.
        2. Gemini free-tier quota should not be consumed
           by normal dashboard usage.
        3. The benchmark should measure the reliability of
           the financial control pipeline independently.
    """

    try:

        # ----------------------------------------------------
        # LOAD BENCHMARK CASES
        # ----------------------------------------------------

        cases = load_cases()

        if not cases:

            raise HTTPException(
                status_code=404,
                detail="No benchmark cases found.",
            )

        # ----------------------------------------------------
        # RUN DETERMINISTIC BENCHMARK
        # ----------------------------------------------------

        result = run_deterministic_benchmark(
            cases
        )

        total = result["total"]

        # ----------------------------------------------------
        # SAFE ACCURACY CALCULATOR
        # ----------------------------------------------------

        def percentage(correct):

            if not total:
                return 0

            return (
                correct / total
            ) * 100

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return {

            "benchmark_version": "4.0",

            "pipeline": "deterministic",

            "total_cases": total,

            # ----------------------------------------------
            # CLASSIFICATION
            # ----------------------------------------------

            "classification": {
                "correct": result[
                    "classification_correct"
                ],

                "total": total,

                "accuracy": percentage(
                    result[
                        "classification_correct"
                    ]
                ),
            },

            # ----------------------------------------------
            # STATUS
            # ----------------------------------------------

            "status": {
                "correct": result[
                    "status_correct"
                ],

                "total": total,

                "accuracy": percentage(
                    result[
                        "status_correct"
                    ]
                ),
            },

            # ----------------------------------------------
            # RECOVERY
            # ----------------------------------------------

            "recovery": {
                "correct": result[
                    "recovery_correct"
                ],

                "total": total,

                "accuracy": percentage(
                    result[
                        "recovery_correct"
                    ]
                ),
            },

            # ----------------------------------------------
            # RESOLUTION
            # ----------------------------------------------

            "resolution": {
                "correct": result[
                    "resolution_correct"
                ],

                "total": total,

                "accuracy": percentage(
                    result[
                        "resolution_correct"
                    ]
                ),
            },

            # ----------------------------------------------
            # UNRESOLVED PRESERVATION
            # ----------------------------------------------

            "unresolved_preservation": {
                "correct": result[
                    "unresolved_correct"
                ],

                "total": total,

                "accuracy": percentage(
                    result[
                        "unresolved_correct"
                    ]
                ),
            },

            # ----------------------------------------------
            # PROOF CHAIN
            # ----------------------------------------------

            "proof_chain": {
                "correct": result[
                    "proof_correct"
                ],

                "total": total,

                "integrity": percentage(
                    result[
                        "proof_correct"
                    ]
                ),
            },

            # ----------------------------------------------
            # PERFORMANCE
            # ----------------------------------------------

            "performance": {
                "elapsed_seconds": result[
                    "elapsed"
                ],

                "throughput_cases_per_second": result[
                    "throughput"
                ],
            },

            # ----------------------------------------------
            # FAILED CASES
            # ----------------------------------------------

            "failed_cases": result[
                "failed_cases"
            ],

            "failed_count": len(
                result[
                    "failed_cases"
                ]
            ),

            # ----------------------------------------------
            # AI BENCHMARK
            # ----------------------------------------------

            "ai_benchmark": {

                "executed": False,

                "reason": (
                    "AI benchmark intentionally excluded "
                    "from this endpoint. Deterministic "
                    "financial truth is benchmarked "
                    "independently."
                ),
            },

            # ----------------------------------------------
            # CORE SYSTEM PRINCIPLE
            # ----------------------------------------------

            "system_principle": (
                "AI explains financial evidence; "
                "deterministic systems establish "
                "financial truth."
            ),
        }

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Benchmark execution failed: "
                f"{str(exc)}"
            ),
        )