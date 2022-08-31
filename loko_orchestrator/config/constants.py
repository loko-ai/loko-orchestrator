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
LICENSE_VALIDATION_URL = e.get("LICENSE_VALIDATION_URL","https://api.keygen.sh/v1/accounts/f4e70b1a-040e-495f-9d79-1ff16d44c2b1/licenses/actions/validate-key")
DEVELOPMENT = False
PROJECTS_LIMIT = 3
CORS_ON = e.get("CORS_ON", True)
