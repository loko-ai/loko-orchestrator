from aiodocker import Docker
from sanic import HTTPResponse
from sanic_openapi.openapi2 import doc

from loko_orchestrator.business.builder.aio_docker_builder import build_extension_image, run_extension_image, run_sides
from loko_orchestrator.business.builder.dockermanager import DockerManager
from loko_orchestrator.business.docker_ext import LokoDockerClient, deploy, undeploy
from loko_orchestrator.business.log_collector import LogCollector
from loko_orchestrator.config.app_config import shared_extensions_dao, pdao
import time

from loko_orchestrator.config.constants import GATEWAY
from loko_orchestrator.utils.jsonutils import GenericJsonEncoder
from loko_orchestrator.utils.sio_utils import emit
import json


def myjson(o, headers=None):
    # print(headers)
    return HTTPResponse(json.dumps(o, default=GenericJsonEncoder().default), content_type="application/json",
                        headers=headers)


def add_deployment_services(app, bp, sio):
    @bp.get("/shared/extensions")
    async def shared_extensions(request):
        ret = []
        for el in shared_extensions_dao.all():
            ret.append(dict(name=el, status=await shared_extensions_dao.status(el)))
        return myjson(ret)

    @bp.delete("/shared/extensions/<id>")
    async def shared_extensions(request, id):
        shared_extensions_dao.delete(id)
        return myjson(f"Extension {id} uninstalled")

    @bp.post("/shared/extensions/deploy/<id>")
    async def deploy_shared_extension(request, id):
        if await shared_extensions_dao.status(id) != "running":
            await shared_extensions_dao.deploy(id)
            await run_sides(shared_extensions_dao.path / id, GATEWAY)
        else:
            print("Undeploying")
            await shared_extensions_dao.undeploy(id)

        await emit(sio, "project", time.time())
        return myjson(f"{id} deployed")

    @bp.get("/deploy/<id>")
    @doc.consumes(doc.String(name="id"), location="path", required=True)
    async def build(request, id):
        """print("Deploying", id, pdao.deployed.get(id, False))
        docker_manager: DockerManager = app.ctx.docker_manager
        if pdao.deployed.get(id, False):
            pdao.undeploy(id)
        else:
            if pdao.has_extensions(id):
                res = await docker_manager.build_extension_image(pdao.path / id)
                if res:
                    await run_extension_image(id, GATEWAY)
                    await run_sides(pdao.path / id, GATEWAY)
            pdao.deploy(id)
        return myjson(True)"""
        if pdao.has_extensions(id):
            client: LokoDockerClient = app.ctx.client
            log_collector: LogCollector = app.ctx.log_collector
            await deploy(pdao.path / id, client, log_collector)
        return myjson(True)

    @bp.get("/undeploy/<id>")
    @doc.consumes(doc.String(name="id"), location="path", required=True)
    async def project_undeploy(request, id):
        """client: Docker = app.ctx.client
        try:
            print("Cerco", id)
            cont = await client.containers.get(id)
            print("Killo", id)
            await cont.kill()
        except Exception as inst:
            print(id, inst)
        for el in await client.containers.list(filters={"label": [f"type={id}_side"]}):
            print(el)
            try:
                await el.kill()
            except Exception as inst:
                print(id, inst)
        pdao.undeploy(id)"""
        if pdao.has_extensions(id):
            client: LokoDockerClient = app.ctx.client
            log_collector: LogCollector = app.ctx.log_collector
            await undeploy(pdao.path / id, client, log_collector)

        return myjson(False)

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
        if pdao.has_extensions(id):
            client: LokoDockerClient = app.ctx.client
            return myjson(await client.get_status(id))
        else:
            return myjson(False)
