# Money Autopsy

## AI-Powered Settlement Investigation & Recovery Intelligence

Money Autopsy investigates financial reconciliation exceptions by reconstructing financial lineage, gathering evidence, explaining likely causes, validating AI conclusions, quantifying potential recovery and preserving a replayable audit trail.

---

## Phase 1

Phase 1 builds the synthetic financial universe and deterministic ground-truth foundation.

### Entities

- Merchant
- Order
- Payment
- Refund
- Fee
- Settlement
- Bank Transaction
- Ledger Entry
- Reconciliation Case
- Ground Truth
- Evidence
- Human Decision
- Replay Event

---

## Exception Types

The synthetic dataset contains:

- NORMAL
- DUPLICATE_REFUND
- MISSING_SETTLEMENT
- PARTIAL_SETTLEMENT
- FEE_MISMATCH
- BANK_REFERENCE_MISMATCH
- TIMING_MISMATCH
- ORPHAN_TRANSACTION
- UNRESOLVED

---

## Architecture

```text
Synthetic Financial World
          |
          v
PostgreSQL
          |
          v
Financial Truth Engine
          |
          v
Investigation Engine
          |
          v
AI + Validation
          |
          v
Human Review
          |
          v
Decision Replay