"""Test the signature verification module."""
from textwrap import dedent

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import load_pem_public_key

from phylum.init import sig


def test_phylum_pubkey_is_bytes():
    """Ensure the RSA public key in use for the rest of these tests is a bytes object."""
    assert isinstance(sig.PHYLUM_RSA_PUBKEY, bytes), "The RSA public key should be in bytes format"


def test_phylum_pubkey_is_constant():
    """Ensure the RSA public key in use by Phylum has not changed."""
    key_text = """\
        -----BEGIN PUBLIC KEY-----
        MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAyGgvuy6CWSgJuhKY8oVz
        42udH1F2yIlaBoxAdQFuY2zxPSSpK9zv34B7m0JekuC5WCYfW0gS2Z8Ryu2RVdQh
        7DXvQb7qwzZT0H11K9Pw8hIHBvZPM+d61GWgWDc3k/rFwMmqd+kytVZy0mVxNdv4
        P2qvy6BNaiUI7yoB1ahR/6klfkPit0X7pkK9sTHwW+/WcYitTQKnEnRzA3q8EmA7
        rbU/sFEypzBA3C3qNJZyKSwy47kWXhC4xXUS2NXvew4FoVU6ybMoeDApwsx1AgTu
        CPPnPlCwuCIyUPezCP5XYczuHfaWeuwArlwdJFSUpMTc+SqO6REKgL9yvpqsO5Ia
        sQIDAQAB
        -----END PUBLIC KEY-----
        """
    expected_key = bytes(dedent(key_text), encoding="ASCII")
    assert expected_key == sig.PHYLUM_RSA_PUBKEY, "The key should not be changing"


def test_phylum_pubkey_is_rsa():
    """Ensure the public key in use by Phylum is in fact a 2048 bit RSA key."""
    key = load_pem_public_key(sig.PHYLUM_RSA_PUBKEY)
    assert isinstance(key, rsa.RSAPublicKey)
    expected_rsa_pubkey_size_in_bits = 2048
    assert key.key_size == expected_rsa_pubkey_size_in_bits
