"""
Validate roles.yaml structure for PersonaOCEAN.

Checks:
- Top-level 'roles' exists and is a mapping
- Each role has 'pattern', 'dept', 'desc'
- Pattern contains exactly keys O,C,E,A,N with numeric weights in [-1.0, 1.0]
- Warns on obviously odd values (like all zeros)

Usage:
  python validate_roles.py
"""
from __future__ import annotations
import sys
import math
from pathlib import Path
import yaml

ROLES_FILE = Path(__file__).with_name("roles.yaml")

REQUIRED_KEYS = {"O", "C", "E", "A", "N"}


def is_number(x) -> bool:
    try:
        float(x)
        return True
    except Exception:
        return False


def validate_roles(path: Path) -> int:
    if not path.exists():
        print(f"❌ roles file not found: {path}")
        return 1

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "roles" not in data or not isinstance(data["roles"], dict):
        print("❌ roles.yaml must contain a top-level 'roles' mapping")
        return 1

    roles = data["roles"]
    if not roles:
        print("❌ roles.yaml contains no roles")
        return 1

    errors = 0
    warnings = 0

    for name, meta in roles.items():
        if not isinstance(meta, dict):
            print(f"❌ Role '{name}' must be a mapping")
            errors += 1
            continue
        for req in ("pattern", "dept", "desc"):
            if req not in meta:
                print(f"❌ Role '{name}' missing key: {req}")
                errors += 1
        pattern = meta.get("pattern", {})
        if not isinstance(pattern, dict):
            print(f"❌ Role '{name}' pattern must be a mapping")
            errors += 1
            continue
        keys = set(pattern.keys())
        if keys != REQUIRED_KEYS:
            print(f"❌ Role '{name}' pattern keys must be exactly {sorted(REQUIRED_KEYS)}, got {sorted(keys)}")
            errors += 1
        # validate weights
        for k in REQUIRED_KEYS:
            v = pattern.get(k)
            if not is_number(v):
                print(f"❌ Role '{name}' pattern '{k}' must be a number, got {type(v).__name__}")
                errors += 1
                continue
            vf = float(v)
            if vf < -1.0 or vf > 1.0:
                print(f"❌ Role '{name}' pattern '{k}' out of range [-1,1]: {vf}")
                errors += 1
        # warn: all zeros
        if all(float(pattern.get(k, 0)) == 0.0 for k in REQUIRED_KEYS):
            print(f"⚠️  Role '{name}' has all-zero weights; it will never match.")
            warnings += 1

    if errors == 0:
        print("✅ roles.yaml validation passed")
        if warnings:
            print(f"ℹ️  Completed with {warnings} warning(s)")
        return 0
    else:
        print(f"❌ Validation failed with {errors} error(s) and {warnings} warning(s)")
        return 2


if __name__ == "__main__":
    sys.exit(validate_roles(ROLES_FILE))
