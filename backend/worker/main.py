from __future__ import annotations

import asyncio

from backend.core.config import settings
from backend.scheduler import setup_scheduler
from backend.worker.service import process_next_job


async def worker_loop() -> None:
    if settings.scheduler_enabled:
        setup_scheduler()
    while True:
        processed = process_next_job()
        if processed is None:
            await asyncio.sleep(2)
        else:
            await asyncio.sleep(0.25)


def main() -> None:
    asyncio.run(worker_loop())


if __name__ == "__main__":
    main()
