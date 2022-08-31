import asyncio
import logging
from pprint import pprint

from loko_orchestrator.business.components.commons import Custom
from loko_orchestrator.business.converters import get_project_info
from loko_orchestrator.business.engine import DummyProcessor, BatchedNotifier, Constant, MessageCollector, Fun, \
    Processor
from loko_orchestrator.business.groups import FACTORY
from loko_orchestrator.config.app_config import pdao, sio
from loko_orchestrator.config.constants import GATEWAY
from loko_orchestrator.dao.projects import FSProjectDAO
from loko_orchestrator.utils.logger_utils import logger

cached_messages = {}


class ProjectConverter:
    def __init__(self, pdao: FSProjectDAO, notifier):
        self.pdao = pdao
        self.notifier = notifier

    def project2processor(self, id, pid, nodes, edges, tab, factory, collect=False, **kwargs):
        def create_component(n):
            cc = factory[n.name]
            try:
                logger.debug('VALUES: {val}'.format(val=n.values))
                processors[n.id] = cc.create(id=n.id, name=n.name, gateway=GATEWAY, headers=headers, project_id=pid,
                                             **n.values)
            except Exception as inst:
                # print(traceback.format_exc())
                logging.exception(inst)
                processors[n.id] = DummyProcessor(id=n.id, name=n.name)
                errors[n.id] = inst
            comp = processors[n.id]
            print("DATTAAAAA", n.name, n.id)
            notifier = self.notifier(pid, n, tab=tab)
            for output in n.outputs:
                comp.pipe(notifier, output=output)

            # Il componente debug non ha outputs
            if n.name == "Debug":
                comp.pipe(notifier)

            for output in n.outputs:
                f = Constant((n.id, output['id']), name='Constant')

                comp.pipe(f, output=output)
                # f.pipe(animation)

            if collect:
                comp = processors[n.id]
                collector = MessageCollector(cached_messages, comp)
                for output in n.outputs:
                    comp.pipe(collector, output=output)

        headers = dict()
        if "headers" in kwargs:
            headers.update(kwargs["headers"])
        processors = dict()
        errors = dict()

        # animation = AnimationNotifier(sio, "animation", loop=asyncio.get_event_loop(), time=.25, name='AnimationNotifier')

        queue = [id]
        visited = [id]

        create_component(nodes[id])

        alias = nodes[id].values.get('alias')
        name = nodes[id].name
        if isinstance(processors[id], DummyProcessor):
            if alias:
                start_c = "'" + alias + "' (" + nodes[id].name + ')'
            else:
                start_c = nodes[id].name
            logging.warning(
                f"COMPONENT: {start_c} - ERROR: {errors.get(id)}")
            raise Exception(f"{id} {alias or nodes[id].name} {nodes[id].options['group']} {errors.get(id)}")

        while queue:
            s = queue.pop(0)
            n1 = nodes[s]
            logger.debug("START %s" % str(nodes[s].values.get('alias') or nodes[s].name))
            # print('START', nodes[s].values.get('alias') or nodes[s].name)
            for neighbour_dict in edges[s]:
                neighbour = neighbour_dict['end']
                n2 = nodes[neighbour]
                if neighbour not in visited:
                    alias = nodes[neighbour].values.get('alias')
                    name = nodes[neighbour].name
                    # print('END', nodes[neighbour].values.get('alias') or nodes[neighbour].name)
                    logger.debug("END %s" % str(nodes[neighbour].values.get('alias') or nodes[neighbour].name))
                    create_component(n2)
                    if isinstance(processors[n2.id], DummyProcessor):
                        if alias:
                            start_c = "'" + alias + "' (" + nodes[n2.id].name + ')'
                        else:
                            start_c = nodes[n2.id].name
                        logging.warning(
                            f"COMPONENT: {start_c} - ERROR: {errors.get(n2.id)}")
                        raise Exception(
                            f"{n2.id} {alias or nodes[n2.id].name} {n2.options['group']} {errors.get(n2.id)}")

                    visited.append(neighbour)
                    queue.append(neighbour)

                p1 = processors[n1.id]
                p2 = processors[n2.id]

                p1.pipe(p2, output=neighbour_dict['endp1'], input=neighbour_dict['endp2'])

        return processors, nodes


id = "sss"
exts = pdao.get_extensions(id)

p = pdao.get(id)

for n in p.nodes():
    print(n[0].id, n[0].data['name'])

cid = "e2dad28b-ea0d-4338-bcf1-1be549766bf3"
id, nodes, edges, graphs = get_project_info(p)



def bn(pid, n, tab):
    return BatchedNotifier(pid, n.values.get("alias") or n.name, n.id, n.options["group"], sio, "messages",
                           loop=asyncio.get_event_loop(),
                           time=.25, max_messages=200, debug=bool(n.values.get("debug")), tab=tab)


def ln(pid, n, tab):
    return Fun(lambda x: print(pid, tab, x))


class Logger(Processor):

    async def process(self, value, input="input", **kwargs):
        print(value)


print(graphs)
factory = dict(FACTORY)

for el in pdao.get_extensions(id):
    factory[el['name']] = Custom(**el)

pc = ProjectConverter(pdao, Logger)
proc, nodes = pc.project2processor(cid, id, nodes, edges, graphs[cid], factory)

print(proc[cid])


async def main():
    await proc[cid].consume(None, flush=True)


asyncio.run(main())
