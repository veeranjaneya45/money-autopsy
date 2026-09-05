from backend.database import fetch_one
from backend.truth_engine import investigate_case

case = fetch_one(
    """
    SELECT case_id
    FROM reconciliation_cases
    ORDER BY case_id
    LIMIT 1;
    """
)

print("CASE:")
print(case)

result = investigate_case(case["case_id"])

print("\nFULL TRUTH ENGINE RESULT:")
print(result)