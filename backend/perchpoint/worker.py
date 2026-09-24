"""One-shot outbox worker. Synthetic delivery only."""
from perchpoint.commands import claim_and_deliver
from perchpoint.settings import Settings


def main() -> None:
    print(claim_and_deliver(Settings.load(), "local-worker"))


if __name__ == "__main__":
    main()
