from collections import defaultdict
from socketio import AsyncClient

from loko_orchestrator.business.groups import get_components
from loko_orchestrator.config.constants import PUBLIC_FOLDER, GATEWAY
from loko_orchestrator.dao.extensions import SharedExtensionsDAO
from loko_orchestrator.dao.fs import FSDao, LayeredFS
from loko_orchestrator.dao.projects import FSProjectDAO, TemplateDAO

sio = AsyncClient(reconnection=True, reconnection_delay=1)

fs_dao = FSDao(PUBLIC_FOLDER, lambda x: x.suffix == ".metadata")
fsdao = LayeredFS()
fsdao.mount("data", fs_dao)

pdao: FSProjectDAO = FSProjectDAO(PUBLIC_FOLDER / "projects", ".project", get_components())
tdao: TemplateDAO = TemplateDAO(PUBLIC_FOLDER / "templates")

shared_extensions_dao = SharedExtensionsDAO(PUBLIC_FOLDER / "shared/extensions", GATEWAY)

