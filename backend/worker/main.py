from __future__ import annotations

import asyncio
import socket

from backend.core.config import settings
from backend.core.logging import configure_logging
from backend.scheduler import setup_scheduler
from backend.worker.service import process_next_job, update_worker_heartbeat


async def worker_loop() -> None:
    worker_id = f"{socket.gethostname()}:{id(asyncio.current_task())}"
    if settings.scheduler_enabled:
        setup_scheduler()
    heartbeat_tick = 0
    while True:
        heartbeat_tick += 1
        if heartbeat_tick % 4 == 0:
            update_worker_heartbeat(worker_id, "running", {"scheduler_enabled": settings.scheduler_enabled})
        processed = process_next_job()
        if processed is None:
            await asyncio.sleep(2)
        else:
            await asyncio.sleep(0.25)


def main() -> None:
    configure_logging(settings.app_log_path)
    asyncio.run(worker_loop())


if __name__ == "__main__":
    main()
