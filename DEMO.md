# Trace-X — Judge Demonstration Script (~5 minutes)

Works identically two ways:

- **Local**: run both servers (see [README.md](README.md#local-setup--run)) and open `http://localhost:3000`.
- **Production**: open the deployed frontend URL directly (e.g. `https://trace-x-frontend.vercel.app`)
  — no setup required on the judge's side, nothing to install, no API keys. See
  [DEPLOYMENT.md](DEPLOYMENT.md) if this hasn't been deployed yet.

Demo Mode is on by default in both — nothing here requires an internet connection (locally) or an
API key (in either case).

## 0. Seeded state (0:00–0:30)

Open the app → you land on **Overview**. Point out:

- 6 emails already analyzed, 4 flagged CRITICAL, 1 correlated campaign, 31+ IOCs extracted
- The threat-type distribution and severity distribution are real, computed data — not
  placeholder numbers
- The **Demo Intelligence Mode** badge, top-right — every intelligence result in this app is
  labeled with its provenance; nothing fake is ever presented as live

> "This is DETECT → TRACE → CORRELATE → INVESTIGATE → REPORT, and every case on this screen went
> through the full pipeline automatically when the server started."

## 1. The centerpiece: Email Analyzer (0:30–3:00)

Click **Email Analyzer** → **Lookalike Domain Attack** (the PayPal case, scored CRITICAL 100/100).

- **Threat Summary tab**: overall score 100/100, classification "Brand Impersonation / Lookalike
  Domain," 90% confidence, and the six sub-scores (Content/Sender/Authentication/URL/
  Infrastructure/Impersonation) broken out individually
- Scroll to **"Why this score"**: point at the `+35 Lookalike domain: paypa1-secure-center.com`
  line — "resembles brand 'paypal' (96% similarity), combosquatting + homoglyph pattern detected."
  This is a deterministic rule, not an LLM guess — the same input always produces this exact score
- **Authentication tab**: SPF/DKIM/DMARC all FAIL, sourced from the `Authentication-Results`
  header — labeled "Reported by Receiving Mail Server," never fabricated
- **Header Forensics tab**: raw headers on the right, forensic findings on the left
- **IOCs tab**: 7 indicators extracted (IPs, domains, URL, Message-ID), filterable by type, each
  with its own risk/confidence/source
- **Relay Trace tab**: the reconstructed hop-by-hop chain, with the earliest reliable observed node
  flagged and the private internal hop clearly distinguished from the external one
- **Geolocation tab**: the malicious hop plotted on the map — click the marker. Point at the
  disclaimer banner: *"observed infrastructure location, not a physical attacker location."*
- **Infrastructure Graph tab**: the interactive React Flow graph — click the red-bordered IP node
  to show the full intelligence record in the inspector panel on the right
- **AI Assessment tab**: this is the responsible-attribution layer — "Probable malicious
  infrastructure," evidence strength STRONG, supporting indicators listed explicitly, and the
  limitations disclaimer stating this is an investigative lead, not a legal finding

## 2. Generate the report (3:00–3:45)

Click **Generate Forensic Report** (top right). The platform automatically opens/creates the
investigation case behind the scenes and navigates to a full 19-section forensic report —
scroll through it once to show the breadth (case info → executive summary → risk score →
authentication → IOCs → relay trace → geolocation → attribution → recommended actions). Click
**Print / Save as PDF** to show it's a real exportable document, not a mockup.

## 3. Investigations & Evidence (3:45–4:15)

Click **Investigations** in the nav — the case just created (or one of the 6 seeded ones) is here
with its status, severity, linked email, and a forensic timeline. Open **Evidence** — show the
SHA-256 hash captured at ingestion and click **Re-verify** to demonstrate the chain-of-custody
integrity check live.

## 4. Campaign correlation (4:15–4:45)

Click **Campaigns**. Explain: two of the seeded phishing emails — worded completely differently,
sent hours apart — were automatically grouped because they share the same malicious domain and
hosting IP. This is deterministic connected-components correlation over shared indicators, not a
black box: click into the campaign card to see exactly which domains/IPs are shared and which
emails are linked.

## 5. Close (4:45–5:00)

Return to **Overview**. Restate the value proposition in one line:

> "Trace-X doesn't just say 'this email is phishing' — it tells you why, traces where it came
> from, maps the infrastructure, correlates it with other attacks, and hands you a report you can
> act on — all in under a minute, entirely offline-capable."

## Optional: show the "not fooled by everything" case

If time allows, open the **Legitimate Institutional Email** demo case (from Email Analyzer) to
show it correctly scores 0/100 LOW / "Likely Legitimate" — the platform is calibrated, not just a
keyword-triggered alarm.

## If a judge asks "does this work on a real email?"

Yes — go to **Email Analyzer**, paste or upload any real `.eml` file (or use the textarea to paste
raw source), and it runs through the identical pipeline live, no seeded data involved.
