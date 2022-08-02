from loko_orchestrator.model.components import Component
from loko_orchestrator.business.engine import Delay
from loko_orchestrator.resources.doc_time_component import delay_doc


class DelayComponent(Component):
    def __init__(self):
        args = [{
            "name": "time",
            "type": "number",
            "label": "Time",
            "helper": "Expressed in milliseconds",
            "validation": {"required": "Required field"}
        }]

        super().__init__("Delay", group="Time", description=delay_doc, args=args, values=dict(time="500"),
                         icon="RiTimerFill", configured=True)

    def create(self, time, **kwargs):
        return Delay(int(time) / 1000, **kwargs)
