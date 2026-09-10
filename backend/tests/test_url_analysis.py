from app.core.detection.url_analysis import analyze_url


def test_flags_ip_literal_url():
    finding = analyze_url("http://8.8.8.8/login")
    assert finding.risk in ("MEDIUM", "HIGH")
    assert any("IP address" in r for r in finding.reasons)


def test_flags_suspicious_tld():
    finding = analyze_url("http://secure-login-update.xyz/verify")
    assert any("uncommon TLD" in r for r in finding.reasons)


def test_clean_url_is_low_risk():
    finding = analyze_url("https://www.example.com/about")
    assert finding.risk == "LOW"
    assert finding.reasons == []


def test_url_shortener_flagged():
    finding = analyze_url("http://bit.ly/abcd123")
    assert any("shortening" in r for r in finding.reasons)
