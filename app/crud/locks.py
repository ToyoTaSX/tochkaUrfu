from contextlib import asynccontextmanager

LOCKS = dict()

@asynccontextmanager
async def acquire_locks(*locks):
    locks = sorted(locks, key=id)
    for lock in locks:
        await lock.acquire()
    try:
        yield
    finally:
        for lock in reversed(locks):
            lock.release()