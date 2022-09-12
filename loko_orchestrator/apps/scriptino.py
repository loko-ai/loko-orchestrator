import json
import sys

import requests


def validate(key, account_id):
    data = requests.post(
        "https://api.keygen.sh/v1/accounts/{}/licenses/actions/validate-key".format(account_id),
        headers={
            "Content-Type": "application/vnd.api+json",
            "Accept": "application/vnd.api+json"
        },
        data=json.dumps({
            "meta": {
                "key": key
            }
        })
    ).json()

    ret = data["meta"].get("valid")

    if ret:
        return data["meta"].get("valid")
    return False


if __name__ == '__main__':
    # account_id = "f4e70b1a-040e-495f-9d79-1ff16d44c2b1"
    # key = "FD33E5-B11056-FE8959-699E72-66175C-V3"
    print(sys.argv[1], sys.argv[2])
    print(validate(sys.argv[1], sys.argv[2]))
