"""One synthetic outbox claim for the existing worker command. Not an external provider."""
from perchpoint.commands import claim_and_deliver
from perchpoint.settings import Settings


def main() -> None:
    from perchpoint.telemetry import init_sentry

    init_sentry()
    print(claim_and_deliver(Settings.load(), "phase3-worker"))


if __name__ == "__main__":
    main()
