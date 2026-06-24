"""Project-wide constants shared across the API surface."""

from app.schemas import Pollutant

# HL4 — the app may show AQI category + EPA descriptor only, never medical advice.
DISCLAIMER = "Informational forecast — not medical guidance."

# Canonical measurement units per pollutant.
UNITS: dict[Pollutant, str] = {
    Pollutant.pm25: "µg/m³",
    Pollutant.o3: "ppb",
    Pollutant.no2: "ppb",
}

# Human-readable EPA category descriptors (display text only — see HL4).
CATEGORY_DESCRIPTORS: dict[str, str] = {
    "good": "Air quality is satisfactory, and air pollution poses little or no risk.",
    "moderate": (
        "Air quality is acceptable; unusually sensitive people may limit prolonged exertion."
    ),
    "unhealthy_sensitive": "Members of sensitive groups may experience health effects.",
    "unhealthy": "Some members of the general public may experience health effects.",
    "very_unhealthy": "Health alert: the risk of health effects is increased for everyone.",
    "hazardous": "Health warning of emergency conditions; everyone is more likely to be affected.",
}

# Phase 0 serves seed data only; the real validated model replaces this in Phase 3.
SEED_MODEL_VERSION = "seed-0.1"
