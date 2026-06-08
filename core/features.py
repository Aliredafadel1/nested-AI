"""
Feature engineering — pure functions, no DB access.
All inputs are plain dicts or primitives extracted from ORM models.
Call these from schemas (computed fields) or services (fraud/roommate signals).
"""
from __future__ import annotations

# ── Amenity weights ────────────────────────────────────────────────────────────
# Premium amenities score higher; basics score 1.0
_AMENITY_WEIGHTS: dict[str, float] = {
    "generator":        1.0,
    "wifi":             1.0,
    "ac":               1.0,
    "furnished":        1.0,
    "water_tank":       1.0,
    "washing_machine":  0.8,
    "elevator":         0.8,
    "parking":          0.8,
    "balcony":          0.6,
    "terrace":          0.6,
    "concierge":        0.8,
    "security":         0.8,
    "gym":              1.5,
    "pool":             2.0,
    "sea_view":         1.2,
    "city_view":        0.8,
    "rooftop":          1.0,
    "solar_water_heater": 0.8,
    "smart_lock":       0.5,
    "pet_friendly":     0.6,
    "bills_included":   1.5,
    "water_included":   0.8,
    "garden":           0.8,
}

# ── Listing features ───────────────────────────────────────────────────────────

def price_per_sqm(price: int, area_sqm: int | None) -> float | None:
    """USD per m². None when area is unknown."""
    if not area_sqm or area_sqm <= 0:
        return None
    return round(price / area_sqm, 2)


def amenity_count(amenities: dict) -> int:
    """Number of amenity flags that are truthy."""
    return sum(1 for v in amenities.values() if v)


def amenity_score(amenities: dict) -> float:
    """Weighted amenity score. Premium amenities (pool, gym) count more."""
    return round(
        sum(_AMENITY_WEIGHTS.get(k, 0.5) for k, v in amenities.items() if v),
        2,
    )


def bedroom_type(bedrooms: int, area_sqm: int | None) -> str:
    """Human label: studio / 1br / 2br / 3br+"""
    if bedrooms == 1:
        return "studio" if (area_sqm or 99) <= 45 else "1br"
    if bedrooms == 2:
        return "2br"
    return "3br+"


def has_essentials(amenities: dict) -> bool:
    """Listing has the Lebanon essentials: generator + wifi."""
    return bool(amenities.get("generator")) and bool(amenities.get("wifi"))


def is_premium(amenities: dict) -> bool:
    """Pool, gym, concierge, or 24h security."""
    return any(amenities.get(k) for k in ("pool", "gym", "concierge", "security"))


def detect_language(text: str) -> str:
    """
    Rough language detection from character sets.
    BGE-M3 handles all three natively — this is for display/analytics only.
    """
    if not text:
        return "unknown"
    arabic = sum(1 for c in text if "؀" <= c <= "ۿ")
    french_markers = sum(text.lower().count(w) for w in ("le ", "la ", "les ", "un ", "une ", "du ", "de ", "et ", "est "))
    if arabic > len(text) * 0.15:
        return "arabic" if french_markers < 3 else "mixed"
    if french_markers >= 3:
        return "french"
    return "english"


# ── Neighbourhood composite scores ────────────────────────────────────────────

def livability_score(electricity: float | None, internet: int | None,
                     safety: int | None, transport: int | None) -> float:
    """
    0–1 composite: electricity reliability 25%, internet 25%, safety 25%, transport 25%.
    Missing values treated as midpoint (0.5).
    """
    elec   = (electricity or 12) / 24
    inet   = (internet   or 3)  / 5
    safe   = (safety     or 3)  / 5
    trans  = (transport  or 3)  / 5
    return round(0.25 * elec + 0.25 * inet + 0.25 * safe + 0.25 * trans, 3)


def student_score(student_vibe: int | None, transport: int | None,
                  safety: int | None, internet: int | None) -> float:
    """
    0–1 composite weighted for student priorities:
    vibe 35%, transport 30%, safety 20%, internet 15%.
    """
    vibe  = (student_vibe or 3) / 5
    trans = (transport    or 3) / 5
    safe  = (safety       or 3) / 5
    inet  = (internet     or 3) / 5
    return round(0.35 * vibe + 0.30 * trans + 0.20 * safe + 0.15 * inet, 3)


def electricity_reliability(electricity_hours: float | None) -> float:
    """Fraction of day with EDL power. 0–1."""
    return round((electricity_hours or 12) / 24, 3)


def generator_cost_ratio(generator_cost: int | None, rent: int) -> float | None:
    """Generator cost as fraction of rent. High ratio = significant hidden cost."""
    if rent <= 0:
        return None
    return round((generator_cost or 0) / rent, 3)


# ── Total monthly cost ─────────────────────────────────────────────────────────

WATER_FIXED    = 15   # USD/month
INTERNET_FIXED = 30   # USD/month

def true_monthly_cost(
    rent: int,
    generator_cost: int | None,
    transport_score: int | None,
    bills_included: bool = False,
) -> int:
    """
    Estimated total monthly cost including Lebanon-specific overhead.
    If bills_included, generator and water are already in rent.
    """
    gen_cost   = 0 if bills_included else (generator_cost or 40)
    water_cost = 0 if bills_included else WATER_FIXED
    inet_cost  = INTERNET_FIXED
    trans_cost = (transport_score or 3) * 10   # score 1–5 → $10–$50
    return rent + gen_cost + water_cost + inet_cost + trans_cost


def rent_to_total_ratio(rent: int, total: int) -> float:
    """Fraction of total monthly cost that is base rent."""
    return round(rent / total, 3) if total > 0 else 1.0


# ── Fraud signals ─────────────────────────────────────────────────────────────

# Words associated with fraudulent urgency in all three languages
_URGENCY_WORDS = [
    "urgent", "urgently", "immediately", "asap", "hurry", "limited",
    "عاجل", "فوري", "الآن", "سريع",
    "immédiatement", "urgent", "vite",
]

_EXTERNAL_CONTACT_PATTERNS = [
    "@gmail", "@hotmail", "@yahoo", "whatsapp", "western union",
    "wire transfer", "wired", "deposit abroad",
]


def urgency_word_count(title: str, description: str | None) -> int:
    """Count of urgency words in listing text — fraud signal."""
    text = f"{title} {description or ''}".lower()
    return sum(1 for w in _URGENCY_WORDS if w in text)


def external_contact_flag(title: str, description: str | None) -> bool:
    """True if listing tries to move contact off-platform — strong fraud signal."""
    text = f"{title} {description or ''}".lower()
    return any(p in text for p in _EXTERNAL_CONTACT_PATTERNS)


def amenity_vs_price_anomaly(amenities: dict, price: int) -> float:
    """
    High amenity score relative to very low price is a fraud signal.
    Returns 0–1: higher = more anomalous.
    Score > 0.6 at price < $300 indicates suspicious value proposition.
    """
    if price <= 0:
        return 1.0
    a_score = amenity_score(amenities)
    # Normalise: typical max amenity_score ~12, typical min price ~300
    # Anomaly = amenity density per dollar (scaled)
    density = a_score / price * 100
    # Sigmoid-like clamp: density > 4 is highly anomalous
    return round(min(density / 4.0, 1.0), 3)


def price_to_median_ratio(price: int, median: float) -> float | None:
    """Price relative to neighbourhood median. < 0.5 is suspicious."""
    if not median or median <= 0:
        return None
    return round(price / median, 3)


# ── Roommate compatibility pre-signals ────────────────────────────────────────

_SLEEP_COMPAT: dict[tuple[str, str], float] = {
    ("night_owl",  "night_owl"):  1.0,
    ("early_bird", "early_bird"): 1.0,
    ("flexible",   "flexible"):   0.85,
    ("flexible",   "night_owl"):  0.6,
    ("flexible",   "early_bird"): 0.6,
    ("night_owl",  "early_bird"): 0.05,
    ("night_owl",  "flexible"):   0.6,
    ("early_bird", "flexible"):   0.6,
    ("early_bird", "night_owl"):  0.05,
}

_CLEANLINESS_ORDINAL = {"low": 1, "medium": 2, "high": 3}
_GUESTS_ORDINAL      = {"never": 1, "rarely": 2, "sometimes": 3, "often": 4}


def sleep_compatibility(s1: str, s2: str) -> float:
    """0–1 heuristic sleep compatibility before embeddings are available."""
    return _SLEEP_COMPAT.get((s1, s2), _SLEEP_COMPAT.get((s2, s1), 0.5))


def budget_overlap(min1: int, max1: int, min2: int, max2: int) -> int:
    """
    USD overlap between two budget ranges. Positive = overlap, 0 = adjacent, negative = gap.
    Used to pre-filter incompatible pairs before expensive vector queries.
    """
    return min(max1, max2) - max(min1, min2)


def lifestyle_distance(
    cleanliness1: str, guests1: str,
    cleanliness2: str, guests2: str,
) -> float:
    """
    0–1 normalised Manhattan distance on cleanliness + guests ordinals.
    0 = identical lifestyle, 1 = maximum distance.
    """
    c1 = _CLEANLINESS_ORDINAL.get(cleanliness1, 2)
    c2 = _CLEANLINESS_ORDINAL.get(cleanliness2, 2)
    g1 = _GUESTS_ORDINAL.get(guests1, 2)
    g2 = _GUESTS_ORDINAL.get(guests2, 2)
    max_dist = (_CLEANLINESS_ORDINAL["high"] - _CLEANLINESS_ORDINAL["low"]) + \
               (_GUESTS_ORDINAL["often"]     - _GUESTS_ORDINAL["never"])
    dist = abs(c1 - c2) + abs(g1 - g2)
    return round(dist / max_dist, 3)
