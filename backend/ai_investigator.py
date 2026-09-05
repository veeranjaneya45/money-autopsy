import json
import os
import re
import time
from typing import Any, Dict

from dotenv import load_dotenv
from google import genai


load_dotenv()


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.1-flash-lite",
)

# Number of retries for temporary server failures.
# 429 quota exhaustion is NOT retried repeatedly.
GEMINI_MAX_RETRIES = int(
    os.getenv(
        "GEMINI_MAX_RETRIES",
        "2",
    )
)

# Delay between temporary retries.
GEMINI_RETRY_DELAY = float(
    os.getenv(
        "GEMINI_RETRY_DELAY",
        "3",
    )
)


if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not configured. "
        "Add it to your .env file."
    )


client = genai.Client(
    api_key=GEMINI_API_KEY
)


AI_INVESTIGATOR_VERSION = "1.1"


SYSTEM_INSTRUCTIONS = """
You are Money Autopsy's AI Financial Investigator.

Your role is ONLY to explain and investigate
deterministic financial findings.

The Truth Engine has already established
the financial truth.

The Proof Chain contains the evidence.

You MUST NOT replace or override them.

STRICT RULES:

1. Never invent financial facts.

2. Never invent transaction IDs,
   amounts, dates, references, or evidence.

3. Never independently calculate financial amounts.

4. Never change the Truth Engine status.

5. Never change the Truth Engine exception type.

6. Never change the deterministic recovery amount.

7. Never claim an exception is proven unless
   the supplied evidence supports it.

8. If the case is UNRESOLVED,
   keep it UNRESOLVED.

9. If evidence is insufficient,
   explicitly state that more evidence is required.

10. Every important claim must reference
    evidence supplied in the investigation.

11. Use only supplied financial values.

12. Do not provide legal, tax, accounting,
    or investment advice.

13. Do not recommend irreversible financial actions.

14. Human review is required for consequential
    financial decisions.

15. The Truth Engine is the authoritative
    source of financial truth.

16. The AI is an explanation layer,
    not the financial authority.

Return JSON only.
"""


def _safe_json(value: Any) -> str:

    return json.dumps(
        value,
        default=str,
        ensure_ascii=False,
        indent=2,
    )


def _build_prompt(
    investigation: Dict[str, Any]
) -> str:

    return f"""
Analyze this Money Autopsy investigation.

The deterministic Truth Engine and Proof Chain
are authoritative.

Do NOT alter their conclusions.

INVESTIGATION:

{_safe_json(investigation)}


Return JSON with exactly these fields:

{{
  "executive_summary": "Short explanation of what happened.",

  "root_cause": "Supported cause or UNRESOLVED.",

  "financial_impact": "Explain the financial impact using only supplied facts.",

  "evidence": [
    {{
      "evidence_id": "Existing evidence ID",
      "reason": "Why this evidence supports the finding."
    }}
  ],

  "recommended_action": "Safe operational next step.",

  "confidence": "HIGH, MEDIUM, LOW, or UNRESOLVED",

  "human_review_required": true,

  "unresolved_reason": "Empty string if resolved; otherwise explain missing evidence."
}}


Additional requirements:

- Evidence IDs must already exist in the supplied data.
- Never create an evidence ID.
- Never invent an amount.
- Never invent a transaction.
- Never invent a reference.
- Never modify the recovery amount.
- Never modify the case status.
- Never modify the exception type.
- If status is UNRESOLVED:
    root_cause must be "UNRESOLVED"
    confidence must be "UNRESOLVED"
    human_review_required must be true
- If evidence is insufficient, explain what is missing.
"""


def _extract_json(
    text: str
) -> Dict[str, Any]:

    text = text.strip()

    if text.startswith("```"):

        lines = text.splitlines()

        if (
            lines
            and lines[0].startswith("```")
        ):
            lines = lines[1:]

        if (
            lines
            and lines[-1].strip() == "```"
        ):
            lines = lines[:-1]

        text = "\n".join(
            lines
        ).strip()

    try:

        return json.loads(text)

    except json.JSONDecodeError as exc:

        start = text.find("{")
        end = text.rfind("}")

        if (
            start != -1
            and end != -1
            and end > start
        ):

            try:

                return json.loads(
                    text[
                        start:end + 1
                    ]
                )

            except json.JSONDecodeError:
                pass

        raise RuntimeError(
            f"Gemini returned invalid JSON: {exc}"
        ) from exc


# ============================================================
# GEMINI ERROR CLASSIFICATION
# ============================================================

def _classify_gemini_error(
    exc: Exception,
) -> str:

    message = str(exc).upper()

    if (
        "429" in message
        or "RESOURCE_EXHAUSTED" in message
        or "QUOTA" in message
        or "RATE LIMIT" in message
    ):
        return "QUOTA_EXHAUSTED"

    if (
        "503" in message
        or "UNAVAILABLE" in message
        or "SERVICE UNAVAILABLE" in message
    ):
        return "SERVICE_UNAVAILABLE"

    if (
        "500" in message
        or "INTERNAL" in message
    ):
        return "SERVER_ERROR"

    if (
        "504" in message
        or "TIMEOUT" in message
        or "DEADLINE" in message
    ):
        return "TIMEOUT"

    return "UNKNOWN"


def _extract_retry_seconds(
    exc: Exception,
) -> float | None:

    message = str(exc)

    patterns = [
        r"retry in ([0-9]+(?:\.[0-9]+)?)s",
        r"retryDelay.*?([0-9]+(?:\.[0-9]+)?)s",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            message,
            flags=re.IGNORECASE,
        )

        if match:

            try:

                return float(
                    match.group(1)
                )

            except ValueError:
                pass

    return None


# ============================================================
# GEMINI REQUEST
# ============================================================

def _generate_content_with_retry(
    prompt: str,
):

    attempts = 0

    while True:

        try:

            return client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    SYSTEM_INSTRUCTIONS,
                    prompt,
                ],
            )

        except Exception as exc:

            error_type = (
                _classify_gemini_error(
                    exc
                )
            )

            # ------------------------------------------------
            # QUOTA
            # ------------------------------------------------
            #
            # Do NOT repeatedly retry a quota error.
            # This protects the free-tier quota.
            # ------------------------------------------------

            if error_type == "QUOTA_EXHAUSTED":

                retry_seconds = (
                    _extract_retry_seconds(
                        exc
                    )
                )

                if retry_seconds is not None:

                    raise RuntimeError(
                        "Gemini API quota exhausted "
                        f"for model '{GEMINI_MODEL}'. "
                        f"Provider suggested retrying "
                        f"in approximately "
                        f"{retry_seconds:.0f} seconds. "
                        "No automatic retry was attempted "
                        "to avoid wasting quota."
                    ) from exc

                raise RuntimeError(
                    "Gemini API quota exhausted "
                    f"for model '{GEMINI_MODEL}'. "
                    "No automatic retry was attempted."
                ) from exc

            # ------------------------------------------------
            # TEMPORARY SERVER FAILURE
            # ------------------------------------------------

            if error_type in {
                "SERVICE_UNAVAILABLE",
                "SERVER_ERROR",
                "TIMEOUT",
            }:

                if attempts >= GEMINI_MAX_RETRIES:

                    raise RuntimeError(
                        "Gemini Investigator failed after "
                        f"{attempts + 1} attempts. "
                        f"Error type: {error_type}. "
                        f"Model: {GEMINI_MODEL}."
                    ) from exc

                attempts += 1

                time.sleep(
                    GEMINI_RETRY_DELAY
                    * attempts
                )

                continue

            # ------------------------------------------------
            # UNKNOWN ERROR
            # ------------------------------------------------

            raise RuntimeError(
                "Gemini Investigator request failed. "
                f"Error type: {error_type}. "
                f"Model: {GEMINI_MODEL}. "
                f"Details: {exc}"
            ) from exc


# ============================================================
# MAIN AI INVESTIGATOR
# ============================================================

def investigate_with_ai(
    investigation: Dict[str, Any]
) -> Dict[str, Any]:

    prompt = _build_prompt(
        investigation
    )

    response = (
        _generate_content_with_retry(
            prompt
        )
    )

    output_text = response.text

    if not output_text:

        raise RuntimeError(
            "Gemini Investigator returned "
            "an empty response."
        )

    report = _extract_json(
        output_text
    )

    required_fields = {
        "executive_summary",
        "root_cause",
        "financial_impact",
        "evidence",
        "recommended_action",
        "confidence",
        "human_review_required",
        "unresolved_reason",
    }

    missing = (
        required_fields
        - set(report.keys())
    )

    if missing:

        raise RuntimeError(
            "Gemini Investigator response "
            "is missing fields: "
            f"{sorted(missing)}"
        )

    return {

        "report":
            report,

        "ai_investigator": {

            "version":
                AI_INVESTIGATOR_VERSION,

            "provider":
                "Google Gemini",

            "model":
                GEMINI_MODEL,

            "grounded_in": [
                "truth_engine",
                "proof_chain",
                "evidence",
            ],

            "financial_truth_source":
                "truth_engine",

            "llm_used":
                True,
        },
    }