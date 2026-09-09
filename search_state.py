"""Small, bounded caches; failures never overwrite verified evidence.

Memory is an optimization, not durable storage across Vercel instances. The
browser also keeps its own verified observations for continuity within a session.
"""
from collections import OrderedDict
from concurrent.futures import Future
from copy import deepcopy
from threading import RLock
from time import monotonic
from datetime import datetime, timedelta, timezone


class SearchCache:
    def __init__(self, capacity=64):
        self.capacity, self.values, self.pending = capacity, OrderedDict(), {}
        self.lock = RLock()

    def get(self, key):
        with self.lock:
            entry = self.values.get(key)
            if entry and entry[0] > monotonic():
                self.values.move_to_end(key)
                return deepcopy(entry[1])
            self.values.pop(key, None)
        return None

    def put(self, key, value, ttl=300):
        with self.lock:
            self.values[key] = (monotonic() + ttl, deepcopy(value))
            self.values.move_to_end(key)
            while len(self.values) > self.capacity:
                self.values.popitem(last=False)

    def call(self, key, fn, accept=lambda result: True, ttl=300):
        with self.lock:
            cached = self.get(key)
            if cached is not None:
                return cached
            owner = key not in self.pending
            future = self.pending.setdefault(key, Future())
        if not owner:
            return deepcopy(future.result())
        try:
            value = fn()
            if accept(value):
                self.put(key, value, ttl)
            future.set_result(value)
            return deepcopy(value)
        except BaseException as error:
            future.set_exception(error)
            raise
        finally:
            with self.lock:
                self.pending.pop(key, None)

    def clear(self):
        with self.lock:
            self.values.clear()


queries = SearchCache(64)
verified = SearchCache(1200)
observations = SearchCache(64)


def remember(key, items):
    # Atomic read/merge prevents two periods from overwriting each other's notes.
    with observations.lock:
        previous = observations.get(key) or []
        current = datetime.now(timezone.utc)
        by_url = {item['url']: item for item in previous
                  if datetime.fromisoformat(item['verified_at'].replace('Z', '+00:00')) > current-timedelta(days=1)}
        for item in items:
            by_url[item['url']] = {**item, 'verified_at':item.get('verified_at') or by_url.get(item['url'], {}).get('verified_at') or current.isoformat()}
        result = sorted(by_url.values(), key=lambda i: (i['published'], i['url']), reverse=True)[:300]
        if result:
            observations.put(key, result, ttl=86400)
        return result


def clear():
    for cache in (queries, verified, observations):
        cache.clear()
