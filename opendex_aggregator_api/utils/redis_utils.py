
import json
import logging
import os
from datetime import timedelta
from typing import Any, Callable, Optional

from fastapi.encoders import jsonable_encoder
from redis import Redis

CACHE_KEY_PREFIX = 'agg-api'

REDIS = Redis(host=os.environ['REDIS_HOST'], port=6379)


def redis_get(raw_key: str,
              parse: Callable[[dict], Any],
              default: Any = None) -> Any:
    fmt_key = _format_cache_key(raw_key)

    # get from cache
    cached = REDIS.get(fmt_key)
    if cached:
        json_ = json.loads(cached)
        return parse(json_)

    return default


def redis_set(raw_key: str,
              obj: Any,
              cache_ttl: timedelta):
    fmt_key = _format_cache_key(raw_key)

    serialized = json.dumps(jsonable_encoder(obj))

    REDIS.setex(fmt_key,
                cache_ttl,
                serialized)


def redis_get_or_set_cache(raw_key: str,
                           cache_ttl: timedelta,
                           task: Callable[[], Any],
                           parse: Callable[[dict], Any],
                           lock_ttl: timedelta = timedelta(seconds=5)):
    from_cache = redis_get(raw_key,
                           parse)
    if from_cache:
        return from_cache

    # or try to lock for update
    lock_key = _format_lock_key(raw_key)
    lock = REDIS.lock(lock_key, timeout=lock_ttl.total_seconds())
    if not lock.acquire(blocking=False):
        # already locked, return "previously" known value
        return _get_prev(raw_key, parse)

    def _do_task_and_update_cache():
        body = task()

        # update cache
        redis_set(raw_key,
                  body,
                  cache_ttl)
        _set_prev(raw_key, body)

        return body

    try:
        body = _do_task_and_update_cache()

    finally:
        # release lock
        try:
            lock.release()
        except:
            pass

    return body


def redis_lock_and_do(raw_key: str,
                      task: Callable[[], Any],
                      task_ttl: timedelta,
                      lock_ttl: timedelta):
    """
    Run a concurrent task.

    Task must be executed only if not execution recently (+task_ttl+)
    """

    lock_key = _format_cache_key(f'{raw_key}_lock')

    lock = REDIS.lock(lock_key, timeout=lock_ttl.total_seconds())

    if lock.acquire(blocking=False):
        try:

            task_key = _format_cache_key(raw_key)
            if REDIS.get(task_key):
                logging.info(f'Task {raw_key} executed recently -> skip')
                return

            task()

            REDIS.setex(task_key,
                        task_ttl,
                        'DONE')
        finally:
            try:
                lock.release()
            except:
                pass
    else:
        logging.info(f'could not get lock for {raw_key} -> skip')


def _format_cache_key(raw_key: str) -> str:
    return f'{CACHE_KEY_PREFIX}::{raw_key}'


def _format_lock_key(raw_key: str) -> str:
    return _format_cache_key(f'{raw_key}_lock')


def _format_cache_key_prev(raw_key: str) -> str:
    return _format_cache_key(f'{raw_key}_prev')


def _get_prev(raw_key: str,
              parse: Callable[[dict], Any]) -> Optional[Any]:
    key_prev = _format_cache_key_prev(raw_key)

    from_cache = REDIS.get(key_prev)
    if from_cache:
        json_ = json.loads(from_cache)
        return parse(json_)

    return None


def _set_prev(raw_key: str,
              value: Any):
    key_prev = _format_cache_key_prev(raw_key)

    REDIS.setex(key_prev,
                timedelta(hours=1),
                json.dumps(jsonable_encoder(value)))
