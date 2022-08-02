csv_reader_doc = '''### Description
The CSV READER component allows reading files in csv format. 

You have the possibility to set a separator using the **Separator** parameter. The **Infer types** parameter allows the automatic transformation of the type of non-textual fields.

### Input
The input required by this component is the file path in PosixPath format. However, the file path can also be defined when the component is created, in which case no input is required.

### Output
The submitted file is returned row by row, where each row is represented by a dictionary that has the column names as keys.'''

line_reader_doc = '''### Description
The LINE READER component allows reading text files line by line.

### Input
The input required by this component consists of the file path in PosixPath format.

### Output
The submitted file is returned on a line-by-line basis, which allows the entire file to never be completely loaded into memory.'''

file_reader_doc = '''### Description
The FILE READER component allows the reading of individual files.

### Output
Setting the **Read Content** parameter to **False**, the output provides the file path in PosixPath format. The component will then need to be connected to other components to read the content, for example *LineReader*.

On the contrary, setting the **Read Content** parameter to **True**, you can choose whether to read the content in *Binary* format. This format will be selected for reading non-text files.'''

directory_reader_doc = '''### Description
The DIRECTORY READER component allows reading files contained in a folder.

### Output
The output provides the path to the files of interest in PosixPath format. You can set **recursive** parameter to True in order to recursively read all folders contained into the main path. Finally, the **suffixes** parameter is used to filter files by extension (e.g. csv, txt, pdf).'''


file_content_doc = '''### Description
The FILE CONTENT component allows you to read the contents of a file.

### Input
The input required by this component consists of the file path in PosixPath format.

### Output
The **Binary** parameter lets you choose whether to read the file in binary or text mode.'''

file_writer_doc = '''### Description
The FILE WRITER component allows you to write files. The **Append** parameter allows you to write a file using multiple inputs. The destination path of the file can be defined when creating the block or passed as input in the previous block. In this way you have the possibility to write multiple files using one block.

### Input
Using the parameter **Save as**, the format of the data to be received as input is defined. The available formats are: *text*, *bytes* and *json*. To define the destination path of the file instead, the input is defined as:
```python
Parameters(data = data, path = filename)
```

### Output
The output confirms that the file has been written with the string: **Written to filename**.'''

csv_writer_doc = '''### Description
The CSV WRITER component allows you to write files in csv format. The separator is set via the **Separator** parameter. The **Append** parameter allows you to write a file using multiple inputs. Finally, the **Header** parameter is used to indicate whether or not to write the line containing the column names of the file.

### Input
The input must be provided as a list of dictionaries whose keys represent the names of the columns in the file.

### Output
The component returns the data received as input.'''

