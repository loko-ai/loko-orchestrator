import asyncio
import inspect
import pathlib
import re
from os import path

from loko_orchestrator.business.engine import MultiFun, AsyncFun, TSCollector, ChainProcessor

from loko_orchestrator.model.components import Component, Text
from loko_orchestrator.resources.doc_ds4biz_component import faker_doc, matcher_doc, textractor_doc, nlp_doc, \
    storage_doc, predictor_doc, \
    vision_doc, entity_extractor_doc
from loko_orchestrator.utils import async_request
from loko_orchestrator.utils.async_request import AsyncRequest

timeout_vision_fit = 60 * 10


def kdict(name, **kwargs):
    return dict(__klass__=name, **kwargs)


class NLP(Component):
    def __init__(self):
        self.microservice = "nlp"

        args = [dict(name="service", type="service", label="Available services", fragment="nlp",
                     validation={"required": "Required field"}),
                dict(name="language", label="Language", type="dynamic", options=["en", "it"], dynamicType="select",
                     parent="service"),
                dict(name="tasks", label="NLP tasks", type="dynamic", options=["pos", "tokenize", "lemmatisation",
                                                                               "stemming"], dynamicType="select",
                     parent="service")]  # , group='Process'),
        # dict(name="libraries", label="Libraries", type="dynamic", options=["spacy", "nltk"],
        #      dynamicType="select", parent="service"),
        # dict(name="grammar", label="Grammar", type="dynamic", parent="service", dynamicType="text",
        #      group='Chunk')]
        # dict(name="word_norm", label="Word Normalization", type="dynamic", dynamicType="select",
        #      options=["lemmatisation", "stemming"], parent="service", group='Process')]  # ,
        # dict(name="stopwords", label="Remove stopwords", type="boolean",dynamicType="boolean", parent="service", group='Process')]

        super().__init__("NLP", icon="RiBlazeFill", group="DS4Biz", description=nlp_doc, inputs=["process"],
                         outputs=["process"], args=args,
                         values=dict(grammar="NP: {<ADJ>*<NOUN>+}", stopwords=False))

    def create(self, gateway, service, language, tasks, headers=None, **kwargs):
        headers = headers or dict()

        async def process(value, gateway=gateway, service=service, language=language, tasks=tasks):
            url = path.join(gateway, service, "process")
            libraries = 'nltk' if tasks == 'stemming' else 'spacy'

            if tasks in ['stemming', 'lemmatisation']:
                word_norm = tasks
                tasks = 'tokenize'
            else:
                word_norm = None

            content = dict(tasks=[tasks],
                           libraries=[libraries],
                           language=language,
                           word_norm=word_norm,
                           stopwords=False)
            content.update(value)

            resp = await async_request.request(url, "POST", json=content, headers=headers)
            resp = resp[libraries]
            if tasks == 'pos':
                resp['pos'] = [dict(zip(['token', 'tag'], el)) for el in resp['pos']]
                del resp['tokens']

            return resp

        # async def chunk(value, gateway=gateway, service=service, language=language, grammar=grammar):
        #     libraries = 'spacy'
        #     url = path.join(gateway, service, "chunk")
        #     content = dict(library=libraries,
        #                    language=language,
        #                    grammar=grammar)
        #     content.update(value)
        #     resp = await async_request.request(url, "POST", json=content, headers=headers)
        #     return resp

        return MultiFun(dict(process=(process, "process")), **kwargs)
        #                      chunk=(chunk, "chunk")))


"""class Textract(Component):
    def __init__(self):
        self.microservice = "ds4biz-textract"
        args = [dict(name="service", type="service", label="Available services", fragment="ds4biz-textract",
                     validation={"required": "Required field"}),
                ############################ OCR EXTRACTION #############################
                dict(name="force_ocr", label="Force OCR extraction", type="boolean",
                     description="If True, even if the document is machine readable the OCR engine will be used",
                     group="OCR Extraction"),
                dict(name="analyzer",
                     label="Analyzer",
                     type="dynamic",
                     parent="service",
                     fragment="analyzer",
                     dynamicType="dependent",
                     helper="File name of the chosen analyzer, if not set the default analyzer settings will be used",
                     group="OCR Extraction"
                     ),
                dict(name="pre_processing", label="Pre-Processing",
                     type="dynamic",
                     parent="service",
                     fragment="preprocessing",
                     dynamicType="dependent",
                     helper="File name of the chosen pre-processing, if not set no pre-processing will be done",
                     group="OCR Extraction"
                     ),
                # dict(name="post_processing", label="Post-Processing",
                #      type="dynamic",
                #      parent="service",
                #      fragment="postprocessing",
                #      dynamicType="dependent",
                #      helper="File name of the chosen pre-processing, if not set no pre-processing will be done",
                #      group="OCR Extraction"
                #      ),
                dict(name="accept", label="Accept", type="dynamic",
                     options=["application/json", "plain/text"],
                     dynamicType="select",
                     parent="service",
                     group="OCR Extraction",
                     helper="If plain is selected the entire ocr-doc will be returned, otherwise the response will be a json which separates each page. Default='application/json'"
                     ),
                # dict(name="pool",
                #      type="number",
                #      label="Concurrent calls",
                #      group="OCR Extraction",
                #      helper="Number of concurrent calls to the OCR extractor service"),
                ############################ CUSTOM SETTINGS #############################
                dict(name="settings_type", label="Settings Type",
                     options=["Analyzer", "Pre-Processing"],  # , "Post-Processing"],
                     type="select",
                     group="Custom Settings",
                     ),
                ############################ ANALYZER SETTINGS#############################
                dict(name="new_analyzer_name", label="Name", type="dynamic",
                     dynamicType="text",
                     parent="settings_type",
                     group="Custom Settings",
                     condition='{parent}==="Analyzer"',
                     helper="Name of the analyzer custom settings"),
                dict(name="oem_type", label="OEM", type="dynamic",
                     # options=[0, 1, 2, 3],
                     options=["0: legacy engine only",
                              "1: neural nets LSTM engine only",
                              "2: legacy + LSTM engines",
                              "3: default, based on what is available"],
                     dynamicType="select",
                     parent="settings_type",
                     group="Custom Settings",
                     condition='{parent}==="Analyzer"',
                     helper="OCR Engine Mode to use "),
                dict(name="psm_type", label="PSM", type="dynamic",
                     # options=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
                     options=["0: orientation and script detection (OSD) only",
                              "1: automatic page segmentation with OSD",
                              "2: automatic page segmentation, but no OSD, or OCR",
                              "3: fully automatic page segmentation, but no OSD",
                              "4: assume a single column of text of variable sizes",
                              "5: assume a single uniform block of vertically aligned text",
                              "6: assume a single uniform block of text",
                              "7: treat the image as a single text line",
                              "8: treat the image as a single word",
                              "9: treat the image as a single word in a circle",
                              "10: treat the image as a single character",
                              "11: sparse text. Find as much text as possible in no particular order",
                              "12: sparse text with OSD",
                              "13: raw line. Treat the image as a single text line, bypassing hacks that are Tesseract-specific"],
                     dynamicType="select",
                     parent="settings_type",
                     group="Custom Settings",
                     condition='{parent}==="Analyzer"',
                     helper="Page Segmentation Mode to use"),
                dict(name="lang", label="Language", type="dynamic",
                     options=["auto", "ita", "eng"],
                     dynamicType="select",
                     parent="settings_type",
                     group="Custom Settings",
                     condition='{parent}==="Analyzer"',
                     helper="If auto the language will be detected, otherwise you can select italian or english."),
                dict(name="whitelist", label="Character Whitelist ", type="dynamic",
                     dynamicType="text",
                     parent="settings_type",
                     group="Custom Settings",
                     condition='{parent}==="Analyzer"',
                     helper="The only characters that the OCR engine is allowed to recognize",
                     # helper="All the characters must be write without separator"
                     ),
                dict(name="blacklist", label="Character Blacklist ", type="dynamic",
                     dynamicType="text",
                     parent="settings_type",
                     group="Custom Settings",
                     condition='{parent}==="Analyzer"',
                     helper="Characters that must never be included in the results"),
                dict(name="vocab_file", label="Vocabulary File Name", type="dynamic",  # cambiare in File
                     dynamicType="files",
                     parent="settings_type",
                     group="Custom Settings",
                     condition='{parent}==="Analyzer"',
                     helper=""),
                dict(name="patterns_file", label="Patterns File Name", type="dynamic",
                     dynamicType="files",
                     parent="settings_type",
                     group="Custom Settings",
                     condition='{parent}==="Analyzer"',
                     helper=""),
                ############################ PRE-PROCESSING SETTINGS#############################
                dict(name="new_preprocessing_name", label="Name", type="dynamic",
                     dynamicType="text",
                     parent="settings_type",
                     group="Custom Settings",
                     condition='{parent}==="Pre-Processing"',
                     helper="Name of the pre-processing custom settings"),
                dict(name="dpi", label="DPI", type="dynamic",
                     dynamicType="number",
                     parent="settings_type",
                     group="Custom Settings",
                     condition='{parent}==="Pre-Processing"',
                     helper="DPI value to use when processing files"
                     ),
                dict(name="zoom", label="Apply Zoom", type="dynamic",
                     dynamicType="boolean",
                     parent="settings_type",
                     group="Custom Settings",
                     condition='{parent}==="Pre-Processing"',
                     ),
                dict(name="zoom_level", label="Zoom Level", type="dynamic",
                     dynamicType="number",
                     parent="zoom",
                     group="Custom Settings",
                     condition='{parent}===true',
                     helper="If the zoom rate level is set to a lower value than 1.0 the image will be shrinked, otherwise the image will be enlarged"),
                dict(name="interpolation_mode", label="Interpolation Mode", type="dynamic",
                     options=["0: INTER_NEAREST",
                              "1: INTER_LINEAR",
                              "2: INTER_CUBIC",
                              "3: INTER_AREA",
                              "4: INTER_LANCZOS4",
                              "7: INTER_MAX",
                              "8: WARP_FILL_OUTLIERS",
                              "16: WARP_INVERSE_MAP"],
                     dynamicType="select",
                     parent="zoom",
                     group="Custom Settings",
                     condition='{parent}===true',
                     description="Interpolation algorithm to use when doing the resize",
                     helper="In case of Zoom-In the image will generally look best with INTER_CUBIC mode (slow) or INTER_LINEAR (faster but still looks good);"
                            " In case of Zoom-Out the mode INTER_AREA generally works better"),
                ############################ DELETE SETTINGS #############################
                # dict(name="settings_type_d", label="Settings Types",
                #      options=["Analyzer", "Pre-Processing", "Post-Processing"],
                #      type="select",
                #      group="Delete Settings",
                #      ),
                dict(name="anal_name_delete", label="Analyzer Settings Name",
                     type="dynamic",
                     parent="service",
                     fragment="analyzer",
                     dynamicType="dependent",
                     # parent="settings_type",
                     group="Delete Settings",
                     helper="Name of the custom settings you want to delete"),
                dict(name="preproc_name_delete", label="Pre-Processing Settings Name",
                     type="dynamic",
                     parent="service",
                     fragment="preprocessing",
                     dynamicType="dependent",
                     # parent="settings_type",
                     group="Delete Settings",
                     # condition='{settings_type_d}==="Analyzer"',
                     helper="Name of the custom settings you want to delete"),
                # dict(name="postpro_name_delete", label="Post-Processing Settings Name",
                #      type="dynamic",
                #      parent="service",
                #      fragment="postprocessing",
                #      dynamicType="dependent",
                #      # parent="settings_type",
                #      group="Delete Settings",
                #      # condition='{settings_type_d}==="Analyzer"',
                #      helper="Name of the custom settings you want to delete"),

                ############################ INFO SETTINGS #############################
                # todo: poter avere doppia dipendenza (sia da service che da parametro)
                ]
        # altri gruppi: "Custom Settings" per la creazione, "Delete Settings" per cancellare e "Info Settings" per le info su un custom settings
        super().__init__("Textract", group="DS4Biz", description=textractor_doc, icon="RiBubbleChartLine", args=args,
                         values=dict(accept="plain/text", force_ocr=False,
                                     oem_type="1: neural nets LSTM engine only",
                                     psm_type="1: automatic page segmentation with OSD",
                                     lang="auto",
                                     zoom_level=1.3,
                                     dpi=100,
                                     # new_analyzer_name=None,
                                     # new_preprocessing_name=None,
                                     # zoom=False,
                                     # whitelist=None,
                                     # blacklist="",
                                     # vocab_file=None,
                                     # patterns_file=None,
                                     interpolation_mode="1: INTER_LINEAR"),
                         inputs=["ocr_extraction", "settings", "delete_settings"],
                         outputs=["ocr_extraction", "settings", "delete_settings"])

    def create(self, gateway, service, analyzer="", pre_processing=None,  # post_processing="",
               settings_type="", force_ocr=False, new_analyzer_name=None, oem_type="1: neural nets LSTM engine only",
               psm_type="1: automatic page segmentation with OSD", lang="auto", whitelist=None, blacklist="",
               vocab_file=None, patterns_file=None, new_preprocessing_name=False, dpi=None, zoom=False,
               zoom_level=1.3, interpolation_mode="1: INTER_LINEAR", accept="plain/text",  # pool=0,
               anal_name_delete=None, preproc_name_delete=None,  # postpro_name_delete=None,
               headers=None, **kwargs):
        # async def ocr_extraction():
        headers = headers or dict()
        

        async def ocr_extraction(v, event=None, gateway=gateway, service=service, accept=accept,  # pool=pool,
                                 force_ocr=force_ocr, analyzer=analyzer, pre_processing=pre_processing,
                                 # post_processing=post_processing
                                 ):
            # try:
            #     pool = int(pool)
            # except:
            #     pool = 1
            if event:
                await event.wait()

            async def extraction(v, event=None, gateway=gateway, service=service, accept=accept,
                                 force_ocr=force_ocr, analyzer=analyzer, pre_processing=pre_processing,
                                 # post_processing=post_processing
                                 ):
                base_url = path.join(gateway, service)

                headers["Accept"] = accept
                # todo: far funzionare la parte di configs
                if event:
                    await event.wait()
                extraction_url = path.join(base_url, "extract")
                resp_type = 'json' if accept == 'application/json' else 'text'
                if analyzer != "":
                    base_anal = path.join(base_url, "analyzer")
                    ret_check_anal = await async_request.request(base_anal, "GET", accept=resp_type, headers=headers)
                    if analyzer not in ret_check_anal:
                        logger.warning(
                            'Analyzer {anal} not anymore available. Extraction will be performed without considering '
                            'it.'.format(
                                anal=analyzer))
                        analyzer = ""
                if pre_processing != "":
                    base_preproc = path.join(base_url, "preprocessing")
                    ret_check_preproc = await async_request.request(base_preproc, "GET", accept=resp_type,
                                                                    headers=headers)
                    if pre_processing not in ret_check_preproc:
                        logger.warning(
                            "Pre-processing {preproc} not anymore available. Extraction will be performed without considering it.".format(
                                preproc=pre_processing))
                        pre_processing = ""
                params = dict(force_ocr=str(force_ocr).lower(), analyzer_configs=analyzer,
                              preprocessing_configs=pre_processing,
                              # postprocessing_configs=post_processing
                              )
                if isinstance(v, pathlib.PosixPath):
                    fname = str(v)

                    with fsdao.get(v, "rb") as o:
                        resp = await async_request.request(extraction_url, "POST", data=dict(file=o), params=params,
                                                           accept=resp_type,
                                                           headers=headers, timeout=60 * 10)

                else:
                    fname = v.name
                    resp = await async_request.request(extraction_url, "POST", data=dict(file=v), params=params,
                                                       accept=resp_type,
                                                       headers=headers, timeout=60 * 10)
                if accept == 'plain/text':
                    return dict(path=fname, text=resp)
                if isinstance(resp, str):
                    resp = re.sub('"text":null', '"text":None', resp)
                    resp = eval(resp)

                return dict(path=fname, content=resp)

            # if pool >= 2:
            #     return Pool(extraction, pool, asyncio.get_event_loop())
            #
            # else:
            return await extraction(v)

        async def settings(v, event=None, gateway=gateway, service=service, settings_type=settings_type,
                           new_analyzer_name=new_analyzer_name, oem_type=oem_type, psm_type=psm_type, lang=lang,
                           zoom=zoom, whitelist=whitelist, blacklist=blacklist, vocab_file=vocab_file,
                           patterns_file=patterns_file,
                           new_preprocessing_name=new_preprocessing_name, dpi=dpi, zoom_level=zoom_level,
                           interpolation_mode=interpolation_mode):

            if event:
                await event.wait()

            base_url = path.join(gateway, service)
            resp_type = 'text'

            if settings_type == "Pre-Processing":
                logger.debug("creating pre-processing...")
                url = path.join(base_url, "preprocessing", new_preprocessing_name)
                dpi = int(float(dpi))
                zoom_level = float(
                    zoom_level)  # float(zoom_level.replace(",", ".")) if "," in zoom_level else float(zoom_level) ##---->inutile, non si possono inserire , o stringhe o altri caratteri
                interpl_mode = int(interpolation_mode.split(":")[0])
                params = dict(dpi=dpi,
                              zoom_level=zoom_level,
                              interpolation_mode=interpl_mode)

            elif settings_type == "Analyzer":
                logger.debug("creating analyzer...")
                url = path.join(base_url, "analyzer", new_analyzer_name)
                oem = int(oem_type.split(":")[0])
                psm = int(psm_type.split(":")[0])
                lang = lang if lang != "auto" else None
                vocab_name = None
                patterns_name = None
                if vocab_file != "":
                    logger.debug("creating vocabulary file")
                    vocab_name = "vocab_" + new_analyzer_name + "_anal"
                    v_data = content_reader(vocab_file["path"])
                    v_data = ','.join(v_data.split('\n'))
                    v_params = dict(data=v_data)
                    v_url = path.join(base_url, "files/vocabulary/{name}".format(name=vocab_name))
                    ret = await async_request.request(v_url, "POST", params=v_params,
                                                      headers=headers, accept="application/json")
                    logger.debug(ret)
                if patterns_file != "":
                    logger.debug("creating patterns file")
                    patterns_name = "patterns_" + new_analyzer_name + "_anal"
                    p_data = content_reader(patterns_file["path"])
                    p_data = ','.join(p_data.split('\n'))
                    p_params = dict(data=p_data)
                    p_url = path.join(base_url, "files/patterns/{name}".format(name=patterns_name))
                    ret = await async_request.request(p_url, "POST", params=p_params,
                                                      headers=headers, accept="application/json")
                    logger.debug(ret)
                params = dict(oem=oem, psm=psm, lang=lang, whitelist=whitelist,
                              blacklist=blacklist, vocab_file=vocab_name, patterns_file=patterns_name)
                params = {k: v for k, v in params.items() if v != "" and v != None}

            ret = await async_request.request(url, "POST", accept=resp_type,
                                              params=params, headers=headers)
            logger.debug(ret)
            return ret

        async def delete_settings(v, event=None, gateway=gateway, service=service, anal_name_delete=anal_name_delete,
                                  preproc_name_delete=preproc_name_delete,
                                  # postpro_name_delete=postpro_name_delete
                                  ):
            ##deleting settings and if one of the settings to delete is an analyzer
            if event:
                await event.wait()
            # print("analyzer", analyzer)
            # print("preprocessing", pre_processing)
            url = path.join(gateway, service)
            resp_type = 'text'
            ret_anal = ""
            ret_preproc = ""
            # ret_postproc = ""
            # print(anal_name_delete)
            if anal_name_delete != None or anal_name_delete != "":
                logger.debug("analyzer to delete: %s" % anal_name_delete)
                base_anal = path.join(url, "analyzer")
                ret_check_anal = await async_request.request(base_anal, "GET", accept=resp_type, headers=headers)
                if (anal_name_delete in ret_check_anal) and (anal_name_delete != ""):
                    del_anal = path.join(base_anal, anal_name_delete)
                    ret_anal = await async_request.request(del_anal, "DELETE", accept=resp_type, headers=headers)
                    logger.debug(ret_anal)
                    vocab_name = "vocab_" + anal_name_delete + "_anal"
                    v_url = path.join(url, "files/vocabulary")
                    ret_v = await async_request.request(v_url, "GET", accept=resp_type, headers=headers)
                    if vocab_name in ret_v:
                        delete_vocab_url = path.join(v_url, vocab_name)
                        ret_v = await async_request.request(delete_vocab_url, "DELETE", accept="application/json",
                                                            headers=headers)
                        logger.debug(ret_v)
                    patterns_name = "patterns_" + anal_name_delete + "_anal"
                    p_url = path.join(url, "files/patterns")
                    ret_p = await async_request.request(p_url, "GET", accept=resp_type, headers=headers)
                    if patterns_name in ret_p:
                        delete_patterns_url = path.join(p_url, patterns_name)
                        ret_p = await async_request.request(delete_patterns_url, "DELETE", accept="application/json",
                                                            headers=headers)
                        logger.debug(ret_p)
                elif anal_name_delete != "":

                    ret_anal = "analyzer configuration '{anal}' already deleted".format(anal=anal_name_delete)
            if preproc_name_delete != None or preproc_name_delete != "":
                base_preproc = path.join(url, "preprocessing")

                ret_check_preproc = await async_request.request(base_preproc, "GET", accept=resp_type, headers=headers)
                if (preproc_name_delete in ret_check_preproc) and (preproc_name_delete != ""):
                    del_preproc = path.join(url, "preprocessing", preproc_name_delete)
                    ret_preproc = await async_request.request(del_preproc, "DELETE", accept=resp_type, headers=headers)

                elif preproc_name_delete != "":
                    ret_preproc = "preprocessing configuration '{preproc}' already deleted".format(
                        preproc=preproc_name_delete)

            if (anal_name_delete == None or anal_name_delete == "") and (
                    preproc_name_delete == None or preproc_name_delete == ""):
                return "No Configuration to delete specified... Select at least one analyzer/preprocessor"
            ret = "None"
            if ret_anal != "":
                if ret_preproc != "":
                    ret = ret_anal + "; " + ret_preproc
                else:
                    ret = ret_anal
            else:
                if ret_preproc != "":
                    ret = ret_preproc

            return ret

        # print(pool)
        # if int(pool) >= 2:
        return MultiFun(dict(ocr_extraction=(ocr_extraction, "ocr_extraction"), settings=(settings, "settings"),
                             delete_settings=(delete_settings, "delete_settings")), **kwargs)

        # else:
        #     f = ChainProcessor(ocr_extraction)
        #     return MultiFun(dict(ocr_extraction=(f.pro, "ocr_extraction"), settings=(settings, "settings"),
        #                          delete_settings=(delete_settings, "delete_settings")), **kwargs)


class Vision(Component):
    def __init__(self):
        self.microservice = "ds4biz-vision"
        args = [dict(name="service", type="service", label="Available services", fragment="ds4biz-vision",
                     validation={"required": "Required field"}),
                ### CREATE PARAMS ###
                dict(name="predictor_name",
                     type="text",
                     # parent="service",
                     label="Vision Model Name",
                     # dynamicType="dependent",
                     group='Create parameters',
                     # fragment="",
                     helper='Name of the model you want to use for fitting/predicting',
                     ),
                dict(name='pretrained_model',
                     type="dynamic",
                     parent="service",
                     # type='select', options= pretrained_model_vision,
                     label='Pretrained model',
                     dynamicType="dependent",
                     fragment="?model_type=pretrained",
                     group='Create parameters',
                     helper='choose your pretrained NN'),
                ### FIT PARAMS ###
                dict(name="predictor_name_fit",
                     type="dynamic",
                     parent="service",
                     label="Vision Model",
                     dynamicType="dependent",
                     group='Fit parameters',
                     fragment="?model_type=custom",
                     helper='Name of the model you want to use for fitting/predicting'
                     ),
                ### PREDICT PARAMS ###
                dict(name="predictor_name_predict",
                     type="dynamic",
                     parent="service",
                     label="Vision Model",
                     dynamicType="dependent",
                     group='Predict parameters',
                     fragment="",
                     helper='Name of the model you want to use for fitting/predicting'),
                dict(name='include_probs',
                     type='boolean',
                     label='Predict proba',
                     group='Predict parameters',
                     helper=""),
                # helper='If True the probability for each class will be returned, otherwise only the resulting class'),
                dict(name='multilabel',
                     type='boolean',
                     label='Multilabel',
                     group='Predict parameters',
                     helper=""),
                # helper='If True the results will be seen as a MultiLabel problem, otherwise as a MultiClass'),
                dict(name='multilabel_threshold',
                     type='dynamic', options=["0.5", "0.6", "0.7", "0.8", "0.9"],
                     label='Multilabel Threshold',
                     group='Predict parameters',
                     dynamicType="select",
                     parent="multilabel",
                     helper='Threshold rate to decide the belongings to one class for the MultiLabel'),
                ### INFO PARAMS ###
                dict(name="predictor_name_info",
                     type="dynamic",
                     parent="service",
                     label="Vision Model1",
                     dynamicType="dependent",
                     group='Info parameters',
                     fragment="?model_type=custom",
                     helper='Name of the model you want to know details about'),
                dict(name='adv_info',
                     type='boolean',
                     label='Advanced information',
                     group='Info parameters',
                     helper=""),
                ### DELETE PARAMS ###
                dict(name="predictor_name_delete",
                     type="dynamic",
                     parent="service",
                     label="Vision Model1",
                     dynamicType="dependent",
                     group='Delete parameters',
                     fragment="?model_type=custom",
                     helper='Name of the model you want to delete'),
                ]

        super().__init__("Vision", group="DS4Biz", icon="RiFlowChart", description=vision_doc, args=args,
                         values=dict(  # predict params
                             include_probs=False,
                             multilabel=False,
                             multilabel_threshold='0.5'),
                         inputs=["create", "fit", "predict", "info", "delete"],
                         outputs=["create", "fit", "predict", "info", "delete"])

    def create(self, gateway, service, predictor_name, predictor_name_fit, predictor_name_predict, predictor_name_info,
               predictor_name_delete,
               include_probs, multilabel, pretrained_model, adv_info, headers=None, multilabel_threshold="0.5",
               **kwargs):

        headers = headers or dict()

        async def create(value, event=None, gateway=gateway, service=service, predictor_name=predictor_name,
                         pretrained_model=pretrained_model):
            if event:
                await event.wait()
            if predictor_name == "":
                msg = "VISION SETTINGS MISSING!!!Model name not setted, you have to specify it"
                # status_code = 400
                # raise Exception()
                # abort(status_code, msg)
                # raise SanicException(msg, status_code, quiet=False)
                return msg
            url = path.join(gateway, service, predictor_name)

            # purl = path.join(url, "evaluate")
            create_params = dict(pretrained_model=pretrained_model)
            ret = await async_request.request(url, "POST", params=create_params, headers=headers)

            return ret

        async def delete(value, event=None, gateway=gateway, service=service, predictor_name=predictor_name_delete):
            if event:
                await event.wait()
            if predictor_name == "":
                msg = "VISION SETTINGS MISSING!!!Model to delete not selected, you have to specify one model name"
                # status_code = 400
                # raise Exception()
                # abort(status_code, msg)
                # raise SanicException(msg, status_code, quiet=False)
                return msg
            url = path.join(gateway, service, predictor_name)

            # purl = path.join(url, "evaluate")
            ret = await async_request.request(url, "DELETE", json=value,
                                              headers=headers)

            return ret

        async def predict(value, event=None, gateway=gateway, service=service, predictor_name=predictor_name_predict,
                          include_probs=include_probs, multilabel=multilabel,
                          multilabel_threshold=multilabel_threshold):
            if event:
                await event.wait()
            if predictor_name == "":
                msg = "VISION SETTINGS MISSING!!!Model to use for prediction not selected, you have to specify one model name"
                return msg
            url = path.join(gateway, service, predictor_name, "predict")
            # logger.debug("url    ", url)
            # url = path.join(gateway, service, "predictors", )
            resp_type = 'json'
            predict_params = dict(predictor_name=predictor_name,
                                  # top=str(top),
                                  multilabel=str(multilabel).lower(),
                                  multilabel_threshold=multilabel_threshold,
                                  include_probs=str(include_probs).lower())
            # print("params    ==== ", predict_params)
            logger.debug("pred params {params}".format(params=predict_params))
            if isinstance(value, pathlib.PosixPath):
                fname = str(value)
                with fsdao.get(value, "rb") as o:
                    resp = await async_request.request(url, "POST", params=predict_params, data=dict(file=o),
                                                       accept=resp_type,
                                                       timeout=60 * 10, headers=headers)
            else:
                fname = value.name
                resp = await async_request.request(url, "POST", params=predict_params, data=dict(file=value),
                                                   accept=resp_type,
                                                   timeout=60 * 10, headers=headers)

            return resp

        async def fit(value, event=None, gateway=gateway, service=service, predictor_name=predictor_name_fit):
            if event:
                await event.wait()
            logger.debug("Vision Model Name %s" % predictor_name)
            if predictor_name == "":
                msg = "VISION SETTINGS MISSING!!!Model to fit not selected, you have to specify one model name"
                # status_code = 400
                # raise Exception()
                # abort(status_code, msg)
                # raise SanicException(msg, status_code, quiet=False)
                return msg
                # raise SanicException("Model to fit not selected, you have to specify one model name", status_code=400)
            url = path.join(gateway, service, predictor_name, "fit")
            resp_type = 'text'
            if isinstance(value, pathlib.PosixPath):
                fname = str(value)
                with fsdao.get(value, "rb") as o:
                    resp = await async_request.request(url, "POST", data=dict(file=o),
                                                       # accept=resp_type,
                                                       timeout=60 * 10, headers=headers)
            else:
                fname = value.name
                resp = await async_request.request(url, "POST", data=dict(file=value),
                                                   # params=dict(pretrained_model=model),
                                                   # accept=resp_type,
                                                   timeout=60 * 10, headers=headers)

            return resp

        async def info(value, event=None, gateway=gateway, service=service, predictor_name=predictor_name_info,
                       adv_info=adv_info):
            if event:
                await event.wait()
            if predictor_name == "":
                msg = "VISION SETTINGS MISSING!!!Model of interest not selected, you have to specify one model name"
                # status_code = 400
                # raise Exception()
                # abort(status_code, msg)
                # raise SanicException(msg, status_code, quiet=False)
                return msg
            url = path.join(gateway, service, predictor_name, "info")

            resp_type = 'json'
            info_params = dict(predictor_name=predictor_name, advanced_info=str(adv_info).lower(), )
            resp = await async_request.request(url, "GET", json=value,
                                               accept=resp_type,
                                               params=info_params,
                                               timeout=60 * 10, headers=headers)

            return resp

        return MultiFun(dict(predict=(predict, 'predict'),
                             fit=(fit, 'fit'),
                             create=(create, 'create'),
                             info=(info, "info"),
                             delete=(delete, "delete")), **kwargs)
"""


class Predictor(Component):
    def __init__(self):
        self.microservice = "predictor"
        args = [dict(name="service",
                     type="service",
                     label="Available services",
                     fragment="predictor",
                     validation={"required": "Required field"}),
                dict(name="predictor",
                     type="dynamic",
                     dynamicType="dependent",
                     parent="service",
                     label="Predictors",
                     fragment="predictors",
                     validation={"required": "Required field"}),
                # dict(name='task',
                #      type='select', options=['classification', 'regression', 'none'],
                #      helper='if none, task will be inferred',
                #      label='Task'),
                dict(name='stream',
                     type='boolean',
                     label='Stream data'),
                dict(name='target_y',
                     type='text',
                     label='Target name',
                     helper='Name of the features you want to estimate, if not specified the default feature name is "target"'),
                ### FIT PARAMS ###
                dict(name='partial_fit',
                     type='boolean',
                     label='Partial fit',
                     group='Fit parameters'),
                dict(name='save_dataset',
                     type='select', options=['yes', 'no'],
                     label='Save dataset',
                     helper='save testset to compute the metrics report for partial fit task',
                     group='Fit parameters'),
                dict(name='report',
                     type='boolean',
                     label='Compute metrics report',
                     group='Fit parameters'),
                dict(name='test_size',
                     type="dynamic",
                     dynamicType="select",
                     parent="report",
                     condition='{parent}===true',
                     options=[0.1, 0.2, 0.3, 0.4, 0.5],
                     label='Test size',
                     group='Fit parameters'),
                dict(name='cv',
                     dynamicType="select",
                     parent="report",
                     condition='{parent}===true',
                     type='select', options=[0, 2, 3, 4, 5],
                     label='Number of folds used for cross-validation',
                     group='Fit parameters'),
                dict(name='history_limit',
                     type='select', options=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                     label='Number of models to keep saved',
                     group='Fit parameters'),
                dict(name='fit_params',
                     type='area',
                     label='Additional fit parameters',
                     group='Fit parameters'),
                ### PREDICT PARAMS ###
                dict(name='include_probs',
                     type='boolean',
                     label='Predict proba',
                     group='Predict parameters'),
                dict(name='predict_branch',
                     type='select', options=['development', 'master'],
                     label='Branch',
                     helper='fit task automatically saves model on development branch',
                     group='Predict parameters'),
                ### EVALUATE PARAMS ###
                dict(name='limit',
                     type='select', options=[-1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                     label='Limit',
                     helper='set to 0 to evalute only last model, set to -1 to evaluate all models in history',
                     group='Evaluate parameters'),
                dict(name='eval_branch',
                     type='select', options=['development', 'master'],
                     label='Branch',
                     helper='fit task automatically saves model on development branch',
                     group='Evaluate parameters'),
                ### FLUSH AT THE END ###
                dict(name='propagate',
                     type='boolean',
                     label='Flush at the end'),
                ]

        super().__init__("Predictor",
                         group="DS4Biz",
                         description=predictor_doc,
                         events=dict(type="predictor", field="predictor"),
                         inputs=["fit", "predict", "evaluate"],
                         outputs=["fit", "predict", "evaluate"],
                         icon="RiTyphoonFill",
                         args=args,
                         values=dict(stream=False, target_y='', propagate=True,
                                     # fit params
                                     partial_fit=False, fit_params='{}', cv='0', report=True, history_limit='0',
                                     test_size=0.2, save_dataset='no',
                                     # predict params
                                     include_probs=False, predict_branch='development',
                                     # evaluate params
                                     limit='0', eval_branch='development'
                                     ))

    def create(self, gateway, service, predictor, session, propagate=True, stream=False, target_y='',
               # fit params
               partial_fit=False, fit_params='{}', cv='0', report=True, history_limit='0', test_size=.2,
               save_dataset='no',
               # predict params
               include_probs=False, predict_branch='development',
               # evaluate params
               limit='0', eval_branch='development',
               headers=None, **kwargs):

        headers = headers or dict()
        gateway = path.join(gateway, "routes")

        async def init(value, gateway=gateway, service=service, predictor=predictor):
            url = path.join(gateway, service, "predictors", predictor)
            ret = await async_request.request(url, session, "POST", headers=headers)
            return ret

        async def evaluate(value, gateway=gateway, service=service, predictor=predictor,
                           limit=limit, eval_branch=eval_branch):
            task = 'none'
            url = path.join(gateway, service, "predictors", predictor)
            purl = path.join(url, "evaluate")

            ret = await async_request.request(purl, session, "POST", json=value,
                                              params=dict(limit=str(limit),
                                                          branch=eval_branch,
                                                          task=task), headers=headers)

            return ret

        async def predict(value, gateway=gateway, service=service, predictor=predictor,
                          include_probs=include_probs, predict_branch=predict_branch):
            url = path.join(gateway, service, "predictors", predictor)

            if isinstance(value, dict) and isinstance(value.get('data'), list):
                value = value['data']

            purl = path.join(url, "predict")
            if not isinstance(value, (list, tuple)):
                value = [value]

            ret = await async_request.request(purl, session, "POST", json=value,
                                              params=dict(include_probs=str(include_probs).lower(),
                                                          branch=predict_branch), headers=headers)
            ## se non e' una lista, e' un errore
            if isinstance(ret, list):
                temp = []
                for el, pred in zip(value, ret):
                    temp.append(dict(prediction=pred, object=el))
            else:
                temp = ret
            return temp

        async def fit(value, gateway=gateway, service=service, predictor=predictor,
                      partial_fit=partial_fit, cv=cv, report=report, history_limit=history_limit, test_size=test_size,
                      save_dataset=save_dataset, fit_params=fit_params):
            task = 'none'
            url = path.join(gateway, service, "predictors", predictor)
            purl = path.join(url, "fit")
            if isinstance(value, list):
                temp = dict(data=[], target=[])
                for el in value:
                    target = el["target"]
                    del el['target']
                    temp['data'].append(el)
                    temp['target'].append(target)
                value = temp
            save_dataset = 'true' if save_dataset == 'yes' else 'false'
            ret = await async_request.request(purl, session, "POST", json=value,
                                              params=dict(partial=str(partial_fit).lower(),
                                                          cv=str(cv),
                                                          report=str(report).lower(),
                                                          history_limit=str(history_limit),
                                                          test_size=str(test_size),
                                                          task=str(task),
                                                          save_dataset=str(save_dataset).lower(),
                                                          fit_params=str(fit_params)), headers=headers)

            return ret

        async def get_data_target(x, target_y=target_y):
            if target_y and (target_y in x):
                target = x[target_y]
                del x[target_y]
                return dict(data=x, target=target)
            else:
                return x

        pred = MultiFun(dict(predict=(predict, 'predict'),
                             fit=(fit, 'fit'),
                             evaluate=(evaluate, 'evaluate'),
                             create=(init, 'init')), propagate=propagate, **kwargs)

        if stream:

            mf1 = MultiFun(dict(fit=(get_data_target, 'fit'),
                                predict=(get_data_target, 'predict'),
                                evaluate=(get_data_target, 'evaluate'),
                                create=(get_data_target, 'init')),
                           stream_result=False, **kwargs)

            tsf = TSCollector()
            tsp = TSCollector()
            tse = TSCollector()
            tsc = TSCollector()

            mf1.pipe(tsf, output='fit')
            mf1.pipe(tsp, output='predict')
            mf1.pipe(tse, output='evaluate')
            mf1.pipe(tsc, output='init')

            tsf.pipe(pred, input='fit')
            tsp.pipe(pred, input='predict')
            tse.pipe(pred, input='evaluate')
            tsc.pipe(pred, input='create')

            return ChainProcessor(mf1, pred, **kwargs)
        else:
            return pred


class Matcher(Component):
    def __init__(self):
        self.microservice = "matcher"
        args = [dict(name="service", type="service", label="Available services", fragment="matcher",
                     validation={"required": "Required field"}),
                dict(name="rule", type="code", label="Rule", validation={"required": "Required field"})]

        super().__init__("Matcher", group="DS4Biz", description=matcher_doc, args=args, icon="RiFocus2Fill")

    def create(self, gateway, service, rule, headers=None, **kwargs):
        headers = headers or dict()

        async def f(v):
            url = path.join(gateway, service, "extract")
            if isinstance(v, list):
                resp = await async_request.request(url, "POST", json=dict(tokens=v, rule=rule), headers=headers)
            else:
                resp = await async_request.request(url, "POST", json=dict(text=v, rule=rule), headers=headers)
            return resp

        return AsyncFun(f, **kwargs)


class Faker(Component):
    def __init__(self):
        self.microservice = "ds4biz-faker"
        args = [dict(name="service", type="service", label="Available services", fragment="ds4biz-faker",
                     validation={"required": "Required field"}),
                dict(name="n", type="number", label="Num. of elements"),
                dict(name="template", type="code", label="Template", validation={"required": "Required field"})]

        super().__init__("Faker", group="DS4Biz", description=faker_doc, args=args, icon="RiLinksFill",
                         click="Generate")

    def create(self, gateway, service, template, n=10, headers=None, **kwargs):
        headers = headers or dict()
        n = int(n)

        async def f(v):
            url = path.join(gateway, service, "generate")
            d = eval(template)

            resp = await async_request.request(url, "POST", json=d, params=dict(n=n), headers=headers)
            return resp

        return AsyncFun(f, stream=True, **kwargs)


class Anonymizer(Component):
    def __init__(self):
        args = [dict(name="service", type="service", label="Available services", fragment="ds4biz-faker",
                     validation=dict(required="Required field")),
                dict(name="template", type="code", label="Template", validation={"required": "Required field"})]

        super().__init__("Anonymizer", group="DS4Biz", icon="RiSafeFill", args=args)

    def create(self, gateway, service, template, n=10, headers=None, **kwargs):
        headers = headers or dict()
        n = int(n)

        async def f(v):
            url = path.join(gateway, service, "mask")
            d = eval(template)

            resp = await async_request.request(url, "POST", json=d, params=dict(n=n), headers=headers)
            return resp

        return AsyncFun(f, stream=True, **kwargs)


class Entities(Component):
    def __init__(self):
        self.microservice = "ds4biz-entity-extractor"

        args = [dict(name="service", type="service", label="Available services", fragment="ds4biz-entity-extractor",
                     validation={"required": "Required field"}),
                dict(name="model_name",
                     label="Model name",
                     type="dynamic",
                     parent="service",
                     dynamicType="dependent",
                     fragment="all_extractors",
                     helper=''),
                dict(name="new_model_name",
                     type='text',
                     label='New Model',
                     group='Fit Parameters',
                     helper="",
                     ),
                dict(name="lang",
                     label="Language",
                     type="select",
                     options=["it", "en"],
                     group="Fit Parameters",
                     helper=""),
                dict(name="extend_pretrained",
                     label="From Pretrained",
                     type="boolean",
                     group="Fit Parameters",
                     helper=""),
                dict(name="n_iter",
                     label="N. Iterations",
                     type="number",
                     group="Fit Parameters",
                     helper=""),
                dict(name="minibatch_size",
                     label="Mini-Batch Size",
                     type="number",
                     group="Fit Parameters",
                     helper=""),
                dict(name="dropout_rate",
                     label="Dropout Rate",
                     type="number",
                     group="Fit Parameters",
                     helper=""),

                # dict(name="template", type="code", label="Template", validation={"required": "Required field"})
                ]

        super().__init__("Entities", group="DS4Biz",
                         description=entity_extractor_doc,
                         inputs=["fit", "predict", "delete"],
                         outputs=["fit", "predict", "delete"],
                         icon="RiTyphoonFill",
                         args=args,
                         values=dict(extend_pretrained=False, lang='it', n_iter=100, minibatch_size=500,
                                     dropout_rate="0.2"
                                     ))

    def create(self, gateway, service, model_name, new_model_name, lang, extend_pretrained, n_iter,
               minibatch_size, dropout_rate, headers=None, **kwargs):
        headers = headers or dict()
        typology = 'trainable_spacy'

        async def fit(v):
            new_model = dict(identifier=new_model_name,
                             typology=typology,
                             lang=lang,
                             extend_pretrained=extend_pretrained,
                             n_iter=n_iter,
                             minibatch_size=minibatch_size,
                             dropout_rate=dropout_rate)

            url = path.join(gateway, service, "create")
            ret = await async_request.request(url, "POST", headers=headers, json=new_model)
            if not ret:
                return ret
            url = path.join(gateway, service, "train_ner")
            ret = await async_request.request(url, "POST", headers=headers, json=v,
                                              params=dict(extractor=new_model_name))
            print(ret)
            return ret

        async def predict(v):
            url = path.join(gateway, service, model_name or new_model_name, "extract")
            req = dict(text=v) if isinstance(v, str) else v
            ret = await async_request.request(url, "POST", headers=headers, json=req)
            return dict(text=req['text'], entities=ret)

        async def delete(v):
            url = path.join(gateway, service, model_name or new_model_name, "delete")
            ret = await async_request.request(url, "DELETE", headers=headers)
            return ret

        ret = MultiFun(dict(fit=(fit, 'fit'),
                            predict=(predict, 'predict'),
                            delete=(delete, 'delete')), **kwargs)
        return ret


class Crumbs(Component):
    def __init__(self):
        args = [dict(name="service", type="service", label="Available services", fragment="ds4biz-faker",
                     validation={"required": "Required field"}),
                dict(name="template", type="code", label="Template", validation={"required": "Required field"})]

        super().__init__("Crumbs", group="DS4Biz", args=args)

    def create(self, gateway, service, template, n=10, headers=None, **kwargs):
        headers = headers or dict()
        n = int(n)

        async def f(v):
            url = path.join(gateway, service, "mask")
            d = eval(template)

            resp = await async_request.request(url, "POST", json=d, params=dict(n=n), headers=headers)
            return resp

        return AsyncFun(f, stream=True, **kwargs)


def dictify(el):
    if not isinstance(el, dict):
        return dict(data=el)
    else:
        return el


class Storage(Component):
    def __init__(self):
        self.microservice = "ds4biz-storage"
        args = [dict(name="service", type="service", label="Available services", fragment="ds4biz-storage",
                     validation={"required": "Required field"}),
                dict(name="collection", type="dynamic", dynamicType="dependent", parent="service", label="Collections",
                     fragment="collections"),
                dict(name="nc", type="dynamic", dynamicType="text", parent="collection", condition='{parent}===""',
                     label="New collection", description="Choose the new collection name"),
                dict(name="start", label="Start", type="number", group="Read Parameters"),
                dict(name="end", label="End", type="number", group="Read Parameters"),
                dict(name="propagate", type="boolean", label="Flush at the end"),
                dict(name="show_id", label="Show ID", type="boolean",
                     description="Enable this option if you want to keep the item id in the output")
                ]
        super().__init__("Storage", group="DS4Biz", description=storage_doc,
                         icon="RiStackFill", args=args,
                         inputs=["read", "save", "delete", "query"],
                         outputs=["read", "save", "delete", "query"], events=dict(type="ds4biz"),
                         values=dict(propagate=True, show_id=False))

    def create(self, service, collection, gateway, nc=None, start=0, end=500, headers=None, show_id=False, **kwargs):
        headers = headers or dict()

        async def read(v, service=service, collection=collection, nc=nc, gateway=gateway, start=start, end=end,
                       show_id=show_id,
                       **kwargs):
            url = path.join(gateway, service, "collections", collection or nc)
            show_id = str(show_id).lower()
            req = AsyncRequest(url=url, method="GET", params=dict(start=start, end=end, show_id=show_id),
                               headers=headers)
            # ret = await async_request.request(url, "GET", params=dict(start=start, end=end), headers=headers)
            # if not show_id:
            #     for el in ret:
            #         del el["_id"]
            return req

        async def save(v, service=service, collection=collection, nc=nc, gateway=gateway, **kwargs):
            url = path.join(gateway, service, "collections", collection or nc)
            if not isinstance(v, (list, tuple)):
                v = [v]
            r = await async_request.request(url, "POST", json=[dictify(x) for x in v], headers=headers)
            return r

        async def delete(v, service=service, collection=collection, nc=nc, gateway=gateway, **kwargs):
            url = path.join(gateway, service, "collections", collection or nc)
            r = await async_request.request(url, "DELETE", headers=headers)
            return r

        async def query(v, service=service, collection=collection, nc=nc, gateway=gateway, show_id=show_id, **kwargs):
            url = path.join(gateway, service, "collections", collection or nc, 'query')
            show_id = str(show_id).lower()
            req = AsyncRequest(url=url, method="POST", json=dict(q=v), params=dict(show_id=show_id), headers=headers)
            return req

        return MultiFun(
            dict(read=(read, "read"), save=(save, "save"), delete=(delete, "delete"), query=(query, "query")), **kwargs)
