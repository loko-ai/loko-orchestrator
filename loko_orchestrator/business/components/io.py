import email
from io import BytesIO
from os import path
from pathlib import Path

from loko_orchestrator.business.engine import Fun, FileWriter, Directory, CSVReader, CSVWriter, LineReader
from loko_orchestrator.config.app_config import fsdao
from loko_orchestrator.model.components import Component
from loko_orchestrator.resources.doc_io_component import file_reader_doc, directory_reader_doc, file_content_doc, \
    line_reader_doc, file_writer_doc, csv_reader_doc, csv_writer_doc
from loko_orchestrator.utils.io_utils import content_reader
from loko_orchestrator.utils.logger_utils import logger


class FileReader(Component):
    def __init__(self):
        args = [dict(name="value", type="files", label="File", fragment="files",
                     validation=dict(required="Required field")),
                dict(name="read_content", type="boolean", label="Read content"),
                dict(name="binary", type="dynamic", label="Binary", dynamicType={True: "boolean"},
                     parent="read_content")]

        super().__init__("File Reader", group="Inputs", description=file_reader_doc, args=args, icon="RiFileList3Fill",
                         click="Send file")

    def create(self, value, read_content, binary=False, **kwargs):

        def f(_value):
            return content_reader(value["path"], binary)

        if read_content:
            return Fun(f, **kwargs)
        else:
            return Fun(lambda x: Path(value['path']), **kwargs)


class FileContent(Component):
    def __init__(self):
        args = [dict(name="binary", type="boolean", label="Binary")]
        super().__init__("File Content", group="Inputs", description=file_content_doc, args=args,
                         icon="RiFileList2Fill", configured=True)

    def create(self, binary, **kwargs):
        def f(value):
            return content_reader(value, binary)

        return Fun(f, **kwargs)


class FileWriterComponent(Component):
    def __init__(self):
        args = [dict(name="path", type="text", label="Path"),
                dict(name="type",
                     label="Save as",
                     type="select",
                     options=["text", "bytes", "json"],
                     validation={"required": "Required field"}),
                dict(name="append",
                     label="Append",
                     type="dynamic",
                     dynamicType="boolean",
                     condition='["text", "bytes"].includes({parent})',
                     parent="type"),
                dict(name="overwrite",
                     type="dynamic",
                     dynamicType={True: "boolean"},
                     parent="append",
                     label="Overwrite")
                ]
        # dict(name="to_json", label="Save as JSON", type="boolean"),
        # dict(name="append", label="Append", type="dynamic",
        #      dynamicType={False:"boolean"},
        #      parent="to_json")]

        super().__init__("File Writer", group="Outputs", description=file_writer_doc, args=args, icon="RiFileEditFill",
                         configured=True, values=dict(type="text",
                                                      overwrite=False))

    # def create(self, path=None, append=False, to_json=True, **kwargs):
    # return FileWriter(path, fsdao.base, append, to_json)
    def create(self, path=None, append=False, type="text", overwrite=False, **kwargs):
        return FileWriter(path, fsdao, append, type, overwrite, **kwargs)


class LineReaderComponent(Component):
    def __init__(self):
        super().__init__("Line Reader", group="Inputs", description=line_reader_doc, configured=True,
                         icon="RiFileReduceFill",
                         values=dict(propagate=True),
                         args=[
                             dict(name="propagate", type="boolean", label="Flush at the end",
                                  group='Advanced settings')])

    def create(self, propagate=True, **kwargs):
        return LineReader(fsdao, propagate=propagate, **kwargs)


class DirectoryComponent(Component):

    def __init__(self):
        args = [
            dict(name="value", type="directories", fragment="files",
                 validation=dict(required="Select at least one directory")),
            dict(name="recursive", type="boolean"),
            dict(name="suffixes", type="text", group='Advanced settings'),
            dict(name="propagate", type="boolean", label="Flush at the end", group='Advanced settings')]
        super().__init__("Directory Reader", group="Inputs", description=directory_reader_doc, icon="RiFolder3Fill",
                         values=dict(recursive=False, propagate=True), configured=True,
                         args=args, click="Send file")

    def create(self, value, recursive, propagate=True, suffixes=None, **kwargs):
        if suffixes:
            suffixes = [y.lower().strip() for y in suffixes.split(",")]

            def f(x):
                return x['path'].suffix[1:] in suffixes
        else:
            f = None
        return Directory(value.get("path"), fsdao, f=f, recursive=recursive, propagate=propagate,
                         **kwargs)


class CSVReaderComponent(Component):
    def __init__(self):
        args = [dict(name="value", type="files", label="File", fragment="files",
                     helper='choose a file or read input'),
                dict(name="separator", type="text", label="Separator"),
                dict(name="df", type="boolean", label="Dask Dataframe"),
                dict(name="infer_type", type="boolean", label="Infer types"),
                dict(name="propagate", type="boolean", label="Flush at the end")]

        super().__init__("CSV Reader", group="Inputs", description=csv_reader_doc, args=args,
                         values=dict(value=None, separator=",", infer_type=False, propagate=True), configured=True,
                         icon="RiFileChart2Fill", click="Send file")

    def create(self, separator, infer_type, propagate, df, value=None, **kwargs):
        return CSVReader(value, separator, fsdao, infer_type=infer_type, propagate=propagate, df=df, **kwargs)


class CSVWriterComponent(Component):
    def __init__(self):
        args = [dict(name="path", type="text", label="Path"),
                dict(name="separator", type="text", label="Separator"),
                dict(name="append",
                     label="Append",
                     type="boolean",
                     ),
                dict(name="overwrite",
                     type="dynamic",
                     dynamicType={True: "boolean"},
                     parent="append",
                     label="Overwrite")
                ]
        super().__init__("CSV Writer", icon="RiFileChartFill", group="Outputs", description=csv_writer_doc, args=args,
                         values=dict(separator=",", overwrite=False),
                         configured=True)

    def create(self, path=None, append=False, separator=',', overwrite=False, **kwargs):
        return CSVWriter(path, fsdao, append, separator, overwrite=overwrite, **kwargs)
