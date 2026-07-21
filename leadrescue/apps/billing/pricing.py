from decimal import Decimal
from apps.agencies.models import Agency

PLAN_PRICING = {
    Agency.PlanTier.STARTER: Decimal("2499.00"),
    Agency.PlanTier.GROWTH: Decimal("6499.00"),
}
