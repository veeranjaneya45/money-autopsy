-- ============================================================
-- MONEY AUTOPSY
-- DATABASE SCHEMA
-- ============================================================

-- ============================================================
-- EXTENSIONS
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- ============================================================
-- MERCHANTS
-- ============================================================

CREATE TABLE IF NOT EXISTS merchants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    merchant_id VARCHAR(100) UNIQUE NOT NULL,

    name VARCHAR(255) NOT NULL,

    currency VARCHAR(10) NOT NULL DEFAULT 'INR',

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- ORDERS
-- ============================================================

CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    order_id VARCHAR(100) UNIQUE NOT NULL,

    merchant_id UUID NOT NULL
        REFERENCES merchants(id)
        ON DELETE CASCADE,

    order_amount NUMERIC(18,2) NOT NULL,

    currency VARCHAR(10) NOT NULL DEFAULT 'INR',

    status VARCHAR(50) NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX IF NOT EXISTS idx_orders_merchant_id
    ON orders(merchant_id);

CREATE INDEX IF NOT EXISTS idx_orders_created_at
    ON orders(created_at);


-- ============================================================
-- PAYMENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    payment_id VARCHAR(100) UNIQUE NOT NULL,

    order_id UUID NOT NULL
        REFERENCES orders(id)
        ON DELETE CASCADE,

    merchant_id UUID NOT NULL
        REFERENCES merchants(id)
        ON DELETE CASCADE,

    amount NUMERIC(18,2) NOT NULL,

    currency VARCHAR(10) NOT NULL DEFAULT 'INR',

    status VARCHAR(50) NOT NULL,

    payment_reference VARCHAR(255),

    captured_at TIMESTAMP,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX IF NOT EXISTS idx_payments_order_id
    ON payments(order_id);

CREATE INDEX IF NOT EXISTS idx_payments_merchant_id
    ON payments(merchant_id);

CREATE INDEX IF NOT EXISTS idx_payments_reference
    ON payments(payment_reference);

CREATE INDEX IF NOT EXISTS idx_payments_created_at
    ON payments(created_at);


-- ============================================================
-- REFUNDS
-- ============================================================

CREATE TABLE IF NOT EXISTS refunds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    refund_id VARCHAR(100) UNIQUE NOT NULL,

    payment_id UUID NOT NULL
        REFERENCES payments(id)
        ON DELETE CASCADE,

    order_id UUID NOT NULL
        REFERENCES orders(id)
        ON DELETE CASCADE,

    merchant_id UUID NOT NULL
        REFERENCES merchants(id)
        ON DELETE CASCADE,

    amount NUMERIC(18,2) NOT NULL,

    currency VARCHAR(10) NOT NULL DEFAULT 'INR',

    status VARCHAR(50) NOT NULL,

    refund_reference VARCHAR(255),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX IF NOT EXISTS idx_refunds_payment_id
    ON refunds(payment_id);

CREATE INDEX IF NOT EXISTS idx_refunds_order_id
    ON refunds(order_id);

CREATE INDEX IF NOT EXISTS idx_refunds_merchant_id
    ON refunds(merchant_id);

CREATE INDEX IF NOT EXISTS idx_refunds_reference
    ON refunds(refund_reference);


-- ============================================================
-- FEES
-- ============================================================

CREATE TABLE IF NOT EXISTS fees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    fee_id VARCHAR(100) UNIQUE NOT NULL,

    payment_id UUID NOT NULL
        REFERENCES payments(id)
        ON DELETE CASCADE,

    merchant_id UUID NOT NULL
        REFERENCES merchants(id)
        ON DELETE CASCADE,

    amount NUMERIC(18,2) NOT NULL,

    currency VARCHAR(10) NOT NULL DEFAULT 'INR',

    fee_type VARCHAR(100) NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX IF NOT EXISTS idx_fees_payment_id
    ON fees(payment_id);

CREATE INDEX IF NOT EXISTS idx_fees_merchant_id
    ON fees(merchant_id);


-- ============================================================
-- SETTLEMENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS settlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    settlement_id VARCHAR(100) UNIQUE NOT NULL,

    merchant_id UUID NOT NULL
        REFERENCES merchants(id)
        ON DELETE CASCADE,

    payment_id UUID NOT NULL
        REFERENCES payments(id)
        ON DELETE CASCADE,

    expected_amount NUMERIC(18,2) NOT NULL,

    settled_amount NUMERIC(18,2) NOT NULL,

    currency VARCHAR(10) NOT NULL DEFAULT 'INR',

    status VARCHAR(50) NOT NULL,

    settlement_reference VARCHAR(255),

    settlement_date TIMESTAMP NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX IF NOT EXISTS idx_settlements_merchant_id
    ON settlements(merchant_id);

CREATE INDEX IF NOT EXISTS idx_settlements_payment_id
    ON settlements(payment_id);

CREATE INDEX IF NOT EXISTS idx_settlements_reference
    ON settlements(settlement_reference);

CREATE INDEX IF NOT EXISTS idx_settlements_date
    ON settlements(settlement_date);


-- ============================================================
-- BANK TRANSACTIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS bank_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    bank_transaction_id VARCHAR(100) UNIQUE NOT NULL,

    merchant_id UUID NOT NULL
        REFERENCES merchants(id)
        ON DELETE CASCADE,

    settlement_id UUID
        REFERENCES settlements(id)
        ON DELETE SET NULL,

    amount NUMERIC(18,2) NOT NULL,

    currency VARCHAR(10) NOT NULL DEFAULT 'INR',

    bank_reference VARCHAR(255),

    status VARCHAR(50) NOT NULL,

    transaction_date TIMESTAMP NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX IF NOT EXISTS idx_bank_transactions_merchant_id
    ON bank_transactions(merchant_id);

CREATE INDEX IF NOT EXISTS idx_bank_transactions_settlement_id
    ON bank_transactions(settlement_id);

CREATE INDEX IF NOT EXISTS idx_bank_transactions_reference
    ON bank_transactions(bank_reference);

CREATE INDEX IF NOT EXISTS idx_bank_transactions_date
    ON bank_transactions(transaction_date);


-- ============================================================
-- LEDGER ENTRIES
-- ============================================================

CREATE TABLE IF NOT EXISTS ledger_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    ledger_entry_id VARCHAR(100) UNIQUE NOT NULL,

    merchant_id UUID NOT NULL
        REFERENCES merchants(id)
        ON DELETE CASCADE,

    payment_id UUID
        REFERENCES payments(id)
        ON DELETE SET NULL,

    settlement_id UUID
        REFERENCES settlements(id)
        ON DELETE SET NULL,

    debit NUMERIC(18,2) NOT NULL DEFAULT 0.00,

    credit NUMERIC(18,2) NOT NULL DEFAULT 0.00,

    currency VARCHAR(10) NOT NULL DEFAULT 'INR',

    entry_type VARCHAR(100) NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX IF NOT EXISTS idx_ledger_entries_merchant_id
    ON ledger_entries(merchant_id);

CREATE INDEX IF NOT EXISTS idx_ledger_entries_payment_id
    ON ledger_entries(payment_id);

CREATE INDEX IF NOT EXISTS idx_ledger_entries_settlement_id
    ON ledger_entries(settlement_id);


-- ============================================================
-- RECONCILIATION CASES
-- ============================================================

CREATE TABLE IF NOT EXISTS reconciliation_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    case_id VARCHAR(100) UNIQUE NOT NULL,

    merchant_id UUID NOT NULL
        REFERENCES merchants(id)
        ON DELETE CASCADE,

    payment_id UUID
        REFERENCES payments(id)
        ON DELETE SET NULL,

    settlement_id UUID
        REFERENCES settlements(id)
        ON DELETE SET NULL,

    case_status VARCHAR(50) NOT NULL,

    exception_type VARCHAR(100) NOT NULL,

    expected_amount NUMERIC(18,2) NOT NULL,

    observed_amount NUMERIC(18,2) NOT NULL,

    discrepancy_amount NUMERIC(18,2) NOT NULL,

    potential_recovery_amount NUMERIC(18,2) NOT NULL DEFAULT 0.00,

    priority VARCHAR(50) NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX IF NOT EXISTS idx_reconciliation_cases_merchant_id
    ON reconciliation_cases(merchant_id);

CREATE INDEX IF NOT EXISTS idx_reconciliation_cases_payment_id
    ON reconciliation_cases(payment_id);

CREATE INDEX IF NOT EXISTS idx_reconciliation_cases_settlement_id
    ON reconciliation_cases(settlement_id);

CREATE INDEX IF NOT EXISTS idx_reconciliation_cases_status
    ON reconciliation_cases(case_status);

CREATE INDEX IF NOT EXISTS idx_reconciliation_cases_exception
    ON reconciliation_cases(exception_type);

CREATE INDEX IF NOT EXISTS idx_reconciliation_cases_priority
    ON reconciliation_cases(priority);

CREATE INDEX IF NOT EXISTS idx_reconciliation_cases_created_at
    ON reconciliation_cases(created_at);


-- ============================================================
-- GROUND TRUTH
-- ============================================================
--
-- IMPORTANT:
--
-- This table is ONLY for benchmark evaluation.
--
-- The Truth Engine must NEVER read this table.
--
-- It represents the hidden answer key for the
-- synthetic financial dataset.
-- ============================================================

CREATE TABLE IF NOT EXISTS ground_truth (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    case_id UUID NOT NULL
        REFERENCES reconciliation_cases(id)
        ON DELETE CASCADE,

    true_status VARCHAR(50) NOT NULL,

    true_exception_type VARCHAR(100) NOT NULL,

    true_affected_amount NUMERIC(18,2) NOT NULL,

    true_recoverable_amount NUMERIC(18,2) NOT NULL,

    required_evidence JSONB NOT NULL DEFAULT '[]'::jsonb,

    expected_resolution VARCHAR(100) NOT NULL,

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX IF NOT EXISTS idx_ground_truth_case_id
    ON ground_truth(case_id);


-- ============================================================
-- EVIDENCE
-- ============================================================

CREATE TABLE IF NOT EXISTS evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    evidence_id VARCHAR(100) UNIQUE NOT NULL,

    merchant_id UUID NOT NULL
        REFERENCES merchants(id)
        ON DELETE CASCADE,

    evidence_type VARCHAR(100) NOT NULL,

    source_table VARCHAR(100) NOT NULL,

    source_record_id VARCHAR(255) NOT NULL,

    description TEXT NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX IF NOT EXISTS idx_evidence_merchant_id
    ON evidence(merchant_id);

CREATE INDEX IF NOT EXISTS idx_evidence_type
    ON evidence(evidence_type);

CREATE INDEX IF NOT EXISTS idx_evidence_source_record
    ON evidence(source_record_id);


-- ============================================================
-- INVESTIGATION EVIDENCE
-- ============================================================

CREATE TABLE IF NOT EXISTS investigation_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    case_id UUID NOT NULL
        REFERENCES reconciliation_cases(id)
        ON DELETE CASCADE,

    evidence_id UUID NOT NULL
        REFERENCES evidence(id)
        ON DELETE CASCADE,

    relevance_reason TEXT NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(case_id, evidence_id)
);


CREATE INDEX IF NOT EXISTS idx_investigation_evidence_case_id
    ON investigation_evidence(case_id);

CREATE INDEX IF NOT EXISTS idx_investigation_evidence_evidence_id
    ON investigation_evidence(evidence_id);


-- ============================================================
-- REPLAY EVENTS
-- ============================================================
--
-- These are low-level case lifecycle events generated
-- during synthetic dataset creation.
-- ============================================================

CREATE TABLE IF NOT EXISTS replay_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    case_id UUID NOT NULL
        REFERENCES reconciliation_cases(id)
        ON DELETE CASCADE,

    sequence_number INTEGER NOT NULL,

    event_type VARCHAR(100) NOT NULL,

    event_data JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX IF NOT EXISTS idx_replay_events_case_id
    ON replay_events(case_id);

CREATE INDEX IF NOT EXISTS idx_replay_events_sequence
    ON replay_events(case_id, sequence_number);


-- ============================================================
-- HUMAN DECISIONS
-- ============================================================
--
-- Reserved for the controlled human-review workflow.
--
-- No real financial action is executed automatically.
-- ============================================================

CREATE TABLE IF NOT EXISTS human_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    case_id UUID NOT NULL
        REFERENCES reconciliation_cases(id)
        ON DELETE CASCADE,

    decision VARCHAR(100) NOT NULL,

    reason TEXT,

    reviewer VARCHAR(255),

    evidence_snapshot JSONB NOT NULL DEFAULT '[]'::jsonb,

    model_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX IF NOT EXISTS idx_human_decisions_case_id
    ON human_decisions(case_id);

CREATE INDEX IF NOT EXISTS idx_human_decisions_created_at
    ON human_decisions(created_at);


-- ============================================================
-- INVESTIGATION REPLAYS
-- ============================================================
--
-- PHASE 8
--
-- Stores the complete investigation state:
--
-- Truth Engine
-- Proof Chain
-- AI Report
-- Validation
-- Decision
--
-- Replay reads this snapshot.
--
-- Gemini is NOT called during replay.
-- ============================================================

CREATE TABLE IF NOT EXISTS investigation_replays (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    replay_id VARCHAR(150) UNIQUE NOT NULL,

    case_id VARCHAR(100) NOT NULL,

    truth_snapshot JSONB NOT NULL,

    ai_report JSONB NOT NULL,

    validation_snapshot JSONB NOT NULL,

    decision_snapshot JSONB NOT NULL,

    fingerprint VARCHAR(64) NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX IF NOT EXISTS idx_investigation_replays_case_id
    ON investigation_replays(case_id);

CREATE INDEX IF NOT EXISTS idx_investigation_replays_created_at
    ON investigation_replays(created_at);

CREATE INDEX IF NOT EXISTS idx_investigation_replays_fingerprint
    ON investigation_replays(fingerprint);


-- ============================================================
-- BENCHMARK RESULTS
-- ============================================================
--
-- Stores measured benchmark runs.
-- ============================================================

CREATE TABLE IF NOT EXISTS benchmark_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    benchmark_id VARCHAR(100) UNIQUE NOT NULL,

    total_cases INTEGER NOT NULL,

    exact_classification_correct INTEGER NOT NULL,

    recovery_amount_correct INTEGER NOT NULL,

    resolution_correct INTEGER NOT NULL,

    normal_correct INTEGER NOT NULL,

    exception_correct INTEGER NOT NULL,

    unresolved_correct INTEGER NOT NULL,

    accuracy NUMERIC(8,4) NOT NULL,

    recovery_accuracy NUMERIC(8,4) NOT NULL,

    resolution_accuracy NUMERIC(8,4) NOT NULL,

    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX IF NOT EXISTS idx_benchmark_results_created_at
    ON benchmark_results(created_at);


-- ============================================================
-- SCHEMA COMPLETE
-- ============================================================A