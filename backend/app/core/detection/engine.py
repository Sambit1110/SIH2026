"""Deterministic, explainable rule/lexicon-based threat detection engine.

Designed behind a stable function signature so a trained ML/NLP classifier
can later be substituted or blended in without changing callers -- see
`classify()` docstring.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from app.core.detection.lexicons import CATEGORY_GROUPS, TECHNIQUE_BUCKETS


@dataclass
class DetectionSignal:
    category: str
    technique_bucket: str
    matched_phrase: str
    points: int
    reason: str


@dataclass
class DetectionResult:
    signals: list[DetectionSignal] = field(default_factory=list)
    technique_totals: dict = field(default_factory=dict)
    dominant_technique: str = "Unclassified"


def classify(subject: str, body_text: str, body_html: str) -> DetectionResult:
    """Rule-based classification. Swap-point for a trained model: replace this
    function body with `model.predict(text) -> DetectionResult`-shaped output
    while keeping the same return type, and the scoring engine / API need no
    changes.
    """
    haystack = " ".join([subject or "", body_text or "", re.sub(r"<[^>]+>", " ", body_html or "")])
    haystack_lower = haystack.lower()

    signals: list[DetectionSignal] = []
    for category, patterns in CATEGORY_GROUPS.items():
        bucket = TECHNIQUE_BUCKETS[category]
        for pattern, weight, reason in patterns:
            match = re.search(pattern, haystack_lower, re.IGNORECASE)
            if match:
                signals.append(
                    DetectionSignal(
                        category=category,
                        technique_bucket=bucket,
                        matched_phrase=match.group(0),
                        points=weight,
                        reason=reason,
                    )
                )

    technique_totals = Counter()
    for s in signals:
        technique_totals[s.technique_bucket] += s.points

    dominant = "Unclassified"
    if technique_totals:
        dominant = technique_totals.most_common(1)[0][0]

    return DetectionResult(
        signals=signals,
        technique_totals=dict(technique_totals),
        dominant_technique=dominant,
    )
