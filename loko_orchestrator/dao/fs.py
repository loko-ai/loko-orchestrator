from abc import abstractmethod
from pathlib import Path

from sanic import response

from loko_orchestrator.utils.logger_utils import logger
from loko_orchestrator.utils.pathutils import to_relative
import shutil
from contextlib import contextmanager
import os

from loko_orchestrator.utils.trie import Trie, Value


class FSLikeDAO:
    @abstractmethod
    def copy(self, src, trg):
        pass

    @abstractmethod
    def ls(self, path="/", start=0, end=10, recursive=False, filter=None):
        pass

    @abstractmethod
    def save(self, path, stream):
        pass

    @abstractmethod
    def delete(self, path):
        pass

    @abstractmethod
    def get(self, path, mode="rb"):
        pass

    @abstractmethod
    def mkdir(self, path):
        pass

    @abstractmethod
    def is_dir(self, path):
        pass

    @abstractmethod
    def real(self, path):
        pass

    @abstractmethod
    def exists(self, path):
        pass

    @abstractmethod
    def move(self, path, newpath):
        pass

    @abstractmethod
    def response(self, path):
        pass


class FSDao(FSLikeDAO):
    def __init__(self, base, hidden=lambda x: False):
        self.base = Path(base).resolve()
        self.base.mkdir(parents=True, exist_ok=True)
        self.hidden = hidden
        self.type = None

    def copy(self, src, trg):
        src = (self.base / to_relative(src)).resolve()
        trg = (self.base / to_relative(trg)).resolve()
        # print("Copy", self.base, src.resolve(), trg)
        if src.is_dir():
            # print("TRG", trg)
            logger.debug("TRG {trg}".format(trg=trg))
            original = Path(trg / src.name)
            count = 1
            while trg.exists():
                trg = Path(str(original.parent), f"{original.stem}_copy_{count}{trg.suffix}")
                count += 1

            shutil.copytree(src, trg)
        else:
            if trg.is_dir():
                trg = trg / src.name
            original = Path(trg)
            count = 1
            while trg.exists():
                trg = Path(str(original.parent), f"{original.stem}_copy_{count}{trg.suffix}")
                count += 1
            shutil.copyfile(src, trg)

    def ls(self, path="/", start=0, end=10, recursive=False, filter=None):
        trg = self.base / to_relative(path)
        if not trg.is_dir():
            raise Exception("Not a directory")
        else:
            files = trg.rglob('*') if recursive else trg.iterdir()

            for x in sorted(files, key=os.path.getmtime, reverse=True):
                if not filter or filter(x):
                    path = x.relative_to(self.base)
                    name = x.name
                    parent = x.parent.relative_to(self.base)
                    # print(f"PARENT: {parent}")
                    yield dict(name=name, path=path, parent=parent, isDir=x.is_dir(), hidden=self.hidden(path))

    def save(self, path, stream, mode="wb", **kwargs):
        trg = self.base / to_relative(path)
        if not trg.parent.exists():
            trg.parent.mkdir(parents=True)
        with open(trg, mode) as o:
            shutil.copyfileobj(stream, o)

    def delete(self, path):
        trg = self.base / to_relative(path)
        if trg.is_dir():
            shutil.rmtree(trg)
        else:
            trg.unlink()

    @contextmanager
    def get(self, path, mode="rb"):
        trg = self.base / to_relative(path)
        f = open(trg, mode)
        try:
            yield f
        finally:
            f.close()

    def response(self, path):

        return response.file(self.real(path))

    def mkdir(self, path):
        trg = self.base / to_relative(path)
        trg.mkdir(parents=True, exist_ok=True)

    def is_dir(self, path):
        return (self.base / to_relative(path)).is_dir()

    def real(self, path):
        #
        # print(self.base)
        # print(to_relative(path))
        # print(self.base / to_relative(path))
        return self.base / to_relative(path)

    def exists(self, path):
        return (self.base / to_relative(path)).exists()

    def move(self, path, newpath):
        src = self.base / to_relative(path)
        trg = self.base / to_relative(newpath)
        if trg.is_dir():
            trg = trg / src.name
        src.rename(trg)


class LayeredFS(FSLikeDAO):
    def __init__(self):
        self.daos = Trie()

    def mount(self, path, dao):
        path = Path(path)
        self.daos.set(path.parts, dao)

    def get_type(self, dname):
        return self.daos.get_type(dname)

    @contextmanager
    def get(self, path, mode="rb"):
        # print("context_path", path)

        path = Path(path)
        dao, prefix, rest_path = self.daos.find_prefix(path.parts)
        # print("dao--------", dao)
        # print("rest_path____________", rest_path, mode)
        logger.debug("dao: %s" % dao)
        logger.debug("rest path: %s, %s" % (str(rest_path), str(mode)))
        with dao.get("/".join(rest_path), mode=mode) as f:
            yield f

    def ls(self, path="/", start=0, end=10, recursive=False, filter=None):
        """root = Path("/")
        path = Path(path)
        if path == root:
            for k in self.daos.keys():
                yield dict(name=str(k), path=k.relative_to(root), parent="/", isDir=True)

        ii = list(path.parents) + [path]
        for k, dao in self.daos.items():
            if k in ii:
                yield from dao.ls(path.relative_to(k), start, end, recursive, filter)"""

        path = Path(path)
        if path == Path("/"):
            return [dict(name=x, path=x, parent=path, type=self.daos.data.get(x).value.type, isDir=True, hidden=False)
                    for x in
                    self.daos.data.keys()]

        dao, prefix, rest_path = self.daos.find_prefix(path.parts)
        logger.debug("{d} {p} {r}".format(d=dao, p=prefix, r=rest_path))
        # print(dao,prefix,rest_path)
        listina = []
        res = [dict(x, path=Path(*prefix) / x['path'], parent=Path(*prefix) / x['parent']) for x in
               dao.ls(Path(*rest_path), start, end, recursive, filter)]
        return res

    def is_dir(self, path):
        path = Path(path)
        if path == Path("/"):
            return True
        else:
            dao, prefix, rest_path = self.daos.find_prefix(path.parts)
            return dao.is_dir(Path(*rest_path))

    def exists(self, path):
        path = Path(path)
        # print("path to check", path)
        if path == Path("/") or path == Path("."):
            return True
        dao, prefix, rest_path = self.daos.find_prefix(path.parts)
        # print("exists?")
        # print(dao,"-----", prefix, "-----", rest_path)
        # <ds4biz_orchestrator.dao.fs.FSDao object at 0x7f40b05fd040> ----- ['data'] ----- ['file_converter_files']

        # <ds4biz_orchestrator.dao.fs.FSDao object at 0x7ff6cd9c5070> ----- ['data'] ----- ['file_converter_files', 'Annotazione_picco_manicotto.xls']
        exists = dao.exists(Path(*rest_path))
        # print("esiste: ", exists)

        return exists

    def real(self, path):
        path = Path(path)
        dao, prefix, rest_path = self.daos.find_prefix(path.parts)
        # print(dao, prefix, rest_path)
        # print(dao.real(Path(*rest_path)))
        return dao.real(Path(*rest_path))

    def save(self, path, stream, mode="wb", **kwargs):
        path = Path(path)
        print("paaath", path)
        dao, prefix, rest_path = self.daos.find_prefix(path.parts)
        print(rest_path)
        dao.save(Path(*rest_path), stream, mode=mode, **kwargs)

    def mkdir(self, path, **kwargs):
        path = Path(path)
        dao, prefix, rest_path = self.daos.find_prefix(path.parts)
        dao.mkdir(Path(*rest_path, **kwargs))

    def delete(self, path):
        path = Path(path)
        dao, prefix, rest_path = self.daos.find_prefix(path.parts)
        # print(dao, prefix, rest_path)
        logger.debug("{d} {p} {r}".format(d=dao, p=prefix, r=rest_path))
        dao.delete(Path(*rest_path))

    def response(self, path):
        path = Path(path)
        dao, prefix, rest_path = self.daos.find_prefix(path.parts)
        # print(dao, prefix, rest_path)
        logger.debug("{d} {p} {r}".format(d=dao, p=prefix, r=rest_path))
        return dao.response(Path(*rest_path))

    def copy(self, src, trg):
        path = Path(src)
        trg = Path(trg)
        dao, prefix, rest_path = self.daos.find_prefix(path.parts)
        dao2, prefix2, rest_path2 = self.daos.find_prefix(trg.parts)
        # print(dao, prefix, rest_path)
        logger.debug("{d} {p} {r}".format(d=dao, p=prefix, r=rest_path))
        if dao != dao2:
            raise Exception("Can't copy file")

        return dao.copy(Path(*rest_path), Path(*rest_path2))

    def move(self, path, newpath):
        path = Path(path)
        newpath = Path(newpath)
        dao, prefix, rest_path = self.daos.find_prefix(path.parts)
        dao2, prefix2, rest_path2 = self.daos.find_prefix(newpath.parts)
        if dao != dao2:
            raise Exception("Can't move file")

        return dao.move(Path(*rest_path), Path(*rest_path2))


if __name__ == "__main__":
    dao1 = FSDao("..")
    dao2 = FSDao(".")

    daol = LayeredFS()
    dao3 = FSDao(".")
    daol.mount("/folder1", dao1)
    daol.mount("/folder2", dao2)
    for el in daol.ls("/folder1/model"):
        print(el)
    print("L")
    for el in daol.ls("/folder2"):
        print(el)

    print(daol.exists("/folder1/hh"))
