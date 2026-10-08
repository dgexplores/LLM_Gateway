import re

PII_PATTERNS = {
    "email": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "api_key": r"(sk-[a-zA-Z0-9]{32,})",
    "phone": r"\b\d{10,}\b"
}

def redact(text: str) -> str:
    for name, pattern in PII_PATTERNS.items():
        text = re.sub(pattern, f"<{name.upper()}_REDACTED>", text)
    return text

def test_redaction():
    assert "Contact <EMAIL_REDACTED>" == redact("Contact test@example.com")
    assert "<API_KEY_REDACTED>" == redact("sk-123456789012345678901234567890123456")
    print("Redaction tests passed")

if __name__ == "__main__":
    test_redaction()
