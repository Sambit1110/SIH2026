from app.core.parsing.ioc_extractor import (
    extract_domains,
    extract_emails,
    extract_ips,
    extract_urls,
    is_ip_literal_url,
    registered_domain,
)


def test_extract_ips_valid_only():
    text = "Server at 192.168.1.1 and 8.8.8.8, also 999.999.999.999 which is invalid."
    ips = extract_ips(text)
    assert "8.8.8.8" in ips
    assert "192.168.1.1" in ips
    assert "999.999.999.999" not in ips


def test_extract_urls():
    text = "Visit http://example.com/path and https://sub.example.org/a?b=1 now."
    urls = extract_urls(text)
    assert "http://example.com/path" in urls
    assert "https://sub.example.org/a?b=1" in urls


def test_extract_emails_lowercased():
    text = "Contact Alice@Example.COM or bob@example.org"
    emails = extract_emails(text)
    assert "alice@example.com" in emails
    assert "bob@example.org" in emails


def test_registered_domain_strips_subdomains():
    assert registered_domain("mail.sub.example.co.uk") == "example.co.uk"
    assert registered_domain("example.com") == "example.com"


def test_extract_domains_from_urls_and_emails():
    urls = ["http://phish.example-fraud.com/login"]
    emails = ["user@another-example.com"]
    domains = extract_domains(urls, emails, [])
    assert "example-fraud.com" in domains
    assert "another-example.com" in domains


def test_is_ip_literal_url():
    assert is_ip_literal_url("http://8.8.8.8/path") is True
    assert is_ip_literal_url("http://example.com/path") is False
