"""RFC 5322 / MIME email parsing. Never executes attachments — metadata only."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from email import message_from_bytes, policy
from email.message import Message
from email.utils import getaddresses


@dataclass
class ParsedAttachment:
    filename: str
    size: int
    mime: str
    sha256: str


@dataclass
class ParsedEmail:
    from_addr: str
    to_addr: str
    cc_addr: str
    reply_to: str
    return_path: str
    subject: str
    date_header: str
    message_id: str
    raw_headers: list[dict]
    body_text: str
    body_html: str
    attachments: list[dict]
    received_headers: list[str]
    auth_results_header: str
    x_headers: list[dict]


def _addr_list(msg: Message, name: str) -> str:
    values = msg.get_all(name, [])
    addrs = getaddresses(values)
    return ", ".join(a for _, a in addrs if a)


def _single_addr(msg: Message, name: str) -> str:
    values = msg.get_all(name, [])
    addrs = getaddresses(values)
    return addrs[0][1] if addrs else ""


def parse_eml_bytes(raw: bytes) -> ParsedEmail:
    msg = message_from_bytes(raw, policy=policy.default)

    raw_headers = [{"name": k, "value": v} for k, v in msg.items()]
    received_headers = [v for k, v in msg.items() if k.lower() == "received"]
    x_headers = [{"name": k, "value": v} for k, v in msg.items() if k.lower().startswith("x-")]
    auth_results = msg.get("Authentication-Results", "") or ""

    body_text, body_html, attachments = "", "", []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = (part.get_content_disposition() or "").lower()
            if disposition == "attachment" or part.get_filename():
                payload = part.get_payload(decode=True) or b""
                attachments.append(
                    {
                        "filename": part.get_filename() or "unnamed",
                        "size": len(payload),
                        "mime": content_type,
                        "sha256": hashlib.sha256(payload).hexdigest(),
                    }
                )
                continue
            if content_type == "text/plain" and not body_text:
                try:
                    body_text = part.get_content()
                except Exception:
                    body_text = (part.get_payload(decode=True) or b"").decode("utf-8", "replace")
            elif content_type == "text/html" and not body_html:
                try:
                    body_html = part.get_content()
                except Exception:
                    body_html = (part.get_payload(decode=True) or b"").decode("utf-8", "replace")
    else:
        content_type = msg.get_content_type()
        try:
            content = msg.get_content()
        except Exception:
            content = (msg.get_payload(decode=True) or b"").decode("utf-8", "replace")
        if content_type == "text/html":
            body_html = content
        else:
            body_text = content

    return ParsedEmail(
        from_addr=_single_addr(msg, "From"),
        to_addr=_addr_list(msg, "To"),
        cc_addr=_addr_list(msg, "Cc"),
        reply_to=_single_addr(msg, "Reply-To"),
        return_path=_single_addr(msg, "Return-Path"),
        subject=msg.get("Subject", "") or "",
        date_header=msg.get("Date", "") or "",
        message_id=msg.get("Message-ID", "") or "",
        raw_headers=raw_headers,
        body_text=body_text.strip(),
        body_html=body_html.strip(),
        attachments=attachments,
        received_headers=received_headers,
        auth_results_header=auth_results,
        x_headers=x_headers,
    )


def parse_raw_email_text(raw_text: str) -> ParsedEmail:
    return parse_eml_bytes(raw_text.encode("utf-8", "replace"))
