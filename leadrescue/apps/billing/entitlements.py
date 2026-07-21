from typing import Optional
from apps.agencies.models import Agency

PLAN_FEATURES = {
    Agency.PlanTier.FREE: {
        "max_agents": 1,
        "ai_lead_scoring": False,
        "advanced_analytics": False,
        "whatsapp_bot": False,
        "data_import": False,
    },
    Agency.PlanTier.STARTER: {
        "max_agents": 3,
        "ai_lead_scoring": False,
        "advanced_analytics": False,
        "whatsapp_bot": True,
        "data_import": True,
    },
    Agency.PlanTier.GROWTH: {
        "max_agents": None,
        "ai_lead_scoring": True,
        "advanced_analytics": True,
        "whatsapp_bot": True,
        "data_import": True,
    },
}

def has_feature(agency: Agency, feature_name: str) -> bool:
    """Check if an agency has access to a specific feature."""
    plan = agency.plan_tier or Agency.PlanTier.FREE
    features = PLAN_FEATURES.get(plan, PLAN_FEATURES[Agency.PlanTier.FREE])
    return features.get(feature_name, False)

def get_limit(agency: Agency, limit_name: str) -> Optional[int]:
    """Get the numerical limit for a specific entitlement, or None if unlimited."""
    plan = agency.plan_tier or Agency.PlanTier.FREE
    features = PLAN_FEATURES.get(plan, PLAN_FEATURES[Agency.PlanTier.FREE])
    return features.get(limit_name)

def is_within_limit(agency: Agency, limit_name: str, current_count: int) -> bool:
    """Check if a current count is within the agency's limit."""
    limit = get_limit(agency, limit_name)
    if limit is None:
        return True
    return current_count < limit
