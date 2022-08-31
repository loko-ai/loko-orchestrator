import logging
import traceback
from collections import defaultdict

from loko_orchestrator.business.components.io import WireIn, WireOut
# from loko_orchestrator.business.groups import FACTORY
from loko_orchestrator.business.groups import FACTORY
from loko_orchestrator.config.app_config import GATEWAY, sio
from loko_orchestrator.business.engine import Notifier, BatchedNotifier, MessageCollector, Constant, DummyProcessor
# from loko_orchestrator.business.notifiers import AnimationNotifier
import asyncio

from loko_orchestrator.model.projects import NodeInfo
from loko_orchestrator.utils.logger_utils import logger

cached_messages = {}


def get_project_info(p):
    edges = defaultdict(list)
    nodes = dict()
    graphs = dict()
    for n, graph_id in p.nodes():
        ### altrimenti e' un commento!
        if 'options' in n.data:
            nodes[n.id] = NodeInfo(n)
            graphs[n.id] = graph_id

    for e in p.edges():
        start_closed = [el for el in nodes[e.source].outputs if (el['id'] == e.sourceHandle and el.get('closed'))]
        end_closed = [el for el in nodes[e.target].inputs if (el['id'] == e.targetHandle and el.get('closed'))]

        if not (start_closed or end_closed):
            edges[e.source].append(dict(end=e.target,
                                        endp1=e.sourceHandle,
                                        endp2=e.targetHandle))
    wireouts = defaultdict(list)
    for n in nodes.values():
        if n.name == "Wire Out":
            wire_in = n.values['wire_in']
            wireouts[wire_in].append(n)
    for n in nodes.values():
        if n.name == "Wire In":
            wire_in = n.values['alias']
            for target in wireouts[wire_in]:
                print(n.id, target.id)
                edges[n.id].append(dict(end=target.id, endp1="output", endp2="input"))

    return p.id, nodes, edges, graphs


def project2processor(id, pid, nodes, edges, tab, factory, collect=False, **kwargs):
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
        notifier = BatchedNotifier(pid, n.values.get("alias") or n.name, n.id, n.options["group"], sio, "messages",
                                   loop=asyncio.get_event_loop(),
                                   time=.25, max_messages=200, debug=bool(n.values.get("debug")), tab=tab)
        for output in n.outputs:
            print(n.name, n.id, notifier.sid, output)
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
                    raise Exception(f"{n2.id} {alias or nodes[n2.id].name} {n2.options['group']} {errors.get(n2.id)}")

                visited.append(neighbour)
                queue.append(neighbour)

            p1 = processors[n1.id]
            p2 = processors[n2.id]

            p1.pipe(p2, output=neighbour_dict['endp1'], input=neighbour_dict['endp2'])

    return processors, nodes


def node2processor(n):
    cc = FACTORY[n.name]
    return cc.create(name=n.name, gateway=GATEWAY, **n.values)
