# Trace-X API Reference

Base URL: `http://localhost:8000` locally, or the deployed backend Vercel project's URL in
production (e.g. `https://trace-x-backend.vercel.app` — see [DEPLOYMENT.md](DEPLOYMENT.md)). The
frontend never hardcodes this; it reads `NEXT_PUBLIC_API_URL`. All endpoints are prefixed `/api/v1`
unless noted. Interactive Swagger docs are auto-generated at `/docs` on whichever base URL you're
running against.

## Emails

| Method | Path | Description |
|---|---|---|
| `POST` | `/emails/upload` | Multipart upload of a `.eml`/`.txt` file. Optional `?case_id=` to link immediately. Returns `{email_id, evidence_id}`. |
| `POST` | `/emails/analyze` | JSON body `{raw_email: string, case_id?: string}`. Same pipeline as upload, for pasted source. |
| `GET` | `/emails` | List all analyzed emails (summary view). |
| `GET` | `/emails/{id}` | Full email record (metadata, body, attachments). |
| `GET` | `/emails/{id}/headers` | Raw headers + header-forensics findings. |
| `GET` | `/emails/{id}/threat-analysis` | Risk score, sub-scores, factors, lookalike findings, attribution. |
| `GET` | `/emails/{id}/auth` | SPF/DKIM/DMARC results + provenance. |
| `GET` | `/emails/{id}/iocs` | Extracted indicators of compromise. |
| `GET` | `/emails/{id}/trace` | Reconstructed, geo-enriched relay chain. |
| `GET` | `/emails/{id}/graph` | Infrastructure relationship graph (React Flow node/edge JSON). |
| `GET` | `/emails/{id}/full` | **Aggregate** of all of the above in one call — what the Email Analyzer UI uses. |

## Cases (Investigations)

| Method | Path | Description |
|---|---|---|
| `GET` | `/cases` | List all cases. |
| `POST` | `/cases` | Create a case. Body: `{title, severity?, analyst?, summary?}`. |
| `GET` | `/cases/{id}` | Full case detail: linked emails, evidence, IOCs, timeline, notes. |
| `PATCH` | `/cases/{id}` | Update `title`/`status`/`severity`/`analyst`/`summary`. `status` must be one of `Open, Investigating, Contained, Resolved, Archived`. |
| `POST` | `/cases/{id}/notes` | Add an analyst note. Body: `{author, text}`. |
| `POST` | `/cases/{id}/link-email/{email_id}` | Link an already-analyzed email into a case. |

## Evidence

| Method | Path | Description |
|---|---|---|
| `GET` | `/evidence` | List all evidence records. |
| `GET` | `/evidence/{id}` | One evidence record. |
| `POST` | `/evidence/{id}/verify` | Re-hashes the stored file and confirms it matches the hash captured at ingestion. Returns `VERIFIED`, `TAMPERED`, or `MISSING`. |

## Campaigns

| Method | Path | Description |
|---|---|---|
| `GET` | `/campaigns` | List correlated campaigns. |
| `GET` | `/campaigns/{id}` | One campaign, with related emails. |
| `POST` | `/campaigns/recompute` | Re-run connected-components correlation across all analyzed emails. |

## Reports

| Method | Path | Description |
|---|---|---|
| `POST` | `/reports/{case_id}` | Generate a 19-section forensic report. Optional `?email_id=` (defaults to the case's most recent email). |
| `GET` | `/reports/{id}` | Fetch a previously generated report. |
| `GET` | `/reports` | List all generated reports. |

## Dashboard & Intelligence

| Method | Path | Description |
|---|---|---|
| `GET` | `/dashboard/summary` | Metrics, threat/severity distribution, recent alerts, recent investigations, activity timeline. |
| `GET` | `/ip/{ip}` | IP intelligence (cached if previously observed, otherwise a fresh provider lookup). |
| `GET` | `/domains/{domain}` | Domain intelligence, same caching behavior. |
| `GET` | `/iocs` | All extracted IOCs across every analyzed email (latest 500). |
| `GET` | `/settings` | Current `intel_mode` and app name. |

## Error Format

Non-2xx responses return `{"detail": "human-readable message"}`. Validation failures (e.g. status
enum, empty upload) return `400`; missing resources return `404`.
