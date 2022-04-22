"""Test the minisign signature verification module."""
from phylum.init import sig


def test_phylum_minisign_pubkey():
    """Ensure the minisign public key in use by Phylum has not changed."""
    expected_key = "RWT6G44ykbS8GABiLXrJrYsap7FCY77m/Jyi0fgsr/Fsy3oLwU4l0IDf"
    assert sig.PHYLUM_MINISIGN_PUBKEY == expected_key, "The key should not be changing"


def test_phylum_pubkey_sig_algo():
    """Ensure the Phylum minisign public key signature algorithm is `Ed` (legacy)."""
    assert isinstance(sig.PHYLUM_MINISIGN_PUBKEY_SIG_ALGO, bytes)
    assert sig.PHYLUM_MINISIGN_PUBKEY_SIG_ALGO == b"Ed", "Only the legacy `Ed` signature is used by Phylum currently"


def test_phylum_pubkey_key_id():
    """Ensure the Phylum minisign public key `key_id` has not changed."""
    expected_key_id = b"\xfa\x1b\x8e2\x91\xb4\xbc\x18"
    assert isinstance(sig.PHYLUM_MINISIGN_PUBKEY_KEY_ID, bytes)
    assert sig.PHYLUM_MINISIGN_PUBKEY_KEY_ID == expected_key_id, "The key ID should not be changing"


def test_phylum_ed25519_pubkey():
    """Ensure the Phylum minisign Ed25519 public key has not changed."""
    expected_key = b"\x00b-z\xc9\xad\x8b\x1a\xa7\xb1Bc\xbe\xe6\xfc\x9c\xa2\xd1\xf8,\xaf\xf1l\xcbz\x0b\xc1N%\xd0\x80\xdf"
    assert isinstance(sig.PHYLUM_MINISIGN_PUBKEY_ED25519, bytes)
    assert sig.PHYLUM_MINISIGN_PUBKEY_ED25519 == expected_key, "The Ed25519 public key should not be changing"
