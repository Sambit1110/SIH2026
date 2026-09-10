from app.core.forensics.auth_analysis import build_auth_result, parse_authentication_results


def test_parse_authentication_results():
    header = "mx.example.com; spf=fail smtp.mailfrom=evil.com; dkim=pass header.d=evil.com; dmarc=fail"
    parsed = parse_authentication_results(header)
    assert parsed == {"spf": "FAIL", "dkim": "PASS", "dmarc": "FAIL"}


def test_build_auth_result_from_header():
    result = build_auth_result("spf=pass; dkim=pass; dmarc=pass")
    assert result["spf"] == "PASS"
    assert result["source"].startswith("Reported by Receiving Mail Server")


def test_build_auth_result_demo_fallback_when_header_absent():
    result = build_auth_result("", demo_fallback={"spf": "FAIL", "dkim": "FAIL", "dmarc": "FAIL"})
    assert result["spf"] == "FAIL"
    assert "Demo Intelligence Dataset" in result["source"]


def test_build_auth_result_unavailable_when_nothing_present():
    result = build_auth_result("", demo_fallback=None)
    assert result["spf"] == "NONE"
    assert "Unavailable" in result["source"]
