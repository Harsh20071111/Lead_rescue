import hashlib

from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


# ---------------------------------------------------------------------------
# Indian currency formatting
# ---------------------------------------------------------------------------

@register.filter
def inr_compact(value):
    """Format a number into compact Indian notation.
    Examples: 7500000 -> ₹75 L, 15000000 -> ₹1.5 Cr, 50000 -> ₹50,000
    """
    if value is None or value == "":
        return ""
    try:
        num = float(value)
    except (ValueError, TypeError):
        return str(value)

    if num >= 10000000:
        crores = num / 10000000
        if crores == int(crores):
            return f"₹{int(crores)} Cr"
        return f"₹{crores:.1f} Cr"
    elif num >= 100000:
        lakhs = num / 100000
        if lakhs == int(lakhs):
            return f"₹{int(lakhs)} L"
        return f"₹{lakhs:.1f} L"
    elif num >= 1000:
        return f"₹{_indian_group(int(num))}"
    else:
        return f"₹{int(num)}"


@register.filter
def inr_full(value):
    """Format a number into full Indian grouping.
    Examples: 15000000 -> ₹1,50,00,000
    """
    if value is None or value == "":
        return ""
    try:
        num = int(float(value))
    except (ValueError, TypeError):
        return str(value)
    return f"₹{_indian_group(num)}"


def _indian_group(n):
    s = str(n)
    if len(s) <= 3:
        return s
    last3 = s[-3:]
    rest = s[:-3]
    groups = []
    while rest:
        groups.append(rest[-2:])
        rest = rest[:-2]
    groups.reverse()
    return ",".join(groups) + "," + last3


# ---------------------------------------------------------------------------
# Status-color mapping (canonical)
# ---------------------------------------------------------------------------

STATUS_COLORS = {
    "new": "#d97706",
    "contacted": "#b56a30",
    "qualified": "#995f4c",
    "site_visit": "#7c4c3a",
    "negotiation": "#6366f1",
    "converted": "#15803d",
    "lost": "#78716c",
}

SOURCE_COLORS = {
    "website": "#b56a30",
    "referral": "#ff784b",
    "google": "#995f4c",
    "manual": "#ffe2d9",
    "whatsapp": "#25D366",
    "import": "#6366f1",
}


@register.filter
def status_color(value):
    return STATUS_COLORS.get(value, "#78716c")


@register.filter
def source_color(value):
    return SOURCE_COLORS.get(value, "#78716c")


# ---------------------------------------------------------------------------
# Avatar helpers
# ---------------------------------------------------------------------------

AVATAR_PALETTE = [
    "#b56a30", "#995f4c", "#ff784b", "#7c4c3a",
    "#d97706", "#6366f1", "#15803d", "#c026d3",
    "#0891b2", "#be123c",
]


def _pick_avatar_color(seed):
    idx = hashlib.md5(str(seed).encode()).digest()[0] % len(AVATAR_PALETTE)
    return AVATAR_PALETTE[idx]


@register.filter
def avatar_initials(name):
    initials = ""
    for part in name.split()[:2]:
        if part:
            initials += part[0].upper()
    return initials or "?"


@register.simple_tag
def avatar_bg(seed):
    return _pick_avatar_color(seed)
