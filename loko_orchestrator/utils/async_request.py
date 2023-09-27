import asyncio
import json

from aiohttp import ClientSession, ClientTimeout
import ast

from loguru import logger

from loko_orchestrator.config.constants import streams
# from loko_orchestrator.config.app_config import ASYNC_SESSION_TIMEOUT
from loko_orchestrator.utils.config_utils import guess_convert


class AsyncRequest:
    def __init__(self, url, method='GET', accept='json', eval=True, **kwargs):
        self.url = url
        self.method = method
        self.accept = accept
        self.eval = eval
        self.kwargs = kwargs


class Temp:
    def __init__(self, resp):
        self.resp = resp
        self.stopped = False

    async def __call__(self):
        async for line in self.resp.content:
            if self.stopped:
                break
            yield json.loads(line)
        self.resp.release()
        self.resp.close()
        logger.debug(self.resp.closed)


async def request(url, session: ClientSession, method="GET", accept="json", **kwargs):
    # session = ClientSession(timeout=ClientTimeout(total=1000))
    # async with ClientSession(timeout=ClientTimeout(total=1000)) as session:
    resp = await session.request(method=method, url=url, **kwargs)

    if resp.content_type == "application/jsonl":
        ret = Temp(resp)
        streams.append(ret)
        return ret()
    if resp.content_type == "text/html":
        return await resp.text()

    if resp.content_type != "application/json":
        return await resp.read()
    if resp.status != 200:
        raise Exception((await resp.text()).strip('"'))
    if accept == "json":
        """if resp.headers.get('Transfer-Encoding') == 'chunked':
            resp = await resp.content.read()
            return guess_convert(resp.decode())"""
        return await resp.json()
    if accept == "file":
        return await resp.read()
    resp = await resp.text()
    return guess_convert(resp)
    # except Exception as inst:
    #     logging.exception(inst)
