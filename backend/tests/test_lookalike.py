from app.core.detection.lookalike import analyze_domain, analyze_domains


def test_detects_combosquatted_brand_domain():
    finding = analyze_domain("microsoft-verify-account.xyz")
    assert finding is not None
    assert finding.target_brand == "microsoft"
    assert finding.confidence == "HIGH"


def test_detects_homoglyph_typosquat():
    finding = analyze_domain("paypa1-secure-center.com")
    assert finding is not None
    assert finding.target_brand == "paypal"


def test_no_false_positive_for_unrelated_domain():
    finding = analyze_domain("northbridge-financial.com")
    assert finding is None


def test_exact_brand_domain_is_not_flagged():
    finding = analyze_domain("paypal.com")
    assert finding is None


def test_analyze_domains_returns_only_matches():
    findings = analyze_domains(["paypal.com", "paypa1-alerts.com", "example.org"])
    domains_flagged = [f.observed_domain for f in findings]
    assert "paypa1-alerts.com" in domains_flagged
    assert "paypal.com" not in domains_flagged
    assert "example.org" not in domains_flagged
