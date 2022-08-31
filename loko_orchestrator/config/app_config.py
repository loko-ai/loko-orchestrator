import asyncio
import os
from pathlib import Path

# from ds4biz_commons.utils.dict_utils import ObjectDict
# from ds4biz_commons.utils.requests_utils import URLRequest
from socketio import AsyncClient

from loko_orchestrator.config.constants import PUBLIC_FOLDER, GATEWAY
from loko_orchestrator.dao.extensions import SharedExtensionsDAO
# from ds4biz_orchestrator.config.inititalize import mount_ms_daos
from loko_orchestrator.dao.fs import FSDao, LayeredFS
from loko_orchestrator.dao.projects import FSProjectDAO, TemplateDAO
# from ds4biz_orchestrator.dao.plugins import PluginDAO

# from ds4biz_orchestrator.utils.codeutils import load_external_modules
# from ds4biz_orchestrator.utils.pathutils import find_file
from loko_orchestrator.utils.config_utils import EnvInit

sio = AsyncClient(reconnection=True, reconnection_delay=1)

fs_dao = FSDao(PUBLIC_FOLDER, lambda x: x.suffix == ".metadata")
fsdao = LayeredFS()
fsdao.mount("data", fs_dao)

pdao: FSProjectDAO = FSProjectDAO(PUBLIC_FOLDER / "projects", ".project")
tdao: TemplateDAO = TemplateDAO(PUBLIC_FOLDER / "templates")

shared_extensions_dao = SharedExtensionsDAO(PUBLIC_FOLDER / "shared/extensions", GATEWAY)
# EXTERNAL_MODULES = {}
# imports = find_file("imports.json")
# print("Imports", imports)
# if imports:
#    EXTERNAL_MODULES = load_external_modules(imports)
