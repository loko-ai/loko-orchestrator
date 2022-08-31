vision_doc = '''
### Description

VISION is the Loko AI component which allows to classify images either using a pre-trained Neural Networks, or using a transfer-learning model over one of them. Specifically, VISION helps you with training, predicting and managing your models.

### Configuration

The heading ***Available services*** allows user to select the VISION instance of interest (remembering that different vision-models will necessarily be found on different instances). 

If you just want to use a pre-trained Neural Network in order to classify your set of images, you can directly link a *File Reader* component to the *Predict* Inputs of VISION.

If you want to create a transfer-learning model to customize your classifier on your own data, follow these steps:


- **Create a model:** in *Create parameters* choose the name of the model you want to create (*Vision Model Name*) and select the pre-trained models to use (*Pretrained Models*). Then, link a *Trigger* component to the **Create** input;

- **Fit a model:** in *Fit parameters* choose the name of the model you want to train (*Vision Model*), and use a *File Reader* to pass a zipped folder to the VISION component ***Fit*** input.

- **Get prediction with a model:** in *Predict parameters* you can set the model to use (*Vision Model*) choosing between the customized models and the pre-trained NN. Then, you can choose if you want to see directly the predicted class or the probability of each of them, setting the **Predict proba** parameters. 
If you use a customized model, you can also decide to see predictions as a **generic Multi-Class** or as a **Multi-Label model**; in the latter case, if you don't want to see the probability of belonging to each class you can set the value of the **MultiLabel Threshold**, that indicate the minimum probability value in order to assign a specific class.


You may also want to:


- **Delete a model:** in the section *delete parameters* specify the model you want to delete. It's possible to delete only the customized models.

- **Get information about a model:** in *info parameters* you have to set the model name and then choose if you just want to know if the model is fitted and the pre-trained model used, or if you want **advanced** information.




### Output

For **Create, Fit and Delete** services the output messages will only be a sentence that confirms that the required action has been finalized. For the *fit* service it may take a while to have the output back, depending on how much the fitting lasts.


The output for the **info** services change if the model has already been fitted or not, and based on the setting chosen regarding advanced information. In case the model has been fitted and advanced information was activated the output will be the following:

```json
{"predictor_name": name of the model chosen, 
"pretrained_model": name of the pretrained model chosen,
"top_layer": {"n_layer":1,
    "n_classes": number of classes,
    "metrics": ["accuracy"],
    "loss_function": "binary_crossentropy",
    "epochs":100},
"fitted": say if the model was trained or not}
```

In case the model *is not fitted* or *the advanced information* is not activated, the output will be the same without the "top layer" information.

The **predict** service has different output based on the settings chosen. If the field *predict proba* has been selected, we can see the probabilities next to each labels:

```json
{"fname": name of the file used for the prediction, 
"pred": [["cat",0.9996217489242554],
        ["dog",0.001642674207687378]]}
```

Otherwise, the output will be:

```json
{"fname": name of the file used for the prediction, 
"pred": "cat"}
```

If *multilabel* is selected the output will be:

```
{"fname": name of the file used for the prediction, 
"pred": ["cat", "persian","black"]}
```
'''

textractor_doc = '''### Description
The TEXTRACT component allows you to use OCR technologies to extract textual content - from machine-readable documents - images or mixed content. One of TEXTRACT's embedded technologies is Tesseract 4, which offers the possibility to improve the process of recognition of characters and words through the use of an LSTM neural network (as default). If you want, you can also create your own settings and modify both the OCR engine and the pre-processing that must be applied to the input files.

### Input


TEXTRACT has three different input:
- OCR Extraction
- Settings
- Delete Settings

**OCR Extraction:** generally, a FileReader component must be linked to this input, and the service will directly extract the text from the input file. You can decide if you want a plain text ("plain/text") or in a json format(“application/json”) which will treat separately each page, by selecting in the **“Accept”** field the formats which suits you the most: this parameter changes your output type. Accepted file extension: jpeg, docx, pdf, txt, jpg, png, eml.


**Settings:** a trigger must be linked to this input, and using the designed parameters it's possible to create an analyzer or a pre-processing setting. The analyzer will change the OCR parameter,  whilst the pre-processing will change the way in which the file will be "seen" by the OCR engine. Once a setting is created, in order to be used in an extraction you need to specify it in the OCR Extraction parameters.


**Delete Settings:** if you want to delete an already created settings you can link a trigger to this input and specify which settings you want to delete. Warning: this action is permanent.



### Output
The output of the extraction service is a json composed of the key“ text ”and the text extracted from the submitted document as a value.

**OCR Extraction:** the output of this service depends on the type of “accept” chosen: 



- In case *“plain/text”* is chosen, the output will be a json composed of the key “path”, which as value will have the path of the examined file, and the key "text"  which will contain the text extracted from the submitted document. You can see an example below:


```json
{"path": "path/to_the/file.extension"
"text": "Lorem ipsum Lorem ipsum"}
```
    
- If instead you selected *“application/json”* as accepted value, your output will have the key “path”, with the path of the examined file as value, and the key “content” which will have as value a list of two keys (“page” and “text”) for each page present in the document examined. The “page” key will have as value an integer number, representing the position (the numeration starts from 0),  and the “text” key the extracted text for the relative page. Here an example:

```json
{ "path": "path/to_the/file.extension"
"content": [{"page": 0, 
            "text": "Lorem ipsum Lorem ipsum"},
            {"page": 1, 
             "text": "Lorem ipsum Lorem ipsum"},
            {"page": 2, 
             "text": "Lorem ipsum Lorem ipsum"}]
}
```


**Settings:** this output will only be a message which declares the setting creation.



**Delete Settings:** this output will only be a message which declares the setting creation. 


'''

# ### Configuration
# Textract allows you to configure:
# - Engine
# - Vocabulary
entity_extractor_doc = '''### Description
ENTITY EXTRACTOR is a component used to fit **NER (Named Entity Recognition) models** and extract entities from text. It’s mainly based on *SPACY* pre-trained language models.

### Configuration 

After selecting the instance of interest inside the field Available Service, you can choose one of the models inside the field *Model name* if you either want to use one of the pre-trained Spacy language model or one that you have previously created and trained, in order to make some prediction. 
Instead, if you still need to create one, you can leave that field blank, and choose the name you want to assign to your model and type it inside *New Model*. Then, you can also set the *Language* of your data and if you want to use a pre-trained model (*From Pre-Trained*) and perform a transfer learning. 

Finally, you can set several different field related to the Neural Network that will be used: 

- N. Iterations
- Mini Batch Size
- Dropout Rate

### Input
The required input depends on the task you’re going to submit. In the case of a **training task** (*fit input*), it accepts a list of **labeled sentences**:
```json
    [{"text": "Who is Shaka Khan?", 
    "entities": [{"start_index": 7, "end_index": 17, "entity": "Shaka Khan", "tag": "PERSON"}]},
```            

```json
    [{"text": "I like London and Berlin.",
    "entities": [{"start_index": 7, "end_index": 13, "entity": "London", "tag": "LOC"}, 
                {"start_index": 18, "end_index": 24, "entity": "Berlin", "tag": "LOC"}]}]
```
In the case of a **predict task** (*predict input*), it accepts as input both a string containing the text to predict or a dictionary:

```json
 "Who is Shaka Khan?"
```

```json
 {"text": "Who is Shaka Khan?"}
```

### Output
If you are **fitting** or **deleting** a model, the output will be just a message saying that the process has been successfully concluded. 


When a sentence to be **predicted** is passed, the component returns the sentence itself and the list of extracted entities:

```json
    [{"text": "Apple is looking at buying U.K. startup for $1 billion", 
    "entities": 
            [{"entity": "Apple", "tag": "ORG", "start_index": 0, "end_index": 5}, 
            {"entity": "U.K.", "tag": "LOC", "start_index": 27, "end_index": 31}, 
            {"entity": "$1 billion", "tag": "MONEY", "start_index": 44, "end_index": 54}]}]
```                  

'''

nlp_doc = '''### Description
The NLP component allows the processing of natural language, through the use of the most common methods: part of speech tagging, tokenization, lemmatization and stemming.

### Configuration
The NLP component allows you to configure:
- Language: it, en (otherwise it will be inferred)
- NLP tasks: pos, tokenize, lemmatisation, stemming



### Input
The input of the NLP service must be passed as a dictionary, with key “text” and value the text you want to parse. An example:
```json
{"text":"Today is a beautiful day"}
```

### Output
The output of the NLP service is a json. Specifically, the output will change based on the NLP task chosen:
*Pos* output:
```json
{"language":"en", "pos":[{"token":"Today","tag":"NOUN"},
{"token":"is","tag":"AUX"}, {"token":"a","tag":"DET"},
{"token":"beautiful","tag":"ADJ"},
{"token":"day","tag":"NOUN"}]
```

*Tokenize* output:
```json
{"language":"en", "tokens":["Today","is","a","beautiful","day"]}
```

*Lemmatisation* output:
```json
{"language":"en", "tokens":["today","be","a","beautiful","day"]}
```

*Stemming* output:
```json
{"language":"en", "tokens":["today","is","a","beauti","day"]}
```

### Configuration
The NLP component allows to configure:
- Language: it, en (otherwise it will be inferred)
- NLP tasks: pos, tokenize, lemmatisation, stemming'''

storage_doc = '''### Description
STORAGE component is used to persist, on the main DBs, the data processed through the developed flows.

It allows to save, read, query and delete the data in the chosen database directly within the workflows.

### Configuration
**Available services** allows to select the STORAGE instance of interest. Each service is associated to a different DB (MongoDB, MySQL, Elasticsearch ...).

**Collections** is used to select a collection already present in the DB. Use **New Collection** to create a new collection.

**Show ID** must be enabled to keep the item id in the output.

Finally, in the *Read Parameters* section, **start** and **end** are used to read the collection in batches.

You can dynamically change the configuration parameters using the Parameter object:
```python
Parameters(data = None, collection = 'collection_name', nc = None, start = 0, end = 500)
```

### Input
The component has four inputs:
- **Read** doesn't need a specific input, it reads a collection using the configuration parameters.
- **Save** accepts single dictionaries (representing rows of the collection) or list of dictionaries. Passing single rows as input can be time consuming. 
- **Delete** doesn't need a specific input and deletes the collection set in the configuration parameters.
- **Query** requires different inputs depending on the DB. Let's see some examples:

  *MongoDB* accepts tuples
```python
['find', {"author": {"$in": ["Jane Roe", "John Doe"]}}]

['aggregate', [{
    '$lookup': {
            'from': "books_selling_data",
            'localField': "isbn",
            'foreignField': "isbn",
            'as': "copies_sold"
        }
}]]
```
  In the first case we want to select books whose author is "Jane Roe" or "John Doe", in the second one we want to join the books collection with books_selling_data on field "isbn".
  
  
  *MySQL* also allows to create custom tables
  ```python
dict(query="CREATE TABLE books (isbn varchar(16) NOT NULL, title varchar(50) NOT NULL, author varchar(50) NOT NULL, PRIMARY KEY (isbn))")

dict(query="SELECT * FROM books")
```
  *Elasticsearch* accepts a dictionary containing the query
```python
{
    "query" : {
        "match_all" : {}
    }
}
```

### Output
- **Read** returns a dictionary for each element of the collection defined in the component configuration.
- **Save** returns a string with the number of elements saved.
- **Delete** returns a string: "deleted".
- **Query** returns a dictionary for each element of the requested query. If the query produces no results, None will be returned.
'''

predictor_doc = '''### Description
The PREDICTOR component is one of the most sophisticated in Loko AI, and deals with the training, prediction and evaluation of ML models. 

Its configuration and function in the flow are described below to give the user a general understanding of how this can be used.

### Input
To transmit the data of the PREDICTOR component as input, you can operate in two ways, choosing to set the parameter **Stream Data** to **True** or **False**.

In the first case it is possible to pass the samples one at a time: in this way the data will be passed as dictionaries:
```json
{"data": {"text":"Today is a beautiful day"}, "target": "class01"}
```

In the second case, ie by setting this parameter as False, the data will be transmitted all at once as a list of dictionaries:
```json
{"data": [{"text":"Today is a beautiful day"}, {"text":"Today is a bad day"}], "target": ["class01","class02"]}
```

Another parameter related to data input is target.

By setting the name of the target variable, there is no need to split the variables into date and target.

Supposing to read a line of a csv as:
```json
{"text":"Today is a beautiful day", "label": "class01"}
```

setting the target variable to label, the PREDICTOR component will automatically interpret all variables other than the target variable as explanatory and the variable label as the response variable. In this way it is not necessary to divide the data in the two keys before hand data and target.

As for fit and evaluate of PREDICTOR, it is necessary to supply both the variable data and the variable target.

Conversely, as far as concerned Predict is, the target variable is not required.

### Output
The output of theservice fit will only provide as response: Job submitted.

This means that the PREDICTOR training has started correctly. You will be able to check the results obtained through the appropriate dashboard.

As for the predict, the output is the following:
```json
{"prediction": "class01", "object": {"text":"Today is a beautiful day"}}
```

Finally, the evaluate has a more complex:
```json
{"tdist": distribution of the target variable provided
 "report_test": metrics used for the evaluation of the model (vary according to the task)
 "datetime": date and time
 "task": classification or regression
}
```'''

matcher_doc = '''### Description
MATCHER is a component used to extract entities from documents using rules. Inside there is a set of specific objects for a certain type of research.

It is possible to individually recall these objects for match bases and from the composition of them it is possible to realize more complex and articulated rules. Matcher objects work a list of tokens obtained from the text by means of a tokenizer and are validated by means of specific checkers.

### Configuration

Available services allow you to select the MATCHER instance to use. 
rule is the field in which to insert the rules to be applied to the received text in input. The matcher are divided into:

##### INDIVIDUAL TOKENS
- simple(value): it is used to match a specific token 

- regex(regex,flags=re.IGNORECASE,junk="",terminate="$"): it allows to match tokens using a regex. 

- fuzzy(ent,t=.8): the token is matched by analogy, and “t” parameter indicates the minimum threshold. 

- syn(options): it allows to match any of the tokens inserted into it.

- all(): gives back individually all the tokens present in the document.

- condition(cond): within it requires a condition and is used in combination with other matchers.

##### **MULTI TOKEN**
- span(matcher,m,n,separator="",strategy="longest"): set a minimum value (m) and a maximum value (n), it can match plus tokens that meet the conditions imposed in the matcher (join tokens to try to match the rule, between one token and the other you can set a separator).

- phrase(matchers): more matchers can be inserted inside. The tokens must sequentially respect all the matchers inserted inside the object; it returns the tokens that have respected the conditions. 

- perm(matchers): similar to Phasematcher but the conditions do not have to be respected in order, the matchers are exchanged.

- rep(matcher,minlen=1,maxlen=100): repeats the match inserted inside the object until the tokens all respect the condition set sequentially. It stops when the condition is no longer respected: the minimum and maximum of times can be indicated in the creation of the object.

- skip(start_matcher,end_matcher,max_skip=5,skipcond=MatchAll()): returns the tokens that within a range (max_skip) can match initial (start_matcher) and final (end_matcher) condition. You can set, for tokens between initial and final match, a condition that they must comply (skip_cond). 

- expand(matcher,left=10,right=10): starting from the matchate token, based on the range set within the object, it also matches a certain number of tokens left (left) and a certain number of tokens right (right). 

- context(*matchers,max_dist=100): returns all tokens in a context bounded by matchers within the object, if the distance does not exceed that of max_dist.

##### **CHOICE OF DIFFERENT CONDITIONS** 

- oneof(*matchers): more matchers can be inserted inside. It matches all tokens that respect at least one of the matcher within it (if a token matches in more matcher, returns it several times).
 
- backoff(*matchers): given a series of matchers, it returns what that matches first, leaving out all the others. 

- chain(matcher1,matcher2): it applies the second matcher to the tokens extracted from the first. It is used in combination with expand, skip, and context.

##### NORMALIZATION OF TOKENS
- norm(matcher,fun): it normalizes the tokens (via a function) that are passed into the matcher present within it. Only for control, does not transform them.

- lower(matcher): it allows passing all the tokens to the matcher inserted inside the object in lowercase. Only for the control, does not transform them.

##### **FILTER FUNCTIONS**
- filter(matcher,cond): it applies a filter to the candidates (matched tokens) after applying the matcher, it returns the candidates who meet the (boolean) condition set in the filter. The filter is a function that takes in input m and n, where n is the document length.

expandfilter(matcher,cond,left=10,right=10): it allows to apply a filter, starting from an initial matcher, also to the tokens external to it (the number depends on the parameters "left" and "right"). Useful if you want to filter candidates that respect the created rules.

##### **POST-PROCESSING**
- exclude(matcher): the tokens that match the condition within the object, will not then be displayed within the candidates. 

- post(matcher,f): it applies the function (f) to tokens extracted from the matcher with the aim of cleaning them up. The difference with the norm is that in this case the tokens are modified only for display. 

- token(fun=None): it is used to create new functions.

### Input
The component accepts as input a string that represents the text to be analyzed. 

### Output
The output structure consists of two keys: tokens and matches. Tokens returns the tokenization of the received text in input and a boolean indicates whether the token is part of matches. Matcher is represented with a list.
Each match contains the position of the first token that makes up the match (start), the position of the last (end), the score reached, the submatches and the list of tokens that make up the match. Taking as an example a simple input: "Hello 1010 world" and supposing to extract consecutive numbers within this sentence, the output will be:
```json
{"tokens": [["Hello", False], ["1010", True], ["world", False]], 
"matches":[{"start": 1, "end": 2, "score": 1, "submatches": None, 
"tokens": ["1010"]}]}
```
We then got a single match consisting of a single token, "1010", with score 1.'''

faker_doc = '''### Description
Often the lack of data means that the project processing time is very long: FAKER is the component of LOKO AI that allows you to create synthetic data, immediately and instantly available for processing.
This component is based on the python package of the same name.

These are the categories of data that can be created:
- personal information (address, first name, last name, email address, etc.) and company information (VAT/VAT number, company names, email)
- geographic information (latitude, longitude, state, city codes, etc.)
- bank and financial data, relating to credit cards, iban, bban and cryptocurrencies, but also with respect to coins (symbol, name, code)
- data of different types: boolean, timestamp, integer, float
- time data such as year, month, day, or complete dates
- simulations of complex structures such as json files, file paths, urls, tar or zip files
- Internet related data: domain names, http methods, url, ip, mac address, ports
- text data such as paragraphs, sentences, text, words

### Configuration
Available services allows you to select the FAKER instance to use.
Template is the field to insert fakers to return.

Fakers shall comply with the following form:
```json
{"first name": {"__klass__": "first_name"}, "last name": {"__klass__": "last_name"}}
```
Which produces Num. of elements outputs:
```json
{"name": "Imelda", "surname": "Battle"}
```

We list below examples of the most used FAKER types:

**PERSONAL INFORMATION:** first_name, first_name_female, first_name_male, last_name, language_name, prefix_female, prefix_male, suffix, country_calling_code, phone_number, street_address, street_name, street_suffix, simple_profile, ascii_email, iban, building_number, city, city_prefix, city suffix, country, country_code, current_country, color_name, company_name, company_email, company_suffix, company_vat, currency, currency_name, currency_simbol, price_tag, job.

**GEOGRAPHIC INFORMATIONS:** coordinates, country, country_calling_code, country_code, latitude, location_on_land, longitude.

**TIME DATA:** am_pm, century, date, date_between, month_name, time, timezone, year.

**MISC:** binary, boolean, bothify(text="## ??"), csv, image, json, null_boolean, password, tar, tsv, uuid4, zip, chrome, color, file_extension, file_name, file_path, mime_type, http_method, ipv4, ipv6, mac_address, port_number, url, user_name.

**TEXT:** paragraph, paragraphs, sentence, sentences, text, texts, word, words.

**Num. of elements** represents the number of observations required as output.

### Output
In output Num. of elements are returned'''
