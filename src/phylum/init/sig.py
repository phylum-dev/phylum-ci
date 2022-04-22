"""Helper functions for verifying minisign signatures.

This module is meant to be a quick and dirty means of verifying minisign signatures in Python.
There is no readily accessible Python library at this time. The `py-minisign` repository exists
on GitHub to attempt this - https://github.com/x13a/py-minisign - but it does not exist as a
package on PyPI and also does not appear to be actively maintained. There is a `minisign` package
on PyPI - https://pypi.org/project/minisign/ - but it comes from a different repo and has no
functionality at the time of this writing.

Short of forking the `py-minisign` repo to maintain it and publish a package from it on PyPI,
the actual format for signatures and public keys is simple and so is verifying signatures.

Minisign reference: https://jedisct1.github.io/minisign/

Even still, this module is NOT meant to be used as a library or general purpose minisign
signature verification. It is purpose written to specifically verify minisign signatures that
were created by Phylum. As such, it makes a number of assumptions:

* The Minisign Public Key for Phylum, Inc. will not change between releases
* The files to be verified were created by Phylum, Inc.
* The `.minisig` signature includes a trusted comment and will therefore contain a known number of lines
* The source of the `.minisig` signature is a trusted location, controlled by Phylum, Inc. for it's CLI releases
"""
import base64

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives.asymmetric import ed25519

# This is the Minisign Public Key for Phylum, Inc. The matching private key was used to sign the software releases
PHYLUM_MINISIGN_PUBKEY = "RWT6G44ykbS8GABiLXrJrYsap7FCY77m/Jyi0fgsr/Fsy3oLwU4l0IDf"

# The format for a minisign public key is:
#
# base64(<signature_algorithm> || <key_id> || <public_key>)
#
# signature_algorithm: `Ed`
# key_id: 8 random bytes
# public_key: Ed25519 public key
PHYLUM_MINISIGN_PUBKEY_SIG_ALGO = base64.b64decode(PHYLUM_MINISIGN_PUBKEY)[:2]
PHYLUM_MINISIGN_PUBKEY_KEY_ID = base64.b64decode(PHYLUM_MINISIGN_PUBKEY)[2:10]
PHYLUM_MINISIGN_PUBKEY_ED25519 = base64.b64decode(PHYLUM_MINISIGN_PUBKEY)[10:]


def verify_minisig(file_path, sig_path):
    """Verify a given file has a valid minisign signature.

    `file_path` is the path to the file data to verify.
    `sig_path` is the path to the `.minisig` file containing the minisign signature information.

    The public key is an assumed constant, the Minisign Public Key for Phylum, Inc.
    """
    try:
        phylum_public_key = ed25519.Ed25519PublicKey.from_public_bytes(PHYLUM_MINISIGN_PUBKEY_ED25519)
    except UnsupportedAlgorithm as err:
        raise RuntimeError("Ed25519 algorithm is not supported by the OpenSSL version `cryptography` is using") from err

    signature_algorithm, key_id, signature, trusted_comment, global_signature = extract_minisig_elements(sig_path)

    if signature_algorithm != b"Ed":
        raise RuntimeError("Only the legacy `Ed` signature algorithm is used by Phylum currently")

    if key_id != PHYLUM_MINISIGN_PUBKEY_KEY_ID:
        raise RuntimeError("The `key_id` from the `.minisig` signature did not match the `key_id` from the public key")

    # Confirm the trusted comment in the sig_path with the `global_signature` there
    try:
        phylum_public_key.verify(global_signature, signature + trusted_comment)
    except InvalidSignature as err:
        raise RuntimeError("The signature could not be verified") from err

    # Confirm the data from file_path with the signature from the .minisig `sig_path`
    with open(file_path, "rb") as f:
        file_data = f.read()
    try:
        phylum_public_key.verify(signature, file_data)
    except InvalidSignature as err:
        raise RuntimeError("The signature could not be verified") from err


def extract_minisig_elements(sig_path):
    """Extract the elements from a given minisig signature file and return them."""
    # The format for a minisign signature is:
    #
    # untrusted comment: <arbitrary text>
    # base64(<signature_algorithm> || <key_id> || <signature>)
    # trusted_comment: <arbitrary text>
    # base64(<global_signature>)
    #
    # where each line above represents a line from the `.minisig` file and the elements are defined as:
    #
    # signature_algorithm: `Ed` (legacy) or `ED` (hashed)
    # key_id: 8 random bytes, matching the public key
    # signature (legacy): ed25519(<file data>)
    # signature (prehashed): ed25519(Blake2b-512(<file data>))
    # global_signature: ed25519(<signature> || <trusted_comment>)
    trusted_comment_prefix = "trusted comment: "
    trusted_comment_prefix_len = len(trusted_comment_prefix)
    ed25519_signature_len = 64

    with open(sig_path, "rb") as f:
        lines = f.read().splitlines()
    if len(lines) not in (4, 5):
        raise RuntimeError("The .minisig file format expects 4 lines, with an optional blank 5th line")

    decoded_sig_line = base64.b64decode(lines[1])
    signature_algorithm = decoded_sig_line[:2]
    key_id = decoded_sig_line[2:10]
    signature = decoded_sig_line[10:]
    if len(signature) != ed25519_signature_len:
        raise RuntimeError(f"The decoded signature was not {ed25519_signature_len} bytes long")

    trusted_comment = lines[2][trusted_comment_prefix_len:]

    global_signature = base64.b64decode(lines[3])
    if len(global_signature) != ed25519_signature_len:
        raise RuntimeError(f"The global signature was not {ed25519_signature_len} bytes long")

    return signature_algorithm, key_id, signature, trusted_comment, global_signature
