
import json
import logging
import os
from datetime import timedelta
from typing import Any, Callable, Optional
from fastapi import BackgroundTasks

from fastapi.encoders import jsonable_encoder
from redis import Redis

CACHE_KEY_PREFIX = 'agg-api'

REDIS = Redis(host=os.environ['REDIS_HOST'], port=6379)


def redis_get(cache_key: str,
              parse: Callable[[dict], Any],
              default: Any = None) -> Any:
    key = _format_cache_key(cache_key)

    # get from cache
    cached = REDIS.get(key)
    if cached:
        json_ = json.loads(cached)
        return parse(json_)

    return default


def redis_set(cache_key: str,
              obj: Any,
              cache_ttl: timedelta):
    key = _format_cache_key(cache_key)

    serialized = json.dumps(jsonable_encoder(obj))

    REDIS.setex(key,
                cache_ttl,
                serialized)


def redis_get_or_set_cache(cache_key: str,
                           cache_ttl: timedelta,
                           task: Callable[[], Any],
                           parse: Callable[[dict], Any],
                           lock_ttl: timedelta = timedelta(seconds=5),
                           deferred=False,
                           background_tasks: Optional[BackgroundTasks] = None):
    from_cache = redis_get(cache_key,
                           parse)
    if from_cache:
        return from_cache

    # or try to lock for update
    lock_key = _format_lock_key(cache_key)
    lock = REDIS.lock(lock_key, timeout=lock_ttl.total_seconds())
    if not lock.acquire(blocking=False):
        # already locked, return "previously" known value
        return _get_prev(cache_key, parse)

    def _do_task_and_update_cache():
        body = task()

        # update cache
        redis_set(cache_key,
                  body,
                  cache_ttl)
        _set_prev(cache_key, body)

        return body

    try:
        if deferred:
            body = _get_prev(cache_key, parse)
            if body:
                background_tasks.add_task(_do_task_and_update_cache)
            else:
                body = _do_task_and_update_cache()
        else:
            body = _do_task_and_update_cache()

    finally:
        # release lock
        try:
            lock.release()
        except:
            pass

    return body


def redis_lock_and_do(key: str,
                      task: Callable[[], Any],
                      task_ttl: timedelta,
                      lock_ttl: timedelta):
    """
    Run a concurrent task.

    Task must be executed only if not execution recently (+task_ttl+)
    """

    lock_key = _format_cache_key(f'{key}_lock')

    lock = REDIS.lock(lock_key, timeout=lock_ttl.total_seconds())

    if lock.acquire(blocking=False):
        try:

            task_key = _format_cache_key(f'{key}')
            if REDIS.get(task_key):
                logging.info(f'Task {key} executed recently -> skip')
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
        logging.info(f'could not get lock for {key} -> skip')


def _format_cache_key(key: str) -> str:
    return f'{CACHE_KEY_PREFIX}::{key}'


def _format_lock_key(key: str) -> str:
    return _format_cache_key(f'{key}_lock')


def _format_cache_key_prev(key: str) -> str:
    return _format_cache_key(f'{key}_prev')


def _get_prev(key: str,
              parse: Callable[[dict], Any]) -> Optional[Any]:
    key_prev = _format_cache_key_prev(key)

    from_cache = REDIS.get(key_prev)
    if from_cache:
        json_ = json.loads(from_cache)
        return parse(json_)

    return None


def _set_prev(key: str,
              value: Any):
    key_prev = _format_cache_key_prev(key)

    REDIS.setex(key_prev,
                timedelta(hours=1),
                json.dumps(jsonable_encoder(value)))
