import logging
import time
from pathlib import Path

import docker
import requests
from docker.errors import NotFound

client = docker.APIClient(base_url='unix://var/run/docker.sock')


def build_extension_image(path):
    path = Path(path)
    for line in client.build(path=str(path), decode=True, tag=f"{path.name}",
                             buildargs=dict(GATEWAY="http://localhost:8080")):
        if "stream" in line:
            msg = line['stream'].strip()
            if msg:
                print(msg)


def run_extension_image(id, gw):
    client = docker.from_env()
    for c in client.containers.list(filters={"label": "type=loko"}):
        try:
            c.stop(timeout=3)
            c.kill()
        except:
            try:
                print(c.kill())
            except Exception as inst:
                print("Killalo!", inst)
        while c.status == "running":
            print(c.status)
            try:
                c.reload()
                print(c.status)
                time.sleep(2)
                break
            except NotFound:
                break
            except Exception as inst:
                logging.exception(inst)
                print(inst, "Non c'è")
    resp = requests.post(gw + "/rules", json={
        "name": id,
        "host": "localhost",
        "port": 8083,
        "type": "custom",
        "scan": False
    })
    print(resp.text)
    print(client.containers.run(id, name=id, ports={8080: 8083}, detach=True, labels={"type": "loko"}, remove=True,
                                network="loko"))
    print(f"Deployed {id}")


if __name__ == "__main__":
    id = "cincilla"
    build_extension_image(f"/home/fulvio/loko/projects/{id}")
    run_extension_image(id, "http://localhost:8080")
