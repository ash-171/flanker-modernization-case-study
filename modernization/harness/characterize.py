#!/usr/bin/env python3
"""
Characterization ("golden master") harness for flanker.

Exercises flanker's public API over a fixed corpus and writes a single
deterministic JSON document describing every result. Run it against the
baseline install and against the modernized install; the two JSON files
must be byte-identical (see compare.py).

No network, no timestamps, no randomness. Framework-free on purpose so the
same script runs unchanged on the baseline and modern virtualenvs.

Usage:
    python characterize.py --corpus <path/to/flanker/tests/fixtures> --out <file.json>
"""

import argparse
import base64
import hashlib
import io
import json
import os
import sys
import traceback


# --------------------------------------------------------------------------
# serialization helpers
# --------------------------------------------------------------------------

def _sha(b):
    if isinstance(b, str):
        b = b.encode("utf-8", "surrogatepass")
    return hashlib.sha256(b).hexdigest()


def canon(obj, _depth=0):
    """Convert an arbitrary flanker/py object into a JSON-safe, stable form."""
    if _depth > 12:
        return {"__truncated__": True}

    if obj is None or isinstance(obj, (bool, int, float)):
        return obj

    if isinstance(obj, str):
        return obj

    if isinstance(obj, (bytes, bytearray)):
        b = bytes(obj)
        return {"__bytes__": True, "len": len(b), "sha256": _sha(b),
                "head_b64": base64.b64encode(b[:64]).decode("ascii")}

    if isinstance(obj, (list, tuple)):
        return [canon(x, _depth + 1) for x in obj]

    if isinstance(obj, dict):
        return {str(k): canon(v, _depth + 1) for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))}

    # flanker Address / AddressList / MimePart etc. -> structural summary
    cls = type(obj).__name__
    mod = type(obj).__module__

    # AddressList-like (iterable of addresses)
    if cls in ("AddressList", "EmailAddress", "UrlAddress", "Address"):
        return _canon_address(obj, cls, mod)

    if mod.startswith("flanker.mime"):
        return _canon_mime(obj, _depth)

    # generic object: expose a sorted subset of simple public attributes
    out = {"__class__": "%s.%s" % (mod, cls)}
    for name in sorted(dir(obj)):
        if name.startswith("_"):
            continue
        try:
            val = getattr(obj, name)
        except Exception as e:  # noqa: BLE001
            out[name] = {"__attr_error__": "%s: %s" % (type(e).__name__, e)}
            continue
        if callable(val):
            continue
        try:
            out[name] = canon(val, _depth + 1)
        except Exception as e:  # noqa: BLE001
            out[name] = {"__canon_error__": "%s: %s" % (type(e).__name__, e)}
    return out


def _canon_address(obj, cls, mod):
    if cls == "AddressList":
        return {"__class__": "AddressList",
                "len": len(obj),
                "items": [_canon_address(a, type(a).__name__, type(a).__module__) for a in obj]}
    d = {"__class__": cls}
    for name in ("address", "display_name", "hostname", "mailbox",
                 "requires_non_ascii", "supports_routing", "full_spec"):
        try:
            v = getattr(obj, name)
            v = v() if callable(v) else v
            d[name] = canon(v)
        except Exception as e:  # noqa: BLE001
            d[name] = {"__attr_error__": "%s: %s" % (type(e).__name__, e)}
    try:
        d["str"] = str(obj)
    except Exception as e:  # noqa: BLE001
        d["str"] = {"__str_error__": "%s: %s" % (type(e).__name__, e)}
    return d


def _canon_mime(part, _depth):
    d = {"__class__": "MimePart"}
    for name in ("content_type", "content_disposition", "content_encoding",
                 "detected_file_name", "detected_subtype", "detected_content_type",
                 "charset", "is_attachment", "is_inline", "is_body",
                 "is_delivery_notification", "is_bounce"):
        try:
            v = getattr(part, name)
            v = v() if callable(v) else v
            if hasattr(v, "__iter__") and not isinstance(v, (str, bytes)):
                v = list(v)
            d[name] = canon(v, _depth + 1)
        except Exception as e:  # noqa: BLE001
            d[name] = {"__attr_error__": "%s: %s" % (type(e).__name__, e)}

    # headers as an ordered list of pairs
    try:
        d["headers"] = [[canon(k), canon(v, _depth + 1)] for k, v in part.headers.items()]
    except Exception as e:  # noqa: BLE001
        d["headers"] = {"__error__": "%s: %s" % (type(e).__name__, e)}

    # body
    try:
        body = part.body
        d["body"] = canon(body, _depth + 1)
    except Exception as e:  # noqa: BLE001
        d["body"] = {"__error__": "%s: %s" % (type(e).__name__, e)}

    # children
    try:
        parts = list(part.parts)
        d["parts"] = [_canon_mime(p, _depth + 1) for p in parts]
    except Exception as e:  # noqa: BLE001
        d["parts"] = {"__error__": "%s: %s" % (type(e).__name__, e)}
    return d


def guarded(fn):
    """Run fn() and return its canonised result or a canonised exception."""
    try:
        return {"ok": True, "value": canon(fn())}
    except Exception as e:  # noqa: BLE001
        return {"ok": False,
                "error": "%s: %s" % (type(e).__name__, e),
                "trace_tail": traceback.format_exc().strip().splitlines()[-1]}


# --------------------------------------------------------------------------
# corpus loading
# --------------------------------------------------------------------------

def load_lines(path):
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.lstrip().startswith("#"):
                continue
            out.append(line)
    return out


def read_eml(path):
    with open(path, "rb") as f:
        return f.read()


# --------------------------------------------------------------------------
# scenarios
# --------------------------------------------------------------------------

def scenario_address_parse(corpus):
    from flanker.addresslib import address
    files = ["mailbox_valid.txt", "mailbox_invalid.txt",
             "abridged_localpart_valid.txt", "abridged_localpart_invalid.txt"]
    results = {}
    for name in files:
        p = os.path.join(corpus, name)
        if not os.path.exists(p):
            continue
        per_file = []
        for line in load_lines(p):
            per_file.append({
                "input": line,
                "lenient": guarded(lambda l=line: address.parse(l, strict=False)),
                "strict": guarded(lambda l=line: address.parse(l, strict=True)),
            })
        results[name] = per_file
    return results


def scenario_address_parse_list(corpus):
    from flanker.addresslib import address
    cases = [
        "bob@example.com, alice@example.org",
        'Bob <bob@example.com>, "Alice, A" <alice@example.org>',
        "bob@example.com, not-an-address, carol@example.net",
        "bob@example.com; alice@example.org",
        "",
        "   ",
        u"björn@example.com, other@example.org",
        "a@b.com," * 5,
        "<a@b.com>",
        "root@localhost",
    ]
    out = []
    for c in cases:
        out.append({
            "input": c,
            "lenient": guarded(lambda x=c: address.parse_list(x, strict=False)),
            "strict": guarded(lambda x=c: address.parse_list(x, strict=True)),
            "as_tuple_strict": guarded(
                lambda x=c: address.parse_list(x, strict=True, as_tuple=True)),
        })
    return out


def scenario_url_parse(corpus):
    from flanker.addresslib import address
    out = {}
    for name in ("url_valid.txt", "url_invalid.txt"):
        p = os.path.join(corpus, name)
        if not os.path.exists(p):
            continue
        out[name] = [{"input": line, "result": guarded(lambda l=line: address.parse(l))}
                     for line in load_lines(p)]
    return out


def scenario_mime_parse(corpus):
    from flanker import mime
    msgdir = os.path.join(corpus, "messages")
    results = {}
    emls = []
    for root, _dirs, files in os.walk(msgdir):
        for fn in files:
            if fn.endswith(".eml"):
                emls.append(os.path.join(root, fn))
    for path in sorted(emls):
        rel = os.path.relpath(path, msgdir)
        raw = read_eml(path)

        def _do(raw=raw):
            msg = mime.from_string(raw)
            summary = canon(msg)
            # round-trip serialization
            rt = msg.to_string()
            if isinstance(rt, str):
                rt_bytes = rt.encode("utf-8", "surrogatepass")
            else:
                rt_bytes = rt
            summary["__roundtrip__"] = {"len": len(rt_bytes), "sha256": _sha(rt_bytes)}
            return summary

        results[rel] = guarded(_do)
    return results


def scenario_bounce(corpus):
    from flanker import mime
    from flanker.mime.message.headers import parametrized  # noqa: F401
    try:
        from flanker.mime import bounce  # noqa: F401
    except Exception:
        pass
    msgdir = os.path.join(corpus, "messages", "bounce")
    out = {}
    if not os.path.isdir(msgdir):
        return out
    for fn in sorted(os.listdir(msgdir)):
        if not fn.endswith(".eml"):
            continue
        raw = read_eml(os.path.join(msgdir, fn))

        def _do(raw=raw):
            msg = mime.from_string(raw)
            b = msg.bounce
            return {
                "is_bounce": msg.is_bounce(),
                "score": getattr(b, "score", None),
                "status": getattr(b, "status", None),
                "notification": getattr(b, "notification", None),
                "diagnostic_code": getattr(b, "diagnostic_code", None),
            }

        out[fn] = guarded(_do)
    return out


def scenario_headers(corpus):
    from flanker.mime.message.headers import encoding as hdr_encoding
    cases = [
        ("Subject", u"Hello world"),
        ("Subject", u"café – naïve résumé"),
        ("Subject", "A" * 200),
        ("From", u"Björn <bjorn@example.com>"),
        ("To", "a@b.com, c@d.com, e@f.com"),
        ("X-Custom", u"tab\there and  nbsp"),
    ]
    out = []
    for key, val in cases:
        out.append({
            "key": key,
            "value": val,
            "encoded": guarded(lambda k=key, v=val: hdr_encoding.encode(k, v)),
        })
    return out


def scenario_versions():
    import flanker
    info = {
        "python": sys.version.split()[0],
        "python_impl": sys.implementation.name,
        "flanker_version": getattr(flanker, "__version__", None),
    }
    for name in ("six", "webob", "ply", "regex", "chardet", "idna", "tld", "attr"):
        try:
            m = __import__(name)
            info[name] = getattr(m, "__version__", "present")
        except Exception:
            info[name] = None
    return info


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True,
                    help="path to flanker/tests/fixtures")
    ap.add_argument("--out", required=True)
    ap.add_argument("--include-env", action="store_true",
                    help="include interpreter/dependency versions (informational; "
                         "excluded from equivalence comparison by default)")
    args = ap.parse_args()

    document = {
        "schema": 1,
        "address_parse": scenario_address_parse(args.corpus),
        "address_parse_list": scenario_address_parse_list(args.corpus),
        "url_parse": scenario_url_parse(args.corpus),
        "mime_parse": scenario_mime_parse(args.corpus),
        "bounce": scenario_bounce(args.corpus),
        "headers": scenario_headers(args.corpus),
    }
    if args.include_env:
        document["_env"] = scenario_versions()

    with io.open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(document, f, indent=2, sort_keys=True, ensure_ascii=True)
        f.write("\n")

    # tiny console summary
    n_addr = sum(len(v) for v in document["address_parse"].values())
    n_mime = len(document["mime_parse"])
    print("wrote %s  (addresses=%d, eml=%d, bounce=%d)"
          % (args.out, n_addr, n_mime, len(document["bounce"])))


if __name__ == "__main__":
    main()
