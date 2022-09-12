import json
from pathlib import Path
from pprint import pprint

import requests

from loko_orchestrator.config.constants import PUBLIC_FOLDER

KEYGEN_SH_ACCOUNT = "f4e70b1a-040e-495f-9d79-1ff16d44c2b1"


class LicenseManager:
    def __init__(self, path: Path):
        self.path = path
        self.valid = self.is_valid()

    def is_valid(self):
        key = self.get_license()
        return self.validate(key, KEYGEN_SH_ACCOUNT)

    def projects_limit(self):
        if self.valid:
            return 100
        else:
            return 5

    def get_license(self):
        license_path = self.path / "LICENSE.txt"
        if license_path.exists():
            try:
                with license_path.open() as f:
                    return f.read().strip()
            except Exception as e:
                print(str(e))

        print("License not found")
        return None

    def validate(self, key, account_id):
        data = requests.post(
            f"https://api.keygen.sh/v1/accounts/{account_id}/licenses/actions/validate-key",
            headers={
                "Content-Type": "application/vnd.api+json",
                "Accept": "application/vnd.api+json"
            },
            json={
                "meta": {
                    "key": key
                }
            }
        ).json()
        ret = data["meta"].get("valid")
        print("Valid", ret)

        if ret:
            return data["meta"].get("valid")
        return False


lm = LicenseManager(PUBLIC_FOLDER)
print(PUBLIC_FOLDER)
