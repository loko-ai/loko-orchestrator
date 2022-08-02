import json
import logging
from os.path import join
from urllib.parse import urljoin

import requests

from loko_orchestrator.business.components.collections import GrouperComponent, HeadComponent, SamplerComponent
from loko_orchestrator.business.components.commons import Debug, Function, Trigger, Array, Selector, MergeComponent, \
    SwitchComponent, Template, FilterComponent, Value, Renamer, Custom
from loko_orchestrator.business.components.http import HTTPReq, HTTPResponse, HTTPRoute
from loko_orchestrator.business.components.io import CSVReaderComponent, DirectoryComponent, FileContent, FileReader, \
    LineReaderComponent, CSVWriterComponent, FileWriterComponent
from loko_orchestrator.business.components.time import DelayComponent

# from loko_orchestrator.config import app_config
# from loko_orchestrator.config.app_config import pdao

COMPONENTS = []

COMPONENTS.append(dict(group="Common",
                       components=[Array(), Debug(), FilterComponent(), Function(),
                                   GrouperComponent(), HeadComponent(), MergeComponent(), Renamer(), SamplerComponent(),
                                   Selector(),
                                   SwitchComponent(), Trigger()]))  # , FileConverter()]))

COMPONENTS.append(dict(group="HTTP", components=[HTTPReq(), HTTPResponse(), HTTPRoute(), Template()]))
COMPONENTS.append(
    dict(group="Inputs",
         components=[CSVReaderComponent(), DirectoryComponent(), FileContent(), FileReader(), LineReaderComponent()]))
# COMPONENTS.append(dict(group="Integrations", components=[EmailListener(), EmailReader()]))
COMPONENTS.append(dict(group="Outputs", components=[CSVWriterComponent(), FileWriterComponent()]))
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
    """try:
        for el in ms:
            _rtype = getattr(el, "microservice", None)
            el.disabled = False
            if _rtype:
                _type = urljoin(app_config.GATEWAY, join("services", _rtype))
                avail = requests.get(_type).json()
                if not avail:
                    el.disabled = True
            else:
                el.disabled = True

            ds4biz.append(el)


    except Exception as inst:
        print("No gateway")
        logging.exception(inst)"""

    return [dict(group="DS4Biz", components=ds4biz)] + COMPONENTS
