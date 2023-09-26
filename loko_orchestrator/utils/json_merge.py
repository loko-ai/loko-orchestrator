import json
import os
import re
import dict_path
from datetime import datetime
from pathlib import Path

import git
from loguru import logger

from loko_orchestrator.utils.dict_path_utils import SafeDictPath


class JSONMerge:
    def __init__(self, rules=None, sep='/'):
        self.rules = rules or {}
        self.conflicts = {}
        self.ne = 'not exist'
        self.sep = sep

    def merge_conflicts(self, root, local, remote, p=''):
        if local == remote:
            return local
        if isinstance(local, dict) and isinstance(remote, dict):
            root_tmp = root if isinstance(root, dict) else {}
            ret = {}
            kk = set(local).union(remote)
            for k in kk:
                res = self.merge_conflicts(root_tmp.get(k, self.ne), local.get(k, self.ne), remote.get(k, self.ne),
                                           p + self.sep + k)
                if res!=self.ne:
                    ret[k] = res
            return ret
        return self._merge(root, local, remote, p)

    def _merge(self, root, local, remote, p):
        if local != root:
            # both modified
            if remote != root:
                if remote==self.ne:
                    return local
                if local==self.ne:
                    return remote
                last_key = p.strip(self.sep).split(self.sep)[-1]
                if last_key in self.rules:
                    if self.rules[last_key]['validate'](p):
                        logger.debug(f'Apply rule: {p} - local: {local} - remote: {remote}')
                        return self.rules[last_key]['rule'](local, remote)
                logger.debug(f'Conflict on {p} - local: {local} - remote: {remote}')
                self.conflicts[p.strip(self.sep)] = dict(local=local, remote=remote)
            # only local modified
            return local
        # only remote modified
        return remote


class LokoProjectMerge(JSONMerge):
    def __init__(self, ignore_conflicts=True, sep='/'):
        self.ignore_conflicts = ignore_conflicts
        rules = dict()
        rules['last_modify'] = dict(rule=self._date_rule, validate=lambda x: x == f'{sep}last_modify')
        rules['x'] = dict(rule=lambda local, remote: local,
                          validate=lambda x: re.search(f'position{sep}x|positionAbsolute{sep}x', x))
        rules['y'] = dict(rule=lambda local, remote: local,
                          validate=lambda x: re.search(f'position{sep}y|positionAbsolute{sep}y', x))
        super().__init__(rules=rules, sep=sep)

    def _date_rule(self, local, remote):
        local = datetime.strptime(local, '%d/%m/%Y, %H:%M:%S')
        remote = datetime.strptime(remote, '%d/%m/%Y, %H:%M:%S')
        return max(local, remote).strftime('%d/%m/%Y, %H:%M:%S')

    def __call__(self, project, fname = 'loko.project'):

        os.system(f'git config --global --add safe.directory {project}')
        repo = git.Repo(project)


        if fname not in repo.index.unmerged_blobs():
            return

        root_prj = json.loads(repo.git.show(f":1:{fname}"))
        local_prj = json.loads(repo.git.show(f":2:{fname}"))
        remote_prj = json.loads(repo.git.show(f":3:{fname}"))

        self._preprocess(root_prj)
        self._preprocess(local_prj)
        self._preprocess(remote_prj)

        merged = self.merge_conflicts(root_prj, local_prj, remote_prj)
        self._add_values_conflicts(merged)
        self._postprocess(merged)

        with open(Path(project) / fname, 'w') as f:
            json.dump(merged, f, indent=2)

    def _add_values_conflicts(self, prj):
        unresolved = {}
        node_pattern = f'^graphs{self.sep}.+{self.sep}nodes{self.sep}[a-z0-9-]+{self.sep}data'
        for el, v in self.conflicts.items():
            node_match = re.search(node_pattern, el)
            if node_match:
                tab_name = el.split('graphs'+self.sep)[1].split(self.sep+'nodes'+self.sep)[0]
                node_id = el.split(self.sep+'nodes'+self.sep)[1].split(self.sep+'data'+self.sep)[0]
                node = prj['graphs'][tab_name]['nodes'][node_id]
                prop = el.split(node_match.group())[1]
                node_up = SafeDictPath(node)
                if self.ignore_conflicts:
                    node_up.set(prop.replace(self.sep, '/'), v.get('remote'))
                    node.update(node_up.dict.copy())
                    logger.debug(f'Ignored conflict on {prop} - local: {v.get("local")} - remote: {v.get("remote")}')
                    continue
                node_up.set('conflicts'+prop.replace(self.sep, '/'), v)
                node.update(node_up.dict.copy())
            else:
                unresolved[el] = v
        if unresolved:
            logger.error(f'Unresolved conflicts on: {unresolved}')
            raise Exception('Conflict Error')

    def _dict2list(self, obj, *keys):

        obj = SafeDictPath(obj)
        nkeys = '/'.join(keys)
        cont = obj.get(nkeys)
        if isinstance(cont, dict_path.DictPath):
            cont = cont.dict.copy()
            obj.set(nkeys, list(cont.values()))

        return obj.dict.copy()


    def _list2dict(self, obj, nid, *keys):

        obj = SafeDictPath(obj)
        nkeys = '/'.join(keys)
        cont = obj.get(nkeys)
        if isinstance(cont, list):
            obj.set(nkeys, {el[nid]: el for el in cont})

        return obj.dict.copy()

    def _preprocess(self, prj):
        # list2dict
        for tab, tab_cont in prj['graphs'].items():
            tab_cont.update(self._list2dict(tab_cont, 'id', 'nodes'))
            tab_cont.update(self._list2dict(tab_cont, 'id', 'edges'))
            if 'nodes' in tab_cont:
                for node, node_cont in tab_cont['nodes'].items():
                    node_cont.update(self._list2dict(node_cont, 'id', 'data', 'inputs'))
                    node_cont.update(self._list2dict(node_cont, 'id', 'data', 'outputs'))
                    node_cont.update(self._list2dict(node_cont, 'name', 'data', 'options', 'args'))

    def _postprocess(self, prj):
        # dict2list
        for tab, tab_cont in prj['graphs'].items():
            tab_cont.update(self._dict2list(tab_cont, 'nodes'))
            tab_cont.update(self._dict2list(tab_cont, 'edges'))
            if 'nodes' in tab_cont:
                for i, node_cont in enumerate(tab_cont['nodes']):
                    node_cont.update(self._dict2list(node_cont, 'data', 'inputs'))
                    node_cont.update(self._dict2list(node_cont, 'data', 'outputs'))
                    node_cont.update(self._dict2list(node_cont, 'data', 'options', 'args'))



if __name__ == '__main__':
    import copy
    import sys

    lp_merge = LokoProjectMerge(ignore_conflicts=True)
    merged = lp_merge(project='/home/cecilia/loko/projects/problemanuovo')

    print('MERGED:', merged)

    sys.exit()

    #### modifichiamo a mano ####

    print('\n##### MANUAL #####\n')

    repo = git.Repo('/home/cecilia/loko/projects/problemanuovo')
    path = 'loko.project'
    if path not in repo.index.unmerged_blobs():
        print('no conflicts')
        with open('/home/cecilia/loko/projects/problemanuovo/loko.project') as f:
            local_prj = json.load(f)
        root_prj = copy.deepcopy(local_prj)
        remote_prj = copy.deepcopy(local_prj)
    else:
        print('conflicts')
        root_prj = json.loads(repo.git.show(f":1:{path}"))
        local_prj = json.loads(repo.git.show(f":2:{path}"))
        remote_prj = json.loads(repo.git.show(f":3:{path}"))

    print('ROOT:', root_prj)

    lp_merge._preprocess(root_prj)
    lp_merge._preprocess(local_prj)
    lp_merge._preprocess(remote_prj)

    remote_prj['last_modify'] = '20/03/2023, 19:55:39'
    local_prj['last_modify'] = '28/02/2023, 20:55:39'
    print('NODES:', list(remote_prj['graphs']['main']['nodes'].keys()))
    node = '79b9f20a-00ff-4433-a2e5-410d5a4ab6d2'  # influxdb

    root_prj['graphs']['main']['nodes'][node]['position'] = {'x': 550, 'y': 850}
    local_prj['graphs']['main']['nodes'][node]['position'] = {'x': 500, 'y': 800}
    remote_prj['graphs']['main']['nodes'][node]['position'] = {'x': 430, 'y': 300}

    root_prj['graphs']['main']['nodes'][node]['data']['options']['values']['measurement_name'] = '123'
    local_prj['graphs']['main']['nodes'][node]['data']['options']['values']['measurement_name'] = 'pasticcio'
    remote_prj['graphs']['main']['nodes'][node]['data']['options']['values']['measurement_name'] = 'ciccio'

    merged = lp_merge.merge_conflicts(root_prj, local_prj, remote_prj)
    lp_merge._add_values_conflicts(merged)

    print('NEW LAST MODIFY:', merged['last_modify'])
    print('NEW POSITION:', merged['graphs']['main']['nodes'][node]['position'])
    print('CONFLICTS:', merged.get('graphs', {}).get('main', {}).get('nodes', {}).get(node, {}).get('conflicts', {}))

    print('MERGED:', merged)

    # niente conflicts, vince remoto
    # aggiungere get
    # da mettere del dao dei progetti get, se  ci sono conflitti salva e ritorna
