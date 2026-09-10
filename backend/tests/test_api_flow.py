RAW_PHISHING_EMAIL = """From: "Support" <support@fake-bank-alerts.com>
To: victim@example.com
Reply-To: support@another-domain.net
Return-Path: <bounce@fake-bank-alerts.com>
Subject: Urgent - verify your account immediately
Date: Mon, 01 Sep 2026 10:00:00 +0000
Message-ID: <xyz789@fake-bank-alerts.com>
Authentication-Results: mx.example.com; spf=fail; dkim=fail; dmarc=fail
Content-Type: text/plain; charset="utf-8"

Your account will be suspended within 24 hours. Click here to verify your
account: http://fake-bank-alerts.com/verify
"""


def test_full_investigation_flow(client):
    # 1. Create a case
    resp = client.post("/api/v1/cases", json={"title": "Test Investigation", "severity": "LOW"})
    assert resp.status_code == 200
    case_id = resp.json()["id"]

    # 2. Analyze a raw email into that case
    resp = client.post("/api/v1/emails/analyze", json={"raw_email": RAW_PHISHING_EMAIL, "case_id": case_id})
    assert resp.status_code == 200
    email_id = resp.json()["email_id"]
    evidence_id = resp.json()["evidence_id"]

    # 3. Full aggregate analysis view works end-to-end
    resp = client.get(f"/api/v1/emails/{email_id}/full")
    assert resp.status_code == 200
    data = resp.json()
    assert data["threat_analysis"]["severity"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert data["auth"]["spf"] == "FAIL"
    assert len(data["iocs"]) > 0
    assert data["graph"]["nodes"]

    # 4. Evidence integrity check passes
    resp = client.post(f"/api/v1/evidence/{evidence_id}/verify")
    assert resp.status_code == 200
    assert resp.json()["integrity_status"] == "VERIFIED"

    # 5. Case detail reflects the linked email
    resp = client.get(f"/api/v1/cases/{case_id}")
    assert resp.status_code == 200
    assert len(resp.json()["emails"]) == 1

    # 6. Report generation aggregates everything
    resp = client.post(f"/api/v1/reports/{case_id}")
    assert resp.status_code == 200
    report = resp.json()["data"]
    assert report["risk_score"]["overall_score"] is not None
    assert report["attribution_assessment"]["conclusion"]
    assert "physical location" in report["attribution_assessment"]["limitations"]


def test_reject_oversized_or_wrong_type_upload(client):
    import io
    resp = client.post(
        "/api/v1/emails/upload",
        files={"file": ("malware.exe", io.BytesIO(b"MZ fake binary"), "application/octet-stream")},
    )
    assert resp.status_code == 400


def test_reject_empty_raw_email(client):
    resp = client.post("/api/v1/emails/analyze", json={"raw_email": "   "})
    assert resp.status_code == 400


def test_case_status_validation(client):
    resp = client.post("/api/v1/cases", json={"title": "Status Test"})
    case_id = resp.json()["id"]
    resp = client.patch(f"/api/v1/cases/{case_id}", json={"status": "NotARealStatus"})
    assert resp.status_code == 400


def test_dashboard_summary_returns_metrics(client):
    resp = client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 200
    assert "emails_analyzed" in resp.json()["metrics"]


def test_campaign_recompute_endpoint(client):
    resp = client.post("/api/v1/campaigns/recompute")
    assert resp.status_code == 200
    assert "campaign_count" in resp.json()
