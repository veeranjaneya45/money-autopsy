import os
import random
import json

from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

import psycopg2
from dotenv import load_dotenv
from faker import Faker


# ============================================================
# MONEY AUTOPSY
# SYNTHETIC FINANCIAL DATASET GENERATOR
# ============================================================

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not configured.")


# ============================================================
# DATASET CONFIGURATION
# ============================================================

SEED = 20260904
TARGET_CASES = 300

random.seed(SEED)

fake = Faker("en_IN")
Faker.seed(SEED)


CASE_DISTRIBUTION = [
    ("NORMAL", 150),
    ("DUPLICATE_REFUND", 30),
    ("MISSING_SETTLEMENT", 25),
    ("PARTIAL_SETTLEMENT", 20),
    ("FEE_MISMATCH", 20),
    ("BANK_REFERENCE_MISMATCH", 15),
    ("TIMING_MISMATCH", 15),
    ("ORPHAN_TRANSACTION", 10),
    ("UNRESOLVED", 15),
]


# ============================================================
# DATABASE
# ============================================================

def connect():
    return psycopg2.connect(DATABASE_URL)


# ============================================================
# MONEY
# ============================================================

def money(value):
    return Decimal(value).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


# ============================================================
# RESET GENERATED DATA
# ============================================================

def reset_generated_data(cursor):
    """
    Remove previously generated data while preserving
    the database schema.

    This makes the generator safe to run again.
    """

    cursor.execute(
        """
        TRUNCATE TABLE
            replay_events,
            human_decisions,
            investigation_evidence,
            evidence,
            ground_truth,
            reconciliation_cases,
            ledger_entries,
            bank_transactions,
            settlements,
            fees,
            refunds,
            payments,
            orders,
            merchants
        CASCADE;
        """
    )


# ============================================================
# MERCHANT
# ============================================================

def create_merchant(cursor):
    merchant_id = "MERCHANT_001"

    cursor.execute(
        """
        INSERT INTO merchants (
            merchant_id,
            name,
            currency
        )
        VALUES (
            %s,
            %s,
            'INR'
        )
        RETURNING id;
        """,
        (
            merchant_id,
            "Money Autopsy Demo Merchant",
        ),
    )

    return cursor.fetchone()[0]


# ============================================================
# CREATE ONE CASE
# ============================================================

def create_case(
    cursor,
    merchant_uuid,
    case_number,
    exception_type,
):
    # --------------------------------------------------------
    # CASE TIMESTAMP
    # --------------------------------------------------------

    created_at = datetime.now(
        timezone.utc
    ) - timedelta(
        days=random.randint(1, 90),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )

    # --------------------------------------------------------
    # IDENTIFIERS
    # --------------------------------------------------------

    order_id = f"ORD_{case_number:06d}"
    payment_id = f"PAY_{case_number:06d}"
    settlement_id = f"SET_{case_number:06d}"
    case_id = f"CASE_{case_number:06d}"

    # --------------------------------------------------------
    # BASE PAYMENT AMOUNT
    # --------------------------------------------------------

    base_amount = money(
        Decimal(
            random.randint(
                1000,
                100000,
            )
        )
        + Decimal(
            random.randint(
                0,
                99,
            )
        )
        / Decimal("100")
    )

    # --------------------------------------------------------
    # DEFAULT FINANCIAL VALUES
    # --------------------------------------------------------

    refund_amount = Decimal("0.00")

    fee_amount = money(
        base_amount
        * Decimal(
            random.choice(
                [
                    "0.015",
                    "0.02",
                    "0.025",
                ]
            )
        )
    )

    payment_status = "CAPTURED"
    order_status = "PAID"

    # ========================================================
    # ORDER
    # ========================================================

    cursor.execute(
        """
        INSERT INTO orders (
            order_id,
            merchant_id,
            order_amount,
            currency,
            status,
            created_at
        )
        VALUES (
            %s,
            %s,
            %s,
            'INR',
            %s,
            %s
        )
        RETURNING id;
        """,
        (
            order_id,
            merchant_uuid,
            base_amount,
            order_status,
            created_at,
        ),
    )

    order_uuid = cursor.fetchone()[0]

    # ========================================================
    # PAYMENT
    # ========================================================

    payment_reference = (
        f"PAYREF_{case_number:08d}"
    )

    captured_at = (
        created_at
        + timedelta(minutes=2)
    )

    cursor.execute(
        """
        INSERT INTO payments (
            payment_id,
            order_id,
            merchant_id,
            amount,
            currency,
            status,
            payment_reference,
            captured_at,
            created_at
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            'INR',
            %s,
            %s,
            %s,
            %s
        )
        RETURNING id;
        """,
        (
            payment_id,
            order_uuid,
            merchant_uuid,
            base_amount,
            payment_status,
            payment_reference,
            captured_at,
            created_at,
        ),
    )

    payment_uuid = cursor.fetchone()[0]

    # ========================================================
    # REFUNDS
    # ========================================================

    if exception_type == "DUPLICATE_REFUND":

        # One refund amount is created twice.
        #
        # The second refund is the duplicate exposure.
        refund_amount = money(
            base_amount
            * Decimal("0.90")
        )

    elif exception_type in {
        "NORMAL",
        "FEE_MISMATCH",
        "BANK_REFERENCE_MISMATCH",
        "TIMING_MISMATCH",
        "ORPHAN_TRANSACTION",
        "UNRESOLVED",
    }:

        # Some ordinary cases contain a legitimate refund.
        # This prevents the Truth Engine from simply assuming
        # every refund is an exception.
        if random.random() < 0.15:

            refund_amount = money(
                base_amount
                * Decimal("0.10")
            )

    # --------------------------------------------------------
    # FIRST REFUND
    # --------------------------------------------------------

    if refund_amount > Decimal("0.00"):

        cursor.execute(
            """
            INSERT INTO refunds (
                refund_id,
                payment_id,
                order_id,
                merchant_id,
                amount,
                currency,
                status,
                refund_reference,
                created_at
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                'INR',
                'COMPLETED',
                %s,
                %s
            );
            """,
            (
                f"REF_{case_number:06d}_A",
                payment_uuid,
                order_uuid,
                merchant_uuid,
                refund_amount,
                f"RFREF_{case_number:08d}_A",
                created_at
                + timedelta(hours=1),
            ),
        )

        # ----------------------------------------------------
        # DUPLICATE REFUND
        # ----------------------------------------------------

        if exception_type == "DUPLICATE_REFUND":

            cursor.execute(
                """
                INSERT INTO refunds (
                    refund_id,
                    payment_id,
                    order_id,
                    merchant_id,
                    amount,
                    currency,
                    status,
                    refund_reference,
                    created_at
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    'INR',
                    'COMPLETED',
                    %s,
                    %s
                );
                """,
                (
                    f"REF_{case_number:06d}_B",
                    payment_uuid,
                    order_uuid,
                    merchant_uuid,
                    refund_amount,
                    f"RFREF_{case_number:08d}_B",
                    created_at
                    + timedelta(
                        hours=1,
                        minutes=2,
                    ),
                ),
            )

    # ========================================================
    # FEE
    # ========================================================

    if exception_type == "FEE_MISMATCH":

        fee_amount = money(
            base_amount
            * Decimal("0.05")
        )

    cursor.execute(
        """
        INSERT INTO fees (
            fee_id,
            payment_id,
            merchant_id,
            amount,
            currency,
            fee_type,
            created_at
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            'INR',
            %s,
            %s
        );
        """,
        (
            f"FEE_{case_number:06d}",
            payment_uuid,
            merchant_uuid,
            fee_amount,
            "PROCESSING_FEE",
            created_at
            + timedelta(hours=1),
        ),
    )

    # ========================================================
    # EXPECTED SETTLEMENT
    # ========================================================

    # A settlement represents money actually owed to
    # the merchant.
    #
    # It must never become negative, even when a
    # DUPLICATE_REFUND creates excess refund exposure.

    expected_amount = money(
        max(
            Decimal("0.00"),
            base_amount
            - refund_amount
            - fee_amount,
        )
    )

    observed_amount = expected_amount

    settlement_status = "SETTLED"

    # ========================================================
    # EXCEPTION-SPECIFIC SETTLEMENT
    # ========================================================

    if exception_type == "MISSING_SETTLEMENT":

        observed_amount = Decimal("0.00")

        settlement_status = "MISSING"

    elif exception_type == "PARTIAL_SETTLEMENT":

        observed_amount = money(
            expected_amount
            * Decimal("0.70")
        )

        settlement_status = "PARTIAL"

    elif exception_type == "BANK_REFERENCE_MISMATCH":

        observed_amount = expected_amount

    elif exception_type == "TIMING_MISMATCH":

        observed_amount = expected_amount

    elif exception_type == "ORPHAN_TRANSACTION":

        observed_amount = expected_amount

    elif exception_type == "UNRESOLVED":

        # Financial amounts are valid.
        #
        # The ambiguity is deliberately introduced through
        # missing bank settlement-reference evidence below.
        observed_amount = expected_amount

    # ========================================================
    # SETTLEMENT DATE
    # ========================================================

    settlement_date = (
        created_at
        + timedelta(days=1)
    )

    if exception_type == "TIMING_MISMATCH":

        settlement_date = (
            created_at
            + timedelta(days=5)
        )

    # ========================================================
    # SETTLEMENT REFERENCE
    # ========================================================

    settlement_reference = (
        f"SETREF_{case_number:08d}"
    )

    cursor.execute(
        """
        INSERT INTO settlements (
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
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            'INR',
            %s,
            %s,
            %s,
            %s
        )
        RETURNING id;
        """,
        (
            settlement_id,
            merchant_uuid,
            payment_uuid,
            expected_amount,
            observed_amount,
            settlement_status,
            settlement_reference,
            settlement_date,
            settlement_date,
        ),
    )

    settlement_uuid = cursor.fetchone()[0]

    # ========================================================
    # BANK TRANSACTION
    # ========================================================

    # Normal bank reference.
    bank_reference = (
        f"BANKREF_{case_number:08d}"
    )

    # Deliberately incorrect reference.
    if exception_type == "BANK_REFERENCE_MISMATCH":

        bank_reference = (
            f"WRONGREF_{case_number:08d}"
        )

    # --------------------------------------------------------
    # IMPORTANT: UNRESOLVED
    # --------------------------------------------------------
    #
    # The bank transaction exists, but its settlement
    # reference is missing.
    #
    # This gives the Truth Engine a genuine observable
    # evidence gap.
    #
    # It must classify this as UNRESOLVED rather than
    # inventing a root cause.
    # --------------------------------------------------------

    if exception_type == "UNRESOLVED":

        bank_reference = None

    bank_transaction_id = (
        f"BANK_{case_number:06d}"
    )

    bank_amount = observed_amount

    cursor.execute(
        """
        INSERT INTO bank_transactions (
            bank_transaction_id,
            merchant_id,
            settlement_id,
            amount,
            currency,
            bank_reference,
            status,
            transaction_date,
            created_at
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            'INR',
            %s,
            'POSTED',
            %s,
            %s
        );
        """,
        (
            bank_transaction_id,
            merchant_uuid,
            settlement_uuid,
            bank_amount,
            bank_reference,
            settlement_date
            + timedelta(hours=2),
            settlement_date
            + timedelta(hours=2),
        ),
    )

    # ========================================================
    # ORPHAN TRANSACTION
    # ========================================================

    if exception_type == "ORPHAN_TRANSACTION":

        # This transaction deliberately has:
        #
        #   settlement_id = NULL
        #
        # and a case-specific reference:
        #
        #   ORPHANREF_00000281
        #
        # This allows the Truth Engine to identify the
        # orphan belonging to this exact case.

        cursor.execute(
            """
            INSERT INTO bank_transactions (
                bank_transaction_id,
                merchant_id,
                settlement_id,
                amount,
                currency,
                bank_reference,
                status,
                transaction_date,
                created_at
            )
            VALUES (
                %s,
                %s,
                NULL,
                %s,
                'INR',
                %s,
                'POSTED',
                %s,
                %s
            );
            """,
            (
                f"BANK_ORPHAN_{case_number:06d}",
                merchant_uuid,
                money(
                    base_amount
                    * Decimal("0.50")
                ),
                f"ORPHANREF_{case_number:08d}",
                settlement_date
                + timedelta(hours=4),
                settlement_date
                + timedelta(hours=4),
            ),
        )

    # ========================================================
    # LEDGER
    # ========================================================

    cursor.execute(
        """
        INSERT INTO ledger_entries (
            ledger_entry_id,
            merchant_id,
            payment_id,
            settlement_id,
            debit,
            credit,
            currency,
            entry_type,
            created_at
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            'INR',
            %s,
            %s
        );
        """,
        (
            f"LEDGER_{case_number:06d}",
            merchant_uuid,
            payment_uuid,
            settlement_uuid,
            Decimal("0.00"),
            expected_amount,
            "SETTLEMENT",
            settlement_date,
        ),
    )

    # ========================================================
    # RECONCILIATION CASE
    # ========================================================

    discrepancy_amount = money(
        abs(
            expected_amount
            - observed_amount
        )
    )

    potential_recovery_amount = (
        Decimal("0.00")
    )

    # --------------------------------------------------------
    # RECOVERY LOGIC
    # --------------------------------------------------------

    if exception_type == "DUPLICATE_REFUND":

        # The duplicate refund itself is the recoverable
        # exposure.

        potential_recovery_amount = (
            refund_amount
        )

    elif exception_type == "MISSING_SETTLEMENT":

        potential_recovery_amount = (
            expected_amount
        )

    elif exception_type == "PARTIAL_SETTLEMENT":

        potential_recovery_amount = (
            discrepancy_amount
        )

    elif exception_type == "FEE_MISMATCH":

        potential_recovery_amount = (
            fee_amount
        )

    elif exception_type == "BANK_REFERENCE_MISMATCH":

        potential_recovery_amount = (
            observed_amount
        )

    elif exception_type == "ORPHAN_TRANSACTION":

        potential_recovery_amount = money(
            base_amount
            * Decimal("0.50")
        )

    elif exception_type == "UNRESOLVED":

        potential_recovery_amount = (
            Decimal("0.00")
        )

    # ========================================================
    # CASE STATUS / PRIORITY
    # ========================================================

    if exception_type == "NORMAL":

        case_status = "RESOLVED"
        priority = "LOW"

    elif exception_type == "UNRESOLVED":

        case_status = "NEW"
        priority = "HIGH"

    elif exception_type in {
        "DUPLICATE_REFUND",
        "MISSING_SETTLEMENT",
        "ORPHAN_TRANSACTION",
    }:

        case_status = "EXCEPTION"
        priority = "HIGH"

    else:

        case_status = "EXCEPTION"
        priority = "MEDIUM"

    # ========================================================
    # INSERT RECONCILIATION CASE
    # ========================================================

    cursor.execute(
        """
        INSERT INTO reconciliation_cases (
            case_id,
            merchant_id,
            payment_id,
            settlement_id,
            case_status,
            exception_type,
            expected_amount,
            observed_amount,
            discrepancy_amount,
            potential_recovery_amount,
            priority,
            created_at,
            updated_at
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
        RETURNING id;
        """,
        (
            case_id,
            merchant_uuid,
            payment_uuid,
            settlement_uuid,
            case_status,
            exception_type,
            expected_amount,
            observed_amount,
            discrepancy_amount,
            potential_recovery_amount,
            priority,
            created_at,
            created_at,
        ),
    )

    case_uuid = cursor.fetchone()[0]

    # ========================================================
    # GROUND TRUTH
    # ========================================================
    #
    # IMPORTANT:
    #
    # ground_truth is the hidden answer key.
    #
    # The Truth Engine must NEVER read it.
    #
    # It exists only for benchmark evaluation.
    # ========================================================

    if exception_type == "NORMAL":

        true_status = "RESOLVED"
        true_recoverable = Decimal("0.00")
        expected_resolution = "NO_ACTION"

    elif exception_type == "UNRESOLVED":

        true_status = "UNRESOLVED"
        true_recoverable = Decimal("0.00")
        expected_resolution = "REQUEST_EVIDENCE"

    else:

        true_status = "EXCEPTION"
        true_recoverable = (
            potential_recovery_amount
        )
        expected_resolution = "REVIEW"

    # --------------------------------------------------------
    # REQUIRED EVIDENCE
    # --------------------------------------------------------

    required_evidence = [
        f"PAY_{case_number:06d}",
        f"SET_{case_number:06d}",
    ]

    if exception_type == "DUPLICATE_REFUND":

        required_evidence.extend(
            [
                f"REF_{case_number:06d}_A",
                f"REF_{case_number:06d}_B",
            ]
        )

    if exception_type == "FEE_MISMATCH":

        required_evidence.append(
            f"FEE_{case_number:06d}"
        )

    if exception_type in {
        "BANK_REFERENCE_MISMATCH",
        "ORPHAN_TRANSACTION",
        "UNRESOLVED",
    }:

        required_evidence.append(
            f"BANK_{case_number:06d}"
        )

    cursor.execute(
        """
        INSERT INTO ground_truth (
            case_id,
            true_status,
            true_exception_type,
            true_affected_amount,
            true_recoverable_amount,
            required_evidence,
            expected_resolution,
            notes
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s::jsonb,
            %s,
            %s
        );
        """,
        (
            case_uuid,
            true_status,
            exception_type,
            discrepancy_amount,
            true_recoverable,
            json.dumps(
                required_evidence
            ),
            expected_resolution,
            (
                f"Hidden ground truth "
                f"for {exception_type}."
            ),
        ),
    )

    # ========================================================
    # EVIDENCE RECORDS
    # ========================================================

    evidence_rows = [
        (
            f"PAY_{case_number:06d}",
            "PAYMENT",
            "payments",
            payment_id,
            (
                f"Payment {payment_id} "
                f"for INR "
                f"{base_amount:.2f}."
            ),
        ),
        (
            f"SET_{case_number:06d}",
            "SETTLEMENT",
            "settlements",
            settlement_id,
            (
                f"Settlement "
                f"{settlement_id} "
                f"for INR "
                f"{observed_amount:.2f}."
            ),
        ),
        (
            f"FEE_{case_number:06d}",
            "FEE",
            "fees",
            f"FEE_{case_number:06d}",
            (
                f"Processing fee "
                f"for case "
                f"{case_number}."
            ),
        ),
        (
            f"BANK_{case_number:06d}",
            "BANK_TRANSACTION",
            "bank_transactions",
            bank_transaction_id,
            (
                f"Bank transaction "
                f"{bank_transaction_id}."
            ),
        ),
    ]

    # --------------------------------------------------------
    # REFUND EVIDENCE
    # --------------------------------------------------------

    if refund_amount > Decimal("0.00"):

        evidence_rows.append(
            (
                f"REF_{case_number:06d}_A",
                "REFUND",
                "refunds",
                f"REF_{case_number:06d}_A",
                (
                    f"Refund A for "
                    f"INR "
                    f"{refund_amount:.2f}."
                ),
            )
        )

        if exception_type == "DUPLICATE_REFUND":

            evidence_rows.append(
                (
                    f"REF_{case_number:06d}_B",
                    "REFUND",
                    "refunds",
                    f"REF_{case_number:06d}_B",
                    (
                        f"Duplicate refund B "
                        f"for INR "
                        f"{refund_amount:.2f}."
                    ),
                )
            )

    # --------------------------------------------------------
    # INSERT EVIDENCE
    # --------------------------------------------------------

    for (
        evidence_id,
        evidence_type,
        source_table,
        source_record_id,
        description,
    ) in evidence_rows:

        cursor.execute(
            """
            INSERT INTO evidence (
                evidence_id,
                merchant_id,
                evidence_type,
                source_table,
                source_record_id,
                description,
                created_at
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
            RETURNING id;
            """,
            (
                evidence_id,
                merchant_uuid,
                evidence_type,
                source_table,
                source_record_id,
                description,
                created_at,
            ),
        )

        evidence_uuid = cursor.fetchone()[0]

        relevance_reason = (
            "Relevant financial evidence."
        )

        if (
            exception_type
            == "DUPLICATE_REFUND"
            and evidence_type == "REFUND"
        ):

            relevance_reason = (
                "Refund evidence used to "
                "establish duplicate refund."
            )

        elif (
            exception_type
            == "BANK_REFERENCE_MISMATCH"
            and evidence_type
            == "BANK_TRANSACTION"
        ):

            relevance_reason = (
                "Bank evidence used to "
                "compare settlement reference."
            )

        elif (
            exception_type
            == "ORPHAN_TRANSACTION"
            and evidence_type
            == "BANK_TRANSACTION"
        ):

            relevance_reason = (
                "Bank evidence shows a "
                "transaction without settlement linkage."
            )

        elif (
            exception_type
            == "UNRESOLVED"
            and evidence_type
            == "BANK_TRANSACTION"
        ):

            relevance_reason = (
                "Bank transaction exists, "
                "but settlement reference evidence "
                "is missing."
            )

        cursor.execute(
            """
            INSERT INTO investigation_evidence (
                case_id,
                evidence_id,
                relevance_reason,
                created_at
            )
            VALUES (
                %s,
                %s,
                %s,
                %s
            )
            ON CONFLICT (
                case_id,
                evidence_id
            )
            DO NOTHING;
            """,
            (
                case_uuid,
                evidence_uuid,
                relevance_reason,
                created_at,
            ),
        )

    # ========================================================
    # REPLAY EVENTS
    # ========================================================

    replay_events = [
        (
            1,
            "CASE_CREATED",
            {
                "case_id": case_id,
                "exception_type": exception_type,
            },
        ),
        (
            2,
            "RECONCILIATION_COMPLETED",
            {
                "expected_amount": str(
                    expected_amount
                ),
                "observed_amount": str(
                    observed_amount
                ),
                "discrepancy_amount": str(
                    discrepancy_amount
                ),
            },
        ),
    ]

    if exception_type != "NORMAL":

        replay_events.append(
            (
                3,
                "EXCEPTION_DETECTED",
                {
                    "exception_type": (
                        exception_type
                    ),
                    "priority": priority,
                },
            )
        )

    for (
        sequence_number,
        event_type,
        event_data,
    ) in replay_events:

        cursor.execute(
            """
            INSERT INTO replay_events (
                case_id,
                sequence_number,
                event_type,
                event_data,
                created_at
            )
            VALUES (
                %s,
                %s,
                %s,
                %s::jsonb,
                %s
            );
            """,
            (
                case_uuid,
                sequence_number,
                event_type,
                json.dumps(event_data),
                created_at,
            ),
        )


# ============================================================
# GENERATE DATASET
# ============================================================

def generate():

    print(
        "Creating synthetic Money Autopsy dataset..."
    )

    print(
        f"Seed: {SEED}"
    )

    print(
        f"Target cases: {TARGET_CASES}"
    )

    print()

    connection = connect()

    try:

        with connection.cursor() as cursor:

            # ------------------------------------------------
            # RESET
            # ------------------------------------------------

            reset_generated_data(
                cursor
            )

            # ------------------------------------------------
            # MERCHANT
            # ------------------------------------------------

            merchant_uuid = create_merchant(
                cursor
            )

            # ------------------------------------------------
            # CASES
            # ------------------------------------------------

            case_number = 1

            for (
                exception_type,
                count,
            ) in CASE_DISTRIBUTION:

                print(
                    f"Generating "
                    f"{count:3d} "
                    f"{exception_type}"
                )

                for _ in range(count):

                    create_case(
                        cursor,
                        merchant_uuid,
                        case_number,
                        exception_type,
                    )

                    case_number += 1

            # ------------------------------------------------
            # COMMIT
            # ------------------------------------------------

            connection.commit()

            print()

            print("=" * 60)
            print(
                "DATASET GENERATION COMPLETE"
            )
            print("=" * 60)

            print(
                f"Cases generated: "
                f"{case_number - 1}"
            )

            print(
                f"Seed: {SEED}"
            )

            print()

            print(
                "Distribution:"
            )

            for (
                exception_type,
                count,
            ) in CASE_DISTRIBUTION:

                print(
                    f"  "
                    f"{exception_type:25s} "
                    f"{count:3d}"
                )

            print()

            print(
                "Database transaction "
                "committed successfully."
            )

    except Exception as exc:

        connection.rollback()

        print()
        print("=" * 60)
        print("DATASET GENERATION FAILED")
        print("=" * 60)
        print(
            f"Error: {exc}"
        )

        raise

    finally:

        connection.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    generate()