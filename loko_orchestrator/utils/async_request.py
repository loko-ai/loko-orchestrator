from aiohttp import ClientSession, ClientTimeout
import ast
# from loko_orchestrator.config.app_config import ASYNC_SESSION_TIMEOUT
from loko_orchestrator.utils.config_utils import guess_convert


class AsyncRequest:
    def __init__(self, url, method='GET', accept='json', eval=True, **kwargs):
        self.url = url
        self.method = method
        self.accept = accept
        self.eval = eval
        self.kwargs = kwargs


async def request(url, method="GET", accept="json", **kwargs):
    async with ClientSession(timeout=ClientTimeout(total=1000)) as session:
        resp = await session.request(method=method, url=url, **kwargs)
        if resp.status != 200:
            raise Exception((await resp.text()).strip('"'))
        if accept == "json":
            if resp.headers.get('Transfer-Encoding') == 'chunked':
                resp = await resp.content.read()
                return guess_convert(resp.decode())
            return await resp.json()
        if accept == "file":
            return await resp.read()
        resp = await resp.text()
        return guess_convert(resp)
    # except Exception as inst:
    #     logging.exception(inst)
