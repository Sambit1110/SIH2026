"""Lookalike / typosquat / homoglyph domain detection against a small brand list."""
from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz

from app.core.detection.lexicons import PROTECTED_BRANDS

SUSPICIOUS_TLDS = {"xyz", "top", "click", "gq", "cf", "tk", "ml", "work", "support", "info"}

HOMOGLYPH_MAP = {
    "0": "o", "1": "l", "3": "e", "5": "s", "7": "t",
    "rn": "m", "vv": "w", "cl": "d",
}


def _normalize_homoglyphs(s: str) -> str:
    out = s
    for glyph, real in HOMOGLYPH_MAP.items():
        out = out.replace(glyph, real)
    return out


@dataclass
class LookalikeFinding:
    observed_domain: str
    target_brand: str
    similarity: float
    reason: str
    confidence: str


def analyze_domain(domain: str) -> LookalikeFinding | None:
    domain_lower = domain.lower()
    root = domain_lower.split(".")[0]
    tld = domain_lower.split(".")[-1] if "." in domain_lower else ""
    normalized_root = _normalize_homoglyphs(root)

    best: LookalikeFinding | None = None
    for brand in PROTECTED_BRANDS:
        if brand == root or brand == normalized_root:
            continue  # exact match to the real brand root is not a lookalike

        contains_brand = brand in root or brand in normalized_root
        # partial_ratio finds the best-aligned substring match, which is what
        # we want for "brand name padded with extra words" (combosquatting);
        # ratio captures near-miss typos where lengths are close.
        partial_score = max(fuzz.partial_ratio(root, brand), fuzz.partial_ratio(normalized_root, brand))
        ratio_score = max(fuzz.ratio(root, brand), fuzz.ratio(normalized_root, brand))
        score = 96.0 if contains_brand else max(partial_score, ratio_score)

        # A high bar for the non-containment fuzzy-only path: short brand
        # names (e.g. "apple", "adobe") otherwise false-positive against
        # unrelated short English words at a 75-ish ratio threshold.
        if score < 84:
            continue

        reasons = []
        if contains_brand:
            reasons.append(f"contains brand name '{brand}' padded with extra characters (combosquatting)")
        if normalized_root != root:
            reasons.append("character-substitution / homoglyph pattern detected")
        if tld in SUSPICIOUS_TLDS:
            reasons.append(f"uses uncommon TLD '.{tld}' often associated with low-cost bulk registration")
        if not reasons:
            reasons.append("high string similarity to a known brand domain")

        finding = LookalikeFinding(
            observed_domain=domain,
            target_brand=brand,
            similarity=round(score, 1),
            reason="; ".join(reasons),
            confidence="HIGH" if score >= 90 else ("MEDIUM" if score >= 82 else "LOW"),
        )
        if best is None or finding.similarity > best.similarity:
            best = finding

    return best


def analyze_domains(domains: list[str]) -> list[LookalikeFinding]:
    findings = []
    for d in domains:
        f = analyze_domain(d)
        if f:
            findings.append(f)
    return findings
