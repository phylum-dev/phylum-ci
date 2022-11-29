"""Verify Phylum generated digital signatures.

This module is meant to be a simple means of verifying RSA signatures in Python. It makes use of the hazardous materials
layer of the `cryptography` library, but does so in a way that closely follows the example documentation:

https://cryptography.io/en/latest/hazmat/primitives/asymmetric/rsa/#verification

There are a number of assumptions:

* The RSA Public Key for Phylum, Inc. will not change between releases
* The RSA signature was created with the SHA256 hash function
* The RSA signature was created with the PKCS1 v1.5 padding scheme
* The files to be verified were created by Phylum, Inc.
* The source of the `.signature` files is a trusted location, controlled by Phylum, Inc. for it's CLI releases

If these assumptions are not met, the signature verification will fail and the CLI install will exit with a message and
a non-zero return code. The Phylum RSA public key is hard-coded in this module on purpose. It helps to limit network
calls to GitHub, which can be a source of failure. It also has the advantage of "spreading" the public key to multiple
locations so that a change to it (malicious or benign) will require access and coordination to each of those sources.
It is understood that this method is not fool proof but should help the Phylum devs identify failures.

A functional test exists to check that the hard-coded signature matches the one hosted at
https://raw.githubusercontent.com/phylum-dev/cli/main/scripts/signing-key.pub since that is where the quickstart
documentation directs CLI users.
"""
from pathlib import Path
from textwrap import dedent

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.backends.openssl import backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa, types

# This is the RSA Public Key for Phylum, Inc. The matching private key was used to sign the software releases
PHYLUM_RSA_PUBKEY = bytes(
    dedent(
        """\
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
    ),
    encoding="ASCII",
)


def verify_sig(file_path: Path, sig_path: Path) -> None:
    """Verify a given file has a valid signature.

    `file_path` is the path to the file data to verify.
    `sig_path` is the path to the `.signature` file containing the RSA SHA256 signature information.

    The public key is an assumed constant, the RSA Public Key for Phylum, Inc.
    """
    try:
        # The `cryptography` library does not know this is an RSA public key yet...make sure it is
        phylum_public_key: types.PUBLIC_KEY_TYPES = serialization.load_pem_public_key(PHYLUM_RSA_PUBKEY)
        if isinstance(phylum_public_key, rsa.RSAPublicKey):
            phylum_rsa_public_key: rsa.RSAPublicKey = phylum_public_key
        else:
            raise SystemExit(f" [!] The public key was expected to be RSA but instead got: {type(phylum_public_key)}")
    except UnsupportedAlgorithm as err:
        openssl_ver = backend.openssl_version_text()
        msg = f" [!] Serialized key type is not supported by the OpenSSL version `cryptography` is using: {openssl_ver}"
        raise SystemExit(msg) from err
    except ValueError as err:
        raise SystemExit(" [!] The PEM data's structure could not be decoded successfully") from err

    # Confirm the data from `file_path` with the signature from the `sig_path`
    try:
        print(f" [*] Verifying {file_path} with signature from {sig_path} ...", end="")
        # NOTE: The verify method has no return value, but will raise an exception when the signature does not validate
        phylum_rsa_public_key.verify(sig_path.read_bytes(), file_path.read_bytes(), padding.PKCS1v15(), hashes.SHA256())
        print("SUCCESS", flush=True)
    except InvalidSignature as err:
        print("FAIL", flush=True)
        raise SystemExit(" [!] The signature could not be verified and may be invalid") from err
