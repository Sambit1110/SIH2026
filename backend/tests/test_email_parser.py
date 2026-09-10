from app.core.parsing.email_parser import parse_eml_bytes, parse_raw_email_text

SAMPLE = b"""From: Alice <alice@example.com>
To: bob@example.org
Cc: carol@example.org
Reply-To: alice-reply@example.com
Return-Path: <alice@example.com>
Subject: Hello Bob
Date: Mon, 01 Sep 2026 10:00:00 +0000
Message-ID: <abc123@example.com>
Content-Type: text/plain; charset="utf-8"

Hi Bob, just checking in. Visit https://example.org/status for details.
My IP for reference is 8.8.8.8.
"""


def test_parses_basic_headers():
    parsed = parse_eml_bytes(SAMPLE)
    assert parsed.from_addr == "alice@example.com"
    assert parsed.to_addr == "bob@example.org"
    assert parsed.cc_addr == "carol@example.org"
    assert parsed.reply_to == "alice-reply@example.com"
    assert parsed.return_path == "alice@example.com"
    assert parsed.subject == "Hello Bob"
    assert parsed.message_id == "<abc123@example.com>"
    assert "checking in" in parsed.body_text


def test_parse_raw_text_matches_bytes_path():
    parsed = parse_raw_email_text(SAMPLE.decode("utf-8"))
    assert parsed.from_addr == "alice@example.com"


def test_malformed_email_does_not_crash():
    malformed = b"This is not really a valid email at all, just plain text.\nNo headers here."
    parsed = parse_eml_bytes(malformed)
    # No headers parse out, but it must not raise -- graceful degradation.
    assert parsed.from_addr == ""
    assert parsed.subject == ""


def test_empty_bytes_does_not_crash():
    parsed = parse_eml_bytes(b"")
    assert parsed.from_addr == ""
    assert parsed.raw_headers == []


def test_attachment_metadata_captured_without_execution():
    raw = b"""From: a@example.com
To: b@example.com
Subject: With attachment
Content-Type: multipart/mixed; boundary="BOUND"

--BOUND
Content-Type: text/plain

body text
--BOUND
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="invoice.pdf"
Content-Transfer-Encoding: base64

aGVsbG8gd29ybGQ=
--BOUND--
"""
    parsed = parse_eml_bytes(raw)
    assert len(parsed.attachments) == 1
    assert parsed.attachments[0]["filename"] == "invoice.pdf"
    assert "sha256" in parsed.attachments[0]
    assert parsed.attachments[0]["size"] > 0
