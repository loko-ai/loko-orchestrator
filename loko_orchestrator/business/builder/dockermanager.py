import asyncio
import random
import time
from collections import defaultdict
from pathlib import Path

import aiohttp
import requests
from docker.api.build import process_dockerfile
from docker.utils import tar

from loko_orchestrator.business.builder.aio_docker_builder import prepare_docker_ignore
from loko_orchestrator.utils.validators import DictVal, TypeValidator


class Throttle:
    def __init__(self, f, t=0.1):
        self.f = f
        self.task = None
        self.t = t

    async def __call__(self, *args, **kwargs):
        if self.task:
            self.task.cancel()
            self.task = None

        async def temp():
            await asyncio.sleep(self.t)
            await self.f(*args, **kwargs)

        self.task = asyncio.create_task(temp())


class DockerManager:
    def __init__(self, client):
        self.client = client

    async def build_extension_image(self, path):
        async with aiohttp.ClientSession(timeout=300 * 1000) as session:
            client = self.client
            client.session = aiohttp.ClientSession(connector=client.connector, read_timeout=200 * 1000,
                                                   conn_timeout=200 * 1000)

            path = Path(path)
            print("Tarring the file")
            exclude = prepare_docker_ignore(path)
            print("Excludes", exclude)
            context = tar(
                path, exclude=exclude, dockerfile=process_dockerfile("Dockerfile", path), gzip=True
            )
            print("File tarred")

            async for line in client.images.build(fileobj=context,
                                                  encoding="gzip",
                                                  tag=f"{path.name}",
                                                  buildargs=dict(GATEWAY="http://localhost:8080"), stream=True):
                if "stream" in line:
                    msg = line['stream'].strip()
                if msg:
                    print(msg)

    async def run_extension_image(self, id, gw=None):
        client = self.client
        print("Trying to get", id)

        try:
            container = await client.containers.get(id)
            await container.kill()
            while await self.get_status(id):
                await asyncio.sleep(0.5)


        except Exception as inst:
            print("kkk", inst)
        config = dict(Image=id, ExposedPorts={
            '8080/tcp': {},
        }, HostConfig={
            "AutoRemove": True,
            "NetworkMode": 'loko',
        })

        try:
            cont = await client.containers.run(name=id, config=config)
            print("Ora loggo")
            print("Deployed", id)
            if gw:
                resp = requests.post(gw + "/rules", json={
                    "name": id,
                    "host": id,
                    "port": 8080,
                    "type": "custom",
                    "scan": False
                })
        except Exception as inst:
            print(inst)
        print("Routed", id)

    async def get_status(self, id):
        try:
            cont = await self.client.containers.get(id)
            return cont._container["State"]["Status"]
        except:
            return None


async def get_name(cont):
    return (await cont.show())['Name'].replace("/", "")


class DockerMessageCollector:
    def __init__(self, client, sio, app):
        self.logs = defaultdict(list)
        self.dead_logs = {}
        self.events = []
        self.tasks = {}
        self.queue = asyncio.Queue()
        self.client = client
        self.sio = sio
        self.app = app

        async def temp(type):
            await sio.emit(type, {})

        self.notifier = Throttle(temp, t=1)

    async def event_task(self):

        sub = self.client.events.subscribe()
        dv = DictVal(status=TypeValidator(str), Actor=DictVal(Attributes=TypeValidator(dict)))
        while True:
            value = await sub.get()
            if dv(value):
                ret = {}
                ret["status"] = value['status']
                ret["Attributes"] = value['Actor']['Attributes']
                self.events.append(str(ret))
            await self.update_tasks()
            await self.notifier("events")

    async def log_task(self, id, err=False):

        cont = await self.client.containers.get(id)
        name = await get_name(cont)

        async for ev in cont.log(stdout=not err, stderr=err, follow=True):
            self.logs[name].append(str(ev))
            await self.queue.put((name, "ERROR" if err else "DEBUG", ev))

    async def dequeue(self):
        while True:
            id, _type, msg = await self.queue.get()
            self.logs[id].append(dict(type=_type, msg=msg))
            if len(self.logs[id]) > 100:
                self.logs[id].pop(0)
            await self.notifier("logs")

    async def update_tasks(self):
        visited = set()
        for cont in await self.client.containers.list():
            name = await get_name(cont)
            id = cont.id
            if name in self.tasks and self.tasks[name][0] != cont.id:
                self.tasks[name][1].cancel()
                self.tasks[name][2].cancel()

                self.logs[name] = []
                del self.tasks[name]
            if name not in self.tasks:
                task = self.app.add_task(self.log_task(id))
                task2 = self.app.add_task(self.log_task(id, err=True))

                self.tasks[name] = cont.id, task, task2
            visited.add(name)
        for key in list(self.logs.keys()):
            if key not in visited:
                self.tasks[key][1].cancel()
                self.tasks[key][2].cancel()
                self.dead_logs[key] = list(self.logs[key])
                del self.logs[key]
                print("Removing", key)
        await self.notifier("logs")
