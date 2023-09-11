from pathlib import Path

import sanic
from git import Repo
from sanic_openapi.openapi2 import doc

from loko_orchestrator.config.constants import PUBLIC_FOLDER


def git_clone(url, path: Path):
    url = url.strip()
    name = url.split("/")[-1]
    if name.endswith(".git"):
        name = name[:-4]
    Repo.clone_from(url, path / name)


def add_git_services(app, bp, sio):
    @bp.post("/git/clone")
    @doc.consumes(doc.JsonBody(), location="body")
    async def clone(request):
        url = request.json['url']
        shared = request.json.get("shared", False)
        if shared:
            git_clone(url, PUBLIC_FOLDER / "shared/extensions")
            return sanic.json(f"{url} imported")
        else:
            git_clone(url, PUBLIC_FOLDER / "projects")
            await sio.emit("system", {})
            return sanic.json(f"Extension installed")
