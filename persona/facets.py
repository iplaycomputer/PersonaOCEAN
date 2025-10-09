"""
PersonaOCEAN facet scaffolding (v0.5.0 roadmap)

Purpose
- Define Big Five facet names aligned with rubynor/bigfive-web (IPIP-NEO-120 mapping)
- Provide normalization helpers for 0–1 → −1..+1
- Keep this module import-safe; no side effects

This is a non-breaking stub to support future facet-level features.
"""
from __future__ import annotations

# Canonical facet map (names mirror rubynor/bigfive-web)
FACET_MAP: dict[str, list[str]] = {
    "O": [
        "Imagination",
        "Artistic interests",
        "Emotionality",
        "Adventurousness",
        "Intellect",
        "Liberalism",
    ],
    "C": [
        "Self-efficacy",
        "Orderliness",
        "Dutifulness",
        "Achievement-striving",
        "Self-discipline",
        "Cautiousness",
    ],
    "E": [
        "Friendliness",
        "Gregariousness",
        "Assertiveness",
        "Activity level",
        "Excitement-seeking",
        "Cheerfulness",
    ],
    "A": [
        "Trust",
        "Morality",
        "Altruism",
        "Cooperation",
        "Modesty",
        "Sympathy",
    ],
    "N": [
        "Anxiety",
        "Anger",
        "Depression",
        "Self-consciousness",
        "Immoderation",
        "Vulnerability",
    ],
}


def normalize_01_to_signed(value: float | None) -> float:
    """Map 0..1 → −1..+1; clamps outside inputs.
    Examples: 0.0→-1.0, 0.5→0.0, 1.0→+1.0
    """
    if value is None:
        v = 0.0
    else:
        try:
            v = float(value)
        except Exception:
            v = 0.0
    if v < 0.0:
        v = 0.0
    if v > 1.0:
        v = 1.0
    return (v - 0.5) * 2.0


def normalize_facets_payload(data: dict) -> dict:
    """Best-effort facet extraction from a BigFive-Web-like JSON payload.
    Returns a flat {FacetName: score[-1..+1]} dict. Unknown keys are skipped.
    Safe if payload does not contain facets.
    """
    out: dict[str, float] = {}
    facets = (data or {}).get("facets")
    if not isinstance(facets, dict):
        return out
    for domain, items in facets.items():
        if not isinstance(items, dict):
            continue
        for raw_name, raw_val in items.items():
            try:
                # Title-case for readability, preserve spaces/hyphens
                name = str(raw_name).strip().title()
                out[name] = normalize_01_to_signed(float(raw_val))
            except Exception:
                continue
    return out


__all__ = [
    "FACET_MAP",
    "normalize_01_to_signed",
    "normalize_facets_payload",
]
