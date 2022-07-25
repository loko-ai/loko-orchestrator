import asyncio
import concurrent
import datetime
import io
import os
import pathlib
import re
import sys
import traceback
import warnings

from aiohttp import ClientSession, ClientTimeout
from collections import defaultdict
from io import BytesIO, StringIO
from pathlib import Path
import csv
import random
import time
from types import GeneratorType
import json

from loko_orchestrator.utils.async_request import AsyncRequest
from loko_orchestrator.utils.codeutils import flatten
from loko_orchestrator.utils.debug_utils import ellipsis
from loko_orchestrator.utils.logger_utils import logger
# from ds4biz_orchestrator.utils.pathutils import to_relative
from loko_orchestrator.utils.jsonutils import json_friendly, IDDict
from uuid import uuid4
from contextvars import ContextVar
import logging
import itertools
from contextvars_executor import ContextVarExecutor

from loko_orchestrator.utils.sio_utils import emit

CHOKE = "CHOKE"
repository = ContextVar('repo', default={})

workers = 8
# executor = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
executor = ContextVarExecutor(max_workers=workers)


class Repository:
    def __init__(self, repository):
        self.repository = repository

    def get(self, k):
        return self.repository.get()[k]

    def set(self, k, v):
        self.repository.get()[k] = v


class Parameters(dict):
    pass


class RespAcc:
    def __init__(self, data=None, type="json", status=200):
        self.status = status
        self.data = data or []
        self.type = type

    def append(self, el):
        self.data.append(el)

    def __getitem__(self, k):
        return getattr(self, k)


def update_parameters(f):
    def update(self, *args, **kwargs):
        value = args[0]
        if not isinstance(value, Parameters):
            return f(self, *args, **kwargs)

        vv = value.copy()
        v = vv.pop('data')
        self.__dict__.update(vv)
        args = args[1:]
        return f(self, v, *args, **kwargs)

    return update


def update_mf_parameters(f):
    def update(self, *args, **kwargs):
        value = args[0]
        if not isinstance(value, Parameters):
            return f(self, *args, **kwargs)
        vv = value.copy()
        v = vv.pop('data')
        kwargs.update(vv)
        args = args[1:]
        return f(self, v, *args, **kwargs)

    return update


async def notify_warnings(self, w):
    while w:
        ww = w.pop(0)
        ww.lineno = ww.lineno - 1
        msg = f'{ww._category_name} line {ww.lineno}: {ww.message}'
        m = ProcessorError(msg, self.name)
        await self.notify(m)
    return w


class ProcessorError:
    def __init__(self, msg, component_name, source_id=None):
        self.msg = msg
        self.component_name = component_name
        self.source_id = source_id

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return str(self.__dict__)


class Processor:

    def __init__(self, id=None, propagate=True, name=None, debug=False, **kwargs):
        self.id = id or str(uuid4())
        self.pipes = IDDict(list)
        self.propagate = propagate
        self.name = name

    async def notify(self, value, output="output"):
        res = await asyncio.gather(*[p.consume(value, input) for (input, p) in self.pipes[output]])
        for el in res:
            if el == CHOKE:
                return CHOKE

    def piped_from(self, processor, output="output", input="input"):
        pass

    def pipe(self, processor, output="output", input="input"):
        self.pipes[output].append((input, processor))
        processor.piped_from(self, output, input)
        return processor

    async def process(self, value, input="input", **kwargs):
        pass

    async def flush(self, input="input"):
        # print(self.name)
        # print('INPUT::', input)
        # for k,v in self.pipes.items():
        #     print(k)
        #     for vv in v:
        #         print(vv[0], vv[1].__class__.__name__)
        #     print()
        ret = []
        for v in self.pipes.values():
            ret.extend([x[1].flush(x[0]) for x in v])
        await asyncio.gather(*ret)

    async def end(self, input="input"):
        # print(self.name)
        # print('INPUT::', input)
        # for k,v in self.pipes.items():
        #     print(k)
        #     for vv in v:
        #         print(vv[0], vv[1].__class__.__name__)
        #     print()
        ret = []
        for v in self.pipes.values():
            ret.extend([x[1].end(x[0]) for x in v])
        await asyncio.gather(*ret)

    async def consume(self, value, input="input", flush=False, output="output", **kwargs):
        ret = None
        if isinstance(value, ProcessorError):
            await self.notify(value)
        else:
            try:
                ret = await self.process(value, input, **kwargs)
            except Exception as inst:
                logger.debug(traceback.format_exc())
                logging.exception(inst)
                await self.notify(ProcessorError(str(inst), self.name, self.id), output=output)
            if flush:
                await self.end(input=input)
        return ret

    async def preview(self):
        return "No preview available"

    def run(self, value, input="input", loop=None):
        loop = loop or asyncio.get_event_loop()
        loop.run_until_complete(self.consume(value, input))
        loop.close()


class Constant(Processor):
    def __init__(self, value, **kwargs):
        super().__init__(**kwargs)
        self.value = value

    async def process(self, value, input="input", **kwargs):
        await self.notify(self.value)


class Fun(Processor):
    def __init__(self, f, notify_warnings=False, **kwargs):
        super().__init__(**kwargs)
        self.f = f
        self.notify_warnings = notify_warnings

    @update_mf_parameters
    async def process(self, value, input="input", executor=executor, **kwargs):

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # ret = self.f(value, **kwargs)
            # loop = asyncio.get_running_loop()
            # loop.set_debug(True)
            # ret = await loop.run_in_executor(executor, self.f, value, **kwargs)
            ret = await asyncio.get_running_loop().run_in_executor(executor, self.f, value, **kwargs)
            if isinstance(ret, (GeneratorType, range)):
                for el in ret:
                    if self.notify_warnings: w = await notify_warnings(self, w)
                    cont = await self.notify(el)
                    if cont == CHOKE:
                        return cont
            else:
                if self.notify_warnings: w = await notify_warnings(self, w)
                await self.notify(ret)

        if not self.propagate:
            await super().flush(input=input)


class AsyncFun(Processor):
    def __init__(self, f, stream=False, **kwargs):
        super().__init__(**kwargs)
        self.f = f
        self.stream = stream

    @update_mf_parameters
    async def process(self, value, input="input", **kwargs):
        ret = await self.f(value, **kwargs)
        if self.stream:
            await stream(self, ret)

        else:

            await self.notify(ret)


class HttpResponseFun(Processor):
    def __init__(self, type, **kwargs):
        super().__init__(**kwargs)
        self.type = type

    async def consume(self, value, input="input", flush=False, **kwargs):
        logger.debug("Resp %s" % repository.get())
        ret = None
        r = repository.get()
        if isinstance(value, ProcessorError):
            r.update(response=dict(data=value.msg, type='json', status=500))
        else:
            try:
                ret = await self.process(value, input, **kwargs)
            except Exception as inst:
                r.update(response=dict(data=str(inst), type='json', status=500))

        return ret

    async def process(self, value, input="input", **kwargs):
        r = repository.get()
        resp = r.get("response")

        if resp:
            if isinstance(resp, RespAcc):
                resp.append(value)
            else:
                r.update(response=RespAcc(data=[resp['data'], value], type=self.type, status=200))

        else:
            r.update(response=dict(data=value, type=self.type, status=200))

        return value


class ArrayStream(Processor):
    def __init__(self, value=None, flatten=False, **kwargs):
        super().__init__(**kwargs)
        self.value = value
        self.flatten = flatten

    async def process(self, value, input="input", **kwargs):
        value = value or self.value
        if self.flatten:
            value = flatten(value)
        for v in value:
            await self.notify(v)
        if not self.propagate:
            await self.flush()


class Delay(Processor):
    def __init__(self, t, **kwargs):
        super().__init__(**kwargs)
        if not callable(t):
            self.t = lambda: t
        else:
            self.t = t

    async def process(self, value, input="input", **kwargs):
        await asyncio.sleep(self.t())
        return await self.notify(value)


class Directory(Processor):
    def __init__(self, path, dao=None, recursive=False, f=None, **kwargs):
        super().__init__(**kwargs)
        self.f = f
        self.dao = dao
        self.recursive = recursive
        self.path = path

    async def consume(self, value, input="input", flush=False, **kwargs):
        return await super().consume(self.path, input, flush=flush, **kwargs)

    async def process(self, value, input="input", **kwargs):
        """repo = repository.get()
        count = 0
        if self.dao:
            value = self.dao.real(value)
            base = self.dao.base
        else:
            value = Path(value)
            base = Path("/")
        if self.recursive:
            for el in value.rglob("*"):
                if not self.f or self.f(el):
                    cont = await self.notify(el.relative_to(base))
                    if cont == CHOKE:
                        break
        else:"""
        for el in self.dao.ls(value, recursive=self.recursive):
            if not self.f or self.f(el):
                # repo['progress'] = count
                # count += 1
                cont = await self.notify(el['path'])
                if cont == CHOKE:
                    break
        if not self.propagate:
            await self.flush(input=input)

    def _getiter(self, value):
        if self.dao:
            value = self.dao.real(value)
            base = self.dao.base
        else:
            value = Path(value)
            base = Path("/")
        if self.recursive:
            for el in value.rglob("*"):
                if not self.f or self.f(el):
                    yield el.relative_to(base)

        else:
            for el in value.iterdir():
                if not self.f or self.f(el):
                    yield el.relative_to(base)

    async def preview(self):
        return list(itertools.islice(self._getiter(self.path), 3))


class Head(Processor):
    def __init__(self, n, **kwargs):
        super().__init__(**kwargs)
        self.n = n
        self.index = 0

    @update_parameters
    async def process(self, value, input="input", **kwargs):
        if self.index < self.n:
            await self.notify(value)
            self.index += 1
        else:
            return CHOKE

    async def flush(self, input='input'):
        self.index = 0
        await super().flush(input=input)


#
# class Subset(Processor):
#     def __init__(self, start, end, **kwargs):
#         super().__init__(**kwargs)
#         self.start = start
#         self.end = end
#         self.index = start
#
#     @update_parameters
#     async def process(self, value, input="input", **kwargs):
#         if self.index < self.end:
#             await self.notify(value)
#             self.index += 1
#         else:
#             return CHOKE
#
#     async def flush(self):
#         self.index = 0
#         await super().flush()


class CSVReader(Processor):
    def __init__(self, value=None, sep=",", dao=None, infer_type=False, df=False, **kwargs):
        super().__init__(**kwargs)
        self.path = value['path'] if value else None
        self.sep = eval('"' + sep + '"')
        self.dao = dao
        self.infer_type = infer_type
        self.df = df

    def find_type(self, v):
        if v.replace('.', '', 1).isdigit():
            return float(v)
        if v.lower() == 'true':
            return True
        if v.lower() == 'false':
            return False
        return v

    async def read(self, f):
        reader = csv.reader(f, delimiter=self.sep)
        header = next(reader)
        for row in reader:
            if self.infer_type:
                el = {k: self.find_type(v) for k, v in zip(header, row)}
            else:
                el = dict(zip(header, row))
            cont = await self.notify(el)
            if cont == CHOKE:
                break

    async def process(self, value, input="input", **kwargs):
        value = value if isinstance(value, pathlib.PosixPath) else self.path

        if not value:
            raise Exception('missing path parameter')
        if self.dao:
            if self.df:
                df = dd.read_csv(self.dao.real(value))
                print("FDF" * 100, df)
                await self.notify(df)
            else:
                with self.dao.get(value, "r") as f:
                    await self.read(f)
        else:
            with open(value) as f:
                await self.read(f)
        if not self.propagate:
            await super().flush(input=input)

    def _getiter(self, value):
        if self.dao:
            with self.dao.get(value, "r") as f:
                reader = csv.reader(f)
                header = next(reader)
                for row in reader:
                    yield dict(zip(header, row))
        else:
            with open(value) as f:
                reader = csv.reader(f)
                header = next(reader)
                for row in reader:
                    yield dict(zip(header, row))

    async def preview(self):
        return "ciccio"


class CSVWriter(Processor):
    def __init__(self, path=None, dao=None, append=False, sep=",", overwrite=False, **kwargs):
        super().__init__(**kwargs)
        self.append = append
        self.path = path
        self.sep = sep
        self.dao = dao
        self.overwrite = overwrite
        self.exists = None
        self.paths = []  # usato nel caso di parameters

    @update_parameters
    async def process(self, value, input="input", **kwargs):

        mode = 'a' if self.append else 'w'
        if isinstance(value, dict):
            value = [value]
        _stream = StringIO()
        writer = csv.DictWriter(_stream, value[0].keys(), delimiter=self.sep)

        if self.path not in self.paths:
            self.exists = self.dao.exists(self.path)
            if self.overwrite and self.exists:
                self.dao.delete(self.path)
                self.exists = False
            if not self.exists:
                writer.writeheader()
            self.paths.append(self.path)

        for row in value:
            writer.writerow(row)
        _stream.seek(0)
        res = re.sub('(?<=,)nan(?=[\n,])', '', _stream.read())
        _stream = StringIO(res)
        _stream.seek(0)
        if self.path:
            self.dao.save(self.path, _stream, mode)
        _stream.seek(0)
        await self.notify(_stream.read())


class LineReader(Processor):
    def __init__(self, dao, **kwargs):
        super().__init__(**kwargs)
        self.dao = dao

    async def process(self, value, input="input"):
        with self.dao.get(value, mode="r") as f:
            for line in f:
                cont = await self.notify(line.strip())
                if cont == CHOKE:
                    break
        if not self.propagate:
            await super().flush(input=input)


class Counter(Processor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.count = 0

    async def process(self, value, input="input"):
        self.count += 1

    async def flush(self, input="input"):
        count = self.count
        self.count = 0
        if count:
            await self.notify(count)
        # await super().flush()

    async def end(self, input="input"):
        count = self.count
        self.count = 0
        if count:
            await self.notify(count)
        await super().end()


class Merger(Processor):
    def __init__(self, inputs, **kwargs):
        super().__init__(**kwargs)
        self.inputs = {x["id"]: x['label'] for x in inputs}
        self.data = defaultdict(list)

    async def process(self, value, input="input"):
        self.data[self.inputs[input]].append(value)
        if len(self.data) == len(self.inputs) and all([len(x) for x in self.data.values()]):
            ret = {}
            for k, v in self.data.items():
                ret[k] = v.pop(0)
            await self.notify(ret)


async def stream(processor, result, output="output"):
    if isinstance(result, (GeneratorType, range, list, tuple)):
        for el in result:
            await processor.notify(el, output=output)

    elif isinstance(result, AsyncRequest):
        async with ClientSession(timeout=ClientTimeout(total=None)) as session:
            r = await session.request(method=result.method, url=result.url, **result.kwargs)
            if r.status != 200:
                raise Exception((await r.text()).strip('"'))
            ret = None
            async for chunk, _ in r.content.iter_chunks():
                if chunk:
                    ret = ret + chunk if ret else chunk
                    if _:
                        if result.eval:
                            ret = eval(ret)
                        await processor.notify(ret, output=output)
                        # print('line::', _, str(ret)[:100])
                        ret = None
        logger.debug("end streaming info...")
    else:
        await processor.notify(result, output=output)


class MultiFun(Processor):
    def __init__(self, funs, stream_result=True, **kwargs):
        super().__init__(**kwargs)
        self.funs = funs
        self.stream_result = stream_result

    @update_mf_parameters
    async def process(self, value, input="input", **kwargs):
        if input in self.funs:
            f, output = self.funs[input]
            res = await f(value, **kwargs)
            if self.stream_result:
                await stream(self, res, output)
            else:
                await self.notify(res, output)
            # await self.flush()
            if not self.propagate:
                await super().flush(input=input)

        else:
            raise Exception("Input '%s' not managed" % input)

    async def consume(self, value, input="input", **kwargs):
        return await super().consume(value, input=input, output=self.funs[input][1])

    async def flush(self, input='input'):
        ret = []
        f, output = self.funs[input]
        v = self.pipes[output]
        # print(self.name)
        # print('INPUT::', input)
        # print(output)
        # for vv in v:
        #     print(vv[0], vv[1].__class__.__name__)
        # print()
        ret.extend([x[1].flush(input=x[0]) for x in v])
        await asyncio.gather(*ret)

    async def end(self, input='input'):
        ret = []
        f, output = self.funs[input]
        v = self.pipes[output]
        # print(self.name)
        # print('INPUT::', input)
        # print(output)
        # for vv in v:
        #     print(vv[0], vv[1].__class__.__name__)
        # print()
        ret.extend([x[1].end(input=x[0]) for x in v])
        await asyncio.gather(*ret)


class FileWriter(Processor):
    def __init__(self, path=None, dao=None, append=False, type="text", overwrite=False, **kwargs):
        super().__init__(**kwargs)
        self.append = append
        self.path = path
        self.dao = dao
        self.type = type
        self.overwrite = overwrite

    @update_parameters
    async def process(self, value, input="input"):
        trg = self.path
        data = value

        if self.overwrite and self.dao.exists(self.path):
            self.dao.delete(self.path)
            self.overwrite = False

        mode = 'a' if self.append else 'w'
        _stream = None
        if self.type == 'bytes':
            mode += 'b'
            _stream = BytesIO()
        else:
            _stream = StringIO()
        # with open(self.base / to_relative(trg), method) as o:
        if self.type == 'json':
            _stream.write(json.dumps(data) + "\n")
        else:
            if self.type == 'text':
                data += '\n'
            _stream.write(data)
        _stream.seek(0)
        self.dao.save(trg, _stream, mode=mode)
        await self.notify("Written to %s" % trg)


class Sampler(Processor):
    def __init__(self, p, **kwargs):
        super().__init__(**kwargs)
        self.p = p

    async def process(self, value, input="input"):
        if random.random() <= self.p:
            return await self.notify(value)


class TimedCounter(Processor):
    def __init__(self, t, **kwargs):
        super().__init__(**kwargs)
        self.t = t
        self.last = None
        self.count = 0

    async def process(self, value, input="input"):
        if self.last is None:
            self.last = time.time()
        nt = time.time()
        self.count += 1
        if nt - self.last > self.t and self.count:
            self.last = nt
            c = self.count
            self.count = 0
            return await self.notify(c)

    async def flush(self, input='input'):
        if self.count:
            c = self.count
            self.count = 0
            await self.notify(c)
        await super().flush(input=input)


class RSampler(Processor):
    def __init__(self, k, **kwargs):
        super().__init__(**kwargs)
        self.k = k
        self.buffer = []
        self.i = 0

    @update_parameters
    async def process(self, value, input="input"):
        self.i += 1
        if len(self.buffer) < self.k:
            self.buffer.append(value)
        else:
            s = int(random.random() * self.i)
            if s < self.k:
                self.buffer[s] = value

    async def flush(self, input='input'):
        if self.buffer:
            ret = list(self.buffer)
            self.buffer = []
            for r in ret:
                await self.notify(r)
        await super().flush(input=input)

    async def end(self, input='input'):
        if self.buffer:
            ret = list(self.buffer)
            self.buffer = []
            for r in ret:
                await self.notify(r)
        await super().end(input=input)


class Filter(Processor):
    def __init__(self, f, notify_warnings, **kwargs):
        super().__init__(**kwargs, outputs=["output", "discarded"])
        self.f = f
        self.notify_warnings = notify_warnings

    async def process(self, value, input="input"):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            res = self.f(value)
            if self.notify_warnings: w = await notify_warnings(self, w)
            if res:
                return await self.notify(value, "output")
            else:
                return await self.notify(value, "discarded")


class Reducer(Processor):
    def __init__(self, fun, acc=0, **kwargs):
        super().__init__(**kwargs)
        self.fun = fun
        self.acc = acc

    async def process(self, value, input="input"):
        self.acc = self.fun(self.acc, value)

    async def flush(self, input='input'):
        await self.notify(self.acc)
        await super().flush(input=input)


class Grouper(Processor):
    def __init__(self, n, **kwargs):
        super().__init__(**kwargs)
        self.n = n
        self.buffer = []

    @update_parameters
    async def process(self, value, input="input"):
        self.buffer.append(value)
        if self.n and len(self.buffer) >= self.n:
            ret = list(self.buffer)
            self.buffer = []
            return await self.notify(ret)

    async def flush(self, input='input'):
        if self.buffer:
            ret = list(self.buffer)
            self.buffer = []
            await self.notify(ret)

        # await super().flush(input=input)

    async def end(self, input='input'):
        if self.buffer:
            ret = list(self.buffer)
            self.buffer = []
            await self.notify(ret)
        await super().end(input)


class Switch(Processor):
    def __init__(self, conditions, **kwargs):
        super().__init__(**kwargs)
        self.conditions = conditions

    async def process(self, value, input="input"):
        for k, v in self.conditions.items():
            if v(value):
                await self.notify(value, k)


class Notifier(Processor):
    def __init__(self, sender, clients, label, max_messages=20, **kwargs):
        super().__init__(**kwargs)
        self.sender = sender
        self.clients = clients
        self.label = label
        self.max_messages = max_messages
        self.n = 0
        self.errors = 0

    async def consume(self, value, input="input"):
        now = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        info = dict(uid=str(uuid4()), timestamp=now, name=self.sender)
        ret = {}
        value = json_friendly(value)

        if isinstance(value, ProcessorError):
            self.errors += 1
            ret = dict(info, name=value.component_name, type="error", uid=str(uuid4()), data=ellipsis(value.msg, n=500))
        else:
            ret = dict(info, data=ellipsis(value, n=500))
        if self.n <= self.max_messages:
            await emit(self.clients, self.label, json_friendly(ret))
        if self.n == self.max_messages + 1:
            await emit(self.clients, self.label, dict(ret, data="..."))
        self.n += 1

    async def flush(self, input='input'):
        now = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        info = dict(timestamp=now, name=self.sender, uid=str(uuid4()))
        if self.n > self.max_messages:
            if self.errors > 0:
                await emit(self.clients, self.label, dict(info, data="(other %d elements, %d errors)" % (
                    self.n - self.max_messages, self.errors)))
            else:
                await emit(self.clients, self.label,
                           dict(info, data="(other %d elements)" % (self.n - self.max_messages)))


class BatchedNotifier(Processor):
    def __init__(self, project, sender, sid, group, clients, label, loop, tab, max_messages=20, time=.5, debug=True,
                 **kwargs):
        super().__init__(**kwargs)
        self.project = project
        self.group = group
        self.tab = tab
        self.sender = sender
        self.sid = sid
        self.clients = clients
        self.label = label
        self.max_messages = max_messages
        self.n = 0
        self.errors = 0
        self.queue = []
        self.time = time
        self.loop = loop
        self.dequeuer = None
        self.running = False
        self.debug = debug

    async def _dequeue(self):
        while self.running:
            try:
                await asyncio.sleep(self.time)
                if self.queue:
                    if self.queue[-1] is None:
                        self.running = False
                        self.queue.pop()
                    if self.debug:
                        await emit(self.clients, self.label, json_friendly([x for x in self.queue if x]))
                    else:
                        msg = [x for x in self.queue if x and x.get('type') == "error"]
                        if msg:
                            await emit(self.clients, self.label,
                                       json_friendly(msg))
                    self.queue = []
            except Exception as e:
                logging.exception(e)

    async def consume(self, value, input="input"):
        if not self.running:
            self.running = True
            self.dequeuer = self.loop.create_task(self._dequeue())
        now = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        info = dict(uid=str(uuid4()), timestamp=now, tab=self.tab, id=self.sid, name=self.sender)
        ret = {}
        error = isinstance(value, ProcessorError)
        msg = json_friendly(value)
        if error:
            if value.source_id == self.sid:
                self.errors += 1
                ret = dict(info, project=self.project, group=self.group, name=self.sender, type="error",
                           uid=str(uuid4()),
                           data=ellipsis(msg["msg"], n=500))

        elif self.debug:
            ret = dict(info, project=self.project, group=self.group, data=ellipsis(msg, n=500))
            # print("-----")
            # print(ret)
        if ret:
            if self.n <= self.max_messages:
                self.queue.append(ret)
            if self.n == self.max_messages + 1:
                self.queue.append(dict(ret, data="..."))
            self.n += 1

    async def flush(self, input='input'):
        now = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        info = dict(timestamp=now, tab=self.tab, id=self.sid, name=self.sender)
        if self.n > self.max_messages:
            if self.errors > 0:
                self.queue.append(
                    dict(info, project=self.project, group=self.group,
                         data="(other %d elements, %d errors)" % (self.n - self.max_messages, self.errors)))
            else:
                self.queue.append(dict(info, project=self.project, group=self.group,
                                       data="(other %d elements)" % (self.n - self.max_messages)))
        if not self.queue or self.queue[-1] is not None:
            self.queue.append(None)

    async def end(self, input='input'):
        await self.flush()


class Pool(Processor):
    def __init__(self, f, n, loop, **kwargs):
        super().__init__(**kwargs)
        if n < 2:
            raise Exception("n must be >=2")
        self.n = n
        self.f = f
        self.loop = loop
        self.dt = None
        self.queue = asyncio.Queue(loop=loop, maxsize=n - 1)

    async def dequeue(self):
        while True:
            item = await self.queue.get()
            if item == None:
                break
            item = await item
            await self.notify(item)

    async def process(self, value, input="input"):
        if self.dt == None:
            self.dt = self.loop.create_task(self.dequeue())
        event = asyncio.Event()
        res = self.loop.create_task(self.f(value, event))
        await self.queue.put(res)
        event.set()

    async def flush(self, input='input'):
        await self.queue.put(None)


class MessageCollector(Processor):
    def __init__(self, collection, node, **kwargs):
        super().__init__(**kwargs)
        self.collection = collection
        self.node = node

    async def process(self, value, input="input"):
        self.collection[self.node.id] = value


class DummyProcessor(Processor):

    def __init__(self, id, name, **kwargs):
        super().__init__(id=id, name=name, **kwargs)


def log(label):
    return Fun(lambda x: print(label, x))


class ChainProcessor(Processor):
    def __init__(self, start, end, **kwargs):
        super().__init__(**kwargs)
        self.pstart = start
        self.pend = end

    def pipe(self, processor, output="output", input="input"):
        return self.pend.pipe(processor, output, input)

    async def flush(self, input='input'):
        return await self.pstart.flush(input=input)

    async def end(self, input='input'):
        return await self.pstart.end(input=input)

    async def process(self, value, input="input"):
        return await self.pstart.process(value, input)


class TSCollector(Processor):
    def __init__(self, n=None, **kwargs):
        super().__init__(**kwargs)
        self.n = n
        self.buffer = dict(data=[], target=[])

    async def process(self, value, input="input"):
        if isinstance(value, list):
            self.buffer['data'].append(value[0])
            self.buffer['target'].append(value[1])
        elif isinstance(value, dict):
            if 'data' in value:
                self.buffer['data'].append(value.get('data'))
                self.buffer['target'].append(value.get('target'))
            else:
                self.buffer['data'].append(value)
        else:
            logger.debug('value must be a list, dict[data,target] or dict of data!')
            raise Exception('value must be a list, dict[data,target] or dict of data!')

        if self.n and len(self.buffer['data']) >= self.n:
            ret = self.buffer
            self.buffer = dict(data=[], target=[])
            return await self.notify(ret)

    async def flush(self, input='input'):
        if self.buffer['data']:
            ret = self.buffer
            self.buffer = dict(data=[], target=[])
            await self.notify(ret)
        await super().flush(input=input)

    async def end(self, input='input'):
        if self.buffer['data']:
            ret = self.buffer
            self.buffer = dict(data=[], target=[])
            await self.notify(ret)
        await super().end(input=input)


if __name__ == "__main__":
    a = lambda data: eval("data==3")
    b = lambda data: eval("data==4")

    conds = {"a": a, "b": b}
    s = Switch(conds)

    ass = ArrayStream(value=[2, 3, 4])

    ass.pipe(s)
    s.pipe(log("A"), output="a")
    s.pipe(log("B"), output="b")
    ass.run(None)
