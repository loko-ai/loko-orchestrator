import csv
import itertools
import json
import logging
from io import BytesIO

from loko_orchestrator.config.app_config import fsdao


# import pandas as pd



def json2excelbuffer(data):
    data = json.loads(data)
    buffer = BytesIO()
    writer = pd.ExcelWriter(buffer, engine='xlsxwriter')
    df = pd.DataFrame(data)
    df.to_excel(writer, index=False)
    writer.save()
    buffer.seek(0)
    return buffer

def json2csvbuffer(data):
    data = json.loads(data)
    df = pd.DataFrame(data)
    res = df.to_csv(None, index=False)
    buffer = BytesIO(str.encode(res))
    buffer.seek(0)
    return buffer

def txt2buffer(data):
    buffer = BytesIO(data)
    buffer.seek(0)
    return buffer

def infer_ext(path, converter, default = 'txt'):
    try:
        suffix = path.suffix[1:]
        if suffix in converter:
            return suffix
        else:
            return default
    except Exception as inst:
        logging.debug(inst)
        return default

def csv_reader(path, nrows=50, delimiter=None):
    delimiter = delimiter or ","
    ret = []
    with fsdao.get(path, "r") as f:
        reader = csv.reader(f, delimiter=delimiter, quoting=csv.QUOTE_MINIMAL)
        header = next(reader)
        for row in itertools.islice(reader, 0, nrows):
            ret.append(dict(zip(header, row)))
    return ret

def json_reader(path):
    with fsdao.get(path, "r") as f:
        ret = json.loads(f.read())
    return ret

def xlsx_reader(path):
    with fsdao.get(path, "rb") as f:
        df = pd.read_excel(f, engine='openpyxl', skiprows=0, nrows=50)
    # return df.to_dict(orient='records')
    return json.loads(df.to_json(orient='table'))['data']

def xls_reader(path):
    with fsdao.get(path, "rb") as f:
        df = pd.read_excel(f)
    # return df.to_dict(orient='records')
    return json.loads(df.to_json(orient='table'))['data']



JSON2FORMATS = dict(xls=json2excelbuffer,
                    xlsx=json2excelbuffer,
                    csv=json2csvbuffer,
                    txt=txt2buffer)

FORMATS2JSON = dict(json=json_reader,
                    csv=csv_reader,
                    xlsx=xlsx_reader,
                    xls=xls_reader)