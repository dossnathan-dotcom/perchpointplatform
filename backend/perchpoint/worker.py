"""One synthetic outbox claim for the existing worker command. Not an external provider."""
from perchpoint.commands import claim_and_deliver
from perchpoint.settings import Settings


def main() -> None:
    from perchpoint.phase5_closeout import process_document_jobs
    from perchpoint.telemetry import init_sentry

    init_sentry()
    settings = Settings.load()
    print(process_document_jobs(settings))
    print(claim_and_deliver(settings, "phase3-worker"))


if __name__ == "__main__":
    main()
