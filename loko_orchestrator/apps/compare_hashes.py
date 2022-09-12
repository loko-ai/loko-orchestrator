import docker
from docker.models.images import RegistryData

client = docker.from_env()

r = client.images.get_registry_data("lokoai/loko-orchestrator:0.0.2-dev")
print("Remote", r.id)
r2 = client.images.get("lokoai/loko-orchestrator:0.0.2-dev")

print("Local", r2.id)
