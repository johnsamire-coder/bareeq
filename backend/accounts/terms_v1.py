"""First published terms text (version 1). Same text as docs/TERMS-ar.md,
which is the copy for review and for sending to the client."""
from pathlib import Path

# Kept next to the code so the server does not depend on the docs folder.
TERMS_V1_PATH = Path(__file__).with_name("terms_v1_ar.md")


def terms_v1_text():
    return TERMS_V1_PATH.read_text(encoding="utf-8")
