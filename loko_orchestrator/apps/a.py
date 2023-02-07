import asyncio
import inspect
import logging
import time
from functools import wraps
from io import StringIO

import aiohttp
import requests

from loko_orchestrator.utils import async_request


class TTL:
    def __init__(self, t):
        self.last = time.time()
        self.t = t
        self.__cache = None
        self.is_async = False

    def __call__(self, f):
        self.is_async = inspect.iscoroutinefunction(f)

        @wraps(f)
        async def temp(*args, **kwargs):
            req_time = time.time()
            if (req_time - self.last) > self.t or self.__cache is None:
                self.last = req_time
                self.__cache = f(*args, **kwargs)
                if self.is_async:
                    self.__cache = await self.__cache
            else:
                print("Hitting cache")
            return self.__cache

        return temp


@TTL(t=10)
async def retrieve():
    github_url = "https://api.github.com/orgs/loko-ai/repos"
    all = []

    async with aiohttp.ClientSession() as session:
        for i in range(1, 10):
            async with session.get(github_url, params=dict(per_page=20, page=i)) as resp:
                data = await resp.json()
                print(len(data))
                all.extend(data)
                if len(data) == 0:
                    break
    print("All", len(all))
    return all


# print(inspect.iscoroutinefunction(retrieve))


async def main():
    for i in range(10):
        data = await retrieve()
        print(len(data))
    await asyncio.sleep(10)

    for i in range(10):
        data = await retrieve()
        print(len(data))


asyncio.run(main())
