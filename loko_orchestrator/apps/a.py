import asyncio
import inspect
import logging
import time
from functools import wraps
from io import StringIO

import aiohttp
import requests

from loko_orchestrator.utils import async_request
from loko_orchestrator.utils.cache_utils import TTL


@TTL(t=10)
async def retrieve_extensions():
    github_url = "https://api.github.com/orgs/loko-ai/repos"
    all = []

    async with aiohttp.ClientSession() as session:
        for i in range(1, 10):
            async with session.get(github_url, params=dict(per_page=20, page=i)) as resp:
                data = await resp.json()
                all.extend(data)
                if len(data) == 0:
                    break

    return all


# print(inspect.iscoroutinefunction(retrieve))


async def main():
    for i in range(10):
        data = await retrieve_extensions()
        print(len(data))
    await asyncio.sleep(10)

    for i in range(10):
        data = await retrieve_extensions()
        print(len(data))


asyncio.run(main())
