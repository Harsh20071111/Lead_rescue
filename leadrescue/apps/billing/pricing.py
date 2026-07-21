from decimal import Decimal
from apps.agencies.models import Agency

PLAN_PRICING = {
    Agency.PlanTier.FREE: Decimal("0.00"),
    Agency.PlanTier.STARTER: Decimal("2499.00"),
    Agency.PlanTier.GROWTH: Decimal("6499.00"),
}
