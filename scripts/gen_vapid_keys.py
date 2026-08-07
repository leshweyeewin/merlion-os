"""
scripts/gen_vapid_keys.py — generate a VAPID key pair for Web Push
-----------------------------------------------------------------------------
Web Push needs one server-wide VAPID (ECDSA P-256) key pair: the public key is handed to the
browser as the `applicationServerKey` when it subscribes, and the private key signs the push
requests the server sends. Run this ONCE, paste the two lines into your .env (or Render env), and
keep the private key secret. Rotating the pair invalidates every existing browser subscription.

    python scripts/gen_vapid_keys.py

Prints VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY (base64url) plus a suggested VAPID_SUBJECT.
"""
import base64

from py_vapid import Vapid02
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


def main():
    v = Vapid02()
    v.generate_keys()

    # Public: the uncompressed EC point (0x04 ‖ X ‖ Y) — exactly the applicationServerKey the
    # browser's PushManager.subscribe() expects, base64url without padding.
    public = v._public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    # Private: the raw 32-byte scalar, base64url — the form pywebpush's Vapid.from_string accepts.
    private = v._private_key.private_numbers().private_value.to_bytes(32, "big")

    b64 = lambda b: base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")
    pub_b64, priv_b64 = b64(public), b64(private)

    # Sanity check: the private string must round-trip back through pywebpush's loader.
    Vapid02.from_raw(priv_b64.encode("ascii"))

    print("# --- Web Push VAPID keys — paste into .env (keep the private key secret) ---")
    print(f"VAPID_PUBLIC_KEY={pub_b64}")
    print(f"VAPID_PRIVATE_KEY={priv_b64}")
    print("VAPID_SUBJECT=mailto:you@example.com")


if __name__ == "__main__":
    main()
