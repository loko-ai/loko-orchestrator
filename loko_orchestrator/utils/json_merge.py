import itertools
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
    def __init__(self, rules=None):
        self.rules = rules or {}
        self.conflicts = {}
        self.tmp_conflicts = {}
        self.ne = 'not exist'
    def _unique(self, sequence):
        seen = set()
        return [x for x in sequence if not (x in seen or seen.add(x))]

    def merge_conflicts(self, root, local, remote, p=None, tmp_conflicts=False):
        if local == remote:
            return local
        if isinstance(local, dict) and isinstance(remote, dict):
            root_tmp = root if isinstance(root, dict) else {}
            ret = {}
            kk = self._unique(itertools.chain(local.keys(), remote.keys()))
            if not p:
                p = []
            for k in kk:
                res = self.merge_conflicts(root_tmp.get(k, self.ne), local.get(k, self.ne), remote.get(k, self.ne),
                                           p+[k], tmp_conflicts=tmp_conflicts)
                if res!=self.ne:
                    ret[k] = res
            return ret
        return self._merge(root, local, remote, p, tmp_conflicts=tmp_conflicts)

    def _tmp_conflicts(self, b1, b2):
        self.merge_conflicts(None, dict(tmp=b1), dict(tmp=b2), tmp_conflicts=True)
        tmp_conflicts = self.tmp_conflicts.copy()
        self.tmp_conflicts = {}
        return tmp_conflicts

    def _merge(self, root, local, remote, p, tmp_conflicts=False):
        if local != root:
            # both modified
            if remote != root:
                if remote==self.ne:
                    if not tmp_conflicts and self.rules and 'miss' in self.rules:
                        _tmp_conflicts = self._tmp_conflicts(local, root)
                        if self.rules['miss']['validate'](_tmp_conflicts):
                            logger.debug(f'Apply miss rule: {p} - local skipped')
                            return remote
                    return local
                if local==self.ne:
                    if not tmp_conflicts and self.rules and 'miss' in self.rules:
                        _tmp_conflicts = self._tmp_conflicts(remote, root)
                        if self.rules['miss']['validate'](_tmp_conflicts):
                            logger.debug(f'Apply miss rule: {p} - remote skipped')
                            return local
                    return remote
                if not tmp_conflicts and self.rules and 'diff' in self.rules:
                    last_key = p[-1]
                    if last_key in self.rules['diff']:
                        if self.rules['diff'][last_key]['validate'](p):
                            logger.debug(f'Apply rule: {p} - local: {local} - remote: {remote}')
                            return self.rules['diff'][last_key]['rule'](local, remote)
                logger.debug(f'Conflict on {p} - local: {local} - remote: {remote}')
                if tmp_conflicts:
                    self.tmp_conflicts[tuple(p)] = dict(local=local, remote=remote)
                else:
                    self.conflicts[tuple(p)] = dict(local=local, remote=remote)
            # only local modified
            return local
        # only remote modified
        return remote


class LokoProjectMerge(JSONMerge):
    def __init__(self, ignore_conflicts=True):
        self.ignore_conflicts = ignore_conflicts
        rules = dict(diff={}, miss={})
        rules['diff']['last_modify'] = dict(rule=self._date_rule, validate=lambda x: x == ['last_modify'])
        rules['diff']['x'] = dict(rule=lambda local, remote: local,
                                  validate=lambda x: x[-2:]==['position', 'x'] or x[-2:]==['positionAbsolute', 'x'])
        rules['diff']['y'] = dict(rule=lambda local, remote: local,
                                  validate=lambda x: x[-2:]==['position', 'y'] or x[-2:]==['positionAbsolute', 'y'])
        rules['miss'] = dict(validate=lambda x: self._miss_rule(x, [('tmp', 'position', 'x'),
                                                                    ('tmp', 'position', 'y'),
                                                                    ('tmp', 'positionAbsolute', 'x'),
                                                                    ('tmp', 'positionAbsolute', 'y')]))
        super().__init__(rules=rules)

    def _miss_rule(self, conflicts, skip_keys):
        for el in conflicts:
            if el not in skip_keys:
                logger.debug(f'Skipped miss rule on: {el}')
                return False
        return True
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
        node_pattern = f'^graphs/.+/nodes/[a-z0-9-]+/data'
        for el, v in self.conflicts.items():
            node_match = re.search(node_pattern, '/'.join(el))
            if node_match:
                tab_name = el[1]
                node_id = el[3]
                node = prj['graphs'][tab_name]['nodes'][node_id]
                prop = el[5:]
                node_up = SafeDictPath(node)
                if self.ignore_conflicts:
                    node_up.set(prop, v.get('remote'))
                    node.update(node_up.dict.copy())
                    logger.debug(f'Ignored conflict on {prop} - local: {v.get("local")} - remote: {v.get("remote")}')
                    continue
                node_up.set('conflicts'+prop, v)
                node.update(node_up.dict.copy())
            else:
                unresolved[el] = v
        if unresolved:
            logger.error(f'Unresolved conflicts on: {unresolved}')
            raise Exception('Conflict Error')

    def _dict2list(self, obj, *keys):

        obj = SafeDictPath(obj)
        cont = obj.get(keys)
        if isinstance(cont, dict_path.DictPath):
            cont = cont.dict.copy()
            obj.set(keys, list(cont.values()))

        return obj.dict.copy()


    def _list2dict(self, obj, nid, *keys):

        obj = SafeDictPath(obj)
        cont = obj.get(keys)
        if isinstance(cont, list):
            obj.set(keys, {el[nid]: el for el in cont})

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

    # sys.exit()

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
    tabname = 'Untitled. 2'
    print('NODES:', list(remote_prj['graphs'][tabname]['nodes'].keys()))
    node = '9f219eae-1e4f-45f4-acc2-011f7c831f78'  # translate

    root_prj['graphs'][tabname]['nodes'][node]['position'] = {'x': 550, 'y': 850}
    local_prj['graphs'][tabname]['nodes'][node]['position'] = {'x': 500, 'y': 800}
    remote_prj['graphs'][tabname]['nodes'][node]['position'] = {'x': 430, 'y': 300}

    root_prj['graphs'][tabname]['nodes'][node]['data']['options']['values']['measurement_name'] = '123'
    local_prj['graphs'][tabname]['nodes'][node]['data']['options']['values']['measurement_name'] = '1234'#'pasticcio'
    remote_prj['graphs'][tabname]['nodes'][node]['data']['options']['values']['measurement_name'] = 'ciccio'

    del remote_prj['graphs'][tabname]['nodes'][node]

    merged = lp_merge.merge_conflicts(root_prj, local_prj, remote_prj)
    lp_merge._add_values_conflicts(merged)

    print('CONFLICTS:', merged.get('graphs', {}).get(tabname, {}).get('nodes', {}).get(node, {}).get('conflicts', {}))

    print('MERGED:', merged)

    print('NEW LAST MODIFY:', merged['last_modify'])
    print('NEW POSITION:', merged['graphs'][tabname]['nodes'][node]['position'])

    # niente conflicts, vince remoto
    # aggiungere get
    # da mettere del dao dei progetti get, se  ci sono conflitti salva e ritorna


    # none e position vince position
    # liste invece che join OK
    # controllare questione dell'ordine OK
    # controllare merge tra branch