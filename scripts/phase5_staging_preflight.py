"""Check whether hosted staging can run. Never print secret values."""
import os
import sys

REQUIRED = ("SUPABASE_DB_URL", "SUPABASE_STORAGE_URL", "SUPABASE_STORAGE_KEY")
PRODUCTION_MARKERS = ("prod", "production", "live")


def main() -> None:
    present = [name for name in REQUIRED if os.environ.get(name)]
    missing = [name for name in REQUIRED if name not in present]
    target = os.environ.get("PHASE3_ENVIRONMENT", "local")
    if any(marker in target.lower() for marker in PRODUCTION_MARKERS):
        print("refused: Phase 5 will not migrate or seed a production-designated target")
        sys.exit(2)
    if missing:
        print("hosted staging externally blocked")
        print("missing secret names: " + ", ".join(missing))
        print("local PostgreSQL and the storage abstraction remain the Phase 5 proof")
        return
    print("hosted staging secret names are present; values were not printed")


if __name__ == "__main__":
    main()
