import laya
from laya import Router

# Preload checkpoints into memory for instant sub-35ms routing
print("Initializing Router...")
router = Router(preload=True)

state = {
    "from": "user@acme.com",
    "subject": "Duplicate charge on invoice #4411",
    "body": "Hi, we were billed twice for March. Please refund the duplicate today or we will cancel our plan."
}

questions = {
    "department": {
        "type": "choice",
        "instructions": "Which department should handle this request?",
        "criteria": {
            "billing": "invoices, payments, refunds",
            "technical": "bugs, outages, system errors",
            "sales": "pricing, new contracts",
            "other": "everything else"
        }
    },
    "urgency": {
        "type": "score",
        "instructions": "How urgent is this request?",
        "criteria": ["not urgent", "soon", "critical deadline or blocking issue"]
    },
    "churn_risk": {
        "type": "noul",
        "instructions": "Does the user threaten to cancel or leave?"
    },
    "refund_requested": {
        "type": "noul",
        "instructions": "Does the user explicitly request a refund?"
    }
}

# 1. English state -> automatically routed to ModernBERT-large (39.5 ms)
print("\n--- Running English prediction ---")
res_en = router.predict(state, questions)
print("Department :", res_en["answers"]["department"]["choice"])
print("Routing    :", res_en["routing"]["model"])
print("Full res_en answers:", res_en["answers"])
# 2. Hindi state -> automatically routed to mmBERT-base (100+ languages, 32.8 ms)
print("\n--- Running Hindi prediction ---")
res_hi = router.predict({"body": "मुझसे दो बार शुल्क लिया गया, कृपया पैसे वापस करें।"}, questions)
print("Department :", res_hi["answers"]["department"]["choice"])
print("Routing    :", res_hi["routing"]["model"])
print("Full res_hi answers:", res_hi["answers"])

# 3. Explicit override when you already know the checkpoint
print("\n--- Running explicit override prediction ---")
res_td = router.predict(state, questions, model="typed-decisions")
print("Override answers:", res_td["answers"])
