"""Phrase/pattern banks for the rule-based threat detection engine.

Each entry: (regex_pattern, weight, human_reason). Weights feed directly into
the explainable scoring engine as point contributions, so they double as
documentation of the methodology.
"""

CREDENTIAL_HARVESTING = [
    (r"verify your (account|password|identity)", 14, "Credential verification request"),
    (r"(click|log ?in) here to (confirm|verify|update)", 12, "Login/verify link pressure"),
    (r"unusual (sign-?in|login) activity", 10, "Fake unusual-activity alert"),
    (r"your (account|mailbox) (will be|has been) (suspended|locked|disabled)", 16, "Account suspension threat"),
    (r"re-?enter your (password|credentials)", 14, "Credential re-entry request"),
]

PAYMENT_DIVERSION = [
    (r"update(d)? (bank|banking|account) details", 18, "Banking detail change request"),
    (r"change (of )?(payment|remittance) (details|instructions)", 18, "Payment instruction change"),
    (r"new (bank|beneficiary) account", 16, "New beneficiary account introduced"),
    (r"wire (the )?(funds|payment|transfer)", 14, "Wire transfer request"),
    (r"process (this|the) payment (urgently|immediately|today)", 12, "Urgent payment processing request"),
]

INVOICE_FRAUD = [
    (r"(attached|see attached) invoice", 6, "Invoice attachment reference"),
    (r"overdue (invoice|payment)", 10, "Overdue invoice pressure"),
    (r"outstanding balance", 8, "Outstanding balance framing"),
    (r"remit(tance)? (advice|payment)", 8, "Remittance advice framing"),
]

GIFT_CARD_SCAM = [
    (r"gift cards?", 16, "Gift card request pattern"),
    (r"(itunes|amazon|google play) cards?", 18, "Retail gift card fraud pattern"),
]

URGENCY = [
    (r"\burgent\b", 8, "Urgency language"),
    (r"immediate(ly)? (action|response|attention)", 10, "Immediate action demand"),
    (r"as soon as possible|asap\b", 6, "ASAP pressure"),
    (r"time[- ]sensitive", 6, "Time-sensitive framing"),
    (r"within (24|48) hours", 8, "Artificial deadline"),
]

AUTHORITY_PRESSURE = [
    (r"\bceo\b|\bcfo\b|\bcoo\b|managing director|chief executive", 10, "Executive-authority framing"),
    (r"on behalf of (the )?(ceo|cfo|director|board)", 12, "Executive delegation claim"),
    (r"per (my|our) (last )?(conversation|call)", 6, "False prior-conversation reference"),
]

SECRECY = [
    (r"keep this (confidential|between us|private)", 14, "Secrecy/confidentiality pressure"),
    (r"do not (discuss|tell|forward|share) (this|with anyone)", 14, "Non-disclosure pressure"),
    (r"handle (this )?discreetly", 10, "Discretion pressure"),
]

FEAR = [
    (r"legal action", 10, "Legal-threat framing"),
    (r"account (closure|termination)", 10, "Account closure threat"),
    (r"suspicious (activity|transaction) detected", 8, "Fabricated security alert"),
]

MALICIOUS_LINK_LANGUAGE = [
    (r"click (here|below|the link)", 8, "Generic click-through pressure"),
    (r"download (the )?attachment", 6, "Attachment download prompt"),
]

CATEGORY_GROUPS = {
    "Credential Harvesting": CREDENTIAL_HARVESTING,
    "Payment Diversion": PAYMENT_DIVERSION,
    "Invoice Fraud": INVOICE_FRAUD,
    "Gift Card Scam": GIFT_CARD_SCAM,
    "Urgency": URGENCY,
    "Authority Pressure": AUTHORITY_PRESSURE,
    "Secrecy": SECRECY,
    "Fear": FEAR,
    "Malicious Link Language": MALICIOUS_LINK_LANGUAGE,
}

# Category -> broad technique bucket, used to pick a final classification.
TECHNIQUE_BUCKETS = {
    "Credential Harvesting": "Phishing",
    "Payment Diversion": "Business Email Compromise",
    "Invoice Fraud": "Vendor Invoice Fraud",
    "Gift Card Scam": "Fraud",
    "Urgency": "Social Engineering",
    "Authority Pressure": "Social Engineering",
    "Secrecy": "Social Engineering",
    "Fear": "Social Engineering",
    "Malicious Link Language": "Phishing",
}

# Well-known brands commonly impersonated, used for lookalike-domain detection.
PROTECTED_BRANDS = [
    "paypal", "microsoft", "office365", "google", "apple", "amazon",
    "netflix", "bankofamerica", "hdfcbank", "icicibank", "sbi", "rbi",
    "irs", "dhl", "fedex", "linkedin", "docusign", "adobe", "outlook",
]
