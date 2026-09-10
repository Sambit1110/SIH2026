from app.core.forensics.header_forensics import analyze_headers


def test_detects_reply_to_mismatch():
    findings = analyze_headers(
        from_addr="ceo@realcompany.com",
        reply_to="ceo@fake-domain.com",
        return_path="ceo@realcompany.com",
        subject="Hello",
        message_id="<1@realcompany.com>",
        date_header="Mon, 01 Sep 2026 10:00:00 +0000",
        x_headers=[],
    )
    issues = [f["issue"] for f in findings]
    assert "Reply-To / From domain mismatch" in issues


def test_no_findings_for_consistent_headers():
    findings = analyze_headers(
        from_addr="registrar@university.edu",
        reply_to="",
        return_path="registrar@university.edu",
        subject="Registration Confirmation",
        message_id="<abc@university.edu>",
        date_header="Mon, 01 Sep 2026 10:00:00 +0000",
        x_headers=[],
    )
    issues = [f["issue"] for f in findings]
    assert "Reply-To / From domain mismatch" not in issues
    assert "Return-Path / From domain mismatch" not in issues
    assert any(f["severity"] == "INFO" for f in findings)


def test_missing_message_id_flagged():
    findings = analyze_headers(
        from_addr="a@example.com", reply_to="", return_path="a@example.com",
        subject="Test", message_id="", date_header="Mon, 01 Sep 2026 10:00:00 +0000", x_headers=[],
    )
    issues = [f["issue"] for f in findings]
    assert "Missing Message-ID" in issues
