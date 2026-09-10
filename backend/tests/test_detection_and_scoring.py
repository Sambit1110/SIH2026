from app.core.detection.engine import classify
from app.core.detection.lookalike import analyze_domains
from app.core.detection.url_analysis import analyze_urls
from app.core.scoring.engine import compute_risk_score


def test_classify_detects_credential_harvesting():
    result = classify(
        subject="Unusual sign-in activity detected",
        body_text="Please verify your account immediately or it will be suspended within 24 hours.",
        body_html="",
    )
    assert result.dominant_technique in ("Phishing", "Social Engineering")
    assert len(result.signals) > 0


def test_classify_clean_email_has_no_signals():
    result = classify(subject="Meeting notes", body_text="Attached are the notes from today's meeting.", body_html="")
    assert result.signals == []
    assert result.dominant_technique == "Unclassified"


def test_scoring_is_deterministic_and_reproducible():
    detection = classify("Urgent wire transfer", "Please wire the funds to our new beneficiary account urgently.", "")
    header_findings = [{"issue": "Reply-To / From domain mismatch", "severity": "HIGH", "detail": "x"}]
    auth_result = {"spf": "FAIL", "dkim": "FAIL", "dmarc": "FAIL", "alignment": {}, "source": "test"}
    url_findings = analyze_urls([])
    lookalike_findings = analyze_domains(["totally-unrelated-domain.com"])

    result_a = compute_risk_score(
        detection, header_findings, auth_result, url_findings, lookalike_findings,
        from_domain_intel={"reputation": "MALICIOUS", "domain": "evil.com", "created_date": "2026-08-01"},
        observed_ip_intel=[], relay_flags=[],
    )
    result_b = compute_risk_score(
        detection, header_findings, auth_result, url_findings, lookalike_findings,
        from_domain_intel={"reputation": "MALICIOUS", "domain": "evil.com", "created_date": "2026-08-01"},
        observed_ip_intel=[], relay_flags=[],
    )
    assert result_a.overall_score == result_b.overall_score
    assert result_a.severity == result_b.severity
    assert result_a.factors == result_b.factors


def test_clean_email_scores_low_and_legitimate():
    detection = classify("Meeting notes", "Attached are the notes from today's meeting.", "")
    auth_result = {"spf": "PASS", "dkim": "PASS", "dmarc": "PASS", "alignment": {}, "source": "test"}
    result = compute_risk_score(
        detection, [], auth_result, [], [],
        from_domain_intel={"reputation": "CLEAN", "domain": "example.com", "created_date": "2010-01-01"},
        observed_ip_intel=[], relay_flags=[],
    )
    assert result.overall_score < 25
    assert result.severity == "LOW"
    assert result.classification == "Likely Legitimate"


def test_severity_thresholds_are_monotonic():
    from app.core.scoring.engine import _cap
    assert _cap(150) == 100
    assert _cap(-10) == 0
    assert _cap(50) == 50


def test_high_severity_bec_gets_real_attribution_not_insufficient_evidence():
    """Regression test: a CRITICAL-scoring BEC email with strong sender-mismatch
    and full auth failure must not report 'Insufficient evidence' / WEAK just
    because its observed IP is merely SUSPICIOUS (not MALICIOUS) and it has no
    lookalike-domain hit. Strong sender+auth evidence must itself count as
    attribution evidence.
    """
    detection = classify(
        "Urgent - Confidential Wire Transfer Required Today",
        "On behalf of the CEO, wire the funds to our new beneficiary account urgently. "
        "Keep this confidential and do not discuss this with anyone.",
        "",
    )
    header_findings = [
        {"issue": "Reply-To / From domain mismatch", "severity": "HIGH", "detail": "x"},
    ]
    auth_result = {"spf": "FAIL", "dkim": "FAIL", "dmarc": "FAIL", "alignment": {}, "source": "test"}
    result = compute_risk_score(
        detection, header_findings, auth_result, [], [],
        from_domain_intel={"reputation": "SUSPICIOUS", "domain": "evil-typo.com", "created_date": "2026-08-01"},
        observed_ip_intel=[{"ip": "1.2.3.4", "reputation": "SUSPICIOUS", "proxy_vpn_tor": "UNKNOWN", "org": "Test"}],
        relay_flags=[],
    )
    assert result.severity in ("HIGH", "CRITICAL")
    assert result.attribution["evidence_strength"] != "WEAK"
    assert "Insufficient evidence" not in result.attribution["conclusion"]
