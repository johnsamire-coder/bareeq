"""Terms texts published by migrations. docs/TERMS-ar.md is always a copy of
the latest one, for review and for sending to the client."""
from pathlib import Path

_HERE = Path(__file__).parent


def terms_v1_text():
    return (_HERE / "terms_v1_ar.md").read_text(encoding="utf-8")


def terms_v2_text():
    """v2: adds the 15-minute wait for 'car not found' and the 24-hour damage report window."""
    return (_HERE / "terms_v2_ar.md").read_text(encoding="utf-8")


def terms_v3_text():
    """v3 (phase 2): rewards and discounts: one discount per order, wallet, cashback,
    invite a friend, wash card, InstaPay refund into the wallet. No fixed numbers:
    they show in the app and the manager may change them."""
    return (_HERE / "terms_v3_ar.md").read_text(encoding="utf-8")


def terms_v4_text():
    """v4 (phase 3): the monthly subscription, and paying by card / mobile wallet."""
    return (_HERE / "terms_v4_ar.md").read_text(encoding="utf-8")


def terms_v5_text():
    """v5 (phase 4): express order, distance fee, technician tracking, supervisors."""
    return (_HERE / "terms_v5_ar.md").read_text(encoding="utf-8")


def latest_terms_text():
    return terms_v5_text()
