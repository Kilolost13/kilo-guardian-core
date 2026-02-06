"""Admin service functions moved out of server_core.

This includes listing/verifying submissions and HMAC key operations as
well as administrative update operations.
"""

import hashlib
import hmac
import json
import os
from datetime import datetime
from typing import Any, Dict


def list_submissions(submissions_dir: str, limit: int = 50) -> Dict[str, Any]:
    jsonl_path = os.path.join(submissions_dir, "submissions.jsonl")
    out = []
    if not os.path.exists(jsonl_path):
        return {"total": 0, "submissions": []}
    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            lines = f.readlines()[-limit:]
            for ln in lines:
                try:
                    out.append(json.loads(ln))
                except Exception:
                    continue
    except Exception as e:
        raise e
    return {"total": len(out), "submissions": out}


def verify_submissions(submissions_dir: str, load_hmac_keys) -> Dict[str, Any]:
    jsonl_path = os.path.join(submissions_dir, "submissions.jsonl")
    results = {"checked": 0, "mismatches": [], "missing_backups": []}
    if not os.path.exists(jsonl_path):
        return results
    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    rec = json.loads(ln)
                except Exception:
                    continue
                results["checked"] += 1
                expected_checksum = rec.get("checksum")
                raw = json.dumps(
                    {
                        k: rec[k]
                        for k in rec
                        if k not in ("checksum", "hmac", "hmac_key_id")
                    },
                    sort_keys=True,
                    ensure_ascii=False,
                )
                actual_checksum = hashlib.sha256(raw.encode("utf-8")).hexdigest()
                if expected_checksum != actual_checksum:
                    results["mismatches"].append(
                        {
                            "record": rec,
                            "expected": expected_checksum,
                            "actual": actual_checksum,
                        }
                    )

                expected_hmac = rec.get("hmac")
                if expected_hmac:
                    verified = False
                    key_id = rec.get("hmac_key_id")
                    store = load_hmac_keys()
                    if key_id and store.get("keys", {}).get(key_id):
                        secret = store["keys"][key_id].get("secret")
                        try:
                            actual_hmac = hmac.new(
                                secret.encode("utf-8"),
                                raw.encode("utf-8"),
                                hashlib.sha256,
                            ).hexdigest()
                            if actual_hmac == expected_hmac:
                                verified = True
                        except Exception:
                            pass
                    if not verified:
                        legacy = os.getenv("HMAC_SECRET") or store.get("legacy_secret")
                        if legacy:
                            try:
                                actual_hmac = hmac.new(
                                    legacy.encode("utf-8"),
                                    raw.encode("utf-8"),
                                    hashlib.sha256,
                                ).hexdigest()
                                if actual_hmac == expected_hmac:
                                    verified = True
                            except Exception:
                                pass
                    if not verified:
                        results["mismatches"].append(
                            {
                                "record": rec,
                                "expected_hmac": expected_hmac,
                                "note": ("HMAC did not verify with available keys"),
                            }
                        )
                checksum_prefix = (expected_checksum or "")[:8]
                matches = [
                    p
                    for p in os.listdir(submissions_dir)
                    if (
                        p.endswith(f"_{checksum_prefix}.json")
                        and f"_{rec.get('tool')}_" in p
                    )
                ]
                if not matches:
                    results["missing_backups"].append(
                        f"*_{rec.get('tool')}_{checksum_prefix}.json"
                    )
    except Exception as e:
        raise e
    return results


def hmac_keys(load_hmac_keys) -> Dict[str, Any]:
    store = load_hmac_keys()
    keys_items = store.get("keys", {}).items()
    key_map = {k: {"created": v.get("created")} for k, v in keys_items}
    return {"current": store.get("current"), "keys": key_map}


def hmac_rotate(add_hmac_key, submissions_dir: str, req) -> Dict[str, Any]:
    new_secret = req.new_secret or os.getenv("HMAC_SECRET")
    if not new_secret:
        raise ValueError("new_secret must be provided in body or HMAC_SECRET env var")
    kid = add_hmac_key(new_secret, set_current=True)
    if req.re_sign:
        jsonl_path = os.path.join(submissions_dir, "submissions.jsonl")
        if not os.path.exists(jsonl_path):
            return {
                "ok": True,
                "kid": kid,
                "message": "Key rotated; no submissions to re-sign",
            }
        updated_lines = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                rec = json.loads(ln)
                raw = json.dumps(
                    {
                        k: rec[k]
                        for k in rec
                        if k not in ("checksum", "hmac", "hmac_key_id")
                    },
                    sort_keys=True,
                    ensure_ascii=False,
                )
                checksum = hashlib.sha256(raw.encode("utf-8")).hexdigest()
                rec["checksum"] = checksum
                try:
                    signature = hmac.new(
                        new_secret.encode("utf-8"),
                        raw.encode("utf-8"),
                        hashlib.sha256,
                    ).hexdigest()
                    rec["hmac"] = signature
                    rec["hmac_key_id"] = kid
                except Exception:
                    pass
                backup_filename = (
                    f"{datetime.now().strftime('%Y%m%dT%H%M%S')}_"
                    f"{rec.get('tool')}_{checksum[:8]}.json"
                )
                backup_path = os.path.join(submissions_dir, backup_filename)
                try:
                    with open(backup_path, "w", encoding="utf-8") as bf:
                        bf.write(json.dumps(rec, ensure_ascii=False, indent=2))
                except Exception:
                    pass
                updated_lines.append(json.dumps(rec, ensure_ascii=False))
        try:
            with open(jsonl_path, "w", encoding="utf-8") as f:
                f.write("\n".join(updated_lines) + "\n")
        except Exception:
            pass
    return {"ok": True, "kid": kid, "message": "HMAC key rotated"}
