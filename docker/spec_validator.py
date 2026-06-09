"""Validates specs/all_modules.yaml against NestAI module contracts.
Exits 0 on success, 1 on any violation.
"""
import sys

import yaml

REQUIRED_MODULE_FIELDS = {"description", "tables", "endpoints"}
REQUIRED_ENDPOINT_FIELDS = {"method", "path", "status"}
VALID_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}", file=sys.stderr)
    sys.exit(1)


def warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def main() -> None:
    try:
        with open("/specs/all_modules.yaml") as f:
            spec = yaml.safe_load(f)
    except FileNotFoundError:
        fail("specs/all_modules.yaml not found")
    except yaml.YAMLError as e:
        fail(f"YAML parse error: {e}")

    if "modules" not in spec:
        fail("Missing top-level 'modules' key")

    all_tables: dict[str, str] = {}  # table -> module that owns it
    errors: list[str] = []

    for mod_name, mod in spec["modules"].items():
        if not isinstance(mod, dict):
            errors.append(f"Module '{mod_name}' is not a mapping")
            continue

        # Required fields
        missing = REQUIRED_MODULE_FIELDS - mod.keys()
        if missing:
            errors.append(f"Module '{mod_name}' missing fields: {missing}")

        # Table uniqueness
        for table in mod.get("tables", []):
            if table in all_tables:
                errors.append(
                    f"Table '{table}' claimed by both '{all_tables[table]}' and '{mod_name}'"
                )
            else:
                all_tables[table] = mod_name

        # Endpoint shape (only for active modules)
        if mod.get("status", "active").startswith("pending"):
            continue

        for i, ep in enumerate(mod.get("endpoints", [])):
            if not isinstance(ep, dict):
                errors.append(f"Module '{mod_name}' endpoint[{i}] is not a mapping")
                continue
            missing_ep = REQUIRED_ENDPOINT_FIELDS - ep.keys()
            if missing_ep:
                errors.append(
                    f"Module '{mod_name}' endpoint[{i}] ({ep.get('path', '?')}) "
                    f"missing fields: {missing_ep}"
                )
            method = ep.get("method", "").upper()
            if method and method not in VALID_METHODS:
                errors.append(
                    f"Module '{mod_name}' endpoint '{ep.get('path')}' "
                    f"has invalid method '{method}'"
                )

    if errors:
        for e in errors:
            print(f"[FAIL] {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[OK] specs/all_modules.yaml — {len(spec['modules'])} modules, "
          f"{len(all_tables)} tables validated")


if __name__ == "__main__":
    main()
