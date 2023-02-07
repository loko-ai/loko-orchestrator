from pprint import pprint

import docker

client = docker.from_env()

img = client.images.get("prova_only_container_ext:latest")

layers = img.attrs['RootFS']['Layers']

h = img.history()

for el in h:
    print(el)
