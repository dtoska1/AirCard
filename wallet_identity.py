"""Validated Wallet identifiers used by every public artwork entry point."""
import re

# Existing catalog/path grammar; observed fixtures are 28 characters including '='.
# Keep the established 20–64 range rather than guessing an exact iOS length.
CARD_ID = re.compile(r"[-A-Za-z0-9_+=]{20,64}\Z")


def valid_card_id(value):
    return isinstance(value, str) and CARD_ID.fullmatch(value) is not None


def require_card_id(value):
    if not valid_card_id(value):
        raise ValueError("Invalid Wallet card ID: use 20–64 ASCII letters, digits, _, +, = or -")
    return value


def wallet_directory(identifier, extension):
    require_card_id(identifier)
    if extension not in (".pkpass", ".cache", ".pkcache"):
        raise ValueError("Invalid Wallet directory type")
    return f"/var/mobile/Library/Passes/Cards/{identifier}{extension}"
