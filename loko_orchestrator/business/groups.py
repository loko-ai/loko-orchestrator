import json
import logging
from os.path import join
from pathlib import Path
from urllib.parse import urljoin

import aiodocker
import requests

from loko_orchestrator.business.components.collections import GrouperComponent, HeadComponent, SamplerComponent
from loko_orchestrator.business.components.commons import Debug, Function, Trigger, Array, Selector, MergeComponent, \
    SwitchComponent, Template, FilterComponent, Value, Renamer, Custom, SharedExtension, EventComponent, Globals
from loko_orchestrator.business.components.ds4biz import Predictor
from loko_orchestrator.business.components.http import HTTPReq, HTTPResponse, HTTPRoute
from loko_orchestrator.business.components.io import CSVReaderComponent, DirectoryComponent, FileContent, FileReader, \
    LineReaderComponent, CSVWriterComponent, FileWriterComponent, WireIn, WireOut
from loko_orchestrator.business.components.time import DelayComponent

# from loko_orchestrator.config import app_config
# from loko_orchestrator.config.app_config import pdao
from loko_orchestrator.config.constants import PUBLIC_FOLDER, GATEWAY

COMPONENTS = []

COMPONENTS.append(dict(group="Common",
                       components=[Array(), Debug(), FilterComponent(), Function(),
                                   GrouperComponent(), HeadComponent(), MergeComponent(), Renamer(), SamplerComponent(),
                                   Selector(),
                                   SwitchComponent(), Trigger(), EventComponent(), Globals()]))  # , FileConverter()]))

COMPONENTS.append(dict(group="HTTP", components=[HTTPReq(), HTTPResponse(), HTTPRoute(), Template()]))
COMPONENTS.append(
    dict(group="Inputs",
         components=[CSVReaderComponent(), DirectoryComponent(), FileContent(), FileReader(), LineReaderComponent(),
                     WireIn()]))
# COMPONENTS.append(dict(group="Integrations", components=[EmailListener(), EmailReader()]))
COMPONENTS.append(dict(group="Outputs", components=[CSVWriterComponent(), FileWriterComponent(), WireOut()]))
COMPONENTS.append(dict(group="Time", components=[DelayComponent()]))
# COMPONENTS.append(dict(group="Custom", components=[DelayComponent(), CSVWriterComponent()]))
# COMPONENTS.append(dict(group="Cloud",components=[SageMaker(),AzureML(),GoogleML()]))
# COMPONENTS.append(dict(group="Brokers",components=[RabbitMQ(),Kafka(),MQTT()]))

ms = [
    # Anonymizer(),
    # Crumbs(),
    # EmailListener(),
    # Entities(),
    # Faker(), Matcher(), NLP(), Predictor(), Storage(), Textract(), Vision()
    Predictor()
]

FACTORY = {}
for g in COMPONENTS:
    for comp in g['components']:
        FACTORY[comp.name] = comp

for el in ms:
    FACTORY[el.name] = el


# aggiungere componenti ds4biz

def get_components():
    ds4biz = []
    try:
        for el in ms:
            _rtype = getattr(el, "microservice", None)
            el.disabled = False
            if _rtype:
                _type = urljoin(GATEWAY, join("services", _rtype))
                avail = requests.get(_type).json()
                if not avail:
                    el.disabled = True
            else:
                el.disabled = True

            ds4biz.append(el)


    except Exception as inst:
        print("No gateway")
        logging.exception(inst)

    return [dict(group="DS4Biz", components=ds4biz)] + [
        dict(group="Global", components=get_global_extensions())] + COMPONENTS


def is_extension(path: Path):
    return len(list(path.glob("**/components.json"))) == 1


def get_global_extensions():
    ext = PUBLIC_FOLDER / "shared/extensions"
    custom = []

    if ext.exists():
        for el in ext.iterdir():
            if el.is_dir():
                temp = list(el.glob("**/components.json"))
                if len(temp) == 1:
                    conf = temp[0]
                    with open(conf) as comp:
                        try:
                            for d in json.load(comp):
                                c = SharedExtension(pname=el.name, **d)
                                custom.append(c)
                                FACTORY[c.name] = c
                        except Exception as e:
                            logging.exception(e)

    return custom


async def deployed_extensions():
    ext = PUBLIC_FOLDER / "shared/extensions"
    custom = []
    client = aiodocker.Docker()
    ret = []

    if ext.exists():
        for el in ext.iterdir():
            if el.is_dir():
                temp = list(el.glob("**/components.json"))
                if len(temp) == 1:
                    try:
                        temp = dict(name=el.name, status="off")
                        ret.append(temp)
                        await client.containers.get(el.name)
                        temp["status"] = "deployed"
                    except Exception as inst:
                        print(el.name, inst)

    await client.close()
    return ret
