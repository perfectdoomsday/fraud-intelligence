from app.services.risk_engine import risk_category


def decide(score: int) -> tuple[str, list[str]]:
    category = risk_category(score)
    if category == "CRITICAL":
        return "ESCALATE", ["RISK_SCORE_CRITICAL"]
    if category == "HIGH":
        return "FLAG_FOR_REVIEW", ["RISK_SCORE_HIGH"]
    if category == "MEDIUM":
        return "MONITOR", ["RISK_SCORE_MEDIUM"]
    return "ALLOW", []
