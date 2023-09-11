import json

from loguru import logger

# from loko_orchestrator.config import app_config
from loko_orchestrator.config.constants import PUBLIC_FOLDER
from loko_orchestrator.dao.fs import FSDao, LayeredFS
from loko_orchestrator.model.components import Component
from loko_orchestrator.business.engine import Fun, AsyncFun, repository, RespAcc, HttpResponseFun, ProcessorError, \
    HTTPRouteProcessor
from loko_orchestrator.utils import async_request
from pathlib import Path
# from loko_orchestrator.config.app_config import fsdao
from loko_orchestrator.resources.doc_http_component import request_doc, route_doc, template_doc, response_doc


class HTTPReq(Component):
    def __init__(self):
        args = [{
            "type": "text",
            "name": "url",
            "label": "URL",
            "validation": {
                "required": "Required field",
            }
        },
            {
                "name": "method",
                "label": "Method",
                "type": "select",
                "options": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                "validation": {
                    "required": "Required field",
                }
            },
            {
                "name": "accept",
                "label": "Accept",
                "type": "select",
                "options": ["text", "json", "file"],
                "validation": {
                    "required": "Required field",
                }
            },
            {
                "name": "query",
                "label": "Query params",
                "type": "multiKeyValue",
                "fields": [
                    {
                        "name": "key",
                        "placeholder": "Key",
                        "validation": {
                            "required": "Required field",
                        }
                    },
                    {
                        "name": "value",
                        "placeholder": "Value",
                        "validation": {
                            "required": "Required field",
                        }
                    }
                ],
            }]

        super().__init__("HTTP Request", group="HTTP", description=request_doc, args=args, click="Launch request",
                         icon="RiUploadCloud2Fill", values={"method": "GET"})

    def create(self, url, method, accept="json", query=None, headers=None, session=None, **kwargs):

        """if not url.startswith(app_config.EXTERNAL_GATEWAY):
            headers = dict()"""
        headers = headers or dict()
        fs_dao = FSDao(PUBLIC_FOLDER, lambda x: x.suffix == ".metadata")
        fsdao = LayeredFS()
        fsdao.mount("data", fs_dao)

        async def req(value, url=url, method=method, accept=accept, query=query):
            query = query or dict()
            query = {el["key"]: el["value"] for el in query}
            logger.debug(f"http req {value}")
            if isinstance(value, Path):
                with fsdao.get(value, 'rb') as inp:
                    files = dict(file=inp)
                    return await async_request.request(url, session=session, method=method, accept=accept, data=files,
                                                       params=query,
                                                       headers=headers)
            if method in ("POST", "PUT"):
                return await async_request.request(url, session=session, method=method, accept=accept, json=value,
                                                   params=query,
                                                   headers=headers)
            else:
                return await async_request.request(url, session=session, method=method, accept=accept, params=query,
                                                   headers=headers)

        return AsyncFun(req, **kwargs)


class HTTPRoute(Component):
    def __init__(self):
        args = []
        args.append({"name": "path", "type": "path", "helper": "Insert a path without '/' at start"}, )
        args.append(dict(name="args", type="text"))
        super().__init__("Route", group="HTTP", description=route_doc, args=args, inputs=[], outputs=['output', 'args'],
                         icon="RiCloudyFill")

    def create(self, path, args, **kwargs):
        # def f(v):
        #    return v

        # ret = Fun(f, **kwargs)
        if args is not None:
            args = [x.strip() for x in args.split(",")]
        ret = HTTPRouteProcessor(args, **kwargs)
        ret.http = True
        ret.path = path
        return ret


class HTTPResponse(Component):
    def __init__(self):
        args = [dict(name="type", type="select", options=["html", "json"], label="Response Type",
                     validation={"required": "Required field"})]
        super().__init__("Response", group="HTTP", description=response_doc, args=args, outputs=[],
                         icon="RiDownloadCloud2Fill")

    def create(self, type, **kwargs):
        return HttpResponseFun(type, **kwargs)
