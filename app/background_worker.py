"""SAGE ONE durable background worker entry point.

Run with:
    python -m app.background_worker
"""

from app.worker import worker


def main() -> None:
    worker.run_forever()


if __name__ == "__main__":
    main()
