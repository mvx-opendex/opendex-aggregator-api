
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

LOCAL_CACHE = {}


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
                           lock_for_update=True,
                           deferred=False,
                           background_tasks: Optional[BackgroundTasks] = None):
    key = _format_cache_key(cache_key)

    default_value = LOCAL_CACHE.get(key, None)

    # get from cache
    cached = REDIS.get(key)
    if cached:
        json_ = json.loads(cached)
        return parse(json_), False

    # or try to lock for update
    if lock_for_update:
        lock_key = f'{key}_lock'
        lock = REDIS.lock(lock_key, timeout=lock_ttl.total_seconds())
        if not lock.acquire(blocking=False):
            # already locked, return default value
            return default_value, False

    def _do_task_and_update_cache():
        body = task()

        # update cache
        LOCAL_CACHE[key] = body
        REDIS.setex(key, cache_ttl,
                    json.dumps(jsonable_encoder(body)))

        return body

    if deferred and key in LOCAL_CACHE:
        body = LOCAL_CACHE[key]
        background_tasks.add_task(_do_task_and_update_cache)
    else:
        # get value from task return
        body = _do_task_and_update_cache()

    # release lock
    if lock_for_update:
        try:
            lock.release()
        except:
            pass

    return body, True


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
