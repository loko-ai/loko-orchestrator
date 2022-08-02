import asyncio
import io
import json
import logging
import traceback
from ast import literal_eval
from datetime import datetime
from fileinput import fileno
from pathlib import Path
from urllib.parse import unquote
from uuid import uuid4

import sanic
from aiohttp import ClientSession, ClientTimeout
from sanic import Blueprint
from sanic import Sanic
from sanic import response
from sanic.exceptions import NotFound, SanicException
from sanic.response import HTTPResponse, text
from sanic.response import json as sjson, html
from sanic_cors import CORS
from sanic_openapi import swagger_blueprint, doc
from socketio.exceptions import ConnectionError

from loko_orchestrator.business.builder.docker_builder import build_extension_image, run_extension_image
from loko_orchestrator.business.converters import project2processor, cached_messages, get_project_info
from loko_orchestrator.business.engine import repository
# from loko_orchestrator.business.forms import all_forms, get_form
# from loko_orchestrator.business.groups import get_components

# from loko_orchestrator.config.app_config import sio, pdao, tdao, fsdao, DEBUG, \
#    PLUGIN_DAO, services_scan, ASYNC_SESSION_TIMEOUT, GATEWAY, PORT, CORS_ON
# from loko_orchestrator.model.plugins import Plugin
from loko_orchestrator.business.groups import get_components
from loko_orchestrator.config import app_config

app_config.init()
from loko_orchestrator.config.app_config import CORS_ON, GATEWAY, ASYNC_SESSION_TIMEOUT, pdao, tdao, fsdao, PORT, DEBUG, \
    sio
from loko_orchestrator.model.projects import Project, LATEST_PRJ_VERSION
# from loko_orchestrator.utils.authutils import get_user_role
# from loko_orchestrator.utils.conversions_utils import infer_ext, FORMATS2JSON
# from loko_orchestrator.utils.file_conv_utils import FileConverter
# from loko_orchestrator.utils.file_manager_utils import check_for_duplicate, check_protected_folders, \
#    check_special_characters
from loko_orchestrator.utils.jsonutils import GenericJsonEncoder
from loko_orchestrator.utils.logger_utils import logger
# from loko_orchestrator.utils.projects_utils import check_prj_duplicate, check_prj_id_duplicate
from loko_orchestrator.utils.sio_utils import emit

# from loko_orchestrator.utils.update_version_prj_utils import get_updated_prj_structure
# from loko_orchestrator.utils.zip_utils import files2zip, zip2files

# POOL = ProcessPoolExecutor(max_workers=4)

appname = "orchestrator"
app = Sanic(appname)

swagger_blueprint.url_prefix = "/api"
app.blueprint(swagger_blueprint)
bp = Blueprint("default", url_prefix=f"ds4biz/orchestrator/0.1")

app.config["API_TITLE"] = appname
app.config["API_VERSION"] = "0.1"
app.config["API_SCHEMES"] = ["http", "https"]
app.config["API_SECURITY"] = [{"ApiKeyAuth": []}]
app.config["API_SECURITY_DEFINITIONS"] = {
    "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "Authorization"}
}

if CORS_ON:
    CORS(app, expose_headers=["Range"])

# @app.exception(Exception)
# async def generic_exception(request, exception):
#     e = str(exception)
#     j = dict(error=e)
#     if isinstance(exception, NotFound):
#         return response.json(j, status=404, headers={"Access-Control-Allow-Origin": "*"})
#     return response.json(j, status=500, headers={"Access-Control-Allow-Origin": "*"})


flows = {}
flows_info = {}


def flows_list():
    ret = []
    for k in flows.keys():
        ret.append(dict(flows_info[k], uid=k))
    return ret


async def task(id, t, repo=True):
    if repo:
        token = repository.set({})

    logger.debug(flows.keys())

    await emit(sio, "flows", flows_list())

    try:
        await t
    except Exception as inst:
        logging.exception(inst)
    if id in flows:
        del flows[id]
        del flows_info[id]
    if repo:
        repository.reset(token)
    await emit(sio, "flows", flows_list())


@bp.get("/tasks")
def get_tasks(request):
    ret = []
    # print("tasks call")
    logger.debug("tasks call")
    for k in flows.keys():
        ret.append(dict(flows_info[k], uid=k))
    # return sjson(list(flows.keys()))
    return sjson(ret)


@bp.delete("/tasks", ignore_body=False)
async def cancel(request):
    for id in flows:
        t = flows[id]
        del flows[id]
        del flows_info[id]
        t.cancel()
    await emit(sio, "flows", flows_list())
    return sjson({"msg": "Ok"})


"""@bp.post("/lock")
async def lock(request):
    user, role = get_user_role(request)
    print("USER", user)
    j = request.json
    await emit(sio, "system", {"action": "lock", "id": j.get("id"), "user": user})
    return sjson({"msg": "Ok"})


@bp.post("/release")
async def release(request):
    j = request.json
    await emit(sio, "system", {"action": "release", "id": j.get("id")})
    return sjson({"msg": "Ok"})"""


@bp.delete("/tasks/<id>", ignore_body=False)
async def cancel(request, id):
    if id in flows:
        t = flows[id]
        del flows[id]
        del flows_info[id]
        t.cancel()
        await emit(sio, "flows", flows_list())

    return sjson({"msg": "Ok"})


@bp.route("/endpoints/<project_id>/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
@doc.consumes(doc.Boolean(name="return"), location="query")
# @doc.consumes(doc.JsonBody(), location="body", required=False)
# @doc.consumes(doc.File(name="file"), location="formData", content_type="multipart/form-data", required=False)
# @app_config.AUTHORIZATION(role="USER")
async def endpoints(request, project_id, path):
    # print("Project", project_id, type(project_id))
    logger.debug("Project {id} {type}".format(id=project_id, type=type(project_id)))
    project = pdao.get(project_id)
    id = None
    now = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")

    bth = dict()
    headers = dict(request.headers)
    if "authorization" in headers:
        bth["authorization"] = headers.pop("authorization")

    try:
        for n, graph_id in project.nodes():
            if 'comment' not in n.data:
                if n.data['name'] == "Route":
                    if n.data['options']['values'].get("path") == path:
                        id = n.id

        pid, nodes, edges, graphs = get_project_info(project)
        processors, metadata = project2processor(id, pid, nodes, edges, tab=graphs[id], headers=bth)

    except Exception as inst:
        logging.exception(inst)
        alias = nodes[id].values.get('alias', '')
        if alias:
            start_c = "'" + alias + "' (" + nodes[id].name + ')'
        else:
            start_c = nodes[id].name
        id, name, group, *error = str(inst).split()
        error = ' '.join(error)
        msg = f"Can't start flow - TAB: '{graphs[id]}' - START: {start_c} - COMPONENT: {name} - ERROR: {error}"
        info = dict(uid=str(uuid4()), timestamp=now, tab=graphs[id], id=id, name=name, project=project_id, group=group,
                    type='error', data=f"Can't start flow - ERROR: {error}")
        await emit(sio, "messages", info)
        raise Exception(msg)
    if id == None:
        raise SanicException(status_code=404)

    tid = str(uuid4())
    token = repository.set({})
    t = app.loop.create_task(task(tid, processors[id].consume(request, flush=True), False))
    flows[tid] = t
    flows_info[tid] = dict(startedAt=now)

    if request.args.get("return") == "true":
        repository.reset(token)
        return sjson("Flow started")
    try:
        await t
    except Exception as inst:
        logging.exception(inst)
    # r = repository.get()
    # err = r.get('response_error')
    # if err:
    #     raise Exception(err)
    # print("REPOSITORY", repository.get())
    logger.debug("REPOSITORY %s" % repository.get())

    ret = repository.get().get("response")
    repository.reset(token)
    if ret:
        if ret['type'] == "json":
            return sjson(ret['data'], status=ret['status'])
        if ret['type'] == "html":
            return html(ret['data'], status=ret['status'])

    return sjson("Default response for %s" % path)


# @sio.event
async def connect(sid, environ):
    print('connect ', sid)
    return "Ok"


@bp.get("/projects")
@doc.consumes(doc.String(name="search"), location="query")
@doc.consumes(doc.Boolean(name="info"), location='query')
def projects(request):
    info = get_value(request.args, "info", "none", str).capitalize()
    prjs_info = pdao.all(info=eval(info))
    print("Infor", prjs_info)

    res = prjs_info
    return sjson(res)


@bp.get("/projects/<id>")
@doc.consumes(doc.String(name="id"), location="path", required=True)
def project_by_id(request, id):
    return myjson(pdao.get(id))


@bp.delete("/projects/<id>")
def delete_project(request, id):
    pdao.delete(id)
    return sjson(dict(project=id))


@bp.post("/projects")
@doc.consumes(doc.JsonBody(), location="body")
def save_project(request):
    req = request.json
    # check_prj_duplicate(req["name"])  # check if the project id is already present
    p = Project(**request.json)
    pdao.save(p)
    res = p.info()
    return sjson(res)


"""
@bp.post("/projects/import")
# @doc.consumes(doc.String(name="file"), location="query")
@doc.consumes(doc.JsonBody(), location="body")
def import_project(request):
    if request.files:
        f = request.files.get("file")
        bb = io.BytesIO(f.body)
        bb.seek(0)
        prj_str = bb.getvalue().decode()
        prj = json.loads(prj_str)
        prj = get_updated_prj_structure(prj)
        prj_id = prj["id"]
        prj_name = Path(f.name).stem
        check_prj_duplicate(prj_name)
        try:
            check_prj_id_duplicate(prj_id)
        except:
            prj_id = uuid4()
        pdao.save_json(id=prj_id, o=prj, f_name=prj_name, update=False)
    prj = pdao.get(prj_id)
    return sjson(prj.info())
    # except Exception as e:
    #     print("nella eccezione::: ", e)
    #     raise e
"""


@bp.put("/projects/<id>")
@doc.consumes(doc.JsonBody(), location="body")
@doc.consumes(doc.Boolean(name="emit_msg"), location="body")
async def update_project(request, id):
    # user, role = get_user_role(request)
    # print(request.json)
    pdao.save_json(id, request.json)
    d = dict(id=id)

    emit_msg = request.args.get("emit_msg", "true").capitalize()
    if eval(emit_msg):
        await emit(sio, "project", d)
    return sjson(request.json)


@bp.patch("/projects/<id>")
@doc.consumes(doc.JsonBody(), location="body")
def update_info_project(request, id):
    new_name = request.json["new_name"]
    prj = pdao.get(id)
    """if prj.name != new_name:
        check_prj_duplicate(new_name)"""
    pdao.rename(id, new_name)
    return sjson(pdao.get(new_name).info())


@bp.get("/templates")
def templates(request):
    templates = tdao.all()
    templates_info = [tdao.get(t).info() for t in templates]
    return sjson(templates_info)


def myjson(o, headers=None):
    # print(headers)
    logger.debug(headers)
    return HTTPResponse(json.dumps(o, default=GenericJsonEncoder().default), content_type="application/json",
                        headers=headers)


@bp.get("/templates/<id>")
def template_by_id(request, id):
    return myjson(tdao.get(id))


@bp.put("/templates/<id>")
@doc.consumes(doc.JsonBody(), location="body")
def update_template(request, id):
    tdao.save_json(id, request.json)
    return sjson(request.json)


@bp.delete("/templates/<id>")
def delete_template(request, id):
    tdao.delete(id)
    return sjson(dict(template=id))


@bp.post("/templates")
@doc.consumes(doc.JsonBody(), location="body")
def save_template(request):
    # print("jsorn req", request.json)
    logger.debug("json req {req}".format(req=request.json))
    tdao.save_json(request.json['id'], request.json['graph'])
    return sjson(request.json)


@bp.patch("/templates/<id>")
def update_info_templates(request, id):
    tdao.update(id, request.json)
    return sjson(tdao.get(request.json["new_id"]).info())


@bp.get("/components/preview/<edge_id>")
async def component_preview(request, edge_id):
    # print("EEEI", edge_id, cached_messages)

    if edge_id in cached_messages:
        return myjson(cached_messages[edge_id])
    return sjson("No preview available")


@bp.get("/resources")
def resources(request):
    prjs = pdao.all(info=True)
    prjs_info = [pdao.get(p["id"]).info() for p in prjs]
    templates = tdao.all()
    templates_info = [tdao.get(t).info() for t in templates]
    res = dict(components=get_components(), projects=prjs_info, templates=templates_info)
    return myjson(res)  # gateway=EXTERNAL_GATEWAY,


@bp.get("/components/<id>")
def components(request, id):
    return myjson(pdao.get_components(id))


"""@bp.get("/forms")
@doc.consumes(doc.Boolean(name="partial_fit"))
@doc.consumes(doc.Boolean(name="proba"))
@doc.consumes(doc.String(name="framework", choices=["sklearn", "ds4biz"]))
@doc.consumes(doc.String(name="task", choices=["classification", "regression"]))
@doc.consumes(doc.String(name="service"), required=True)
async def forms(request):
    service = get_value(request.args, "service", "predictor", str)
    task = get_value(request.args, "task", "classification", str)
    framework = get_value(request.args, "framework", "none", str)
    partial_fit = get_value(request.args, "partial_fit", "false", str)
    proba = get_value(request.args, "proba", "false", str)
    return sjson(await all_forms(service, task=task, framework=framework, partial_fit=partial_fit, proba=proba))


@bp.post("/forms")
@doc.consumes(doc.JsonBody(), location="body")
@doc.consumes(doc.String(name="service"), required=True)
async def get_form_by_bp(request):
    service = get_value(request.args, "service", "predictor", str)
    return sjson(await get_form(service, request.json))"""


@bp.post("/projects/<project_id>/trigger")
@doc.consumes(doc.JsonBody(), location="body")
async def message(request, project_id):
    # print("EMIT TRIGGER", project_id)
    logger.debug("EMIT TRIGGER %s" % project_id)
    bth = dict()
    headers = dict(request.headers)
    if "authorization" in headers:
        bth["authorization"] = headers.pop("authorization")

    # user, role = get_user_role(request)
    # print("USER OBJ ", user)
    # logger.debug("USER OBJ %s" % user)
    id = request.json['id']
    project = pdao.get(project_id)
    now = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    alias = None

    try:
        pid, nodes, edges, graphs = get_project_info(project)
        processors, metadata = project2processor(id, pid, nodes, edges, tab=graphs[id], headers=bth)
        alias = metadata[id].values.get("alias") or metadata[id].name
    except Exception as inst:
        logging.exception(inst)
        alias = nodes[id].values.get('alias', '')
        if alias:
            start_c = "'" + alias + "' (" + nodes[id].name + ')'
        else:
            start_c = nodes[id].name
        id, name, group, *error = str(inst).split()
        error = ' '.join(error)
        msg = f"Can't start flow - TAB: '{graphs[id]}' - START: {start_c} - COMPONENT: {name} - ERROR: {error}"
        info = dict(uid=str(uuid4()), timestamp=now, tab=graphs[id], id=id, name=name, project=project_id, group=group,
                    type='error', data=f"Can't start flow - ERROR: {error}")
        await emit(sio, "messages", info)
        print(traceback.format_exc())
        raise Exception(msg)

    if id in flows:
        msg = f"Flow already running!"
        info = dict(timestamp=now, project=project_id, source=alias, data=msg, uid=str(uuid4()), type="error")
        await emit(sio, "messages", info)
        return sjson("ok")

    loop = asyncio.get_event_loop()
    # tid = str(uuid4())
    t = loop.create_task(task(id, processors[id].consume(None, flush=True)))
    # t=loop.run_in_executor(POOL,task(tid,processors[id].consume(None)))
    flows[id] = t
    flows_info[id] = dict(startedAt=now, graph=graphs[id], project=project_id, source=alias, user="user")
    logger.debug("Emitting info")
    # await sio.emit("info",dict(uid=str(uuid4()),value="Flow started"))

    return sjson("ok")


def get_value(args, key, default, conv=int):
    if key in args:
        return conv(args.get(key))
    else:
        return default


"""
@bp.post("/files/zip")
@doc.consumes(doc.JsonBody(fields={"paths": list}), location="body")
@doc.consumes(doc.String(name="folder_name"), location="query")
def get_zip(request):
    paths = request.json.get("paths")
    folder_name = request.args.get("folder_name", "compressed_archive")
    l = []
    for p in paths:
        r = unquote(str(fsdao.real(p)))
        l.append(r)
    z = files2zip(l, folder_name)
    # headers = {'Content-Disposition': 'attachment; filename="{}"'.format(f'{str(uuid4())}.zip')}
    # response.raw(body=z.read(), headers=headers, content_type="application/zip")
    return response.text("file/s correctly compressed")


@bp.get("/files/unzip")
# @doc.consumes(doc.JsonBody(fields={"paths":list}), location="body")
@doc.consumes(doc.String(name="file"), location="query")
def get_unzipped(request):
    # implementare possibilita' di non salvare il file zippato automaticamente, ma passarlo in download
    file = request.args.get("file")
    zip2files(file)
    return text("file correctly unzipped")"""


@bp.get("/files")
@bp.get("/files/<path:path>")
@doc.consumes(doc.Integer(name="start"), location="query")
@doc.consumes(doc.Integer(name="end"), location="query")
@doc.consumes(doc.Boolean(name="files"), location="query")
@doc.consumes(doc.Boolean(name="directories"), location="query")
@doc.consumes(doc.String(name="search"), location="query")
@doc.consumes(doc.String(name="path"), location="path")
def get_files(request, path=None):
    try:
        logger.debug("PATH %s" % path)
        try:
            path = unquote(path) or "/"
        except:
            raise SanicException(message="Path not correctly specified", status_code=400)
        if not fsdao.exists(path):
            raise NotFound(f"Path {path} not found")
        if not fsdao.is_dir(path) and "." in path:
            path = Path(path)
            # if path.suffix==".project":
            #     print("rientr")
            #     parent_path = path.parent
            #     prj = pdao.get(path.stem)
            #     name = prj.id
            #     # fsdao.copy(path, parent_path/name)
            res = fsdao.response(path)
            return res
        start = get_value(request.args, "start", 0)
        end = get_value(request.args, "end", 10)
        files = get_value(request.args, "files", True, lambda x: x == "true")
        directories = get_value(request.args, "directories", True, lambda x: x == "true")
        search = get_value(request.args, "search", "", str).strip()
        filter = None
        if search:
            filter = lambda x: search in x.name.lower()

        ret = fsdao.ls(path or "/", filter=filter)
        sliced = dict(type=fsdao.get_type(path), items=ret[start:end])
        return myjson(sliced, headers={"Range": len(ret)})
    except Exception as e:
        code = e.status_code
        logging.exception(e)
        raise SanicException(e, status_code=code)


@bp.put("/files")
@bp.put("/files/<path:path>")
@doc.consumes(doc.String(name="output", choices=["xlsx", "csv", "txt"]), required=False)
def update_files(request, path=None):
    if "cloud-storage" in path:
        p = Path(path or "/")
        if request.files:
            f = request.files.get("file")
            fsdao.save(p, f, headers=request.headers)
        elif request.body:
            bb = io.BytesIO(request.body)
            bb.seek(0)
            fsdao.save(p, bb, headers=request.headers)
        else:
            fsdao.mkdir(p, headers=request.headers)
    else:
        if request.files:
            f = request.files.get("file")
            p = Path(path or "/") / f.name
            bb = io.BytesIO(f.body)
            bb.seek(0)
            fsdao.save(p, bb)
        elif request.body:
            p = Path(path)
            bb = io.BytesIO(request.body)
            bb.seek(0)
            fsdao.save(p, bb)
    return myjson("ok")


@bp.post("/files")
@bp.post("/files/<path:path>")
@doc.consumes(doc.String(name="output", choices=["xlsx", "csv", "txt"]), required=False)
def create_file(request, path=None):
    if "cloud-storage" in path:
        p = Path(path or "/")
        if request.files:
            f = request.files.get("file")
            fsdao.save(p, f, headers=request.headers)
        elif request.body:
            bb = io.BytesIO(request.body)
            bb.seek(0)
            fsdao.save(p, bb, headers=request.headers)
        else:
            fsdao.mkdir(p, headers=request.headers)
    else:
        if request.files:
            f = request.files.get("file")
            p = Path(path or "/") / f.name
            # check_special_characters(p.stem)
            # check_for_duplicate(p, f.name)
            """if p.suffix == ".project":
                check_prj_duplicate(p.stem)
            else:
                check_for_duplicate(p, f.name)"""
            bb = io.BytesIO(f.body)
            bb.seek(0)
            if p.suffix == ".project":
                prj = eval(bb.getvalue())
                prj_id = prj["id"]
                parent = p.parent
                p = parent / (prj_id + ".project")
            fsdao.save(p, bb)
        elif request.body:
            p = Path(path)
            if not p.suffix:
                raise SanicException('Add file extension',
                                     status_code=400)
            """check_for_duplicate(p, p.name)
            check_special_characters(p.stem)"""
            bb = io.BytesIO(request.body)
            bb.seek(0)
            fsdao.save(p, bb)

        else:
            """check_for_duplicate(path, path)
            check_special_characters(path.split('/')[-1])"""
            fsdao.mkdir(path)
    return myjson("ok")


@bp.delete("/files/<path:path>")
@doc.consumes(doc.String(name="path"), location="path")
def delete_file(request, path):
    # check_protected_folders(path)
    path = unquote(path)
    fsdao.delete(path)
    return myjson("ok")


@bp.patch("/files/<path:path>")
@doc.consumes(doc.Object(name="newPath", cls=dict), location="body")
def move_file(request, path):
    # check_protected_folders(path)
    path = Path(unquote(path))
    newpath = Path(request.json['path'])
    if path.suffix and not newpath.suffix:
        raise SanicException('Add file extension', status_code=400)
    # check_special_characters(newpath.stem)
    # check_for_duplicate(path, newpath)
    fsdao.move(path, newpath)
    return myjson("ok")


@bp.post("/copy/<path:path>")
@doc.consumes(doc.Object(name="newPath", cls=dict), location="body")
def copy(request, path):
    path = unquote(path)
    newpath = unquote(request.json['path'])
    fsdao.copy(path, newpath)

    return myjson("ok")


@bp.get("/build/<id>")
@doc.consumes(doc.String(name="id"), location="path", required=True)
def build(request, id):
    print(pdao.path / id)
    build_extension_image(pdao.path / id)
    run_extension_image(id, GATEWAY)
    return myjson("ok")


@bp.post("/extensions/<id>")
@doc.consumes(doc.String(name="id"), location="path", required=True)
def build(request, id):
    pdao.new_extension(id)

    return myjson("ok")


"""
@bp.get("/preview/<path:path>")
@doc.consumes(doc.String(name="separator"), required=False, location="query")
@doc.consumes(doc.Integer(name="nrows"), required=False, location="query")
def preview(request, path=None):
    if path:
        path = unquote(path)
    separator = request.args.get("separator")
    ext = request.args.get('output') or infer_ext(Path(path), FORMATS2JSON, default='csv')
    ret = FORMATS2JSON[ext](path, int(request.args.get("nrows", 50)),
                            delimiter=separator)

    return sjson(ret)


@bp.get("/files/convert/")
@doc.consumes(doc.String(name="fname"), required=True, location="query")
@doc.consumes(doc.String(name="output_format", choices=["csv"]), required=True)
@doc.consumes(doc.String(name="input_format", choices=["xls"]), required=True)
async def file_conv(request):
    # print("aaaa ",request.json)
    headers = dict(request.headers)
    auth_headers = dict()
    if "authorization" in headers:
        auth_headers["authorization"] = headers.pop("authorization")
    input_format = request.args.get("input_format")
    output_format = request.args.get("output_format")
    fname = request.args.get('fname')
    # print("stiamo convertendo...", fname)
    fc = FileConverter()
    # print(fname)
    r = await fc.convert(fname, input_format, output_format, auth_headers)
    # print("rrrrrrrrrrrrrrrrr ",r)
    return r


@bp.put("/plugins")
@doc.consumes(doc.JsonBody(), location="body")
async def install_plugin(request):
    PLUGIN_DAO.update(Plugin(**request.json))
    return myjson("OK")


@bp.get("/plugins")
async def plugins(request):
    ret = PLUGIN_DAO.all()
    return myjson(ret)


@bp.post("/plugins")
@doc.consumes(doc.JsonBody(), location="body")
async def new_plugin(request):
    p = Plugin(**request.json)
    PLUGIN_DAO.save(p)


@bp.get("/commands/files")
@doc.consumes(doc.Integer(name="cmd"), location="query")
def exec_files_command(request):
    search = get_value(request.args, "cmd", "", str)
    if search:
        pass"""


@app.listener('before_server_stop')
def term(app, loop):
    exit(0)


@app.listener("before_server_start")
async def b(app, loop):
    connected = False
    while not connected:
        try:
            await sio.connect(GATEWAY, wait=True)
            connected = True
        except ConnectionError as inst:
            print("Trying to connect to socket")
            await asyncio.sleep(2)
    print("Connected to socket")

    # loop.create_task(services_scan())

    total_timeout = ClientTimeout(total=ASYNC_SESSION_TIMEOUT)
    # app.aiohttp_session = ClientSession(loop=loop, timeout=total_timeout)


@app.exception(Exception)
async def manage_exception(request, exception):
    if isinstance(exception, NotFound):
        return sanic.json(str(exception), status=404)
    print(traceback.format_exc())
    return sanic.json(str(exception), status=500)


@sio.event
def connect_error(message):
    print('Connection was rejected due to ' + str(message))


@sio.event
async def disconnect():
    logger.debug('DISCONNECTED!!')


@app.exception(Exception)
async def generic_exception(request, exception):
    e = str(exception)
    j = dict(error=e)
    if not isinstance(exception, sanic.exceptions.NotFound):
        logger.debug(traceback.format_exc())
        logging.exception(exception)
    else:
        logger.debug(f'NOTFOUND EXCEPTION: {e}')
    status_code = exception.status_code or 500
    if isinstance(exception, NotFound):
        return sanic.json(j, status=404, headers={"Access-Control-Allow-Origin": "*"})
    return sanic.json(j, status=status_code, headers={"Access-Control-Allow-Origin": "*"})


app.blueprint(bp)

app.error_handler.add(Exception, generic_exception)

if __name__ == "__main__":
    # for el in fsdao.ls():
    #     print(type(el),el)
    #
    # print(fsdao.real('anomaly_report.csv'))
    # app.update_config(dict(GRACEFUL_SHUTDOWN_TIMEOUT=0))
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG, auto_reload=True)
