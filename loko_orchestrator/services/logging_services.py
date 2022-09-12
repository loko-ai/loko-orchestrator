from sanic import json

from loko_orchestrator.business.builder.dockermanager import DockerMessageCollector


def add_logging_services(app, bp):
    @bp.route("/events")
    async def get_events(request):
        mc: DockerMessageCollector = app.ctx.message_collector
        return json(mc.events)

    @bp.route("/logs")
    async def get_logs(request):
        mc: DockerMessageCollector = app.ctx.message_collector
        return json(dict(logs=mc.logs, labels=mc.labels))
