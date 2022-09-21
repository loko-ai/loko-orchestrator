from sanic import json

from loko_orchestrator.business.builder.dockermanager import DockerMessageCollector
from loko_orchestrator.business.log_collector import LogCollector


def add_logging_services(app, bp):
    @bp.route("/events")
    async def get_events(request):
        # mc: DockerMessageCollector = app.ctx.message_collector
        return json([])

    @bp.route("/logs")
    async def get_logs(request):
        log_collector: LogCollector = app.ctx.log_collector
        labels = {x: "loko_project" for x in log_collector.logs.keys()}

        return json(dict(labels=labels, logs=log_collector.logs))
        # return json(dict(logs=mc.logs, labels=mc.labels))
