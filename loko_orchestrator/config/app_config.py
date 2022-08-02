import asyncio
import os
from pathlib import Path

# from ds4biz_commons.utils.dict_utils import ObjectDict
# from ds4biz_commons.utils.requests_utils import URLRequest
from socketio import AsyncClient

# from ds4biz_orchestrator.config.inititalize import mount_ms_daos
from loko_orchestrator.dao.fs import FSDao, LayeredFS
# from ds4biz_orchestrator.dao.plugins import PluginDAO

# from ds4biz_orchestrator.utils.codeutils import load_external_modules
# from ds4biz_orchestrator.utils.pathutils import find_file
from loko_orchestrator.utils.config_utils import EnvInit

e = EnvInit()

PORT = e.get("PORT", 8888)

DEBUG = e.get("DEBUG", False)
PUBLIC_FOLDER = Path(os.environ.get("PUBLIC_FOLDER", Path.home() / "loko"))
PUBLIC_FOLDER.mkdir(exist_ok=True)
GATEWAY = e.get("GATEWAY", "http://localhost:8080")
# FILE_CONVERTER_URL = e.get("FILE_CONVERTER_URL", "http://file-convert:8080/file-convert/0.0/convert")
EXTERNAL_GATEWAY = e.get("EXTERNAL_GATEWAY", GATEWAY)
ASYNC_SESSION_TIMEOUT = e.get("ASYNC_SESSION_TIMEOUT", 5 * 60)
# TOKEN_EXPIRATION = e.get("TOKEN_EXPIRATION", 7 * 24 * 60 * 60)
# token = e.get("BEARER_TOKEN", "")
# BEARER_TOKEN = "Bearer {}".format(token) if token else ""
CORS_ON = e.get("CORS_ON", True)
# APP_USERNAME = e.get("APP_USERNAME", "admin")
# APP_PASSWORD = e.get("APP_PASSWORD", "admin")
print("CORS", CORS_ON)

# PLUGIN_DAO = PluginDAO()

sio = AsyncClient(reconnection=True, reconnection_delay=1)

fs_dao = FSDao(PUBLIC_FOLDER, lambda x: x.suffix == ".metadata")
fsdao = LayeredFS()
fsdao.mount("data", fs_dao)

"""async def services_scan():
    global BEARER_TOKEN

    url = URLRequest(GATEWAY)

    t = 3
    while True:

        try:
            r = url.auth.post()  # json=dict(username=APP_USERNAME, password=APP_PASSWORD)
            r = ObjectDict(r)
            BEARER_TOKEN = f"Bearer {r.access_token}"
            if BEARER_TOKEN:
                print(BEARER_TOKEN, "*" * 100)
                try:
                    #mount_ms_daos(fsdao, GATEWAY, BEARER_TOKEN)
                    break
                except Exception as inst:
                    print("Gateway or service not available")
        except Exception as inst:
            print("Can't retrieve JWT token")

        finally:
            await asyncio.sleep(t)
            t += 5
            t = min(30, t)"""

print(PUBLIC_FOLDER)
pdao = None
tdao = None


def init():
    from loko_orchestrator.dao.projects import FSProjectDAO, TemplateDAO

    global pdao, tdao
    pdao = FSProjectDAO(PUBLIC_FOLDER / "projects", ".project")
    tdao = TemplateDAO(PUBLIC_FOLDER / "templates")

# EXTERNAL_MODULES = {}
# imports = find_file("imports.json")
# print("Imports", imports)
# if imports:
#    EXTERNAL_MODULES = load_external_modules(imports)
