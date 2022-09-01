from pathlib import Path

from loko_orchestrator.utils.config_utils import EnvInit

e = EnvInit()
PORT = e.get("PORT", 8888)
DEBUG = e.get("DEBUG", False)
PUBLIC_FOLDER = Path(e.get("PUBLIC_FOLDER", Path.home() / "loko"))
PUBLIC_FOLDER.mkdir(exist_ok=True)
GATEWAY = e.get("GATEWAY", "http://localhost:8080")
EXTERNAL_GATEWAY = e.get("EXTERNAL_GATEWAY", GATEWAY)
ASYNC_SESSION_TIMEOUT = e.get("ASYNC_SESSION_TIMEOUT", 5 * 60)
DEVELOPMENT = False
PROJECTS_LIMIT = 3
CORS_ON = e.get("CORS_ON", True)
