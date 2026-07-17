"""Data contract shared with the rental-price-estimator-sd project.

The estimator trains on a CSV with exactly these feature columns, so
every listing the agent saves must validate against this schema. Extra
columns (like source_url) are allowed: the estimator selects columns
by name and ignores the rest.
"""

from __future__ import annotations

import unicodedata

# Columns the estimator consumes (its training contract) plus two
# audit columns: source_url (provenance) and collected_at (capture
# date, the raw material for price-over-time reports).
COLUMNS = [
    "sector",
    "area_m2",
    "bedrooms",
    "bathrooms",
    "parking_spots",
    "furnished",
    "age_years",
    "price_dop",
    "source_url",
    "collected_at",
]

# The 10 sectors the deployed estimator knows. Listings outside these
# are skipped: the model cannot price a sector it has no baseline for.
KNOWN_SECTORS = [
    "Piantini",
    "Naco",
    "Serrallés",
    "Bella Vista",
    "Arroyo Hondo",
    "Los Prados",
    "Gazcue",
    "Santo Domingo Este",
    "Villa Mella",
    "Los Alcarrizos",
]

# Sanity ranges for the Santo Domingo rental market. Records outside
# these are almost always data errors (sale prices, USD amounts, typos).
RANGES = {
    "area_m2": (15, 1000),
    "bedrooms": (0, 10),
    "bathrooms": (1, 10),
    "parking_spots": (0, 10),
    "furnished": (0, 1),
    "age_years": (0, 80),
    "price_dop": (5_000, 1_000_000),
}


def _strip_accents(text: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn"
    )


# Accent/spelling variants seen in real listings, normalized form.
_SECTOR_LOOKUP = {_strip_accents(s).lower(): s for s in KNOWN_SECTORS}
_SECTOR_LOOKUP.update(
    {
        "sto dgo este": "Santo Domingo Este",
        "sto. dgo. este": "Santo Domingo Este",
        "santo domingo e.": "Santo Domingo Este",
        "ensanche naco": "Naco",
        "ensanche serralles": "Serrallés",
    }
)


def normalize_sector(raw: str) -> str | None:
    """Map a raw sector name to a known sector, or None if unknown."""
    key = _strip_accents(raw.strip()).lower()
    return _SECTOR_LOOKUP.get(key)


def validate(record: dict) -> list[str]:
    """Return a list of problems; empty list means the record is valid."""
    problems = []

    sector = record.get("sector", "")
    if not isinstance(sector, str) or normalize_sector(sector) is None:
        problems.append(
            f"unknown sector '{sector}' (must be one of: {', '.join(KNOWN_SECTORS)})"
        )

    for field, (lo, hi) in RANGES.items():
        value = record.get(field)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            problems.append(f"{field} must be a number, got {value!r}")
        elif not lo <= value <= hi:
            problems.append(f"{field}={value} outside sane range [{lo}, {hi}]")

    url = record.get("source_url", "")
    if not isinstance(url, str) or not url.startswith(("http://", "https://", "sample:")):
        problems.append(f"source_url must be a URL, got {url!r}")

    return problems
