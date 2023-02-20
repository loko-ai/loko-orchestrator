import asyncio
import uuid
from pprint import pprint

import aiohttp
from aiodocker import Docker
from loguru import logger
from sanic import HTTPResponse
from sanic_openapi.openapi2 import doc

from loko_orchestrator.business.builder.aio_docker_builder import build_extension_image, run_extension_image, run_sides
from loko_orchestrator.business.builder.dockermanager import DockerManager
from loko_orchestrator.business.docker_ext import LokoDockerClient, deploy, undeploy
from loko_orchestrator.business.log_collector import LogCollector
from loko_orchestrator.config.app_config import shared_extensions_dao, pdao
import time

from loko_orchestrator.config.constants import GATEWAY
from loko_orchestrator.utils.cache_utils import TTL
from loko_orchestrator.utils.jsonutils import GenericJsonEncoder
from loko_orchestrator.utils.sio_utils import emit
import json


def myjson(o, headers=None):
    # print(headers)
    return HTTPResponse(json.dumps(o, default=GenericJsonEncoder().default), content_type="application/json",
                        headers=headers)


github_url = "https://api.github.com/orgs/loko-ai/repos"
default_image = 'https://raw.githubusercontent.com/loko-ai/prova_gui/master/icon.png'
avatar_url = "https://avatars.githubusercontent.com/u/109956019?v=4"


@TTL(t=60 * 10)
async def retrieve_extensions():
    github_url = "https://api.github.com/orgs/loko-ai/repos"
    all = []

    async with aiohttp.ClientSession() as session:
        for i in range(1, 10):
            async with session.get(github_url, params=dict(per_page=100, page=i)) as resp:
                data = await resp.json()
                all.extend(data)
                if len(data) < 100:
                    break

    return all


@TTL(t=20)
async def get_installed():
    return set(shared_extensions_dao.all())


def check_github_project(p):
    print(p)
    return not p['private'] and "extension" in p.get("topics")


def add_deployment_services(app, bp, sio):
    @bp.get("/shared/extensions")
    async def shared_extensions(request):
        ret = []
        client: LokoDockerClient = app.ctx.client
        log_collector: LogCollector = app.ctx.log_collector
        for el in await get_installed():
            guis = await shared_extensions_dao.get_guis(el, client)
            ret.append(dict(name=el, id=el, topics=[], html_url="", image=default_image,
                            owner=dict(login="loko-ai", avatar_url=avatar_url),
                            status=await client.is_deployed(el), guis=guis))
            ret = sorted(ret, key=lambda x: x['name'])
        return myjson(ret)

    @bp.delete("/shared/extensions/<id>")
    async def shared_extensions(request, id):
        shared_extensions_dao.delete(id)
        return myjson(f"Extension {id} uninstalled")

    @bp.get("/shared/extensions/deploy/<id>")
    async def deploy_shared_extension(request, id):
        """if await shared_extensions_dao.status(id) != "running":
            await shared_extensions_dao.deploy(id)
            await run_sides(shared_extensions_dao.path / id, GATEWAY)
        else:
            print("Undeploying")
            await shared_extensions_dao.undeploy(id)

        await emit(sio, "project", time.time())"""
        client: LokoDockerClient = app.ctx.client
        log_collector: LogCollector = app.ctx.log_collector
        print("Deploying", id)
        await deploy(shared_extensions_dao.path / id, client, log_collector)
        await shared_extensions_dao.deploy(id)

        return myjson(True)

    @bp.get("/shared/extensions/undeploy/<id>")
    async def undeploy_shared_extension(request, id):
        client: LokoDockerClient = app.ctx.client
        log_collector: LogCollector = app.ctx.log_collector
        await undeploy(shared_extensions_dao.path / id, client, log_collector)
        await shared_extensions_dao.undeploy(id)
        await sio.emit("events", {})

        return myjson(False)

    @bp.get("/deploy/<id>")
    @doc.consumes(doc.String(name="id"), location="path", required=True)
    async def build(request, id):
        client: LokoDockerClient = app.ctx.client
        log_collector: LogCollector = app.ctx.log_collector
        if pdao.has_extensions(id):
            await deploy(pdao.path / id, client, log_collector)
            guis = await pdao.get_guis(id, client)
            pdao.deploy(id)
            return myjson(dict(status=True, guis=guis))
        else:
            log_collector.add_log(id)
            log_collector.logs[id] = [
                dict(type="log", channel='DEBUG', msg=f"Project '{id}' started. (This project has no local extensions)",
                     log_id=str(uuid.uuid4()))]
            pdao.deploy(id)
            await sio.emit("events", {})
            return myjson(dict(status=True))

    @bp.get("/undeploy/<id>")
    @doc.consumes(doc.String(name="id"), location="path", required=True)
    async def project_undeploy(request, id):
        client: LokoDockerClient = app.ctx.client
        log_collector: LogCollector = app.ctx.log_collector
        if pdao.has_extensions(id):
            pdao.undeploy(id)
            await undeploy(pdao.path / id, client, log_collector)
        else:
            log_collector.remove_log(id)
            pdao.undeploy(id)

        return myjson(dict(status=False))

    @bp.get("/deployment_status/<id>")
    async def status(request, id):
        """client: Docker = app.ctx.client
        log_collector: LogCollector = app.ctx.log_collector
        try:
            print("Cerco", id)
            cont = await client.containers.get(id)
            return myjson(True)
        except Exception as inst:
            print(id, inst)
            pdao.undeploy(id)
            return myjson(False)"""
        client: LokoDockerClient = app.ctx.client
        if pdao.has_extensions(id):

            guis = await pdao.get_guis(id, client)

            return myjson(dict(status=await client.get_status(id), guis=guis))
        else:
            return myjson(dict(status=await pdao.is_deployed(id, client)))

    @bp.get("/applications/installed")
    async def get_installed_applications(request):
        # async with aiohttp.ClientSession() as session:
        #     async with session.get(github_url) as resp:
        #         data = await resp.json()
        #         data = [x for x in data if not x['private']]
        #         await asyncio.gather(*[set_image(x, session) for x in data])
        data = []

        return myjson(data)

    @bp.get("/applications/available")
    async def get_available_applications(request):
        already = await get_installed()
        async with aiohttp.ClientSession() as session:
            # async with session.get(github_url, params=dict(per_page=100)) as resp:
            data = await retrieve_extensions()
            logger.debug(data)
            data = [x for x in data if check_github_project(x) and not x['name'] in already]
            data = sorted(data, key=lambda x: x['name'])
            await asyncio.gather(*[set_image(x, session) for x in data])

        return myjson(data)

    async def set_image(repo, session):
        image_url = f"https://raw.githubusercontent.com/{repo['owner']['login']}/{repo['name']}/master/icon.png"
        async with session.head(image_url) as imresp:
            if imresp.status == 200:
                repo['image'] = image_url
            else:
                repo['image'] = default_image
