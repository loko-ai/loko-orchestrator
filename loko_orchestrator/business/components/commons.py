import json
import os
import sys
import traceback
from collections import defaultdict
from functools import partial
from io import StringIO
from pathlib import Path
import sanic.request
from aiohttp import FormData
from dict_path import DictPath
from loguru import logger
from sanic.exceptions import SanicException

from loko_orchestrator.business.engine import Fun, Notifier, Parameters, repository, ArrayStream, Merger, Filter, \
    Repository, Switch, AsyncFun, MultiFun, ProcessorError
# from loko_orchestrator.config.app_config import fsdao, sio
from loko_orchestrator.config.constants import global_daos
from loko_orchestrator.config.constants import PUBLIC_FOLDER
from loko_orchestrator.dao.fs import LayeredFS, FSDao
from loko_orchestrator.model.components import Component, Field, Options, required, Text
from loko_orchestrator.utils import async_request
from loko_orchestrator.utils.codeutils import compile_fun
from loko_orchestrator.resources.doc_commons_component import trigger_doc, debug_doc, function_doc, array_doc, \
    filter_doc, selector_doc, merge_doc, switch_doc, renamer_doc
from loko_orchestrator.resources.doc_http_component import template_doc
from loko_orchestrator.utils.dict_path_utils import SafeDictPath

from os import path

from loko_orchestrator.utils.logger_utils import logger


class Debug(Component):
    def __init__(self):
        super().__init__("Debug", group="Common", description=debug_doc, args=[], outputs=[], values=dict(debug=True),
                         icon="RiBugFill", configured=True)

    def create(self, name, **kwargs):
        p = Fun(lambda x: x, **kwargs)
        # sender = kwargs.get("alias") or name
        # p.pipe(Notifier(sender, sio, "messages"))
        # p.pipe(Fun(lambda x: print("EEEEE", x)))
        return p


class Function(Component):
    def __init__(self):
        desc = """A python function that processes the incoming message. 
Variables available are:
- **data**: the incoming message
"""

        args = [dict(name="propagate", type="boolean", label="Flush at the end"),
                dict(name="notify_warnings", type="boolean", label="Notify warnings"),
                Field(name="code", type="code", description=desc, label="Code", validation=required)]

        super().__init__("Function", group="Common", description=function_doc, args=args,
                         values=dict(code="return data", propagate=True, notify_warnings=True), icon="RiCodeSSlashFill",
                         configured=True)

    def create(self, code, name, project_id, propagate=True, notify_warnings=True, **kwargs):
        name = kwargs.get("alias") or name
        kwargs["name"] = name
        g = dict(Parameters=Parameters, repository=Repository(repository), globals=global_daos[project_id])
        # g.update(app_config.EXTERNAL_MODULES)
        return Fun(compile_fun(code, g), propagate=propagate, notify_warnings=notify_warnings, **kwargs)


class FilterComponent(Component):
    def __init__(self):
        desc = """Python code that return a boolean (True,False). Incoming messages that evaluates to True are sent to the first output while the others are redirected to the second one"""

        args = [dict(name="notify_warnings", type="boolean", label="Notify warnings"),
                Field(name="code", type="code", description=desc, label="Code", validation=required)]

        super().__init__("Filter", group="Common", description=filter_doc, args=args, icon="RiFilter2Fill",
                         values=dict(notify_warnings=True), outputs=["output", "discarded"])

    def create(self, code, name, notify_warnings=True, **kwargs):
        name = kwargs.get("alias") or name
        kwargs["name"] = name
        g = dict(Parameters=Parameters, repository=Repository(repository))
        # g.update(app_config.EXTERNAL_MODULES)
        return Filter(compile_fun(code, g), notify_warnings=notify_warnings, **kwargs)


class Trigger(Component):
    def __init__(self):
        args = [Options(name="type", description="The type of data", options=["String", "Object"], label="Type",
                        validation=required),
                dict(name="value", type="dynamic", dynamicType={
                    "String": "area",
                    "Object": "code",
                }, parent="type", label="Value", validation={"required": "Required field"})]

        super().__init__("Trigger", group="Common", description=trigger_doc, inputs=[], click="Send message",
                         args=args,
                         values=dict(type="String", value="Hello world!"), icon="RiPlayFill", configured=True)

    def create(self, type, value, **kwargs):
        if type == "Object":
            value = eval(value)
        return Fun(lambda x: value, propagate=True, **kwargs)


class Value(Component):
    def __init__(self):
        args = [Options(name="type", description="The type of data", options=["String", "Object"], label="Type",
                        validation=required),
                dict(name="value", type="dynamic", dynamicType={
                    "String": "area",
                    "Object": "code",
                }, parent="type", label="Value", validation={"required": "Required field"})]

        super().__init__("Value", group="Common", description=trigger_doc, inputs=["input"],
                         args=args,
                         values=dict(type="String", value="Hello world!"), icon="RiPlayFill", configured=True)

    def create(self, type, value, **kwargs):
        if type == "Object":
            value = eval(value)
        return Fun(lambda x: value, propagate=True, **kwargs)


class Array(Component):
    def __init__(self):
        args = [
            Text(name="value", label="value", description="Python or json code that evaluates to a list or iterable"),
            dict(name="propagate", type="boolean", label="Flush at the end"),
            dict(name="flatten", type="boolean", label="Flatten the array recursively")
        ]
        super().__init__("Array", group="Common", description=array_doc, args=args, click="Send message",
                         values=dict(value="[1,2,3,4,5]", propagate=True, flatten=False), icon="RiBracketsFill",
                         configured=True)

    def create(self, value, **kwargs):
        return ArrayStream(eval(value), **kwargs)


class Selector(Component):
    def __init__(self):
        super().__init__("Selector", group="Common", description=selector_doc, icon="RiCursorFill",
                         args=[dict(name="ignore_err", label="Ignor Error", type="boolean",
                                    description="Choose whether to ignore error in case of a missing key or not"),
                               dict(name="exclude", label="Exclude Keys", type="boolean",
                                    description="If enabled, the output contains the whole input object excluding the specified keys; otherwise, only the specified keys are returned"
                                    ),
                               dict(name="keys", label="Keys", type="multiKeyValue", validation=required,
                                    description="Name of the key/s to select from the incoming message",
                                    fields=[dict(name="k", placeholder="key", validation=required)])
                               ],
                         values=dict(ignore_err=False,
                                     include=False
                                     ))

    def reshape_nested_key(self, key, shape_back=False):
        if not shape_back:
            if "." in key:
                key = "/".join(key.split("."))

        else:
            if "/" in key:
                key = ".".join(key.split("/"))
        return key

    def create(self, keys, ignore_err, exclude, **kwargs):
        def f(v, keys=keys, ignore_err=ignore_err, exclude=exclude, **kwargs):
            v = SafeDictPath(v)
            selected = SafeDictPath({}) if not exclude else v.copy()
            if not ignore_err:
                for k in keys:
                    key = k["k"]
                    key = self.reshape_nested_key(key)
                    if key in v:
                        if exclude:
                            del selected[key]
                        else:
                            selected[key] = v.get(key)

                    else:
                        key = self.reshape_nested_key(key, shape_back=True)
                        raise KeyError(key)
            else:
                for k in keys:
                    key = k["k"]
                    key = self.reshape_nested_key(key)
                    if key in v:
                        if exclude:
                            del selected[key]
                        else:
                            selected[key] = v.get(key)

            if len(keys) == 1 and not exclude:
                selected = selected.get(key)

            try:
                selected = selected.dict.copy()
            except AttributeError as a_error:
                pass
            except Exception as e:
                raise e

            return selected

        return Fun(f, **kwargs)


class Renamer(Component):
    def __init__(self):
        args = [dict(name="ignore_err", label="Ignor Error", type="boolean",
                     description="Choose whether to ignore error in case of a missing key or not"),
                dict(name="keys", label="Inputs", type="multiKeyValue", validation=required, fields=[
                    dict(name="source", placeholder="Source", validation=required),
                    dict(name="target", placeholder="Target", validation=required)
                ])]
        super().__init__("Renamer", group="Common", description=renamer_doc, icon="RiEditFill",
                         args=args, inputs=['input'])

    def create(self, keys, ignore_err, **kwargs):
        def f(v, keys=keys, ignore_err=ignore_err, **kwargs):
            ret = v.copy()
            for key in keys:
                if key["source"] not in v:
                    if not ignore_err:
                        raise KeyError(key['source'])
                else:
                    ret[key['target']] = ret.pop(key['source'])
            return ret

        return Fun(f, **kwargs)


class MergeComponent(Component):
    def __init__(self):
        args = [dict(name="inputs", label="Inputs", type="multiKeyValue", validation=required, fields=[
            dict(name="label", placeholder="Input", validation=required)
        ])]

        super().__init__("Merge", group="Common", description=merge_doc, args=args, icon="RiGitMergeFill", inputs=[])

    def create(self, inputs, **kwargs):
        p = Merger(inputs, **kwargs)
        return p


class Cond:
    def __init__(self, code):
        self.code = code

    def __call__(self, data):
        return eval(self.code)


class SwitchComponent(Component):
    def __init__(self):
        args = [dict(name="outputs", label="Outputs", type="multiKeyValue", validation={
            "required": "Required field",
        }, fields=[
            dict(name="condition", placeholder="Condition", validation={
                "required": "Required field",
            }),
            dict(name="label", placeholder="Output", validation={
                "required": "Required field",
            })
        ])]

        super().__init__("Switch", group="Common", description=switch_doc, icon="RiFileCodeFill", args=args)

    def create(self, outputs, **kwargs):
        conds = {}
        for el in outputs:
            conds[el['id']] = Cond(el['condition'])

        p = Switch(conds, **kwargs)
        return p


class Template(Component):
    def __init__(self):
        args = [Field(name="code", type="code", label="Template code", validation=required)]
        super().__init__("Template", group="HTTP", description=template_doc, icon="RiHtml5Fill", args=args)

    def create(self, code, **kwargs):
        def f(v):
            if isinstance(v, dict):
                return eval('f"""%s"""' % code, v)
            else:
                return eval('f"""%s"""' % code, {"data": v})

        return Fun(f, **kwargs)


"""class FileConverter(Component):
    def __init__(self):
        self.microservice = "file-converter"
        args = [
            dict(name="service", type="service", label="Available services", fragment="file-converter",
                 validation={"required": "Required field"}),
            dict(name="input_format", label="Input format", type="select", options=["xls"], validation=dict(
                required="Required field")),
            dict(name="output_format", label="Output format", type="select", options=["csv"], validation=dict(
                required="Required field"))]

        super().__init__("File Converter", group="Common", icon="RiFileTransferFill", args=args)

    def create(self, gateway, service, input_format, output_format, headers=None, **kwargs):
        url = os.path.join(gateway, service, "convert")
        headers = headers or dict()

        async def req(value):
            if isinstance(value, Path):
                with open(fsdao.real(value), "rb") as inp:
                    files = dict(file=inp)
                    return await async_request.request(url, method="POST", data=files, accept="a",
                                                       params=dict(input_format=input_format,
                                                                   output_format=output_format), headers=headers)

        return AsyncFun(req, **kwargs)
"""


class EventComponent(Component):
    def __init__(self):
        args = [Options(name="event", options=["start", "stop"], value="start")]
        super().__init__("Event", group="Common", description="template_doc", icon="RiHtml5Fill", args=args)

    def create(self, gateway, project_id, session, **kwargs):
        return Fun(lambda x: x)


class Globals(Component):
    def __init__(self):
        args = [dict(name="inputs", label="Inputs", type="multiKeyValue", validation=required, fields=[
            dict(name="label", placeholder="Input", validation=required)
        ]), dict(name="persist", type="boolean", label="Persist value")]
        super().__init__("Globals", group="Common", description="template_doc", icon="RiGlobalLine", args=args,
                         inputs=[])

    def create(self, project_id, inputs, persist, **kwargs):
        mapping = {}
        repo = Repository(repository)
        for inp in inputs:
            async def f(value, key=inp['label']):
                if persist:
                    setattr(global_daos[project_id], key, value)
                else:
                    repo.set(key, value)

                return value

            mapping[inp['id']] = f, "output"

        return MultiFun(mapping, **kwargs)


class Custom(Component):
    def __init__(self, **kwargs):
        args = []
        values = {}
        if "options" in kwargs:
            options = kwargs["options"]
            args = options.get('args', [])
            values = options.get("values", {})
            del kwargs['options']

        logger.debug(("Custom", args, kwargs))
        fs_dao = FSDao(PUBLIC_FOLDER, lambda x: x.suffix == ".metadata")
        self.fsdao = LayeredFS()
        self.fsdao.mount("data", fs_dao)

        super().__init__(args=args, values=values, **kwargs)

    def create(self, gateway, project_id, session, **kwargs):
        async def f(v, input, service, **other_args):
            if other_args:
                other_args = kwargs | other_args
            else:
                other_args = kwargs
            headers = {"accept": "application/jsonl,application.json,*/*"}
            try:
                url = path.join(gateway, "routes", project_id, service)
                logger.debug(f"URL is {url}")
                logger.debug(type(v))

                if isinstance(v, Path):
                    with self.fsdao.get(v, "rb") as o:
                        resp = await async_request.request(url, session, "POST",
                                                           data={"file": o,
                                                                 "args": StringIO(json.dumps(other_args))},
                                                           headers=headers)
                elif isinstance(v, sanic.request.File):
                    fd = FormData()
                    fd.add_field("file", v.body, filename=v.name, content_type=v.type)
                    fd.add_field("args", StringIO(json.dumps(other_args)))

                    resp = await async_request.request(url, session, "POST",
                                                       data=fd, headers=headers)
                else:
                    resp = await async_request.request(url, session, "POST", json=dict(value=v, args=other_args),
                                                       headers=headers)
                return resp
            except Exception as inst:
                logger.exception(inst)
                raise Exception(f"Problems with extension '{project_id}' - {inst}")

        mapping = {}
        for el in self.inputs:
            mapping[el['id']] = partial(f, input=el['id'], service=el.get("service", "")), el.get("to", "output")

        return MultiFun(mapping, **kwargs)


class SharedExtension(Component):
    def __init__(self, pname, **kwargs):
        args = []
        values = {}
        self.pname = pname
        if "options" in kwargs:
            options = kwargs["options"]
            args = options.get('args', [])
            values = options.get("values", {})
            del kwargs['options']

        logger.debug(("Custom", args, kwargs))
        fs_dao = FSDao(PUBLIC_FOLDER, lambda x: x.suffix == ".metadata")
        self.fsdao = LayeredFS()
        self.fsdao.mount("data", fs_dao)

        super().__init__(args=args, values=values, **kwargs)

    def create(self, gateway, project_id, session, **kwargs):
        async def f(v, input, service, **other_args):
            if other_args:
                other_args = kwargs | other_args
            else:
                other_args = kwargs

            try:
                url = path.join(gateway, "routes", self.pname, service)
                if isinstance(v, Path):
                    with self.fsdao.get(v, "rb") as o:
                        resp = await async_request.request(url, session, "POST",
                                                           data={"file": o, "args": StringIO(json.dumps(other_args))})
                elif isinstance(v, sanic.request.File):
                    fd = FormData()
                    fd.add_field("file", v.body, filename=v.name, content_type=v.type)
                    fd.add_field("args", StringIO(json.dumps(other_args)))
                    resp = await async_request.request(url, session, "POST",
                                                       data=fd)
                else:
                    resp = await async_request.request(url, session, "POST", json=dict(value=v, args=other_args))
                return resp
            except Exception as inst:
                # logger.exception(inst)
                raise Exception(f"Problems with extension '{self.pname}' - {inst}")

        mapping = {}
        for el in self.inputs:
            mapping[el['id']] = partial(f, input=el['id'], service=el.get("service", "")), el.get("to", "output")

        return MultiFun(mapping, **kwargs)
