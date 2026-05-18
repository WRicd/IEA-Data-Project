def normalize_ev_scenario(category: str) -> str:
    if category == "Projection-STEPS":
        return "STEPS"
    if category == "Projection-APS":
        return "APS"
    return category or "Unknown"


def normalize_ai_scenario(scenario: str) -> str:
    if scenario == "Base":
        return "Base Case"
    return scenario or "Unknown"
