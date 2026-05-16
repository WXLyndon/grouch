from datetime import datetime

TERM_SUFFIXES = {
    "spring": "02",
    "summer": "05",
    "fall": "08",
}

TERM_MONTHS = {
    "spring": 2,
    "summer": 5,
    "fall": 8,
}


def resolve_term(season: str, now: datetime | None = None) -> str:
    """Return the next Banner term code for a season name."""
    normalized = season.lower()
    if normalized not in TERM_SUFFIXES:
        valid = ", ".join(TERM_SUFFIXES)
        raise ValueError(f"Invalid season '{season}'. Expected one of: {valid}.")

    current = now or datetime.now()
    year = current.year
    if current.month > TERM_MONTHS[normalized]:
        year += 1

    return f"{year}{TERM_SUFFIXES[normalized]}"
