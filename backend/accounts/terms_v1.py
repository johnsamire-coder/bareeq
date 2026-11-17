"""Terms texts published by migrations. docs/TERMS-ar.md is always a copy of
the latest one, for review and for sending to the client."""
from pathlib import Path

_HERE = Path(__file__).parent


def terms_v1_text():
    return (_HERE / "terms_v1_ar.md").read_text(encoding="utf-8")


def terms_v2_text():
    """v2: adds the 15-minute wait for 'car not found' and the 24-hour damage report window."""
    return (_HERE / "terms_v2_ar.md").read_text(encoding="utf-8")


def latest_terms_text():
    return terms_v2_text()
