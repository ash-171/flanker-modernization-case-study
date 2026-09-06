#!/usr/bin/env python3
"""
A short, readable tour of what `flanker` actually does: parse messy email
addresses, walk a real MIME message, and score a bounce.

Framework-free and deterministic on purpose -- the *same* script runs against
the pristine library and the modernized one, and its stdout is byte-identical
(see demo-both.sh). The "which install is this" line goes to stderr so it does
not perturb that comparison.

Usage:
    python demo.py <path/to/flanker/tests/fixtures>
"""

import hashlib
import os
import sys
import time

# Set DEMO_SLOW=1 to pace the output for a screen recording; unset it (the
# default) for normal runs and for the byte-for-byte comparison in demo-both.sh.
_SLOW = float(os.environ.get("DEMO_SLOW") or 0)


def rule(title):
    if _SLOW:
        time.sleep(_SLOW)
    print("\n" + title)
    print("-" * len(title))


def sha(x):
    if isinstance(x, str):
        x = x.encode("utf-8", "surrogatepass")
    return hashlib.sha256(x).hexdigest()


def main(fixtures):
    import flanker
    from flanker.addresslib import address
    from flanker import mime

    print(f"flanker loaded from: {os.path.dirname(flanker.__file__)}", file=sys.stderr)
    print(f"python: {sys.version.split()[0]}", file=sys.stderr)

    # ------------------------------------------------------------------ addresses
    rule("1. Address list -- split and normalize")
    raw = '"Alice K." <ALICE@Example.COM>, torvalds@kernel.org, bob@marley.example'
    print("  parse_list of:")
    print(f"    {raw}")
    print("  ->")
    for a in address.parse_list(raw):
        print(f"    - {str(a):28}  host={a.hostname}")

    rule("2. One address with a comma in the display name")
    a = address.parse('"Bob, Jr." <BOB@Example.COM>')
    print(f"  input       : \"Bob, Jr.\" <BOB@Example.COM>")
    print(f"  display_name: {a.display_name}")
    print(f"  address     : {a.address}          (host lower-cased, local part kept)")
    print(f"  full_spec() : {a.full_spec()}")

    rule("3. Internationalized address -> punycode (IDNA)")
    a = address.parse("Алиса <alice@почта.рф>")
    print(f"  to_unicode() : {a.to_unicode()}")
    print(f"  address      : {a.address}")
    print(f"  ace_address  : {a.ace_address}")

    rule("4. Reject junk")
    for bad in ("not an email", "@nope", "a b c"):
        print(f"  parse({bad!r}) -> {address.parse(bad)!r}")

    # ----------------------------------------------------------------------- MIME
    rule("5. MIME message -- structure, attachment, round-trip")
    eml = open(os.path.join(fixtures, "messages", "attached-pdf.eml"), "rb").read()
    m = mime.from_string(eml)
    print(f"  subject     : {m.subject}")
    print(f"  content_type: {m.content_type}")
    print(f"  part tree   :")
    for p in m.walk(with_self=True):
        tag = f"  <- attachment: {p.detected_file_name}" if p.is_attachment() else ""
        print(f"    {p.content_type}{tag}")
    same = sha(m.to_string()) == sha(eml.decode("utf-8", "surrogatepass")) or sha(m.to_string()) == sha(eml)
    print(f"  to_string() reproduces the original byte-for-byte: {same}")

    # --------------------------------------------------------------------- bounce
    rule("6. Bounce detection")
    b = mime.from_string(open(os.path.join(fixtures, "messages", "bounce", "zed.eml"), "rb").read())
    r = b.bounce
    print(f"  is_bounce()     : {r.is_bounce()}")
    print(f"  score           : {r.score}")
    print(f"  status          : {r.status}")
    print(f"  diagnostic_code : {r.diagnostic_code[:70]}...")

    print()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python demo.py <flanker/tests/fixtures>")
    main(sys.argv[1])
